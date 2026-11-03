#!/usr/bin/env python3
"""Build the /tutors/ directory from a Wyzant partner product CSV.

Usage: python3 scripts/build-tutors.py Wyzant-Tutors.csv

Writes static, crawlable pages:
  /tutors/                 hub (disclosure banner, featured grid, states, subjects)
  /tutors/state/<st>/      every tutor in a state, with search + subject filter
  /tutors/<slug>/          one page per tutor, with the shared promo sidebar
and sitemap-tutors.xml (registered in sitemap-index.xml). Re-running is idempotent.
Affiliate "Product URL" values are used verbatim so attribution is preserved.
"""
import csv, html, json, os, re, shutil, sys, unicodedata
from collections import Counter, defaultdict
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'tutors')
SITE = 'https://dealuxapp.com'
TODAY = date.today().isoformat()
e = lambda s: html.escape(s or '', quote=True)

STATES = {
    'AL': 'Alabama', 'AK': 'Alaska', 'AZ': 'Arizona', 'AR': 'Arkansas', 'CA': 'California', 'CO': 'Colorado',
    'CT': 'Connecticut', 'DE': 'Delaware', 'DC': 'District of Columbia', 'FL': 'Florida', 'GA': 'Georgia',
    'HI': 'Hawaii', 'ID': 'Idaho', 'IL': 'Illinois', 'IN': 'Indiana', 'IA': 'Iowa', 'KS': 'Kansas',
    'KY': 'Kentucky', 'LA': 'Louisiana', 'ME': 'Maine', 'MD': 'Maryland', 'MA': 'Massachusetts',
    'MI': 'Michigan', 'MN': 'Minnesota', 'MS': 'Mississippi', 'MO': 'Missouri', 'MT': 'Montana',
    'NE': 'Nebraska', 'NV': 'Nevada', 'NH': 'New Hampshire', 'NJ': 'New Jersey', 'NM': 'New Mexico',
    'NY': 'New York', 'NC': 'North Carolina', 'ND': 'North Dakota', 'OH': 'Ohio', 'OK': 'Oklahoma',
    'OR': 'Oregon', 'PA': 'Pennsylvania', 'RI': 'Rhode Island', 'SC': 'South Carolina', 'SD': 'South Dakota',
    'TN': 'Tennessee', 'TX': 'Texas', 'UT': 'Utah', 'VT': 'Vermont', 'VA': 'Virginia', 'WA': 'Washington',
    'WV': 'West Virginia', 'WI': 'Wisconsin', 'WY': 'Wyoming', 'PR': 'Puerto Rico',
}

DISCLOSURE = ('<div class="partner-disclosure" role="note"><p><b>Partnership Disclosure:</b> Dealux is an affiliate partner '
              'of the Wyzant Partner Program. We display listings directly sourced from their network and may receive a '
              'commission on lessons booked through our links, at no extra cost to you.</p></div>')

CSS = '''<style>
.partner-disclosure{background:#fff8e1;color:#3b2f00;border:2px solid #d4a017;border-radius:10px;padding:.85rem 1.1rem;margin:1rem 0 1.25rem;font-size:1rem;line-height:1.5}
.partner-disclosure p{margin:0}
.tutor-grid{display:grid;gap:1rem;grid-template-columns:repeat(auto-fill,minmax(240px,1fr))}
.tutor-card{display:flex;flex-direction:column;gap:.4rem}
.tutor-card img{width:72px;height:72px;border-radius:50%;object-fit:cover;background:#ddd}
.tutor-card h3{margin:0;font-size:1.05rem}.tutor-card h3 a{color:inherit;text-decoration:none}
.tutor-card .price,.tutor-page .price{font-weight:700;color:var(--gold)}
.tutor-card .subs{font-size:.85rem;margin:0}
.tutor-card .btn{margin-top:auto;text-align:center}
.tutor-head{display:flex;gap:1.25rem;align-items:center;flex-wrap:wrap}
.tutor-head img{width:140px;height:140px;border-radius:50%;object-fit:cover;background:#ddd}
.tutor-subjects{display:flex;flex-wrap:wrap;gap:.4rem;padding:0;list-style:none}
.tutor-subjects li{border:1px solid rgba(127,127,127,.35);border-radius:999px;padding:.2rem .65rem;font-size:.85rem}
.tutor-filter{display:flex;gap:.5rem;flex-wrap:wrap;margin:0 0 1rem}
.tutor-filter input,.tutor-filter select{padding:.55rem .7rem;border-radius:8px;border:1px solid var(--line);background:var(--panel);color:inherit}
.tutor-filter input{flex:1;min-width:200px}
</style>'''


