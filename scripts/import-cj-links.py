#!/usr/bin/env python3
"""Import a CJ Affiliate link export (CSV) into the static shop.

Usage: python3 scripts/import-cj-links.py path/to/cj_links.csv

Every unique link becomes a shop item at /shop/<slug>, keeping CJ's tracking
click URL, name and description untouched. Banner size variants of the same
creative collapse into one item, and promotions that already ended are skipped.
Items are filed under their advertiser's brand page and a department/type
mapped from CJ's category. Product data, brand/department/type lists, the
brand directory and the sitemaps are all updated in place, so re-running with
the same CSV is a no-op.
"""
import csv, datetime, glob, html, json, os, re, sys, unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
TODAY = datetime.date.today()
IMG_SHARDS = 64
SITE = 'https://dealuxapp.com'

# New groupings that CJ advertisers need beyond the existing shop tree.
NEW_DEPT = ('services', 'Services &amp; Marketplaces', [
    ('web-hosting-marketing', 'Web Hosting, Domains &amp; Marketing'),
    ('finance-insurance', 'Finance, Credit &amp; Insurance'),
    ('phone-internet', 'Phone, Internet &amp; VPN'),
    ('business-services', 'Business &amp; Home Services'),
    ('marketplaces', 'Department Stores &amp; Marketplaces'),
])
NEW_TYPES = {'travel': [('flights-car-rentals', 'Flights, Vacations &amp; Car Rentals')]}
TYPE_DESC = {
    'web-hosting-marketing': 'Web hosting, domains, site builders, email and marketing tools.',
    'finance-insurance': 'Banking, trading, credit reports, tax help and insurance offers.',
    'phone-internet': 'Phone plans, internet providers, VPNs and calling cards.',
    'business-services': 'Business, professional and home services.',
    'marketplaces': 'Department stores, online malls and marketplaces.',
    'flights-car-rentals': 'Flights, vacation packages, travel deals and car rentals.',
}

