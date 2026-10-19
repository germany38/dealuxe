import type { Config, Context } from "@netlify/edge-functions";

// Server-renders /shop/<slug> product pages so search engines get a real 200 page
// with the product's title, description, canonical URL and structured data.
// Product data lives in the same static shards the browser uses (/data/img/<n>.json).

const IMG_SHARDS = 64;
const RESERVED = new Set(["product", "brand", "department", "type"]);
const shardCache = new Map<number, Promise<Record<string, string[]>>>();
let templatePromise: Promise<string> | null = null;

function shardOf(slug: string) {
  let h = 5381;
  for (let i = 0; i < slug.length; i++) h = ((h * 33) ^ slug.charCodeAt(i)) >>> 0;
  return h % IMG_SHARDS;
}

function esc(s: string) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]!);
}

function money(price: string, currency: string) {
  if (!price) return "";
  try {
    return Number(price).toLocaleString("en-US", { style: "currency", currency: currency || "USD" });
  } catch {
    return `${price} ${currency || ""}`;
  }
}

function loadShard(origin: string, n: number) {
  if (!shardCache.has(n)) {
    const p = fetch(`${origin}/data/img/${n}.json`).then((r) => (r.ok ? r.json() : {})).catch(() => ({}));
    shardCache.set(n, p);
  }
  return shardCache.get(n)!;
}

export default async (req: Request, context: Context) => {
  const url = new URL(req.url);

  // Old query-string product URLs permanently move to the clean, indexable URL.
  if (url.pathname === "/shop/product/" || url.pathname === "/shop/product") {
    const p = url.searchParams.get("p");
    if (p) return Response.redirect(`${url.origin}/shop/${encodeURIComponent(p)}`, 301);
    return;
  }

  const m = url.pathname.match(/^\/shop\/([^\/]+)\/?$/);
  if (!m || RESERVED.has(m[1])) return;
  const slug = decodeURIComponent(m[1]);

  const record = (await loadShard(url.origin, shardOf(slug)))[slug];
  if (!record) return context.next();
  const [name, price, currency, brand, image, link, description] = record;

  templatePromise ??= fetch(`${url.origin}/shop/product/index.html`).then((r) => r.text());
  let html = await templatePromise;

  const canonical = `https://dealuxapp.com/shop/${slug}`;
  const priceText = money(price, currency);
  const desc = (description || `${name}${brand ? ` by ${brand}` : ""}${priceText ? ` — ${priceText}` : ""}. Compare deals on Dealux.`).slice(0, 300);
  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "Product",
    name,
    description: desc,
    url: canonical,
    ...(image ? { image } : {}),
    ...(brand ? { brand: { "@type": "Brand", name: brand } } : {}),
    ...(price
      ? { offers: { "@type": "Offer", price, priceCurrency: currency || "USD", availability: "https://schema.org/InStock", url: canonical } }
      : {}),
  };

  // Google rejects Product markup without an offer, so price-less listings (e.g. affiliate
  // banners and text links) are described as a plain web page instead.
  const structured = price
    ? jsonLd
    : { "@context": "https://schema.org", "@type": "WebPage", name, description: desc, url: canonical, ...(image ? { image } : {}) };

  html = html
    .replace(/<title>.*?<\/title>/, `<title>${esc(name)} — Dealux</title>`)
    .replace(/<meta name="description" content="[^"]*">/, `<meta name="description" content="${esc(desc)}">`)
    .replace(
      /<link rel="canonical" href="[^"]*">/,
      `<link rel="canonical" href="${esc(canonical)}">\n<meta name="robots" content="index, follow">` +
        `\n<meta property="og:type" content="product"><meta property="og:title" content="${esc(name)}"><meta property="og:url" content="${esc(canonical)}">` +
        (image ? `<meta property="og:image" content="${esc(image)}">` : "") +
        `\n<script type="application/ld+json">${JSON.stringify(structured).replace(/</g, "\\u003c")}</script>`,
    )
    .replace('<img data-img-slug=""', `<img data-img-slug="${esc(slug)}"${image ? ` src="${esc(image)}"` : ""}`)
    .replace(/<h1 data-product-name>.*?<\/h1>/, `<h1 data-product-name>${esc(name)}</h1>`)
    .replace(
      /<p class="muted" data-product-brand><\/p>/,
      `<p class="muted" data-product-brand>${esc([priceText, brand && `by ${brand}`].filter(Boolean).join(" · "))}</p>` +
        (description ? `\n  <p class="product-description">${esc(description)}</p>` : ""),
    );
  if (link) {
    html = html.replace(
      '<a class="btn btn-gold hidden" data-product-link',
      `<a class="btn btn-gold" href="${esc(link)}" data-product-link`,
    );
  }

  return new Response(html, {
    headers: { "content-type": "text/html; charset=utf-8", "cache-control": "public, max-age=0, must-revalidate", "netlify-cdn-cache-control": "public, s-maxage=86400, stale-while-revalidate=604800" },
  });
};

export const config: Config = {
  path: "/shop/*",
  excludedPath: ["/shop/brand/*", "/shop/department/*", "/shop/type/*"],
  cache: "manual",
};
