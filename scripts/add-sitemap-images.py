#!/usr/bin/env python3
"""Rewrite every sitemap-shop-products-*.xml with image:image entries.

Usage: python3 scripts/add-sitemap-images.py

Each product URL gets its product photo (from data/img shards) attached, so the
images show up in Google Images and Bing Images and link back to the product
page. Existing <lastmod> dates are kept; safe to re-run.
"""
import glob, html, importlib.util, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location('cj', os.path.join(HERE, 'import-cj-links.py'))
cj = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cj)


def main():
    records = cj.load_records()
    total = 0
    for f in sorted(glob.glob('sitemap-shop-products-*.xml')):
        xml = open(f, encoding='utf-8').read()
        urls = re.findall(r'<loc>[^<]*/shop/([^<]+)</loc>\s*(?:<lastmod>([^<]*)</lastmod>)?', xml)
        body = ''.join(cj.product_url_entry(html.unescape(s), records.get(html.unescape(s)), d or cj.TODAY.isoformat()) for s, d in urls)
        assert len(urls) == xml.count('<url>'), f
        open(f, 'w', encoding='utf-8').write(cj.SITEMAP_HEAD + body + '</urlset>\n')
        total += body.count('<image:image>')
    print(f'{total:,} product images listed across the product sitemaps')


if __name__ == '__main__':
    main()