# CJ category -> (department, type)
CATEGORY = {
    'Computer SW': ('electronics', 'software-apps'), 'Productivity Tools': ('electronics', 'software-apps'),
    'Consumer Electronics': ('electronics', 'tech-accessories'), 'Computer HW': ('electronics', 'tech-accessories'),
    'Peripherals': ('electronics', 'tech-accessories'), 'Home Appliances': ('electronics', 'appliances'),
    'Events': ('experiences', 'shows-attractions'), 'Entertainment': ('experiences', 'shows-attractions'),
    'Music': ('experiences', 'shows-attractions'), 'Videos/Movies': ('experiences', 'shows-attractions'),
    'Hotel': ('experiences', 'hotels-stays'), 'Rentals': ('experiences', 'hotels-stays'),
    'Vacation': ('travel', 'flights-car-rentals'), 'Travel': ('travel', 'flights-car-rentals'),
    'Air': ('travel', 'flights-car-rentals'), 'Car': ('travel', 'flights-car-rentals'),
    'Womens': ('clothing', 'clothing-other'), 'Mens': ('clothing', 'clothing-other'),
    'Apparel': ('clothing', 'clothing-other'), 'Childrens': ('clothing', 'clothing-other'),
    'Children': ('clothing', 'clothing-other'),
    'Cosmetics': ('hair-beauty', 'beauty-care'), 'Bath & Body': ('hair-beauty', 'beauty-care'),
    'Fragrance': ('hair-beauty', 'beauty-care'),
    'Furniture': ('home-decor', 'decor-accents'), 'Bed & Bath': ('home-decor', 'home-textiles'),
    'Flowers': ('home-decor', 'plants-flowers'),
    'Kitchen': ('home-garden', 'kitchen-dining'), 'Garden': ('home-garden', 'garden-patio'),
    'Energy Saving': ('home-garden', 'home-essentials'), 'Tools and Supplies': ('home-garden', 'home-essentials'),
    'Construction': ('home-garden', 'home-essentials'),
    'Shoes': ('shoes-bags', 'shoes'), 'Handbags': ('shoes-bags', 'bags'), 'Luggage': ('shoes-bags', 'luggage'),
    'Electronic Games': ('toys-hobbies', 'video-games'), 'Games': ('toys-hobbies', 'video-games'),
    'Toys': ('toys-hobbies', 'toys-games'), 'Halloween': ('toys-hobbies', 'costumes'),
    'Party Goods': ('toys-hobbies', 'party-supplies'), 'Pets': ('toys-hobbies', 'pet-supplies'),
    'Babies': ('toys-hobbies', 'baby-nursery'),
    'Nutritional Supplements': ('wellness', 'vitamins-supplements'), 'Health Food': ('wellness', 'vitamins-supplements'),
    'Wellness': ('wellness', 'medical-supplies'), 'Vision Care': ('wellness', 'medical-supplies'),
    'Exercise & Health': ('sports-outdoors', 'sports-outdoor-gear'), 'Sports': ('sports-outdoors', 'sports-outdoor-gear'),
    'Golf': ('sports-outdoors', 'sports-outdoor-gear'), 'Water Sports': ('sports-outdoors', 'sports-outdoor-gear'),
    'Outdoors': ('sports-outdoors', 'sports-outdoor-gear'), 'Equipment': ('sports-outdoors', 'sports-outdoor-gear'),
    'Jewelry': ('jewelry', 'jewelry-sets'),
    'Gifts': ('food-snacks', 'gift-baskets'), 'Gourmet': ('food-snacks', 'pantry-food'),
    'Restaurants': ('food-snacks', 'pantry-food'),
    'Collectibles': ('fan-shop', 'fan-gear'), 'Collectibles and Memorabilia': ('fan-shop', 'fan-gear'),
    'Photo': ('cameras-photo', 'photo-video-accessories'),
    'Books': ('education', 'workbooks'), 'Magazines': ('education', 'workbooks'), 'Audio Books': ('education', 'workbooks'),
    'Languages': ('education', 'courses-health-humanities'),
    'Cars & Trucks': ('automotive', 'car-accessories'), 'Parts & Accessories': ('automotive', 'car-accessories'),
    'Motorcycles': ('automotive', 'car-accessories'),
    'Web Tools': ('services', 'web-hosting-marketing'), 'Web Hosting/Servers': ('services', 'web-hosting-marketing'),
    'Domain Registrations': ('services', 'web-hosting-marketing'), 'Marketing': ('services', 'web-hosting-marketing'),
    'Email Marketing': ('services', 'web-hosting-marketing'),
    'E-commerce Solutions/Providers': ('services', 'web-hosting-marketing'),
    'Banking/Trading': ('services', 'finance-insurance'), 'Credit Reporting and Repair': ('services', 'finance-insurance'),
    'Insurance': ('services', 'finance-insurance'), 'Tax Services': ('services', 'finance-insurance'),
    'Telephone Services': ('services', 'phone-internet'), 'Internet Service Providers': ('services', 'phone-internet'),
    'Online/Wireless': ('services', 'phone-internet'), 'Phone Card Services': ('services', 'phone-internet'),
    'Services': ('services', 'business-services'), 'Business-to-Business': ('services', 'business-services'),
    'Professional': ('services', 'business-services'),
    'Department Stores': ('services', 'marketplaces'), 'Virtual Malls': ('services', 'marketplaces'),
    'Malls': ('services', 'marketplaces'), 'New/Used Goods': ('services', 'marketplaces'),
}
DEFAULT_CAT = ('services', 'marketplaces')

SIZE_RE = re.compile(r'[\s_\-–(]*(?<![a-z0-9])\d{2,4}\s*[x×*]\s*\d{2,4}(?:_\d+)?(?![a-z0-9])(\s*(px|banner))?[)\s]*', re.I)
GENERIC = {'', 'logo', 'banner', 'skyscraper', 'leaderboard', 'rectangle', 'square', 'button', 'homepage', 'home page'}


