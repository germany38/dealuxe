// Runs automatically after every successful deploy. On production deploys it submits the
// URLs from the sitemaps updated most recently to IndexNow (Bing, Yandex, Seznam, Naver…),
// so new products, videos and pages get crawled without running scripts/indexnow.mjs by hand.
const HOST = 'dealuxapp.com';
const KEY = '6a129e95992581a16de8aa65fc87d8fb'; // public key file served at /<key>.txt
const BATCH = 10000; // IndexNow maximum per request
const MAX_URLS = 30000; // stay well inside the function time limit

export default async (req) => {
  const { payload } = await req.json().catch(() => ({}));
  if (payload?.context && payload.context !== 'production') return new Response('skipped');

  const site = `https://${HOST}`;
  const index = await fetch(`${site}/sitemap-index.xml`).then((r) => r.text());
  const sitemaps = [...index.matchAll(/<loc>([^<]+)<\/loc><lastmod>([^<]+)<\/lastmod>/g)]
    .map((m, i) => ({ url: m[1], lastmod: m[2], i }))
    .sort((a, b) => b.lastmod.localeCompare(a.lastmod) || b.i - a.i);
  const newest = sitemaps[0]?.lastmod;

  const urls = new Set();
  for (const sm of sitemaps.filter((s) => s.lastmod === newest)) {
    if (urls.size >= MAX_URLS) break;
    const xml = await fetch(sm.url).then((r) => r.text());
    for (const m of xml.matchAll(/<url>\s*<loc>([^<]+)<\/loc>/g)) urls.add(m[1].replace(/&amp;/g, '&'));
  }
  const list = [...urls].slice(0, MAX_URLS);

  for (let i = 0; i < list.length; i += BATCH) {
    const res = await fetch('https://api.indexnow.org/indexnow', {
      method: 'POST',
      headers: { 'content-type': 'application/json; charset=utf-8' },
      body: JSON.stringify({ host: HOST, key: KEY, keyLocation: `${site}/${KEY}.txt`, urlList: list.slice(i, i + BATCH) }),
    });
    console.log(`IndexNow batch ${i / BATCH + 1}: HTTP ${res.status}`);
    if (res.status === 429) break;
  }
  return new Response(`submitted ${list.length} URLs`);
};
