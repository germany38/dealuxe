import datetime
import html
import json
import re
from pathlib import Path

SITE = 'https://dealuxapp.com'
INITIAL = 48
SITEMAP_SIZE = 10000


def write(path, content):
    if not path.exists() or path.read_text(encoding='utf-8') != content:
        path.write_text(content, encoding='utf-8')


def from_page(path):
    source = path.read_text(encoding='utf-8').split('</head>', 1)[0]
    slug = path.parent.name
    if f'<link rel="canonical" href="{SITE}/journal/{slug}/">' not in source or re.search(r'<meta name="robots" content="[^"]*noindex', source):
        return None
    for block in re.findall(r'<script type="application/ld\+json">(.*?)</script>', source, re.S):
        article = json.loads(block)
        if not isinstance(article, dict) or article.get('@type') not in ('Article', 'BlogPosting', 'NewsArticle'):
            continue
        title = re.search(r'<title>(.*?)</title>', source, re.S)
        return [slug, html.unescape(title[1].removesuffix(' — Dealux Journal')) if title else article['headline'],
                'amazon' if slug.startswith(('amazon-', 'audible-', 'kindle-', 'prime-')) else 'journal',
                article['datePublished'][:10], re.search(r'<meta property="og:image" content="([^"]*)"', source)[1]
                if '<meta property="og:image" content="' in source else '']
    return None


def refresh():
    inventory = Path('journal.json')
    pages = {path.parent.name: path for path in Path('journal').glob('*/index.html')}
    posts = {post[0]: post for post in json.loads(inventory.read_text()) if post[0] in pages}
    for slug in pages.keys() - posts.keys():
        post = from_page(pages[slug])
        if post:
            posts[slug] = post
    ordered = sorted(posts.values(), key=lambda post: (datetime.date.fromisoformat(post[3]), post[0]), reverse=True)
    records = '[\n' + ',\n'.join(json.dumps(post, ensure_ascii=False, separators=(',', ':')) for post in ordered) + '\n]\n'
    for path in (inventory, Path('data/journal.json')):
        write(path, records)

    home = Path('journal/index.html')
    source = home.read_text()
    source = re.sub(r'\n?<!-- amazon-journal -->.*?<!-- /amazon-journal -->\n?', '\n', source, flags=re.S)
    source = re.sub(r'<meta name="description" content="[\d,]+ buying guides and articles\.">',
                    f'<meta name="description" content="{len(posts):,} buying guides and articles.">', source)
    source = re.sub(r'Search [\d,]+ articles…', f'Search {len(posts):,} articles…', source)
    if 'value="amazon"' not in source:
        source = source.replace('<option value="">All topics</option>', '<option value="">All topics</option><option value="amazon">Amazon</option>', 1)
    source = re.sub(r'data-result-count>[\d,]+ articles<', f'data-result-count>{len(posts):,} articles<', source)
    cards = []
    for slug, title, topic, date, image in ordered[:INITIAL]:
        thumb = f'<img loading="lazy" src="{html.escape(image, quote=True)}" alt="">' if image else ''
        cards.append(f'<a class="card post-card" href="/journal/{slug}/">{thumb}'
                     f'<span class="eyebrow">{html.escape(topic.replace("-", " ").title())} · <time datetime="{date}">{date}</time></span>'
                     f'<h3>{html.escape(title)}</h3></a>')
    source = re.sub(r'(<div class="grid" data-results>).*?(</div>)',
                    lambda match: match[1] + '\n' + '\n'.join(cards) + '\n' + match[2], source, count=1, flags=re.S)
    if 'id="amazon"' not in source:
        source = source.replace('</main>', '<p id="amazon"><a href="/journal/?topic=amazon">Browse all Amazon guides</a> · '
                                'As an Amazon Associate, Dealux earns from qualifying purchases.</p>\n</main>', 1)
    write(home, source)

    index = Path('sitemap-index.xml')
    current = index.read_text()
    current = re.sub(r'^\s*<sitemap><loc>https://dealuxapp\.com/sitemap-journal(?:-\d+)?\.xml</loc>.*?</sitemap>\n', '', current, flags=re.M)
    entries = []
    for offset in range(0, max(len(ordered), 1), SITEMAP_SIZE):
        slug = 'sitemap-journal' if not offset else f'sitemap-journal-{1 + offset // SITEMAP_SIZE}'
        batch = ordered[offset:offset + SITEMAP_SIZE]
        urls = ['  <url><loc>https://dealuxapp.com/journal/</loc></url>'] if not offset else []
        urls.extend(f'  <url><loc>{SITE}/journal/{post[0]}/</loc></url>' for post in batch)
        write(Path(f'{slug}.xml'), '<?xml version="1.0" encoding="UTF-8"?>\n'
              '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + '\n'.join(urls) + '\n</urlset>\n')
        entries.append(f'  <sitemap><loc>{SITE}/{slug}.xml</loc></sitemap>\n')
    write(index, current.replace('</sitemapindex>', ''.join(entries) + '</sitemapindex>'))
    return ordered
