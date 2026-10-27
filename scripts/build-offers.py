#!/usr/bin/env python3
"""Build the Dealux offer pages from an Impact "Ads" export (image ads only).

Usage: python3 scripts/build-offers.py path/to/Ads.csv

Every active, unexpired image ad gets its own indexable page so the banner can
rank in Google/Bing web and image search:
  /offers/<slug>/        offer page: banner image, description, deal, tracked CTA,
                         Impact impression pixel, ImageObject + Offer JSON-LD
  /offers/               index of every offer
  /data/offers.json      offer data (merged across runs, keyed by ad id)
  /sitemap-offers.xml    sitemap with image:image entries (added to sitemap-index.xml)
and refreshes the "Featured offers" block on the homepage (between the
offers:start / offers:end markers, below Featured videos). Re-running merges in
new ads and keeps first-seen dates, so it is safe to run with several exports.
"""
import csv, html, importlib.util, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location('vid', os.path.join(HERE, 'build-videos.py'))
vid = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vid)
SITE, TODAY, esc, slugify = vid.SITE, vid.TODAY, vid.esc, vid.slugify
HOME_COUNT = 12


def image_of(r):
    if r['HostedBy'].strip() == 'URL' and r['Creative'].strip().startswith(('http://', 'https://')):
        return r['Creative'].strip()
    return f"https://a.impactradius-go.com/display-ad/{r['ProgramId'].strip()}-{r['AdId'].strip()}"


def program_names():
    """Impact program id -> brand name, from the tracked links in brands.json."""
    names = {}
    for name, link in json.load(open('data/brands.json', encoding='utf-8')):
        m = re.search(r'/c/\d+/\d+/(\d+)', link)
        if m:
            names.setdefault(m.group(1), html.unescape(name))
    return names


PROGRAMS = {}


def clean_name(r):
    name = re.sub(r'\.(jpe?g|png|gif|webp)$', '', r['Name'].strip(), flags=re.I)
    name = re.sub(r'[\s_\-]*\(?\b\d{2,4}\s*[x×*\s_\-]\s*\d{2,4}\b\)?(px)?', '', name).replace('_', ' ').strip(' -_|')
    return re.sub(r'\s+', ' ', name) or r['Name'].strip()


def offer_of(r):
    brand = PROGRAMS.get(r['ProgramId'].strip()) or vid.brand_of(r)
    name = clean_name(r)
    deal = vid.deal_of(r)
    desc = re.sub(r'\s+', ' ', r['DealDescription'] or r['Description']).strip()
    if not desc:
        desc = (f"{deal}. " if deal else '') + f"See “{name}” from {brand} and tap through for {brand}’s latest offer on Dealux."
    w, h = r['ThirdPartyServableAdCreativeWidth'].strip(), r['ThirdPartyServableAdCreativeHeight'].strip()
    return dict(adid=r['AdId'].strip(), pid=r['ProgramId'].strip(), name=name, brand=brand, desc=desc, deal=deal,
                img=image_of(r), alt=r['ImageAlternativeTag'].strip() or f'{name} — {brand}', link=r['TrackingLink'].strip(),
                w=w if w.isdigit() else '', h=h if h.isdigit() else '', end=r['LimitedTimeEndDate'][:10], date=TODAY,
                slug=f"{slugify(brand + ' ' + name)[:80].strip('-')}-{r['AdId'].strip()}")


def figure(o, lazy=False):
    size = f' width="{o["w"]}" height="{o["h"]}"' if o['w'] and o['h'] else ''
    return (f'<img class="offer-banner" src="{esc(o["img"])}" alt="{esc(o["alt"])}"{size}'
            f'{" loading=\"lazy\"" if lazy else ""} referrerpolicy="no-referrer">')


def offer_ld(o):
    url = f"{SITE}/offers/{o['slug']}/"
    img = {'@type': 'ImageObject', 'contentUrl': o['img'], 'url': o['img'], 'name': o['name'], 'caption': o['alt'],
           'description': o['desc'], 'uploadDate': o['date'], 'representativeOfPage': True,
           'creditText': o['brand'], 'copyrightNotice': f"© {o['brand']}", 'acquireLicensePage': url}
    if o['w'] and o['h']:
        img['width'], img['height'] = int(o['w']), int(o['h'])
    return {'@context': 'https://schema.org', '@type': 'WebPage', 'name': f"{o['name']} — {o['brand']}", 'url': url,
            'description': o['desc'], 'primaryImageOfPage': img, 'image': img,
            'about': {'@type': 'Organization', 'name': o['brand']},
            'publisher': {'@type': 'Organization', 'name': 'Dealux', 'url': SITE}}


