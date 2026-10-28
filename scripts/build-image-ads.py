#!/usr/bin/env python3
"""Build the Dealux image-ad pages from one or more Impact "Ads" exports (image ads only).

Usage: python3 scripts/build-image-ads.py path/to/impact-image-ads.csv [more.csv ...]

New exports are merged into data/ads.json (the full ad list), so earlier imports are kept.
Every banner gets its own indexable page at /ads/<slug>/. Ads imported before data/ads.json
existed ("static") are written as files; the rest are rendered by the ad-page edge function from
data/ad-pages/<n>.json shards (one file per ad made the deploy too big to upload). Also writes
/ads/ + /ads/page/<n>/ (paginated directory), /sitemap-ads.xml (image sitemap, added to sitemap-index.xml) and a
"Featured offers" block on the homepage right after the videos block.

Ad images are served from /ad-img/<program>-<ad> (a _redirects proxy to Impact's image
host) because a.impactradius-go.com's robots.txt blocks crawlers, which would keep the
images out of Google Images. Shared helpers come from build-videos.py.
"""
import csv, glob, html, importlib.util, json, os, re, shutil, sys

spec = importlib.util.spec_from_file_location('bv', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'build-videos.py'))
bv = importlib.util.module_from_spec(spec); spec.loader.exec_module(bv)
SITE, TODAY, esc, ld_script = bv.SITE, bv.TODAY, bv.esc, bv.ld_script
HOME_COUNT = 12
PER_PAGE = 120
MANIFEST = 'data/ads.json'
SHARDS = 128  # must match netlify/edge-functions/ad-page.ts
# The site is English-only; other-language creatives and tiny logos/buttons aren't useful offers.
LANGS = {'', 'ENGLISH', 'ENGLISH_GB', 'ENGLISH_US', 'ENGLISH_AU', 'ENGLISH_CA'}
ROBOTS = '<meta name="robots" content="index, follow, max-image-preview:large">'


def img_path(a):
    return f"/ad-img/{a['pid']}-{a['adid']}"


def img_tag(a, lazy=True):
    dims = f' width="{a["w"]}" height="{a["h"]}"' if a['w'] and a['h'] else ''
    return f'<img src="{img_path(a)}" alt="{esc(a["alt"])}"{dims}{" loading=\"lazy\"" if lazy else ""} style="max-width:100%;height:auto">'


