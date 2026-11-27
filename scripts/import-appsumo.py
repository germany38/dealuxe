#!/usr/bin/env python3
"""Import the AppSumo (Awin) affiliate creative feed into the static shop.

Usage: python3 scripts/import-appsumo.py [path/to/appsumo.csv]

Every unique AppSumo creative becomes a shop item at /shop/appsumo-<name>-<ad id>,
keeping AppSumo/Awin's affiliate click URL, product name and description intact.
Items are filed under the AppSumo brand page and the Software & Apps type. The
product index, brand page, brand directory and a dedicated product sitemap are
updated in place, so re-running with the same feed is a no-op.

The feed gives Awin a per-creative click URL but no hosted image, so each item's
og:image is read once from its AppSumo landing page (the same image AppSumo shows
when the link is shared) and reused on later runs.
"""
import csv, html, importlib.util, os, re, sys, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location('cj', os.path.join(HERE, 'import-cj-links.py'))
cj = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cj)

BRAND = 'AppSumo'
DEPT, TYPE = 'electronics', 'software-apps'
DEFAULT_FEED = 'data/feeds/dealux-appsumo-deduplicated.csv'
OG_RE = re.compile(r'<meta[^>]+property=["\']og:image["\'][^>]*?content=["\']([^"\']+)', re.I | re.S)
OG_RE2 = re.compile(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]*?property=["\']og:image["\']', re.I | re.S)
# AppSumo lists the lifetime-deal tiers as JSON prices; the lowest is the "from" price.
PRICE_RE = re.compile(r'"price"\s*:\s*"?([0-9]+(?:\.[0-9]+)?)"?')
CURRENCY_RE = re.compile(r'"priceCurrency"\s*:\s*"([A-Z]{3})"')
OGTYPE_RE = re.compile(r'og:type["\'][^>]*?content=["\']([^"\']+)', re.I | re.S)
# Awin labels many creatives "<product> - logo", "<product> 300x250" etc. Those are
# the same product, so the creative wording is stripped to leave the product name.
CREATIVE_RE = re.compile(r'[\s\-–|:_]*(logo|banner|skyscraper|leaderboard|rectangle|square|button|image|text\s*link|deep\s*link|creative)\s*\d*\s*$', re.I)


def clean_name(name):
    n = cj.clean_text(cj.SIZE_RE.sub(' ', name or ''))
    for _ in range(3):
        n = CREATIVE_RE.sub('', n)
        n = re.sub(r'\s*[-–|:_]+\s*$', '', n).strip()
    n = re.sub(r'\s+', ' ', n).strip()
    return n or cj.clean_text(name)


def fetch_meta(url):
    """Return the og:image and lowest lifetime-deal price for a landing page."""
    out = {'image': '', 'price': '', 'currency': ''}
    if not url:
        return out
    html = ''
    for _ in range(3):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (compatible; DealuxBot/1.0)'})
            with urllib.request.urlopen(req, timeout=20) as r:
                html = r.read(300000).decode('utf-8', 'ignore')
            break
        except Exception:
            html = ''
    if not html:
        return out
    m = OG_RE.search(html) or OG_RE2.search(html)
    if m:
        src = m.group(1).strip()
        if src.startswith('//'):
            src = 'https:' + src
        elif src.startswith('/'):
            src = urllib.parse.urljoin(url, src)
        out['image'] = src
    # Prices are only taken from real product/deal pages (og:type "article"); the
    # homepage, collections and search pages also list prices for other deals.
    ogtype = OGTYPE_RE.search(html)
    if ogtype and ogtype.group(1).strip().lower() == 'article':
        prices = [p for p in (float(x) for x in PRICE_RE.findall(html)) if p > 0]
        if prices:
            out['price'] = f'{min(prices):.2f}'
            cur = CURRENCY_RE.search(html)
            out['currency'] = cur.group(1) if cur else 'USD'
    return out


def build_items(path, refresh=False):
    rows = list(csv.DictReader(open(path, encoding='utf-8-sig')))
    shards = {n: cj.read_json(f'data/img/{n}.json', {}) for n in range(cj.IMG_SHARDS)}
    existing = {} if refresh else {s: rec for rec in shards.values() for s, rec in rec.items()}
    items, seen = [], set()
    for r in rows:
        adid = (r.get('AdId') or '').strip()
        link = (r.get('TrackingLink') or '').strip()
        name = clean_name(r.get('Name', ''))
        if not adid or not link or not name or adid in seen:
            continue
        seen.add(adid)
        slug = ('appsumo-' + cj.slugify(name)[:70].strip('-') + '-' + adid).strip('-')
        desc = cj.clean_text(r.get('Description', ''))
        if desc.lower() == name.lower():
            desc = ''
        old = existing.get(slug)
        items.append(dict(slug=slug, name=name, link=link, desc=desc,
                          landing=(r.get('LandingPage') or '').strip(),
                          image=old[4] if old and len(old) > 4 else '',
                          price=old[1] if old and len(old) > 1 else '',
                          currency=old[2] if old and len(old) > 2 else ''))
    fetch = sorted({i['landing'] for i in items if i['landing'] and not (i['image'] and i['price'])})
    print(f'{len(items)} unique AppSumo items; fetching {len(fetch)} product pages…')
    metas = {}
    with ThreadPoolExecutor(max_workers=16) as ex:
        for fut, url in ((ex.submit(fetch_meta, u), u) for u in fetch):
            metas[url] = fut.result()
    for i in items:
        meta = metas.get(i['landing'], {})
        i['image'] = i['image'] or meta.get('image', '')
        i['price'] = i['price'] or meta.get('price', '')
        i['currency'] = i['currency'] or meta.get('currency', '')
    return items


