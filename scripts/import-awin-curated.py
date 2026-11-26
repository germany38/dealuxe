#!/usr/bin/env python3
"""Publish a curated multi-brand Awin feed into the shop catalog.

Usage: python3 scripts/import-awin-curated.py data/feeds/dealux-curated-products.csv
       python3 scripts/update-counts.py

The feed carries merchant_name, product_name, description, search_price,
currency, aw_deep_link and aw_product_id, covering many advertisers. Each row is
filed under its merchant's brand (reusing an existing brand page when one is
already known) and a department/type resolved from the product name, with a
small per-merchant fallback for brands whose names carry no category keywords.
Rows are published through import-awin-export.py (Netlify Database migration,
static shards, brand/department/type lists, brand pages and sitemaps).
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

# Awin merchant id -> Awin category, used when the product name has no useful
# category keywords (a brand sells one kind of thing, so this is reliable).
MERCHANT_CATEGORY = {
    '24111': 'Shoes',                      # CHIKO
    '73047': 'Decorations',                # Aperturee photo backdrops
    '102429': "Men's Suits",               # Alberto Nardoni
    '109364': 'General Clothing',          # Printerval printed apparel
    '111020': 'Kitchen',                   # Kuishi glassware
    '114402': 'Video Games',               # Keycense game keys
    '115789': 'General Clothing',          # Mustard Seed apparel
    '67974': 'Car Parts',                  # Dunford wheels
    '57145': 'General Clothing',           # COMENII scrubwear
    '113638': "Women's Jewellery",         # BBBGEM gemstones
    '79904': 'Vitamins & Supplements',     # Herbsdaily
    '84293': 'Car Accessories',            # Nilight lighting
    '95201': 'Gifts',                      # Giftlab personalised gifts
    '91177': "Women's Jewellery",          # Shenzhen Shibao Jewelry
    '74394': 'Car Parts',                  # labworkauto
    '80917': 'Gifts',                      # TrophyCentral awards
    '88509': 'Home Textiles',              # Super Area Rugs
    '105263': 'Gadgets',                   # 2Fdeal vape hardware
    '91941': "Women's Jewellery",          # OUFER body jewellery
    '88751': 'Arts & Crafts',              # PandaHall craft supplies
    '93517': 'Glasses',                    # Lensmart eyewear
    '87175': 'Gifts',                      # Beyond Memories keepsakes
    '87919': 'Flowers',                    # Flowers Fast
    '17940': 'Gifts',                      # Alibaba US marketplace
    '123074': 'Home Textiles',             # hugmoom curtains
    '124966': 'Glasses',                   # Eydology eyewear
    '127361': 'Holidays',                  # Aussui travel gift cards
    '123388': 'Pets',                      # PawFurEver pet tags
    '124284': 'Home Accessories',          # Alorair air treatment
    '127767': 'Decorations',               # Regina Andrew Detroit decor
    '127953': 'Small Appliances',          # Tiny Lux appliances
    '128179': 'Gifts',                     # CardCash gift cards
    '131143': 'Toys',                      # intimatify
    '131140': 'Tourist Attractions',       # Booking Radar tours
    '28831': 'General Household',          # Vevor tools and equipment
    '131822': 'Fragrance',                 # BRND COLLECTION perfume
}


def resolve_category(merchant, product, merchant_name):
    return MERCHANT_CATEGORY.get(merchant) or compact.resolve_category(product, merchant_name)


def read_feed(path, known, shop_slugs, merchant_brands):
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
            if row.get('aw_product_id') and row['aw_product_id'] != product:
                raise ValueError(f'Product id does not match the affiliate link for {product}')
            if not re.fullmatch(r'\d+(?:\.\d+)?', row['search_price']) or not re.fullmatch('[A-Z]{3}', row['currency']):
                raise ValueError(f'Invalid price or currency for product {product}')
            merchant_name = row['merchant_name']
            name = cj.clean_text(row['product_name'])
            if not name:
                raise ValueError(f'Empty product name for product {product}')

            brand, brand_slug = compact.resolve_brand(merchant_name, merchant, shop_slugs, merchant_brands)
            category = resolve_category(merchant, name, merchant_name)
            dept, kind = awin.CATEGORY[category]
            if 'esim' in merchant_name.casefold():
                dept, kind = 'travel', 'travel-esims'
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
    merchant_brands = compact.build_merchant_brands()
    export.read_feed = lambda path, known: read_feed(path, known, shop_slugs, merchant_brands)
    export.main(Path(sys.argv[1]).resolve())
