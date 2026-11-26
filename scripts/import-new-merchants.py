#!/usr/bin/env python3
"""Import the simplified "new merchants" product feed into the shop.

Usage: python3 scripts/import-new-merchants.py data/feeds/dealux-new-merchants.csv
       python3 scripts/update-counts.py

The feed carries only name, brand, description, price and affiliate_url (an AWIN
click link). The merchant id and product id are read from the click link, prices
are treated as USD, and each merchant is filed under a department/type chosen
from its catalogue (TrophyCentral -> Gifts, BRND COLLECTION -> Fragrance,
PawFurEver -> Pets). Rows are published through import-awin-export.py, so they
land in the Netlify Database migration, the static product shards, the
brand/department/type lists, the brand directory and the sitemaps.
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

# Merchant brand -> Awin category key already mapped to a department/type.
BRAND_CATEGORY = {
    'trophycentral': 'Gifts',
    'brnd collection': 'Fragrance',
    'pawfurever': 'Pets',
}
DEFAULT_CURRENCY = 'USD'


def read_feed(path, known):
    items = {}
    with open(path, encoding='utf-8-sig', newline='') as stream:
        for row in csv.DictReader(stream):
            if None in row or None in row.values():
                raise ValueError('Malformed feed row')
            name = cj.clean_text(row['name'])
            brand = cj.clean_text(row['brand'])
            description = cj.clean_text(row['description'])
            price = (row['price'] or '').strip()
            currency = (row.get('currency') or DEFAULT_CURRENCY).strip() or DEFAULT_CURRENCY
            link = (row['affiliate_url'] or '').strip()
            if not name or not brand:
                raise ValueError(f'Row is missing a name or brand: {row!r}')
            url = urlparse(link)
            query = parse_qs(url.query)
            merchant, product = (query.get('m') or [''])[0], (query.get('p') or [''])[0]
            if (not re.fullmatch(r'\d+-\d+', f'{merchant}-{product}') or url.scheme != 'https'
                    or url.netloc != 'www.awin1.com' or not query.get('a')):
                raise ValueError(f'Invalid affiliate link for product {product!r}')
            if not re.fullmatch(r'\d+(?:\.\d+)?', price) or not re.fullmatch('[A-Z]{3}', currency):
                raise ValueError(f'Invalid price or currency for product {product!r}')
            category = BRAND_CATEGORY.get(brand.casefold())
            if not category:
                raise ValueError(f'No category mapped for brand {brand!r}')
            dept, kind = awin.CATEGORY[category]
            brand_slug = cj.slugify(brand)
            slug = known.get((merchant, product)) or f'awin-{brand_slug}-{cj.slugify(name)[:90].strip("-")}-{merchant}-{product}'
            if slug in items:
                continue
            raw = {
                'product_name': name, 'search_price': price, 'currency': currency,
                'merchant_name': brand, 'category_name': category,
                'aw_deep_link': link, 'description': description[:500],
            }
            details = {'merchant': brand, 'category': category, 'type_slug': kind, 'brand_slug': brand_slug}
            record = [name, price, currency, brand, '', link, description, details]
            items[slug] = (slug, raw, record, dept, kind)
    if not items:
        raise ValueError('The feed contained no products')
    return items


if __name__ == '__main__':
    export.read_feed = read_feed
    export.main(Path(sys.argv[1]).resolve())
