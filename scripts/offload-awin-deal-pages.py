#!/usr/bin/env python3
"""Move Awin promotion deal pages out of the static site into data shards.

Usage: python3 scripts/offload-awin-deal-pages.py            # dry-run: verify only
       python3 scripts/offload-awin-deal-pages.py --apply    # write shards, delete static pages

Each Awin promotion page (written by import-awin-promotions.py) shares one head and one
tail template; only the title, meta description, canonical, robots and article body differ.
This script stores those per-page parts in data/awin-deals/<pid % 128>.json, keeps one
shared shell in data/awin-deals/shell.html, and checks that shell + record rebuilds every
page byte-for-byte before anything is deleted. netlify/edge-functions/awin-deal.ts then
serves the same URLs from the shards.
"""
import glob, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEALS = os.path.join(ROOT, 'deals')
OUT = os.path.join(ROOT, 'data', 'awin-deals')
MARK = 'Dealux may earn a commission from qualifying purchases through this link'
SHARDS = 128
APPLY = '--apply' in sys.argv

HEAD_RE = [
    ('title', re.compile(r'<title>(.*?)</title>', re.S)),
    ('meta', re.compile(r'<meta name="description" content="([^"]*)">')),
    ('canonical', re.compile(r'<link rel="canonical" href="([^"]*)">')),
    ('robots', re.compile(r'<meta name="robots" content="([^"]*)">')),
]
ART_OPEN = '<article class="post deal-page">'


def split_page(src):
    """Return (shell_head_with_placeholders, vals, body, tail) or raise."""
    head, rest = src.split(ART_OPEN, 1)
    # import-awin-promotions.py writes the article without its closing tag, followed by the
    # shared sidebar and footer; split at the sidebar.
    cut = rest.index('<aside class="post-sidebar">')
    body, tail = rest[:cut], rest[cut:]
    vals = {}
    shell = head
    for key, rx in HEAD_RE:
        m = rx.search(shell)
        if not m:
            raise ValueError(f'missing {key}')
        vals[key] = m.group(1)
        shell = shell[:m.start(1)] + '{{' + key + '}}' + shell[m.end(1):]
    return shell, vals, body, tail


def main():
    pages = {}
    shells, tails = set(), set()
    for path in sorted(glob.glob(os.path.join(DEALS, '*', 'index.html'))):
        src = open(path, encoding='utf-8').read()
        if MARK not in src:
            continue
        slug = os.path.basename(os.path.dirname(path))
        shell, vals, body, tail = split_page(src)
        shells.add(shell)
        tails.add(tail)
        pages[slug] = (vals, body, tail, src)

    if len(shells) != 1 or len(tails) != 1:
        sys.exit(f'templates differ: {len(shells)} head variants, {len(tails)} tail variants; aborting')
    shell = shells.pop()
    tail = tails.pop()
    shell_full = shell + ART_OPEN + '{{body}}' + tail

    # Verify every page rebuilds byte-for-byte from shell + record.
    records = {}
    for slug, (vals, body, _tail, src) in pages.items():
        html_out = shell_full
        for k, v in vals.items():
            html_out = html_out.replace('{{' + k + '}}', v, 1)
        html_out = html_out.replace('{{body}}', ART_OPEN + body, 1)
        if html_out != src:
            sys.exit(f'rebuild mismatch for {slug}; aborting')
        records[slug] = [vals['title'], vals['meta'], vals['canonical'], vals['robots'], body]

    print(f'verified {len(records)} Awin deal pages rebuild exactly')
    if not APPLY:
        return

    os.makedirs(OUT, exist_ok=True)
    open(os.path.join(OUT, 'shell.html'), 'w', encoding='utf-8').write(shell_full)
    shards = {}
    for slug, rec in records.items():
        pid = re.search(r'-(\d+)$', slug).group(1)
        shards.setdefault(int(pid) % SHARDS, {})[slug] = rec
    for n, d in shards.items():
        with open(os.path.join(OUT, f'{n}.json'), 'w', encoding='utf-8') as f:
            json.dump(d, f, ensure_ascii=False, separators=(',', ':'))
    for slug in records:
        os.remove(os.path.join(DEALS, slug, 'index.html'))
        try:
            os.rmdir(os.path.join(DEALS, slug))
        except OSError:
            pass
    print(f'wrote {len(shards)} shards, removed {len(records)} static pages')


if __name__ == '__main__':
    main()
