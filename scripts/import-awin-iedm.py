#!/usr/bin/env python3
"""Publish the iEDM Awin product feed into the shop catalog.

Usage: python3 scripts/import-awin-iedm.py data/feeds/iedm-dealux.csv
       python3 scripts/update-counts.py

The feed carries only aw_deep_link, product_name, description, search_price and
currency. Every row belongs to the iEDM merchant (awinmid=71579), so the brand
is fixed and the product name is kept exactly as supplied (it already ends in
"by iEDM"). Departments and types are inferred from the product name, and the
rows are published through import-awin-export.py (Netlify Database migration,
static shards, brand/department/type lists, brand page and sitemaps).
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

BRAND = 'iEDM'
BRAND_SLUG = 'iedm'
DEFAULT_CATEGORY = 'General Clothing'

# (pattern, Awin category) searched in the product name; first match wins.
NAME_RULES = [
    (r'\bdress\b|gown', "Women's Dresses & Skirts"),
    (r'hoodie|hooded|sweatshirt|sweater|pullover|zip[- ]?up|crewneck', "Men's Outerwear"),
    (r't-?shirt|\btee\b|\btank\b|\bshirt\b|polo|\btop\b', "Men's Tops"),
    (r'\bshort|jogger|legging|\bpants?\b|trouser|sweatpants', "Men's Trousers"),
    (r'\bhat\b|beanie|\bcap\b|headband|bucket hat', 'Accessories'),
    (r'tote|\bbag\b|backpack|pouch', 'Bags'),
]
NAME_RULES = [(re.compile(p, re.I), c) for p, c in NAME_RULES]


def resolve_category(name):
    for pattern, category in NAME_RULES:
        if pattern.search(name):
            return category
    return DEFAULT_CATEGORY


def read_feed(path, known):
    items = {}
    with Path(path).open(encoding='utf-8-sig', newline='') as stream:
        for row in csv.DictReader(stream):
            if None in row or None in row.values():
                raise ValueError('Malformed feed row')
            url = urlparse(row['aw_deep_link'])
            query = parse_qs(url.query)
            merchant, product = (query.get('m') or [''])[0], (query.get('p') or [''])[0]
            if (not re.fullmatch(r'\d+-\d+', f'{merchant}-{product}') or url.scheme != 'https'
                    or url.netloc != 'www.awin1.com' or not query.get('a')):
                raise ValueError(f'Invalid affiliate link for product {product}')
            if not re.fullmatch(r'\d+(?:\.\d+)?', row['search_price']) or not re.fullmatch('[A-Z]{3}', row['currency']):
                raise ValueError(f'Invalid price or currency for product {product}')
            name = cj.clean_text(row['product_name'])
            if not name:
                raise ValueError(f'Empty product name for product {product}')

            category = resolve_category(name)
            dept, kind = awin.CATEGORY[category]
            base = re.sub(r'\s+by\s+iEDM$', '', name, flags=re.I)
            slug = known.get((merchant, product)) or f'awin-{BRAND_SLUG}-{cj.slugify(base)[:90].strip("-")}-{merchant}-{product}'
            description = cj.clean_text(row['description'])
            raw = {
                'product_name': name, 'search_price': row['search_price'], 'currency': row['currency'],
                'merchant_name': BRAND, 'category_name': category,
                'aw_deep_link': row['aw_deep_link'], 'description': description[:500],
            }
            details = {'merchant': BRAND, 'category': category, 'type_slug': kind, 'brand_slug': BRAND_SLUG}
            record = [name, row['search_price'], row['currency'], BRAND, '', row['aw_deep_link'], description, details]
            if slug in items:
                raise ValueError(f'Duplicate feed row for product {product}')
            items[slug] = (slug, raw, record, dept, kind)
    if not items:
        raise ValueError('The feed contained no products')
    return items


if __name__ == '__main__':
    export.read_feed = read_feed
    export.main(Path(sys.argv[1]).resolve())
