#!/usr/bin/env python3
"""Import the Amazon best-sellers affiliate feed (Partnerize click URLs) into the static shop.

Usage: python3 scripts/import-amazon-bestsellers.py [path/to/feed.csv]
       python3 scripts/update-counts.py

Every row becomes a shop item at /shop/amazon-<brand>-<name>-<asin>, keeping the
Partnerize affiliate click URL, name, price and description intact. Items are filed
under the single Amazon brand plus a department and product type mapped from the
product name, so no new brand pages are created. Each product's main photo is read
once from its Amazon product page and cached in data/amazon/images.json.

Product data, the product index, the Amazon brand list/page, department/type lists,
the brand directory and the sitemaps are updated in place, so re-running with the
same feed is a clean sync rather than a growing append. Only this feed's own items
are replaced; the Amazon products imported from other feeds are left untouched.
"""
import csv
import gzip
import importlib.util
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))


def _load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


cj = _load('import-cj-links')
bs = _load('import-awin-best-sellers')
awin = bs.awin

BRAND = 'Amazon'
DEFAULT_FEED = 'data/feeds/dealux-amazon-bestsellers.csv'
MANIFEST = Path('data/amazon/products.txt')
CACHE = Path('data/amazon/images.json')
ASIN_RE = re.compile(r'/dp/([A-Z0-9]{10})')
IMG_ID_RE = re.compile(rb'id="landing-image-wrapper".{0,800}?src="https://m\.media-amazon\.com/images/I/([A-Za-z0-9+%\-]+)\._AC_', re.S)
IMG_CDN = 'https://m.media-amazon.com/images/I/'
UA = ('Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 '
      '(KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1')
READ_LIMIT = 400000

# Amazon household goods the shared Awin rules miss, mapped to Awin category names.
AMAZON_RULES = [(re.compile(p, re.I), c) for p, c in [
    (r'water ?filter|water filtration|filter pitcher|water purifier|filter replacement|refrigerator water filter|faucet water filter|waterdrop|fil-?fresh', 'Home Accessories'),
    (r'\b(sheets?|sateen|combed cotton|microfiber|duvet|comforter|pillowcase|bed ?skirt|mattress protector)\b', 'Home Textiles'),
    (r'radiator|towing mirror|\bbumper\b|headlight|tail ?light|brake pad|spark plug|alternator|wiper|car cover|yitamotor|dwvo|engine mount', 'Car Parts'),
    (r'smoke|carbon monoxide|detector|\balarm\b|smart lock|door lock|deadbolt|keyless entry|doorbell|security camera|ultraloq|x-sense', 'Home Security'),
    (r'body (weight )?scale|bathroom scale|smart scale|weighing scale|digital scale', 'Health'),
    (r'massage|massager', 'Health'),
    (r'\bwelding\b|welder|arccaptain|screwdriver|\bdrill\b|tool kit|wrench|socket set', 'DIY'),
    (r'\bkeyboard\b|\bmouse\b|multimeter|\bhdmi\b|splitter|webcam|power bank|\bcharger\b|headphone|earbud|projector|\bmonitor\b|ssd|hard drive', 'Gadgets'),
    (r'air duct|ducting|vent hose|dryer vent', 'DIY'),
    (r'preserved rose|preserved flower|flower forever|\broses?\b|bouquet', 'Flowers'),
    (r'embosser|book stamp|library stamp', 'Office Supplies'),
    (r'\btights\b|\bleggings\b|yoga pants|activewear|sports bra', 'Sportswear & Swimwear'),
    (r'griddle|cast iron|skillet|cookware|cookware set|utensil|cutting board|air fryer|toaster|\bblender\b', 'Kitchen'),
    (r'garment steamer|\bsteamer\b|vacuum cleaner|vacuum steamer', 'Small Appliances'),
    (r'\btumbler\b|water bottle|thermos', 'Kitchen'),
    (r'\brugs?\b|\bmat\b|carpet|runner rug', 'Home Textiles'),
    (r'resistance band|dumbbell|kettlebell|yoga mat|exercise', 'Fitness'),
    (r'jewelry|necklace|earring|bracelet|\bring\b|pendant', "Women's Jewellery"),
    (r'sunglass|eyewear|reading glasses', 'Glasses'),
    (r'fire pit|firepit|fire bowl|fire glass|patio|gazebo|canopy', 'Garden & Leisure'),
]]


def category_for(name, brand):
    """Map a product onto the shop's Awin category taxonomy using its name and brand."""
    text = f'{name} {brand}'
    for pattern, category in bs.RULES:
        if pattern.search(text):
            return category
    for pattern, category in AMAZON_RULES:
        if pattern.search(text):
            return category
    return 'Gifts'


