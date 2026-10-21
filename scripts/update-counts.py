#!/usr/bin/env python3
"""Refresh the site-wide product, brand and article counts after an import.

Usage: python3 scripts/update-counts.py

Rebuilds the brand directory from every brand list (so each brand page is
linked), refreshes the homepage "Shop by brand" and "Latest from the Journal"
grids, the Journal counts and the "Search Nk+ products" box on every page.
"""
import datetime, glob, html, json, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)


def brand_name(slug, known):
    if slug in known:
        return known[slug]
    page = f'shop/brand/{slug}/index.html'
    if os.path.exists(page):
        m = re.search(r'<h1>Shop (.*?)</h1>', open(page, encoding='utf-8').read())
        if m:
            return m.group(1)
    return slug.replace('-', ' ').title()


def main():
    products = len({l.strip() for l in open('data/products.txt', encoding='utf-8') if l.strip()})
    journal = json.load(open('journal.json', encoding='utf-8'))
    articles = len(journal)

    # ---- brand directory: every brand with products ----
    p = 'brands/index.html'
    h = open(p, encoding='utf-8').read()
    m = re.search(r'<ul class="brand-list">(.*?)</ul>', h, re.S)
    known = {s: n for s, n in re.findall(r'<a href="/shop/brand/([^/]+)/">(.*?)</a>', m.group(1))}
    brands = []
    for f in glob.glob('data/list/brand-*.json'):
        slug = f[len('data/list/brand-'):-len('.json')]
        n = len(json.load(open(f, encoding='utf-8')))
        if n and os.path.exists(f'shop/brand/{slug}/index.html'):
            name = brand_name(slug, known)
            brands.append((slug, name, n))
    brands.sort(key=lambda b: (-b[2], html.unescape(b[1]).lower()))
    lis = ''.join(f'<li data-name="{html.escape(html.unescape(n).lower(), quote=True)}"><a href="/shop/brand/{s}/">{n}</a>'
                  f'<span class="muted">{c:,} product{"s" if c != 1 else ""}</span></li>' for s, n, c in brands)
    nb = len(brands)
    h = h[:m.start(1)] + lis + h[m.end(1):]
    h = re.sub(r'placeholder="Search [\d,]+ brands…"', f'placeholder="Search {nb:,} brands…"', h)
    h = re.sub(r'data-result-count>[\d,]+ brands<', f'data-result-count>{nb:,} brands<', h)
    h = re.sub(r'<meta name="description" content="[^"]*">',
               f'<meta name="description" content="Browse all {nb:,} brands in the Dealux shop and {products:,} products.">', h, count=1)
    open(p, 'w', encoding='utf-8').write(h)

    # ---- homepage ----
    p = 'index.html'
    h = open(p, encoding='utf-8').read()
    h = re.sub(r'<meta name="description" content="Shop [^"]*">',
               f'<meta name="description" content="Shop {products:,}+ products from {nb:,} brands and read our {articles:,} buying guides.">', h, count=1)
    h = re.sub(r'<p class="muted">[\d,]+\+ products, [\d,]+ brands and [\d,]+ buying guides\.</p>',
               f'<p class="muted">{products:,}+ products, {nb:,} brands and {articles:,} buying guides.</p>', h, count=1)
    cards = ''.join(f'<a class="card dept-card" href="/shop/brand/{s}/">{n}<span class="muted">{c:,} products</span></a>' for s, n, c in brands[:24])
    h = re.sub(r'(<h2>Shop by brand.*?<div class="grid dept-grid">).*?(</div>)', lambda mm: mm.group(1) + cards + mm.group(2), h, count=1, flags=re.S)
    img = lambda u: f'<img loading="lazy" src="{html.escape(u, quote=True)}" alt="">' if u else ''
    posts = ''.join(f'<a class="card post-card" href="/journal/{q[0]}/">\n  {img(q[4])}\n'
                    f'  <span class="eyebrow">{q[2].replace("-", " ").title()} · {datetime.date.fromisoformat(q[3]).strftime("%b %-d, %Y")}</span>\n'
                    f'  <h3>{html.escape(q[1])}</h3>\n</a>' for q in journal[:9])
    h = re.sub(r'(<h2>Latest from the Journal.*?<div class="grid">).*?(</div>)', lambda mm: mm.group(1) + posts + mm.group(2), h, count=1, flags=re.S)
    open(p, 'w', encoding='utf-8').write(h)

    # ---- journal index ----
    p = 'journal/index.html'
    h = open(p, encoding='utf-8').read()
    h = re.sub(r'<meta name="description" content="[\d,]+ buying guides and articles\.">',
               f'<meta name="description" content="{articles:,} buying guides and articles.">', h, count=1)
    h = re.sub(r'placeholder="Search [\d,]+ articles…"', f'placeholder="Search {articles:,} articles…"', h)
    h = re.sub(r'data-result-count>[\d,]+ articles<', f'data-result-count>{articles:,} articles<', h)
    open(p, 'w', encoding='utf-8').write(h)

    # ---- header search box on every page ----
    label = f'Search {products // 1000}k+ products'
    changed = 0
    for f in glob.glob('**/*.html', recursive=True):
        if f.startswith(('.netlify/', 'node_modules/', 'exclusive-files/')):
            continue
        s = open(f, encoding='utf-8').read()
        t = re.sub(r'Search \d+k\+ products', label, s)
        if t != s:
            open(f, 'w', encoding='utf-8').write(t)
            changed += 1
    print(f'{products:,} products, {nb:,} brands, {articles:,} articles; search label updated on {changed:,} pages')


if __name__ == '__main__':
    main()
