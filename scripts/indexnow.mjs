// Submits every URL in the local sitemaps to IndexNow (Bing, Yandex, Seznam, Naver…),
// so new and re-rendered pages get crawled in days instead of weeks.
// Run after a deploy is live:   node scripts/indexnow.mjs
// Only some sitemaps:           node scripts/indexnow.mjs sitemap-tickets-1.xml sitemap-shop-products-1.xml
// Preview without sending:      node scripts/indexnow.mjs --dry-run
import fs from 'node:fs';

const HOST = 'dealuxapp.com';
const KEY = '6a129e95992581a16de8aa65fc87d8fb'; // served at /<key>.txt
const BATCH = 10000; // IndexNow maximum per request

const root = new URL('../', import.meta.url);
const args = process.argv.slice(2);
const dryRun = args.includes('--dry-run');
const index = fs.readFileSync(new URL('sitemap-index.xml', root), 'utf8');
const files = args.filter((a) => !a.startsWith('--'));
const sitemaps = files.length ? files : [...index.matchAll(/<loc>https:\/\/dealuxapp\.com\/([^<]+)<\/loc>/g)].map((m) => m[1]);

const urls = new Set();
for (const file of sitemaps) {
  const xml = fs.readFileSync(new URL(file, root), 'utf8');
  for (const m of xml.matchAll(/<loc>([^<]+)<\/loc>/g)) urls.add(m[1].replace(/&amp;/g, '&'));
}
const list = [...urls];
console.log(`${list.length} URLs from ${sitemaps.length} sitemaps`);

for (let i = 0; i < list.length; i += BATCH) {
  const urlList = list.slice(i, i + BATCH);
  if (dryRun) {
    console.log(`batch ${i / BATCH + 1}: ${urlList.length} URLs (dry run)`);
    continue;
  }
  const res = await fetch('https://api.indexnow.org/indexnow', {
    method: 'POST',
    headers: { 'content-type': 'application/json; charset=utf-8' },
    body: JSON.stringify({ host: HOST, key: KEY, keyLocation: `https://${HOST}/${KEY}.txt`, urlList }),
  });
  console.log(`batch ${i / BATCH + 1}: ${urlList.length} URLs -> HTTP ${res.status}`);
  if (res.status === 429) {
    console.log('Rate limited; re-run later with the remaining sitemaps.');
    break;
  }
  await new Promise((r) => setTimeout(r, 2000));
}