def asin_of(link):
    match = ASIN_RE.search(urllib.parse.unquote(link or ''))
    return match.group(1) if match else ''


def fetch_image(asin):
    """Return the product's main photo URL, or '' when Amazon has none or blocks us."""
    url = f'https://www.amazon.com/gp/aw/d/{asin}'
    for attempt in range(3):
        try:
            request = urllib.request.Request(url, headers={
                'User-Agent': UA, 'Accept-Encoding': 'gzip', 'Accept-Language': 'en-US,en;q=0.9'})
            with urllib.request.urlopen(request, timeout=25) as response:
                if response.headers.get('Content-Encoding') == 'gzip':
                    body = gzip.GzipFile(fileobj=response).read(READ_LIMIT)
                else:
                    body = response.read(READ_LIMIT)
            match = IMG_ID_RE.search(body)
            return IMG_CDN + match.group(1).decode() + '._AC_SL1500_.jpg' if match else ''
        except urllib.error.HTTPError as error:
            if error.code == 404:
                return ''
        except Exception:
            pass
    return ''


def load_images():
    return json.loads(CACHE.read_text(encoding='utf-8')) if CACHE.exists() else {}


def save_images(cache):
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(cache, separators=(',', ':'), sort_keys=True), encoding='utf-8')


def fetch_images(asins):
    cache = load_images()
    todo = [a for a in asins if a not in cache]
    print(f'{len(cache):,} images cached; fetching {len(todo):,}…', flush=True)
    if todo:
        done = 0
        with ThreadPoolExecutor(max_workers=16) as pool:
            for start in range(0, len(todo), 2000):
                batch = todo[start:start + 2000]
                for asin, image in zip(batch, pool.map(fetch_image, batch)):
                    cache[asin] = image
                done += len(batch)
                save_images(cache)
                found = sum(1 for a in todo[:done] if cache.get(a))
                print(f'  {done:,}/{len(todo):,} fetched ({found:,} with a photo)', flush=True)
    return cache


def build_items(rows, images):
    items = {}
    for row in rows:
        name = cj.clean_text(row.get('name', ''))
        brand = cj.clean_text(row.get('brand', ''))
        link = (row.get('affiliate_url') or '').strip()
        asin = asin_of(link)
        price = (row.get('price') or '').strip()
        if not name or not link or not asin or not re.fullmatch(r'\d+(?:\.\d+)?', price):
            continue
        slug = f'amazon-{cj.slugify(brand) or "amazon"}-{cj.slugify(name)[:80].strip("-")}-{asin.lower()}'
        desc = cj.clean_text(row.get('description', ''))
        if desc.lower() == name.lower():
            desc = ''
        category = category_for(name, brand)
        dept, kind = awin.CATEGORY[category]
        details = {'merchant': 'Amazon', 'category': category, 'type_slug': kind,
                   'brand_slug': 'amazon', 'product_brand': brand, 'stock_status': 'in stock'}
        record = [name, price, 'USD', BRAND, images.get(asin, ''), link, desc, details]
        items[slug] = dict(slug=slug, dept=dept, kind=kind, record=record)
    return items


def write_products(items, slugs, previous):
    shards = {n: cj.read_json(f'data/img/{n}.json', {}) for n in range(cj.IMG_SHARDS)}
    for n in shards:
        shards[n] = {k: v for k, v in shards[n].items() if k not in previous}
    for slug, item in items.items():
        shards[cj.shard_of(slug)][slug] = item['record']
    for n, data in shards.items():
        cj.write_json(f'data/img/{n}.json', data)

    for path in ('data/products.txt', 'products.txt'):
        lines = [s for s in Path(path).read_text(encoding='utf-8').splitlines() if s and s not in previous]
        Path(path).write_text('\n'.join(lines + slugs) + '\n', encoding='utf-8')

    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text('\n'.join(slugs) + '\n', encoding='utf-8')


def sync_lists(items, slugs, previous):
    for path in list(Path('data/list').glob('dept-*.json')) + list(Path('data/list').glob('type-*.json')) \
            + [Path('data/list/brand-amazon.json')]:
        current = cj.read_json(path, [])
        trimmed = [s for s in current if s not in previous]
        if trimmed != current:
            cj.write_json(path, trimmed)

    groups = {}
    for slug, item in items.items():
        groups.setdefault(f"dept-{item['dept']}", []).append(slug)
        groups.setdefault(f"type-{item['kind']}", []).append(slug)
    groups['brand-amazon'] = list(slugs)
    for name, added in groups.items():
        path = Path(f'data/list/{name}.json')
        current = cj.read_json(path, [])
        have = set(added)
        cj.write_json(path, added + [s for s in current if s not in have])