def slugify(s):
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+', '-', s).strip('-')


def clean_text(s):
    s = re.sub(r'</?link>', ' ', s or '')
    return re.sub(r'\s+', ' ', html.unescape(s)).strip()


def clean_name(name, advertiser):
    n = clean_text(SIZE_RE.sub(' ', name))
    n = re.sub(r'\s*[-–|:_]+\s*$', '', n).strip()
    n = re.sub(r'\s*\(\d+\)$', '', n).strip()
    return n if n.lower() not in GENERIC else f'{advertiser} — Official Site'


def ended(date_str):
    if not date_str:
        return False
    try:
        return datetime.datetime.strptime(date_str.strip(), '%d-%b-%Y').date() < TODAY
    except ValueError:
        return False


def shard_of(slug):
    h = 5381
    for ch in slug:
        h = ((h * 33) ^ ord(ch)) & 0xFFFFFFFF
    return h % IMG_SHARDS


def read_json(path, default):
    return json.load(open(path, encoding='utf-8')) if os.path.exists(path) else default


def write_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, separators=(',', ':'))


def main(csv_path):
    rows = list(csv.DictReader(open(csv_path, encoding='utf-8-sig')))
    shards = {n: read_json(f'data/img/{n}.json', {}) for n in range(IMG_SHARDS)}
    known_links = {rec[5] for s in shards.values() for rec in s.values() if len(rec) > 5}
    taken = set(k for s in shards.values() for k in s)

    items, seen, skipped_ended = [], set(), 0
    brand_link = {}
    for r in rows:
        adv = clean_text(r['ADVERTISER'])
        link = r['CLICK URL'].strip()
        if not adv or not link:
            continue
        # The evergreen/homepage link becomes the brand's default affiliate link.
        if r['LINK TYPE'] in ('Evergreen Link', 'Deep Link'):
            brand_link[adv] = link
        elif r['LINK TYPE'] == 'Text Link':
            brand_link.setdefault(adv, link)
        if ended(r['PROMOTIONAL END DATE']):
            skipped_ended += 1
            continue
        if r['LINK TYPE'] == 'Evergreen Link':
            continue  # generic "Evergreen Link for X" boilerplate; used as the brand link instead
        name = clean_name(r['NAME'], adv)
        key = (adv.lower(), name.lower())
        if key in seen or link in known_links:
            continue
        seen.add(key)
        desc = clean_text(r['DESCRIPTION'])
        if desc.lower() == name.lower() or desc.lower() == clean_text(r['NAME']).lower():
            desc = ''
        extra = []
        if r['COUPON CODE'].strip():
            extra.append(f"Use code {r['COUPON CODE'].strip()}.")
        if r['PROMOTIONAL END DATE'].strip():
            extra.append(f"Offer ends {r['PROMOTIONAL END DATE'].strip()}.")
        desc = ' '.join([d for d in [desc] + extra if d])
        image = re.sub(r'/click-(\d+-\d+)$', r'/image-\1', link) if r['LINK TYPE'] == 'Banner' else ''
        base = slugify(name)
        if slugify(adv) not in base:
            base = f'{slugify(adv)}-{base}'.strip('-')
        base = base[:72].strip('-')
        slug = f"{base}-{r['LINK ID']}"
        if slug in taken:
            continue
        taken.add(slug)
        dept, typ = CATEGORY.get(r['CATEGORY'].strip(), DEFAULT_CAT)
        items.append(dict(slug=slug, name=name, brand=adv, image=image, link=link, desc=desc, dept=dept, type=typ,
                          rec=[name, '', 'USD', adv, image, link, desc]))
    for adv in {i['brand'] for i in items}:
        brand_link.setdefault(adv, next(i['link'] for i in items if i['brand'] == adv))

    if not items:
        print('Nothing new to import.')
        return
    print(f'{len(items)} new items from {len(rows)} rows ({skipped_ended} expired promotions skipped)')

    # ---- product data ----
    for it in items:
        shards[shard_of(it['slug'])][it['slug']] = it['rec']
    for n, data in shards.items():
        write_json(f'data/img/{n}.json', data)
    for path in ('data/products.txt', 'products.txt'):
        with open(path, 'a', encoding='utf-8') as f:
            f.write(''.join(i['slug'] + '\n' for i in items))

    # ---- lists ----
    def add_to_list(name, slugs):
        path = f'data/list/{name}.json'
        lst = read_json(path, [])
        have = set(lst)
        lst += [s for s in slugs if s not in have]
        write_json(path, lst)
        return len(lst)

    by = lambda k: {v: [i['slug'] for i in items if i[k] == v] for v in {i[k] for i in items}}
    for d, slugs in by('dept').items():
        add_to_list(f'dept-{d}', slugs)
    for t, slugs in by('type').items():
        add_to_list(f'type-{t}', slugs)

    template = open('shop/brand/3w/index.html', encoding='utf-8').read()
    update_sidebars(template)
    template = open('shop/brand/3w/index.html', encoding='utf-8').read()

    brand_counts, new_pages = {}, []
    brand_names = {}
    for b, slugs in by('brand').items():
        bslug = slugify(b)
        brand_names[bslug] = b
        count = add_to_list(f'brand-{bslug}', slugs)
        brand_counts[bslug] = count
        page = f'shop/brand/{bslug}/index.html'
        if os.path.exists(page):
            h = open(page, encoding='utf-8').read()
            h = re.sub(r'<p class="muted">[\d,]+ products</p>', f'<p class="muted">{count:,} products</p>', h, count=1)
            h = re.sub(r'content="Shop [\d,]+ ', f'content="Shop {count:,} ', h, count=1)
        else:
            e = html.escape(b, quote=True)
            h = page_from(template, f'/shop/brand/{bslug}/', e, f'Shop {count:,} {e} products, deals and offers.',
                          f'Shop {e}', f'{count:,} products', f'/data/list/brand-{bslug}.json')
            new_pages.append(f'{SITE}/shop/brand/{bslug}/')
        os.makedirs(os.path.dirname(page), exist_ok=True)
        open(page, 'w', encoding='utf-8').write(h)

    # New department/type landing pages.
    for dslug, dname, types in [NEW_DEPT]:
        p = f'shop/department/{dslug}/index.html'
        if not os.path.exists(p):
            write_page(p, page_from(template, f'/shop/department/{dslug}/', dname, f'Shop {dname}.', dname, '',
                                    f'/data/list/dept-{dslug}.json', active=f'/shop/department/{dslug}/'))
            new_pages.append(f'{SITE}/shop/department/{dslug}/')
    for tslug, tname in NEW_DEPT[2] + sum(NEW_TYPES.values(), []):
        p = f'shop/type/{tslug}/index.html'
        if not os.path.exists(p):
            if not os.path.exists(f'data/list/type-{tslug}.json'):
                write_json(f'data/list/type-{tslug}.json', [])
            write_page(p, page_from(template, f'/shop/type/{tslug}/', tname, TYPE_DESC[tslug], tname, TYPE_DESC[tslug],
                                    f'/data/list/type-{tslug}.json', active=f'/shop/type/{tslug}/'))
            new_pages.append(f'{SITE}/shop/type/{tslug}/')
    if not os.path.exists(f'data/list/dept-{NEW_DEPT[0]}.json'):
        write_json(f'data/list/dept-{NEW_DEPT[0]}.json', [])

    # ---- brand affiliate links + brand directory ----
    for path in ('data/brands.json', 'brands.json'):
        lst = read_json(path, [])
        have = {slugify(b[0]) for b in lst}
        lst += [[b, brand_link[b]] for b in sorted(brand_link) if slugify(b) in brand_counts and slugify(b) not in have]
        lst.sort(key=lambda b: b[0].lower())
        write_json(path, lst)
    update_brand_directory(brand_counts, brand_names)

    # ---- sitemaps ----
    update_sitemaps([i['slug'] for i in items], new_pages)
    print(f'{len(brand_counts)} brands, {len(new_pages)} new listing pages')


