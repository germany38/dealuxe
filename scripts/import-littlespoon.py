#!/usr/bin/env python3
"""Import the Little Spoon product feed (Impact CSV) into the static shop.

Usage: python3 scripts/import-littlespoon.py path/to/Little-Spoon-Product-Feed.csv

Each in-stock SKU becomes one shop item at /shop/little-spoon-<sku>, keeping
Little Spoon's tracked affiliate link. Baby food, kids' meals and smoothies go
to Food & Snacks › Pantry & Food, snacks to Snack Bars and plates/gear to
Baby & Nursery. Product data, lists, the brand page, brand directory and
sitemaps are updated in place, so re-running with the same CSV is a no-op.
"""
import csv, importlib.util, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location('cj', os.path.join(HERE, 'import-cj-links.py'))
cj = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cj)

BRAND = 'Little Spoon'
BRAND_SLUG = 'little-spoon'
BRAND_LINK = 'https://littlespoon.sjv.io/c/5661882/2886090/30259'
CATEGORY = {'Snacks': ('food-snacks', 'snack-bars'), 'Puffs': ('food-snacks', 'snack-bars'),
            'Plates': ('toys-hobbies', 'baby-nursery')}
DEFAULT = ('food-snacks', 'pantry-food')


def main(csv_path):
    rows = [r for r in csv.DictReader(open(csv_path, encoding='utf-8-sig')) if r['Stock Availability'].strip() == 'Y']
    shards = {n: cj.read_json(f'data/img/{n}.json', {}) for n in range(cj.IMG_SHARDS)}
    taken = set(k for s in shards.values() for k in s)

    items = []
    for r in rows:
        sku, link = r['Unique Merchant SKU'].strip(), r['Product URL'].strip()
        if not sku or not link:
            continue
        slug = f'{BRAND_SLUG}-' + cj.slugify(sku)[:90].strip('-')
        if slug in taken:
            continue
        taken.add(slug)
        dept, typ = CATEGORY.get(r['Category'].strip(), DEFAULT)
        name = cj.clean_text(re.sub(r'\s*\|\s*Little Spoon\s*$', '', r['Product Name']))
        desc = cj.clean_text(r['Product Description'])
        items.append(dict(slug=slug, dept=dept, type=typ,
                          rec=[name, r['Current Price'].strip(), r['Currency'].strip() or 'USD', BRAND,
                               r['Image URL'].strip(), link, desc]))
    if not items:
        print('Nothing new to import.')
        return
    print(f'{len(items)} new Little Spoon items from {len(rows)} rows')

    for it in items:
        shards[cj.shard_of(it['slug'])][it['slug']] = it['rec']
    for n, data in shards.items():
        cj.write_json(f'data/img/{n}.json', data)
    for path in ('data/products.txt', 'products.txt'):
        with open(path, 'a', encoding='utf-8') as f:
            f.write(''.join(i['slug'] + '\n' for i in items))

    def add_to_list(name, slugs):
        path = f'data/list/{name}.json'
        lst = cj.read_json(path, [])
        have = set(lst)
        lst += [s for s in slugs if s not in have]
        cj.write_json(path, lst)
        return len(lst)

    for key, prefix in (('dept', 'dept'), ('type', 'type')):
        for v in {i[key] for i in items}:
            add_to_list(f'{prefix}-{v}', [i['slug'] for i in items if i[key] == v])
    count = add_to_list(f'brand-{BRAND_SLUG}', [i['slug'] for i in items])

    template = open('shop/brand/3w/index.html', encoding='utf-8').read()
    new_pages = []
    page = f'shop/brand/{BRAND_SLUG}/index.html'
    if os.path.exists(page):
        h = open(page, encoding='utf-8').read()
        h = re.sub(r'<p class="muted">[\d,]+ products</p>', f'<p class="muted">{count:,} products</p>', h, count=1)
        h = re.sub(r'content="Shop [\d,]+ ', f'content="Shop {count:,} ', h, count=1)
    else:
        h = cj.page_from(template, f'/shop/brand/{BRAND_SLUG}/', BRAND,
                         f'Shop {count:,} {BRAND} organic baby food, toddler meals and healthy kids snacks.',
                         f'Shop {BRAND}', f'{count:,} products', f'/data/list/brand-{BRAND_SLUG}.json')
        new_pages.append(f'{cj.SITE}/shop/brand/{BRAND_SLUG}/')
    cj.write_page(page, h)

    for path in ('data/brands.json', 'brands.json'):
        lst = cj.read_json(path, [])
        if not any(cj.slugify(b[0]) == BRAND_SLUG for b in lst):
            lst.append([BRAND, BRAND_LINK])
            lst.sort(key=lambda b: b[0].lower())
            cj.write_json(path, lst)

    cj.update_sitemaps([i['slug'] for i in items], new_pages)
    print(f'{BRAND} brand now has {count:,} products, {len(new_pages)} new listing pages')


if __name__ == '__main__':
    main(sys.argv[1])
