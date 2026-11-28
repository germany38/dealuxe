// Cloudflare Pages Function: renders /videos/<slug>/ watch pages from the data shards written
// by scripts/offload-videos-pages.py, so the video library keeps working even when the Netlify
// origin is unavailable. The shared chrome is /data/videos/shell.html; only the title,
// description, canonical, extra <head> block and page body differ per video. Slugs not in a
// shard fall through to the static file (the /videos/ index stays static).

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
  const slug = String(params.slug || '');
  if (!/^[a-z0-9-]+$/.test(slug)) return context.next();

  const shardRes = await env.ASSETS.fetch(new URL(`/data/videos/${shardOf(slug)}.json`, url));
  if (!shardRes.ok) return context.next();
  const rec = pick(await shardRes.text(), slug);
  if (!Array.isArray(rec)) return context.next();
  if (!url.pathname.endsWith('/')) return Response.redirect(`${url.origin}/videos/${slug}/`, 301);

  const shellRes = await env.ASSETS.fetch(new URL('/data/videos/shell.html', url));
  if (!shellRes.ok) return context.next();
  const [title, desc, canonical, headExtra, body] = rec;
  const slots = { title, desc, canonical, head_extra: headExtra };
  const html = (await shellRes.text()).replace(/\{\{(title|desc|canonical|head_extra)\}\}/g, (_, k) => slots[k] ?? '') + body;

  return new Response(html, {
    headers: { 'content-type': 'text/html; charset=utf-8', 'cache-control': 'public, max-age=0, must-revalidate' },
  });
}