def write_page(path, h):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, 'w', encoding='utf-8').write(h)


def page_from(template, path, title, desc, h1, sub, list_url, active=None):
    h = template
    h = re.sub(r'<title>.*?</title>', f'<title>{title} — Dealux Shop</title>', h, count=1)
    h = re.sub(r'<meta name="description" content="[^"]*">', f'<meta name="description" content="{desc}">', h, count=1)
    h = re.sub(r'<link rel="canonical" href="[^"]*">', f'<link rel="canonical" href="{SITE}{path}">', h, count=1)
    h = re.sub(r'<h1>.*?</h1>\n\s*<p class="muted">.*?</p>', f'<h1>{h1}</h1>\n    <p class="muted">{sub}</p>', h, count=1, flags=re.S)
    h = re.sub(r'data-list="[^"]*"', f'data-list="{list_url}"', h, count=1)
    if active:
        h = h.replace(f'class="side-link " href="{active}"', f'class="side-link active" href="{active}"')
        h = h.replace(f'class="side-link sub " href="{active}"', f'class="side-link sub active" href="{active}"')
    return h


def update_sidebars(_template):
    """Add the new department and types to the category sidebar on every shop page."""
    dslug, dname, types = NEW_DEPT
    block = ('<details >\n    <summary><a class="side-link " href="/shop/department/%s/">%s</a></summary>\n    %s\n  </details>'
             % (dslug, dname, ''.join(f'<a class="side-link sub " href="/shop/type/{t}/">{n}</a>' for t, n in types)))
    pages = glob.glob('shop/**/index.html', recursive=True)
    for p in pages:
        h = open(p, encoding='utf-8').read()
        if '<aside class="sidebar">' not in h:
            continue
        orig = h
        if f'href="/shop/department/{dslug}/"' not in h:
            # Insert after the last department <details> (right before the "Shop by brand" block).
            h = re.sub(r'(</details>)(\s*<details[^>]*>\s*<summary><span class="side-link side-heading">Shop by brand)',
                       lambda m: m.group(1) + block + m.group(2), h, count=1)
        for parent, extra in NEW_TYPES.items():
            for t, n in extra:
                if f'href="/shop/type/{t}/"' in h:
                    continue
                h = re.sub(r'(href="/shop/department/%s/">[^<]*</a></summary>\s*(?:<a class="side-link sub [^"]*" href="[^"]*">[^<]*</a>)*)' % parent,
                           lambda m: m.group(1) + f'<a class="side-link sub " href="/shop/type/{t}/">{n}</a>', h, count=1)
        if h != orig:
            open(p, 'w', encoding='utf-8').write(h)


