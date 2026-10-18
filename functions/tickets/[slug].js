// Cloudflare Pages Function: server-renders /tickets/<event-slug>-<id> so each event is a
// unique, indexable page (title, venue, dates, prices, Event structured data). Events with no
// upcoming dates answer 410 so search engines drop them instead of keeping soft-404s.
// Data comes from the same static shards the browser uses (/data/tickets/<n>.json).

const SHARDS = 512;
const MAX_LD_EVENTS = 10;
const CATS = { concerts: 'Concerts', sports: 'Sports', theatre: 'Theatre', other: 'Other' };
let template = null;

const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
const slugify = (s) => s.toLowerCase().normalize('NFKD').replace(/[\u0300-\u036f]/g, () => '').replace(/&/g, () => 'and').replace(/[^a-z0-9]+/g, () => '-').replace(/^-|-$/g, () => '');
const jsonLd = (o) => `<script type="application/ld+json">${JSON.stringify(o).replace(/</g, () => '\\u003c')}</script>`;
const usd = (c) => (c ? '$' + (c / 100).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '');
const isoDate = (n) => `${Math.floor(n / 10000)}-${String(Math.floor(n / 100) % 100).padStart(2, '0')}-${String(n % 100).padStart(2, '0')}`;
const fmt = (n) =>
  new Date(Date.UTC(Math.floor(n / 10000), (Math.floor(n / 100) % 100) - 1, n % 100)).toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric', timeZone: 'UTC' });

function shardOf(id) {
  let h = 5381;
  for (let i = 0; i < id.length; i++) h = ((h * 33) ^ id.charCodeAt(i)) >>> 0;
  return h % SHARDS;
}

async function asset(env, request, path) {
  const res = await env.ASSETS.fetch(new URL(path, request.url));
  return res.ok ? res.text() : null;
}

function render(html, { title, desc, canonical, robots, head = '', name, place, body }) {
  return html
    .replace(/<title>.*?<\/title>/, () => `<title>${esc(title)}</title>`)
    .replace(/<meta name="description" content="[^"]*">/, () => `<meta name="description" content="${esc(desc)}">`)
    .replace(/<link rel="canonical" href="[^"]*">/, () => `<link rel="canonical" href="${esc(canonical)}">\n<meta name="robots" content="${robots}">${head}`)
    .replace('<h1 id="ev-name">Loading…</h1>', () => `<h1 id="ev-name">${esc(name)}</h1>`)
    .replace('<p class="muted" id="ev-place"></p>', () => `<p class="muted" id="ev-place">${esc(place)}</p>`)
    .replace('<div id="ev-dates"></div>', () => `<div id="ev-dates">${body}</div>`);
}

