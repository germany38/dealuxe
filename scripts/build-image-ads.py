#!/usr/bin/env python3
"""Build the Dealux image-ad pages from an Impact "Ads" export (image ads only).

Usage: python3 scripts/build-image-ads.py path/to/impact-image-ads.csv

Writes /ads/<slug>/ (one indexable page per banner), /ads/ (index),
/sitemap-ads.xml (image sitemap, added to sitemap-index.xml) and a
"Featured offers" block on the homepage right after the videos block.
Shared helpers come from build-videos.py.
"""
import csv, html, importlib.util, json, os, re, sys

spec = importlib.util.spec_from_file_location('bv', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'build-videos.py'))
bv = importlib.util.module_from_spec(spec); spec.loader.exec_module(bv)
SITE, TODAY, esc, ld_script = bv.SITE, bv.TODAY, bv.esc, bv.ld_script
HOME_COUNT = 12


def img_tag(a, lazy=True):
    dims = f' width="{a["w"]}" height="{a["h"]}"' if a['w'] and a['h'] else ''
    return f'<img src="{esc(a["img"])}" alt="{esc(a["alt"])}"{dims}{" loading=\"lazy\"" if lazy else ""} style="max-width:100%;height:auto">'


def ad_page(a, related):
    t = esc(a['name'])
    img_ld = {'@context': 'https://schema.org', '@type': 'ImageObject', 'name': a['name'], 'description': a['desc'],
              'contentUrl': a['img'], 'url': f"{SITE}/ads/{a['slug']}/", 'uploadDate': a['date'],
              'publisher': {'@type': 'Organization', 'name': 'Dealux', 'url': SITE}}
    crumbs = {'@context': 'https://schema.org', '@type': 'BreadcrumbList', 'itemListElement': [
        {'@type': 'ListItem', 'position': 1, 'name': 'Home', 'item': SITE + '/'},
        {'@type': 'ListItem', 'position': 2, 'name': 'Offers', 'item': SITE + '/ads/'},
        {'@type': 'ListItem', 'position': 3, 'name': a['name'], 'item': f"{SITE}/ads/{a['slug']}/"}]}
    head = '\n'.join([f'<meta property="og:title" content="{t}">', f'<meta property="og:image" content="{esc(a["img"])}">',
                      ld_script(img_ld), ld_script(crumbs)])
    deal = f'<p class="promo-note"><b>Current deal:</b> {esc(a["deal"])}</p>' if a['deal'] else ''
    more = ''.join(f'<a class="card video-mini" href="/ads/{r["slug"]}/">{esc(r["name"])}<span class="muted">{esc(r["brand"])}</span></a>' for r in related)
    main = f'''<div class="post-layout">
<article class="post">
  <a class="muted" href="/ads/">← All offers</a>
  <span class="eyebrow">{esc(a["brand"])} · Offer</span>
  <h1>{t}</h1>
  <p><a href="{esc(a["link"])}" target="_blank" rel="nofollow sponsored noopener">{img_tag(a, lazy=False)}</a></p>
  <p>{esc(a["desc"])}</p>
  {deal}
  <p><a class="btn btn-gold" href="{esc(a["link"])}" target="_blank" rel="nofollow sponsored noopener">Get the {esc(a["brand"])} offer →</a></p>
</article>
<aside class="post-sidebar">
  <div class="card promo-card">
    <span class="eyebrow">More offers</span>
    <div class="video-mini-list">{more}</div>
  </div>
</aside>
</div>'''
    return bv.page_shell(f'{t} — {esc(a["brand"])} offer | Dealux', esc(a['desc'][:160]), f"{SITE}/ads/{a['slug']}/", head, main)


def card(a):
    return (f'<div class="card"><a href="{esc(a["link"])}" target="_blank" rel="nofollow sponsored noopener">{img_tag(a)}</a>'
            f'<span class="eyebrow">{esc(a["brand"])}</span><h3><a href="/ads/{a["slug"]}/">{esc(a["name"])}</a></h3>'
            f'<div class="product-actions"><a class="btn btn-ghost" href="/ads/{a["slug"]}/">Details</a>'
            f'<a class="btn btn-gold" href="{esc(a["link"])}" target="_blank" rel="nofollow sponsored noopener">Get offer →</a></div></div>')