def update_brand_directory(brand_counts, brand_names):
    p = 'brands/index.html'
    h = open(p, encoding='utf-8').read()
    m = re.search(r'<ul class="brand-list">(.*?)</ul>', h, re.S)
    entries = {}
    for li in re.finditer(r'<li data-name="([^"]*)"><a href="/shop/brand/([^/]+)/">(.*?)</a><span class="muted">([\d,]+) products?</span></li>', m.group(1)):
        entries[li.group(2)] = [li.group(1), li.group(3), int(li.group(4).replace(',', ''))]
    for bslug, count in brand_counts.items():
        if bslug in entries:
            entries[bslug][2] = count
        else:
            name = brand_names[bslug]
            entries[bslug] = [html.escape(name.lower(), quote=True), html.escape(name), count]
    ordered = sorted(entries.items(), key=lambda kv: (-kv[1][2], kv[1][0]))
    lis = ''.join(f'<li data-name="{v[0]}"><a href="/shop/brand/{k}/">{v[1]}</a><span class="muted">{v[2]:,} product{"s" if v[2] != 1 else ""}</span></li>'
                  for k, v in ordered)
    n = len(ordered)
    h = h[:m.start(1)] + lis + h[m.end(1):]
    h = re.sub(r'placeholder="Search [\d,]+ brands…"', f'placeholder="Search {n:,} brands…"', h)
    h = re.sub(r'data-result-count>[\d,]+ brands<', f'data-result-count>{n:,} brands<', h)
    h = re.sub(r'(<meta name="description" content="[^"]*?)[\d,]+( brands)', lambda mm: f'{mm.group(1)}{n:,}{mm.group(2)}', h, count=1)
    open(p, 'w', encoding='utf-8').write(h)