def offer_page(o, related):
    t = esc(o['name'])
    url = f"{SITE}/offers/{o['slug']}/"
    crumbs = {'@context': 'https://schema.org', '@type': 'BreadcrumbList', 'itemListElement': [
        {'@type': 'ListItem', 'position': 1, 'name': 'Home', 'item': SITE + '/'},
        {'@type': 'ListItem', 'position': 2, 'name': 'Offers', 'item': SITE + '/offers/'},
        {'@type': 'ListItem', 'position': 3, 'name': o['name'], 'item': url}]}
    head = '\n'.join(['<meta name="robots" content="index, follow, max-image-preview:large">',
                      '<meta property="og:type" content="website">', f'<meta property="og:title" content="{t}">',
                      f'<meta property="og:url" content="{url}">', f'<meta property="og:image" content="{esc(o["img"])}">',
                      '<meta name="twitter:card" content="summary_large_image">',
                      vid.ld_script(offer_ld(o)), vid.ld_script(crumbs)])
    deal = f'<p class="promo-note"><b>Current deal:</b> {esc(o["deal"])}</p>' if o['deal'] else ''
    ends = f'<p class="muted">Offer ends {esc(o["end"])}.</p>' if o['end'] else ''
    more = ''.join(f'<a class="card video-mini" href="/offers/{r["slug"]}/">{esc(r["name"])}<span class="muted">{esc(r["brand"])}</span></a>'
                   for r in related)
    main = f'''<div class="post-layout">
<article class="post offer-page">
  <a class="muted" href="/offers/">← All offers</a>
  <span class="eyebrow">{esc(o["brand"])} · Offer</span>
  <h1>{t}</h1>
  <figure><a href="{esc(o["link"])}" target="_blank" rel="nofollow sponsored noopener">{figure(o)}</a>
    <figcaption class="muted">{esc(o["alt"])}</figcaption></figure>
  <p>{esc(o["desc"])}</p>
  {deal}{ends}
  <p><a class="btn btn-gold" href="{esc(o["link"])}" target="_blank" rel="nofollow sponsored noopener">Get the {esc(o["brand"])} offer →</a></p>
  {vid.pixel(o)}
</article>
<aside class="post-sidebar">
  <div class="card promo-card">
    <span class="eyebrow">More offers</span>
    <div class="video-mini-list">{more}</div>
  </div>
</aside>
</div>'''
    return shell(f'{t} — {esc(o["brand"])} deal | Dealux', esc(o['desc'][:160]), url, head, main)


def shell(*a):
    return vid.page_shell(*a).replace('data-page="videos"', 'data-page="offers"').replace(
        '</head>', '<style>.offer-banner{max-width:100%;height:auto;display:block;margin:0 auto}'
                   '.offer-card .offer-thumb{display:flex;align-items:center;justify-content:center;min-height:140px;background:#f6f6f6;border-radius:8px;overflow:hidden}'
                   '.offer-card .offer-banner{max-height:220px;width:auto}</style>\n</head>', 1)


def card(o):
    return (f'<div class="card video-card offer-card">'
            f'<a class="offer-thumb" href="/offers/{o["slug"]}/">{figure(o, lazy=True)}</a>'
            f'<span class="eyebrow">{esc(o["brand"])}</span>'
            f'<h3><a href="/offers/{o["slug"]}/">{esc(o["name"])}</a></h3>'
            + (f'<p class="promo-note">{esc(o["deal"])}</p>' if o['deal'] else f'<p class="muted">{esc(o["desc"])}</p>') +
            f'<div class="product-actions"><a class="btn btn-ghost" href="/offers/{o["slug"]}/">Details</a>'
            f'<a class="btn btn-gold" href="{esc(o["link"])}" target="_blank" rel="nofollow sponsored noopener">Get offer →</a></div>'
            f'</div>')


