#!/usr/bin/env python3
"""Move /videos/<slug>/ watch pages out of the static site into data shards.

Usage: python3 scripts/offload-videos-pages.py            # dry-run: verify only
       python3 scripts/offload-videos-pages.py --apply    # write shards, delete static pages

Every watch page shares one head template; only the title, meta description, canonical, the
extra <head> block (Open Graph tags and VideoObject/Breadcrumb JSON-LD) and the rest of the
page differ. This stores those per-page parts in data/videos/<hash % 64>.json, keeps one shared
shell in data/videos/shell.html, and checks that shell + record rebuilds every page
byte-for-byte before anything is deleted. functions/videos/[slug].js (Cloudflare) and
netlify/edge-functions/video-page.ts (Netlify) then serve the same URLs from the shards, so
/videos/ keeps working even when the Netlify origin is unavailable. The /videos/ index stays
static.
"""
import glob, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VIDEOS = os.path.join(ROOT, 'videos')
OUT = os.path.join(ROOT, 'data', 'videos')
SHARDS = 64
APPLY = '--apply' in sys.argv

ART_OPEN = '<article class="post video-watch">'
HEAD_RE = [
    ('title', re.compile(r'<title>(.*?)</title>', re.S)),
    ('desc', re.compile(r'<meta name="description" content="([^"]*)">')),
    ('canonical', re.compile(r'<link rel="canonical" href="([^"]*)">')),
]
HE_RE = re.compile(r'(<script src="/assets/app\.js\?v=[^"]*" defer></script>\n)(.*?)(</head>)', re.S)


def shard_of(slug):
    h = 5381
    for ch in slug:
        h = ((h * 33) ^ ord(ch)) & 0xFFFFFFFF
    return h % SHARDS


def split_page(src):
    head, rest = src.split(ART_OPEN, 1)
    vals = {}
    shell = head
    for key, rx in HEAD_RE:
        m = rx.search(shell)
        if not m:
            raise ValueError(f'missing {key}')
        vals[key] = m.group(1)
        shell = shell[:m.start(1)] + '{{' + key + '}}' + shell[m.end(1):]
    m = HE_RE.search(shell)
    if not m:
        raise ValueError('missing head_extra')
    vals['head_extra'] = m.group(2)
    shell = shell[:m.start(2)] + '{{head_extra}}' + shell[m.end(2):]
    return shell, vals, ART_OPEN + rest


def main():
    pages = {}
    shells = set()
    for path in sorted(glob.glob(os.path.join(VIDEOS, '*', 'index.html'))):
        slug = os.path.basename(os.path.dirname(path))
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
        html_out += body
        if html_out != src:
            sys.exit(f'rebuild mismatch for {slug}; aborting')
        records[slug] = [vals['title'], vals['desc'], vals['canonical'], vals['head_extra'], body]

    print(f'verified {len(records)} video pages rebuild exactly')
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
        os.remove(os.path.join(VIDEOS, slug, 'index.html'))
        try:
            os.rmdir(os.path.join(VIDEOS, slug))
        except OSError:
            pass
    print(f'wrote {len(shards)} shards, removed {len(records)} static pages')


if __name__ == '__main__':
    main()
