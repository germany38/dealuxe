#!/usr/bin/env python3
"""Import the Gameseal product feed (Impact CSV) into the static shop.

Usage: python3 scripts/import-gameseal.py path/to/Gameseal_feed.csv

Each in-stock SKU becomes one shop item at /shop/gameseal-<sku>, keeping
Gameseal's tracked affiliate link, and joins the existing Gameseal.com brand.
Games and DLC go to Video Games, software licences to Software & Apps and
top-ups, game points and subscriptions to Gift Cards & Top-Ups. Product data,
lists, the brand page and sitemaps are updated in place, so re-running with
the same CSV is a no-op.
"""
import csv, importlib.util, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location('cj', os.path.join(HERE, 'import-cj-links.py'))
cj = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cj)

BRAND = 'Gameseal.com'
BRAND_SLUG = 'gameseal-com'
GIFT = ('services', 'gift-cards-top-ups')
SOFTWARE = ('electronics', 'software-apps')
GAMES = ('toys-hobbies', 'video-games')


def category(ptype):
    parts = [p.strip() for p in ptype.split('>')]
    if parts[0] in ('Direct Top-Up', 'Game points', 'Subscriptions'):
        return GIFT
    if parts[0] in ('Software', 'AI') or (len(parts) > 1 and parts[1] == 'Software'):
        return SOFTWARE
    return GAMES


def describe(r):
    d = cj.clean_text(r['Product Description'])
    parts = [p.strip() for p in r['Product Type'].split('>')]
    facts = [f"Platform: {parts[-1] if parts[0] == 'PC' else parts[0]}" if parts[0] not in ('Direct Top-Up', 'Game points') else '',
             f"Publisher: {r['Manufacturer'].strip()}" if r['Manufacturer'].strip() else '',
             f"Region: {r['Product Name'].rsplit(' - ', 1)[-1].strip()}" if ' - ' in r['Product Name'] else '']
    facts = ' · '.join(f for f in facts if f)
    return ' '.join(x for x in [d, facts + '.' if facts else ''] if x)


def main(csv_path):
    rows = [r for r in csv.DictReader(open(csv_path, encoding='utf-8-sig')) if r['Stock Availability'].strip() == 'Y']
    shards = {n: cj.read_json(f'data/img/{n}.json', {}) for n in range(cj.IMG_SHARDS)}
    taken = set(k for s in shards.values() for k in s)

    items = []
    for r in rows:
        sku, link = r['Unique Merchant SKU'].strip(), r['Product URL'].strip()
        if not sku or not link:
            continue
        slug = 'gameseal-' + cj.slugify(sku)[:90].strip('-')
        if slug in taken:
            continue
        taken.add(slug)
        dept, typ = category(r['Product Type'])
        items.append(dict(slug=slug, dept=dept, type=typ,
                          rec=[cj.clean_text(r['Product Name']), r['Current Price'].strip(), r['Currency'].strip() or 'USD',
                               BRAND, r['Image URL'].strip(), link, describe(r)]))
    if not items:
        print('Nothing new to import.')
        return
    print(f'{len(items)} new Gameseal items from {len(rows)} rows')

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

    page = f'shop/brand/{BRAND_SLUG}/index.html'
    h = open(page, encoding='utf-8').read()
    h = re.sub(r'<p class="muted">[\d,]+ products</p>', f'<p class="muted">{count:,} products</p>', h, count=1)
    h = re.sub(r'<meta name="description" content="[^"]*">',
               f'<meta name="description" content="Shop {count:,} {BRAND} Steam, Xbox and GOG game keys, DLC, software and game top-ups.">', h, count=1)
    cj.write_page(page, h)

    cj.update_sitemaps([i['slug'] for i in items], [])
    print(f'{BRAND} brand now has {count:,} products')


if __name__ == '__main__':
    main(sys.argv[1])