export async function onRequestGet(context) {
  const { request, env, params } = context;
  const url = new URL(request.url);
  const raw = String(params.slug || '');
  if (raw === 'show') return context.next();
  const id = (raw.match(/(?:^|-)([a-z0-9]+)$/) || [])[1];
  if (!id) return context.next();

  const [shard] = await Promise.all([
    asset(env, request, `/data/tickets/${shardOf(id)}.json`),
    template ? null : asset(env, request, '/tickets/show/').then((t) => (template = t)),
  ]);
  if (!template) return context.next();

  const now = new Date();
  const today = now.getUTCFullYear() * 10000 + (now.getUTCMonth() + 1) * 100 + now.getUTCDate();
  let e = null;
  try {
    e = shard ? JSON.parse(shard)[id] : null;
  } catch {}
  const dates = e ? e.d.filter((d) => d[0] >= today) : [];

  if (!dates.length) {
    const html = render(template, {
      title: `${e ? e.n : 'Event'} — Tickets no longer available | Dealux Tickets`,
      desc: 'Tickets for this event are no longer available. Browse upcoming concerts, sports and theatre events on Dealux.',
      canonical: 'https://dealuxapp.com/tickets/',
      robots: 'noindex, follow',
      name: 'This event has ended',
      place: e ? e.n : '',
      body: '<p>Tickets for this event are no longer available.</p><p><a class="btn btn-gold" href="/tickets/">Browse upcoming events →</a></p>',
    });
    return new Response(html, { status: e ? 410 : 404, headers: { 'content-type': 'text/html; charset=utf-8', 'x-robots-tag': 'noindex' } });
  }

  const slug = `${slugify(e.n) || 'event'}-${id}`;
  if (raw !== slug || url.pathname.endsWith('/')) return Response.redirect(`${url.origin}/tickets/${slug}`, 301);

  const canonical = `https://dealuxapp.com/tickets/${slug}`;
  const city = [e.c, e.s].filter(Boolean).join(', ');
  const place = [e.v, city, CATS[e.k] || e.k].filter(Boolean).join(' · ');
  const prices = dates.map((d) => d[2]).filter(Boolean);
  const from = prices.length ? usd(Math.min(...prices)) : '';
  const range = dates.length > 1 ? `${fmt(dates[0][0])} – ${fmt(dates[dates.length - 1][0])}` : fmt(dates[0][0]);
  const desc =
    `${e.n} tickets${e.v ? ` at ${e.v}` : ''}${city ? `, ${city}` : ''}: ${dates.length} upcoming date${dates.length > 1 ? 's' : ''} (${range})` +
    `${from ? `, from ${from}` : ''}. Compare TicketNetwork, TicketLiquidator and StubHub prices on Dealux.`;

  const location = {
    '@type': 'Place',
    name: e.v || city || e.n,
    address: { '@type': 'PostalAddress', ...(e.c ? { addressLocality: e.c } : {}), ...(e.s ? { addressRegion: e.s } : {}) },
  };
  const events = dates.slice(0, MAX_LD_EVENTS).map((d) => {
    const offerUrl = d[3] || d[4] || d[5] || canonical;
    return {
      '@context': 'https://schema.org',
      '@type': 'Event',
      name: e.n,
      startDate: isoDate(d[0]) + (d[1] ? `T${d[1].slice(0, 5)}` : ''),
      eventStatus: 'https://schema.org/EventScheduled',
      eventAttendanceMode: 'https://schema.org/OfflineEventAttendanceMode',
      location,
      url: canonical,
      ...(e.i ? { image: e.i } : {}),
      offers: { '@type': 'Offer', url: offerUrl, availability: 'https://schema.org/InStock', priceCurrency: 'USD', ...(d[2] ? { price: (d[2] / 100).toFixed(2) } : {}) },
    };
  });
  const head =
    `\n<meta property="og:type" content="website"><meta property="og:title" content="${esc(e.n)} Tickets"><meta property="og:description" content="${esc(desc)}"><meta property="og:url" content="${esc(canonical)}">` +
    (e.i ? `<meta property="og:image" content="${esc(e.i)}">` : '') +
    `\n${jsonLd(events.length === 1 ? events[0] : events)}`;

  const btn = (u, l) => (u ? `<a class="btn btn-gold" style="margin:4px 8px 4px 0" href="${esc(u)}" target="_blank" rel="nofollow sponsored noopener">${l} →</a>` : '');
  const body =
    (e.i ? `<p><img src="${esc(e.i)}" alt="${esc(`${e.n} seating map`)}" referrerpolicy="no-referrer" loading="lazy" style="max-width:100%;max-height:320px;border-radius:12px"></p>` : '') +
    `<h2>${dates.length} upcoming date${dates.length > 1 ? 's' : ''}</h2>` +
    dates
      .map(
        (d) =>
          `<div class="card" style="padding:14px;margin:0 0 10px"><b>${fmt(d[0])}${d[1] ? ` · ${esc(d[1].slice(0, 5))}` : ''}</b>${d[2] ? ` <span class="muted">· from ${usd(d[2])}</span>` : ''}` +
          `<div style="margin-top:8px">${btn(d[3], 'TicketNetwork')}${btn(d[4], 'TicketLiquidator')}${btn(d[5], 'StubHub')}</div></div>`,
      )
      .join('');

  const html = render(template, {
    title: `${e.n} Tickets${e.v ? ` — ${e.v}` : ''}${e.c ? `, ${e.c}` : ''} | Dealux Tickets`,
    desc,
    canonical,
    robots: 'index, follow, max-image-preview:large',
    head,
    name: e.n,
    place,
    body,
  });
  return new Response(html, { headers: { 'content-type': 'text/html; charset=utf-8', 'cache-control': 'public, max-age=3600' } });
}
