#!/usr/bin/env python3
"""Add brand call-to-action buttons to every Journal article.

Usage: python3 scripts/enrich-journal-brand-ctas.py

For each /journal/<slug>/ page the article gets a gold "Visit <brand>" affiliate
button and, next to it, a black "Shop for <brand>" button that links to the
brand's shop directory (or to the shop itself when no directory exists). The
pair is inserted at the top of the article and again at the bottom, reusing an
existing call-to-action when the article already has one. Links already inline
in the body text are left untouched. Re-running is a no-op.
"""
import glob
import html
import json
import os
import re
import unicodedata
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

GOLD_RE = re.compile(r'<a class="btn btn-gold"[^>]*href="https?://[^"]*"[^>]*>.*?</a>', re.S)
CTA_VERBS = ('Visit', 'Bekijk', 'Besuch', 'Besuchen', 'Bezoek', 'Bezoeken', 'Visitar', 'Visita', 'Visite',
             'Découvrir', 'Découvrez', 'Ontdek', 'Ontdekken', 'Scopri', 'Scoprire', 'Odwiedź', 'Besök',
             'Besøg', 'Besøk', 'Käy sivustolla:', 'Posjetite', 'Επισκεφθείτε το', 'Vizitați', 'Navštívte',
             'Посетете')
CTA_LABEL_PREFIXES = re.compile(r'^(?:' + '|'.join(re.escape(v) for v in CTA_VERBS) + r')\s+', re.I)
CTA_LABEL_SUFFIXES = re.compile(r'\s+(?:' + '|'.join(re.escape(v) for v in CTA_VERBS) + r')$', re.I)

# Journal topic -> (Exclusive category slug, short label). A third "PDF" button links the
# article's topic to the matching paid printable in /exclusive/. Topics without a good match
# get no button, so we never send readers to an empty category.
EXCLUSIVE_CTA = {
    'Gifts': ('deals-and-smart-shopping', 'Deals'),
    'Travel': ('travel-and-connectivity', 'Travel'),
    'Technology': ('electronics', 'Tech'),
    'Finance': ('deals-and-smart-shopping', 'Deals'),
    'Beauty': ('hair-and-beauty', 'Beauty'),
    'Home': ('home-decor', 'Home'),
    'Education': ('education-and-classroom', 'Education'),
    'Creative': ('social-media', 'Social Media'),
    'Fashion': ('clothing', 'Fashion'),
    'Entertainment': ('tickets-and-experiences', 'Experiences'),
    'Food Drink': ('food-and-snacks', 'Food'),
    'Sports': ('sports-and-outdoors', 'Sports'),
    'Automotive': ('automotive', 'Automotive'),
    'Business Services B2B': ('deals-and-smart-shopping', 'Deals'),
    'Amazon': ('deals-and-smart-shopping', 'Deals'),
    'Pets': ('toys-costumes-and-pets', 'Pets & Toys'),
    'Jewelry': ('jewelry', 'Jewelry'),
    'Education Training': ('education-and-classroom', 'Education'),
    'Health': ('wellness-and-massage', 'Wellness'),
    'Software Downloads': ('gaming-and-software', 'Software'),
    'Books': ('education-and-classroom', 'Education'),
    'Mobile Pay As You Go': ('travel-and-connectivity', 'Travel'),
    'Tourism': ('travel-and-connectivity', 'Travel'),
    'Department Stores': ('deals-and-smart-shopping', 'Deals'),
    'Travel Agencies': ('travel-and-connectivity', 'Travel'),
    'Hotels': ('travel-and-connectivity', 'Travel'),
    'Pc': ('electronics', 'Tech'),
    'Computers': ('electronics', 'Tech'),
    'Insurance': ('deals-and-smart-shopping', 'Deals'),
    'Clothing': ('clothing', 'Fashion'),
    'Internet Service Provider': ('travel-and-connectivity', 'Travel'),
    'Electronic Accessories': ('electronics', 'Tech'),
    'Web Hosting': ('gaming-and-software', 'Software'),
    'Toys': ('toys-costumes-and-pets', 'Pets & Toys'),
    'Mobile Broadband': ('travel-and-connectivity', 'Travel'),
    'Clothing Accessories': ('shoes-bags-and-accessories', 'Accessories'),
    'Airport Parking': ('travel-and-connectivity', 'Travel'),
    'Tickets': ('tickets-and-experiences', 'Experiences'),
    'Entertainment Downloads': ('gaming-and-software', 'Software'),
    'Diy': ('home-decor', 'Home'),
    'Sports Equipment': ('sports-and-outdoors', 'Sports'),
    'Mobile Downloads': ('gaming-and-software', 'Software'),
    'Digital Tv': ('electronics', 'Tech'),
    'White Goods': ('appliances', 'Appliances'),
    'Jewellery': ('jewelry', 'Jewelry'),
    'Fmcg': ('food-and-snacks', 'Food'),
    'Savings': ('deals-and-smart-shopping', 'Deals'),
    'Sportswear': ('clothing', 'Fashion'),
    'Photography': ('cameras-and-photo', 'Photography'),
    'Online Gaming': ('gaming-and-software', 'Software'),
    'Electronic Superstore': ('electronics', 'Tech'),
    'Womenswear': ('clothing', 'Fashion'),
    'Loans': ('deals-and-smart-shopping', 'Deals'),
    'Office Supplies': ('home-office', 'Office'),
    'Entertainment Superstore': ('tickets-and-experiences', 'Experiences'),
    'Group Buying': ('deals-and-smart-shopping', 'Deals'),
    'Gambling': ('gaming-and-software', 'Software'),
    'Audio Visual': ('electronics', 'Tech'),
    'Network Operators': ('travel-and-connectivity', 'Travel'),
    'Music': ('tickets-and-experiences', 'Experiences'),
    'B2B Telecommunications Services': ('deals-and-smart-shopping', 'Deals'),
    'Pharmaceuticals': ('wellness-and-massage', 'Wellness'),
    'Shoes': ('shoes-bags-and-accessories', 'Accessories'),
    'Baby': ('toys-costumes-and-pets', 'Pets & Toys'),
    'Gadgets': ('electronics', 'Tech'),
    'Mortgages': ('deals-and-smart-shopping', 'Deals'),
    'Mobile Contract': ('travel-and-connectivity', 'Travel'),
    'Food & Drink': ('food-and-snacks', 'Food'),
}


