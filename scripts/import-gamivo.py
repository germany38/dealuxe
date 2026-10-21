#!/usr/bin/env python3
"""Import a Gamivo product feed (CSV) into the static shop.

Usage: python3 scripts/import-gamivo.py path/to/gamivo_catalog.csv

The feed repeats every product once per market; the Global/EN USD row is used
so each product becomes one shop item at /shop/gamivo-<product_id>, keeping
Gamivo's tracked affiliate link. Games go to Video Games, software licences to
Software & Apps and gift cards / top-ups to a Gift Cards type. Product data,
lists, the Gamivo brand page, brand directory and sitemaps are updated in
place, so re-running with the same CSV is a no-op.
"""
import csv, html, importlib.util, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location('cj', os.path.join(HERE, 'import-cj-links.py'))
cj = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cj)

BRAND = 'Gamivo'
BRAND_LINK = 'https://gamivo.prf.hn/click/camref:1100l6w2FS/destination:https%3A%2F%2Fwww.gamivo.com%2F'
GIFT = ('gift-cards-top-ups', 'Gift Cards &amp; Top-Ups')
GIFT_DESC = 'Digital gift cards, wallet top-ups and prepaid codes for games, apps and stores.'
cj.NEW_TYPES = {'services': [GIFT]}


def category(r):
    if r['category_id'] == '1279':
        return 'toys-hobbies', 'video-games'
    if r['category_id'] == '53':
        return 'services', GIFT[0]
    return 'electronics', 'software-apps'


def describe(r):
    d = cj.clean_text(r['description'])
    if len(d) >= 150 and not d.endswith(('.', '!', '?')):
        d = d.rsplit(' ', 1)[0].rstrip(',;:-') + '…'
    facts = [f"Platform: {r['platform']}" if r['platform'] else '',
             f"Edition: {r['edition']}" if r['edition'] and r['edition'] != 'Standard' else '',
             f"Genres: {r['genres']}" if r['genres'] else '']
    facts = ' · '.join(f for f in facts if f)
    return ' '.join(x for x in [d, facts + '.' if facts else ''] if x)


def main(csv_path):
    rows = [r for r in csv.DictReader(open(csv_path, encoding='utf-8-sig'))
            if r['market'] == 'Global/EN' and r['currency'] == 'USD' and r['availability'] == 'in stock']
    shards = {n: cj.read_json(f'data/img/{n}.json', {}) for n in range(cj.IMG_SHARDS)}
    taken = set(k for s in shards.values() for k in s)

    items, seen = [], set()
    for r in rows:
        pid, link = r['product_id'].strip(), r['affiliate_link'].strip()
        if not pid or not link or pid in seen:
            continue
        seen.add(pid)
        slug = 'gamivo-' + cj.slugify(pid)[:90].strip('-')
        if slug in taken:
            continue
        taken.add(slug)
        dept, typ = category(r)
        name = cj.clean_text(r['title'])
        items.append(dict(slug=slug, brand=BRAND, dept=dept, type=typ,
                          rec=[name, r['price'], 'USD', BRAND, r['image_link'].strip(), link, describe(r)]))
    if not items:
        print('Nothing new to import.')
        return
    print(f'{len(items)} new Gamivo items from {len(rows)} rows')

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
    count = add_to_list('brand-gamivo', [i['slug'] for i in items])

    # New Gift Cards type in every shop sidebar, plus its landing page.
    cj.update_sidebars(None)
    template = open('shop/brand/3w/index.html', encoding='utf-8').read()
    new_pages = []
    p = f'shop/type/{GIFT[0]}/index.html'
    if not os.path.exists(p):
        cj.write_page(p, cj.page_from(template, f'/shop/type/{GIFT[0]}/', GIFT[1], GIFT_DESC, GIFT[1], GIFT_DESC,
                                      f'/data/list/type-{GIFT[0]}.json', active=f'/shop/type/{GIFT[0]}/'))
        new_pages.append(f'{cj.SITE}/shop/type/{GIFT[0]}/')

    page = 'shop/brand/gamivo/index.html'
    if os.path.exists(page):
        h = open(page, encoding='utf-8').read()
        h = re.sub(r'<p class="muted">[\d,]+ products</p>', f'<p class="muted">{count:,} products</p>', h, count=1)
        h = re.sub(r'content="Shop [\d,]+ ', f'content="Shop {count:,} ', h, count=1)
    else:
        h = cj.page_from(template, '/shop/brand/gamivo/', BRAND,
                         f'Shop {count:,} {BRAND} game keys, gift cards and software deals.',
                         f'Shop {BRAND}', f'{count:,} products', '/data/list/brand-gamivo.json')
        new_pages.append(f'{cj.SITE}/shop/brand/gamivo/')
    cj.write_page(page, h)

    for path in ('data/brands.json', 'brands.json'):
        lst = cj.read_json(path, [])
        if not any(cj.slugify(b[0]) == 'gamivo' for b in lst):
            lst.append([BRAND, BRAND_LINK])
            lst.sort(key=lambda b: b[0].lower())
            cj.write_json(path, lst)

    cj.update_sitemaps([i['slug'] for i in items], new_pages)
    print(f'Gamivo brand now has {count:,} products, {len(new_pages)} new listing pages')


if __name__ == '__main__':
    main(sys.argv[1])
