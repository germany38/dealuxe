#!/usr/bin/env python3
"""Import an Awin promotions CSV as indexable deal pages.

Usage: python3 scripts/import-awin-promotions.py promotions.csv

Writes deals/<slug>/index.html per active promotion, per-store hubs under
deals/promotions/<store>/, an A-Z directory at deals/promotions/, sitemap-deals-awin-N.xml
files and the matching sitemap-index.xml entries. Re-running is idempotent.
"""
import csv, html, json, os, re, sys, unicodedata
from collections import defaultdict
from datetime import datetime, date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEALS = os.path.join(ROOT, 'deals')
SITE = 'https://dealuxapp.com'
TODAY = date.today().isoformat()
e = lambda s: html.escape(s or '', quote=True)


def slugify(s):
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+', '-', s).strip('-')


def pdate(s):
    try:
        return datetime.strptime(s[:10], '%d/%m/%Y').date()
    except ValueError:
        return None


def clean_name(n):
    return re.sub(r'\s+(US|UK|WW|GB|DE|FR|ES|IT|NL|Many GEOs)$', '', n).strip() or n


def discount(*texts):
    for t in texts:
        m = re.search(r'(\d{1,2})\s?%', t or '')
        if m:
            return m.group(1) + '% off'
        m = re.search(r'([$€£]\s?\d[\d,.]*)\s*(?:off|discount|coupon)|(?:save|get)\s+([$€£]\s?\d[\d,.]*)', t or '', re.I)
        if m:
            return (m.group(1) or m.group(2)).replace(' ', '') + ' off'
    return ''


tpl = open(os.path.join(DEALS, 'aliexpress-ww-70-322183', 'index.html'), encoding='utf-8').read()
tpl_head, tpl_rest = tpl.split('<article class="post deal-page">', 1)
tpl_tail = tpl_rest.split('</article>', 1)[1]


def page(title, meta, canonical, body, robots='index, follow, max-image-preview:large'):
    h = tpl_head
    h = re.sub(r'<title>.*?</title>', lambda m: f'<title>{e(title)} — Dealux Deals</title>', h, flags=re.S)
    h = re.sub(r'<meta name="description" content="[^"]*">', lambda m: f'<meta name="description" content="{e(meta)}">', h)
    h = re.sub(r'<link rel="canonical" href="[^"]*">', lambda m: f'<link rel="canonical" href="{canonical}">', h)
    h = re.sub(r'<meta name="robots" content="[^"]*">', lambda m: f'<meta name="robots" content="{robots}">', h)
    return h + body + tpl_tail


def write(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)


promos, stores = [], defaultdict(list)
for r in csv.DictReader(open(sys.argv[1], encoding='utf-8-sig')):
    end = pdate(r['Ends'])
    url = r['Deeplink Tracking'].strip()
    title = (r['Title'] or r['Description']).strip()
    if (end and end < date.today()) or not url.startswith('http') or not title:
        continue
    brand = clean_name(r['Advertiser'].strip())
    pid = r['Promotion ID'].strip()
    bslug = slugify(brand) or 'store-' + r['Advertiser ID']
    slug = f"{bslug[:30].strip('-')}-{slugify(title)[:50].strip('-')}-{pid}".replace('--', '-')
    promos.append(dict(r=r, brand=brand, bslug=bslug, slug=slug, title=title, url=url, end=end))
    stores[bslug].append(promos[-1])

for p in promos:
    r, brand, title = p['r'], p['brand'], p['title']
    desc = (r['Description'] or '').strip()
    terms = (r['Terms'] or '').strip()
    code = r['Code'].strip()
    has_code = r['Type'] == 'voucher'
    real_code = code if code and set(code) != {'*'} else ''
    disc = discount(title, desc)
    cats = ', '.join(c.strip() for c in r['Categories'].split(',') if c.strip())[:200]
    region = r['Regions'].strip()
    cta = f'Reveal code at {brand} →' if has_code else f'Get deal at {brand} →'
    start, end = pdate(r['Starts']), p['end']
    valid = ('' if not end or end.year >= 2029 else f'Valid until {end.isoformat()}.')
    code_html = (f'<p class="promo-code">Code: <b>{e(real_code)}</b> <button type="button" class="copy-code" data-code="{e(real_code)}">Copy</button></p>'
                 if real_code else
                 ('<p class="muted">This is a voucher offer: click the button to open the store and reveal or apply the code.</p>' if has_code else
                  '<p class="muted">No code needed — the discount applies through the link.</p>'))
    meta = f'{brand} {"voucher" if has_code else "promotion"}: {desc or title}'
    meta = (meta[:152] + '…') if len(meta) > 155 else meta
    body = ('<article class="post deal-page">\n  <a class="muted" href="/deals/">← All deals</a> · '
            f'<a class="muted" href="/deals/promotions/{e(p["bslug"])}/">All {e(brand)} offers</a>\n'
            f'  <span class="eyebrow">{e(brand)} · {"Voucher" if has_code else "Promotion"}</span>\n  <h1>{e(title)}</h1>\n'
            + (f'  <p class="deal-discount">{e(disc)}</p>\n' if disc else '')
            + (f'  <p>{e(desc)}</p>\n' if desc and desc != title else '')
            + f'  {code_html}\n'
            + (f'  <p class="muted">Terms: {e(terms)}</p>\n' if terms else '')
            + f'  <p class="muted">{"Categories: " + e(cats) + " · " if cats else ""}Available in: {e(region)}'
              + (f' · {valid}' if valid else '') + '</p>\n'
            f'  <p><a class="btn btn-gold" href="{e(p["url"])}" target="_blank" rel="sponsored noopener">{e(cta)}</a></p>\n'
            '  <p class="muted"><em>Dealux may earn a commission from qualifying purchases through this link, at no extra cost to you. '
            'Offers can change, so always confirm the final terms on the store\'s site.</em></p>\n')
    write(os.path.join(DEALS, p['slug'], 'index.html'), page(f'{brand}: {title}', meta, f'{SITE}/deals/{p["slug"]}/', body))