def ad_page(a, related, parts=False):
    t = esc(a['name'])
    url, img = f"{SITE}/ads/{a['slug']}/", SITE + img_path(a)
    img_ld = {'@context': 'https://schema.org', '@type': 'ImageObject', 'name': a['name'], 'description': a['desc'],
              'caption': a['alt'], 'contentUrl': img, 'url': url, 'uploadDate': a['date'],
              'creator': {'@type': 'Organization', 'name': a['brand']}, 'creditText': a['brand'],
              'publisher': {'@type': 'Organization', 'name': 'Dealux', 'url': SITE}}
    if a['w'] and a['h']:
        img_ld.update(width=int(a['w']), height=int(a['h']))
    if a.get('labels'):
        img_ld['keywords'] = a['labels']
    crumbs = {'@context': 'https://schema.org', '@type': 'BreadcrumbList', 'itemListElement': [
        {'@type': 'ListItem', 'position': 1, 'name': 'Home', 'item': SITE + '/'},
        {'@type': 'ListItem', 'position': 2, 'name': 'Offers', 'item': SITE + '/ads/'},
        {'@type': 'ListItem', 'position': 3, 'name': a['name'], 'item': url}]}
    og = [ROBOTS, '<meta property="og:type" content="article">', f'<meta property="og:title" content="{t}">',
          f'<meta property="og:description" content="{esc(a["desc"][:200])}">', f'<meta property="og:url" content="{url}">',
          f'<meta property="og:image" content="{img}">', f'<meta property="og:image:alt" content="{esc(a["alt"])}">']
    if a['w'] and a['h']:
        og += [f'<meta property="og:image:width" content="{a["w"]}">', f'<meta property="og:image:height" content="{a["h"]}">']
    og += ['<meta name="twitter:card" content="summary_large_image">', f'<meta name="twitter:image" content="{img}">']
    head = '\n'.join(og + [f'<link rel="preload" as="image" href="{img_path(a)}">', ld_script(img_ld), ld_script(crumbs)])
    facts = []
    if a['deal']:
        facts.append(f'<p class="promo-note"><b>Current deal:</b> {esc(a["deal"])}</p>')
    if a.get('ends'):
        facts.append(f'<p class="muted">Limited time — valid until {esc(a["ends"])}.</p>')
    if a['w'] and a['h']:
        facts.append(f'<p class="muted">Banner size: {a["w"]}×{a["h"]}</p>')
    if a.get('labels'):
        facts.append(f'<p class="muted">Topics: {esc(", ".join(a["labels"]))}</p>')
    cap = f'\n  <figcaption class="muted">{esc(a["alt"])}</figcaption>' if a['alt'] != a['name'] else ''
    more = ''.join(f'<a class="card video-mini" href="/ads/{r["slug"]}/">{esc(r["name"])}<span class="muted">{esc(r["brand"])}</span></a>' for r in related)
    main = f'''<div class="post-layout">
<article class="post">
  <a class="muted" href="/ads/">← All offers</a>
  <span class="eyebrow">{esc(a["brand"])} · Offer</span>
  <h1>{t}</h1>
  <figure><a href="{esc(a["link"])}" target="_blank" rel="nofollow sponsored noopener">{img_tag(a, lazy=False)}</a>{cap}</figure>
  <p>{esc(a["desc"])}</p>
  {"".join(facts)}
  <p><a class="btn btn-gold" href="{esc(a["link"])}" target="_blank" rel="nofollow sponsored noopener">Get the {esc(a["brand"])} offer →</a></p>
</article>
<aside class="post-sidebar">
  <div class="card promo-card">
    <span class="eyebrow">More offers</span>
    <div class="video-mini-list">{more}</div>
  </div>
</aside>
</div>'''
    title, desc = f'{t} — {esc(a["brand"])} offer | Dealux', esc(a['desc'][:160])
    return [title, desc, head, main] if parts else bv.page_shell(title, desc, url, head, main)


def card(a):
    return (f'<div class="card"><a href="{esc(a["link"])}" target="_blank" rel="nofollow sponsored noopener">{img_tag(a)}</a>'
            f'<span class="eyebrow">{esc(a["brand"])}</span><h3><a href="/ads/{a["slug"]}/">{esc(a["name"])}</a></h3>'
            f'<div class="product-actions"><a class="btn btn-ghost" href="/ads/{a["slug"]}/">Details</a>'
            f'<a class="btn btn-gold" href="{esc(a["link"])}" target="_blank" rel="nofollow sponsored noopener">Get offer →</a></div></div>')


def page_url(n):
    return '/ads/' if n == 1 else f'/ads/page/{n}/'


def bootstrap():
    """Recover the ad list from already-built pages (imports made before data/ads.json existed)."""
    ads = []
    for f in sorted(glob.glob('ads/*/index.html')):
        s = open(f, encoding='utf-8').read()
        ld = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', s).group(1))
        m = re.search(r'display-ad/(\d+)-(\d+)', ld['contentUrl'])
        im = re.search(r'<a href="([^"]+)"[^>]*><img [^>]*alt="([^"]*)"(?: width="(\d*)" height="(\d*)")?', s)
        deal = re.search(r'<b>Current deal:</b> (.*?)</p>', s)
        ads.append(dict(slug=f.split('/')[1], pid=m.group(1), adid=m.group(2), name=ld['name'], desc=ld['description'],
                        brand=html.unescape(re.search(r'<span class="eyebrow">(.*?) · Offer</span>', s).group(1)),
                        deal=html.unescape(deal.group(1)) if deal else '', alt=html.unescape(im.group(2)),
                        link=html.unescape(im.group(1)), w=im.group(3) or '', h=im.group(4) or '', date=ld['uploadDate'], static=True))
    return ads


