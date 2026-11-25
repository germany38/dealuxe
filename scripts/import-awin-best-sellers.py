#!/usr/bin/env python3
"""Import an Awin "best sellers" feed (Google Shopping style columns) into the shop.

Run: python3 scripts/import-awin-best-sellers.py data/feeds/awin-best-sellers.csv
     python3 scripts/update-counts.py

Maps each row onto the Awin export format and publishes it through
import-awin-export.py (Netlify Database migration, shards, lists, sitemaps).
Every product is tagged as a Power Deal with a short reason shown on its page and card.
"""
import csv
import importlib.util
import re
import sys
from decimal import Decimal
from pathlib import Path
from urllib.parse import parse_qs, urlparse

spec = importlib.util.spec_from_file_location('export', Path(__file__).with_name('import-awin-export.py'))
export = importlib.util.module_from_spec(spec)
spec.loader.exec_module(export)
awin, cj = export.awin, export.cj

# (pattern, Awin category name) — first match wins; searched in category + product type + title.
RULES = [
    (r'perfume|cologne|fragrance', 'Fragrance'),
    (r'skin ?care|cosmetic|make-?up|serum|cream|lotion|lip|mascara|nail', 'Cosmetics & Skincare'),
    (r'\bhair', 'Haircare Products'),
    (r'sunglass|eyewear|glasses', 'Glasses'),
    (r'jewel|necklace|\brings?\b|earring|bracelet|pendant|diamond|anklet', "Women's Jewellery"),
    (r'\bwatch(es)?\b', 'Accessories'),
    (r'\brugs?\b|carpet|runner', 'Home Textiles'),
    (r'cushion|linens|bedding|duvet|pillow|blanket|curtain|towel', 'Home Textiles'),
    (r'chandelier|lighting|\blamps?\b|pendant light|sconce|\blights?\b', 'Lighting'),
    (r'vehicle|auto ?parts|\bcar\b|truck|headlight|motorcycle', 'Car Parts'),
    (r'costume', 'Fancy Dress'),
    (r'activewear|swim|leggings|sports bra|yoga', 'Sportswear & Swimwear'),
    (r'outerwear|coat|jacket|parka|vest', "Women's Outerwear"),
    (r'dress|skirt', "Women's Dresses & Skirts"),
    (r'shirt|tops?\b|sweatshirt|hoodie|sweater|blouse|tee\b|cardigan', "Women's Tops"),
    (r'pants|trousers|jeans|shorts', "Women's Trousers"),
    (r'shoe|footwear|boot|sneaker|sandal|slipper', 'Shoes'),
    (r'handbag|wallet|luggage|backpack|suitcase|\bbags?\b|purse|tote', 'Bags'),
    (r'clothing accessories|hat|scarf|belt|glove|sock', 'Accessories'),
    (r'clothing|apparel|lingerie|underwear|bodysuit|shapewear', 'General Clothing'),
    (r'pet|\bdogs?\b|\bcats?\b|animals', 'Pets'),
    (r'puzzle|board game|games', 'Games, Puzzles & Learning'),
    (r'baby|toddler|nappy', 'Baby Products'),
    (r'toy', 'Toys'),
    (r'kitchen|dining|cookware|chef|cutlery', 'Kitchen'),
    (r'knife|knives|blade|flashlight|tactical|multi-?tool|survival|camping|hiking|pen\b', 'Outdoor Adventure'),
    (r'herb|supplement|vitamin|capsule|extract|tea\b', 'Vitamins & Supplements'),
    (r'bakery|candy|chocolate|sweets|snack|cake', 'Cakes, Snacks & Sweets'),
    (r'food items|food\b', 'Food'),
    (r'beverage|drink|coffee', 'Drinks'),
    (r'outdoor furniture|lawn & garden|gardening|patio|canopy|gazebo|plant', 'Garden & Leisure'),
    (r'bike|e-?bike|cycling|scooter', 'Cycling'),
    (r'sporting|fitness|exercise|athletics|outdoor recreation', 'Fitness'),
    (r'hobbies|creative arts|craft|model kit|diy kit', 'Arts & Crafts'),
    (r'party|celebration', 'Other Occasions'),
    (r'camera & optic|optics|photography|tripod|lens', 'Photography'),
    (r'camera', 'Cameras'),
    (r'software', 'Software'),
    (r'appliance|fireplace|heater|fan\b', 'Small Appliances'),
    (r'electronic|computer|audio|video|gps|networking|phone|charger', 'Gadgets'),
    (r'chair|stool|bench', 'Chairs'),
    (r'table|desk', 'Tables'),
    (r'sofa|futon|couch', 'Sofas'),
    (r'\bbeds?\b|mattress', 'Beds'),
    (r'cabinet|shelving|storage', 'Storage'),
    (r'furniture', 'Furniture'),
    (r'hardware|tools?\b|building|electrical|hvac', 'DIY'),
    (r'health|medical|safety', 'Health'),
    (r'office|paper', 'Office Supplies'),
    (r'decor|wall art|vase|mirror|home|bathroom|household|pool', 'Home Accessories'),
]
RULES = [(re.compile(p, re.I), c) for p, c in RULES]
# Fallback when a row has no usable category: the merchant's main line of products.
MERCHANTS = {'atlas knife': 'Outdoor Adventure', 'northsky': 'Outdoor Adventure', 'blade infiniti': 'Outdoor Adventure',
             'autoparts': 'Car Parts', 'labworkauto': 'Car Parts', 'grundig auto': 'Car Parts', 'herbsdaily': 'Food',
             'area rugs': 'Home Textiles', 'balarugs': 'Home Textiles', 'sirui': 'Photography', 'willit': 'Sportswear & Swimwear'}
