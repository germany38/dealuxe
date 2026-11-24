#!/usr/bin/env python3
"""Publish a small Awin export without rewriting the legacy product catalog."""

import collections
import csv
import datetime
import hashlib
import html
import importlib.util
import json
import re
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse

feed_path = Path(sys.argv[1]).resolve() if __name__ == '__main__' else None
spec = importlib.util.spec_from_file_location('awin', Path(__file__).with_name('import-awin.py'))
awin = importlib.util.module_from_spec(spec)
spec.loader.exec_module(awin)
cj = awin.cj

OUT = Path('data/awin')
SQL = Path('netlify/database/migrations')
FIELDS = ('merchant_category', 'product_type', 'colour', 'condition', 'stock_status',
          'delivery_cost', 'rrp_price', 'ean', 'mpn', 'merchant_product_category_path')


def write(path, content):
    if not path.exists() or path.read_text(encoding='utf-8') != content:
        path.write_text(content, encoding='utf-8')


def read_slugs(path):
    return path.read_text().splitlines() if path.exists() else []


def sitemap(path, urls):
    write(path, '<?xml version="1.0" encoding="UTF-8"?>\n'
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
          + ''.join(f'<url><loc>{cj.SITE}{url}</loc></url>\n' for url in urls) + '</urlset>\n')


def write_migration(items):
    fingerprint = hashlib.sha256(json.dumps(items, sort_keys=True).encode()).hexdigest()[:12]
    if list(SQL.glob(f'*_awin_export_{fingerprint}.sql')):
        return
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d%H%M%S')
    header = '''ALTER TABLE awin_catalog_products ADD COLUMN IF NOT EXISTS source_data JSONB;
CREATE INDEX IF NOT EXISTS awin_catalog_brand_slug_idx ON awin_catalog_products (brand, slug);
CREATE INDEX IF NOT EXISTS awin_catalog_type_slug_idx ON awin_catalog_products (product_type, slug);
'''
    with (SQL / f'{stamp}_awin_export_{fingerprint}.sql').open('x', encoding='utf-8') as stream:
        stream.write(header)
        fields = 'ARRAY[' + ','.join(map(awin.sql, items[0][1])) + ']'
        for start in range(0, len(items), 500):
            values = []
            for slug, raw, record, dept, kind in items[start:start + 500]:
                payload = json.dumps(list(raw.values()), ensure_ascii=False, separators=(',', ':'))
                values.append('(' + ','.join(map(awin.sql, (slug, record[3], dept, kind, record[4], payload))) + ')')
            stream.write('''INSERT INTO awin_catalog_products
  (slug, name, price, currency, brand, merchant, category, department, product_type, image_url, affiliate_url, description, source_data)
SELECT slug, data->>'product_name', (data->>'search_price')::numeric, data->>'currency', brand,
  data->>'merchant_name', data->>'category_name', department, product_type, image_url,
  data->>'aw_deep_link', data->>'description', data
FROM (SELECT slug, brand, department, product_type, image_url,
  to_jsonb(jsonb_object(''' + fields + ''', ARRAY(SELECT jsonb_array_elements_text(payload::jsonb)))) AS data FROM (VALUES\n''')
            stream.write(',\n'.join(values))
            stream.write('''
) AS src(slug, brand, department, product_type, image_url, payload)) AS parsed
ON CONFLICT (slug) DO UPDATE SET name=EXCLUDED.name, price=EXCLUDED.price, currency=EXCLUDED.currency,
  brand=EXCLUDED.brand, merchant=EXCLUDED.merchant, category=EXCLUDED.category, department=EXCLUDED.department,
  product_type=EXCLUDED.product_type, image_url=EXCLUDED.image_url, affiliate_url=EXCLUDED.affiliate_url,
  description=EXCLUDED.description, source_data=EXCLUDED.source_data;
''')


def read_feed(path, known):
    items = {}
    with path.open(encoding='utf-8-sig', newline='') as stream:
        for row in csv.DictReader(stream):
            if len(items) >= 25000:
                raise ValueError('This importer is for batches below 25,001 products; see the catalog operations guide.')
            merchant, product = row['merchant_id'], row['aw_product_id']
            url = urlparse(row['aw_deep_link'])
            query = parse_qs(url.query)
            if (not re.fullmatch(r'\d+-\d+', f'{merchant}-{product}') or url.scheme != 'https'
                    or url.netloc != 'www.awin1.com' or query.get('m') != [merchant]
                    or query.get('p') != [product] or not query.get('a') or None in row or None in row.values()):
                raise ValueError(f'Invalid affiliate link for product {product}')
            if not re.fullmatch(r'\d+(?:\.\d+)?', row['search_price']) or not re.fullmatch('[A-Z]{3}', row['currency']):
                raise ValueError(f'Invalid price or currency for product {product}')
            brand = cj.clean_text(row['brand_name']) or cj.clean_text(row['merchant_name'])
            name = cj.clean_text(row['product_name'])
            slug = known.get((merchant, product)) or f'awin-{cj.slugify(brand)}-{cj.slugify(name)[:90].strip("-")}-{merchant}-{product}'
            category = row['category_name']
            dept, kind = ('services', 'finance-insurance') if category in ('Insurance', 'Life Insurance') else awin.CATEGORY[category]
            if 'esim' in row['merchant_name'].casefold():
                dept, kind = 'travel', 'travel-esims'
            image = next((row[key] for key in ('merchant_image_url', 'aw_image_url', 'large_image')
                          if urlparse(row[key]).scheme == 'https'), '')
            details = {key: row[key] for key in FIELDS if row.get(key)}
            details.update(merchant=row['merchant_name'], category=category, type_slug=kind, brand_slug=cj.slugify(brand))
            record = [name, row['search_price'], row['currency'], brand, image, row['aw_deep_link'], cj.clean_text(row['description']), details]
            if slug in items:
                raise ValueError(f'Duplicate feed row for product {product}')
            items[slug] = (slug, row, record, dept, kind)
    if not items:
        raise ValueError('The feed contained no products')
    return items


