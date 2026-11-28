#!/usr/bin/env python3
"""Move the hand-picked Amazon pins out of the Amazon brand into their own
"Amazon Exclusives" shop section.

Usage: python3 scripts/add-amazon-exclusives.py
       python3 scripts/update-counts.py

The curated items are the Amazon affiliate products in the Amazon brand whose
links are not Partnerize click URLs (the ones imported from the SMlux673821
"Amazon Finds" Pinterest board). They keep their affiliate URLs verbatim and are
re-filed under a new /shop/brand/amazon-exclusives/ page; the Amazon brand keeps
only the Partnerize best-sellers. The left-hand "Shop by brand" directory entry
is renamed to match. Re-running is a no-op.
"""
import glob
import html
import json
import os
import re
import unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

SITE = 'https://dealuxapp.com'
DATE = '2026-11-28'
BRAND = 'Amazon Exclusives'
SLUG = 'amazon-exclusives'
TEMPLATE = 'shop/brand/amazon-renewed/index.html'
SHARDS = 64
OLD_ANCHOR = '<a class="side-link sub " href="/shop/brand/amazon/">Amazon <span class="muted">25</span></a>'


def slugify(s):
    s = unicodedata.normalize('NFKD', s or '').encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+', '-', s).strip('-')


def read(path, default):
    return json.loads(open(path, encoding='utf-8').read()) if os.path.exists(path) else default


def write(path, data):
    open(path, 'w', encoding='utf-8').write(json.dumps(data, ensure_ascii=False, separators=(',', ':')))


def curated_slugs(amazon):
    """Amazon-brand slugs whose link is not a Partnerize click URL."""
    shards = {n: read(f'data/img/{n}.json', {}) for n in range(SHARDS)}
    out = []
    for s in amazon:
        record = next((d[s] for d in shards.values() if s in d), None)
        if record and len(record) > 5 and 'prf.hn' not in str(record[5]):
            out.append(s)
    return shards, out


def main():
    amazon = read('data/list/brand-amazon.json', [])
    shards, curated = curated_slugs(amazon)
    if not curated:
        raise SystemExit('No curated Amazon items found to move.')

    # Re-file each curated record under the new brand, keeping data intact.
    for n, data in shards.items():
        for s in curated:
            if s not in data:
                continue
            record = data[s]
            record[3] = BRAND
            if len(record) > 7 and isinstance(record[7], dict):
                record[7]['brand_slug'] = SLUG
                record[7]['merchant'] = 'Amazon'
    for n, data in shards.items():
        write(f'data/img/{n}.json', data)

    write('data/list/brand-amazon-exclusives.json', curated)
    write('data/list/brand-amazon.json', [s for s in amazon if s not in set(curated)])
    n = len(curated)

    # ---- brand landing page, cloned from an existing static brand page ----
    page = open(TEMPLATE, encoding='utf-8').read()
    page = page.replace('shop/brand/amazon-renewed/', f'shop/brand/{SLUG}/')
    page = page.replace('brand-amazon-renewed.json', f'brand-{SLUG}.json')
    page = page.replace('Amazon Renewed', BRAND)
    page = page.replace('Shop 2 ' + BRAND + ' products on Amazon.',
                        f'Shop {n} Amazon Exclusives products, hand-picked by Dealux.')
    page = re.sub(r'<p class="muted">2 products</p>', f'<p class="muted">{n} products</p>', page)
    os.makedirs(f'shop/brand/{SLUG}', exist_ok=True)
    open(f'shop/brand/{SLUG}/index.html', 'w', encoding='utf-8').write(page)

    # ---- rename the left-hand "Shop by brand" entry on every shop page ----
    new_anchor = (f'<a class="side-link sub " href="/shop/brand/{SLUG}/">{BRAND} '
                  f'<span class="muted">{n}</span></a>')
    for path in glob.glob('shop/**/index.html', recursive=True):
        text = open(path, encoding='utf-8').read()
        if OLD_ANCHOR in text:
            open(path, 'w', encoding='utf-8').write(text.replace(OLD_ANCHOR, new_anchor))

    # ---- brand affiliate link + directory entry ----
    link = next((shards[k][s][5] for k in shards for s in curated if s in shards[k]), '')
    for path in ('data/brands.json', 'brands.json'):
        brands = read(path, [])
        if not any(b[0] == BRAND for b in brands):
            brands.append([BRAND, link])
            brands.sort(key=lambda b: b[0].casefold())
            write(path, brands)

    # ---- sitemap ----
    sm = open('sitemap-shop.xml', encoding='utf-8').read()
    url = f'{SITE}/shop/brand/{SLUG}/'
    if f'<loc>{url}</loc>' not in sm:
        sm = sm.replace('</urlset>', f'  <url><loc>{url}</loc><lastmod>{DATE}</lastmod></url>\n</urlset>')
        open('sitemap-shop.xml', 'w', encoding='utf-8').write(sm)

    print(f'{n} curated items moved to /shop/brand/{SLUG}/; Amazon brand now '
          f'{len(amazon) - n:,} Partnerize items')


if __name__ == '__main__':
    main()
