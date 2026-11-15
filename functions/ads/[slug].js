// Cloudflare Pages Function: renders /ads/<slug>/ offer pages that have no static file, the same way
// netlify/edge-functions/ad-page.ts does on Netlify, so these pages keep working on Cloudflare even when
// the Netlify site is unavailable. Data comes from the static shards /data/ad-pages/<adid % 128>.json
// and the shared chrome /data/ad-pages/shell.html. Slugs not in a shard fall through to the static file.

const SHARDS = 128;

// Shards are ~1 MB; parsing a whole one would blow the free plan's CPU budget, so find the one
// key in the raw text and parse just its value (an array of strings).
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
      depth--;
      if (depth === 0) {
        try { return JSON.parse(text.slice(start, j + 1)); } catch { return null; }
      }
    }
  }
  return null;
}

export async function onRequestGet(context) {
  const { request, env, params } = context;
  const url = new URL(request.url);
  const slug = String(params.slug || '');
  const m = slug.match(/^[a-z0-9-]+-(\d+)$/);
  if (!m) return context.next();

  const shardRes = await env.ASSETS.fetch(new URL(`/data/ad-pages/${Number(m[1]) % SHARDS}.json`, url));
  if (!shardRes.ok) return context.next();
  const page = pick(await shardRes.text(), slug);
  if (!Array.isArray(page)) return context.next();
  if (!url.pathname.endsWith('/')) return Response.redirect(`${url.origin}/ads/${slug}/`, 301);

  const shellRes = await env.ASSETS.fetch(new URL('/data/ad-pages/shell.html', url));
  if (!shellRes.ok) return context.next();
  const [title, desc, head, main] = page;
  const slots = { title, desc, head, main, canonical: `https://dealuxapp.com/ads/${slug}/` };
  const html = (await shellRes.text()).replace(/\{\{(title|desc|canonical|head|main)\}\}/g, (_, k) => slots[k] ?? '');

  return new Response(html, {
    headers: { 'content-type': 'text/html; charset=utf-8', 'cache-control': 'public, max-age=0, must-revalidate' },
  });
}
