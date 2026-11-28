#!/usr/bin/env python3
"""Remove /deals/ entries that expire in 2026 or the first four months of 2027.

Usage: python3 scripts/prune-deals.py            # dry-run: report only
       python3 scripts/prune-deals.py --apply    # write changes

Deals with no listed expiry date are kept: they still send visitors to the store and
can earn commission. The cutoff is 2027-04-30 inclusive, so anything dated on or before
that day is dropped from the listing, the Awin data shards, the static detail pages and
the sitemaps. Re-running is idempotent.
"""
import glob, html, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEALS = os.path.join(ROOT, 'deals')
IDX = os.path.join(DEALS, 'index.html')
SHARDS = os.path.join(ROOT, 'data', 'awin-deals')
CUTOFF = '2027-04-30'
APPLY = '--apply' in sys.argv

# Reuse the department/brand rules from build-deals.py without running its side effects.
_src = open(os.path.join(ROOT, 'scripts', 'build-deals.py'), encoding='utf-8').read()
exec(_src.split('\ndef discount(', 1)[0].replace('TODAY = date.today().isoformat()', ''), globals())
e = lambda s: html.escape(s or '', quote=True)

EXPIRES = re.compile(r'Expires (\d{4}-\d{2}-\d{2})')
VALID = re.compile(r'Valid until (\d{4}-\d{2}-\d{2})')


def expired(text):
    m = EXPIRES.search(text) or VALID.search(text)
    return bool(m) and m.group(1) <= CUTOFF


# ---- index cards ----------------------------------------------------------
idx = open(IDX, encoding='utf-8').read()
head, rest = idx.split('<div class="grid deal-grid">', 1)
grid, tail = rest.rsplit('</main>', 1)

kept, dropped = [], 0
for block in re.findall(r'<div class="card deal-card".*?\n</div>', grid, re.S):
    if expired(block):
        dropped += 1
        continue
    brand = html.unescape(re.search(r'<span class="eyebrow">(.*?)</span>', block).group(1)).rsplit(' · ', 1)[0].strip()
    href = re.search(r'<h3><a href="([^"]+)"', block).group(1)
    m = re.search(r'data-dept="([^"]+)"', block)
    kept.append(dict(html=block, brand=brand, href=href, dept=m.group(1) if m else 'marketplaces'))

assert len(kept) + dropped == grid.count('<div class="card deal-card"'), 'card parse mismatch'

# ---- static detail pages --------------------------------------------------
static_dropped = []
for path in glob.glob(os.path.join(DEALS, '*', 'index.html')):
    if expired(open(path, encoding='utf-8').read()):
        static_dropped.append(path)

# ---- Awin shards ----------------------------------------------------------
shard_dropped = 0
new_shards = {}
for path in glob.glob(os.path.join(SHARDS, '*.json')):
    data = json.load(open(path, encoding='utf-8'))
    out = {slug: rec for slug, rec in data.items() if not expired(rec[4])}
    shard_dropped += len(data) - len(out)
    new_shards[path] = out

print(f'index cards: {len(kept)} kept, {dropped} dropped')
print(f'static pages: {len(static_dropped)} dropped')
print(f'awin shard records: {shard_dropped} dropped')
if not APPLY:
    sys.exit(0)

# Rebuild the index head counts/options/chips from the kept cards.
n = len(kept)
dept_counts = {s: 0 for s in DEPTS}
brands = {}
for c in kept:
    dept_counts[c['dept']] += 1
    bslug = re.search(r'data-brand="([^"]+)"', c['html'])
    bslug = bslug.group(1) if bslug else slugify(c['brand'])
    brands.setdefault(bslug, [c['brand'], 0])[1] += 1

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
    f.write(head + '<div class="grid deal-grid">\n' + '\n'.join(c['html'] for c in kept) + '\n</div>\n</main>' + tail)

for path in static_dropped:
    os.remove(path)
    try:
        os.rmdir(os.path.dirname(path))
    except OSError:
        pass

for path, out in new_shards.items():
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, separators=(',', ':'))

# ---- sitemaps --------------------------------------------------------------
# Drop sitemap URLs for pages that no longer exist (static) or whose shard record is gone.
live_shard_slugs = set()
for path in glob.glob(os.path.join(SHARDS, '*.json')):
    live_shard_slugs.update(json.load(open(path, encoding='utf-8')).keys())

for sm_name in glob.glob(os.path.join(ROOT, 'sitemap-deals-awin-*.xml')) + [os.path.join(ROOT, 'sitemap-deals.xml')]:
    sm = open(sm_name, encoding='utf-8').read()

    def keep_url(m):
        loc = m.group(1)
        if '/deals/promotions/' in loc:
            return m.group(0)
        slug = loc.rstrip('/').rsplit('/', 1)[-1]
        if slug in live_shard_slugs or os.path.isdir(os.path.join(DEALS, slug)):
            return m.group(0)
        return ''

    sm2 = re.sub(r'  <url>\s*<loc>([^<]+)</loc>.*?</url>\n', keep_url, sm, flags=re.S)
    if sm2 != sm:
        with open(sm_name, 'w', encoding='utf-8') as f:
            f.write(sm2)

print(f'wrote index with {n} deals; removed {len(static_dropped)} static pages; pruned {shard_dropped} shard records')