def add_brand_entry(name, slug, count):
    """Insert or refresh one brand row in brands/index.html, keeping the list sorted
    by product count and leaving every other row (even oddly-formed ones) untouched."""
    p = 'brands/index.html'
    h = open(p, encoding='utf-8').read()
    start = h.index('<ul class="brand-list">') + len('<ul class="brand-list">')
    end = h.index('</ul>', start)
    body = h[start:end]
    li = (f'<li data-name="{slug}"><a href="/shop/brand/{slug}/">{html.escape(name)}</a>'
          f'<span class="muted">{count:,} products</span></li>')
    if f'<li data-name="{slug}">' in body:
        body = re.sub(r'<li data-name="%s">.*?</li>' % re.escape(slug), lambda m: li, body, count=1, flags=re.S)
    else:
        entry = re.compile(r'<li data-name="[^"]*"><a href="/shop/brand/[^/]*/">.*?</a>'
                           r'<span class="muted">([\d,]+) products?</span></li>', re.S)
        off = len(body)
        for m in entry.finditer(body):
            if int(m.group(1).replace(',', '')) < count:
                off = m.start()
                break
        body = body[:off] + li + body[off:]
    n = len(re.findall(r'<li data-name="[^"]*">', body))
    h = h[:start] + body + h[end:]
    h = re.sub(r'placeholder="Search [\d,]+ brands…"', f'placeholder="Search {n:,} brands…"', h)
    h = re.sub(r'data-result-count>[\d,]+ brands<', f'data-result-count>{n:,} brands<', h)
    h = re.sub(r'(<meta name="description" content="[^"]*?)[\d,]+( brands)',
               lambda mm: f'{mm.group(1)}{n:,}{mm.group(2)}', h, count=1)
    open(p, 'w', encoding='utf-8').write(h)
    return n


def main(path, refresh=False):
    items = build_items(path, refresh)
    slugs = [i['slug'] for i in items]

    # ---- purge any previously imported AppSumo items, then write the current set,
    # so re-running after a feed change is a clean sync rather than a growing append ----
    shards = {n: cj.read_json(f'data/img/{n}.json', {}) for n in range(cj.IMG_SHARDS)}
    for n in shards:
        shards[n] = {k: v for k, v in shards[n].items() if not k.startswith('appsumo-')}
    for i in items:
        shards[cj.shard_of(i['slug'])][i['slug']] = [i['name'], i['price'], i['currency'] or 'USD', BRAND, i['image'], i['link'], i['desc']]
    for n, data in shards.items():
        cj.write_json(f'data/img/{n}.json', data)

    for p in ('data/products.txt', 'products.txt'):
        lines = [s for s in open(p, encoding='utf-8').read().splitlines() if not s.startswith('appsumo-')]
        with open(p, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines + slugs) + '\n')

    # ---- lists: brand, type and department ----
    def sync_list(name, new):
        p = f'data/list/{name}.json'
        lst = [s for s in cj.read_json(p, []) if not s.startswith('appsumo-')]
        have = set(lst)
        lst += [s for s in new if s not in have]
        cj.write_json(p, lst)
        return len(lst)

    count = sync_list('brand-appsumo', slugs)
    sync_list(f'type-{TYPE}', slugs)
    sync_list(f'dept-{DEPT}', slugs)

    # ---- AppSumo brand landing page ----
    template = open('shop/brand/3w/index.html', encoding='utf-8').read()
    template = re.sub(r'(<summary><span class="side-link side-heading">Shop by brand</span></summary>).*?(</details>)',
                      r'\1<a class="side-link sub" href="/brands/">Browse all brands</a>\2', template, flags=re.S)
    h = cj.page_from(template, '/shop/brand/appsumo/', 'AppSumo',
                     f'Shop {count:,} AppSumo software lifetime deals and offers.',
                     'Shop AppSumo', f'{count:,} products', '/data/list/brand-appsumo.json')
    cj.write_page('shop/brand/appsumo/index.html', h)

    # ---- brand affiliate link + brand directory ----
    for p in ('data/brands.json', 'brands.json'):
        lst = cj.read_json(p, [])
        have = {cj.slugify(b[0]) for b in lst}
        if cj.slugify(BRAND) not in have:
            lst += [[BRAND, items[0]['link']]]
            lst.sort(key=lambda b: b[0].lower())
            cj.write_json(p, lst)
    add_brand_entry(BRAND, 'appsumo', count)

    # ---- sitemaps ----
    today = cj.TODAY.isoformat()
    sm = 'sitemap-appsumo-products.xml'
    body = ''.join(f'  <url><loc>{cj.SITE}/shop/{s}</loc><lastmod>{today}</lastmod></url>\n' for s in slugs)
    open(sm, 'w', encoding='utf-8').write(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + body + '</urlset>\n')
    idx = open('sitemap-index.xml', encoding='utf-8').read()
    loc = f'<loc>{cj.SITE}/{sm}</loc>'
    if loc not in idx:
        idx = idx.replace('</sitemapindex>', f'  <sitemap>{loc}<lastmod>{today}</lastmod></sitemap>\n</sitemapindex>')
        open('sitemap-index.xml', 'w', encoding='utf-8').write(idx)
    shop_sm = open('sitemap-shop.xml', encoding='utf-8').read()
    brand_loc = f'{cj.SITE}/shop/brand/appsumo/'
    if brand_loc not in shop_sm:
        open('sitemap-shop.xml', 'w', encoding='utf-8').write(
            shop_sm.replace('</urlset>', f'<url><loc>{brand_loc}</loc></url>\n</urlset>'))
    print(f'AppSumo: {count:,} products, brand page /shop/brand/appsumo/, sitemap {sm}')


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('-')]
    main(args[0] if args else DEFAULT_FEED, refresh='--refresh' in sys.argv)