def update_brand_page(count):
    path = Path('shop/brand/amazon/index.html')
    if path.exists():
        text = path.read_text(encoding='utf-8')
        text = re.sub(r'<p class="muted">[\d,]+ products?</p>', f'<p class="muted">{count:,} products</p>', text, count=1)
        text = re.sub(r'content="Shop [\d,]+ ', f'content="Shop {count:,} ', text, count=1)
        text = re.sub(r'<title>.*?</title>', f'<title>{BRAND} — Dealux Shop</title>', text, count=1)
        path.write_text(text, encoding='utf-8')
        return
    template = Path('shop/brand/3w/index.html').read_text(encoding='utf-8')
    template = re.sub(r'(<summary><span class="side-link side-heading">Shop by brand</span></summary>).*?(</details>)',
                      r'\1<a class="side-link sub" href="/brands/">Browse all brands</a>\2', template, flags=re.S)
    cj.write_page(str(path), cj.page_from(template, '/shop/brand/amazon/', BRAND,
                                          f'Shop {count:,} Amazon products and deals.',
                                          f'Shop {BRAND}', f'{count:,} products', '/data/list/brand-amazon.json'))


def update_brand_links(items):
    for path in ('data/brands.json', 'brands.json'):
        brands = cj.read_json(path, [])
        have = {cj.slugify(b[0]) for b in brands}
        if cj.slugify(BRAND) not in have:
            brands.append([BRAND, next(iter(items.values()))['record'][5]])
            cj.write_json(path, sorted(brands, key=lambda b: b[0].casefold()))


def update_sitemaps(slugs):
    today = cj.TODAY.isoformat()
    files = []
    for number, start in enumerate(range(0, len(slugs), 10000), 1):
        name = f'sitemap-amazon-products-{number}.xml'
        files.append(name)
        body = ''.join(f'<url><loc>{cj.SITE}/shop/{s}</loc><lastmod>{today}</lastmod></url>\n' for s in slugs[start:start + 10000])
        Path(name).write_text('<?xml version="1.0" encoding="UTF-8"?>\n'
                              '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + body + '</urlset>\n',
                              encoding='utf-8')
    # Drop stale Amazon shards from a previous run, then list the current set.
    for stale in Path('.').glob('sitemap-amazon-products-*.xml'):
        if stale.name not in files:
            stale.unlink()
    index = Path('sitemap-index.xml')
    text = index.read_text(encoding='utf-8')
    text = re.sub(r'\s*<sitemap><loc>[^<]*/sitemap-amazon-products-\d+\.xml</loc><lastmod>[^<]*</lastmod></sitemap>', '', text)
    add = ''.join(f'  <sitemap><loc>{cj.SITE}/{name}</loc><lastmod>{today}</lastmod></sitemap>\n' for name in files)
    index.write_text(text.replace('</sitemapindex>', add + '</sitemapindex>'), encoding='utf-8')

    shop = Path('sitemap-shop.xml')
    text = shop.read_text(encoding='utf-8')
    url = f'{cj.SITE}/shop/brand/amazon/'
    if f'<loc>{url}</loc>' not in text:
        text = text.replace('</urlset>', f'<url><loc>{url}</loc><lastmod>{today}</lastmod></url>\n</urlset>')
        shop.write_text(text, encoding='utf-8')


def main(path, refresh=False):
    rows = list(csv.DictReader(open(path, encoding='utf-8-sig')))
    previous = set(MANIFEST.read_text(encoding='utf-8').split()) if MANIFEST.exists() else set()
    asins = [asin_of(r.get('affiliate_url', '')) for r in rows]
    images = {} if refresh else fetch_images([a for a in asins if a])
    items = build_items(rows, images)
    if not items:
        raise SystemExit('The feed contained no usable products.')
    slugs = sorted(items)
    write_products(items, slugs, previous)
    sync_lists(items, slugs, previous)
    count = len(cj.read_json('data/list/brand-amazon.json', []))
    update_brand_page(count)
    update_brand_links(items)
    cj.update_brand_directory({'amazon': count}, {'amazon': BRAND})
    update_sitemaps(slugs)
    with_photo = sum(1 for i in items.values() if i['record'][4])
    print(f'Amazon: {len(items):,} products ({with_photo:,} with a photo), brand page /shop/brand/amazon/ '
          f'now lists {count:,} products')


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('-')]
    main(args[0] if args else DEFAULT_FEED, refresh='--refresh' in sys.argv)
