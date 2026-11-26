#!/usr/bin/env python3
"""Create a Journal article for each newly imported merchant brand.

Usage: python3 scripts/build-new-merchant-articles.py
       python3 scripts/update-counts.py

Each /journal/<slug>/ page follows the standard Journal layout and pairs a gold
"When you're ready" affiliate button with a black "Shop for <brand>" button that
links to the brand's /shop/brand/ directory, matching the rest of the Journal.
The article index and sitemaps are refreshed by scripts/update-counts.py.
"""
import html
import json
import os
from pathlib import Path

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

TEMPLATE = Path('journal/zonveer-electric-dirt-bikes-buyers-guide/index.html')
DATE = '2026-11-26'
SITE = 'https://dealuxapp.com'

ARTICLES = [
    {
        'slug': 'trophycentral-awards-and-personalized-gifts-guide',
        'brand': 'TrophyCentral',
        'shop_slug': 'trophycentral',
        'affiliate': 'https://www.awin1.com/pclick.php?p=41923031137&a=2893129&m=80917',
        'topic': 'Gifts',
        'read': '4 min read',
        'title': 'TrophyCentral: Awards, Trophies and Personalized Gifts',
        'description': 'TrophyCentral makes engraved awards, trophies and personalized gifts. Learn how to choose crystal, glass and acrylic pieces and what to check before ordering.',
        'body': '''<p>Recognition is one of the few things people keep for decades, and TrophyCentral has built a business around getting it right. The company supplies trophies, awards and personalized gifts for teams, schools, tournaments and corporate milestones. You can browse the current range on the <a rel="sponsored nofollow noopener" target="_blank" href="{aff}">official TrophyCentral site</a>.</p>
<h2>Start with the occasion</h2>
<p>An award should fit the moment. A youth sports trophy, a retirement keepsake, a sales-recognition piece and a memorial gift all call for different shapes and materials. TrophyCentral separates its catalog by occasion and recipient, which makes it easier to narrow the field before you compare individual pieces. Decide who is receiving it and what the milestone is, then match the piece to that story.</p>
<h2>Crystal, glass and acrylic</h2>
<p>The three common materials behave differently. Optic crystal reads bright and premium and takes a crisp etch; art glass gives each piece a one-of-a-kind quality, with lyrical swirls and suspended bubbles that vary from item to item; acrylic is the lighter, lower-cost option for volume awards. If you need a uniform set for a large event, ask how consistent a run will be. If you are buying a single standout piece, the natural variation in art glass is part of the appeal.</p>
<h2>Personalization and lead time</h2>
<p>Engraving is what turns a generic award into a personal one. Have your wording, dates and any logo ready before you order, and confirm the etchable area for the size you have chosen — a larger piece gives you more room for a name, title and message. Pieces that are individually crafted can take longer to produce, so order ahead of the event rather than the week of. It is also worth reading the returns and replacement terms up front, since personalized items are usually made to order.</p>
<p>If you want to keep browsing, start with the <a href="/shop/brand/trophycentral/">TrophyCentral shop directory</a> to see the range grouped with other gift and award ideas.</p>''',
    },
    {
        'slug': 'brnd-collection-designer-fragrance-sets-guide',
        'brand': 'BRND COLLECTION',
        'shop_slug': 'brnd-collection',
        'affiliate': 'https://www.awin1.com/pclick.php?p=46850903291&a=2893129&m=131822',
        'topic': 'Beauty',
        'read': '4 min read',
        'title': 'BRND COLLECTION: Designer Fragrance Sets and Gift Edits',
        'description': 'BRND COLLECTION curates designer fragrance sets and gift edits. See how to choose a scent pairing, understand EDP and EDT, and pick a set that fits the occasion.',
        'body': '''<p>Fragrance is one of the most personal gifts you can give, which is exactly why it is so easy to get wrong. BRND COLLECTION takes some of that risk out by curating matched sets it calls "edits" — designer scents bundled for a specific mood or occasion. You can see the current edits on the <a rel="sponsored nofollow noopener" target="_blank" href="{aff}">official BRND COLLECTION site</a>.</p>
<h2>What a fragrance edit is</h2>
<p>Rather than a single bottle, an edit pairs two fragrances so the recipient gets a daytime and an evening option, or a his-and-hers combination. A typical set might couple a soft, clean everyday scent with something warmer and more confident for nights out. That pairing is the whole point: it turns a single guess into a small wardrobe, and it gives the recipient options without asking them to choose a full bottle blind.</p>
<h2>EDP, EDT and what the labels mean</h2>
<p>Concentration is the quickest way to read a bottle. Eau de toilette (EDT) is lighter and generally sits closer to the skin; eau de parfum (EDP) carries more oil and usually lasts longer and projects further. Neither is better in the abstract — it comes down to how the person likes to wear scent. If they prefer a quiet, close fragrance, an EDT is often the better fit; if they want something that carries through an evening, an EDP will usually serve better.</p>
<h2>Choosing a set as a gift</h2>
<p>Lean on the occasion. A holiday or birthday set can be more playful; an anniversary or thank-you gift usually calls for something more timeless. Check the bottle sizes and included pieces so there are no surprises, and look at the house and notes involved — designer names people already recognise make the gift feel considered. If you are unsure of their taste, a paired set gives you two chances to land it.</p>
<p>To explore further, browse the <a href="/shop/brand/brnd-collection/">BRND COLLECTION shop directory</a> alongside other beauty and fragrance picks.</p>''',
    },
    {
        'slug': 'pawfurever-engraved-pet-tags-guide',
        'brand': 'PawFurEver',
        'shop_slug': 'pawfurever',
        'affiliate': 'https://www.awin1.com/pclick.php?p=44939909685&a=2893129&m=123388',
        'topic': 'Pets',
        'read': '3 min read',
        'title': 'PawFurEver: Engraved Personalized Pet Tags and Pet Gifts',
        'description': 'PawFurEver engraves breed portraits onto stainless steel pet tags. Learn how the peek-a-boo design works, why deep engraving lasts, and how to choose the right tag.',
        'body': '''<p>A pet tag is one of the few things a dog wears every single day, so it is worth choosing carefully. PawFurEver makes personalized tags with a breed portrait and your pet's name engraved into stainless steel. You can browse the range on the <a rel="sponsored nofollow noopener" target="_blank" href="{aff}">official PawFurEver site</a>.</p>
<h2>The peek-a-boo portrait</h2>
<p>What sets these tags apart is the artwork. Instead of a generic paw or bone, each design shows a specific breed — a Shetland Sheepdog, a Shiba Inu and many others — peeking over the edge of the tag. The idea is a portrait that actually looks like your dog rather than a stock silhouette, which is what makes them work as a gift for a particular pet owner.</p>
<h2>Why deep engraving matters</h2>
<p>A tag takes a beating: it knocks against a collar, a bowl and everything else on a walk. PawFurEver engraves the name and artwork deep into the metal rather than printing on the surface, so it holds up to daily wear and stays legible far longer. Stainless steel also resists rust and tarnish, which matters for a tag that is outdoors in all weather.</p>
<h2>Choosing the right tag</h2>
<p>Match the tag to the collar and the dog. Consider the size and weight so it does not overwhelm a small breed, and think about what contact information you want on the back — a phone number is the most useful single detail if a pet ever slips out. Because the tags are personalized, plan ahead if you need one for a birthday or a new puppy. A breed-specific tag is also a genuinely thoughtful gift for a friend or family member who is hard to shop for.</p>
<p>If you want to see more, start with the <a href="/shop/brand/pawfurever/">PawFurEver shop directory</a> to explore related pet gear and gifting ideas.</p>''',
    },
]


