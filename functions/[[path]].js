// Cloudflare Pages Function: forwards the sections Cloudflare doesn't host itself to the Netlify site.
// Cloudflare's free plan caps a deploy at 20,000 files, so the lowest-traffic sections (see PROXIED in
// scripts/build-cloudflare-pages.mjs) plus Netlify API calls (/.netlify/*) are fetched from Netlify.
// Only paths listed in .cloudflare-pages/_routes.json reach this function; everything else is a free static file.
// More specific routes (functions/shop/[slug].js, functions/tickets/[slug].js) take priority.

const ORIGIN = 'https://dealux.netlify.app';
const ORIGIN_HOST = new URL(ORIGIN).host;

export async function onRequest({ request }) {
  const url = new URL(request.url);
  const target = new URL(url.pathname + url.search, ORIGIN);

  const headers = new Headers(request.headers);
  headers.set('X-Forwarded-Host', url.host);
  headers.set('X-Forwarded-Proto', url.protocol.replace(':', ''));

  const hasBody = !['GET', 'HEAD'].includes(request.method);
  const upstream = await fetch(target, {
    method: request.method,
    headers,
    body: hasBody ? request.body : undefined,
    redirect: 'manual',
  });

  const out = new Headers(upstream.headers);
  const location = out.get('Location');
  if (location) {
    const loc = new URL(location, ORIGIN);
    if (loc.host === ORIGIN_HOST) {
      loc.protocol = url.protocol;
      loc.host = url.host;
      out.set('Location', loc.toString());
    }
  }

  return new Response(upstream.body, { status: upstream.status, statusText: upstream.statusText, headers: out });
}