def slugify(s):
    s = unicodedata.normalize('NFKD', s or '').encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+', '-', s).strip('-')


def esc(s):
    return html.escape(s or '', quote=True)


def reg(host):
    host = (host or '').lower()
    return host[4:] if host.startswith('www.') else host


def dest_host(link):
    try:
        url = urlparse(link)
    except ValueError:
        return ''
    for key in ('ued', 'u', 'url', 'destination', 'dest', 'redirect'):
        value = parse_qs(url.query).get(key, [''])
        if value and value[0]:
            host = urlparse(unquote(value[0])).netloc
            if host:
                return reg(host)
    return reg(url.netloc)


def awin_merchant(link):
    """The Awin advertiser id from a click link (m= on pclick, awinmid= on cread)."""
    try:
        query = parse_qs(urlparse(link).query)
    except ValueError:
        return ''
    for key in ('m', 'awinmid'):
        if query.get(key) and query[key][0].isdigit():
            return query[key][0]
    return ''


def article_links(article):
    links = []
    for match in re.finditer(r'<a\b[^>]*href="([^"]+)"', article):
        inner = re.search(r'https?://[^\s\)\]]+', html.unescape(match.group(1)))
        if inner:
            links.append(inner.group(0))
    return links


def clean_label(text):
    text = html.unescape(re.sub(r'<[^>]+>', '', text)).strip()
    text = re.sub(r'\s*→\s*$', '', text).strip()
    text = CTA_LABEL_PREFIXES.sub('', text).strip()
    text = CTA_LABEL_SUFFIXES.sub('', text).strip()
    return text


def cta_label(article):
    """The brand shown on the article's own call to action, if it has one."""
    for pattern in (r'article-cta">.*?<a\b[^>]*>(.*?)</a>',
                    r'class="btn btn-gold"[^>]*href="https?://[^"]*"[^>]*>(.*?)</a>'):
        match = re.search(pattern, article, re.S)
        if match:
            text = clean_label(match.group(1))
            if text:
                return text
    return ''


def article_category(article):
    """The topic shown in the article's eyebrow (e.g. 'Creative · 7 min read')."""
    match = re.search(r'<span class="eyebrow">([^<·]+)·', article)
    return html.unescape(match.group(1)).strip() if match else ''


def build_maps():
    shop_slugs = {entry.name for entry in Path('shop/brand').iterdir() if entry.is_dir()}
    names = {}
    for name, _ in json.load(open('brands.json', encoding='utf-8')):
        names.setdefault(slugify(name), name)
    for slug in shop_slugs:
        if slug in names:
            continue
        page = Path(f'shop/brand/{slug}/index.html')
        if page.exists():
            match = re.search(r'<h1>(.*?)</h1>', page.read_text(encoding='utf-8'))
            if match:
                names[slug] = re.sub(r'^Shop\s+', '', html.unescape(match.group(1)))
        names.setdefault(slug, slug.replace('-', ' ').title())
    host_map = {}
    merchant_map = {}
    for path in glob.glob('data/awin/*.json') + glob.glob('data/img/*.json'):
        for slug, record in json.load(open(path, encoding='utf-8')).items():
            if len(record) < 6:
                continue
            link = record[5] or ''
            brand_slug = record[7].get('brand_slug') if len(record) > 7 and isinstance(record[7], dict) else None
            brand_slug = brand_slug or slugify(record[3] or '')
            if not brand_slug:
                continue
            host = dest_host(link)
            if host:
                host_map.setdefault(host, brand_slug)
            merchant = awin_merchant(link)
            if merchant:
                merchant_map.setdefault(merchant, brand_slug)
    for name, link in json.load(open('brands.json', encoding='utf-8')):
        host = dest_host(link)
        if host:
            host_map.setdefault(host, slugify(name))
    return shop_slugs, names, host_map, merchant_map