def slugify(s):
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+', '-', s).strip('-')


def price(v):
    try:
        return f'${float(v):,.0f}/hr'
    except ValueError:
        return ''


# ---- shared chrome, taken from the jobs pages so header/footer/sidebar match the site
tpl = open(os.path.join(ROOT, 'jobs', 'agent-engineer', 'index.html'), encoding='utf-8').read()
HEADER = tpl[tpl.index('<header class="site-header">'):tpl.index('</header>') + 9]
HEADER = HEADER.replace('<a href="/jobs/">Jobs</a>', '<a href="/jobs/">Jobs</a><a href="/tutors/">Tutors</a>', 1)
FOOTER = tpl[tpl.index('<footer class="site-footer">'):tpl.index('</footer>') + 9]
SIDEBAR_PROMOS = tpl[tpl.index('<aside class="post-sidebar">') + len('<aside class="post-sidebar">'):tpl.index('</aside>')]


def sidebar(state=None):
    links = ''
    if state:
        links = (f'  <div class="card"><span class="eyebrow">More tutors</span><h3>{e(STATES.get(state, state))}</h3>'
                 f'<p class="muted">Browse every tutor listed in {e(STATES.get(state, state))}.</p>'
                 f'<a class="btn" href="/tutors/state/{state.lower()}/">All {e(state)} tutors →</a>'
                 f'<a class="muted" href="/tutors/">← Tutor directory</a></div>\n')
    return '<aside class="post-sidebar">\n' + links + SIDEBAR_PROMOS + '</aside>'


def page(title, desc, path, body, extra_head=''):
    return (f'<!DOCTYPE html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
            f'<meta name="viewport" content="width=device-width, initial-scale=1">\n'
            f'<title>{e(title)}</title>\n<meta name="description" content="{e(desc[:300])}">\n'
            f'<meta name="robots" content="index, follow">\n'
            f'<link rel="canonical" href="{SITE}{path}">\n<link rel="icon" href="/favicon.ico">\n'
            f'<meta property="og:title" content="{e(title)}">\n<meta property="og:description" content="{e(desc[:300])}">\n'
            f'<meta property="og:url" content="{SITE}{path}">\n'
            '<link rel="stylesheet" href="/assets/dealux.css">\n<link rel="stylesheet" href="/assets/site.css?v=20261012b">\n'
            f'<script src="/assets/app.js?v=20261012c" defer></script>\n{CSS}\n{extra_head}</head>\n<body data-page="tutors">\n'
            f'{HEADER}\n<main class="wrap">\n{body}\n</main>\n{FOOTER}\n<script data-name="BMC-Widget" data-cfasync="false" src="https://cdnjs.buymeacoffee.com/1.0.0/widget.prod.min.js" data-id="dealuxfeed" data-description="Support me on Buy me a coffee!" data-message="Thank you for your contribution. We sincerely appreciate your support!" data-color="#FF813F" data-position="Right" data-x_margin="18" data-y_margin="18"></script>\n</body>\n</html>\n')


