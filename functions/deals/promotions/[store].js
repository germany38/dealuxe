// Cloudflare Pages Function: renders /deals/promotions/<store>/ hub pages from the data shards
// written by scripts/offload-deal-pages.py, so the store hubs keep working even when the Netlify
// origin is unavailable. The shared chrome is /data/deals/shell.html. Stores not in a shard fall
// through to the static file (the A-Z directory at /deals/promotions/ stays static).

const SHARDS = 64;

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

function shardOf(slug) {
  let h = 5381;
  for (let i = 0; i < slug.length; i++) h = ((h * 33) ^ slug.charCodeAt(i)) >>> 0;
  return h % SHARDS;
}

export async function onRequestGet(context) {
  const { request, env, params } = context;
  const url = new URL(request.url);
  const store = String(params.store || '');
  if (!/^[a-z0-9-]+$/.test(store)) return context.next();

  const shardRes = await env.ASSETS.fetch(new URL(`/data/deals/${shardOf(store)}.json`, url));
  if (!shardRes.ok) return context.next();
  const rec = pick(await shardRes.text(), store);
  if (!Array.isArray(rec)) return context.next();
  if (!url.pathname.endsWith('/')) return Response.redirect(`${url.origin}/deals/promotions/${store}/`, 301);

  const shellRes = await env.ASSETS.fetch(new URL('/data/deals/shell.html', url));
  if (!shellRes.ok) return context.next();
  const [title, meta, canonical, robots, body] = rec;
  const slots = { title, meta, canonical, robots, body };
  const html = (await shellRes.text()).replace(/\{\{(title|meta|canonical|robots|body)\}\}/g, (_, k) => slots[k] ?? '');

  return new Response(html, {
    headers: { 'content-type': 'text/html; charset=utf-8', 'cache-control': 'public, max-age=0, must-revalidate' },
  });
}