def resolve(article, art_slug, shop_slugs, names, host_map, merchant_map):
    links = article_links(article)
    match = (re.search(r'article-cta">.*?<a\b[^>]*href="([^"]+)"', article, re.S)
             or re.search(r'<p class="cta">.*?<a\b[^>]*href="([^"]+)"', article, re.S))
    affiliate = html.unescape(match.group(1)) if match else (links[0] if links else '')
    label = cta_label(article)
    brand_slug = slugify(label) if label and slugify(label) in shop_slugs else None
    if not brand_slug and affiliate:
        for candidate in (host_map.get(dest_host(affiliate)), merchant_map.get(awin_merchant(affiliate))):
            if candidate in shop_slugs:
                brand_slug = candidate
                break
    if not brand_slug:
        candidates = [slug for slug in shop_slugs if art_slug == slug or art_slug.startswith(slug + '-')]
        if candidates:
            brand_slug = max(candidates, key=len)
    if label:
        brand_name = label
    else:
        brand_name = names.get(brand_slug) if brand_slug else None
    return affiliate, brand_slug, brand_name


def buttons(affiliate, brand_slug, brand_name, pdf=None):
    gold_label = f'Visit {brand_name}' if brand_name else 'Visit site'
    black_label = f'Shop for {brand_name}' if brand_name else 'Shop similar deals'
    shop_dir = f'/shop/brand/{brand_slug}/' if brand_slug else '/shop/'
    gold = (f'<a class="btn btn-gold" href="{esc(affiliate)}" target="_blank" rel="sponsored nofollow noopener">'
            f'{esc(gold_label)} →</a>')
    black = f'<a class="btn btn-dark" href="{esc(shop_dir)}">{esc(black_label)} →</a>'
    pdf_html = ''
    if pdf:
        slug, label = pdf
        pdf_html = f'<a class="btn btn-gold" href="/exclusive/?category={esc(slug)}">Get the {esc(label)} PDF →</a>'
    return gold, black, pdf_html


def strip_previous(article):
    article = re.sub(r'<!-- dx-cta-top -->.*?<!-- /dx-cta-top -->\n?', '', article, flags=re.S)
    article = re.sub(r'<!-- dx-cta-bottom -->.*?<!-- /dx-cta-bottom -->\n?', '', article, flags=re.S)
    article = re.sub(r'<span class="dx-brand-cta">(.*?)<a class="btn btn-dark".*?</a></span>', r'\1',
                     article, flags=re.S)
    return article


def enrich(html_text, art_slug, shop_slugs, names, host_map, merchant_map):
    start = html_text.find('<article class="post">')
    if start < 0:
        return html_text, False
    end = html_text.find('</article>', start)
    article = strip_previous(html_text[start:end])
    affiliate, brand_slug, brand_name = resolve(article, art_slug, shop_slugs, names, host_map, merchant_map)
    if not affiliate and not brand_name:
        return html_text, False
    pdf = EXCLUSIVE_CTA.get(article_category(article))
    gold, black, pdf_html = buttons(affiliate, brand_slug, brand_name, pdf)

    # Bottom: reuse an existing call-to-action when the article has one, adding
    # the shop button beside it; otherwise add a fresh bottom block.
    existing = GOLD_RE.search(article)
    if existing:
        pair = f'<span class="dx-brand-cta">{existing.group(0)}{black}{pdf_html}</span>'
        article = article[:existing.start()] + pair + article[existing.end():]
    else:
        bottom = (f'<!-- dx-cta-bottom -->\n<div class="dx-brand-cta dx-cta-bottom">'
                  f'{gold if affiliate else ""}{black}{pdf_html}</div>\n<!-- /dx-cta-bottom -->')
        article = article + bottom + '\n'

    top_buttons = (gold if affiliate else '') + black + pdf_html
    top = f'<!-- dx-cta-top -->\n<div class="dx-brand-cta dx-cta-top">{top_buttons}</div>\n<!-- /dx-cta-top -->'
    article = article.replace('</h1>', '</h1>\n' + top, 1)

    return html_text[:start] + article + html_text[end:], True


def main():
    shop_slugs, names, host_map, merchant_map = build_maps()
    changed = 0
    for path in sorted(glob.glob('journal/*/index.html')):
        art_slug = path.split('/')[1]
        source = Path(path).read_text(encoding='utf-8')
        updated, did = enrich(source, art_slug, shop_slugs, names, host_map, merchant_map)
        if did:
            Path(path).write_text(updated, encoding='utf-8')
            changed += 1
    print(f'{changed} journal articles enriched')


if __name__ == '__main__':
    main()
