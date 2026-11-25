#!/usr/bin/env python3
"""Refresh the site-wide product, brand and article counts after an import.

Usage: python3 scripts/update-counts.py

Rebuilds the brand directory, shop totals, landing pages and journal index.
Does not rewrite every article and brand page to update a shared search label.
"""
import datetime, glob, html, json, os, re
from pathlib import Path
from journal_index import refresh as refresh_journal

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
    listings = [Path('data/products.txt'), Path('data/awin/products.txt')]
    products = len({slug for path in listings if path.exists() for slug in path.read_text().splitlines() if slug})
    journal = refresh_journal()
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
    h = re.sub(r'<p class="muted" data-catalog-summary>.*?</p>',
               f'<p class="muted" data-catalog-summary>{products:,} products, {nb:,} brands and {articles:,} articles — '
               f'every product page and article is indexable on Google and Bing.</p>', h, count=1)
    cards = ''.join(f'<a class="card dept-card" href="/shop/brand/{s}/">{n}<span class="muted">{c:,} products</span></a>' for s, n, c in brands[:24])
    h = re.sub(r'(<h2>Shop by brand.*?<div class="grid dept-grid">).*?(</div>)', lambda mm: mm.group(1) + cards + mm.group(2), h, count=1, flags=re.S)
    img = lambda u: f'<img loading="lazy" src="{html.escape(u, quote=True)}" alt="">' if u else ''
    posts = ''.join(f'<a class="card post-card" href="/journal/{q[0]}/">\n  {img(q[4])}\n'
                    f'  <span class="eyebrow">{q[2].replace("-", " ").title()} · {datetime.date.fromisoformat(q[3]).strftime("%b %-d, %Y")}</span>\n'
                    f'  <h3>{html.escape(q[1])}</h3>\n</a>' for q in journal[:9])
    h = re.sub(r'(<h2>Latest from the Journal.*?<div class="grid">).*?(</div>)', lambda mm: mm.group(1) + posts + mm.group(2), h, count=1, flags=re.S)
    open(p, 'w', encoding='utf-8').write(h)

    p = 'shop/index.html'
    h = open(p, encoding='utf-8').read()
    h = re.sub(r'<meta name="description" content="Search and filter [^"]*">', f'<meta name="description" content="Search and filter {products:,} products.">', h, count=1)
    h = re.sub(r'data-result-count(?: data-catalog-total="[^"]*")?>[^<]*<',
               f'data-result-count data-catalog-total="{products:,}">{products:,} products · New arrivals first<', h, count=1)
    summary = (f'<p class="muted" data-index-summary>{products:,} products and {articles:,} articles in total · '
               f'all indexable on Google and Bing via our sitemaps.</p>')
    if 'data-index-summary' in h:
        h = re.sub(r'<p class="muted" data-index-summary>.*?</p>', summary, h, count=1)
    else:
        h = re.sub(r'(<p class="muted" data-result-count[^>]*>[^<]*</p>)', lambda mm: mm.group(1) + '\n    ' + summary, h, count=1)
    open(p, 'w', encoding='utf-8').write(h)
    p = 'assets/app.js'
    h = open(p, encoding='utf-8').read()
    h = re.sub(r"var CATALOG_TOTAL = '[\d,]+';", f"var CATALOG_TOTAL = '{products:,}';", h, count=1)
    open(p, 'w', encoding='utf-8').write(h)
    for p in ('shop/index.html', 'shop/product/index.html', 'index.html'):
        h = open(p, encoding='utf-8').read()
        h = re.sub(r'placeholder="Search [\d,k+]+ products"', f'placeholder="Search {products:,} products"', h)
        h = re.sub(r'placeholder="(?:Filter by name or brand…|Search [\d,]+ products by name or brand…)"',
                   f'placeholder="Search {products:,} products by name or brand…"', h)
        open(p, 'w', encoding='utf-8').write(h)
    print(f'{products:,} products, {nb:,} brands, {articles:,} articles')


if __name__ == '__main__':
    main()
