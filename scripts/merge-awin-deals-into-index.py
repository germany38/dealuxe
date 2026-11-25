#!/usr/bin/env python3
"""Merge every Awin promotion deal page into /deals/ as filterable cards.

Usage: python3 scripts/merge-awin-deals-into-index.py

Scans deals/<slug>/index.html for Awin promotion pages (the ones built by
import-awin-promotions.py) and appends a card for each one that is not already on the
index. Existing cards are kept byte-for-byte. Awin links are used untouched: they already
carry awinmid/awinaffid, so affiliate attribution is preserved. Re-running is idempotent.
"""
import glob, html, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEALS = os.path.join(ROOT, 'deals')
IDX = os.path.join(DEALS, 'index.html')

# Reuse the department/brand rules from build-deals.py without running its side effects.
_src = open(os.path.join(ROOT, 'scripts', 'build-deals.py'), encoding='utf-8').read()
exec(_src.split('\ndef discount(', 1)[0].replace('TODAY = date.today().isoformat()', ''), globals())
e = lambda s: html.escape(s or '', quote=True)

MARK = 'Dealux may earn a commission from qualifying purchases through this link'

idx = open(IDX, encoding='utf-8').read()
head, rest = idx.split('<div class="grid deal-grid">', 1)
grid, tail = rest.rsplit('</main>', 1)

cards = []
for block in re.findall(r'<div class="card deal-card".*?\n</div>', grid, re.S):
    brand = html.unescape(re.search(r'<span class="eyebrow">(.*?)</span>', block).group(1)).rsplit(' · ', 1)[0].strip()
    href = re.search(r'<h3><a href="([^"]+)"', block).group(1)
    cards.append(dict(html=block, brand=brand, href=href, dept=None))
assert len(cards) == grid.count('<div class="card deal-card"'), 'card parse mismatch'
have = {c['href'] for c in cards}

added = 0
for path in glob.glob(os.path.join(DEALS, '*', 'index.html')):
    src = open(path, encoding='utf-8').read()
    if MARK not in src:
        continue
    slug = os.path.basename(os.path.dirname(path))
    href = f'/deals/{slug}/'
    if href in have:
        continue
    art = src.split('<article class="post deal-page">', 1)[1].split('</article>', 1)[0]
    eyebrow = html.unescape(re.search(r'<span class="eyebrow">(.*?)</span>', art).group(1))
    brand = eyebrow.rsplit(' · ', 1)[0].strip()
    is_voucher = eyebrow.endswith('Voucher')
    title = html.unescape(re.search(r'<h1>(.*?)</h1>', art, re.S).group(1)).strip()
    m = re.search(r'</h1>\n  <p>(.*?)</p>', art, re.S)
    desc = html.unescape(m.group(1)).strip() if m else ''
    m = re.search(r'<p class="deal-discount">(.*?)</p>', art)
    disc = html.unescape(m.group(1)).strip() if m else ''
    m = re.search(r'Categories: (.*?) · Available in', art)
    cats = [c.strip() for c in html.unescape(m.group(1)).split(',') if c.strip()] if m else []
    m = re.search(r'Valid until (\d{4}-\d{2}-\d{2})', art)
    expires = m.group(1) if m else ''
    url = html.unescape(re.search(r'<a class="btn btn-gold" href="([^"]+)" target="_blank"', art).group(1))
    dept = dept_for([c for c in cats if not re.search('marketplace', c, re.I)] + [title]) or dept_for(cats) or 'marketplaces'
    ctype = 'code' if is_voucher else 'deal'
    cta = f'Reveal code at {brand} →' if is_voucher else f'Get deal at {brand} →'
    bslug = slugify(brand)
    parts = [
        f'<div class="card deal-card" data-name="{e((title + " " + desc).lower())}" data-cats="{e("|".join(cats))}" '
        f'data-dept="{dept}" data-brand="{e(bslug)}" data-type="{ctype}">',
        f'  <span class="eyebrow">{e(brand)}</span>',
        f'  <h3><a href="{href}">{e(title)}</a></h3>',
    ]
    if desc and desc != title:
        parts.append(f'  <p class="muted">{e(desc)}</p>')
    if disc:
        parts.append(f'  <p class="deal-discount">{e(disc)}</p>')
    parts.append(f'  <p class="muted deal-meta">{e(DEPTS[dept])}</p>')
    if expires:
        parts.append(f'  <p class="muted deal-meta">Expires {expires}</p>')
    parts.append(f'  <a class="btn btn-gold" href="{e(url)}" target="_blank" rel="sponsored noopener">{e(cta)}</a>')
    parts.append('</div>')
    cards.append(dict(html='\n'.join(parts), brand=brand, href=href, dept=dept))
    have.add(href)
    added += 1

