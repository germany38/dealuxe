#!/usr/bin/env python3
"""Build the Dealux video pages from an Impact "Ads" export (video ads only).

Usage: python3 scripts/build-videos.py path/to/impact-video-ads.csv

For every active video ad this fetches Impact's ad code to find the hosted MP4
and poster, skips videos that no longer play, and writes:
  /videos/<slug>/        watch page: player, description, deal, tracked CTA,
                         Impact impression pixel and VideoObject JSON-LD
  /videos/               index of every video
  /data/videos.json      data for the homepage "Show more" button
  /sitemap-videos.xml    Google video sitemap (added to sitemap-index.xml)
and refreshes the "Featured videos" block on the homepage, which sits above
"Shop by department". Upload dates are kept from data/videos.json so re-runs
don't change them.
"""
import csv, datetime, html, json, os, re, sys, unicodedata, urllib.request
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
SITE = 'https://dealuxapp.com'
PUBLISHER = '5661882'
TODAY = datetime.date.today().isoformat()
HOME_COUNT = 12
GENERIC_HOSTS = {'google', 'apple', 'apps', 'bit', 'linktr', 'imp', 'go', 'click', 'track', 'www', 'shop', 'buy', 'get', 'try', 'offers', 'join'}


def slugify(s):
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+', '-', s).strip('-')


def esc(s):
    return html.escape(s or '', quote=True)


def brand_of(r):
    """Best-effort advertiser name from the landing page, else the tracking domain."""
    for url in (r['LandingPage'], r['TrackingLink']):
        host = re.sub(r'^https?://', '', url or '').split('/')[0].lower()
        parts = [p for p in host.split('.') if p]
        if len(parts) < 2:
            continue
        label = parts[-3] if len(parts) >= 3 and parts[-2] in ('co', 'com') and len(parts[-1]) == 2 else parts[-2]
        if label not in GENERIC_HOSTS and not re.match(r'^i?\d+$|^[a-z]\d{4,}$', label):
            return label.replace('-', ' ').title()
    return 'Partner'


def fetch(url, rng=False):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Dealux video builder)', **({'Range': 'bytes=0-1'} if rng else {})})
    try:
        with urllib.request.urlopen(req, timeout=25) as res:
            return res.status, res.read(4096 if rng else 200000).decode('utf-8', 'ignore')
    except (OSError, ValueError) as e:
        return getattr(e, 'code', 0), ''


def resolve(r):
    """Return (video src, poster) from Impact's ad code, or None if the video doesn't play."""
    _, code = fetch(f"https://a.impactradius-go.com/gen-ad-code/{PUBLISHER}/{r['AdId']}/{r['ProgramId']}/")
    m = re.search(r'<source src="([^"]+)"', code) or re.search(r'<iframe src="([^"]+\.mp4)"', code)
    if not m:
        return None
    src = 'https:' + m.group(1) if m.group(1).startswith('//') else m.group(1)
    if not src.startswith('http'):
        return None
    status, _ = fetch(src, rng=True)
    if status not in (200, 206):
        return None
    p = re.search(r'poster="([^"]+)"', code)
    poster = ('https:' + p.group(1) if p.group(1).startswith('//') else p.group(1)) if p else ''
    if not poster.startswith('http'):
        poster = ''
    if poster and fetch(poster, rng=True)[0] not in (200, 206):
        poster = ''
    return src, poster


def describe(r, brand):
    d = re.sub(r'\s+', ' ', r['Description']).strip()
    if not d:
        d = f"Watch “{r['Name'].strip()}”, a video from {brand}, and tap through for {brand}’s latest offer."
    return d


def deal_of(r):
    if not r['DealName'].strip():
        return ''
    code = r['DealDefaultDiscountCode'].strip()
    return r['DealName'].strip() + (f' — code {code}' if code else '')


def page_shell(title, desc, canonical, head_extra, main):
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{canonical}">
<link rel="icon" href="/favicon.ico">
<link rel="stylesheet" href="/assets/dealux.css">
<link rel="stylesheet" href="/assets/site.css?v=20261012b">
<script src="/assets/app.js?v=20261012c" defer></script>
{head_extra}
</head>
<body data-page="videos">
<header class="site-header">
  <div class="wrap header-row">
    <a class="logo" href="/">DEALUX</a>
    <nav class="main-nav">
      <a href="/shop/">Shop</a><a href="/exclusive/">Exclusives</a><a href="/deals/">Deals</a><a href="/brands/">Brands</a><a href="/journal/">Journal</a><a href="/jobs/">Jobs</a><a href="/tickets/">Tickets</a>
    </nav>
    <form class="header-search" action="/shop/" method="get" role="search">
      <input type="search" name="q" placeholder="Search 206k+ products" aria-label="Search products">
    </form>
  </div>
