#!/usr/bin/env python3
"""Publish generated brand articles into /journal/ (indexable, in sitemap).

Usage: python3 scripts/import-journal-articles.py articles.jsonl [dealux-articles.csv ...] --directory advertiser-directory.csv
Inputs are the JSONL checkpoint / CSV written by build_articles.py. Re-running is idempotent.
"""
import csv, html, json, re, sys, importlib.util, unicodedata
from datetime import date
from pathlib import Path

csv.field_size_limit(10**8)
SITE = 'https://dealuxapp.com'
TODAY = date.today().isoformat()
TEMPLATE = Path('journal/your-first-esim-a-beginner-s-guide-to-prepaid-travel-data/index.html').read_text(encoding='utf-8')
CTA = {  # (button label, lead-in)
    'en': ('Visit {b}', 'Ready to take a closer look?'), 'de': ('{b} besuchen', 'Neugierig geworden?'),
    'nl': ('Bekijk {b}', 'Benieuwd geworden?'), 'es': ('Visitar {b}', '¿Quieres saber más?'),
    'fr': ('Découvrir {b}', 'Envie d’en savoir plus ?'), 'it': ('Visita {b}', 'Vuoi saperne di più?'),
    'pt-BR': ('Visitar {b}', 'Quer saber mais?'), 'pt-PT': ('Visitar {b}', 'Quer saber mais?'),
    'pl': ('Odwiedź {b}', 'Chcesz dowiedzieć się więcej?'), 'sv': ('Besök {b}', 'Vill du veta mer?'),
    'da': ('Besøg {b}', 'Vil du vide mere?'), 'nb': ('Besøk {b}', 'Vil du vite mer?'),
    'fi': ('Käy sivustolla: {b}', 'Haluatko tietää lisää?'), 'hr': ('Posjetite {b}', 'Želite saznati više?'),
    'el': ('Επισκεφθείτε το {b}', 'Θέλετε να μάθετε περισσότερα;'), 'ro': ('Vizitați {b}', 'Vreți să aflați mai mult?'),
    'sk': ('Navštívte {b}', 'Chcete vedieť viac?'), 'bg': ('Посетете {b}', 'Искате да научите повече?'),
}
e = lambda s: html.escape(s or '', quote=True)


def sponsor(m):
    """Mark an external anchor as an affiliate link without duplicating attributes."""
    tag = m.group(0)
    url = e(html.unescape(re.search(r'href="([^"]*)"', tag).group(1)))
    existing = re.search(r'\brel="([^"]*)"', tag)
    tokens = existing.group(1).split() if existing else []
    for token in ('sponsored', 'nofollow', 'noopener'):
        if token not in tokens:
            tokens.append(token)
    tag = re.sub(r'\s*\brel="[^"]*"', '', tag)
    tag = re.sub(r'\s*\btarget="[^"]*"', '', tag)
    tag = re.sub(r'href="[^"]*"', f'href="{url}"', tag, count=1)
    return re.sub(r'^<a\b', f'<a rel="{" ".join(tokens)}" target="_blank"', tag)


def slugify(s):
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+', '-', s).strip('-')


args = sys.argv[1:]
dpath = args[args.index('--directory') + 1]
args = [a for i, a in enumerate(args) if a != '--directory' and (i == 0 or args[i - 1] != '--directory')]
sector = {r['advertiserId']: r['primarySector'] for r in csv.DictReader(open(dpath, encoding='utf-8-sig'))}

records = {}
for path in args:
    if path.endswith('.jsonl'):
        recs = [json.loads(l) for l in open(path, encoding='utf-8') if l.strip()]
    else:
        recs = list(csv.DictReader(open(path, encoding='utf-8-sig')))
    for r in recs:
        records[r['slug']] = r