def main(csv_path):
    rows = [r for r in csv.DictReader(open(csv_path, encoding='utf-8-sig'))
            if r['AdType'] == 'IMAGE' and r['State'] == 'ACTIVE' and (r['TrackingLink'].strip() or r['LandingPage'].strip())
            and not (r['LimitedTimeEndDate'].strip() and r['LimitedTimeEndDate'][:10] < TODAY)]
    ads, slugs = [], set()
    for r in rows:
        brand = bv.brand_of(r)
        name = re.sub(r'\s+', ' ', r['Name']).strip() or f'{brand} offer'
        slug = f"{bv.slugify(name)[:70].strip('-')}-{r['AdId']}"
        if slug in slugs:
            continue
        slugs.add(slug)
        desc = re.sub(r'\s+', ' ', r['Description']).strip() or f"“{name}” — a current offer from {brand}. Tap through for {brand}’s latest deal."
        ads.append(dict(slug=slug, adid=r['AdId'], pid=r['ProgramId'], name=name, brand=brand, desc=desc, deal=bv.deal_of(r),
                        img=f"https://a.impactradius-go.com/display-ad/{r['ProgramId']}-{r['AdId']}",
                        alt=r['ImageAlternativeTag'].strip() or name, link=r['TrackingLink'].strip() or r['LandingPage'].strip(),
                        w=r['ThirdPartyServableAdCreativeWidth'], h=r['ThirdPartyServableAdCreativeHeight'], date=TODAY))
    by_pid = {}
    for a in ads:
        by_pid.setdefault(a['pid'], []).append(a)
    for a in ads:
        same = [x for x in by_pid[a['pid']] if x is not a][:6]
        others = [x for x in ads if x['pid'] != a['pid']]
        k = int(a['adid']) % max(1, len(others))
        os.makedirs(f"ads/{a['slug']}", exist_ok=True)
        open(f"ads/{a['slug']}/index.html", 'w', encoding='utf-8').write(ad_page(a, same + others[k:k + 8 - len(same)]))

    lst = {'@context': 'https://schema.org', '@type': 'ItemList', 'itemListElement': [
        {'@type': 'ListItem', 'position': i + 1, 'url': f"{SITE}/ads/{a['slug']}/"} for i, a in enumerate(ads)]}
    open('ads/index.html', 'w', encoding='utf-8').write(bv.page_shell(
        'Featured offers from partner brands | Dealux',
        f'Browse {len(ads):,} current offers from {len(by_pid):,} brands, each with a direct link to the deal.',
        f'{SITE}/ads/', ld_script(lst),
        f'<section class="hero"><h1>Featured <span class="gold">offers</span></h1><p class="muted">{len(ads):,} offers from {len(by_pid):,} brands.</p></section>\n'
        '<div class="grid">' + ''.join(card(a) for a in ads) + '</div>'))

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
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">',
          f'  <url><loc>{SITE}/ads/</loc><lastmod>{TODAY}</lastmod></url>']
    sm += [f'  <url><loc>{SITE}/ads/{a["slug"]}/</loc><lastmod>{a["date"]}</lastmod><image:image><image:loc>{x(a["img"])}</image:loc></image:image></url>' for a in ads]
    open('sitemap-ads.xml', 'w', encoding='utf-8').write('\n'.join(sm + ['</urlset>\n']))
    si = open('sitemap-index.xml', encoding='utf-8').read()
    if 'sitemap-ads.xml' not in si:
        si = si.replace('</sitemapindex>', f'  <sitemap><loc>{SITE}/sitemap-ads.xml</loc><lastmod>{TODAY}</lastmod></sitemap>\n</sitemapindex>', 1)
        open('sitemap-index.xml', 'w', encoding='utf-8').write(si)
    print(f'{len(ads)} ad pages; homepage features {len(feat)}')


if __name__ == '__main__':
    main(sys.argv[1])