# ---- store hubs ----------------------------------------------------------
for bslug, items in stores.items():
    brand = items[0]['brand']
    lis = ''.join(f'<li><a href="/deals/{i["slug"]}/">{e(i["title"])}</a></li>\n' for i in items)
    cta = items[0]['url']
    body = (f'<article class="post deal-page">\n  <a class="muted" href="/deals/promotions/">← All stores</a>\n'
            f'  <h1>{e(brand)} deals, vouchers &amp; promotions</h1>\n'
            f'  <p>{len(items)} current {e(brand)} offer{"s" if len(items) != 1 else ""}, updated {TODAY}. Pick an offer below to see its terms, or head straight to the store.</p>\n'
            f'  <p><a class="btn btn-gold" href="{e(cta)}" target="_blank" rel="sponsored noopener">Shop {e(brand)} →</a></p>\n'
            f'  <ul>\n{lis}  </ul>\n'
            '  <p class="muted"><em>Dealux may earn a commission from qualifying purchases, at no extra cost to you.</em></p>\n')
    write(os.path.join(DEALS, 'promotions', bslug, 'index.html'),
          page(f'{brand} deals & promotions', f'{len(items)} current {brand} deals, vouchers and promotions with terms and links to the store.',
               f'{SITE}/deals/promotions/{bslug}/', body))

# ---- A-Z directory -------------------------------------------------------
groups = defaultdict(list)
for bslug, items in sorted(stores.items(), key=lambda x: x[1][0]['brand'].lower()):
    ch = items[0]['brand'][:1].upper()
    groups[ch if ch.isalpha() and ch.isascii() else '#'].append((bslug, items[0]['brand'], len(items)))
sections = ''.join(f'<h2 id="{k.lower() if k != "#" else "other"}">{k}</h2>\n<ul class="store-list">' +
                   ''.join(f'<li><a href="/deals/promotions/{b}/">{e(n)}</a> <span class="muted">({c})</span></li>' for b, n, c in v) + '</ul>\n'
                   for k, v in sorted(groups.items()))
body = ('<article class="post deal-page">\n  <a class="muted" href="/deals/">← All deals</a>\n'
        f'  <h1>Store promotions &amp; vouchers</h1>\n  <p>Browse {len(promos):,} current offers from {len(stores):,} stores, courtesy of Awin.</p>\n'
        + sections)
write(os.path.join(DEALS, 'promotions', 'index.html'),
      page('Store promotions & vouchers', f'Browse {len(promos):,} current deals, vouchers and promotions from {len(stores):,} stores.',
           f'{SITE}/deals/promotions/', body))

# ---- deals index link ------------------------------------------------------
idx_path = os.path.join(DEALS, 'index.html')
idx = open(idx_path, encoding='utf-8').read()
idx = re.sub(r'<p class="promo-link">.*?</p>\n', '', idx)
idx = idx.replace('<form class="filter-bar" data-deal-filter>',
                  f'<p class="promo-link"><a class="btn btn-gold" href="/deals/">Browse all deals &amp; vouchers →</a></p>\n'
                  '<form class="filter-bar" data-deal-filter>', 1)
write(idx_path, idx)

# ---- sitemaps --------------------------------------------------------------
urls = [f'{SITE}/deals/promotions/'] + [f'{SITE}/deals/promotions/{b}/' for b in stores] + [f'{SITE}/deals/{p["slug"]}/' for p in promos]
names = []
for n, off in enumerate(range(0, len(urls), 10000), 1):
    name = f'sitemap-deals-awin-{n}.xml'
    names.append(name)
    write(os.path.join(ROOT, name), '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
          + ''.join(f'  <url><loc>{u}</loc><lastmod>{TODAY}</lastmod></url>\n' for u in urls[off:off + 10000]) + '</urlset>\n')
sp = os.path.join(ROOT, 'sitemap-index.xml')
s = re.sub(r'^\s*<sitemap><loc>[^<]*sitemap-deals-awin-\d+\.xml</loc>.*?</sitemap>\n', '', open(sp, encoding='utf-8').read(), flags=re.M)
s = s.replace('</sitemapindex>', ''.join(f'  <sitemap><loc>{SITE}/{n}</loc></sitemap>\n' for n in names) + '</sitemapindex>')
write(sp, s)
print(len(promos), 'promotions,', len(stores), 'stores,', len(names), 'sitemaps')