def from_csv(path):
    out = []
    for r in csv.DictReader(open(path, encoding='utf-8-sig')):
        if r['AdType'] != 'IMAGE' or r['State'] != 'ACTIVE' or not (r['TrackingLink'].strip() or r['LandingPage'].strip()):
            continue
        if r['LimitedTimeEndDate'].strip() and r['LimitedTimeEndDate'][:10] < TODAY:
            continue
        w, h = r['ThirdPartyServableAdCreativeWidth'].strip(), r['ThirdPartyServableAdCreativeHeight'].strip()
        if r['Language'].strip().upper() not in LANGS or (w and h and (int(w) < 100 or int(h) < 50)):
            continue
        brand = bv.brand_of(r)
        name = re.sub(r'\s+', ' ', r['Name']).strip() or f'{brand} offer'
        desc = re.sub(r'\s+', ' ', r['Description']).strip() or f"“{name}” — a current offer from {brand}. Tap through for {brand}’s latest deal."
        out.append(dict(slug=f"{bv.slugify(name)[:70].strip('-')}-{r['AdId']}", adid=r['AdId'], pid=r['ProgramId'], name=name,
                        brand=brand, desc=desc, deal=bv.deal_of(r), alt=r['ImageAlternativeTag'].strip() or name,
                        link=r['TrackingLink'].strip() or r['LandingPage'].strip(), w=w, h=h, date=TODAY,
                        ends=r['LimitedTimeEndDate'][:10].strip(), labels=[l.strip() for l in r['Labels'].split(',') if l.strip()]))
    return out