# ---- read CSV
rows, seen = [], set()
for r in csv.DictReader(open(sys.argv[1], encoding='utf-8-sig')):
    sku = r['SKU'].strip()
    if not sku or sku in seen or not r['Product URL'].startswith('http'):
        continue
    seen.add(sku)
    name = re.sub(r'\s+from\s+.*$', '', r['Tutor Name']).strip()
    st = r['State'].strip().upper()
    subs = [s.strip() for s in r['Subjects'].split(',') if s.strip()]
    slug = f"{slugify(name)}-{slugify(r['City'])}-{st.lower()}-{sku}"
    rows.append(dict(sku=sku, name=name, full=r['Tutor Name'].strip(), url=r['Product URL'].strip(),
                     img=r['Image URL'].strip(), price=price(r['Price Per Hour (USD)']), city=r['City'].strip(),
                     st=st, zip=r['ZIP'].strip(), subs=subs, desc=r['Description'].strip(),
                     travel=r['Travel Distance (mi)'].strip(), slug=slug, href=f'/tutors/{slug}/'))

by_state = defaultdict(list)
for t in rows:
    by_state[t['st']].append(t)
subj_count = Counter(s for t in rows for s in t['subs'])


def card(t):
    subs = ', '.join(t['subs'][:5]) + (f' +{len(t["subs"]) - 5} more' if len(t['subs']) > 5 else '')
    img = f'<img src="{e(t["img"])}" alt="{e(t["name"])}, tutor in {e(t["city"])}, {e(t["st"])}" width="72" height="72" loading="lazy">' if t['img'] else ''
    text = ' '.join([t['name'], t['city'], t['st']]).lower()
    return (f'<div class="card tutor-card" data-text="{e(text)}" data-subs="|{e("|".join(t["subs"]))}|">\n'
            f'  <a href="{t["href"]}">{img}</a>\n  <h3><a href="{t["href"]}">{e(t["name"])}</a></h3>\n'
            f'  <p class="muted" style="margin:0">{e(t["city"])}, {e(t["st"])} · <span class="price">{e(t["price"])}</span></p>\n'
            f'  <p class="subs muted">{e(subs)}</p>\n'
            f'  <a class="btn btn-gold" href="{e(t["url"])}" target="_blank" rel="sponsored noopener">View on Wyzant →</a>\n</div>')


# ---- clean previous output, then write tutor pages
if os.path.isdir(OUT):
    shutil.rmtree(OUT)
os.makedirs(OUT)

for t in rows:
    stname = STATES.get(t['st'], t['st'])
    lead = ', '.join(t['subs'][:3])
    title = f'{t["name"]} — {lead} Tutor in {t["city"]}, {t["st"]} | Dealux Tutors'
    desc = f'{t["name"]} tutors {lead} in {t["city"]}, {stname}' + (f' from {t["price"]}' if t['price'] else '') + f'. {t["desc"]}'
    ld = {'@context': 'https://schema.org', '@type': 'Person', 'name': t['name'], 'jobTitle': 'Tutor',
          'image': t['img'] or None, 'description': t['desc'][:500], 'url': SITE + t['href'],
          'knowsAbout': t['subs'],
          'address': {'@type': 'PostalAddress', 'addressLocality': t['city'], 'addressRegion': t['st'], 'postalCode': t['zip'], 'addressCountry': 'US'}}
    ld = {k: v for k, v in ld.items() if v}
    subs_html = ''.join(f'<li>{e(s)}</li>' for s in t['subs'])
    img = f'<img src="{e(t["img"])}" alt="{e(t["name"])}, tutor in {e(t["city"])}, {e(t["st"])}" width="140" height="140">' if t['img'] else ''
    travel = f' · Travels up to {e(t["travel"])} mi' if t['travel'] and t['travel'] != '0' else ''
    body = (f'<div class="post-layout">\n<article class="post tutor-page">\n'
            f'  <a class="muted" href="/tutors/state/{t["st"].lower()}/">← {e(stname)} tutors</a> · <a class="muted" href="/tutors/">All tutors</a>\n'
            f'  {DISCLOSURE}\n'
            f'  <div class="tutor-head">{img}<div>\n    <span class="eyebrow">Wyzant tutor · {e(t["city"])}, {e(t["st"])}</span>\n'
            f'    <h1>{e(t["name"])}</h1>\n    <p class="muted">{e(t["city"])}, {e(stname)} {e(t["zip"])}{travel}</p>\n'
            + (f'    <p class="price">{e(t["price"])}</p>\n' if t['price'] else '')
            + f'    <p><a class="btn btn-gold" href="{e(t["url"])}" target="_blank" rel="sponsored noopener">Book a lesson on Wyzant →</a></p>\n  </div></div>\n'
            f'  <h2>About {e(t["name"])}</h2>\n  <p>{e(t["desc"])}</p>\n'
            f'  <h2>Subjects ({len(t["subs"])})</h2>\n  <ul class="tutor-subjects">{subs_html}</ul>\n'
            f'  <p><a class="btn btn-gold" href="{e(t["url"])}" target="_blank" rel="sponsored noopener">Contact {e(t["name"])} on Wyzant →</a></p>\n'
            f'</article>\n{sidebar(t["st"])}\n</div>')
    extra = f'<meta property="og:image" content="{e(t["img"])}">\n' if t['img'] else ''
    extra += '<script type="application/ld+json">' + json.dumps(ld).replace('</', '<\\/') + '</script>\n'
    os.makedirs(os.path.join(OUT, t['slug']))
    with open(os.path.join(OUT, t['slug'], 'index.html'), 'w', encoding='utf-8') as f:
        f.write(page(title, desc, t['href'], body, extra))

