import type { Config, Context } from "@netlify/edge-functions";

// Serves /exclusive/<slug>/ item pages from the data shards written by
// scripts/offload-exclusive-pages.py. The shared page chrome is /data/exclusive/shell.html with
// placeholders for the per-page title, description, canonical, JSON-LD and body. Slugs that are
// not in a shard fall through to the static files (the directory, success page and previews).

const SHARDS = 64;
const shardCache = new Map<number, Promise<Record<string, string[]>>>();
let shellPromise: Promise<string> | null = null;

function shardOf(slug: string) {
  let h = 5381;
  for (let i = 0; i < slug.length; i++) h = ((h * 33) ^ slug.charCodeAt(i)) >>> 0;
  return h % SHARDS;
}

function loadShard(origin: string, n: number) {
  if (!shardCache.has(n)) {
    const p = fetch(`${origin}/data/exclusive/${n}.json`).then((r) => (r.ok ? r.json() : {})).catch(() => ({}));
    shardCache.set(n, p);
  }
  return shardCache.get(n)!;
}

export default async (req: Request, context: Context) => {
  const url = new URL(req.url);
  const m = url.pathname.match(/^\/exclusive\/([a-z0-9-]+)\/?$/);
  if (!m) return context.next();
  const slug = m[1];

  const rec = (await loadShard(url.origin, shardOf(slug)))[slug];
  if (!rec) return context.next();
  if (!url.pathname.endsWith("/")) return Response.redirect(`${url.origin}/exclusive/${slug}/`, 301);

  shellPromise ??= fetch(`${url.origin}/data/exclusive/shell.html`).then((r) => r.text());
  const [title, desc, canonical, ld, body] = rec;
  const slots: Record<string, string> = { title, desc, canonical, ld, body };
  const html = (await shellPromise).replace(/\{\{(title|desc|canonical|ld|body)\}\}/g, (_, k) => slots[k]);

  return new Response(html, {
    headers: {
      "content-type": "text/html; charset=utf-8",
      "cache-control": "public, max-age=0, must-revalidate",
      "netlify-cdn-cache-control": "public, s-maxage=86400, stale-while-revalidate=604800",
    },
  });
};

export const config: Config = {
  path: "/exclusive/*",
  excludedPath: ["/exclusive/", "/exclusive/previews/*", "/exclusive/success/*", "/exclusive/exclusive.css", "/exclusive/exclusive.js", "/exclusive/success.js"],
  cache: "manual",
};
