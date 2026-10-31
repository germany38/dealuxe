#!/usr/bin/env python3
"""Import the newest posts from the Dealux Blogger blogs into the Journal.

Usage: python3 scripts/import-blogger.py [feed.json | blog URL ...]
  With no arguments every blog in BLOGS is fetched. A feed.json is
  https://<blog>.blogspot.com/feeds/posts/default?alt=json&max-results=150

Each post the Journal doesn't have yet becomes /journal/<slug>/ built from an
existing article page, and is added to journal.json, the Journal grid and the
sitemaps. Job listings (see JOBS) become /jobs/<slug>/ pages on the Jobs board
instead. Posts are matched on title so re-running is a no-op.
"""
import datetime, html, json, os, re, sys, unicodedata, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
SITE = 'https://dealuxapp.com'
TEMPLATE = 'journal/the-ultimate-guide-to-mac-virtualization-streamline-cross-platform-workflows-wit/index.html'
SINCE = '2026-10-21'
JOB_TEMPLATE = 'jobs/agent-engineer/index.html'
BLOGS = ['https://dealuxbestoffers.blogspot.com/', 'https://dealuxdeals.blogspot.com/']

# Posts whose titles don't transliterate to a useful slug.
SLUGS = {
    'ticombo-ticombo-singapore-tixprotect': 'ticombo-singapore-live-event-tickets-safe-buying-guide-ta',
    'blog-post_19': 'ticombo-singapore-concert-sports-tickets-guide-zh',
}
# Blogger post key -> (company, location, type, job family) for posts that are job listings.
JOBS = {
    'featured-teach-abroad-opportunity-teach': ('Guangzhou Pinxin Human Resources Management Co., Ltd',
                                                'Guangdong, China', 'full-time', 'teaching'),
    'global-online-english-teaching': ('Fonpeng Limited', 'Remote — Global', 'part-time', 'teaching'),
    'the-ultimate-guide-to-landing-remote': ('Rancca Online Education', 'Remote — Global', 'part-time', 'teaching'),
}
FAMILIES = {'teaching': 'Teaching &amp; Education'}
TOPICS = [
    (r'english|british council|academy|education|tutor|книгарн|книг|літератур', 'education'),
    (r'pet\b|pets|тварин|zoo', 'pets'),
    (r'jewel|прикрас|ювелір|palmonas', 'jewelry'),
    (r'skincare|beauty|cosmetic|perfume|parfum|fragrance|cologne|grooming|ayurveda|wig|hair|lingerie|косметик|парфум|аромат|догляд|zapach|perfumy', 'beauty'),
    (r'sport|fitness|running|footwear|sneaker|gps watch|decathlon|спорт|бігу', 'sports'),
    (r'sushi|pizza|meal|food|restaurant|nutrition|суші|піц|ресторан|продукт|кухн', 'food-drink'),
    (r'baby|toddler|nursery|little spoon|mamas|hydration|water|air quality|levoit', 'home'),
    (r'myntra|levi|fashion', 'fashion'),
    (r'ticombo|ticket|entradas|boletos|tiket|门票|டிக்கெட்', 'entertainment'),
    (r'insurance|medicare|credit|loan|finance', 'finance'),
    (r'holiday|getaway|travel|hotel|air france|airasia|flying', 'travel'),
    (r'game|gamivo|software|vpn|remotive|remote jobs', 'technology'),
    (r'shopping|consumertestconnect|rewards', 'gifts'),
    (r'bank|forex|trading|invest|p2p|insur|legal|law|trademark|business|кредит|банк|страх|фінанс|ubezpiecz|pojišt|půjčk', 'finance'),
    (r'bus|flight|авіа|автобус|квитк|подорож', 'travel'),
    (r'furniture|kitchen|appliance|home|garden|interior|textile|сад|текстил|побутов|меблі|curtain|ستائر|ديكور', 'home'),
    (r'tech|electronic|gadget|smartphone|phone|hosting|server|cloud|proxy|software|wearable|security|ПК|техн|електрон|гаджет|смартфон|الإلكترونيات|الهواتف|ігров|cs2|case opening|gaming|vpn|digital', 'technology'),
    (r'fashion|clothing|apparel|одяг|гардероб|trikotaž|трикотаж|шкарпет|dkny|أناقة', 'fashion'),
    (r'concert|music|концерт|музик', 'entertainment'),
]
CYRILLIC = dict(zip('абвгґдеєжзиіїйклмнопрстуфхцчшщьюяыэъё',
                    'a b v h g d e ye zh z y i yi y k l m n o p r s t u f kh ts ch sh shch _ yu ya y e _ yo'.split()))