</header>
<main class="wrap">
{main}
</main>
<footer class="site-footer">
  <div class="wrap">
    <p>© 2026 Dealux. Some links are affiliate links; we may earn a commission at no cost to you.</p>
  </div>
</footer>
</body>
</html>
'''


def video_ld(v):
    d = {'@context': 'https://schema.org', '@type': 'VideoObject', 'name': v['name'], 'description': v['desc'],
         'thumbnailUrl': [v['poster'] or f'{SITE}/placeholder.png'], 'uploadDate': v['date'] + 'T00:00:00+00:00',
         'contentUrl': v['src'], 'url': f"{SITE}/videos/{v['slug']}/", 'inLanguage': v['lang'],
         'publisher': {'@type': 'Organization', 'name': 'Dealux', 'url': SITE}}
    if v['w'] and v['h']:
        d['width'], d['height'] = int(v['w']), int(v['h'])
    return d


def ld_script(obj):
    return '<script type="application/ld+json">' + json.dumps(obj, ensure_ascii=False).replace('</', '<\\/') + '</script>'


def player(v, preload='metadata'):
    poster = f' poster="{esc(v["poster"])}"' if v['poster'] else ''
    ratio = f' style="aspect-ratio:{v["w"]}/{v["h"]}"' if v['w'] and v['h'] else ''
    return (f'<video class="video-player" controls playsinline preload="{preload}"{poster}{ratio} title="{esc(v["name"])}">'
            f'<source src="{esc(v["src"])}" type="video/mp4"></video>')


def pixel(v):
    return f'<img class="imp-pixel" height="0" width="0" src="https://imp.pxf.io/i/{PUBLISHER}/{v["adid"]}/{v["pid"]}" alt="" loading="lazy">'


def watch_page(v, related):
    t = esc(v['name'])
    crumbs = {'@context': 'https://schema.org', '@type': 'BreadcrumbList', 'itemListElement': [
        {'@type': 'ListItem', 'position': 1, 'name': 'Home', 'item': SITE + '/'},
        {'@type': 'ListItem', 'position': 2, 'name': 'Videos', 'item': SITE + '/videos/'},
        {'@type': 'ListItem', 'position': 3, 'name': v['name'], 'item': f"{SITE}/videos/{v['slug']}/"}]}
    head = '\n'.join([f'<meta property="og:type" content="video.other">',
                      f'<meta property="og:title" content="{t}">',
                      f'<meta property="og:video" content="{esc(v["src"])}">',
                      f'<meta property="og:image" content="{esc(v["poster"])}">' if v['poster'] else '',
                      ld_script(video_ld(v)), ld_script(crumbs)])
    deal = f'<p class="promo-note"><b>Current deal:</b> {esc(v["deal"])}</p>' if v['deal'] else ''
    more = ''.join(f'<a class="card video-mini" href="/videos/{r["slug"]}/">{esc(r["name"])}<span class="muted">{esc(r["brand"])}</span></a>'
                   for r in related)
    main = f'''<div class="post-layout">
<article class="post video-watch">
  <a class="muted" href="/videos/">← All videos</a>
  <span class="eyebrow">{esc(v["brand"])} · Video</span>
  <h1>{t}</h1>
  {player(v)}
  <p>{esc(v["desc"])}</p>
  {deal}
  <p><a class="btn btn-gold" href="{esc(v["link"])}" target="_blank" rel="sponsored noopener">Get the {esc(v["brand"])} offer →</a></p>
  {pixel(v)}
</article>
<aside class="post-sidebar">
  <div class="card promo-card">
    <span class="eyebrow">More videos</span>
    <div class="video-mini-list">{more}</div>
  </div>