def publish_groups(items):
    groups = collections.defaultdict(list)
    brands = {}
    for slug, _, record, dept, kind in items.values():
        brand = record[7]['brand_slug']
        brands[brand] = (record[3], record[5])
        for group in (f'brand-{brand}', f'dept-{dept}', f'type-{kind}'):
            groups[group].append(slug)
    list_dir = Path('data/list')
    affected = set(groups)
    for path in list_dir.glob('*.json'):
        if not path.name.startswith(('brand-', 'dept-', 'type-')):
            continue
        current = cj.read_json(path, [])
        added = groups.get(path.stem, [])
        new = added + [slug for slug in current if slug not in items]
        if new != current:
            cj.write_json(path, new)
            affected.add(path.stem)
    for group in groups:
        path = list_dir / f'{group}.json'
        if not path.exists():
            cj.write_json(path, groups[group])

    template = Path('shop/brand/3w/index.html').read_text()
    template = re.sub(r'(<summary><span class="side-link side-heading">Shop by brand</span></summary>).*?(</details>)',
                      r'\1<a class="side-link sub" href="/brands/">Browse all brands</a>\2', template, flags=re.S)
    new_pages = []
    for group in sorted(affected):
        prefix, key = group.split('-', 1)
        section = 'department' if prefix == 'dept' else prefix
        url = f'/shop/{section}/{key}/'
        path = Path(url.strip('/')) / 'index.html'
        count = len(cj.read_json(list_dir / f'{group}.json', []))
        if path.exists():
            text = re.sub(r'<p class="muted">[\d,]+ products?</p>', f'<p class="muted">{count:,} products</p>', path.read_text(), count=1)
            text = re.sub(r'content="Shop [\d,]+ ', f'content="Shop {count:,} ', text, count=1)
            write(path, text)
        elif prefix == 'brand' and key in brands:
            name = html.escape(brands[key][0], quote=True)
            cj.write_page(str(path), cj.page_from(template, url, name, f'Shop {count:,} {name} products and deals.',
                                                  f'Shop {name}', f'{count:,} products', f'/data/list/{group}.json'))
            new_pages.append(url)
        else:
            raise ValueError(f'Missing shop landing page for {group}')

    for path in ('brands.json', 'data/brands.json'):
        current = cj.read_json(path, [])
        known = {cj.slugify(brand[0]) for brand in current}
        current.extend(list(details) for key, details in brands.items() if key not in known)
        cj.write_json(path, sorted(current, key=lambda brand: brand[0].casefold()))
    return new_pages


def main(path):
    legacy = set(read_slugs(Path('data/products.txt')))
    previous = read_slugs(OUT / 'products.txt')
    known = {tuple(slug.rsplit('-', 2)[-2:]): slug for slug in sorted(legacy) + previous if slug.startswith('awin-')}
    items = read_feed(path, known)
    write_migration(sorted(items.values()))
    OUT.mkdir(exist_ok=True)
    buckets = collections.defaultdict(dict)
    for slug, _, record, _, _ in items.values():
        buckets[cj.shard_of(slug)][slug] = record
    for bucket, records in buckets.items():
        dest = OUT / f'{bucket}.json'
        current = cj.read_json(dest, {})
        current.update(records)
        write(dest, '{\n' + ',\n'.join(json.dumps(slug) + ':' + json.dumps(rec, ensure_ascii=False, separators=(',', ':'))
                                       for slug, rec in sorted(current.items())) + '\n}\n')

    listing = list(dict.fromkeys([*items, *previous]))
    write(OUT / 'products.txt', '\n'.join(listing) + '\n')
    new = sorted(items.keys() - legacy - set(previous))
    pages = publish_groups(items)
    index = Path('sitemap-index.xml')
    xml = index.read_text()
    existing_coverage = {loc for path in Path('.').glob('sitemap-*-products-*.xml')
                         for loc in re.findall(r'<loc>https://dealuxapp\.com/shop/([^<]+)</loc>', path.read_text())}
    to_index = sorted(set(items) - existing_coverage)
    for start in range(0, len(to_index), 10000):
        urls = to_index[start:start + 10000]
        tag = hashlib.sha256('\n'.join(urls).encode()).hexdigest()[:12]
        name = f'sitemap-awin-products-export-{tag}.xml'
        sitemap(Path(name), [f'/shop/{slug}' for slug in urls])
        xml = xml.replace('</sitemapindex>', f'  <sitemap><loc>{cj.SITE}/{name}</loc></sitemap>\n</sitemapindex>')
    write(index, xml)
    shop = Path('sitemap-shop.xml')
    xml = shop.read_text()
    write(shop, xml.replace('</urlset>', ''.join(f'<url><loc>{cj.SITE}{url}</loc></url>\n' for url in pages) + '</urlset>'))
    print(f'{len(items):,} feed rows; {len(new):,} new products; {len(pages):,} new brand pages')


if __name__ == '__main__':
    main(feed_path)