CYRILLIC.update({'ь': '', 'ъ': ''})


def slugify(s):
    s = ''.join(CYRILLIC.get(c, c) if c.islower() else CYRILLIC.get(c.lower(), c).title() for c in s)
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+', '-', s).strip('-')


def text(s):
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', s or ''))).strip()


def load_feed(src):
    if not src.startswith('http'):
        return json.load(open(src, encoding='utf-8'))['feed'].get('entry', [])
    base, entries = src.split('/feeds/')[0].rstrip('/'), []
    while True:  # Blogger caps a feed page at 150 posts
        url = f'{base}/feeds/posts/default?alt=json&max-results=150&start-index={len(entries) + 1}'
        page = json.load(urllib.request.urlopen(url, timeout=60))['feed'].get('entry', [])
        entries += page
        if len(page) < 150 or page[-1]['published']['$t'][:10] < SINCE:
            return entries


def main(sources):
    feed = [e for src in sources for e in load_feed(src)]
    journal = json.load(open('journal.json', encoding='utf-8'))
    have_titles = {p[1].lower() for p in journal}
    have_slugs = {p[0] for p in journal}
    template = open(TEMPLATE, encoding='utf-8').read()
    job_template = open(JOB_TEMPLATE, encoding='utf-8').read()
    have_slugs |= set(os.listdir('jobs'))
    new, jobs = [], []
    for e in sorted(feed, key=lambda e: e['published']['$t']):
        date = e['published']['$t'][:10]
        if date < SINCE:
            continue
        raw = e['content']['$t']
        # Some posts were pasted with an AI draft (LinkedIn copy + fenced HTML) in front.
        if '```html' in raw:
            raw = raw.split('```html', 1)[1].rsplit('```', 1)[0]
        h1 = re.search(r'<h1[^>]*>(.*?)</h1>', raw, re.S)
        title = text(h1.group(1) if h1 else (re.search(r'<title>(.*?)</title>', raw, re.S) or [None, ''])[1])
        if not title or title.lower() in have_titles:
            continue
        url = next(l['href'] for l in e['link'] if l['rel'] == 'alternate')
        key = url.rsplit('/', 1)[1].removesuffix('.html')
        slug = SLUGS.get(key) or slugify(title)[:80].strip('-')
        if len(slug) < 12:  # e.g. Arabic titles: keep the Latin words and the Blogger key
            slug = slugify(f'{title} {key}')[:80].strip('-')
        if key in JOBS and slug in os.listdir('jobs'):
            continue  # job already on the board (the blogs repeat some listings)
        while slug in have_slugs:
            slug += '-2'
        have_slugs.add(slug)
        have_titles.add(title.lower())

        body = re.search(r'<body[^>]*>(.*)</body>', raw, re.S)
        body = body.group(1) if body else raw
        body = re.sub(r'<(style|script)[^>]*>.*?</\1>', '', body, flags=re.S)
        body = re.sub(r'<h1[^>]*>.*?</h1>', '', body, count=1, flags=re.S).strip()
        m = re.search(r'<meta name="description" content="([^"]*)"', raw)
        desc = text(m.group(1)) if m else text(body)
        if len(desc) > 160:  # cut at a word boundary so search snippets don't end mid-word
            desc = desc[:157].rsplit(' ', 1)[0].rstrip(' ,.;:—-') + '…'
        desc = html.escape(desc, quote=True)
        topic = next((t for pat, t in TOPICS if re.search(pat, title + ' ' + key, re.I)), 'gifts')
        words = len(text(body).split())
        pretty = datetime.date.fromisoformat(date).strftime('%b %-d, %Y')
        t = html.escape(title)

        if key in JOBS:
            jobs.append(job_page(job_template, slug, t, desc, body, date, url, raw, JOBS[key]))
            continue

        h = template
        h = re.sub(r'<title>.*?</title>', lambda _: f'<title>{t} — Dealux Journal</title>', h, count=1)
        h = re.sub(r'<meta name="description" content="[^"]*">', lambda _: f'<meta name="description" content="{desc}">', h, count=1)
        h = re.sub(r'<link rel="canonical" href="[^"]*">', lambda _: f'<link rel="canonical" href="{SITE}/journal/{slug}/">', h, count=1)
        img = next((i for i in re.findall(r'<img[^>]+src="(https?://[^"]+)"', body)), '')
        # Social cards and Article structured data so shares and search results look right.
        ld = json.dumps({'@context': 'https://schema.org', '@type': 'Article', 'headline': title[:110],
                         'description': html.unescape(desc), 'datePublished': date, 'dateModified': date,
                         'mainEntityOfPage': f'{SITE}/journal/{slug}/', **({'image': [img]} if img else {}),
                         'author': {'@type': 'Organization', 'name': 'Dealux'},
                         'publisher': {'@type': 'Organization', 'name': 'Dealux', 'url': SITE}},
                        ensure_ascii=False).replace('</', '<\\/')
        seo = (f'\n<meta property="og:type" content="article">\n<meta property="og:site_name" content="Dealux">'
               f'\n<meta property="og:title" content="{t}">\n<meta property="og:description" content="{desc}">'
               f'\n<meta property="og:url" content="{SITE}/journal/{slug}/">'
               + (f'\n<meta property="og:image" content="{html.escape(img, quote=True)}">' if img else '')
               + f'\n<meta property="article:published_time" content="{date}">'
               f'\n<meta name="twitter:card" content="{"summary_large_image" if img else "summary"}">'
               f'\n<meta name="twitter:title" content="{t}">\n<meta name="twitter:description" content="{desc}">'
               f'\n<script type="application/ld+json">{ld}</script>')
        h = h.replace('\n<link rel="icon"', seo + '\n<link rel="icon"', 1)
        h = re.sub(r'<span class="eyebrow">[^<]*· \d+ min read</span>',
                   lambda _: f'<span class="eyebrow">{topic.replace("-", " ").title()} · {pretty} · {max(1, round(words / 230))} min read</span>', h, count=1)
        h = re.sub(r'(<article class="post">.*?)<h1>.*?</h1>', lambda m: f'{m.group(1)}<h1>{t}</h1>', h, count=1, flags=re.S)
        h = re.sub(r'<div class="post-body"><div class="post-content">.*?</div></div>\n  \n</article>',
                   lambda _: f'<div class="post-body"><div class="post-content">\n{body}\n</div></div>\n  \n</article>', h, count=1, flags=re.S)
        # Every Journal article carries the template's left and right sidebars.
        if h.count('<aside class="post-sidebar') != 2 or body not in h:
            sys.exit(f'Could not build {slug} with both sidebars from {TEMPLATE}')
        os.makedirs(f'journal/{slug}', exist_ok=True)
        open(f'journal/{slug}/index.html', 'w', encoding='utf-8').write(h)
        new.append([slug, title, topic, date, ''])

    if jobs:
        add_jobs(jobs)
    if not new:
        print('Nothing new to import.' if not jobs else 'No new Journal articles.')
        return
    new.reverse()  # newest first, like journal.json
    journal = new + journal
    for path in ('journal.json', 'data/journal.json'):
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(journal, f, ensure_ascii=False, separators=(',', ':'))

    idx = open('journal/index.html', encoding='utf-8').read()
    cards = ''.join(f'<a class="card post-card" href="/journal/{p[0]}/">\n  \n  <span class="eyebrow">{p[2].replace("-", " ").title()} · '
                    f'{datetime.date.fromisoformat(p[3]).strftime("%b %-d, %Y")}</span>\n  <h3>{html.escape(p[1])}</h3>\n</a>' for p in new)
    idx = idx.replace('<div class="grid" data-results>', '<div class="grid" data-results>' + cards, 1)
    idx = re.sub(r'\b\d[\d,]* articles\b', f'{len(journal):,} articles', idx)
    open('journal/index.html', 'w', encoding='utf-8').write(idx)

    sm = open('sitemap-journal.xml', encoding='utf-8').read()
    add = ''.join(f'  <url>\n    <loc>{SITE}/journal/{p[0]}/</loc>\n    <lastmod>{p[3]}</lastmod>\n    <changefreq>weekly</changefreq>\n    <priority>0.7</priority>\n  </url>\n'
                  for p in new)
    sm = sm.replace('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + add, 1)
    open('sitemap-journal.xml', 'w', encoding='utf-8').write(sm)
    today = datetime.date.today().isoformat()
    si = open('sitemap-index.xml', encoding='utf-8').read()
    si = re.sub(r'(<loc>[^<]*/sitemap-journal\.xml</loc><lastmod>)[^<]*', lambda m: m.group(1) + today, si)
    open('sitemap-index.xml', 'w', encoding='utf-8').write(si)
    print(f'{len(new)} new articles:', *[p[0] for p in new], sep='\n  ')


def job_page(template, slug, t, desc, body, date, url, raw, meta):
    company, location, kind, family = meta
    apply = next((a for a in re.findall(r'href="(https?://[^"]+)"', raw) if 'blogspot.com' not in a), url)
    btn = f'<p><a class="btn btn-gold" href="{html.escape(apply)}" target="_blank" rel="sponsored noopener">Apply now →</a></p>'
    h = template
    h = re.sub(r'<title>.*?</title>', lambda _: f'<title>{t} — Dealux Jobs</title>', h, count=1)
    h = re.sub(r'<meta name="description" content="[^"]*">', lambda _: f'<meta name="description" content="{desc}">', h, count=1)
    h = re.sub(r'<link rel="canonical" href="[^"]*">', lambda _: f'<link rel="canonical" href="{SITE}/jobs/{slug}/">', h, count=1)
    h = re.sub(r'(<article class="post">.*?)<h1>.*?</h1>', lambda m: f'{m.group(1)}<h1>{t}</h1>', h, count=1, flags=re.S)
    h = re.sub(r'<p class="muted"><b>Company:</b>.*?</p>',
               lambda _: f'<p class="muted"><b>Company:</b> {html.escape(company)} · <b>Location:</b> {location} · '
                         f'<b>Type:</b> {kind} · <b>Posted:</b> {date}</p>', h, count=1)
    h = re.sub(r'<p><a class="btn btn-gold" href="[^"]*" target="_blank" rel="sponsored noopener">Apply now →</a></p>\n  <div class="post-body">.*?</div>\n  <p><a class="btn btn-gold"[^\n]*</p>',
               lambda _: f'{btn}\n  <div class="post-body">\n{body}\n  </div>\n  {btn}', h, count=1, flags=re.S)
    plain = text(body)
    loc_type = '"jobLocationType":"TELECOMMUTE","applicantLocationRequirements":{"@type":"Country","name":"Worldwide"}' \
        if location.startswith('Remote') else \
        f'"jobLocation":{{"@type":"Place","address":{{"@type":"PostalAddress","addressRegion":{json.dumps(location.split(",")[0])},"addressCountry":"CN"}}}}'
    ld = (f'<script type="application/ld+json">{{"@context":"https://schema.org","@type":"JobPosting",'
          f'"title":{json.dumps(html.unescape(t), ensure_ascii=False)},"description":{json.dumps(plain[:4000], ensure_ascii=False)},'
          f'"datePosted":"{date}","employmentType":"{kind.upper().replace("-", "_")}",'
          f'"hiringOrganization":{{"@type":"Organization","name":{json.dumps(company)}}},{loc_type},'
          f'"directApply":false,"url":"{SITE}/jobs/{slug}/"}}</script>')
    h = h.replace('</head>', ld + '\n</head>', 1)
    os.makedirs(f'jobs/{slug}', exist_ok=True)
    open(f'jobs/{slug}/index.html', 'w', encoding='utf-8').write(h)
    summary = html.escape(html.unescape(desc))
    return dict(slug=slug, title=t, company=company, location=location, kind=kind, family=family, date=date, summary=summary)


def add_jobs(jobs):
    idx = open('jobs/index.html', encoding='utf-8').read()
    cards = ''.join(
        f'<a class="card job-card" href="/jobs/{j["slug"]}/" data-family="{j["family"]}" '
        f'data-text="{html.escape(html.unescape(j["title"]).lower())} {html.escape(j["company"].lower())} '
        f'{FAMILIES[j["family"]].lower()} {j["kind"]} {j["location"].lower()}" '
        f'style="display:block;padding:16px;margin:0 0 12px;text-decoration:none">\n'
        f'  <h3 style="margin:0 0 6px">{j["title"]}</h3>\n'
        f'  <p class="muted" style="margin:0 0 6px">{html.escape(j["company"])} · {j["location"]} · {FAMILIES[j["family"]]}</p>\n'
        f'  <p style="margin:0">{j["summary"]}</p>\n</a>\n' for j in jobs)
    idx = idx.replace('<div id="job-list">\n', '<div id="job-list">\n' + cards, 1)
    total = idx.count('class="card job-card"')
    idx = re.sub(r'\b\d[\d,]* (remote contract roles|remote roles|jobs</p>)', lambda m: f'{total} {m.group(1)}', idx)
    for fam, label in FAMILIES.items():
        n = idx.count(f'data-family="{fam}"')
        opt = f'<option value="{fam}">{label} ({n})</option>'
        if f'<option value="{fam}">' in idx:
            idx = re.sub(rf'<option value="{fam}">[^<]*</option>', lambda _: opt, idx, count=1)
        else:
            idx = idx.replace('</select>', opt + '</select>', 1)
    open('jobs/index.html', 'w', encoding='utf-8').write(idx)

    sm = open('sitemap-jobs.xml', encoding='utf-8').read()
    add = ''.join(f'  <url>\n    <loc>{SITE}/jobs/{j["slug"]}/</loc>\n    <lastmod>{j["date"]}</lastmod>\n    <changefreq>weekly</changefreq>\n    <priority>0.7</priority>\n  </url>\n'
                  for j in jobs)
    sm = re.sub(r'(<loc>https://dealuxapp.com/jobs/</loc>\n    <lastmod>)[^<]*(</lastmod>\n.*?</url>\n)',
                lambda m: m.group(1) + datetime.date.today().isoformat() + m.group(2) + add, sm, count=1, flags=re.S)
    open('sitemap-jobs.xml', 'w', encoding='utf-8').write(sm)
    si = open('sitemap-index.xml', encoding='utf-8').read()
    si = re.sub(r'(<loc>[^<]*/sitemap-jobs\.xml</loc><lastmod>)[^<]*', lambda m: m.group(1) + datetime.date.today().isoformat(), si)
    open('sitemap-index.xml', 'w', encoding='utf-8').write(si)
    print(f'{len(jobs)} new jobs:', *[j['slug'] for j in jobs], sep='\n  ')


if __name__ == '__main__':
    main(sys.argv[1:] or BLOGS)