def main(csv_path):
    rows = [r for r in csv.DictReader(open(csv_path, encoding='utf-8-sig'))
            if r['AdType'] == 'IMAGE' and r['State'] == 'ACTIVE' and r['TrackingLink'].strip()
            and not (r['LimitedTimeEndDate'].strip() and r['LimitedTimeEndDate'][:10] < TODAY)]
    PROGRAMS.update(program_names())
    old = {o['adid']: o for o in json.load(open('data/offers.json', encoding='utf-8'))} if os.path.exists('data/offers.json') else {}
    for r in rows:
        o = offer_of(r)
        o['date'] = old.get(o['adid'], o)['date']
        old[o['adid']] = o
    offers = [o for o in old.values() if not (o['end'] and o['end'] < TODAY)]
    offers.sort(key=lambda o: (o['date'], int(o['adid'])), reverse=True)
    json.dump(offers, open('data/offers.json', 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))

    for i, o in enumerate(offers):
        same = [x for x in offers if x['pid'] == o['pid'] and x is not o][:4]
        related = same + [offers[(i + k) % len(offers)] for k in range(1, 9 - len(same))]
        os.makedirs(f"offers/{o['slug']}", exist_ok=True)
        open(f"offers/{o['slug']}/index.html", 'w', encoding='utf-8').write(offer_page(o, related[:8]))

    n = len(offers)
    index = (f'<h1>Featured offers &amp; deals</h1>\n<p class="muted">{n:,} current offers and promotions from our partner brands.</p>\n'
             f'<div class="grid video-grid">{"".join(card(o) for o in offers)}</div>')
    items = {'@context': 'https://schema.org', '@type': 'ItemList', 'name': 'Dealux offers', 'itemListElement': [
        {'@type': 'ListItem', 'position': k + 1, 'url': f"{SITE}/offers/{o['slug']}/"} for k, o in enumerate(offers[:100])]}
    open('offers/index.html', 'w', encoding='utf-8').write(
        shell('Featured offers &amp; deals | Dealux', f'Browse {n:,} current offers, promotions and deals from Dealux partner brands.',
              f'{SITE}/offers/', vid.ld_script(items), index))

    entry = lambda o: (f"  <url><loc>{SITE}/offers/{o['slug']}/</loc><lastmod>{o['date']}</lastmod>"
                       f"<image:image><image:loc>{html.escape(o['img'], quote=False)}</image:loc>"
                       f"<image:title>{html.escape(o['name'], quote=False)}</image:title>"
                       f"<image:caption>{html.escape(o['alt'], quote=False)}</image:caption></image:image></url>\n")
    open('sitemap-offers.xml', 'w', encoding='utf-8').write(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
        'xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">\n'
        f'  <url><loc>{SITE}/offers/</loc><lastmod>{TODAY}</lastmod><changefreq>daily</changefreq><priority>0.8</priority></url>\n'
        + ''.join(entry(o) for o in offers) + '</urlset>\n')
    idx = open('sitemap-index.xml', encoding='utf-8').read()
    loc = f'<loc>{SITE}/sitemap-offers.xml</loc>'
    if loc in idx:
        idx = re.sub(re.escape(loc) + r'<lastmod>[^<]*</lastmod>', f'{loc}<lastmod>{TODAY}</lastmod>', idx)
    else:
        idx = idx.replace('</sitemapindex>', f'  <sitemap>{loc}<lastmod>{TODAY}</lastmod></sitemap>\n</sitemapindex>')
    open('sitemap-index.xml', 'w', encoding='utf-8').write(idx)

    # Homepage block: one offer per advertiser, round-robin, below Featured videos.
    feat = vid.featured(offers)
    block = ('<!-- offers:start -->\n<section class="video-block" aria-label="Featured offers">\n'
             f'<h2>Featured offers <a class="see-all" href="/offers/">All {n:,} offers →</a></h2>\n'
             f'<div class="grid video-grid">{"".join(card(o) for o in feat)}</div>\n</section>\n<!-- offers:end -->')
    h = open('index.html', encoding='utf-8').read()
    if '<!-- offers:start -->' in h:
        h = re.sub(r'<!-- offers:start -->.*?<!-- offers:end -->', lambda m: block, h, count=1, flags=re.S)
    else:
        h = h.replace('<!-- videos:end -->', '<!-- videos:end -->\n' + block, 1)
    if '.offer-banner{' not in h:
        h = h.replace('</head>', '<style>.offer-card .offer-thumb{display:flex;align-items:center;justify-content:center;min-height:140px;'
                                 'background:#f6f6f6;border-radius:8px;overflow:hidden}.offer-banner{max-width:100%;height:auto}'
                                 '.offer-card .offer-banner{max-height:220px;width:auto}</style>\n</head>', 1)
    open('index.html', 'w', encoding='utf-8').write(h)
    print(f'{n:,} offer pages from {len(rows):,} active image ads; homepage shows {len(feat)}')


if __name__ == '__main__':
    main(sys.argv[1])
