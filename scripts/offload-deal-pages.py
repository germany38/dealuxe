#!/usr/bin/env python3
"""Move /deals/<slug>/ detail pages and /deals/promotions/<store>/ hubs into data shards.

Usage: python3 scripts/offload-deal-pages.py            # dry-run: verify only
       python3 scripts/offload-deal-pages.py --apply    # write shards, delete static pages

The static deal pages (written by build-deals.py) and the store hubs (written by
import-awin-promotions.py) share one head and one tail template; only the title, meta
description, canonical, robots and article body differ. This stores those per-page parts in
data/deals/<hash % 64>.json, keeps one shared shell in data/deals/shell.html, and checks that
shell + record rebuilds every page byte-for-byte before anything is deleted.
functions/deals/[slug].js and functions/deals/promotions/[store].js (Cloudflare) plus
netlify/edge-functions/deal-page.ts (Netlify) serve the same URLs from the shards.

Store hubs are also tidied: links to deals that no longer exist (pruned as expired) are
removed and the offer count in the hub copy is corrected.
"""
import glob, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEALS = os.path.join(ROOT, 'deals')
OUT = os.path.join(ROOT, 'data', 'deals')
AWIN_SHARDS = os.path.join(ROOT, 'data', 'awin-deals')
SHARDS = 64
APPLY = '--apply' in sys.argv

HEAD_RE = [
    ('title', re.compile(r'<title>(.*?)</title>', re.S)),
    ('meta', re.compile(r'<meta name="description" content="([^"]*)">')),
    ('canonical', re.compile(r'<link rel="canonical" href="([^"]*)">')),
    ('robots', re.compile(r'<meta name="robots" content="([^"]*)">')),
]
ART_OPEN = '<article class="post deal-page">'
SIDEBAR = '<aside class="post-sidebar">'
LI = re.compile(r'<li><a href="/deals/([a-z0-9-]+)/">.*?</a></li>\n?', re.S)


def shard_of(slug):
    h = 5381
    for ch in slug:
        h = ((h * 33) ^ ord(ch)) & 0xFFFFFFFF
    return h % SHARDS


def live_awin_slugs():
    live = set()
    for path in glob.glob(os.path.join(AWIN_SHARDS, '*.json')):
        live.update(json.load(open(path, encoding='utf-8')).keys())
    return live


def split_page(src):
    head, rest = src.split(ART_OPEN, 1)
    body, tail = rest.split(SIDEBAR, 1)
    vals = {}
    shell = head
    for key, rx in HEAD_RE:
        m = rx.search(shell)
        if not m:
            raise ValueError(f'missing {key}')
        vals[key] = m.group(1)
        shell = shell[:m.start(1)] + '{{' + key + '}}' + shell[m.end(1):]
    return shell + ART_OPEN + '{{body}}' + SIDEBAR + tail, vals, body


def tidy_hub(body, live):
    """Drop links to pruned deals and fix the '<n> current <brand> offers' count."""
    kept = 0

    def keep(m):
        nonlocal kept
        if m.group(1) in live:
            kept += 1
            return m.group(0)
        return ''

    body = LI.sub(keep, body)
    body = re.sub(r'\d+ current ([^<]+?) offers?,', lambda m: f'{kept} current {m.group(1)} offer{"s" if kept != 1 else ""},', body, count=1)
    return body


def main():
    live = live_awin_slugs()
    pages = {}
    shells = set()
    for path in sorted(glob.glob(os.path.join(DEALS, '*', 'index.html'))):
        slug = os.path.basename(os.path.dirname(path))
        if slug == 'promotions':
            continue
        src = open(path, encoding='utf-8').read()
        shell, vals, body = split_page(src)
        shells.add(shell)
        pages[slug] = (vals, body, src)

    for path in sorted(glob.glob(os.path.join(DEALS, 'promotions', '*', 'index.html'))):
        slug = os.path.basename(os.path.dirname(path))
        src = open(path, encoding='utf-8').read()
        body = tidy_hub(src.split(ART_OPEN, 1)[1].split(SIDEBAR, 1)[0], live)
        src2 = src.replace(src.split(ART_OPEN, 1)[1].split(SIDEBAR, 1)[0], body, 1)
        shell, vals, body = split_page(src2)
        shells.add(shell)
        pages[slug] = (vals, body, src2)

    if len(shells) != 1:
        sys.exit(f'templates differ: {len(shells)} shell variants; aborting')
    shell = shells.pop()

    records = {}
    for slug, (vals, body, src) in pages.items():
        html_out = shell
        for k, v in vals.items():
            html_out = html_out.replace('{{' + k + '}}', v, 1)
        html_out = html_out.replace('{{body}}', body, 1)
        if html_out != src:
            sys.exit(f'rebuild mismatch for {slug}; aborting')
        records[slug] = [vals['title'], vals['meta'], vals['canonical'], vals['robots'], body]

    print(f'verified {len(records)} deal pages rebuild exactly')
    if not APPLY:
        return

    os.makedirs(OUT, exist_ok=True)
    open(os.path.join(OUT, 'shell.html'), 'w', encoding='utf-8').write(shell)
    shards = {}
    for slug, rec in records.items():
        shards.setdefault(shard_of(slug), {})[slug] = rec
    for n, d in shards.items():
        with open(os.path.join(OUT, f'{n}.json'), 'w', encoding='utf-8') as f:
            json.dump(d, f, ensure_ascii=False, separators=(',', ':'))
    removed = 0
    for path in glob.glob(os.path.join(DEALS, '*', 'index.html')) + glob.glob(os.path.join(DEALS, 'promotions', '*', 'index.html')):
        slug = os.path.basename(os.path.dirname(path))
        if slug in records:
            os.remove(path)
            removed += 1
            try:
                os.rmdir(os.path.dirname(path))
            except OSError:
                pass
    print(f'wrote {len(shards)} shards, removed {removed} static pages')


if __name__ == '__main__':
    main()
