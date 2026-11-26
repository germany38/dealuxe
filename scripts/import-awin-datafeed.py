#!/usr/bin/env python3
"""Publish a raw Awin product datafeed into the shop catalog.

Usage: python3 scripts/import-awin-datafeed.py data/feeds/awin-datafeed.csv[.gz]
       python3 scripts/update-counts.py

The feed uses Awin's standard download columns (aw_deep_link, product_name,
aw_product_id, merchant_image_url, merchant_category, search_price,
merchant_name, merchant_id, category_name, aw_image_url, currency, ...).
Each row is normalised onto the export format and published through
import-awin-export.py, so it lands in the Netlify Database migration, the
static product shards, the brand/department/type lists, the brand directory
and the sitemaps. Products are filed under their merchant's brand page and a
department/type resolved from the Awin category (with keyword and merchant
fallbacks for rows the feed leaves uncategorised).
"""
import csv
import gzip
import importlib.util
import re
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse

spec = importlib.util.spec_from_file_location('export', Path(__file__).with_name('import-awin-export.py'))
export = importlib.util.module_from_spec(spec)
spec.loader.exec_module(export)
awin, cj = export.awin, export.cj

# Awin categories that the shop tree does not name yet, mapped onto an existing key.
EXTRA_CATEGORY = {
    'Adult Toys': 'Toys',
    'Adult Gifts': 'Gifts',
    'Adult Movies': 'DVDs',
    'Wine, Spirits & Tobacco': 'Drinks',
}

# (pattern, Awin category) searched in merchant_category + product name; first match wins.
RULES = [
    (r'\brug|carpet|shag|runner', 'Home Textiles'),
    (r'phone case|mobile phone|smart ?phone|mobile accessor', 'Mobile Phone Accessories'),
    (r'christmas', 'Christmas Gifts'),
    (r'gift card|gift ideas|personalized video|personalised', 'Gifts'),
    (r'home ?& ?office', 'Home Accessories'),
    (r'out ?door ?& ?travel', 'Outdoor Adventure'),
    (r'fitness ?& ?health', 'Fitness'),
    (r'lighter', 'Gadgets'),
    (r'oral care|oral health', 'Oral Health'),
    (r'portrait|watercolo', 'Art'),
    (r'automotive|car parts', 'Car Parts'),
    (r'portable wi-?fi', 'Networking'),
    (r'gps tracker', 'Pets'),
    (r'diamond|jewel', "Women's Jewellery"),
    (r'hair ?care|scalp', 'Haircare Products'),
    (r'deodorant|skin ?care|cosmetic', 'Cosmetics & Skincare'),
    (r'dog supplement|green-?lipped', 'Pets'),
    (r'plugin|wordpress', 'Software'),
    (r'clothing|apparel', 'General Clothing'),
    (r'health', 'Health'),
]
RULES = [(re.compile(p, re.I), c) for p, c in RULES]

# Merchant fallbacks for rows the feed ships with no category at all.
MERCHANTS = [
    ('hugmoom', 'Home Textiles'), ('loomy home', 'Home Textiles'), ('mosaic weighted', 'Home Textiles'),
    ('balarugs', 'Home Textiles'), ('knitfirst', 'Home Textiles'),
    ('embossed graphics', 'Gifts'), ('1st class cigar', 'Gifts'), ('magic gram', 'Gifts'),
    ('turbotech', 'Gadgets'), ('mintion', 'Gadgets'), ('superbox', 'Gadgets'),
    ('robotime', 'Toys'),
    ('food valley', 'Kitchen'), ('imarku', 'Kitchen'),
    ('atlanta cutlery', 'Outdoor Adventure'), ('flextail', 'Outdoor Adventure'),
    ('wuben', 'Outdoor Adventure'), ('imalent', 'Outdoor Adventure'),
    ('feinuote', 'Mobile Phone Accessories'),
    ('dragonhawk', 'Cosmetics & Skincare'), ('deluvia', 'Cosmetics & Skincare'),
    ("nature's skin", 'Cosmetics & Skincare'),
    ('nothingprojector', 'Home Entertainment'),
    ('ogstreetwear', 'General Clothing'), ('wonder hoodie', 'General Clothing'), ('needs no label', 'General Clothing'),
    ('everywhere chair', 'Chairs'),
    ('bookemon', 'Books'),
    ('astroai', 'Car Accessories'), ('houlang', 'Car Accessories'), ('autoone', 'Car Accessories'),
    ('ottocast', 'Car Accessories'), ('vatrer', 'Car Parts'),
    ('rowabi', 'Lighting'),
    ('qumi', 'Health'), ('alphabiolabs', 'Health'), ('vivtone', 'Health'), ('check my body health', 'Health'),
    ('jr associates', 'Music'), ('ikarao', 'Audio Equipment'), ('retrolifeplayer', 'Audio Equipment'),
    ('contactlensesplus', 'Contact Lenses'),
    ('ape born', 'Fitness'),
    ('ecosusi', 'Bags'), ('breck and grier', 'Bags'),
    ('wondershare', 'Software'), ('plugins-for-wordpress', 'Software'),
    ('truthbrush', 'Oral Health'),
    ('big horn outdoors', 'Garden & Leisure'),
    ('magicshine', 'Cycling'),
    ('paintmysoul', 'Art'), ('earthly', 'Art'),
    ('contact crafts', 'Arts & Crafts'),
    ('dima eyewear', 'Glasses'),
    ('mojawa', 'Headphones'),
    ('database mart', 'Web Hosting'), ('anylistingseo', 'Web Hosting'),
    ('thrivous', 'Vitamins & Supplements'),
    ('ucloudlink', 'Networking'),
    ('myhand', 'Home Security'),
    ('hck refrigerator', 'Refrigeration'),
    ('upper brand', 'Baby Products'),
    ('alzoo', 'Pets'), ('petcube', 'Pets'), ('dogevera', 'Pets'),
    ('companion candles', 'Decorations'),
    ('colordiamonds', "Women's Jewellery"), ('santean', "Women's Jewellery"),
    ('alan bauman', 'Haircare Products'), ('enable accessible', 'Haircare Products'),
]
DEFAULT_CATEGORY = 'Gifts'