FIELDS = ['aw_deep_link', 'product_name', 'aw_product_id', 'merchant_image_url', 'description', 'merchant_category',
          'search_price', 'merchant_name', 'merchant_id', 'category_name', 'aw_image_url', 'currency', 'delivery_cost',
          'merchant_deep_link', 'language', 'last_updated', 'brand_name', 'colour', 'condition', 'product_type',
          'merchant_product_category_path', 'rrp_price', 'stock_status', 'large_image', 'alternate_image', 'ean', 'mpn',
          'bestseller_score', 'power_deal']


def category_for(row):
    for text in (f"{row['google_product_category']} {row['product_type']}", row['title']):
        for pattern, name in RULES:
            if pattern.search(text):
                return name
    merchant = row['advertiser_name'].casefold()
    return next((name for key, name in MERCHANTS.items() if key in merchant), 'Gifts')


def money(value):
    m = re.fullmatch(r'(\d+(?:\.\d+)?) ([A-Z]{3})', value.strip())
    return (m.group(1), m.group(2)) if m else (None, None)


def power_deal(price, rrp, score, category):
    """A few words on why the item earned its Power Deal badge."""
    label = category.replace("Women's ", '').replace(' & ', ' and ').lower()
    off = int(round((1 - Decimal(price) / Decimal(rrp)) * 100)) if rrp and Decimal(rrp) > Decimal(price) else 0
    if off >= 5:
        return f'{off}% off a best-selling pick in {label}.'
    if score >= 70:
        return f'Top-ranked best seller in {label} right now.'
    if Decimal(price) < 25:
        return f'Shopper favourite in {label} for under 25.'
    if score >= 60:
        return f'One of the most-bought {label} picks, in stock now.'
    return f'Trending best seller in {label} with in-stock availability.'


def read_feed(path, known):
    items = {}
    with Path(path).open(encoding='utf-8-sig', newline='') as stream:
        for row in csv.DictReader(stream):
            if None in row or None in row.values():
                raise ValueError(f"Malformed row for product {row.get('id')}")
            merchant, product = row['advertiser_id'], cj.slugify(row['id'])
            url = urlparse(row['aw_deep_link'])
            if (not re.fullmatch(r'\d+', merchant) or not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', product) or url.scheme != 'https'
                    or url.netloc != 'www.awin1.com' or parse_qs(url.query).get('awinmid') != [merchant]):
                raise ValueError(f'Invalid affiliate link for product {product}')
            regular, currency = money(row['price'])
            sale, sale_currency = money(row['sale_price']) if row['sale_price'] else (None, None)
            if not regular:
                raise ValueError(f'Invalid price for product {product}')
            price = sale if sale and sale_currency == currency and Decimal(sale) < Decimal(regular) else regular
            category = category_for(row)
            dept, kind = awin.CATEGORY[category]
            brand = cj.clean_text(row['brand']) or cj.clean_text(row['advertiser_name'])
            name = cj.clean_text(row['title'])
            slug = known.get((merchant, product)) or f'awin-{cj.slugify(brand)}-{cj.slugify(name)[:90].strip("-")}-{merchant}-{product}'
            image = row['image_link'] if urlparse(row['image_link']).scheme == 'https' else ''
            rrp = regular if price != regular else ''
            reason = power_deal(price, rrp, int(row['bestseller_score'] or 0), category)
            raw = dict.fromkeys(FIELDS, '')
            raw.update(aw_deep_link=row['aw_deep_link'], product_name=name, aw_product_id=row['id'], merchant_image_url=image,
                       description=row['description'], merchant_category=row['google_product_category'], search_price=price,
                       merchant_name=row['advertiser_name'], merchant_id=merchant, category_name=category, currency=currency,
                       brand_name=brand, product_type=row['product_type'], rrp_price=rrp, stock_status=row['availability'],
                       ean=row['gtin'], bestseller_score=row['bestseller_score'], power_deal=reason)
            details = {key: raw[key] for key in export.FIELDS if raw.get(key)}
            details.update(merchant=row['advertiser_name'], category=category, type_slug=kind,
                           brand_slug=cj.slugify(brand), power_deal=reason)
            record = [name, price, currency, brand, image, row['aw_deep_link'], cj.clean_text(row['description']), details]
            if slug in items:
                raise ValueError(f'Duplicate feed row for product {product}')
            items[slug] = (slug, raw, record, dept, kind)
    if not items:
        raise ValueError('The feed contained no products')
    return items


if __name__ == '__main__':
    export.read_feed = read_feed
    export.main(Path(sys.argv[1]).resolve())
