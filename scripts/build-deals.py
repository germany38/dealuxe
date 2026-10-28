#!/usr/bin/env python3
"""Rebuild /deals/ with department + brand categorisation and import coupon CSV feeds.

Usage: python3 scripts/build-deals.py [coupons.csv ...]

Existing hand-built deal cards in deals/index.html are kept (their affiliate links are
copied verbatim). Rows from the CSV feeds become new cards + detail pages; their
tracking_url is used untouched so affiliate attribution is preserved. Re-running is
idempotent: imported cards carry data-uuid and are regenerated from the CSV.
"""
import csv, html, os, re, sys, unicodedata
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEALS = os.path.join(ROOT, 'deals')
TODAY = date.today().isoformat()

DEPTS = {  # slug -> label (mirrors /shop/department/)
    'electronics': 'Electronics & Appliances', 'cameras-photo': 'Cameras & Photo',
    'clothing': 'Clothing', 'shoes-bags': 'Shoes, Bags & Accessories', 'jewelry': 'Jewelry',
    'hair-beauty': 'Hair & Beauty', 'wellness': 'Health & Wellness', 'home-garden': 'Home & Garden',
    'home-decor': 'Home Décor', 'automotive': 'Automotive', 'toys-hobbies': 'Toys, Hobbies & Kids',
    'sports-outdoors': 'Sports & Outdoors', 'food-snacks': 'Food & Snacks', 'office': 'Office & Stationery',
    'education': 'Books & Education', 'experiences': 'Tickets & Experiences', 'travel': 'Travel & Connectivity',
    'services': 'Services & Finance', 'marketplaces': 'Marketplaces & More',
}
# Ordered keyword rules: first match wins. Applied to category names, then to deal titles.
RULES = [
    ('cameras-photo', r'photograph|camera|drone'),
    ('hair-beauty', r'beauty|skin|cosmetic|hair care|nail|makeup|deodorant|personal care'),
    ('wellness', r'wellness|herb|supplement|health|weight|vitamin|fitness|nutrition|medicine|first aid|pharmacy'),
    ('jewelry', r'jewel|watch|moonstone|emerald|diamond|ring\b'),
    ('shoes-bags', r'shoe|footwear|bag|accessor|luggage|glasses'),
    ('clothing', r'cloth|fashion|apparel|designer|style|dress|prom|wedding'),
    ('experiences', r'museum|galler|amusement|theme park|attraction|day trip|zoo|aquarium|ticket|live music'),
    ('travel', r'travel|bed & breakfast|tour|internet service|esim'),
    ('automotive', r'motorcycle|auto|car\b|scooter'),
    ('electronics', r'electronic|smartphone|computer|peripheral|laptop|tablet|appliance|power|energy|smart home|'
                    r'networking|gaming|keyboard|phone|pc\b|battery|flashlight|solar|humidifier'),
    ('toys-hobbies', r'toy|game|hobb|kid|bab|lego|party|skateboard|pet\b'),
    ('sports-outdoors', r'sport|outdoor|camping|canoe|kayak|fishing'),
    ('home-decor', r'interior|decor|candle|gift|flower'),
    ('home-garden', r'home|garden|woodwork|diy|tool|household|utilit|kitchen|house'),
    ('food-snacks', r'food|grocery|snack'),
    ('office', r'office|stationery'),
    ('education', r'book|education|learning'),
    ('services', r'financ|insurance|bank|job|freelance|service|logistic|lease|transport|it and'),
    ('marketplaces', r'marketplace|chinese'),
]
MERCHANT_DEPT = {  # fallback when category/title keywords are generic ("Coupons and Discounts")
    'SHOP SIMON': 'clothing', 'Herbspro US': 'wellness', 'Gshopper': 'electronics', 'Harfington US': 'home-garden',
    'ZAPAKA VINTAGE, Inc. US': 'clothing', 'Tiqets': 'experiences', 'BLUETTI US': 'electronics',
    'FaceTheFuture.co.uk US': 'hair-beauty', 'HONGKONG YINTATECH NETWORK CO., LIMITED US': 'home-garden',
    'Olight USA': 'sports-outdoors', 'Willwork Jewelry US': 'jewelry', 'Banggood WW': 'electronics',
    'LG': 'electronics', 'STYLEVANA': 'hair-beauty', 'AliExpress WW': 'marketplaces', 'LEGO': 'toys-hobbies',
}
BRAND_NAME = {
    'HONGKONG YINTATECH NETWORK CO., LIMITED US': 'Hernest', 'ZAPAKA VINTAGE, Inc. US': 'Zapaka Vintage',
    'FaceTheFuture.co.uk US': 'Face the Future', 'SHOP SIMON': 'Shop Simon', 'BLUETTI US': 'BLUETTI',
    'STYLEVANA': 'Stylevana', 'Olight USA': 'Olight',
}