# ---- state pages (search + subject filter run client-side over the full, crawlable list)
FILTER_JS = r'''<script>
(function () {
  var q = document.getElementById('tutor-q'), s = document.getElementById('tutor-subject'), out = document.getElementById('tutor-count');
  var cards = [].slice.call(document.querySelectorAll('.tutor-card'));
  function run() {
    var v = q.value.trim().toLowerCase(), sub = s.value, n = 0;
    cards.forEach(function (c) {
      var ok = (!v || (c.getAttribute('data-text') + c.getAttribute('data-subs').toLowerCase()).indexOf(v) !== -1) && (!sub || c.getAttribute('data-subs').indexOf('|' + sub + '|') !== -1);
      c.hidden = !ok; if (ok) n++;
    });
    out.textContent = n + ' tutors';
  }
  var u = new URLSearchParams(location.search); if (u.get('subject')) s.value = u.get('subject');
  q.addEventListener('input', run); s.addEventListener('change', run); if (u.get('subject')) run();
})();
</script>'''

state_links = ''.join(f'<a class="chip" href="/tutors/state/{st.lower()}/">{e(STATES.get(st, st))} <span class="muted">{len(ts)}</span></a>'
                      for st, ts in sorted(by_state.items(), key=lambda x: STATES.get(x[0], x[0])))
for st, ts in by_state.items():
    stname = STATES.get(st, st)
    ts.sort(key=lambda t: (t['city'].lower(), t['name'].lower()))
    sc = Counter(s for t in ts for s in t['subs'])
    opts = ''.join(f'<option value="{e(s)}">{e(s)} ({k})</option>' for s, k in sorted(sc.items()))
    top = ', '.join(s for s, _ in sc.most_common(4))
    path = f'/tutors/state/{st.lower()}/'
    body = (f'<div class="post-layout">\n<div class="post">\n'
            f'<a class="muted" href="/tutors/">← Tutor directory</a>\n'
            f'<h1>Private tutors in <span class="gold">{e(stname)}</span></h1>\n'
            f'<p class="muted">{len(ts)} in-person and online tutors in {e(stname)} for {e(top)} and more.</p>\n'
            f'<form class="tutor-filter" onsubmit="return false"><input type="search" id="tutor-q" placeholder="Search by name, city or subject" aria-label="Search tutors">'
            f'<select id="tutor-subject" aria-label="Subject"><option value="">All subjects</option>{opts}</select></form>\n'
            f'<p class="muted" id="tutor-count">{len(ts)} tutors</p>\n'
            f'{DISCLOSURE}\n<div class="tutor-grid">\n' + '\n'.join(card(t) for t in ts) + '\n</div>\n</div>\n'
            f'{sidebar()}\n</div>\n{FILTER_JS}')
    os.makedirs(os.path.join(OUT, 'state', st.lower()))
    with open(os.path.join(OUT, 'state', st.lower(), 'index.html'), 'w', encoding='utf-8') as f:
        f.write(page(f'{len(ts)} Private Tutors in {stname} — {top} | Dealux Tutors',
                     f'Find {len(ts)} private tutors in {stname} for {top} and {len(sc)} other subjects, with hourly rates and profiles from the Wyzant network.',
                     path, body))