head, rest = TEMPLATE.split('<article class="post">', 1)
tail = rest.split('</article>', 1)[1]
for slug, r in records.items():
    if not slug or slug.startswith('-'):
        continue
    title, meta, lang = r['title'].strip(), r['meta_description'].strip(), r.get('language') or 'en'
    brand = re.sub(r'\s+', ' ', re.sub(r'\s*[\(\-–]?\s*\b(US|UK|GB|DE|NL|SE|ES|FR|IT|PL|BR|BNL|DACH|WW)\b\)?\s*$', '', r['programmeName'])).strip() or r['programmeName']
    body = r['article_html']
    words = len(re.sub(r'<[^>]+>', ' ', body).split())
    # Pull the closing affiliate disclosure out so the call to action sits just above it.
    m = re.search(r'\s*<p><em>.*?</em></p>\s*$', body, re.S)
    disclosure = m.group(0).strip() if m else ''
    body = body[:m.start()] if m else body
    label, lead = CTA.get(lang, CTA['en'])
    url = r['displayUrl']
    cta = (f'\n<div class="card promo-card article-cta"><p><strong>{e(lead)}</strong></p>'
           f'<a class="btn btn-gold" href="{e(url)}" target="_blank" rel="sponsored nofollow noopener">{e(label.format(b=brand))} →</a></div>\n')
    body = re.sub(r'<a\b[^>]*\bhref="https?://[^"]*"[^>]*>', sponsor, body)
    content = body + cta + disclosure
    topic = slugify(sector.get(r['advertiserId'], '') .split('&')[0]) or 'journal'
    canonical = f'{SITE}/journal/{slug}/'
    ld = json.dumps({"@context": "https://schema.org", "@type": "Article", "headline": title, "description": meta,
                     "mainEntityOfPage": canonical, "inLanguage": lang, "datePublished": TODAY, "dateModified": TODAY,
                     "author": {"@type": "Organization", "name": "Dealux"},
                     "publisher": {"@type": "Organization", "name": "Dealux", "url": SITE}}, ensure_ascii=False)
    h = head
    h = re.sub(r'<html lang="[^"]*">', f'<html lang="{e(lang)}">', h)
    h = re.sub(r'<title>.*?</title>', lambda m: f'<title>{e(title)} — Dealux Journal</title>', h, flags=re.S)
    h = re.sub(r'(<meta name="description" content=")[^"]*"', lambda m: m[1] + e(meta) + '"', h)
    h = re.sub(r'(<meta (?:property|name)="(?:og|twitter):description" content=")[^"]*"', lambda m: m[1] + e(meta) + '"', h)
    h = re.sub(r'(<meta (?:property|name)="(?:og|twitter):title" content=")[^"]*"', lambda m: m[1] + e(title) + '"', h)
    h = re.sub(r'<link rel="canonical" href="[^"]*">', lambda m: f'<link rel="canonical" href="{canonical}">', h)
    h = re.sub(r'<meta property="og:url" content="[^"]*">', lambda m: f'<meta property="og:url" content="{canonical}">', h)
    h = re.sub(r'<script type="application/ld\+json">.*?</script>', lambda m: f'<script type="application/ld+json">{ld}</script>', h, count=1, flags=re.S)
    page = (h + '<article class="post">\n  <a class="muted" href="/journal/">← The Journal</a>\n'
            f'  <span class="eyebrow">{e(topic.replace("-", " ").title())} · {max(1, round(words / 200))} min read</span>\n'
            f'  <h1>{e(title)}</h1>\n  \n  <div class="post-body"><div class="post-content">\n'
            '<p class="disclosure"><em>Disclosure: Dealux may earn a commission on purchases made through links on this page, at no extra cost to you.</em></p>\n'
            f'{content}\n</div></div>\n  \n</article>' + tail)
    out = Path('journal') / slug
    out.mkdir(parents=True, exist_ok=True)
    (out / 'index.html').write_text(page, encoding='utf-8')

spec = importlib.util.spec_from_file_location('ji', Path(__file__).with_name('journal_index.py'))
ji = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ji)
print(len(records), 'articles written;', len(ji.refresh()), 'in journal index')