e = lambda s: html.escape(s or '', quote=True)


def slugify(s):
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+', '-', s).strip('-')


def dept_for(texts):
    for t in texts:
        for slug, rx in RULES:
            if re.search(rx, t or '', re.I):
                return slug
    return None


def brand_name(m):
    return BRAND_NAME.get(m) or re.sub(r'\s+(US|WW|UK|UA|Many GEOs)$', '', m).strip()


def discount(*texts):
    for t in texts:
        m = re.search(r'(\d{1,2})\s?%', t or '')
        if m: return m.group(1) + '% off'
        m = re.search(r'(?:save|get|extra)\s+([$€£]\s?\d[\d,]*)|([$€£]\s?\d[\d,]*)\s+(?:off|coupon|discount)', t or '', re.I)
        if m: return (m.group(1) or m.group(2)).replace(' ', '') + ' off'
    return ''


# ---- existing cards -------------------------------------------------------
idx_path = os.path.join(DEALS, 'index.html')
idx = open(idx_path, encoding='utf-8').read()
head, rest = idx.split('<div class="grid deal-grid">', 1)
grid, tail = rest.rsplit('</main>', 1)
cards = []  # dicts: html, dept, brand, slug, sort
for block in re.findall(r'<div class="card deal-card".*?\n</div>', grid, re.S):
    if 'data-uuid=' in block:
        continue  # imported earlier; regenerated from CSV below
    cats = html.unescape(re.search(r'data-cats="([^"]*)"', block).group(1)).split('|')
    title = html.unescape(re.search(r'<h3><a[^>]*>(.*?)</a>', block, re.S).group(1))
    brand = html.unescape(re.search(r'<span class="eyebrow">(.*?)</span>', block).group(1)).split(' · ')[0].strip()
    brand = brand_name(brand)
    dept = dept_for([c for c in cats if not re.search('marketplace', c, re.I)] + [title]) or dept_for(cats) or 'marketplaces'
    block = re.sub(r' data-dept="[^"]*" data-brand="[^"]*"', '', block)
    block = block.replace(' data-type=', f' data-dept="{dept}" data-brand="{e(slugify(brand))}" data-type=', 1)
    href = re.search(r'<h3><a href="([^"]+)"', block).group(1)
    cards.append(dict(html=block, dept=dept, brand=brand, href=href, imported=False))

# ---- CSV rows -------------------------------------------------------------
TEMPLATE = open(os.path.join(DEALS, 'abebooks-many-geos-25-great-book-club-books-443772', 'index.html'), encoding='utf-8').read()
tpl_head, tpl_rest = TEMPLATE.split('<article class="post deal-page">', 1)
tpl_tail = tpl_rest.split('</article>', 1)[1]

