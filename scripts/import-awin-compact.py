#!/usr/bin/env python3
"""Publish an Awin "compact" product feed (merchant embedded in the product name).

Usage: python3 scripts/import-awin-compact.py dealux-products-named.csv
       python3 scripts/update-counts.py

The feed carries only aw_deep_link, product_name, description, search_price and
currency. The merchant name is prefixed to the product name as
"<merchant> — <product>", so it is split back out and used as the brand, and the
AWIN merchant id and product id are read from the click link. Departments and
types are inferred from the product name with merchant fallbacks, and the rows
are published through import-awin-export.py (Netlify Database migration, static
shards, brand/department/type lists, brand pages and sitemaps).
"""
import csv
import glob
import importlib.util
import json
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
df = _load('import-awin-datafeed')

SEP = ' — '
AFFILIATE = re.compile(r'\s*Affiliate Program\b', re.I)
REGION = re.compile(r'\s*\(?(?:US|UK|GB|EU|CA|AU|IE|NZ)\)?\s*$', re.I)

# (pattern, Awin category) searched in the product name; first match wins.
NAME_RULES = [
    (r'\bsuit\b|tuxedo|\btux\b|blazer|waistcoat|\bvest\b|three ?piece', "Men's Suits"),
    (r'bow ?tie|neck ?tie|\btie\b|cravat', 'Accessories'),
    (r'\bshirt\b|polo\b|t-shirt|tshirt', "Men's Tops"),
    (r'\btrouser|dress pant|slack|\bjeans\b|chino', "Men's Trousers"),
    (r'\bcoat\b|jacket|parka|overcoat|raincoat', "Men's Outerwear"),
    (r'\bdress\b|gown|frock', "Women's Dresses & Skirts"),
    (r'costume|gangster|mobster|flapper|1920|zoot', 'Fancy Dress'),
    (r'stiletto|block heel|\bheel|pump\b|loafer|sneaker|\bboot|shoe', 'Shoes'),
    (r'handbag|\bbag\b|wallet|purse|tote|clutch|backpack', 'Bags'),
    (r'\bhat\b|fedora|\bcap\b|beanie|headband', 'Accessories'),
    (r'\bwatch\b|sunglass|bracelet|necklace|earring|\bring\b', 'Accessories'),
]
NAME_RULES = [(re.compile(p, re.I), c) for p, c in NAME_RULES]

# Merchant fallbacks for rows the product-name rules do not catch.
MERCHANT_RULES = [
    ('alberto nardoni', "Men's Suits"),
    ('emensuits', "Men's Suits"),
    ('alphabiolabs', 'Health'),
    ('ecosusi', 'Bags'),
    ('aliexpress', 'Gadgets'),
]


def clean_merchant(name):
    name = REGION.sub('', AFFILIATE.sub('', name))
    return re.sub(r'\s+', ' ', name).strip() or name


def resolve_brand(merchant_name, merchant_id, shop_slugs, merchant_brands):
    cleaned = clean_merchant(merchant_name)
    slug = cj.slugify(cleaned)
    if slug in shop_slugs:
        return cleaned, slug
    if merchant_id in merchant_brands:
        name, brand_slug = merchant_brands[merchant_id]
        if brand_slug in shop_slugs:
            return name, brand_slug
    return cleaned, slug


def resolve_category(product, merchant):
    for pattern, category in NAME_RULES:
        if pattern.search(product):
            return category
    for pattern, category in df.RULES:
        if pattern.search(product):
            return category
    key = merchant.casefold()
    for needle, category in MERCHANT_RULES:
        if needle in key:
            return category
    for needle, category in df.MERCHANTS:
        if needle in key:
            return category
    return df.DEFAULT_CATEGORY


def build_merchant_brands():
    """The most common catalogue brand for each AWIN merchant id."""
    counts = {}
    for path in glob.glob('data/awin/*.json') + glob.glob('data/img/*.json'):
        for _, record in json.load(open(path, encoding='utf-8')).items():
            if len(record) < 6:
                continue
            query = parse_qs(urlparse(record[5] or '').query)
            merchant = (query.get('m') or [''])[0]
            if merchant and record[3]:
                brands = counts.setdefault(merchant, {})
                brands[record[3]] = brands.get(record[3], 0) + 1
    return {merchant: (name, cj.slugify(name)) for merchant, brands in counts.items()
            for name in [max(brands, key=brands.get)]}


def read_feed(path, known, shop_slugs, merchant_brands):
    items = {}
    with df.open_feed(Path(path)) as stream:
        for row in csv.DictReader(stream):
            if None in row or None in row.values():
                raise ValueError('Malformed feed row')
            if SEP not in row['product_name']:
                raise ValueError(f'Product name has no merchant prefix: {row["product_name"]!r}')
            merchant_name, name = (cj.clean_text(part) for part in row['product_name'].split(SEP, 1))
            url = urlparse(row['aw_deep_link'])
            query = parse_qs(url.query)
            merchant, product = (query.get('m') or [''])[0], (query.get('p') or [''])[0]
            if (not re.fullmatch(r'\d+-\d+', f'{merchant}-{product}') or url.scheme != 'https'
                    or url.netloc != 'www.awin1.com' or not query.get('a')):
                raise ValueError(f'Invalid affiliate link for product {product}')
            if not re.fullmatch(r'\d+(?:\.\d+)?', row['search_price']) or not re.fullmatch('[A-Z]{3}', row['currency']):
                raise ValueError(f'Invalid price or currency for product {product}')
            if not name:
                raise ValueError(f'Empty product name for product {product}')

            brand, brand_slug = resolve_brand(merchant_name, merchant, shop_slugs, merchant_brands)
            category = resolve_category(name, merchant_name)
            dept, kind = awin.CATEGORY[category]
            slug = known.get((merchant, product)) or f'awin-{brand_slug}-{cj.slugify(name)[:90].strip("-")}-{merchant}-{product}'
            description = cj.clean_text(row['description'])
            raw = {
                'product_name': name, 'search_price': row['search_price'], 'currency': row['currency'],
                'merchant_name': brand, 'category_name': category,
                'aw_deep_link': row['aw_deep_link'], 'description': description[:500],
            }
            details = {'merchant': brand, 'category': category, 'type_slug': kind, 'brand_slug': brand_slug}
            record = [name, row['search_price'], row['currency'], brand, '', row['aw_deep_link'], description, details]
            if slug in items:
                raise ValueError(f'Duplicate feed row for product {product}')
            items[slug] = (slug, raw, record, dept, kind)
    if not items:
        raise ValueError('The feed contained no products')
    return items


if __name__ == '__main__':
    shop_slugs = {entry.name for entry in Path('shop/brand').iterdir() if entry.is_dir()}
    merchant_brands = build_merchant_brands()
    export.read_feed = lambda path, known: read_feed(path, known, shop_slugs, merchant_brands)
    export.main(Path(sys.argv[1]).resolve())
