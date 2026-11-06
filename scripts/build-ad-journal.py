#!/usr/bin/env python3
"""Write one Journal article per advertiser from the image ads in data/ads.json.

Usage: python3 scripts/build-ad-journal.py [impact-image-ads.csv ...]
  With CSV arguments, only advertisers (programs) in those exports get articles;
  with none, every advertiser in data/ads.json does. Run it after build-image-ads.py.

Each article (/journal/<brand>-offers-and-deals-guide/) is built from the Journal article
template (both sidebars included) and uses only facts from the ads themselves: the brand's
banners, ad descriptions, current deals and topics, each linking to its /ads/ offer page and
the tracked merchant link. Banner images load straight from the advertiser's image host.
Articles that already exist are skipped, so re-running is a no-op. New articles are added
to journal.json, data/journal.json, the Journal grid and sitemap-journal.xml.
"""
import csv, datetime, html, importlib.util, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
spec = importlib.util.spec_from_file_location('ib', 'scripts/import-blogger.py')
ib = importlib.util.module_from_spec(spec); spec.loader.exec_module(ib)
spec = importlib.util.spec_from_file_location('ia', 'scripts/build-image-ads.py')
ia = importlib.util.module_from_spec(spec); spec.loader.exec_module(ia)
SITE, esc = ib.SITE, ia.esc
TODAY = datetime.date.today().isoformat()
MAX_OFFERS = 24  # offers listed per article
MAX_BANNERS = 3  # banners shown per article
DISCLOSURE = ('<p class="muted"><em>Disclosure: Dealux may earn a commission if you buy through links on this page, '
              'at no extra cost to you. Prices, availability and offers are set by the merchant and can change — '
              'confirm the details on the merchant’s site before you buy.</em></p>')


def banner(a):
    # Many banners are named after their file (e.g. "300x250-2.png"); caption those with the brand instead.
    alt = a['alt'] if re.search(r'[a-z]{3,} [a-z]{3,}', a['alt'], re.I) and not re.search(r'\.(png|jpe?g|gif)$|\d+x\d+', a['alt'], re.I) else f"{a['brand']} offer"
    return (f'<figure><a href="{esc(a["link"])}" target="_blank" rel="sponsored noopener">{ia.img_tag(dict(a, alt=alt))}</a>'
            f'<figcaption class="muted">{esc(alt)}</figcaption></figure>')


def pick_banners(ads):
    """Prefer large, wide banners; one per distinct image size so the article isn't repetitive."""
    def area(a):
        try:
            return int(a['w']) * int(a['h'])
        except ValueError:
            return 0
    out, sizes = [], set()
    for a in sorted(ads, key=area, reverse=True):
        key = (a['w'], a['h'])
        if key not in sizes:
            sizes.add(key)
            out.append(a)
        if len(out) == MAX_BANNERS:
            break
    return out