seen = set()
for path in sys.argv[1:]:
    for r in csv.DictReader(open(path, encoding='utf-8-sig')):
        if r['uuid'] in seen or r.get('is_active') == 'False' or (r['end_time'] and r['end_time'][:10] < TODAY):
            continue
        if not r['tracking_url'].startswith('http'):
            continue
        seen.add(r['uuid'])
        brand = brand_name(r['merchant_name'])
        dept = dept_for([r['coupon_category_name'], r['name']]) or MERCHANT_DEPT.get(r['merchant_name']) or 'marketplaces'
        if r['coupon_category_name'] in ('Coupons and Discounts', 'Sales', 'Sales and Promotions', 'Shopping',
                                         'Retail Industry', 'Holiday Shopping', 'Holiday', 'Holidays', 'Frugal Living', 'Logistics', 'Consumer Issues'):
            dept = dept_for([r['name']]) or MERCHANT_DEPT.get(r['merchant_name']) or dept
        code = r['promocode'].strip() if r['type'] == 'coupon' else ''
        title = r['name'].strip()
        desc = (r['en_description'] or '').strip()
        disc = discount(title, r['en_user_value'], desc)
        slug = f"{slugify(brand)}-{slugify(title)[:60].strip('-')}-{r['uuid'][:6]}"
        href = f'/deals/{slug}/'
        url = r['tracking_url'].strip()
        bslug = slugify(brand)
        cta = f'Use code at {e(brand)} →' if code else f'Get deal at {e(brand)} →'
        exp = '' if r['end_time'][:4] >= '2029' else f'<p class="muted deal-meta">Expires {r["end_time"][:10]}</p>'
        code_html = f'<p class="promo-code">Code: <b>{e(code)}</b> <button type="button" class="copy-code" data-code="{e(code)}">Copy</button></p>' if code else ''
        card = (f'<div class="card deal-card" data-uuid="{e(r["uuid"])}" data-name="{e((brand + " " + title + " " + code).lower())}" '
                f'data-cats="{e(r["coupon_category_name"])}" data-dept="{dept}" data-brand="{e(bslug)}" data-type="{"code" if code else "deal"}">\n'
                f'  <span class="eyebrow">{e(brand)}</span>\n'
                f'  <h3><a href="{href}">{e(title)}</a></h3>\n'
                + (f'  <p class="deal-discount">{e(disc)}</p>\n' if disc else '')
                + (f'  <p class="muted">{e(desc)}</p>\n' if desc and desc != title else '')
                + (f'  {code_html}\n' if code_html else '')
                + f'  <p class="muted deal-meta">{e(DEPTS[dept])}</p>\n'
                + (f'  {exp}\n' if exp else '')
                + f'  <a class="btn btn-gold" href="{e(url)}" target="_blank" rel="sponsored noopener">{cta}</a>\n</div>')
        cards.append(dict(html=card, dept=dept, brand=brand, href=href, imported=True))

        page_title = f'{brand}: {title}'
        meta = f'{brand} {"coupon" if code else "deal"} — {desc or title}'[:300]
        ph = tpl_head
        ph = re.sub(r'<title>.*?</title>', f'<title>{e(page_title)} — Dealux Deals</title>', ph)
        ph = re.sub(r'<meta name="description" content="[^"]*">', f'<meta name="description" content="{e(meta)}">', ph)
        ph = re.sub(r'<link rel="canonical" href="[^"]*">', f'<link rel="canonical" href="https://dealuxapp.com{href}">', ph)
        article = (f'<article class="post deal-page">\n  <a class="muted" href="/deals/">← All deals</a>\n'
                   f'  <span class="eyebrow">{e(brand)} · {"Coupon" if code else "Deal"}</span>\n  <h1>{e(title)}</h1>\n'
                   + (f'  <p class="deal-discount">{e(disc)}</p>\n' if disc else '')
                   + (f'  <p>{e(desc)}</p>\n' if desc else '')
                   + (f'  {code_html}\n' if code else '  <p class="muted">No code needed — the discount applies through the link.</p>\n')
                   + (f'  <p class="muted">Conditions: {e(r["special_conditions"])}</p>\n' if r.get('special_conditions') else '')
                   + f'  <p class="muted">Department: <a href="/deals/?department={dept}">{e(DEPTS[dept])}</a> · '
                     f'Brand: <a href="/deals/?brand={e(bslug)}">{e(brand)}</a> · Store: {e(r["merchant_domain"])}</p>\n'
                   + (f'  {exp}\n' if exp else '')
                   + f'  <p><a class="btn btn-gold" href="{e(url)}" target="_blank" rel="sponsored noopener">{cta}</a></p>\n</article>')
        os.makedirs(os.path.join(DEALS, slug), exist_ok=True)
        with open(os.path.join(DEALS, slug, 'index.html'), 'w', encoding='utf-8') as f:
            f.write(ph + article + tpl_tail)

# ---- index page -----------------------------------------------------------
cards.sort(key=lambda c: (c['brand'].lower(), c['href']))
n = len(cards)
dept_counts = {s: sum(1 for c in cards if c['dept'] == s) for s in DEPTS}
brands = {}
for c in cards:
    brands.setdefault(slugify(c['brand']), [c['brand'], 0])[1] += 1

dept_opts = ''.join(f'<option value="{s}">{e(DEPTS[s])} ({k})</option>' for s, k in dept_counts.items() if k)
brand_opts = ''.join(f'<option value="{e(s)}">{e(b)} ({k})</option>' for s, (b, k) in sorted(brands.items(), key=lambda x: x[1][0].lower()))
chips = ''.join(f'<a class="chip" href="/deals/?department={s}" data-dept-chip="{s}">{e(DEPTS[s])} <span class="muted">{k}</span></a>'
                for s, k in sorted(dept_counts.items(), key=lambda x: -x[1]) if k)