# ---- hub: one featured tutor per state (longest bio), then the state and subject index
featured = sorted((max(ts, key=lambda t: (bool(t['img']), len(t['desc']))) for ts in by_state.values()),
                  key=lambda t: STATES.get(t['st'], t['st']))
subj_chips = ''.join(f'<a class="chip" href="/tutors/state/{max(by_state, key=lambda st: sum(s in t["subs"] for t in by_state[st])).lower()}/?subject={e(s)}">{e(s)} <span class="muted">{k}</span></a>'
                     for s, k in subj_count.most_common(30))
body = (f'<section class="hero">\n  <h1>Find a <span class="gold">tutor</span> near you</h1>\n'
        f'  <p class="muted">{len(rows):,} private tutors across {len(by_state)} states — math, reading, test prep, science, languages, music and more, with hourly rates and full profiles.</p>\n</section>\n'
        f'<div class="post-layout">\n<div class="post">\n'
        f'<h2>Browse tutors by state</h2>\n<nav class="dept-chips" aria-label="States">{state_links}</nav>\n'
        f'<h2>Featured tutors</h2>\n{DISCLOSURE}\n<div class="tutor-grid">\n' + '\n'.join(card(t) for t in featured) + '\n</div>\n'
        f'<h2>Popular subjects</h2>\n<nav class="dept-chips" aria-label="Subjects">{subj_chips}</nav>\n'
        f'</div>\n{sidebar()}\n</div>')
with open(os.path.join(OUT, 'index.html'), 'w', encoding='utf-8') as f:
    f.write(page('Private Tutors Near You — Math, Reading, SAT/ACT & More | Dealux Tutors',
                 f'Browse {len(rows):,} private tutors in {len(by_state)} states. Compare hourly rates, subjects and profiles, then book lessons through the Wyzant network.',
                 '/tutors/', body))

# ---- sitemap
urls = ['/tutors/'] + [f'/tutors/state/{st.lower()}/' for st in sorted(by_state)] + [t['href'] for t in rows]
with open(os.path.join(ROOT, 'sitemap-tutors.xml'), 'w', encoding='utf-8') as f:
    f.write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            + ''.join(f'  <url><loc>{SITE}{u}</loc><lastmod>{TODAY}</lastmod><changefreq>weekly</changefreq>'
                      f'<priority>{"0.8" if u.count("/") <= 4 and "state" in u or u == "/tutors/" else "0.6"}</priority></url>\n' for u in urls)
            + '</urlset>\n')
idx_path = os.path.join(ROOT, 'sitemap-index.xml')
idx = open(idx_path, encoding='utf-8').read()
loc = f'{SITE}/sitemap-tutors.xml'
idx = re.sub(r'\s*<sitemap><loc>' + re.escape(loc) + r'</loc>.*?</sitemap>', '', idx)
idx = idx.replace('</sitemapindex>', f'  <sitemap><loc>{loc}</loc><lastmod>{TODAY}</lastmod></sitemap>\n</sitemapindex>')
with open(idx_path, 'w', encoding='utf-8') as f:
    f.write(idx)
print(f'{len(rows)} tutors, {len(by_state)} states, {len(urls)} sitemap URLs')