def article(brand, ads):
    descs = list(dict.fromkeys(a['desc'] for a in ads if not a['desc'].startswith('“')))
    deals = list(dict.fromkeys(a['deal'] for a in ads if a.get('deal')))
    labels = list(dict.fromkeys(l for a in ads for l in a.get('labels', [])))[:12]
    ends = sorted({a['ends'] for a in ads if a.get('ends')})
    shown = pick_banners(ads)
    link = ads[0]['link']
    p = []
    p.append(f'<p>{esc(brand)} currently runs {len(ads)} partner offer{"s" if len(ads) != 1 else ""} on Dealux. '
             f'This guide collects them in one place: the banners, what each offer says, any current deals, and '
             f'practical tips for deciding whether {esc(brand)} is the right fit before you click through.</p>')
    p.append(banner(shown[0]))
    p.append(f'<h2>What {esc(brand)} offers</h2>')
    if descs:
        p.append(f'<p>In its own words, {esc(brand)} describes its current campaigns like this:</p>')
        p.append('<ul>' + ''.join(f'<li>{esc(d)}</li>' for d in descs[:6]) + '</ul>')
    else:
        p.append(f'<p>{esc(brand)}’s banners point to its latest promotions. Open any offer below to see the full '
                 f'details on the merchant’s own site.</p>')
    if labels:
        p.append(f'<p>The offers are tagged under: {esc(", ".join(labels))}.</p>')
    if deals:
        p.append('<h2>Current deals</h2><ul>' + ''.join(f'<li>{esc(d)}</li>' for d in deals[:8]) + '</ul>')
    if ends:
        p.append(f'<p class="muted">Some offers are limited-time; the earliest listed end date is {esc(ends[0])}.</p>')
    for a in shown[1:]:
        p.append(banner(a))
    p.append(f'<h2>All {esc(brand)} offers on Dealux</h2><ul>')
    for a in ads[:MAX_OFFERS]:
        d = f' — {esc(a["deal"])}' if a.get('deal') else ''
        p.append(f'<li><a href="/ads/{a["slug"]}/">{esc(a["name"])}</a>{d}</li>')
    p.append('</ul>')
    if len(ads) > MAX_OFFERS:
        p.append(f'<p class="muted">Plus {len(ads) - MAX_OFFERS} more in the <a href="/ads/">offers directory</a>.</p>')
    p.append(f'''<h2>How to get the most from a {esc(brand)} offer</h2>
<ul>
<li><b>Read the terms on the landing page.</b> Discounts often apply to selected items, first orders or a minimum spend.</li>
<li><b>Check the end date.</b> Limited-time offers can close early once stock or budget runs out.</li>
<li><b>Compare the final price.</b> Add shipping, taxes and any subscription renewal price before deciding.</li>
<li><b>Look for a code field.</b> If a deal mentions a promo code, enter it at checkout and confirm it applied.</li>
<li><b>Keep your confirmation.</b> Save the order email in case you need support, a return or a price adjustment.</li>
</ul>
<h2>Is {esc(brand)} right for you?</h2>
<p>Start with what you actually need, then use the offers above to see what {esc(brand)} is promoting right now.
Compare it with one or two alternatives on price, delivery or service terms, return policy and customer support,
and read independent reviews before larger purchases. Dealux lists offers so they are easy to find; it does not
test or endorse every product.</p>
<p><a class="btn btn-gold" href="{esc(link)}" target="_blank" rel="sponsored noopener">Visit {esc(brand)} →</a></p>
{DISCLOSURE}''')
    return '\n'.join(p), shown[0]