head = re.sub(r'content="\d+ working coupons, promo codes and deals from \d+ stores\."',
              f'content="{n} working coupons, promo codes and deals from {len(brands)} stores."', head)
head = re.sub(r'<form class="filter-bar" data-deal-filter>.*?</form>\n(<nav class="dept-chips".*?</nav>\n)?', lambda m: (
    '<form class="filter-bar" data-deal-filter>\n'
    f'  <input type="search" name="q" placeholder="Search {n} deals or stores…" aria-label="Search deals">\n'
    f'  <select name="department" aria-label="Department"><option value="">All departments</option>{dept_opts}</select>\n'
    f'  <select name="brand" aria-label="Brand"><option value="">All brands</option>{brand_opts}</select>\n'
    '  <select name="type" aria-label="Type"><option value="">Codes &amp; deals</option><option value="code">Promo codes</option><option value="deal">Deals (no code)</option></select>\n'
    '</form>\n'
    f'<nav class="dept-chips" aria-label="Departments">{chips}</nav>\n'), head, flags=re.S)
head = re.sub(r'<p class="muted" data-result-count>\d+ deals</p>', f'<p class="muted" data-result-count>{n} deals</p>', head)

SCRIPT = r'''<script>
(function () {
  var f = document.querySelector('[data-deal-filter]'), cards = [].slice.call(document.querySelectorAll('.deal-card')), out = document.querySelector('[data-result-count]');
  var chips = [].slice.call(document.querySelectorAll('[data-dept-chip]'));
  function run() {
    var q = f.q.value.trim().toLowerCase(), d = f.department.value, b = f.brand.value, t = f.type.value, n = 0;
    cards.forEach(function (el) {
      var ok = (!q || el.getAttribute('data-name').indexOf(q) !== -1) && (!d || el.getAttribute('data-dept') === d) && (!b || el.getAttribute('data-brand') === b) && (!t || el.getAttribute('data-type') === t);
      el.hidden = !ok; if (ok) n++;
    });
    chips.forEach(function (c) { c.classList.toggle('active', c.getAttribute('data-dept-chip') === d); });
    out.textContent = n + ' deals';
    var p = new URLSearchParams(); if (d) p.set('department', d); if (b) p.set('brand', b);
    history.replaceState(null, '', location.pathname + (p.toString() ? '?' + p : ''));
  }
  var u = new URLSearchParams(location.search);
  if (u.get('department')) f.department.value = u.get('department');
  if (u.get('brand')) f.brand.value = u.get('brand');
  if (u.get('q')) f.q.value = u.get('q');
  f.addEventListener('input', run); f.addEventListener('submit', function (e) { e.preventDefault(); });
  chips.forEach(function (c) { c.addEventListener('click', function (e) { e.preventDefault(); var s = c.getAttribute('data-dept-chip'); f.department.value = f.department.value === s ? '' : s; run(); }); });
  if (location.search) run();
  document.addEventListener('click', function (e) {
    var b = e.target.closest('.copy-code'); if (!b) return;
    navigator.clipboard && navigator.clipboard.writeText(b.getAttribute('data-code')).then(function () { b.textContent = 'Copied!'; setTimeout(function () { b.textContent = 'Copy'; }, 1500); });
  });
})();
</script>'''
tail = re.sub(r'<script>.*?</script>', lambda m: SCRIPT, tail, count=1, flags=re.S)
with open(idx_path, 'w', encoding='utf-8') as f:
    f.write(head + '<div class="grid deal-grid">\n' + '\n'.join(c['html'] for c in cards) + '\n</div>\n</main>' + tail)

# ---- sitemap --------------------------------------------------------------
sm_path = os.path.join(ROOT, 'sitemap-deals.xml')
sm = open(sm_path, encoding='utf-8').read()
have = set(re.findall(r'<loc>([^<]+)</loc>', sm))
add = ''.join(f'  <url>\n    <loc>https://dealuxapp.com{c["href"]}</loc>\n    <lastmod>{TODAY}</lastmod>\n'
              f'    <changefreq>weekly</changefreq>\n    <priority>0.7</priority>\n  </url>\n'
              for c in cards if c['imported'] and 'https://dealuxapp.com' + c['href'] not in have)
with open(sm_path, 'w', encoding='utf-8') as f:
    f.write(sm.replace('</urlset>', add + '</urlset>'))
print(f'{n} deals ({sum(c["imported"] for c in cards)} imported), {len(brands)} brands', dept_counts)
