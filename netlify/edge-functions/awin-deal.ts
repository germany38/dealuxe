import type { Config, Context } from "@netlify/edge-functions";

// Serves Awin promotion deal pages (/deals/<slug>/) from data shards written by
// scripts/offload-awin-deal-pages.py. Each slug ends in its Awin promotion id; the shard is
// id % 128. The shared page chrome is /data/awin-deals/shell.html with placeholders for the
// per-page title, meta description, canonical, robots and article body. Slugs that are not in
// a shard fall through to the static files.

const SHARDS = 128;
const shardCache = new Map<number, Promise<Record<string, string[]>>>();
let shellPromise: Promise<string> | null = null;

function loadShard(origin: string, n: number) {
  if (!shardCache.has(n)) {
    const p = fetch(`${origin}/data/awin-deals/${n}.json`).then((r) => (r.ok ? r.json() : {})).catch(() => ({}));
    shardCache.set(n, p);
  }
  return shardCache.get(n)!;
}

export default async (req: Request, context: Context) => {
  const url = new URL(req.url);
  const m = url.pathname.match(/^\/deals\/([a-z0-9-]+-(\d+))\/?$/);
  if (!m) return context.next();
  const [, slug, pid] = m;

  const rec = (await loadShard(url.origin, Number(pid) % SHARDS))[slug];
  if (!rec) return context.next();
  if (!url.pathname.endsWith("/")) return Response.redirect(`${url.origin}/deals/${slug}/`, 301);

  shellPromise ??= fetch(`${url.origin}/data/awin-deals/shell.html`).then((r) => r.text());
  const [title, meta, canonical, robots, body] = rec;
  const slots: Record<string, string> = { title, meta, canonical, robots, body };
  // Single pass so inserted content is never rescanned for placeholders.
  const html = (await shellPromise).replace(/\{\{(title|meta|canonical|robots|body)\}\}/g, (_, k) => slots[k]);

  return new Response(html, {
    headers: {
      "content-type": "text/html; charset=utf-8",
      "cache-control": "public, max-age=0, must-revalidate",
      "netlify-cdn-cache-control": "public, s-maxage=86400, stale-while-revalidate=604800",
    },
  });
};

export const config: Config = {
  path: "/deals/*",
  excludedPath: ["/deals/", "/deals/promotions/*"],
  cache: "manual",
};
