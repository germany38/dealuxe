#!/usr/bin/env python3
"""Generate the Exclusive PDF directory from data/exclusive-products.csv.

Outputs:
  exclusive/index.html            directory page (search + category filter)
  exclusive/<slug>/index.html     one page per resource with the Stripe buy link
  exclusive/success/index.html    post-checkout download page
  netlify/lib/exclusive-items.mjs item lookup used by the download function
  sitemap-exclusive.xml

Run: python3 scripts/build-exclusive.py
"""
import csv, html, json, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = "https://dealuxapp.com"
CSV = os.path.join(ROOT, "data", "exclusive-products.csv")

e = html.escape


def slugify(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower().replace("&", "and").replace("é", "e")).strip("-")


WIDGETS = """<aside class="ex-widgets">
  <div class="card promo-card temu-storefront">
    <span class="eyebrow">Temu · My storefront</span>
    <h3>✨Discover Amazing Finds at My Storefront 🎁</h3>
    <p class="muted">Don’t miss out on the special coupon bundle waiting for you. 🌟 Packed with top-notch products at unbeatable prices. Click my link now to enjoy, shop, and save big! 🛍️✨</p>
    <a class="btn btn-gold" href="https://temu.to/k/pss0huunk6r" target="_blank" rel="nofollow sponsored noopener">Shop my storefront →</a>
  </div>
  <div class="card promo-card flexjobs-card">
    <span class="eyebrow">FlexJobs · Remote work</span>
    <a rel="sponsored noopener" href="https://flexjobs.sjv.io/c/5661882/1847140/20168" target="_blank" id="1847140"><img src="https://a.impactradius-go.com/display-ad/20168-1847140" border="0" alt="FlexJobs" width="200" height="200" loading="lazy"></a><img height="0" width="0" src="https://imp.pxf.io/i/5661882/1847140/20168" style="position:absolute;visibility:hidden;" border="0" alt="">
    <h3>The #1 Job Site to Find Work From Home Jobs</h3>
    <p class="muted">No Ads, Scams, or Junk. Find legitimate work-from-home jobs with options for flexible hours and hybrid work.</p>
    <a class="btn btn-gold" href="https://flexjobs.sjv.io/c/5661882/1847140/20168" target="_blank" rel="nofollow sponsored noopener">Start your 2 week trial →</a>
  </div>
</aside>"""


def page(title, desc, canonical, body, extra_head=""):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<link rel="canonical" href="{canonical}">
<link rel="icon" href="/favicon.ico">
<link rel="stylesheet" href="/assets/dealux.css">
<link rel="stylesheet" href="/assets/site.css">
<link rel="stylesheet" href="/exclusive/exclusive.css">
{extra_head}</head>
<body data-page="exclusive">
<header class="site-header">
  <div class="wrap header-row">
    <a class="logo" href="/">DEALUX</a>
    <nav class="main-nav">
      <a href="/shop/">Shop</a><a href="/exclusive/">Exclusives</a><a href="/brands/">Brands</a><a href="/journal/">Journal</a><a href="/jobs/">Jobs</a><a href="/tickets/">Tickets</a>
    </nav>
    <form class="header-search" action="/exclusive/" method="get" role="search">
      <input type="search" name="q" placeholder="Search exclusive PDFs" aria-label="Search exclusive PDFs">
    </form>
  </div>
</header>
<main class="wrap">
{body}
</main>
<footer class="site-footer">
  <div class="wrap">
    <p>© 2026 Dealux. Digital downloads are delivered instantly after secure checkout with Stripe.</p>
  </div>
</footer>
</body>
</html>
"""


def write(rel, content):
    path = os.path.join(ROOT, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def card(it):
    return (
        f'<a class="card ex-card" href="/exclusive/{it["slug"]}/" data-cat="{e(it["cat_slug"])}" '
        f'data-search="{e((it["title"] + " " + it["category"] + " " + it["type"]).lower())}">'
        f'<span class="ex-badge">{e(it["type"])}</span>'
        f'<h3>{e(it["title"])}</h3>'
        f'<p class="muted">{e(it["description"])}</p>'
        f'<span class="ex-meta">{e(it["category"])} · {it["pages"]} page{"s" if it["pages"] != "1" else ""} · <strong>${it["price_usd"]}</strong></span>'
        f"</a>"
    )


def main():
    with open(CSV, newline="", encoding="utf-8") as f:
        items = list(csv.DictReader(f))
    for it in items:
        it["cat_slug"] = slugify(it["category"])

    cats = []
    for it in items:
        if it["category"] not in [c[0] for c in cats]:
            cats.append((it["category"], it["cat_slug"]))

    # Directory
    chips = '<button class="ex-chip active" data-filter="">All</button>' + "".join(
        f'<button class="ex-chip" data-filter="{s}">{e(c)}</button>' for c, s in cats
    )
    body = f"""<section class="ex-hero">
  <span class="eyebrow">Dealux Exclusive</span>
  <h1>Dealux Exclusives — Resource Library</h1>
  <p class="muted">{len(items):,} printable checklists, fillable planners and infographics to shop smarter, organize your home and grow online. Instant download after checkout.</p>
  <input class="ex-search" type="search" id="ex-q" placeholder="Search {len(items):,} downloadable resources…" aria-label="Search resources">
  <div class="ex-chips">{chips}</div>
  <p class="muted ex-count" id="ex-count"></p>
