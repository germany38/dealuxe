// Removes concluded event dates from the static ticket data and sitemap.
// The tickets pages already hide past dates in the browser; run this
// occasionally (`node scripts/prune-tickets.mjs`) to shrink the data files.
import fs from 'node:fs';

const dir = new URL('../data/tickets/', import.meta.url);
const now = new Date();
const today = now.getFullYear() * 10000 + (now.getMonth() + 1) * 100 + now.getDate();
const slugify = (s) => s.toLowerCase().normalize('NFKD').replace(/[̀-ͯ]/g, '').replace(/&/g, 'and').replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');

// Shards: id -> { n, v, c, s, k, i, d: [[YYYYMMDD, time, priceCents, ticketNetwork, ticketLiquidator, stubHub]] }
const live = new Map();
for (let i = 0; i < 512; i++) {
  const file = new URL(`${i}.json`, dir);
  const shard = JSON.parse(fs.readFileSync(file, 'utf8'));
  for (const [id, e] of Object.entries(shard)) {
    e.d = e.d.filter((d) => d[0] >= today);
    if (e.d.length) live.set(id, e);
    else delete shard[id];
  }
  fs.writeFileSync(file, JSON.stringify(shard));
}

// Index rows: [id, name, venue, city, state, category, firstDate, lastDate, minPriceCents, dateCount]
const indexFile = new URL('index.json', dir);
const index = JSON.parse(fs.readFileSync(indexFile, 'utf8'))
  .filter((r) => live.has(r[0]))
  .map((r) => {
    const d = live.get(r[0]).d;
    const prices = d.map((x) => x[2]).filter(Boolean);
    return [r[0], r[1], r[2], r[3], r[4], r[5], d[0][0], d[d.length - 1][0], prices.length ? Math.min(...prices) : 0, d.length];
  })
  .sort((a, b) => a[6] - b[6] || a[1].localeCompare(b[1]));
fs.writeFileSync(indexFile, JSON.stringify(index));

const stamp = now.toISOString().slice(0, 10);
fs.writeFileSync(new URL('../sitemap-tickets-1.xml', import.meta.url),
  `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n` +
  `  <url><loc>https://dealuxapp.com/tickets/</loc><lastmod>${stamp}</lastmod></url>\n` +
  `  <url><loc>https://dealuxapp.com/entradas/</loc><lastmod>${stamp}</lastmod></url>\n` +
  index.map((r) => `  <url><loc>https://dealuxapp.com/tickets/${slugify(r[1]) || 'event'}-${r[0]}</loc></url>`).join('\n') +
  '\n</urlset>\n');

console.log(`${index.length} events with upcoming dates kept`);