def resolve_category(row):
    for value in ((row.get('category_name') or '').strip(), (row.get('merchant_category') or '').strip()):
        if value in awin.CATEGORY:
            return value
        if value in EXTRA_CATEGORY:
            return EXTRA_CATEGORY[value]
    text = f"{row.get('merchant_category') or ''} {row.get('product_name') or ''}"
    for pattern, category in RULES:
        if pattern.search(text):
            return category
    merchant = (row.get('merchant_name') or '').casefold()
    for key, category in MERCHANTS:
        if key in merchant:
            return category
    return DEFAULT_CATEGORY


def open_feed(path):
    if path.suffix == '.gz' or str(path).endswith('.gz'):
        return gzip.open(path, 'rt', encoding='utf-8-sig', newline='')
    return path.open(encoding='utf-8-sig', newline='')


def read_feed(path, known):
    items = {}
    with open_feed(Path(path)) as stream:
        for row in csv.DictReader(stream):
            if None in row or None in row.values():
                raise ValueError(f"Malformed row for product {row.get('aw_product_id')}")
            merchant, product = row['merchant_id'], row['aw_product_id']
            url = urlparse(row['aw_deep_link'])
            query = parse_qs(url.query)
            if (not re.fullmatch(r'\d+-\d+', f'{merchant}-{product}') or url.scheme != 'https'
                    or url.netloc != 'www.awin1.com' or query.get('m') != [merchant]
                    or query.get('p') != [product] or not query.get('a')):
                raise ValueError(f'Invalid affiliate link for product {product}')
            if not re.fullmatch(r'\d+(?:\.\d+)?', row['search_price']) or not re.fullmatch('[A-Z]{3}', row['currency']):
                raise ValueError(f'Invalid price or currency for product {product}')

            category = resolve_category(row)
            dept, kind = awin.CATEGORY[category]
            if 'esim' in row['merchant_name'].casefold():
                dept, kind = 'travel', 'travel-esims'
            brand = cj.clean_text(row['merchant_name'])
            name = cj.clean_text(row['product_name'])
            slug = known.get((merchant, product)) or f'awin-{cj.slugify(brand)}-{cj.slugify(name)[:90].strip("-")}-{merchant}-{product}'
            image = next((row[key] for key in ('merchant_image_url', 'aw_image_url')
                          if urlparse(row.get(key, '')).scheme == 'https'), '')

            description = cj.clean_text(row['description'])
            # Only the columns the migration reads are kept, so the archived
            # source_data stays compact; the full description ships on the page.
            raw = {
                'product_name': name, 'search_price': row['search_price'], 'currency': row['currency'],
                'merchant_name': row['merchant_name'], 'category_name': category,
                'aw_deep_link': row['aw_deep_link'], 'description': description[:500],
            }
            details = {'merchant': row['merchant_name'], 'category': category, 'type_slug': kind,
                       'brand_slug': cj.slugify(brand)}
            if row['merchant_category']:
                details['merchant_category'] = row['merchant_category']
                details['product_type'] = row['merchant_category']
            if row['delivery_cost']:
                details['delivery_cost'] = row['delivery_cost']
            record = [name, row['search_price'], row['currency'], brand, image, row['aw_deep_link'],
                      description, details]
            if slug in items:
                raise ValueError(f'Duplicate feed row for product {product}')
            items[slug] = (slug, raw, record, dept, kind)
    if not items:
        raise ValueError('The feed contained no products')
    return items


if __name__ == '__main__':
    export.read_feed = read_feed
    export.main(Path(sys.argv[1]).resolve())
