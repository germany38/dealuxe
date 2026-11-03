#!/usr/bin/env python3
"""Index every Wyzant tutor staged by scripts/build-tutors.py as a searchable Shop listing.

Usage: python3 scripts/add-tutors-to-shop.py   (run after scripts/build-tutors.py)

Each tutor page becomes a /shop/<slug> listing (served by the shop-product edge
function) in the "Tutoring & Lessons" type under Education & Classroom. Shop
search, the type/department pages and the shop sitemaps all pick them up.
Re-running replaces the previous tutor listings.
"""
import glob, html, json, os, re, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
BRAND = 'Wyzant'
TYPE = 'tutoring'
TYPE_NAME = 'Tutoring &amp; Lessons'
SUFFIX = '-wyzant-tutor-'  # every tutor slug contains this marker
IMG_SHARDS = 64
DATE = '2026-11-03'
SRC = os.environ.get('DEALUX_TUTORS_DIR') or os.path.join(tempfile.gettempdir(), 'dealux-tutors')


def slugify(s):
    return re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')


def shard_of(slug):
    h = 5381
    for c in slug:
        h = ((h * 33) ^ ord(c)) & 0xFFFFFFFF
    return h % IMG_SHARDS


def dump(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(json.dumps(data, ensure_ascii=False, separators=(',', ':')))


tutors = []
for page in sorted(glob.glob(os.path.join(SRC, '*', 'index.html'))):
    folder = os.path.basename(os.path.dirname(page))
    if folder == 'state' or not re.search(r'-\d+$', folder):
        continue
    h = open(page, encoding='utf-8').read()
    m = re.search(r'<script type="application/ld\+json">(\{"@context": "https://schema.org", "@type": "Person".*?)</script>', h)
    if not m:
        continue
    ld = json.loads(m.group(1).replace('<\\/', '</'))
    link = re.search(r'<a class="btn btn-gold" href="([^"]+)"', h)
    rate = re.search(r'<p class="price">\$([\d.,]+)/hr</p>', h)
    addr = ld.get('address', {})
    city, st = addr.get('addressLocality', ''), addr.get('addressRegion', '')
    subs = ld.get('knowsAbout', [])
    tid = folder.rsplit('-', 1)[1]
    top = slugify(' '.join(subs[:3]))[:48].strip('-')
    slug = '-'.join(filter(None, [top, 'tutor', slugify(ld['name']), slugify(city), slugify(st)]))
    slug = slug.replace('-tutor-', SUFFIX, 1) + '-' + tid
    title = f"{ld['name']} — {', '.join(subs[:3]) or 'Private'} Tutor in {city}, {st}"
    desc = f"Book private lessons with {ld['name']}, a Wyzant tutor in {city}, {st}"
    if subs:
        desc += f" teaching {', '.join(subs[:6])}"
    desc += '. ' + (ld.get('description') or '')
    tutors.append((slug, [title, rate.group(1).replace(',', '') if rate else '', 'USD', BRAND,
                          ld.get('image', ''), html.unescape(link.group(1)) if link else 'https://www.wyzant.com/',
                          desc[:400].strip()]))

slugs = [s for s, _ in tutors]
print(f'{len(tutors)} tutors')
if not tutors:
    raise SystemExit(f'No tutor pages in {SRC}; run scripts/build-tutors.py first.')

# ---- product index ----
lines = [l.strip() for l in open('data/products.txt', encoding='utf-8') if l.strip() and SUFFIX not in l]
open('data/products.txt', 'w', encoding='utf-8').write('\n'.join(lines + slugs) + '\n')

# ---- product detail shards ----
by_shard = {}
for s, rec in tutors:
    by_shard.setdefault(shard_of(s), {})[s] = rec
for n in range(IMG_SHARDS):
    p = f'data/img/{n}.json'
    d = json.load(open(p, encoding='utf-8'))
    d = {k: v for k, v in d.items() if SUFFIX not in k}
    d.update(by_shard.get(n, {}))
    dump(p, d)

# ---- type, department and brand lists ----
dump(f'data/list/type-{TYPE}.json', slugs)
dept = [s for s in json.load(open('data/list/dept-education.json', encoding='utf-8')) if SUFFIX not in s]
dump('data/list/dept-education.json', slugs + dept)

# ---- shop type page (cloned from an existing Education type page) ----
src = open('shop/type/courses-tech-data/index.html', encoding='utf-8').read()
page = (src.replace('shop/type/courses-tech-data/">\n', f'shop/type/{TYPE}/">\n', 1)
           .replace('side-link sub active" href="/shop/type/courses-tech-data/"', 'side-link sub " href="/shop/type/courses-tech-data/"')
           .replace('type-courses-tech-data.json', f'type-{TYPE}.json')
           .replace('Tech, Data &amp; Science Courses', TYPE_NAME))
page = re.sub(r'(<meta name="description" content=")[^"]*', r'\g<1>' +
              f'Find {len(slugs):,} private tutors across the US — math, science, test prep, languages and more. Book lessons through Wyzant.', page)
page = re.sub(r'(<meta property="og:description" content=")[^"]*', r'\g<1>' +
              f'Find {len(slugs):,} private tutors across the US — math, science, test prep, languages and more.', page)
# Keep the hand-built intro (disclosure, state and subject chips) and styles from the current page.
prev = open(f'shop/type/{TYPE}/index.html', encoding='utf-8').read() if os.path.exists(f'shop/type/{TYPE}/index.html') else ''
for start, end, at in (('<!-- tutor-browse -->', '<!-- /tutor-browse -->', f'<h1>{TYPE_NAME}</h1>'),
                       ('<!-- tutor-style -->', '<!-- /tutor-style -->', '</head>')):
    m = re.search(re.escape(start) + '.*?' + re.escape(end), prev, re.S)
    if m:
        page = page.replace(at, at + '\n    ' + m.group(0) if at.startswith('<h1') else m.group(0) + '\n' + at, 1)
page = page.replace('    <p class="muted">Online courses and certificates in computer science, IT, data science, math and engineering.</p>\n', '', 1)
os.makedirs(f'shop/type/{TYPE}', exist_ok=True)
open(f'shop/type/{TYPE}/index.html', 'w', encoding='utf-8').write(page)

# ---- sidebar link on every shop page ----
link = f'<a class="side-link sub " href="/shop/type/{TYPE}/">{TYPE_NAME}</a>'
anchor = re.compile(r'<a class="side-link sub (?:active)?" href="/shop/type/workbooks/">')
for p in glob.glob('shop/**/index.html', recursive=True):
    h = open(p, encoding='utf-8').read()
    if f'href="/shop/type/{TYPE}/">' not in h:
        m = anchor.search(h)
        if not m:
            continue
        h = h[:m.start()] + link + h[m.start():]
    # Mark it active on its own page, like the other type links.
    if p == f'shop/type/{TYPE}/index.html':
        h = h.replace(link, link.replace('side-link sub "', 'side-link sub active"'), 1)
    open(p, 'w', encoding='utf-8').write(h)

# ---- sitemaps ----
sm = 'sitemap-shop-products-tutors.xml'
with open(sm, 'w', encoding='utf-8') as f:
    f.write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n')
    for s in slugs:
        f.write(f'  <url><loc>https://dealuxapp.com/shop/{s}</loc><lastmod>{DATE}</lastmod></url>\n')
    f.write('</urlset>\n')
idx = open('sitemap-index.xml', encoding='utf-8').read()
if sm not in idx:
    idx = idx.replace('</sitemapindex>', f'  <sitemap><loc>https://dealuxapp.com/{sm}</loc><lastmod>{DATE}</lastmod></sitemap>\n</sitemapindex>')
    open('sitemap-index.xml', 'w', encoding='utf-8').write(idx)
shop_sm = open('sitemap-shop.xml', encoding='utf-8').read()
type_url = f'https://dealuxapp.com/shop/type/{TYPE}/'
if type_url not in shop_sm:
    shop_sm = shop_sm.replace('</urlset>', f'  <url><loc>{type_url}</loc><lastmod>{DATE}</lastmod></url>\n</urlset>')
    open('sitemap-shop.xml', 'w', encoding='utf-8').write(shop_sm)
print('done')
