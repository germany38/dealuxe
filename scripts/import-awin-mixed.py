#!/usr/bin/env python3
"""Publish a curated multi-brand Awin feed (name/brand/price shape) into the shop.

Usage: python3 scripts/import-awin-mixed.py data/feeds/dealux-mixed-batch-02.csv
       python3 scripts/update-counts.py

The feed carries name, brand, description, price and affiliate_url. Each row is
filed under its brand (reusing an existing brand page when one is already known)
and a department/type resolved with the same rules used for the other curated
feeds. Prices are assumed to be USD, as the feed ships no currency column. Rows
are published through import-awin-export.py (Netlify Database migration, static
shards, brand/department/type lists, brand pages and sitemaps).
"""
import csv
import importlib.util
import re
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse


def _load(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(f'{name}.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


export = _load('import-awin-export')
awin, cj = export.awin, export.cj
compact = _load('import-awin-compact')
curated = _load('import-awin-curated')

CURRENCY = 'USD'


def read_feed(path, known, shop_slugs, merchant_brands):
    items = {}
    with Path(path).open(encoding='utf-8-sig', newline='') as stream:
        for row in csv.DictReader(stream):
            if None in row or None in row.values():
                raise ValueError('Malformed feed row')
            url = urlparse(row['affiliate_url'])
            query = parse_qs(url.query)
            merchant, product = (query.get('m') or [''])[0], (query.get('p') or [''])[0]
            if (not re.fullmatch(r'\d+-\d+', f'{merchant}-{product}') or url.scheme != 'https'
                    or url.netloc != 'www.awin1.com' or not query.get('a')):
                raise ValueError(f'Invalid affiliate link for product {product}')
            price = (row['price'] or '').strip()
            if not re.fullmatch(r'\d+(?:\.\d+)?', price):
                raise ValueError(f'Invalid price for product {product}')
            merchant_name = row['brand']
            name = cj.clean_text(row['name'])
            if not name:
                raise ValueError(f'Empty product name for product {product}')

            brand, brand_slug = compact.resolve_brand(merchant_name, merchant, shop_slugs, merchant_brands)
            category = curated.resolve_category(merchant, name, merchant_name)
            dept, kind = awin.CATEGORY[category]
            if 'esim' in merchant_name.casefold():
                dept, kind = 'travel', 'travel-esims'
            slug = known.get((merchant, product)) or f'awin-{brand_slug}-{cj.slugify(name)[:90].strip("-")}-{merchant}-{product}'
            description = cj.clean_text(row['description'])
            raw = {
                'product_name': name, 'search_price': price, 'currency': CURRENCY,
                'merchant_name': brand, 'category_name': category,
                'aw_deep_link': row['affiliate_url'], 'description': description[:500],
            }
            details = {'merchant': brand, 'category': category, 'type_slug': kind, 'brand_slug': brand_slug}
            record = [name, price, CURRENCY, brand, '', row['affiliate_url'], description, details]
            if slug in items:
                raise ValueError(f'Duplicate feed row for product {product}')
            items[slug] = (slug, raw, record, dept, kind)
    if not items:
        raise ValueError('The feed contained no products')
    return items


if __name__ == '__main__':
    shop_slugs = {entry.name for entry in Path('shop/brand').iterdir() if entry.is_dir()}
    merchant_brands = compact.build_merchant_brands()
    export.read_feed = lambda path, known: read_feed(path, known, shop_slugs, merchant_brands)
    export.main(Path(sys.argv[1]).resolve())