def main(paths):
    ads = json.load(open(ia.MANIFEST, encoding='utf-8'))
    pids = None
    if paths:
        pids = {r['ProgramId'] for p in paths for r in csv.DictReader(open(p, encoding='utf-8-sig'))}
    by = {}
    for a in ads:
        if pids is None or a['pid'] in pids:
            by.setdefault(a['pid'], []).append(a)
    journal = json.load(open('journal.json', encoding='utf-8'))
    have = {p[0] for p in journal} | set(os.listdir('journal'))
    template = open(ib.TEMPLATE, encoding='utf-8').read()
    new = []
    for pid, group in by.items():
        brand = group[0]['brand']
        slug = f'{ib.slugify(brand)[:50].strip("-") or "brand-" + pid}-offers-and-deals-guide'
        if slug in have:
            continue
        have.add(slug)
        body, lead = article(brand, group)
        title = f'{brand} Offers and Deals: A Shopper’s Guide'
        t = html.escape(title)
        desc = esc(f'Current {brand} offers on Dealux: {len(group)} partner deal{"s" if len(group) != 1 else ""}, '
                   f'what each includes, and tips to check before you buy.'[:160])
        img = ia.img_path(lead)
        words = len(ib.text(body).split())
        topic = next((tp for pat, tp in ib.TOPICS if re.search(pat, brand + ' ' + ' '.join(lead.get('labels', [])), re.I)), 'gifts')
        ld = json.dumps({'@context': 'https://schema.org', '@type': 'Article', 'headline': title[:110],
                         'description': html.unescape(desc), 'image': [img], 'datePublished': TODAY,
                         'mainEntityOfPage': f'{SITE}/journal/{slug}/',
                         'author': {'@type': 'Organization', 'name': 'Dealux'},
                         'publisher': {'@type': 'Organization', 'name': 'Dealux', 'url': SITE}},
                        ensure_ascii=False).replace('</', '<\\/')
        seo = (f'\n<meta property="og:type" content="article">\n<meta property="og:site_name" content="Dealux">'
               f'\n<meta property="og:title" content="{t}">\n<meta property="og:description" content="{desc}">'
               f'\n<meta property="og:url" content="{SITE}/journal/{slug}/">\n<meta property="og:image" content="{esc(img)}">'
               f'\n<meta name="twitter:card" content="summary_large_image">'
               f'\n<meta name="twitter:title" content="{t}">\n<meta name="twitter:description" content="{desc}">'
               f'\n<script type="application/ld+json">{ld}</script>')
        h = template
        h = re.sub(r'<title>.*?</title>', lambda _: f'<title>{t} — Dealux Journal</title>', h, count=1)
        h = re.sub(r'<meta name="description" content="[^"]*">', lambda _: f'<meta name="description" content="{desc}">', h, count=1)
        h = re.sub(r'<link rel="canonical" href="[^"]*">', lambda _: f'<link rel="canonical" href="{SITE}/journal/{slug}/">', h, count=1)
        h = h.replace('\n<link rel="icon"', seo + '\n<link rel="icon"', 1)
        h = re.sub(r'<span class="eyebrow">[^<]*· \d+ min read</span>',
                   lambda _: f'<span class="eyebrow">{topic.replace("-", " ").title()} · {max(1, round(words / 230))} min read</span>', h, count=1)
        h = re.sub(r'(<article class="post">.*?)<h1>.*?</h1>', lambda m: f'{m.group(1)}<h1>{t}</h1>', h, count=1, flags=re.S)
        h = re.sub(r'<div class="post-body"><div class="post-content">.*?</div></div>\n  \n</article>',
                   lambda _: f'<div class="post-body"><div class="post-content">\n{body}\n</div></div>\n  \n</article>', h, count=1, flags=re.S)
        if h.count('<aside class="post-sidebar') != 2 or body not in h:
            sys.exit(f'Could not build {slug} with both sidebars from {ib.TEMPLATE}')
        os.makedirs(f'journal/{slug}', exist_ok=True)
        open(f'journal/{slug}/index.html', 'w', encoding='utf-8').write(h)
        new.append([slug, title, topic, TODAY, img])

    if not new:
        print('No new ad-based Journal articles.')
        return
    journal = new + journal
    for path in ('journal.json', 'data/journal.json'):
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(journal, f, ensure_ascii=False, separators=(',', ':'))
    idx = open('journal/index.html', encoding='utf-8').read()
    cards = ''.join(f'<a class="card post-card" href="/journal/{p[0]}/">\n  <img loading="lazy" src="{esc(p[4])}" alt="" onerror="this.remove()">'
                    f'\n  <span class="eyebrow">{p[2].replace("-", " ").title()}</span>\n  <h3>{html.escape(p[1])}</h3>\n</a>' for p in new)
    idx = idx.replace('<div class="grid" data-results>', '<div class="grid" data-results>' + cards, 1)
    idx = re.sub(r'\b\d[\d,]* articles\b', f'{len(journal):,} articles', idx)
    open('journal/index.html', 'w', encoding='utf-8').write(idx)
    sm = open('sitemap-journal.xml', encoding='utf-8').read()
    add = ''.join(f'  <url>\n    <loc>{SITE}/journal/{p[0]}/</loc>\n    <lastmod>{p[3]}</lastmod>\n    <changefreq>weekly</changefreq>\n    <priority>0.7</priority>\n  </url>\n'
                  for p in new)
    sm = sm.replace('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + add, 1)
    open('sitemap-journal.xml', 'w', encoding='utf-8').write(sm)
    si = open('sitemap-index.xml', encoding='utf-8').read()
    si = re.sub(r'(<loc>[^<]*/sitemap-journal\.xml</loc><lastmod>)[^<]*', lambda m: m.group(1) + TODAY, si)
    open('sitemap-index.xml', 'w', encoding='utf-8').write(si)
    print(f'{len(new)} new ad-based Journal articles')


if __name__ == '__main__':
    main(sys.argv[1:])
