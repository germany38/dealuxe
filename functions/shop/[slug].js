// Cloudflare Pages Function: server-renders /shop/<slug> product pages so search engines
// get a unique, indexable page per product (title, description, canonical, structured data,
// links to related products) instead of the shared "Loading…" shell.
// Only /shop/* and /tickets/* reach Functions (see /_routes.json); everything else stays a free static asset.
// Data comes from the same static shards the browser uses (/data/img/<n>.json).

const IMG_SHARDS = 64;
const RESERVED = new Set(['product', 'brand', 'department', 'type']);
const RELATED = 12;
let template = null;

const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
const slugify = (s) => s.toLowerCase().normalize('NFKD').replace(/[\u0300-\u036f]/g, () => '').replace(/&/g, () => 'and').replace(/[^a-z0-9]+/g, () => '-').replace(/^-|-$/g, () => '');
const titleCase = (s) => s.replace(/-+/g, () => ' ').replace(/\b\w/g, (c) => c.toUpperCase());
const jsonLd = (o) => `<script type="application/ld+json">${JSON.stringify(o).replace(/</g, () => '\\u003c')}</script>`;

function shardOf(slug) {
  let h = 5381;
  for (let i = 0; i < slug.length; i++) h = ((h * 33) ^ slug.charCodeAt(i)) >>> 0;
  return h % IMG_SHARDS;
}

function money(price, currency) {
  if (!price) return '';
  try {
    return Number(price).toLocaleString('en-US', { style: 'currency', currency: currency || 'USD' });
  } catch {
    return `${price} ${currency || ''}`;
  }
}

// Shards are ~1.5 MB; parsing a whole one would blow the free plan's CPU budget,
// so find the one key in the raw text and parse just its value.
function pick(text, key) {
  const needle = JSON.stringify(key) + ':';
  let i = text.indexOf(needle);
  while (i > 0 && text[i - 1] !== '{' && text[i - 1] !== ',') i = text.indexOf(needle, i + 1);
  if (i < 0) return null;
  const start = i + needle.length;
  let depth = 0, inStr = false;
  for (let k = start; k < text.length; k++) {
    const c = text[k];
    if (inStr) {
      if (c === '\\') k++;
      else if (c === '"') inStr = false;
    } else if (c === '"') inStr = true;
    else if (c === '[' || c === '{') depth++;
    else if (c === ']' || c === '}') {
      if (--depth === 0) return JSON.parse(text.slice(start, k + 1));
    }
  }
  return null;
}

async function asset(env, request, path) {
  const res = await env.ASSETS.fetch(new URL(path, request.url));
  return res.ok ? res.text() : null;
}

// Neighbouring products from the brand's list, read from a small window of the raw file.
function relatedFrom(listText, slug) {
  const at = listText.indexOf(JSON.stringify(slug));
  const from = at < 0 ? 0 : Math.max(0, at - 1200);
  const to = from + 2400 + slug.length;
  const slugs = [...listText.slice(from, to).matchAll(/"([a-z0-9-]+)"/g)].map((m) => m[1]);
  // The window edges may cut a slug in half.
  if (from > 0) slugs.shift();
  if (to < listText.length) slugs.pop();
  return slugs.filter((s) => s !== slug).slice(0, RELATED);
}

async function notFound(env, request) {
  const body = (await asset(env, request, '/404.html')) || 'Not found';
  return new Response(body, { status: 404, headers: { 'content-type': 'text/html; charset=utf-8', 'x-robots-tag': 'noindex' } });
}

