#!/usr/bin/env python3
"""Add the Amazon Journal articles (CSV) and the Pinterest board pins to the Shop.

Usage: python3 scripts/add-amazon-journal-and-pinterest.py ARTICLES.csv PINS_DIR
  ARTICLES.csv  columns: slug, title, meta_description, affiliate_link, body_html
  PINS_DIR      w-<board>.json files from widgets.pinterest.com/v3/pidgets/boards/SMlux673821/<board>/pins/
Affiliate links are copied verbatim. Pins whose link is already in the Shop (or repeated
across pins) are skipped. Re-running is a no-op for items that already exist.
"""
import csv, glob, html, json, os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
SITE, DATE, SHARDS = 'https://dealuxapp.com', '2026-11-14', 64
TEMPLATE = 'journal/the-ultimate-guide-to-mac-virtualization-streamline-cross-platform-workflows-wit/index.html'
esc = lambda s: html.escape(s, quote=True)
slugify = lambda s: re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')


def shard_of(slug):
    h = 5381
    for c in slug:
        h = ((h * 33) ^ ord(c)) & 0xFFFFFFFF
    return h % SHARDS


def dump(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(json.dumps(data, ensure_ascii=False, separators=(',', ':')))


def add_urls(path, urls):
    sm = open(path, encoding='utf-8').read()
    add = ''.join(f'  <url><loc>{u}</loc><lastmod>{DATE}</lastmod></url>\n' for u in urls if f'<loc>{u}</loc>' not in sm)
    open(path, 'w', encoding='utf-8').write(sm.replace('</urlset>', add + '</urlset>', 1))


def index_sitemap(name):
    idx = open('sitemap-index.xml', encoding='utf-8').read()
    if name not in idx:
        idx = idx.replace('</sitemapindex>', f'  <sitemap><loc>{SITE}/{name}</loc><lastmod>{DATE}</lastmod></sitemap>\n</sitemapindex>')
        open('sitemap-index.xml', 'w', encoding='utf-8').write(idx)


# ---------------- Amazon Journal articles ----------------
def journal(csv_path):
    csv.field_size_limit(10 ** 9)
    rows = list(csv.DictReader(open(csv_path, encoding='utf-8-sig')))
    tpl = open(TEMPLATE, encoding='utf-8').read()
    seen, made = set(), []
    for r in rows:
        slug = 'amazon-' + r['slug'] if not r['slug'].startswith(('amazon', 'audible', 'kindle', 'prime')) else r['slug']
        if slug in seen:
            slug = slugify(r['title'])[:80].strip('-')
        seen.add(slug)
        title, desc, body = r['title'], r['meta_description'], r['body_html']
        t, d, url = esc(title), esc(desc), f'{SITE}/journal/{slug}/'
        words = len(re.sub(r'<[^>]+>', ' ', body).split())
        ld = json.dumps({'@context': 'https://schema.org', '@type': 'Article', 'headline': title[:110], 'description': desc,
                         'datePublished': DATE, 'mainEntityOfPage': url, 'author': {'@type': 'Organization', 'name': 'Dealux'},
                         'publisher': {'@type': 'Organization', 'name': 'Dealux', 'url': SITE}}, ensure_ascii=False).replace('</', '<\\/')
        seo = (f'\n<meta property="og:type" content="article">\n<meta property="og:site_name" content="Dealux">'
               f'\n<meta property="og:title" content="{t}">\n<meta property="og:description" content="{d}">'
               f'\n<meta property="og:url" content="{url}">\n<meta name="twitter:card" content="summary">'
               f'\n<script type="application/ld+json">{ld}</script>')
        h = re.sub(r'<title>.*?</title>', lambda _: f'<title>{t} — Dealux Journal</title>', tpl, count=1)
        h = re.sub(r'<meta name="description" content="[^"]*">', lambda _: f'<meta name="description" content="{d}">', h, count=1)
        h = re.sub(r'<link rel="canonical" href="[^"]*">', lambda _: f'<link rel="canonical" href="{url}">', h, count=1)
        h = h.replace('\n<link rel="icon"', seo + '\n<link rel="icon"', 1)
        h = re.sub(r'<span class="eyebrow">[^<]*· \d+ min read</span>',
                   lambda _: f'<span class="eyebrow">Amazon · {max(1, round(words / 230))} min read</span>', h, count=1)
        h = re.sub(r'(<article class="post">.*?)<h1>.*?</h1>', lambda m: f'{m.group(1)}<h1>{t}</h1>', h, count=1, flags=re.S)
        h = re.sub(r'<div class="post-body"><div class="post-content">.*?</div></div>\n  \n</article>',
                   lambda _: f'<div class="post-body"><div class="post-content">\n{body}\n</div></div>\n  \n</article>', h, count=1, flags=re.S)
        h = h.replace('<a class="muted" href="/journal/">← The Journal</a>', '<a class="muted" href="/journal/#amazon">← Amazon on the Journal</a>', 1)
        if body not in h or h.count('<aside class="post-sidebar') != 2:
            sys.exit(f'could not build {slug}')
        os.makedirs(f'journal/{slug}', exist_ok=True)
        open(f'journal/{slug}/index.html', 'w', encoding='utf-8').write(h)
        made.append((slug, title, desc))
    # Own section on the Journal page, above the general grid.
    idx = open('journal/index.html', encoding='utf-8').read()
    idx = re.sub(r'\n?<!-- amazon-journal -->.*?<!-- /amazon-journal -->\n?', '\n', idx, flags=re.S)
    cards = ''.join(f'<a class="card post-card" href="/journal/{s}/"><span class="eyebrow">Amazon</span><h3>{esc(t)}</h3>'
                    f'<p class="muted">{esc(d)}</p></a>' for s, t, d in made)
    sec = (f'\n<!-- amazon-journal --><section id="amazon" class="amazon-journal" style="margin:1.5rem 0 2rem">'
           f'<h2>Amazon: Prime, Audible, Kindle &amp; more</h2>'
           f'<p class="muted">{len(made)} guides to Amazon memberships, free trials, gift memberships and services. '
           f'<em>As an Amazon Associate, Dealux earns from qualifying purchases.</em></p>'
           f'<div class="grid">{cards}</div><h2 style="margin-top:2rem">All articles</h2></section><!-- /amazon-journal -->\n')
    idx = idx.replace('<form class="filter-bar" data-search-form>', sec + '<form class="filter-bar" data-search-form>', 1)
    open('journal/index.html', 'w', encoding='utf-8').write(idx)
    add_urls('sitemap-journal.xml', [f'{SITE}/journal/{s}/' for s, _, _ in made])
    print(len(made), 'Amazon journal articles')


# ---------------- Pinterest pins → Shop ----------------
BOARDS = {'shein-must-buys': 'SHEIN', 'fashion-nova-must-buys': 'Fashion Nova', 'etsy-must-haves': 'Etsy',
          'amazon-finds': 'Amazon', 'ebay-apparel': 'eBay', 'ebay-collectibles': 'eBay', 'ebooks': None, 'flexjobs': 'FlexJobs'}
DEPT = {'shein-must-buys': 'clothing', 'fashion-nova-must-buys': 'clothing', 'ebay-apparel': 'clothing'}


def ebook_brand(domain):
    if 'ds24' in domain or 'digistore' in domain:
        return 'Digistore24'
    return 'Digital eBooks & Courses'


def pin_title(desc):
    d = re.sub(r'#\w+', '', desc)
    d = re.sub(r'[\U0001F000-\U0001FAFF☀-➿️]', '', d).strip()
    first = re.split(r'(?<=[.!?])\s|\n|—| - ', d, maxsplit=1)[0].strip(' .,:;')
    if len(first) > 90:
        first = first[:90].rsplit(' ', 1)[0]
    return first or 'Featured find'


def shop(pins_dir):
    shards = {n: json.load(open(f'data/img/{n}.json', encoding='utf-8')) for n in range(SHARDS)}
    have_links = {r[5] for d in shards.values() for r in d.values() if len(r) > 5}
    slugs_all = [l.strip() for l in open('data/products.txt', encoding='utf-8') if l.strip()]
    have_slugs = set(slugs_all)
    new, by_brand, by_dept = [], {}, {}
    for board, brand in BOARDS.items():
        p = os.path.join(pins_dir, f'w-{board}.json')
        if not os.path.exists(p):
            continue
        for pin in json.load(open(p, encoding='utf-8'))['data']['pins']:
            link = html.unescape(pin.get('link') or '')
            if not link or link in have_links:
                continue
            have_links.add(link)
            desc = re.sub(r'\s+', ' ', html.unescape(pin.get('description') or '')).strip()
            b = brand or ebook_brand(pin.get('domain') or '')
            title = pin_title(desc)
            price = re.search(r'\$\s?(\d[\d,]*(?:\.\d\d)?)', desc)
            base = slugify(f'{b} {title}')[:80].strip('-')
            slug, i = base, 2
            while slug in have_slugs:
                slug, i = f'{base}-{i}', i + 1
            have_slugs.add(slug)
            img = (pin.get('images') or {}).get('564x', {}).get('url', '')
            rec = [title, price.group(1).replace(',', '') if price else '', 'USD', b, img, link, desc[:400]]
            shards[shard_of(slug)][slug] = rec
            new.append(slug)
            by_brand.setdefault(b, []).append(slug)
            if board in DEPT:
                by_dept.setdefault(DEPT[board], []).append(slug)
    if not new:
        print('No new Pinterest products'); return
    for n, d in shards.items():
        dump(f'data/img/{n}.json', d)
    open('data/products.txt', 'w', encoding='utf-8').write('\n'.join(slugs_all + new) + '\n')
    for dept, s in by_dept.items():
        p = f'data/list/dept-{dept}.json'
        if os.path.exists(p):
            dump(p, s + [x for x in json.load(open(p, encoding='utf-8')) if x not in s])
    # Brand pages, cloned from an existing brand page.
    src = open('shop/brand/amazon-renewed/index.html', encoding='utf-8').read()
    brand_urls = []
    for b, s in by_brand.items():
        key = slugify(b)
        lp = f'data/list/brand-{key}.json'
        old = json.load(open(lp, encoding='utf-8')) if os.path.exists(lp) else []
        allp = s + [x for x in old if x not in s]
        dump(lp, allp)
        n = len(allp)
        page = (src.replace('shop/brand/amazon-renewed/', f'shop/brand/{key}/')
                   .replace('brand-amazon-renewed.json', f'brand-{key}.json')
                   .replace('Amazon Renewed', esc(b))
                   .replace('Shop 2 ', f'Shop {n:,} ').replace('on Amazon.', f'from {esc(b)}, hand-picked by Dealux.')
                   .replace('<p class="muted">2 products</p>', f'<p class="muted">{n:,} products</p>'))
        os.makedirs(f'shop/brand/{key}', exist_ok=True)
        open(f'shop/brand/{key}/index.html', 'w', encoding='utf-8').write(page)
        brand_urls.append(f'{SITE}/shop/brand/{key}/')
    # "Shop by brand" sidebar links on every shop page.
    links = ''.join(f'<a class="side-link sub " href="/shop/brand/{slugify(b)}/">{esc(b)} <span class="muted">{len(json.load(open(f"data/list/brand-{slugify(b)}.json")))}</span></a>'
                    for b in sorted(by_brand, key=lambda x: -len(by_brand[x])))
    marker = '<summary><span class="side-link side-heading">Shop by brand</span></summary>\n    '
    for p in glob.glob('shop/**/index.html', recursive=True):
        h = open(p, encoding='utf-8').read()
        h2 = re.sub(r'<!-- pin-brands -->.*?<!-- /pin-brands -->', '', h, flags=re.S)
        if marker in h2:
            h2 = h2.replace(marker, marker + '<!-- pin-brands -->' + links + '<!-- /pin-brands -->', 1)
        if h2 != h:
            open(p, 'w', encoding='utf-8').write(h2)
    sm = 'sitemap-shop-products-pinterest.xml'
    old = open(sm, encoding='utf-8').read() if os.path.exists(sm) else '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n</urlset>\n'
    open(sm, 'w', encoding='utf-8').write(old)
    add_urls(sm, [f'{SITE}/shop/{s}' for s in new])
    index_sitemap(sm)
    add_urls('sitemap-shop.xml', brand_urls)
    print(len(new), 'Pinterest products;', {b: len(s) for b, s in by_brand.items()})


if __name__ == '__main__':
    journal(sys.argv[1])
    shop(sys.argv[2])
