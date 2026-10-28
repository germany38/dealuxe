import type { Config, Context } from "@netlify/edge-functions";

// Server-renders /ads/<slug>/ offer pages that have no static file, so each banner is a real,
// indexable 200 page. scripts/build-image-ads.py pre-renders each page's head and body into
// /data/ad-pages/<adid % SHARDS>.json; the shared page chrome is /data/ad-pages/shell.html.

const SHARDS = 128;
const shardCache = new Map<number, Promise<Record<string, [string, string, string, string]>>>();
let shellPromise: Promise<string> | null = null;

function loadShard(origin: string, n: number) {
  if (!shardCache.has(n)) {
    const p = fetch(`${origin}/data/ad-pages/${n}.json`).then((r) => (r.ok ? r.json() : {})).catch(() => ({}));
    shardCache.set(n, p);
  }
  return shardCache.get(n)!;
}

export default async (req: Request, context: Context) => {
  const url = new URL(req.url);
  const m = url.pathname.match(/^\/ads\/([a-z0-9-]+-(\d+))\/?$/);
  if (!m) return;
  const [, slug, adid] = m;

  const page = (await loadShard(url.origin, Number(adid) % SHARDS))[slug];
  if (!page) return context.next();
  if (!url.pathname.endsWith("/")) return Response.redirect(`${url.origin}/ads/${slug}/`, 301);

  shellPromise ??= fetch(`${url.origin}/data/ad-pages/shell.html`).then((r) => r.text());
  const [title, desc, head, main] = page;
  const slots: Record<string, string> = {
    title, desc, head, main, canonical: `https://dealuxapp.com/ads/${slug}/`,
  };
  const html = (await shellPromise).replace(/\{\{(title|desc|canonical|head|main)\}\}/g, (_, k) => slots[k]);

  return new Response(html, {
    headers: { "content-type": "text/html; charset=utf-8", "cache-control": "public, max-age=0, must-revalidate", "netlify-cdn-cache-control": "public, s-maxage=86400, stale-while-revalidate=604800" },
  });
};

export const config: Config = {
  path: "/ads/*",
  excludedPath: ["/ads/", "/ads/page/*"],
  cache: "manual",
};
