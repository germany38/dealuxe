#!/usr/bin/env python3
"""Import the newest posts from the Dealux Blogger blog into the Journal.

Usage: python3 scripts/import-blogger.py path/to/feed.json
  (feed.json = https://dealuxbestoffers.blogspot.com/feeds/posts/default?alt=json&max-results=150)

Each post the Journal doesn't have yet becomes /journal/<slug>/ built from an
existing article page, and is added to journal.json, the Journal grid and the
sitemaps. Posts are matched on title so re-running is a no-op.
"""
import datetime, html, json, os, re, sys, unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
SITE = 'https://dealuxapp.com'
TEMPLATE = 'journal/the-ultimate-guide-to-mac-virtualization-streamline-cross-platform-workflows-wit/index.html'
SINCE = '2026-10-18'

# Posts whose titles don't transliterate to a useful slug.
SLUGS = {
    'ticombo-ticombo-singapore-tixprotect': 'ticombo-singapore-live-event-tickets-safe-buying-guide-ta',
    'blog-post_19': 'ticombo-singapore-concert-sports-tickets-guide-zh',
}
TOPICS = [
    (r'ticombo|ticket|entradas|boletos|tiket|门票|டிக்கெட்', 'entertainment'),
    (r'insurance|medicare|credit|loan|finance', 'finance'),
    (r'holiday|getaway|travel|hotel', 'travel'),
    (r'game|gamivo|software|vpn', 'technology'),
]


def slugify(s):
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+', '-', s).strip('-')


def text(s):
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', s or ''))).strip()


def main(feed_path):
    feed = json.load(open(feed_path, encoding='utf-8'))['feed']['entry']
    journal = json.load(open('journal.json', encoding='utf-8'))
    have_titles = {p[1].lower() for p in journal}
    have_slugs = {p[0] for p in journal}
    template = open(TEMPLATE, encoding='utf-8').read()
    new = []
    for e in sorted(feed, key=lambda e: e['published']['$t']):
        date = e['published']['$t'][:10]
        if date < SINCE:
            continue
        raw = e['content']['$t']
        h1 = re.search(r'<h1[^>]*>(.*?)</h1>', raw, re.S)
        title = text(h1.group(1) if h1 else (re.search(r'<title>(.*?)</title>', raw, re.S) or [None, ''])[1])
        if not title or title.lower() in have_titles:
            continue
        url = next(l['href'] for l in e['link'] if l['rel'] == 'alternate')
        key = url.rsplit('/', 1)[1].removesuffix('.html')
        slug = SLUGS.get(key) or slugify(title)[:80].strip('-') or key
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
        desc = html.escape(desc[:160], quote=True)
        topic = next((t for pat, t in TOPICS if re.search(pat, title + ' ' + key, re.I)), 'gifts')
        words = len(text(body).split())
        pretty = datetime.date.fromisoformat(date).strftime('%b %-d, %Y')
        t = html.escape(title)

        h = template
        h = re.sub(r'<title>.*?</title>', lambda _: f'<title>{t} — Dealux Journal</title>', h, count=1)
        h = re.sub(r'<meta name="description" content="[^"]*">', lambda _: f'<meta name="description" content="{desc}">', h, count=1)
        h = re.sub(r'<link rel="canonical" href="[^"]*">', lambda _: f'<link rel="canonical" href="{SITE}/journal/{slug}/">', h, count=1)
        h = re.sub(r'<span class="eyebrow">[^<]*· \d+ min read</span>',
                   lambda _: f'<span class="eyebrow">{topic.replace("-", " ").title()} · {pretty} · {max(1, round(words / 230))} min read</span>', h, count=1)
        h = re.sub(r'(<article class="post">.*?)<h1>.*?</h1>', lambda m: f'{m.group(1)}<h1>{t}</h1>', h, count=1, flags=re.S)
        h = re.sub(r'<div class="post-body"><div class="post-content">.*?</div></div>\n  \n</article>',
                   lambda _: f'<div class="post-body"><div class="post-content">\n{body}\n</div></div>\n  \n</article>', h, count=1, flags=re.S)
        os.makedirs(f'journal/{slug}', exist_ok=True)
        open(f'journal/{slug}/index.html', 'w', encoding='utf-8').write(h)
        new.append([slug, title, topic, date, ''])

    if not new:
        print('Nothing new to import.')
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


if __name__ == '__main__':
    main(sys.argv[1])
