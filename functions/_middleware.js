// Cloudflare Pages middleware: edge-caches the HTML that Functions produce, so repeat visits to
// /shop/<product>, /tickets/<event> and the forwarded sections are answered from Cloudflare's cache
// instead of re-reading large data shards or fetching from Netlify again. This keeps CPU time and
// outbound requests (what Cloudflare's paid plan bills on) low. Netlify API calls (/.netlify/*),
// non-GET requests and personalised responses (cookies) are never cached.

import { injectClickio } from '../scripts/clickio-tags.mjs';

const TTL = 3600; // seconds a page stays in the edge cache
const CACHEABLE = new Set([200, 301, 404, 410]);

export async function onRequest(context) {
  const { request } = context;
  const url = new URL(request.url);
  if (request.method !== 'GET' || url.pathname.startsWith('/.netlify/') || request.headers.has('Authorization')) {
    return context.next();
  }

  const cache = caches.default;
  const key = new Request(url.toString(), { method: 'GET' });
  const hit = await cache.match(key);
  if (hit) return hit;

  let res = await context.next();
  // Pages rendered by Cloudflare Functions (e.g. /shop/<product>) never pass through Netlify's edge function,
  // so add the Clickio tags here. Pages forwarded from Netlify already have them and are left unchanged.
  if ((res.headers.get('Content-Type') || '').includes('text/html')) {
    const html = await res.text();
    const headers = new Headers(res.headers);
    headers.delete('Content-Length');
    res = new Response(injectClickio(html), { status: res.status, statusText: res.statusText, headers });
  }
  if (!CACHEABLE.has(res.status) || res.headers.has('Set-Cookie') || /no-store|private/.test(res.headers.get('Cache-Control') || '')) {
    return res;
  }
  const out = new Response(res.body, res);
  out.headers.set('Cache-Control', `public, max-age=300, s-maxage=${TTL}`);
  context.waitUntil(cache.put(key, out.clone()));
  return out;
}