# Keep the same ordering build-deals.py uses: brand, then href.
cards.sort(key=lambda c: (c['brand'].lower(), c['href']))
n = len(cards)


def dept_of(c):
    if c['dept']:
        return c['dept']
    m = re.search(r'data-dept="([^"]+)"', c['html'])
    return m.group(1) if m else 'marketplaces'


def brand_slug_of(c):
    m = re.search(r'data-brand="([^"]+)"', c['html'])
    return m.group(1) if m else slugify(c['brand'])


dept_counts = {s: 0 for s in DEPTS}
brands = {}
for c in cards:
    dept_counts[dept_of(c)] += 1
    brands.setdefault(brand_slug_of(c), [c['brand'], 0])[1] += 1

dept_opts = ''.join(f'<option value="{s}">{e(DEPTS[s])} ({k})</option>' for s, k in dept_counts.items() if k)
brand_opts = ''.join(f'<option value="{e(s)}">{e(b)} ({k})</option>' for s, (b, k) in sorted(brands.items(), key=lambda x: x[1][0].lower()))
chips = ''.join(f'<a class="chip" href="/deals/?department={s}" data-dept-chip="{s}">{e(DEPTS[s])} <span class="muted">{k}</span></a>'
                for s, k in sorted(dept_counts.items(), key=lambda x: -x[1]) if k)

head, k1 = re.subn(r'content="\d+ working coupons, promo codes and deals from \d+ stores\."',
                   f'content="{n} working coupons, promo codes and deals from {len(brands)} stores."', head)
head, k2 = re.subn(r'<form class="filter-bar" data-deal-filter>.*?</form>\n(<nav class="dept-chips".*?</nav>\n)?', lambda m: (
    '<form class="filter-bar" data-deal-filter>\n'
    f'  <input type="search" name="q" placeholder="Search {n} deals or stores…" aria-label="Search deals">\n'
    f'  <select name="department" aria-label="Department"><option value="">All departments</option>{dept_opts}</select>\n'
    f'  <select name="brand" aria-label="Brand"><option value="">All brands</option>{brand_opts}</select>\n'
    '  <select name="type" aria-label="Type"><option value="">Codes &amp; deals</option><option value="code">Promo codes</option><option value="deal">Deals (no code)</option></select>\n'
    '</form>\n'
    f'<nav class="dept-chips" aria-label="Departments">{chips}</nav>\n'), head, flags=re.S)
head, k3 = re.subn(r'<p class="muted" data-result-count>\d+ deals</p>', f'<p class="muted" data-result-count>{n} deals</p>', head)
if not (k2 == 1 and k3 == 1):
    sys.exit(f'template markers not found (filter={k2}, count={k3}); aborting without writing')

with open(IDX, 'w', encoding='utf-8') as f:
    f.write(head + '<div class="grid deal-grid">\n' + '\n'.join(c['html'] for c in cards) + '\n</div>\n</main>' + tail)
print(f'added {added} Awin deal cards; index now has {n} cards from {len(brands)} brands')
