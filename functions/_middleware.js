// Cloudflare Pages middleware: edge-caches the HTML that Functions produce, so repeat visits to
// /shop/<product>, /tickets/<event> and the forwarded sections are answered from Cloudflare's cache
// instead of re-reading large data shards or fetching from Netlify again. This keeps CPU time and
// outbound requests (what Cloudflare's paid plan bills on) low. Netlify API calls (/.netlify/*),
// non-GET requests and personalised responses (cookies) are never cached.

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

  const res = await context.next();
  if (!CACHEABLE.has(res.status) || res.headers.has('Set-Cookie') || /no-store|private/.test(res.headers.get('Cache-Control') || '')) {
    return res;
  }
  const out = new Response(res.body, res);
  out.headers.set('Cache-Control', `public, max-age=300, s-maxage=${TTL}`);
  context.waitUntil(cache.put(key, out.clone()));
  return out;
}