SITEMAP_HEAD = ('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
                'xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">\n')


def load_records():
    records = {}
    for n in range(IMG_SHARDS):
        records.update(read_json(f'data/img/{n}.json', {}))
    return records


def product_url_entry(slug, rec, lastmod):
    """One product <url>, with an image:image entry so Google/Bing Images can index the product photo."""
    img = ''
    if rec and len(rec) > 4 and rec[4].startswith(('http://', 'https://')):
        title = html.escape(rec[0] or slug.replace('-', ' ').title(), quote=False)
        img = f'<image:image><image:loc>{html.escape(rec[4], quote=False)}</image:loc><image:title>{title}</image:title></image:image>'
    return f'  <url><loc>{SITE}/shop/{html.escape(slug)}</loc><lastmod>{lastmod}</lastmod>{img}</url>\n'


def update_sitemaps(slugs, pages):
    today = TODAY.isoformat()
    records = load_records()
    existing = sorted(glob.glob('sitemap-shop-products-*.xml'), key=lambda f: int(re.search(r'(\d+)', f).group(1)))
    present = set()
    for f in existing:
        present.update(re.findall(r'<loc>[^<]*/shop/([^<]+)</loc>', open(f, encoding='utf-8').read()))
    slugs = [s for s in slugs if s not in present]
    nxt = int(re.search(r'(\d+)', existing[-1]).group(1)) + 1 if existing else 1
    new_files = []
    for i in range(0, len(slugs), 10000):
        name = f'sitemap-shop-products-{nxt}.xml'
        nxt += 1
        body = ''.join(product_url_entry(s, records.get(s), today) for s in slugs[i:i + 10000])
        open(name, 'w', encoding='utf-8').write(SITEMAP_HEAD + body + '</urlset>\n')
        new_files.append(name)

    sm = open('sitemap-shop.xml', encoding='utf-8').read()
    add = ''.join(f'  <url>\n    <loc>{u}</loc>\n    <lastmod>{today}</lastmod>\n    <changefreq>weekly</changefreq>\n    <priority>0.7</priority>\n  </url>\n'
                  for u in pages if f'<loc>{u}</loc>' not in sm)
    open('sitemap-shop.xml', 'w', encoding='utf-8').write(sm.replace('</urlset>', add + '</urlset>'))

    idx = open('sitemap-index.xml', encoding='utf-8').read()
    for name in ['sitemap-shop.xml'] + new_files:
        loc = f'<loc>{SITE}/{name}</loc>'
        if loc in idx:
            idx = re.sub(re.escape(loc) + r'<lastmod>[^<]*</lastmod>', f'{loc}<lastmod>{today}</lastmod>', idx)
        else:
            idx = idx.replace('  <sitemap><loc>' + SITE + '/sitemap-shop.xml</loc>',
                              f'  <sitemap>{loc}<lastmod>{today}</lastmod></sitemap>\n  <sitemap><loc>{SITE}/sitemap-shop.xml</loc>', 1)
    open('sitemap-index.xml', 'w', encoding='utf-8').write(idx)


if __name__ == '__main__':
    main(sys.argv[1])