def esc(text):
    return html.escape(text, quote=True)


def ld_json(article):
    return json.dumps({
        '@context': 'https://schema.org',
        '@type': 'Article',
        'headline': article['title'],
        'description': article['description'],
        'mainEntityOfPage': f'{SITE}/journal/{article["slug"]}/',
        'inLanguage': 'en',
        'datePublished': DATE,
        'dateModified': DATE,
        'author': {'@type': 'Organization', 'name': 'Dealux'},
        'publisher': {'@type': 'Organization', 'name': 'Dealux', 'url': SITE},
    }, ensure_ascii=False)


def render(article):
    import re
    t = TEMPLATE.read_text(encoding='utf-8')
    url = f'{SITE}/journal/{article["slug"]}/'
    title = esc(article['title'])
    desc = esc(article['description'])
    aff = article['affiliate']
    brand = esc(article['brand'])
    shop = f'/shop/brand/{article["shop_slug"]}/'

    t = re.sub(r'<title>.*?</title>', f'<title>{title} — Dealux Journal</title>', t, count=1)
    t = re.sub(r'<meta name="description" content="[^"]*">', f'<meta name="description" content="{desc}">', t, count=1)
    t = re.sub(r'<link rel="canonical" href="[^"]*">', f'<link rel="canonical" href="{url}">', t, count=1)
    t = re.sub(r'<meta property="og:title" content="[^"]*">', f'<meta property="og:title" content="{title}">', t, count=1)
    t = re.sub(r'<meta property="og:description" content="[^"]*">', f'<meta property="og:description" content="{desc}">', t, count=1)
    t = re.sub(r'<meta property="og:url" content="[^"]*">', f'<meta property="og:url" content="{url}">', t, count=1)
    t = re.sub(r'<meta name="twitter:title" content="[^"]*">', f'<meta name="twitter:title" content="{title}">', t, count=1)
    t = re.sub(r'<meta name="twitter:description" content="[^"]*">', f'<meta name="twitter:description" content="{desc}">', t, count=1)
    t = re.sub(r'<script type="application/ld\+json">.*?</script>',
               f'<script type="application/ld+json">{ld_json(article)}</script>', t, count=1, flags=re.S)
    t = re.sub(r'(<a class="muted" href="/journal/">← The Journal</a>\s*<span class="eyebrow">).*?(</span>)',
               lambda m: m.group(1) + f'{esc(article["topic"])} · {esc(article["read"])}' + m.group(2), t, count=1)
    t = re.sub(r'<h1>.*?</h1>', f'<h1>{title}</h1>', t, count=1)
    t = re.sub(r'<!-- dx-cta-top -->.*?<!-- /dx-cta-top -->',
               f'<!-- dx-cta-top -->\n<div class="dx-brand-cta dx-cta-top">'
               f'<a class="btn btn-gold" href="{esc(aff)}" target="_blank" rel="sponsored nofollow noopener">Visit {brand} →</a>'
               f'<a class="btn btn-dark" href="{shop}">Shop for {brand} →</a></div>\n<!-- /dx-cta-top -->',
               t, count=1, flags=re.S)
    body = (
        '<div class="post-body"><div class="post-content">\n'
        '<p class="disclosure"><em>Disclosure: Dealux may earn a commission on purchases made through links '
        'on this page, at no extra cost to you.</em></p>\n'
        + article['body'].format(aff=esc(aff)) + '\n'
        '<div class="card promo-card article-cta"><p><strong>Ready to take a closer look?</strong></p>'
        f'<span class="dx-brand-cta"><a class="btn btn-gold" href="{esc(aff)}" target="_blank" rel="sponsored nofollow noopener">Visit {brand} →</a>'
        f'<a class="btn btn-dark" href="{shop}">Shop for {brand} →</a></span></div>\n'
        '<p><em>This article contains affiliate links, which means Dealux may be compensated if you make a '
        'purchase through them, at no extra cost to you.</em></p>\n'
        '</div></div>'
    )
    t = re.sub(r'<div class="post-body"><div class="post-content">.*?</div></div>\s*\n\s*</article>',
               body + '\n\n</article>', t, count=1, flags=re.S)
    return t


def main():
    for article in ARTICLES:
        out = Path('journal') / article['slug'] / 'index.html'
        content = render(article)
        if out.exists() and out.read_text(encoding='utf-8') == content:
            continue
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(content, encoding='utf-8')
        print(f'wrote {out}')


if __name__ == '__main__':
    main()