</aside>
</div>'''
    desc = esc(v['desc'][:160])
    return page_shell(f'{t} — {esc(v["brand"])} video | Dealux', desc, f"{SITE}/videos/{v['slug']}/", head, main)


def card(v):
    """Homepage / index card: lazy poster that swaps to the player on click (see assets/videos.js)."""
    img = (f'<img src="{esc(v["poster"])}" alt="{esc(v["name"])}" loading="lazy">' if v['poster']
           else f'<span class="video-noposter">{esc(v["brand"])}</span>')
    return (f'<div class="card video-card" data-src="{esc(v["src"])}">'
            f'<button class="video-thumb" type="button" aria-label="Play {esc(v["name"])}">{img}<span class="video-play">▶</span></button>'
            f'<span class="eyebrow">{esc(v["brand"])}</span>'
            f'<h3><a href="/videos/{v["slug"]}/">{esc(v["name"])}</a></h3>'
            f'<p class="muted">{esc(v["desc"])}</p>'
            + (f'<p class="promo-note">{esc(v["deal"])}</p>' if v['deal'] else '') +
            f'<div class="product-actions"><a class="btn btn-ghost" href="/videos/{v["slug"]}/">Details</a>'
            f'<a class="btn btn-gold" href="{esc(v["link"])}" target="_blank" rel="sponsored noopener">Get offer →</a></div>'
            f'</div>')


def featured(videos):
    """One video per advertiser, round-robin, so the homepage block isn't one brand."""
    by, order = {}, []
    for v in videos:
        if v['pid'] not in by:
            order.append(v['pid'])
        by.setdefault(v['pid'], []).append(v)
    out, i = [], 0
    while len(out) < min(HOME_COUNT, len(videos)):
        for pid in order:
            if i < len(by[pid]) and len(out) < HOME_COUNT:
                out.append(by[pid][i])
        i += 1
    return out


def main(csv_path):
    rows = [r for r in csv.DictReader(open(csv_path, encoding='utf-8-sig'))
            if r['AdType'] == 'VIDEO' and r['State'] == 'ACTIVE'
            and not (r['LimitedTimeEndDate'].strip() and r['LimitedTimeEndDate'][:10] < TODAY)]
    old = {v['adid']: v for v in json.load(open('data/videos.json', encoding='utf-8'))} if os.path.exists('data/videos.json') else {}
    with ThreadPoolExecutor(24) as pool:
        resolved = list(pool.map(resolve, rows))

    videos, slugs = [], set()
    for r, res in zip(rows, resolved):
        if not res:
            continue
        brand = brand_of(r)
        name = re.sub(r'\s+', ' ', r['Name']).strip() or f'{brand} video'
        slug = f"{slugify(name)[:70].strip('-')}-{r['AdId']}"
        if slug in slugs:
            continue
        slugs.add(slug)
        videos.append(dict(slug=slug, adid=r['AdId'], pid=r['ProgramId'], name=name, brand=brand,
                           desc=describe(r, brand), deal=deal_of(r), src=res[0], poster=res[1],
                           link=r['TrackingLink'].strip() or r['LandingPage'].strip(),
                           w=r['ThirdPartyServableAdCreativeWidth'], h=r['ThirdPartyServableAdCreativeHeight'],
                           lang={'ENGLISH': 'en', 'SPANISH': 'es', 'FRENCH': 'fr', 'GERMAN': 'de'}.get(r['Language'], 'en'),
                           date=old.get(r['AdId'], {}).get('date', TODAY)))
    print(f'{len(videos)} playable videos from {len(rows)} active ads')

    by_pid = {}
    for v in videos:
        by_pid.setdefault(v['pid'], []).append(v)
    for v in videos:
        same = [x for x in by_pid[v['pid']] if x is not v][:6]
        others = [x for x in videos if x['pid'] != v['pid']]
        k = int(v['adid']) % max(1, len(others))
        related = same + (others[k:k + 8 - len(same)] if len(same) < 8 else [])
        os.makedirs(f"videos/{v['slug']}", exist_ok=True)
        open(f"videos/{v['slug']}/index.html", 'w', encoding='utf-8').write(watch_page(v, related))

    keep = {v['slug'] for v in videos}
    for d in os.listdir('videos'):
        if os.path.isdir(f'videos/{d}') and d not in keep:
            os.remove(f'videos/{d}/index.html')
            os.rmdir(f'videos/{d}')

    lst = {'@context': 'https://schema.org', '@type': 'ItemList', 'itemListElement': [
        {'@type': 'ListItem', 'position': i + 1, 'url': f"{SITE}/videos/{v['slug']}/"} for i, v in enumerate(videos)]}
    main_html = (f'<section class="hero"><h1>Deal <span class="gold">videos</span></h1>'
                 f'<p class="muted">{len(videos):,} short videos from {len(by_pid):,} brands, each with the latest offer.</p></section>\n'
                 f'<div class="grid video-grid">' + ''.join(card(v) for v in videos) + '</div>\n'
                 '<script src="/assets/videos.js" defer></script>')
    open('videos/index.html', 'w', encoding='utf-8').write(page_shell(
        'Deal videos — product demos and offers | Dealux',
        f'Watch {len(videos):,} short product and deal videos from {len(by_pid):,} brands, each with a direct link to the current offer.',
        f'{SITE}/videos/', ld_script(lst), main_html))

    keys = ('slug', 'adid', 'pid', 'name', 'brand', 'desc', 'deal', 'src', 'poster', 'link', 'w', 'h', 'lang', 'date')
    with open('data/videos.json', 'w', encoding='utf-8') as f:
        json.dump([{k: v[k] for k in keys} for v in videos], f, ensure_ascii=False, separators=(',', ':'))

    # Homepage block above "Shop by department".
    feat = featured(videos)
    feat_ld = {'@context': 'https://schema.org', '@type': 'ItemList', 'name': 'Featured deal videos', 'itemListElement': [
        {'@type': 'ListItem', 'position': i + 1, 'item': video_ld(v)} for i, v in enumerate(feat)]}
    block = (f'<!-- videos:start -->\n<section class="video-block" aria-label="Featured videos">\n'
             f'<h2>Featured videos <a class="see-all" href="/videos/">All {len(videos):,} videos →</a></h2>\n'
             f'<div class="grid video-grid" data-video-grid>' + ''.join(card(v) for v in feat) + '</div>\n'
             f'<p style="text-align:center"><button class="btn btn-ghost" type="button" data-video-more data-skip="{",".join(v["slug"] for v in feat)}">Show more videos</button></p>\n'
             f'{ld_script(feat_ld)}\n<script src="/assets/videos.js" defer></script>\n</section>\n<!-- videos:end -->\n')
    home = open('index.html', encoding='utf-8').read()
    if '<!-- videos:start -->' in home:
        home = re.sub(r'<!-- videos:start -->.*?<!-- videos:end -->\n', lambda _: block, home, count=1, flags=re.S)
    else:
        home = home.replace('<h2>Shop by department</h2>', block + '<h2>Shop by department</h2>', 1)
    open('index.html', 'w', encoding='utf-8').write(home)

    # Google video sitemap.
    sm = ['<?xml version="1.0" encoding="UTF-8"?>',
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:video="http://www.google.com/schemas/sitemap-video/1.1">',
          f'  <url><loc>{SITE}/videos/</loc><lastmod>{TODAY}</lastmod><changefreq>weekly</changefreq><priority>0.8</priority></url>']
    for v in videos:
        x = lambda s: html.escape(s, quote=False)
        sm.append(f'  <url><loc>{SITE}/videos/{v["slug"]}/</loc><lastmod>{v["date"]}</lastmod>'
                  f'<video:video><video:thumbnail_loc>{x(v["poster"] or SITE + "/placeholder.png")}</video:thumbnail_loc>'
                  f'<video:title>{x(v["name"][:100])}</video:title><video:description>{x(v["desc"][:2048])}</video:description>'
                  f'<video:content_loc>{x(v["src"])}</video:content_loc><video:publication_date>{v["date"]}T00:00:00+00:00</video:publication_date>'
                  f'<video:family_friendly>yes</video:family_friendly></video:video></url>')
    sm.append('</urlset>\n')
    open('sitemap-videos.xml', 'w', encoding='utf-8').write('\n'.join(sm))
    si = open('sitemap-index.xml', encoding='utf-8').read()
    entry = f'  <sitemap><loc>{SITE}/sitemap-videos.xml</loc><lastmod>{TODAY}</lastmod></sitemap>\n'
    if 'sitemap-videos.xml' in si:
        si = re.sub(r'  <sitemap><loc>[^<]*/sitemap-videos\.xml</loc>.*?\n', lambda _: entry, si, count=1)
    else:
        si = si.replace('</sitemapindex>', entry + '</sitemapindex>', 1)
    open('sitemap-index.xml', 'w', encoding='utf-8').write(si)
    print(f'Homepage features {len(feat)} videos; sitemap-videos.xml lists {len(videos)}')


if __name__ == '__main__':
    main(sys.argv[1])