export async function onRequestGet(context) {
  const { request, env, params } = context;
  const url = new URL(request.url);
  const slug = decodeURIComponent(String(params.slug || '')).toLowerCase();

  if (RESERVED.has(slug)) {
    // Old query-string product URLs permanently move to the clean, indexable URL.
    const p = slug === 'product' && url.searchParams.get('p');
    if (p) return Response.redirect(`${url.origin}/shop/${encodeURIComponent(p)}`, 301);
    return context.next();
  }
  if (url.pathname.endsWith('/')) return Response.redirect(`${url.origin}/shop/${encodeURIComponent(slug)}`, 301);

  const shard = await asset(env, request, `/data/img/${shardOf(slug)}.json`);
  const record = shard && pick(shard, slug);
  if (!record) return notFound(env, request);
  const [name, price, currency, brand, image, link, description] = record;

  const brandSlug = brand ? slugify(brand) : '';
  const [, brandList] = await Promise.all([
    template ? null : asset(env, request, '/shop/product/').then((t) => (template = t)),
    brandSlug ? asset(env, request, `/data/list/brand-${brandSlug}.json`) : null,
  ]);
  if (!template) return context.next();

  const canonical = `https://dealuxapp.com/shop/${slug}`;
  const priceText = money(price, currency);
  const byBrand = brand && !name.toLowerCase().includes(brand.toLowerCase()) ? ` by ${brand}` : '';
  const desc = (description || `${name}${byBrand}${priceText ? ` for ${priceText}` : ''}. Compare prices, photos and the best deal on Dealux.`).replace(/\s+/g, () => ' ').slice(0, 300);
  const brandUrl = brandList ? `/shop/brand/${brandSlug}/` : '';
  const related = brandList ? relatedFrom(brandList, slug) : [];

  const product = {
    '@context': 'https://schema.org',
    '@type': 'Product',
    name,
    description: desc,
    url: canonical,
    ...(image ? { image } : {}),
    ...(brand ? { brand: { '@type': 'Brand', name: brand } } : {}),
    ...(price ? { offers: { '@type': 'Offer', price, priceCurrency: currency || 'USD', availability: 'https://schema.org/InStock', url: canonical } } : {}),
  };
  const crumbs = [['Shop', 'https://dealuxapp.com/shop/'], ...(brandUrl ? [[brand, `https://dealuxapp.com${brandUrl}`]] : []), [name, canonical]];
  const breadcrumb = {
    '@context': 'https://schema.org',
    '@type': 'BreadcrumbList',
    itemListElement: crumbs.map(([n, u], i) => ({ '@type': 'ListItem', position: i + 1, name: n, item: u })),
  };

  const head =
    `<link rel="canonical" href="${esc(canonical)}">\n<meta name="robots" content="index, follow, max-image-preview:large">` +
    `\n<meta property="og:type" content="product"><meta property="og:title" content="${esc(name)}"><meta property="og:description" content="${esc(desc)}"><meta property="og:url" content="${esc(canonical)}">` +
    (image ? `<meta property="og:image" content="${esc(image)}">` : '') +
    `\n${jsonLd(product)}\n${jsonLd(breadcrumb)}`;
  const crumbNav =
    `<nav class="muted" aria-label="Breadcrumb"><a href="/shop/">Shop</a>` +
    (brandUrl ? ` › <a href="${brandUrl}">${esc(brand)}</a>` : '') +
    `</nav>`;
  const relatedHtml = related.length
    ? `\n<section class="product-related" style="clear:both;margin:32px 0">\n  <h2>More from ${esc(brand)}</h2>\n  <ul>` +
      related.map((s) => `<li><a href="/shop/${encodeURIComponent(s)}">${esc(titleCase(s))}</a></li>`).join('') +
      `</ul>\n  <p><a class="btn" href="${brandUrl}">See all ${esc(brand)} products →</a></p>\n</section>`
    : '';

  let html = template
    .replace(/<title>.*?<\/title>/, () => `<title>${esc(name + byBrand)} — Dealux</title>`)
    .replace(/<meta name="description" content="[^"]*">/, () => `<meta name="description" content="${esc(desc)}">`)
    .replace(/<link rel="canonical" href="[^"]*">/, () => head)
    .replace('<a class="muted" href="/shop/">← Back to shop</a>', () => crumbNav)
    .replace('<img data-img-slug=""', () => `<img data-img-slug="${esc(slug)}"${image ? ` src="${esc(image)}"` : ''}`)
    .replace(' referrerpolicy="no-referrer" alt=""></span>', () => ` referrerpolicy="no-referrer" alt="${esc(name)}"></span>`)
    .replace(/<h1 data-product-name>.*?<\/h1>/, () => `<h1 data-product-name>${esc(name)}</h1>`)
    .replace(
      '<p class="muted" data-product-brand></p>',
      () =>
        `<p class="muted" data-product-brand>${esc([priceText, brand && `by ${brand}`].filter(Boolean).join(' · '))}</p>` +
        (description ? `\n  <p class="product-description">${esc(description)}</p>` : ''),
    )
    .replace('</main>', () => `${relatedHtml}\n</main>`);
  if (link) html = html.replace('<a class="btn btn-gold hidden" data-product-link', () => `<a class="btn btn-gold" href="${esc(link)}" data-product-link`);

  return new Response(html, {
    headers: { 'content-type': 'text/html; charset=utf-8', 'cache-control': 'public, max-age=3600' },
  });
}