</section>
<div class="ex-grid" id="ex-grid">
{chr(10).join(card(it) for it in items)}
</div>
<script src="/exclusive/exclusive.js" defer></script>"""
    write(
        "exclusive/index.html",
        page(
            "Dealux Exclusives — Resource Library | Dealux",
            f"Browse {len(items):,} exclusive printable PDFs: checklists, fillable planners and infographics. Instant download.",
            f"{SITE}/exclusive/",
            body,
        ),
    )

    # Item pages
    for it in items:
        related = [r for r in items if r["category"] == it["category"] and r["slug"] != it["slug"]][:6]
        ld = {
            "@context": "https://schema.org",
            "@type": "Product",
            "name": it["title"],
            "description": it["description"],
            "sku": it["id"],
            "category": it["category"],
            "offers": {
                "@type": "Offer",
                "price": it["price_usd"],
                "priceCurrency": "USD",
                "availability": "https://schema.org/InStock",
                "url": f"{SITE}/exclusive/{it['slug']}/",
            },
        }
        body = f"""<a class="muted" href="/exclusive/">← Back to Dealux Exclusives</a>
<article class="ex-item">
  <div class="ex-cover" aria-hidden="true"><span>PDF</span><strong>{e(it["title"])}</strong><em>{e(it["type"])}</em></div>
  <div class="ex-info">
    <span class="eyebrow">{e(it["category"])}</span>
    <h1>{e(it["title"])}</h1>
    <p class="ex-price">${it["price_usd"]} <span class="muted">USD · one-time</span></p>
    <p>{e(it["description"])}</p>
    <ul class="ex-facts">
      <li><strong>Format:</strong> {e(it["type"])} (PDF)</li>
      <li><strong>Length:</strong> {it["pages"]} page{"s" if it["pages"] != "1" else ""}</li>
      <li><strong>File:</strong> {e(it["file_name"])}</li>
      <li><strong>Item #:</strong> {e(it["id"])}</li>
    </ul>
    <a class="btn btn-gold ex-buy" href="{e(it["purchase_url"])}" rel="nofollow noopener">Buy &amp; download — ${it["price_usd"]} →</a>
    <p class="muted ex-note">Secure checkout by Stripe. After payment you're returned to Dealux and your PDF download starts right away.</p>
  </div>
</article>
{WIDGETS}
<section class="ex-related">
  <h2>More in {e(it["category"])}</h2>
  <div class="ex-grid">{"".join(card(r) for r in related)}</div>
</section>"""
        write(
            f"exclusive/{it['slug']}/index.html",
            page(
                f"{it['title']} (PDF) — Dealux Exclusive",
                it["description"],
                f"{SITE}/exclusive/{it['slug']}/",
                body,
                f'<script type="application/ld+json">{json.dumps(ld)}</script>\n',
            ),
        )

    # Success page
    body = """<section class="ex-success" id="ex-success">
  <span class="eyebrow">Dealux Exclusive</span>
  <h1 id="ex-s-title">Confirming your payment…</h1>
  <p class="muted" id="ex-s-msg">One moment while we verify your checkout with Stripe.</p>
  <a class="btn btn-gold hidden" id="ex-s-dl" href="#">Download your PDF →</a>
  <p class="muted ex-note">Bookmark this page — the download link stays valid for 30 days.</p>
  <p><a href="/exclusive/">← Back to Dealux Exclusives</a></p>
</section>
<script src="/exclusive/success.js" defer></script>"""
    write(
        "exclusive/success/index.html",
        page(
            "Thank you — your download | Dealux Exclusive",
            "Download your Dealux Exclusive PDF.",
            f"{SITE}/exclusive/success/",
            body,
            '<meta name="robots" content="noindex">\n',
        ),
    )

    # Lookup for the download function
    lookup = {
        it["slug"]: {
            "id": it["id"],
            "title": it["title"],
            "category": it["category"],
            "type": it["type"],
            "description": it["description"],
            "pages": int(it["pages"]),
            "file": it["file_name"],
        }
        for it in items
    }
    write(
        "netlify/lib/exclusive-items.mjs",
        "// Generated by scripts/build-exclusive.py — do not edit by hand.\nexport default "
        + json.dumps(lookup, ensure_ascii=False, separators=(",", ":"))
        + ";\n",
    )

    urls = [f"{SITE}/exclusive/"] + [f"{SITE}/exclusive/{it['slug']}/" for it in items]
    write(
        "sitemap-exclusive.xml",
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "".join(f"  <url><loc>{u}</loc></url>\n" for u in urls)
        + "</urlset>\n",
    )
    print(f"Generated {len(items)} exclusive item pages")


if __name__ == "__main__":
    main()
