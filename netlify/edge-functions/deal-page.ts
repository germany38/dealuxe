import type { Config, Context } from "@netlify/edge-functions";

// Serves /deals/<slug>/ detail pages and /deals/promotions/<store>/ hubs from the data shards, so
// the deals directory keeps working even when this Netlify origin is unavailable.
//  - Awin promotion pages (scripts/import-awin-promotions.py) live in /data/awin-deals/<pid % 128>.json
//    with chrome /data/awin-deals/shell.html.
//  - Static deal pages and store hubs (scripts/build-deals.py, scripts/offload-deal-pages.py) live in
//    /data/deals/<hash % 64>.json with chrome /data/deals/shell.html.
// Slugs that are not in a shard fall through to the static files.

const AWIN_SHARDS = 128;
const DEAL_SHARDS = 64;
const shardCache = new Map<string, Promise<Record<string, string[]>>>();
const shellCache = new Map<string, Promise<string>>();

function shardOf(slug: string) {
  let h = 5381;
  for (let i = 0; i < slug.length; i++) h = ((h * 33) ^ slug.charCodeAt(i)) >>> 0;
  return h % DEAL_SHARDS;
}

function loadShard(origin: string, path: string) {
  if (!shardCache.has(path)) {
    const p = fetch(`${origin}${path}`).then((r) => (r.ok ? r.json() : {})).catch(() => ({}));
    shardCache.set(path, p);
  }
  return shardCache.get(path)!;
}

function loadShell(origin: string, path: string) {
  if (!shellCache.has(path)) shellCache.set(path, fetch(`${origin}${path}`).then((r) => r.text()));
  return shellCache.get(path)!;
}

async function lookup(origin: string, slug: string) {
  const m = slug.match(/-(\d+)$/);
  if (m) {
    const rec = (await loadShard(origin, `/data/awin-deals/${Number(m[1]) % AWIN_SHARDS}.json`))[slug];
    if (rec) return { rec, shell: "/data/awin-deals/shell.html" };
  }
  const rec = (await loadShard(origin, `/data/deals/${shardOf(slug)}.json`))[slug];
  if (rec) return { rec, shell: "/data/deals/shell.html" };
  return null;
}

export default async (req: Request, context: Context) => {
  const url = new URL(req.url);
  let slug: string;
  let prefix: string;
  const hub = url.pathname.match(/^\/deals\/promotions\/([a-z0-9-]+)\/?$/);
  if (hub) {
    slug = hub[1];
    prefix = "/deals/promotions/";
  } else {
    const deal = url.pathname.match(/^\/deals\/([a-z0-9-]+)\/?$/);
    if (!deal) return context.next();
    slug = deal[1];
    prefix = "/deals/";
  }

  const found = await lookup(url.origin, slug);
  if (!found) return context.next();
  if (!url.pathname.endsWith("/")) return Response.redirect(`${url.origin}${prefix}${slug}/`, 301);

  const [title, meta, canonical, robots, body] = found.rec;
  const slots: Record<string, string> = { title, meta, canonical, robots, body };
  const html = (await loadShell(url.origin, found.shell)).replace(/\{\{(title|meta|canonical|robots|body)\}\}/g, (_, k) => slots[k]);

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
  excludedPath: ["/deals/", "/deals/promotions/"],
  cache: "manual",
};
