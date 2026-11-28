// Cloudflare Pages Function: renders /deals/<slug>/ detail pages from the data shards, so the
// deals directory keeps working even when the Netlify origin is unavailable.
//  - Awin promotion pages (scripts/import-awin-promotions.py) live in /data/awin-deals/<pid % 128>.json
//    with chrome /data/awin-deals/shell.html.
//  - Static deal pages (scripts/build-deals.py) live in /data/deals/<hash % 64>.json with chrome
//    /data/deals/shell.html.
// Slugs not in a shard fall through to the static file.

const AWIN_SHARDS = 128;
const DEAL_SHARDS = 64;

function pick(text, key) {
  const needle = JSON.stringify(key) + ':';
  let i = text.indexOf(needle);
  while (i > 0 && text[i - 1] !== '{' && text[i - 1] !== ',' && !/\s/.test(text[i - 1])) i = text.indexOf(needle, i + 1);
  if (i < 0) return null;
  const start = i + needle.length;
  let depth = 0, inStr = false;
  for (let j = start; j < text.length; j++) {
    const c = text[j];
    if (inStr) {
      if (c === '\\') j++;
      else if (c === '"') inStr = false;
    } else if (c === '"') inStr = true;
    else if (c === '[' || c === '{') depth++;
    else if (c === ']' || c === '}') {
      if (--depth === 0) {
        try { return JSON.parse(text.slice(start, j + 1)); } catch { return null; }
      }
    }
  }
  return null;
}

function dealShardOf(slug) {
  let h = 5381;
  for (let i = 0; i < slug.length; i++) h = ((h * 33) ^ slug.charCodeAt(i)) >>> 0;
  return h % DEAL_SHARDS;
}

async function lookup(env, url, slug) {
  const m = slug.match(/-(\d+)$/);
  if (m) {
    const r = await env.ASSETS.fetch(new URL(`/data/awin-deals/${Number(m[1]) % AWIN_SHARDS}.json`, url));
    if (r.ok) {
      const v = pick(await r.text(), slug);
      if (Array.isArray(v)) return { rec: v, shell: '/data/awin-deals/shell.html' };
    }
  }
  const r = await env.ASSETS.fetch(new URL(`/data/deals/${dealShardOf(slug)}.json`, url));
  if (r.ok) {
    const v = pick(await r.text(), slug);
    if (Array.isArray(v)) return { rec: v, shell: '/data/deals/shell.html' };
  }
  return null;
}

export async function onRequestGet(context) {
  const { request, env, params } = context;
  const url = new URL(request.url);
  const slug = String(params.slug || '');
  if (!/^[a-z0-9-]+$/.test(slug)) return context.next();

  const found = await lookup(env, url, slug);
  if (!found) return context.next();
  if (!url.pathname.endsWith('/')) return Response.redirect(`${url.origin}/deals/${slug}/`, 301);

  const shellRes = await env.ASSETS.fetch(new URL(found.shell, url));
  if (!shellRes.ok) return context.next();
  const [title, meta, canonical, robots, body] = found.rec;
  const slots = { title, meta, canonical, robots, body };
  const html = (await shellRes.text()).replace(/\{\{(title|meta|canonical|robots|body)\}\}/g, (_, k) => slots[k] ?? '');

  return new Response(html, {
    headers: { 'content-type': 'text/html; charset=utf-8', 'cache-control': 'public, max-age=0, must-revalidate' },
  });
}
