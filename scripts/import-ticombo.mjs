// Imports a Ticombo affiliate CSV feed into the static ticket data and sitemap.
// Usage: node scripts/import-ticombo.mjs path/to/ticombo.csv
// Re-running replaces previously imported Ticombo events. Events in 2026 are skipped.
import fs from 'node:fs';

const dir = new URL('../data/tickets/', import.meta.url);
const MIN_DATE = 20270101;
const SRC = 'ticombo';
const CATS = { music: 'concerts', sports: 'sports', theatre: 'theatre' };
const slugify = (s) => s.toLowerCase().normalize('NFKD').replace(/[̀-ͯ]/g, '').replace(/&/g, 'and').replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
const djb = (s) => { let h = 5381; for (let i = 0; i < s.length; i++) h = ((h * 33) ^ s.charCodeAt(i)) >>> 0; return h; };

function parseCsv(text) {
  const rows = []; let row = [], field = '', q = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (q) {
      if (c === '"') { if (text[i + 1] === '"') { field += '"'; i++; } else q = false; } else field += c;
    } else if (c === '"') q = true;
    else if (c === ',') { row.push(field); field = ''; }
    else if (c === '\n' || c === '\r') {
      if (c === '\r' && text[i + 1] === '\n') i++;
      row.push(field); field = ''; if (row.length > 1 || row[0]) rows.push(row); row = [];
    } else field += c;
  }
  if (field || row.length) { row.push(field); rows.push(row); }
  const [head, ...body] = rows;
  return body.map((r) => Object.fromEntries(head.map((h, i) => [h, r[i] ?? ''])));
}

const file = process.argv[2];
if (!file) { console.error('Usage: node scripts/import-ticombo.mjs feed.csv'); process.exit(1); }

// Group per-date feed rows into one event per name + venue.
const events = new Map();
let skipped = 0;
for (const r of parseCsv(fs.readFileSync(file, 'utf8'))) {
  const m = r.event_start_date.match(/^(\d{4})-(\d{2})-(\d{2})T(\d{2}:\d{2})/);
  if (!m || !r.deep_link) { skipped++; continue; }
  const date = +(m[1] + m[2] + m[3]);
  if (date < MIN_DATE) { skipped++; continue; }
  const name = (r.event_name || r.event_full_name).trim();
  const key = `${slugify(name)}|${slugify(r.venue_name)}`;
  let e = events.get(key);
  if (!e) {
    e = { n: name, v: r.venue_name, c: r.venue_city, s: r.venue_country, k: CATS[r.category] || 'other', i: r.image_url, $: r.currency || 'EUR', src: SRC, d: [] };
    events.set(key, e);
  }
  const time = m[4].startsWith('23:59') ? '' : m[4];
  const price = Math.round(parseFloat(r.min_final_sell_price || r.min_sell_price) * 100) || 0;
  // Date row: [YYYYMMDD, time, priceFromCents, TicketNetwork, TicketLiquidator, StubHub, Ticombo]
  e.d.push([date, time, price, '', '', '', r.deep_link]);
}

// Load shards and drop any earlier Ticombo import.
const shards = [];
const taken = new Set();
for (let i = 0; i < 512; i++) {
  const shard = JSON.parse(fs.readFileSync(new URL(`${i}.json`, dir), 'utf8'));
  for (const [id, e] of Object.entries(shard)) { if (e.src === SRC) delete shard[id]; else taken.add(id); }
  shards.push(shard);
}

const rows = [];
for (const [key, e] of events) {
  e.d.sort((a, b) => a[0] - b[0] || a[1].localeCompare(b[1]));
  let id = 'tc' + djb(key).toString(36);
  for (let n = 1; taken.has(id); n++) id = 'tc' + djb(key + n).toString(36);
  taken.add(id);
  shards[djb(id) % 512][id] = e;
  const prices = e.d.map((x) => x[2]).filter(Boolean);
  rows.push([id, e.n, e.v, e.c, e.s, e.k, e.d[0][0], e.d[e.d.length - 1][0], prices.length ? Math.min(...prices) : 0, e.d.length, e.$]);
}
shards.forEach((s, i) => fs.writeFileSync(new URL(`${i}.json`, dir), JSON.stringify(s)));

// Index rows: [id, name, venue, city, state, category, firstDate, lastDate, minPriceCents, dateCount, currency?]
const indexFile = new URL('index.json', dir);
const index = JSON.parse(fs.readFileSync(indexFile, 'utf8'))
  .filter((r) => !r[10])
  .concat(rows)
  .sort((a, b) => a[6] - b[6] || a[1].localeCompare(b[1]));
fs.writeFileSync(indexFile, JSON.stringify(index));

const stamp = new Date().toISOString().slice(0, 10);
fs.writeFileSync(new URL('../sitemap-tickets-1.xml', import.meta.url),
  `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n` +
  `  <url><loc>https://dealuxapp.com/tickets/</loc><lastmod>${stamp}</lastmod></url>\n` +
  `  <url><loc>https://dealuxapp.com/entradas/</loc><lastmod>${stamp}</lastmod></url>\n` +
  index.map((r) => `  <url><loc>https://dealuxapp.com/tickets/${slugify(r[1]) || 'event'}-${r[0]}</loc></url>`).join('\n') +
  '\n</urlset>\n');

console.log(`${rows.length} Ticombo events imported (${skipped} rows skipped); ${index.length} events total`);
