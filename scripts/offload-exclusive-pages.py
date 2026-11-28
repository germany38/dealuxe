#!/usr/bin/env python3
"""Move /exclusive/<slug>/ item pages out of the static site into data shards.

Usage: python3 scripts/offload-exclusive-pages.py            # dry-run: verify only
       python3 scripts/offload-exclusive-pages.py --apply    # write shards, delete static pages

Every item page shares one head and one tail template; only the title, meta description,
canonical, JSON-LD and main body differ. This stores those per-page parts in
data/exclusive/<hash % 64>.json, keeps one shared shell in data/exclusive/shell.html, and
checks that shell + record rebuilds every page byte-for-byte before anything is deleted.
functions/exclusive/[slug].js (Cloudflare) and netlify/edge-functions/exclusive-page.ts
(Netlify) then serve the same URLs from the shards, so /exclusive/ keeps working even when
the Netlify origin is unavailable.
"""
import glob, hashlib, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXCLUSIVE = os.path.join(ROOT, 'exclusive')
OUT = os.path.join(ROOT, 'data', 'exclusive')
SHARDS = 64
APPLY = '--apply' in sys.argv

HEAD_RE = [
    ('title', re.compile(r'<title>(.*?)</title>', re.S)),
    ('desc', re.compile(r'<meta name="description" content="([^"]*)">')),
    ('canonical', re.compile(r'<link rel="canonical" href="([^"]*)">')),
    ('ld', re.compile(r'<script type="application/ld\+json">(.*?)</script>', re.S)),
]
MAIN_OPEN = '<main class="wrap">'


def shard_of(slug):
    h = 5381
    for ch in slug:
        h = ((h * 33) ^ ord(ch)) & 0xFFFFFFFF
    return h % SHARDS


def split_page(src):
    head, rest = src.split(MAIN_OPEN, 1)
    body, tail = rest.split('</main>', 1)
    vals = {}
    shell = head
    for key, rx in HEAD_RE:
        m = rx.search(shell)
        if not m:
            raise ValueError(f'missing {key}')
        vals[key] = m.group(1)
        shell = shell[:m.start(1)] + '{{' + key + '}}' + shell[m.end(1):]
    return shell + MAIN_OPEN + '{{body}}' + '</main>' + tail, vals, body


def main():
    pages = {}
    shells = set()
    for path in sorted(glob.glob(os.path.join(EXCLUSIVE, '*', 'index.html'))):
        slug = os.path.basename(os.path.dirname(path))
        if slug == 'success':
            continue
        src = open(path, encoding='utf-8').read()
        shell, vals, body = split_page(src)
        shells.add(shell)
        pages[slug] = (vals, body, src)

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
        records[slug] = [vals['title'], vals['desc'], vals['canonical'], vals['ld'], body]

    print(f'verified {len(records)} exclusive item pages rebuild exactly')
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
    for slug in records:
        os.remove(os.path.join(EXCLUSIVE, slug, 'index.html'))
        try:
            os.rmdir(os.path.join(EXCLUSIVE, slug))
        except OSError:
            pass
    print(f'wrote {len(shards)} shards, removed {len(records)} static pages')


if __name__ == '__main__':
    main()