def main(paths):
    ads = json.load(open(MANIFEST, encoding='utf-8')) if os.path.exists(MANIFEST) else bootstrap()
    ads = [a for a in ads if not (a.get('ends') and a['ends'] < TODAY)]
    seen = {a['adid'] for a in ads}
    for p in paths:
        for a in from_csv(p):
            if a['adid'] not in seen:
                seen.add(a['adid'])
                ads.append(a)
    json.dump(ads, open(MANIFEST, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))

    by_pid = {}
    for a in ads:
        by_pid.setdefault(a['pid'], []).append(a)
    shards = [{} for _ in range(SHARDS)]
    for a in ads:
        same = [x for x in by_pid[a['pid']] if x is not a][:6]
        k = int(a['adid']) % max(1, len(ads))
        others = [x for x in ads[k:k + 16] + ads[:8] if x['pid'] != a['pid']]
        related = same + others[:8 - len(same)]
        if a.get('static'):
            os.makedirs(f"ads/{a['slug']}", exist_ok=True)
            open(f"ads/{a['slug']}/index.html", 'w', encoding='utf-8').write(ad_page(a, related))
        else:
            shutil.rmtree(f"ads/{a['slug']}", ignore_errors=True)
            shards[int(a['adid']) % SHARDS][a['slug']] = ad_page(a, related, parts=True)
    shutil.rmtree('data/ad-pages', ignore_errors=True)
    os.makedirs('data/ad-pages')
    for n, sh in enumerate(shards):
        json.dump(sh, open(f'data/ad-pages/{n}.json', 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    # Shared page chrome for edge-rendered ad pages; {{...}} slots are filled per ad.
    open('data/ad-pages/shell.html', 'w', encoding='utf-8').write(
        bv.page_shell('{{title}}', '{{desc}}', '{{canonical}}', '{{head}}', '{{main}}'))

    pages = [ads[i:i + PER_PAGE] for i in range(0, len(ads), PER_PAGE)]
    shutil.rmtree('ads/page', ignore_errors=True)
    for n, chunk in enumerate(pages, 1):
        lst = {'@context': 'https://schema.org', '@type': 'ItemList', 'itemListElement': [
            {'@type': 'ListItem', 'position': (n - 1) * PER_PAGE + i + 1, 'url': f"{SITE}/ads/{a['slug']}/"} for i, a in enumerate(chunk)]}
        rel = [ROBOTS] + ([f'<link rel="prev" href="{SITE}{page_url(n - 1)}">'] if n > 1 else []) + \
              ([f'<link rel="next" href="{SITE}{page_url(n + 1)}">'] if n < len(pages) else [])
        nav = ' '.join(f'<b>{i}</b>' if i == n else f'<a href="{page_url(i)}">{i}</a>' for i in range(1, len(pages) + 1))
        suffix = f' — page {n}' if n > 1 else ''
        os.makedirs(f'.{page_url(n)}', exist_ok=True)
        open(f'.{page_url(n)}index.html', 'w', encoding='utf-8').write(bv.page_shell(
            f'Featured offers from partner brands{suffix} | Dealux',
            f'Browse {len(ads):,} current offers from {len(by_pid):,} brands, each with a direct link to the deal{suffix}.',
            f'{SITE}{page_url(n)}', '\n'.join(rel + [ld_script(lst)]),
            f'<section class="hero"><h1>Featured <span class="gold">offers</span></h1><p class="muted">{len(ads):,} offers from {len(by_pid):,} brands{suffix}.</p></section>\n'
            '<div class="grid">' + ''.join(card(a) for a in chunk) + '</div>\n'
            f'<nav class="pagination" aria-label="Offer pages" style="margin:2rem 0;line-height:2;word-spacing:.4rem">{nav}</nav>'))

    feat = bv.featured(ads)
    block = (f'<!-- image-ads:start -->\n<section class="video-block" aria-label="Featured offers">\n'
             f'<h2>Featured offers <a class="see-all" href="/ads/">All {len(ads):,} offers →</a></h2>\n'
             '<div class="grid">' + ''.join(card(a) for a in feat) + '</div>\n</section>\n<!-- image-ads:end -->\n')
    home = open('index.html', encoding='utf-8').read()
    if '<!-- image-ads:start -->' in home:
        home = re.sub(r'<!-- image-ads:start -->.*?<!-- image-ads:end -->\n', lambda _: block, home, count=1, flags=re.S)
    else:
        home = home.replace('<!-- videos:end -->\n', '<!-- videos:end -->\n' + block, 1)
    open('index.html', 'w', encoding='utf-8').write(home)

    x = lambda s: html.escape(s, quote=False)
    sm = ['<?xml version="1.0" encoding="UTF-8"?>',
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">']
    sm += [f'  <url><loc>{SITE}{page_url(n)}</loc><lastmod>{TODAY}</lastmod></url>' for n in range(1, len(pages) + 1)]
    sm += [f'  <url><loc>{SITE}/ads/{a["slug"]}/</loc><lastmod>{a["date"]}</lastmod><image:image><image:loc>{x(SITE + img_path(a))}</image:loc></image:image></url>' for a in ads]
    open('sitemap-ads.xml', 'w', encoding='utf-8').write('\n'.join(sm + ['</urlset>\n']))
    si = open('sitemap-index.xml', encoding='utf-8').read()
    if 'sitemap-ads.xml' not in si:
        si = si.replace('</sitemapindex>', f'  <sitemap><loc>{SITE}/sitemap-ads.xml</loc><lastmod>{TODAY}</lastmod></sitemap>\n</sitemapindex>', 1)
    else:
        si = re.sub(r'(sitemap-ads\.xml</loc><lastmod>)[^<]*', rf'\g<1>{TODAY}', si)
    open('sitemap-index.xml', 'w', encoding='utf-8').write(si)
    print(f'{len(ads)} ad pages on {len(pages)} directory pages; homepage features {len(feat)}')


if __name__ == '__main__':
    main(sys.argv[1:])
