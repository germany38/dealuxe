// Hide any image that fails to load (e.g. a banner an advertiser removed) instead of showing a broken icon.
(function () {
  function hide(img) { if (img && img.tagName === 'IMG') img.style.display = 'none'; }
  document.addEventListener('error', function (e) { hide(e.target); }, true);
  Array.prototype.forEach.call(document.images, function (img) { if (img.complete && img.naturalWidth === 0 && img.src) hide(img); });
})();
// TravelPayouts (emrldco.com, t=602381). Loaded once on every page from this shared script.
(function () {
  if (document.querySelector('script[src*="emrldco.com/NjAyMzgx.js"]')) return;
  var script = document.createElement("script");
  script.async = 1;
  script.setAttribute("data-cmp-ab", "2");
  script.src = 'https://emrldco.com/NjAyMzgx.js?t=602381';
  document.head.appendChild(script);
})();
// Google AdSense (publisher ca-pub-5723887718258446, "Dealux Ad" responsive unit, slot 2061084255).
// Loads the AdSense library once and places one responsive unit at the end of the page's main
// content (just above the footer). Served from this shared script so it runs on every page,
// whether the site is answered by Netlify or by the Cloudflare Pages copy.
(function () {
  if (window.__dxAdsense) return;
  window.__dxAdsense = true;
  var CLIENT = 'ca-pub-5723887718258446';
  if (!document.querySelector('script[src*="pagead2.googlesyndication.com/pagead/js/adsbygoogle.js"]')) {
    var s = document.createElement('script');
    s.async = true;
    s.src = 'https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=' + CLIENT;
    s.crossOrigin = 'anonymous';
    document.head.appendChild(s);
  }
  function place() {
    if (document.querySelector('ins.adsbygoogle[data-ad-slot="2061084255"]')) return;
    var wrap = document.createElement('div');
    wrap.className = 'dx-adsense';
    wrap.style.cssText = 'margin:24px auto;max-width:1200px;padding:0 16px;clear:both';
    var ins = document.createElement('ins');
    ins.className = 'adsbygoogle';
    ins.style.display = 'block';
    ins.setAttribute('data-ad-client', CLIENT);
    ins.setAttribute('data-ad-slot', '2061084255');
    ins.setAttribute('data-ad-format', 'auto');
    ins.setAttribute('data-full-width-responsive', 'true');
    wrap.appendChild(ins);
    var main = document.querySelector('main');
    var footer = document.querySelector('footer');
    if (main) main.appendChild(wrap);
    else if (footer && footer.parentNode) footer.parentNode.insertBefore(wrap, footer);
    else document.body.appendChild(wrap);
    try { (window.adsbygoogle = window.adsbygoogle || []).push({}); } catch (e) {}
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', place);
  else place();
})();
// Ad networks, staggered: each page view loads exactly ONE network, rotating in turn so a
// visitor never sees Monetag, Adsterra and HilltopAds stacked on the same page.
//   0 Monetag   – Vignette zone 12187754
//   1 Adsterra  – popunder
//   2 HilltopAds – unfoldedtrade.com ad tag
// The in-page image units (Monetag In-Page Push, Adsterra native banner) were removed because
// they served dating creatives; don't re-add them.
// The turn is kept per visitor in localStorage (random start if storage is unavailable).
// Add ?dxads=monetag|adsterra|hilltop to a URL to preview a specific network.
(function () {
  if (window.__dxAds) return;
  window.__dxAds = true;
  var NETWORKS = ['monetag', 'adsterra', 'hilltop'];
  var pick = -1;
  var forced = (location.search.match(/[?&]dxads=(\w+)/) || [])[1];
  if (forced) pick = NETWORKS.indexOf(forced);
  if (pick < 0) {
    try {
      var n = parseInt(localStorage.getItem('dx_ad_turn'), 10);
      if (isNaN(n)) n = Math.floor(Math.random() * NETWORKS.length);
      pick = n % NETWORKS.length;
      localStorage.setItem('dx_ad_turn', String((pick + 1) % NETWORKS.length));
    } catch (e) {
      pick = Math.floor(Math.random() * NETWORKS.length);
    }
  }
  window.__dxAdNetwork = NETWORKS[pick];
  function load(src, attrs) {
    var s = document.createElement('script');
    s.src = src;
    s.async = true;
    for (var k in attrs) s.setAttribute(k, attrs[k]);
    [document.documentElement, document.body].filter(Boolean).pop().appendChild(s);
    return s;
  }
  function monetag() {
    load('https://n6wxm.com/vignette.min.js', { 'data-zone': '12187754' });
  }
  function adsterra() {
    load('https://bauval.org/14/5e5de126617e996b572d87f0b61836a4', { 'data-cfasync': 'false' });
  }
  function hilltop() {
    // HilltopAds tag, as supplied by HilltopAds.
    (function(qcrbg){
    var d = document,
        s = d.createElement('script'),
        l = d.currentScript || d.scripts[d.scripts.length - 1];
    s.settings = qcrbg || {};
    s.src = "\/\/unfoldedtrade.com\/bJXXV.sJdCGvl\/0tYIWBcm\/Ie\/mn9mu\/ZBUplQkSP\/TkcJ1\/O\/THYf3pNsDOEWtLNQz\/U\/5rN\/j\/cH0iNqQ_";
    s.async = true;
    s.referrerPolicy = 'no-referrer-when-downgrade';
    if (l && l.parentNode) l.parentNode.insertBefore(s, l); else document.head.appendChild(s);
    })({});
  }
  [monetag, adsterra, hilltop][pick]();
})();

// Google Analytics (gtag.js). Loaded from the shared script so every page is measured.
(function(){var id='G-FDZM02YJ3Q',s=document.createElement('script');s.async=1;s.src='https://www.googletagmanager.com/gtag/js?id='+id;document.head.appendChild(s);window.dataLayer=window.dataLayer||[];window.gtag=function(){dataLayer.push(arguments)};gtag('js',new Date());gtag('config',id);})();

// Pinterest Tag (base code). Loaded from the shared script so every page can be
// used for conversion tracking and retargeting audiences.
!function(e){if(!window.pintrk){window.pintrk=function(){window.pintrk.queue.push(Array.prototype.slice.call(arguments))};var n=window.pintrk;n.queue=[],n.version="3.0";var t=document.createElement("script");t.async=!0,t.src=e;var r=document.getElementsByTagName("script")[0];r.parentNode.insertBefore(t,r)}}("https://s.pinimg.com/ct/core.js");
pintrk('load', '2613676142219');
pintrk('page');

// Impact affiliate tracking tag. Loaded from the shared script so it runs on
// every page that carries affiliate links.
(function(i,m,p,a,c,t){c.ire_o=p;c[p]=c[p]||function(){(c[p].a=c[p].a||[]).push(arguments)};t=a.createElement(m);var z=a.getElementsByTagName(m)[0];t.async=1;t.src=i;z.parentNode.insertBefore(t,z)})('https://utt.impactcdn.com/P-A5661882-9e84-4a48-8d7e-ab9d5989e7151.js','script','impactStat',document,window);impactStat('trackImpression');

// Dealux client-side features. Everything runs in the browser: there is no
// server, account or database.
(function () {
  'use strict';
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };
  var esc = function (s) { return String(s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); };
  var titleCase = function (s) { return s.replace(/-+/g, ' ').replace(/\b\w/g, function (c) { return c.toUpperCase(); }); };
  var slugify = function (s) { return s.toLowerCase().normalize('NFKD').replace(/[̀-ͯ]/g, '').replace(/&/g, 'and').replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, ''); };
  var params = new URLSearchParams(location.search);
  var page = document.body.getAttribute('data-page');

  // ---- Pinterest conversion events ----
  var pinId = function () { return 'dx-' + Date.now().toString(36) + '-' + Math.random().toString(36).slice(2, 8); };
  var pinTrack = function (name, data) { data.event_id = pinId(); window.pintrk('track', name, data); };
  pinTrack('pagevisit', { property: 'Dealux' });
  // Brand, type and department listings count as category views.
  var catMatch = location.pathname.match(/^\/shop\/(brand|type|department)\/[^\/]+/);
  if (catMatch) {
    var catTitle = $('h1');
    pinTrack('viewcategory', { line_items: [{ product_category: catTitle ? catTitle.textContent.trim() : document.title }] });
  }
  // Searches: report the query once the visitor stops typing or submits.
  $$('[data-search-form], [data-brand-filter]').forEach(function (f) {
    var last = '';
    var report = function () {
      var q = f.q && f.q.value.trim();
      if (q && q !== last) { last = q; pinTrack('search', { search_query: q }); }
    };
    if (f.q && f.q.value.trim()) report();
    f.addEventListener('submit', report);
    f.addEventListener('input', function () { clearTimeout(report.t); report.t = setTimeout(report, 1500); });
  });
  // Checkout: clicks on store "Buy" links (product pages) and Stripe buy buttons (exclusive items).
  document.addEventListener('click', function (e) {
    var a = e.target.closest && e.target.closest('[data-product-link], a[href^="https://buy.stripe.com/"]');
    if (!a) return;
    var priceText = (a.textContent.match(/\$\s*([\d,.]+)/) || [])[1];
    var data = { order_quantity: 1, currency: a.getAttribute('data-currency') || 'USD' };
    var value = Number(a.getAttribute('data-value') || (priceText || '').replace(/,/g, ''));
    if (value) data.value = value;
    pinTrack('checkout', data);
  });

  // ---- Partner logos: compact strip under the header on every page, plus
  // a larger block on the homepage. Each logo sits in its own tile so
  // neighbouring links can't be mis-clicked. ----
  var PARTNERS = [
    [['ItaliaRail', 'https://ujhjj.com/c/ca326rdm5vc0d22003ddef1cea9751/', 'italiarail.svg'],
     ['Vagamo', 'https://rthsu.com/c/0lyhuakd0ec0d22003dd6ac117ee14/', 'vagamo.svg'],
     ['Answear Ukraine', 'https://hxbok.com/c/h29o15jdr6c0d22003dda76d99edd2/', 'answear.svg'],
     ['Touch Ukraine', 'https://wbbsv.com/c/ynys1f2mjpc0d22003dd0e81904d8b/', 'touch.svg'],
     ['Intertop Ukraine', 'https://dkfrh.com/c/aaj1enr23tc0d22003ddb9f189b651/', 'intertop.svg'],
     ['Repjegy Hungary', 'https://zallj.com/c/o5xydq5rnpc0d22003dd3fe229b7dc/', 'repjegy.svg']],
    [['Whirlpool Mexico', 'https://rzekl.com/c/hkjqq2fi8qc0d22003dd82ed2bb6aa/', 'whirlpool.svg'],
     ['Budinok Igrashok', 'https://gndrz.com/c/1xuxd52d9oc0d22003dd2165fe5e9d/', 'budinok-igrashok.svg'],
     ['Redmagic', 'https://yyczo.com/c/qmttmvxh1uc0d22003dd56637026d8/', 'redmagic.svg'],
     ['Eurowings', 'https://codeaven.com/c/zrwntqeht4c0d22003dd3cffcf918a/', 'eurowings.svg'],
     ['Alibaba', 'https://rzekl.com/c/pm1aev55clc0d22003dd219aa26f6f/', 'alibaba.png'],
     ['Square', 'https://rcpsj.com/c/xmbwxznk57c0d22003ddc1c4731730/', 'square.svg']],
    [['Notta AI', 'https://ypetp.com/c/7gbdp8tyguc0d22003ddf50bb56640/', 'notta.svg'],
     ['Kicks Crew', 'https://dkfrh.com/c/mecn64hou7c0d22003dd1910db6aa6/', 'kickscrew.svg'],
     ['Geekbuying', 'https://bywiola.com/c/78tuvzaw8kc0d22003dd0267b86f6e/', 'geekbuying.svg'],
     ['Shopee Mexico', 'https://zallj.com/c/qy94wfbelwc0d22003dd6e79f7c2cd/', 'shopee.svg'],
     ['Italo Jewelry', 'https://ad.admitad.com/c/l926tcw2smc0d22003dd87e51e1a66/', 'italo-jewelry.png'],
     ['iCases Ukraine', 'https://ypetp.com/c/wqd2fqy91hc0d22003dd58f5722f30/', 'icases.svg']],
    [['Sunsky', 'https://dorinebeaumont.com/c/7npkd4cs1ic0d22003dd869a299fda/', 'sunsky.png'],
     ['DocHub', 'https://lsuix.com/c/fsbaa03yh2c0d22003dd6dd72211ce/', 'dochub.svg'],
     ['PriceTravel MX', 'https://ogsib.com/c/z4cgp2zr4dc0d22003dd309f617b02/', 'pricetravel.svg'],
     ['Samsonite MX', 'https://xmknb.com/c/cj6zaw6m9pc0d22003dda68f2598b9/', 'samsonite.svg'],
     ['TravelKing PL', 'https://vxrlm.com/c/dquwu4q32hc0d22003dd7eaf385c59/', 'travelking.svg'],
     ['ChicMe', 'https://rzekl.com/c/gf807z8tarc0d22003dd312b8f391a/', 'chicme.png']],
    [['TTGO E-bike', 'https://dkfrh.com/c/nz4081dh12c0d22003ddd0a9902774/', 'ttgo.svg'],
     ['HyperHost', 'https://rcpsj.com/c/4y24lnxl7fc0d22003dd7f67b8171e/', 'hyperhost.svg'],
     ['Govee', 'https://rthsu.com/c/yzzx0gmxy0c0d22003dd3791d3d079/', 'govee.png'],
     ['Hidemyname VPN', 'https://codeaven.com/c/d6ig17yj38c0d22003ddcfba9fca8a/', 'hidemyname.svg'],
     ['DelSol Woolworth MX', 'https://rthsu.com/c/d59il9migtc0d22003dd20bedc2379/', 'delsol-woolworth.svg'],
     ['Nubia', 'https://ziejy.com/c/lh3bbik9lyc0d22003dde62ca5e32f/', 'nubia.svg']],
    [['NordPass', 'https://rkdro.com/c/mx19yq7dtcc0d22003dd410fff306a/', 'nordpass.svg'],
     ['Vegas.com', 'https://naiawork.com/c/7z8rbci6j9c0d22003dd2a35947101/', 'vegas.svg'],
     ['Homestyler', 'https://cafxq.com/c/swlngq9rrzc0d22003dd28a65238d7/', 'homestyler.svg'],
     ['TurboVPN', 'https://grfpr.com/c/exe221unkpc0d22003ddddf84d4c0b/', 'turbovpn.png'],
     ['StyleWe', 'https://codeaven.com/c/r9ybpohdxoc0d22003dd806f4427c0/', 'stylewe.svg'],
     ['ExpressVPN', 'https://ziejy.com/c/4raik6r0sqc0d22003dd954d043f6e/', 'expressvpn.svg']],
    [['JustFashionNow', 'https://rzekl.com/c/kmcoj56juvc0d22003dd608cdf386b/', 'justfashionnow.png'],
     ['Ticombo', 'https://zmgig.com/c/hn23xca4o8c0d22003ddbcf92d8d7a/', 'ticombo.svg'],
     ['NAGA', 'https://cafxq.com/c/xeokmvvyj1c0d22003dd95dffe8bc5/', 'naga.svg'],
     ['Noracora', 'https://qwpeg.com/c/of8pqgktr2c0d22003ddc8dbeb8f0d/', 'noracora.png'],
     ['Gshopper', 'https://bywiola.com/c/nx2yncwth6c0d22003ddd497214fca/', 'gshopper.svg']],
    [['ASAP Tickets', 'https://yknhc.com/c/lv8vbf9a4ec0d22003ddf5f67e30af/', 'asaptickets.svg'],
     ['Fiverr', 'https://twnfz.com/c/oqcmadzidpc0d22003ddacbbb3152e/', 'fiverr.svg'],
     ['italki', 'https://xcdus.com/c/cp8w1bohgmc0d22003dd0dfa1a7923/', 'italki.svg'],
     ['Wondershare', 'https://kjuzv.com/c/8u3trxihmwc0d22003ddef655e4ac9/', 'wondershare.svg'],
     ['Cheapvuelos', 'https://yknhc.com/c/cmazc4pm8oc0d22003ddce5f810ebf/', 'cheapvuelos.svg'],
     ['Tiqets', 'https://ad.admitad.com/c/rq0x895xioc0d22003dd0a1126e84f/', 'tiqets.svg']],
    [['Multilogin', 'https://kpwfp.com/c/jcy22p74gec0d22003dd40e692d5b7/', 'multilogin.svg'],
     ['Spartoo', 'https://tsygg.com/c/hhw513jc2uc0d22003dd266cbebcee/', 'spartoo.svg'],
     ['HoraCredit', 'https://rzekl.com/c/hnimhgl6y7c0d22003dd527fa9a677/', 'horacredit.svg'],
     ['PureVPN', 'https://plrvq.com/c/ayvzzawv40c0d22003dddd63dd688c/', 'purevpn.svg'],
     ['Corsair', 'https://ntzgd.com/c/hpl2levo9fc0d22003dd45cfa0a3aa/', 'corsair.svg'],
     ['Thordata', 'https://heqgr.com/c/io8l389mo3c0d22003ddfe5733b304/', 'thordata.svg']],
    [['Qustodio', 'https://zejcl.com/c/zgsaevrb3ac0d22003dd2411861ed1/', 'qustodio.svg'],
     ['Camp David', 'https://xqjeo.com/c/t39rzrme55c0d22003dd5474323be3/', 'camp-david.svg'],
     ['ZenHotels', 'https://qwpeg.com/c/qpi6kwbvr0c0d22003dd2f6f9b0ac2/', 'zenhotels.svg'],
     ['Skylux Travel', 'https://bednari.com/c/xe662ka26wc0d22003dd7fc733cd6a/', 'skylux.svg'],
     ['Vodafone CZ', 'https://flcoz.com/c/7v9ajpmwz2c0d22003dd14b1736132/', 'vodafone.svg'],
     ['PDFFiller', 'https://bednari.com/c/ml1y8ck0k7c0d22003ddab072b2ee3/', 'pdffiller.svg'],
     ['Chicco', 'https://dorinebeaumont.com/c/407f9c2a7ac0d22003dd1fffad291b/', 'chicco.svg']]
  ];
  // Displayed in rows of 12; extras start their own row.
  var ALL_PARTNERS = [].concat.apply([], PARTNERS), PARTNER_ROWS = [];
  for (var pi = 0; pi < ALL_PARTNERS.length; pi += 12) PARTNER_ROWS.push(ALL_PARTNERS.slice(pi, pi + 12));
  function partnerRows() {
    return PARTNER_ROWS.filter(function (row) { return row.length; }).map(function (row) {
      return '<div class="partner-row">' + row.map(function (p) {
        return '<a class="partner-tile" href="' + esc(p[1]) + '" target="_blank" rel="sponsored noopener" title="' + esc(p[0]) + '">' +
          '<img src="/assets/partners/' + p[2] + '" alt="' + esc(p[0]) + '" loading="lazy" decoding="async"></a>';
      }).join('') + '</div>';
    }).join('');
  }
  var siteHeader = $('.site-header');
  var strip = '<nav class="partner-strip" aria-label="Partner deals"><div class="wrap">' + partnerRows() + '</div></nav>';
  if (siteHeader) siteHeader.insertAdjacentHTML('afterend', strip);
  else document.body.insertAdjacentHTML('afterbegin', strip);
  $$('[data-partner-logos]').forEach(function (el) { el.innerHTML = partnerRows(); });

  // ---- Shared incremental result rendering ----
  function paginate(items, render, container, more, count, label, size, initial) {
    var shown = 0, step = initial || size;
    container.innerHTML = '';
    count.textContent = items.length.toLocaleString() + ' ' + label;
    function next() {
      container.insertAdjacentHTML('beforeend', items.slice(shown, shown + step).map(render).join(''));
      shown += step; step = size;
      more.classList.toggle('hidden', shown >= items.length);
      fillImages(container);
    }
    more.onclick = next;
    next();
  }
  // ---- Product photos: static slug -> URL shards built by scripts/build.mjs ----
  var IMG_SHARDS = 64, shards = {};
  function shardOf(slug) { var h = 5381; for (var i = 0; i < slug.length; i++) h = ((h * 33) ^ slug.charCodeAt(i)) >>> 0; return h % IMG_SHARDS; }
  // Product record: [name, price, currency, brand, image, affiliate link]
  function detailsFor(slug) {
    var n = shardOf(slug);
    shards[n] = shards[n] || fetch('/data/img/' + n + '.json').then(function (r) { return r.ok ? r.json() : {}; }).catch(function () { return {}; });
    return shards[n].then(function (map) { return map[slug] || ['', '', '', '', '', '']; });
  }
  function money(price, currency) {
    if (!price) return '';
    try { return Number(price).toLocaleString('en-US', { style: 'currency', currency: currency || 'USD' }); } catch (e) { return price + ' ' + (currency || ''); }
  }
  function fillImages(root) {
    $$('img[data-img-slug]', root).forEach(function (img) {
      var slug = img.getAttribute('data-img-slug');
      img.removeAttribute('data-img-slug');
      var card = img.closest('.product-card');
      detailsFor(slug).then(function (d) {
        if (card) {
          if (d[0]) $('h3', card).textContent = d[0];
          var meta = $('.muted', card);
          if (meta && (d[1] || d[3])) meta.textContent = [money(d[1], d[2]), d[3]].filter(Boolean).join(' · ');
        }
        if (!d[4]) return;
        img.onerror = function () { img.parentNode.classList.remove('has-img'); img.remove(); };
        img.src = d[4];
        img.parentNode.classList.add('has-img');
      });
    });
  }
  var tokens = function (q) { return slugify(q || '').split('-').filter(Boolean); };

  // ---- Shop: client-side search over the static product index ----
  var productsPromise;
  function loadProducts() {
    productsPromise = productsPromise || fetch('/data/products.txt').then(function (r) { return r.text(); }).then(function (t) { return t.split('\n').filter(Boolean); });
    return productsPromise;
  }
  var brandsPromise;
  function loadBrands() {
    brandsPromise = brandsPromise || fetch('/data/brands.json').then(function (r) { return r.json(); }).then(function (list) {
      return list.map(function (b) { return { name: b[0], link: b[1], slug: slugify(b[0]) }; }).sort(function (a, b) { return b.slug.length - a.slug.length; });
    });
    return brandsPromise;
  }

  if (page === 'shop') {
    var results = $('[data-results]');
    var form = $('[data-search-form]');
    var keywords = (results.getAttribute('data-keywords') || '').split(' ').filter(Boolean);
    // Brand, type and department pages ship their own product list.
    var listUrl = results.getAttribute('data-list');
    var source = listUrl ? fetch(listUrl).then(function (r) { return r.json(); }) : null;
    form.q.value = params.get('q') || '';
    // Tutor listings end in -<state>-<id>, so ?state=ca narrows them to one state.
    var stateCode = (params.get('state') || '').toLowerCase().replace(/[^a-z]/g, '').slice(0, 2);
    var stateRe = stateCode ? new RegExp('-' + stateCode + '-\\d+$') : null;
    document.querySelectorAll('[data-state-chip]').forEach(function (c) { c.classList.toggle('active', c.getAttribute('data-state-chip') === stateCode); });
    var run = function () {
      (source || loadProducts()).then(function (all) {
        var q = tokens(form.q.value);
        var items = all.filter(function (slug) {
          var parts = slug.split('-');
          if (keywords.length && !keywords.some(function (k) { return parts.some(function (p) { return p.indexOf(k) === 0; }); })) return false;
          if (stateRe && !stateRe.test(slug)) return false;
          return q.every(function (w) { return slug.indexOf(w) !== -1; });
        });
        paginate(items, function (slug) {
          return '<a class="card product-card" href="/shop/' + encodeURIComponent(slug) + '"><span class="product-thumb"><img data-img-slug="' + esc(slug) + '" loading="lazy" referrerpolicy="no-referrer" alt=""></span><h3>' + esc(titleCase(slug)) + '</h3><span class="muted">View product →</span></a>';
        }, results, $('[data-load-more]'), $('[data-result-count]'), 'products', 60);
      });
    };
    form.addEventListener('submit', function (e) { e.preventDefault(); run(); });
    form.q.addEventListener('input', function () { clearTimeout(run.t); run.t = setTimeout(run, 200); });
    run();
  }

  if (page === 'product') {
    var pathSlug = location.pathname.match(/^\/shop\/([^\/]+)\/?$/);
    var slug = params.get('p') || (pathSlug && pathSlug[1] !== 'product' ? decodeURIComponent(pathSlug[1]) : '');
    var name = titleCase(slug) || 'Product not found';
    document.title = name + ' — Dealux';
    $('[data-product-name]').textContent = name;
    $('[data-product] img[data-img-slug]').setAttribute('data-img-slug', slug);
    fillImages($('[data-product]'));
    var link = $('[data-product-link]');
    detailsFor(slug).then(function (d) {
      if (d[0]) { $('[data-product-name]').textContent = d[0]; document.title = d[0] + ' — Dealux'; }
      $('[data-product-brand]').textContent = [money(d[1], d[2]), d[3] && 'by ' + d[3]].filter(Boolean).join(' · ');
      if (d[1]) { link.setAttribute('data-value', d[1]); link.setAttribute('data-currency', d[2] || 'USD'); }
      if (d[5]) {
        link.href = d[5];
        link.setAttribute('rel', 'sponsored noopener');
        link.textContent = 'Buy at ' + (d[3] || 'the store') + ' →';
        return;
      }
      // No stored product link: fall back to the brand's own affiliate link.
      return loadBrands().then(function (brands) {
        var key = slugify(d[3] || '');
        var brand = brands.filter(function (b) { return b.slug && (b.slug === key || slug === b.slug || slug.indexOf(b.slug + '-') === 0); })[0];
        if (brand) {
          if (!d[3]) $('[data-product-brand]').textContent = 'by ' + brand.name;
          link.href = brand.link;
          link.textContent = 'Shop at ' + brand.name + ' →';
        } else {
          link.href = '/brands/';
          link.removeAttribute('target');
          link.textContent = 'Browse our brands →';
        }
      });
    }).then(function () {
      link.classList.remove('hidden');
    });
  }

  // ---- Brand directory: filter the pre-rendered list ----
  if (page === 'brands') {
    var bf = $('[data-brand-filter]');
    var rows = $$('.brand-list li');
    var filterBrands = function () {
      var q = bf.q.value.trim().toLowerCase(), c = bf.category ? bf.category.value : '', n = 0;
      rows.forEach(function (li) {
        var ok = (!q || li.getAttribute('data-name').indexOf(q) !== -1) && (!c || li.getAttribute('data-category') === c);
        li.hidden = !ok; if (ok) n++;
      });
      $('[data-result-count]').textContent = n.toLocaleString() + ' brands';
    };
    bf.addEventListener('input', filterBrands);
    bf.addEventListener('submit', function (e) { e.preventDefault(); });
  }

  // ---- Journal: client-side search over the static article index ----
  if (page === 'journal') {
    var jf = $('[data-search-form]');
    var jr = $('[data-results]');
    jf.q.value = params.get('q') || '';
    jf.topic.value = params.get('topic') || '';
    var posts;
    var runJournal = function (initial) {
      (posts ? Promise.resolve(posts) : fetch('/data/journal.json').then(function (r) { return r.json(); })).then(function (list) {
        posts = list;
        var q = jf.q.value.trim().toLowerCase(), topic = jf.topic.value;
        var items = list.filter(function (p) { return (!topic || p[2] === topic) && (!q || p[1].toLowerCase().indexOf(q) !== -1); });
        paginate(items, function (p) {
          return '<a class="card post-card" href="/journal/' + p[0] + '/">' + (p[4] ? '<img loading="lazy" src="' + esc(p[4]) + '" alt="">' : '') +
            '<span class="eyebrow">' + esc(titleCase(p[2] || 'journal')) + '</span><h3>' + esc(p[1]) + '</h3></a>';
        }, jr, $('[data-load-more]'), $('[data-result-count]'), 'articles', 24, initial);
      });
    };
    jf.addEventListener('input', function () { clearTimeout(runJournal.t); runJournal.t = setTimeout(function () { runJournal(); }, 150); });
    jf.addEventListener('submit', function (e) { e.preventDefault(); runJournal(); });
    $('[data-load-more]').onclick = function () { runJournal(48); };
    if (jf.q.value || jf.topic.value) runJournal();
  }
})();

// ---- Share bar on every detail page (deal, shop item, exclusive, article, job, ticket) ----
(function () {
  'use strict';
  var h1 = document.querySelector('main h1, h1');
  var depth = location.pathname.split('/').filter(Boolean).length;
  if (!h1 || depth < 2 && !/^\/(tickets|entradas)/.test(location.pathname)) return;
  var u = encodeURIComponent(location.href), t = encodeURIComponent(document.title);
  var img = document.querySelector('meta[property="og:image"]');
  var m = encodeURIComponent(img ? img.content : '');
  var NETS = [
    ['Facebook', 'facebook', '#1877F2', 'https://www.facebook.com/sharer/sharer.php?u=' + u],
    ['X', 'x', '#000', 'https://x.com/intent/tweet?url=' + u + '&text=' + t],
    ['WhatsApp', 'whatsapp', '#25D366', 'https://wa.me/?text=' + t + '%20' + u],
    ['Telegram', 'telegram', '#26A5E4', 'https://t.me/share/url?url=' + u + '&text=' + t],
    ['Pinterest', 'pinterest', '#BD081C', 'https://www.pinterest.com/pin/create/button/?url=' + u + '&media=' + m + '&description=' + t],
    ['LinkedIn', 'linkedin', '#0A66C2', 'https://www.linkedin.com/sharing/share-offsite/?url=' + u],
    ['Reddit', 'reddit', '#FF4500', 'https://www.reddit.com/submit?url=' + u + '&title=' + t],
    ['VK', 'vk', '#0077FF', 'https://vk.com/share.php?url=' + u + '&title=' + t],
    ['LINE', 'line', '#00C300', 'https://social-plugins.line.me/lineit/share?url=' + u],
    ['KakaoTalk', 'kakaotalk', '#FFCD00', 'https://story.kakao.com/share?url=' + u],
    ['Snapchat', 'snapchat', '#FFFC00', 'https://www.snapchat.com/scan?attachmentUrl=' + u],
    ['Instagram', 'instagram', '#E4405F', 'https://www.instagram.com/', 1],
    ['Discord', 'discord', '#5865F2', 'https://discord.com/channels/@me', 1],
    ['WeChat', 'wechat', '#07C160', 'https://www.wechat.com/en', 1],
    ['RedNote', 'xiaohongshu', '#FF2442', 'https://www.xiaohongshu.com/', 1]
  ];
  var bar = document.createElement('div');
  bar.className = 'share-bar';
  bar.innerHTML = '<span class="eyebrow">Share</span>' +
    '<button type="button" class="share-btn share-copy" data-copy title="Copy link">🔗 Copy link</button>' +
    NETS.map(function (n) {
      return '<a class="share-btn" href="' + n[3] + '" target="_blank" rel="noopener" title="Share on ' + n[0] + '"' +
        (n[4] ? ' data-copyfirst' : '') + ' style="background:' + n[2] + '"><img src="/assets/share/' + n[1] + '.svg" alt="' + n[0] + '" width="18" height="18"></a>';
    }).join('');
  h1.insertAdjacentElement('afterend', bar);
  var copy = function () { return navigator.clipboard ? navigator.clipboard.writeText(location.href).catch(function () {}) : Promise.resolve(); };
  bar.addEventListener('click', function (e) {
    var b = e.target.closest('[data-copy]');
    if (b) { copy().then(function () { b.textContent = '✓ Link copied'; setTimeout(function () { b.textContent = '🔗 Copy link'; }, 2000); }); return; }
    // Apps without a web share URL: copy the link first so it can be pasted there.
    if (e.target.closest('[data-copyfirst]')) copy();
  });
})();

// Contact Dealux Support box, injected at the bottom of every page (Netlify Forms: "support-contact").
(function () {
  function mount() {
    if (document.getElementById('dx-support')) return;
    var box = document.createElement('section');
    box.id = 'dx-support';
    box.setAttribute('aria-labelledby', 'dx-support-title');
    box.innerHTML =
      '<style>#dx-support{box-sizing:border-box;max-width:760px;margin:40px auto 10px;padding:24px;border:1px solid #e3e3e8;border-radius:14px;background:#fafafc;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color:#222}' +
      '#dx-support *{box-sizing:border-box}#dx-support h2{margin:0 0 8px;font-size:1.3em}#dx-support p{margin:0 0 10px;color:#555;line-height:1.5}' +
      '#dx-support ul{margin:0 0 16px;padding-left:18px;color:#444;line-height:1.7}#dx-support a{color:#5b3df5}' +
      '#dx-support .dx-row{display:grid;grid-template-columns:1fr 1fr;gap:10px}@media(max-width:560px){#dx-support .dx-row{grid-template-columns:1fr}}' +
      '#dx-support input,#dx-support select,#dx-support textarea{width:100%;padding:10px 12px;margin:0 0 10px;border:1px solid #d4d4dc;border-radius:8px;font:inherit;background:#fff;color:#222}' +
      '#dx-support textarea{min-height:110px;resize:vertical}#dx-support button{padding:11px 22px;border:0;border-radius:8px;background:#5b3df5;color:#fff;font-weight:600;font-size:1em;cursor:pointer}' +
      '#dx-support button[disabled]{opacity:.6;cursor:wait}#dx-support .dx-status{margin-top:10px;font-weight:500}</style>' +
      '<h2 id="dx-support-title">Contact Dealux Support</h2>' +
      '<p>For any digital download asset delivery issues, checkout questions, or technical help, please reach out to our team directly.</p>' +
      '<ul><li><strong>Customer Support Email:</strong> <a href="mailto:support@dealuxapp.com">support@dealuxapp.com</a></li>' +
      '<li><strong>Response Window:</strong> We review all inquiries within 24–48 business hours.</li></ul>' +
      '<form name="support-contact" method="POST" data-netlify="true" netlify-honeypot="bot-field">' +
      '<input type="hidden" name="form-name" value="support-contact">' +
      '<p hidden><label>Leave blank <input name="bot-field"></label></p>' +
      '<input type="email" name="email" placeholder="Your email" required aria-label="Your email">' +
      '<div class="dx-row"><select name="topic" aria-label="Topic"><option>Download / delivery issue</option><option>Checkout question</option><option>Technical help</option><option>Other</option></select>' +
      '<input name="order" placeholder="Order / session ID (optional)" aria-label="Order ID"></div>' +
      '<textarea name="message" placeholder="How can we help?" required aria-label="Message"></textarea>' +
      '<input type="hidden" name="page">' +
      '<input type="hidden" name="subject" value="Dealux support request (%{submissionId})">' +
      '<button type="submit">Send message</button><div class="dx-status" role="status"></div></form>';
    var footer = document.querySelector('body > footer');
    if (footer) footer.parentNode.insertBefore(box, footer); else document.body.appendChild(box);
    var form = box.querySelector('form'), status = box.querySelector('.dx-status'), btn = box.querySelector('button');
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      form.page.value = location.href;
      btn.disabled = true; status.style.color = '#555'; status.textContent = 'Sending…';
      // dealuxapp.com is fronted by a host that rejects POSTs (405), so off Netlify the submission goes
      // straight to the Netlify deploy. That reply has no CORS headers, hence "no-cors" (opaque response).
      var onNetlify = /\.netlify\.app$/.test(location.hostname) || location.hostname === 'localhost';
      fetch(onNetlify ? '/__forms.html' : 'https://dealux.netlify.app/__forms.html', { method: 'POST', mode: onNetlify ? 'same-origin' : 'no-cors', headers: { 'Content-Type': 'application/x-www-form-urlencoded' }, body: new URLSearchParams(new FormData(form)).toString() })
        .then(function (r) {
          if (r.type !== 'opaque' && !r.ok) throw new Error(r.status);
          form.reset(); status.style.color = '#1a7f37';
          status.textContent = '✓ Thanks! Your message was sent. We’ll reply from support@dealuxapp.com within 24–48 business hours.';
        })
        .catch(function () { status.style.color = '#c62828'; status.textContent = 'Something went wrong. Please email support@dealuxapp.com directly.'; })
        .then(function () { btn.disabled = false; });
    });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mount); else mount();
})();

// Terms of Service & Privacy Policy link, added to the site footer on every page.
(function () {
  function mount() {
    var footer = document.querySelector('.site-footer .wrap, body > footer');
    if (!footer || footer.querySelector('a[href^="/legal"]')) return;
    var p = document.createElement('p');
    p.innerHTML = '<a href="/legal">Terms of Service &amp; Privacy Policy</a>';
    footer.appendChild(p);
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mount); else mount();
})();

// Admitad, Temu and FlexJobs partner cards, guaranteed on every page. Cards a page already
// ships in its own sidebar are left alone; any that are missing are added to that sidebar,
// or, on pages without one, to a partner row just above the footer.
(function () {
  var CARDS = [
    ['twnfz.com/g/vtnpdcgcecc0d22003ddbef570c363', '<div class="card promo-card side-banner">' +
      '<span class="eyebrow">Admitad · Publishers</span>' +
      '<h3>Wait – don’t leave empty-handed</h3>' +
      '<p class="muted">It takes 2 minutes to get started. Tell us who you are and we’ll take you to the right place.</p>' +
      '<p class="muted"><b>Publishers:</b> Turn your traffic and audience into steady revenue with 3000+ brands.</p>' +
      '<a class="btn btn-gold" href="https://twnfz.com/g/vtnpdcgcecc0d22003ddbef570c363/" target="_blank" rel="sponsored noopener">Get Started with ADMITAD →</a></div>'],
    ['temu.to/k/pss0huunk6r', '<div class="card promo-card temu-storefront">' +
      '<span class="eyebrow">Temu · My storefront</span>' +
      '<h3>✨Discover Amazing Finds at My Storefront 🎁</h3>' +
      '<p class="muted">Don’t miss out on the special coupon bundle waiting for you. 🌟 Packed with top-notch products at unbeatable prices. Click my link now to enjoy, shop, and save big! 🛍️✨</p>' +
      '<a class="btn btn-gold" href="https://temu.to/k/pss0huunk6r" target="_blank" rel="sponsored noopener">Shop my storefront →</a></div>'],
    ['flexjobs.sjv.io/c/5661882/1847140/20168', '<div class="card promo-card flexjobs-card">' +
      '<span class="eyebrow">FlexJobs · Remote work</span>' +
      '<a rel="sponsored noopener" href="https://flexjobs.sjv.io/c/5661882/1847140/20168" target="_blank"><img src="https://a.impactradius-go.com/display-ad/20168-1847140" alt="FlexJobs" width="200" height="200" loading="lazy" style="max-width:200px;height:auto"></a>' +
      '<img height="0" width="0" src="https://imp.pxf.io/i/5661882/1847140/20168" style="position:absolute;visibility:hidden;" alt="">' +
      '<h3>The #1 Job Site to Find Work From Home Jobs</h3>' +
      '<p class="muted">No Ads, Scams, or Junk. Find legitimate work-from-home jobs with options for flexible hours and hybrid work.</p>' +
      '<a class="btn btn-gold" href="https://flexjobs.sjv.io/c/5661882/1847140/20168" target="_blank" rel="sponsored noopener">Start your 2 week trial →</a></div>'],
    ['t.mercor.com/aOxh6', '<div class="card promo-card mercor-card">' +
      '<span class="eyebrow">Mercor · Remote jobs</span>' +
      '<h3>Mercor: Apply for remote jobs today!</h3>' +
      '<p class="muted">Get matched with top AI labs and companies hiring remote experts, engineers and specialists for well-paid contract work.</p>' +
      '<a class="btn btn-gold" href="https://t.mercor.com/aOxh6" target="_blank" rel="sponsored noopener">Apply on Mercor →</a></div>']
  ];
  function mount() {
    if (document.querySelector('.dx-partner-cards')) return;
    var missing = CARDS.filter(function (c) { return !document.querySelector('.promo-card a[href*="' + c[0] + '"]'); });
    if (!missing.length) return;
    var html = missing.map(function (c) { return c[1]; }).join('');
    var existing = document.querySelector('.post-sidebar .promo-card, .ex-widgets .promo-card, aside .promo-card');
    if (existing) {
      var wrap = document.createElement('div');
      wrap.className = 'dx-partner-cards';
      wrap.style.cssText = 'display:contents';
      wrap.innerHTML = html;
      existing.parentNode.appendChild(wrap);
      return;
    }
    var css = document.createElement('style');
    css.textContent = '.dx-partner-cards.wrap{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:16px;margin-top:2rem;margin-bottom:2rem}' +
      '.dx-partner-cards .card{display:flex;flex-direction:column;gap:8px}.dx-partner-cards .btn{align-self:flex-start}';
    document.head.appendChild(css);
    var box = document.createElement('aside');
    box.className = 'wrap dx-partner-cards';
    box.setAttribute('aria-label', 'Sponsored partners');
    box.innerHTML = html;
    var footer = document.querySelector('.site-footer, body > footer');
    if (footer) footer.parentNode.insertBefore(box, footer); else document.body.appendChild(box);
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mount); else mount();
})();

// Partner row: five compact sponsor boxes (Gumroad, Clickworker, SproutGigs, Monetag, Takefluence)
// shown on every page as a static (in-flow, non-floating) row directly below the white
// partner-logo strip, so they're on screen as the page opens. Each whole box is one link; the
// longer description is kept as its hover tooltip to keep the row short. The
// Bulent Labs QA product row stays above the footer on Journal, Shop, Tutoring and Tickets pages.
(function () {
  var m = location.pathname.match(/^\/(jobs|journal|shop|tickets|tutors)(\/|$)/);
  var withQA = !!m && m[1] !== 'jobs';
  var QA = [
    ['yhsmbr', 'PawShop QA – Bug Hunting Practice Platform'],
    ['gjcft', '7-Day QA Challenge – Learn Testing by Finding Real Bugs'],
    ['eounw', 'Bug Hunt Edition – Manual QA Testing Practice App'],
    ['hwwerd', 'PageTurner Bookstore – Manual QA Testing Practice App'],
    ['ujwclh', 'Manual QA University – Realistic Practice App with 30 Intentional Bugs']
  ];
  var CARDS = [
    ['Gumroad', 'Gumroad · Digital products', 'Gumroad: Shop for digital products today!',
      'Discover ebooks, courses, templates, software and more from independent creators.',
      'https://gumroad.com/discover?a=938737555', 'Discover on Gumroad →'],
    ['Clickworker', 'Clickworker · Earn online', 'Clickworker: Join and make your first $10',
      'Complete simple online micro-tasks from home and get paid for your work.',
      'https://www.clickworker.com/clickworker?customer=false&utm_source=31341333&utm_campaign=CW4CW&utm_medium=email', 'Join Clickworker →'],
    ['SproutGigs', 'SproutGigs · Micro-tasks', 'SproutGigs: Hire Real People For Any Task',
      'An online marketplace that instantly connects freelancers and business owners around the world with easy-to-do affordable digital tasks.',
      'https://sproutgigs.com/?a=491c4d1d', 'Visit SproutGigs →'],
    ['Monetag', 'Monetag · Publishers', 'Join Monetag and Monetize your Projects!',
      'Turn your website, app or blog traffic into revenue with Monetag ad formats.',
      'https://monetag.com/?ref_id=tpAC', 'Join Monetag →'],
    ['Takefluence', 'Takefluence · Creators', 'Turn Your Influence Into Income',
      'From personal profiles to themed pages — monetize with Takefluence. No matter the platform or following.',
      'https://takefluence.com/?ref=DLOOA', 'Join Takefluence →']
  ];
  function card(c) {
    return '<a class="card dx-partner-card" href="' + c[4].replace(/&/g, '&amp;') + '" target="_blank" rel="sponsored noopener"' +
      ' title="' + c[3] + '" aria-label="Sponsored: ' + c[0] + ' – ' + c[2] + '">' +
      '<span class="eyebrow">' + c[1] + '</span><b class="dx-pc-title">' + c[2] + '</b>' +
      '<span class="dx-pc-cta">' + c[5] + '</span></a>';
  }
  function mount() {
    if (document.querySelector('.dx-partner-rails')) return;
    var css = document.createElement('style');
    css.textContent =
      '.dx-partner-rails{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:8px;max-width:1240px;margin:.6rem auto;padding:0 16px}' +
      '@media(max-width:900px){.dx-partner-rails{grid-template-columns:repeat(3,minmax(0,1fr))}}@media(max-width:560px){.dx-partner-rails{grid-template-columns:repeat(2,minmax(0,1fr))}}' +
      '.dx-partner-rail{display:contents}' +
      '.dx-partner-rails .dx-partner-card{display:flex;flex-direction:column;gap:3px;margin:0;padding:8px 10px;text-decoration:none;color:inherit;min-width:0}' +
      '.dx-partner-rails .dx-partner-card:hover{border-color:var(--gold)}' +
      '.dx-partner-rails .eyebrow{font-size:.62rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}' +
      '.dx-pc-title{font-size:.8rem;line-height:1.25;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;flex:1}' +
      '.dx-pc-cta{font-size:.72rem;font-weight:600;color:var(--gold)}' +
      '.dx-bulent{margin-top:2rem;margin-bottom:2rem}.dx-bulent h2{margin:0 0 .25rem}' +
      '.dx-bulent-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:16px;margin-top:1rem}' +
      '.dx-bulent .card{display:flex;flex-direction:column;gap:8px;justify-content:space-between}.dx-bulent .btn{align-self:flex-start}';
    document.head.appendChild(css);

    var rail = document.createElement('aside');
    rail.className = 'dx-partner-rails';
    rail.setAttribute('aria-label', 'Sponsored partners');
    rail.innerHTML = CARDS.map(card).join('');

    var footer = document.querySelector('.site-footer, body > footer');
    var parent = footer ? footer.parentNode : document.body;
    if (withQA) {
      var qa = document.createElement('section');
      qa.className = 'wrap dx-bulent';
      qa.setAttribute('aria-label', 'Sponsored: Bulent Labs QA practice apps');
      qa.innerHTML = '<span class="eyebrow">Sponsored · Courtesy of Bulent Labs in partnership with Gumroad</span>' +
        '<h2>Practice QA testing on real apps</h2>' +
        '<div class="dx-bulent-grid">' + QA.map(function (p) {
          return '<div class="card promo-card"><h3>' + p[1] + '</h3>' +
            '<a class="btn btn-gold" href="https://gumroad.com/a/699604883/' + p[0] + '" target="_blank" rel="sponsored noopener">Get it on Gumroad →</a></div>';
        }).join('') + '</div>';
      parent.insertBefore(qa, footer || null);
    }
    var strip = document.querySelector('.partner-strip');
    if (strip) strip.parentNode.insertBefore(rail, strip.nextSibling);
    else parent.insertBefore(rail, footer || null);
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mount); else mount();
})();


// Top-converting offers: 3–5 cards, shuffled on every page view, in the sidebar of Shop
// (incl. tutors), Journal article and Tickets pages. Free trials and $0 sign-ups first.
(function () {
  var p = location.pathname;
  if (!/^\/(shop|tickets|tutors)(\/|$)/.test(p) && !/^\/journal\/[^\/]+/.test(p)) return;
  var OFFERS = [
    ['Amazon Prime · 30-day free trial', 'Try Prime free for 30 days', 'Fast free delivery, Prime Video, Prime Music and member deals. Cancel anytime.', 'https://link.amazon/B06mOwNMn', 'Start free trial →'],
    ['Audible · Free trial', 'Your first audiobook is on us', 'Start an Audible free trial and listen to bestsellers, podcasts and Originals.', 'https://link.amazon/A0dWMpD9R', 'Try Audible free →'],
    ['Kindle Unlimited · Free trial', 'Read millions of ebooks free', 'Unlimited reading on any device during your Kindle Unlimited free trial.', 'https://link.amazon/A0iKJZ418', 'Start reading free →'],
    ['Amazon Music Unlimited · Free trial', '100 million songs, ad-free', 'Try Amazon Music Unlimited free and listen offline on any device.', 'https://link.amazon/A04nYUHSN', 'Listen free →'],
    ['Prime Video · Free trial', 'Stream movies & originals free', 'Watch award-winning Amazon Originals and blockbusters with a Prime Video trial.', 'https://link.amazon/A0bM79KKJ', 'Watch free →'],
    ['Prime for Young Adults', '6 months of Prime free', 'Ages 18–24: full Prime benefits free for 6 months, then half price.', 'https://link.amazon/B0iBeZKpt', 'Claim 6 months free →'],
    ['Temu · $100 coupon bundle', '👋 Get a $100 coupon bundle', 'Download the Temu app, then use code afp71786 at checkout for 30% off.', 'https://temu.to/k/us99VQ0Kn3pQvzg', 'Get $100 in coupons →'],
    ['FlexJobs · Remote work', 'Find legit work-from-home jobs', 'Hand-screened remote and flexible jobs. No ads, scams or junk.', 'https://flexjobs.sjv.io/c/5661882/1847140/20168', 'Start your trial →']
  ];
  function mount() {
    if (document.querySelector('.dx-top-offers')) return;
    var list = OFFERS.slice();
    for (var i = list.length - 1; i > 0; i--) { var j = Math.floor(Math.random() * (i + 1)), t = list[i]; list[i] = list[j]; list[j] = t; }
    list = list.slice(0, 3 + Math.floor(Math.random() * 3));
    var box = document.createElement('div');
    box.className = 'dx-top-offers';
    box.setAttribute('aria-label', 'Sponsored offers');
    box.innerHTML = list.map(function (o) {
      return '<div class="card promo-card"><span class="eyebrow">' + o[0] + '</span><h3>' + o[1] + '</h3>' +
        '<p class="muted">' + o[2] + '</p><a class="btn btn-gold" href="' + o[3] + '" target="_blank" rel="sponsored noopener">' + o[4] + '</a></div>';
    }).join('');
    var css = document.createElement('style');
    css.textContent = '.dx-top-offers{display:flex;flex-direction:column;gap:1rem;margin:0 0 1rem}.dx-top-offers .btn{align-self:flex-start}' +
      '.dx-top-offers.dx-row{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));margin:1rem 0 1.5rem}';
    document.head.appendChild(css);
    var side = document.querySelector('.post-sidebar:not(.post-sidebar-left)') || document.querySelector('.shop-layout > aside.sidebar') ||
      document.querySelector('aside.product-flexjobs');
    if (side) { side.insertBefore(box, side.firstChild); return; }
    var h1 = document.querySelector('main h1');
    box.className += ' dx-row';
    if (h1 && h1.parentNode) h1.parentNode.insertBefore(box, h1.nextSibling);
    else (document.querySelector('main') || document.body).appendChild(box);
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mount); else mount();
})();
// Static partner sidebar on every page that loads this script: TravelPayouts (marker 699401) and
// Creative HR Solutions AI automation (am_id smlux6738218502). A fixed right rail on wide screens and
// a compact fixed bar at the bottom on small screens. It is always shown and has no close button.
(function () {
  function mount() {
    if (document.getElementById('dx-tp-side')) return;
    var css = document.createElement('style');
    css.textContent =
      '#dx-tp-side{position:fixed;right:8px;top:50%;transform:translateY(-50%);z-index:900;width:136px;' +
      'display:flex;flex-direction:column;gap:8px;font-family:inherit}' +
      '#dx-tp-side .dx-sc{border-radius:14px;padding:10px;color:#fff;box-sizing:border-box;' +
      'box-shadow:0 18px 40px -12px rgba(11,61,145,.55),0 0 0 1px rgba(255,255,255,.08) inset}' +
      '#dx-tp-side .dx-sc-tp{background:linear-gradient(160deg,#0b3d91 0%,#1565d8 55%,#22b3c8 100%)}' +
      '#dx-tp-side .dx-sc-hr{background:linear-gradient(160deg,#1e1b4b 0%,#4338ca 55%,#2563eb 100%)}' +
      '#dx-tp-side .dx-tp-tag{display:inline-block;font-size:8.5px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;' +
      'background:rgba(255,255,255,.18);padding:3px 8px;border-radius:999px;margin-bottom:5px}' +
      '#dx-tp-side .dx-tp-ico{font-size:18px;line-height:1;margin-bottom:4px}' +
      '#dx-tp-side h3{margin:0 0 4px;font-size:13px;line-height:1.25;font-weight:800;color:#fff}' +
      '#dx-tp-side h3 b{color:#ffd54a}' +
      '#dx-tp-side p{margin:0 0 8px;font-size:11px;line-height:1.45;color:rgba(255,255,255,.88)}' +
      '#dx-tp-side a.dx-tp-cta{display:block;text-align:center;background:#ffd54a;color:#0b2a5c;font-weight:800;font-size:13px;' +
      'padding:9px 10px;border-radius:10px;text-decoration:none;transition:transform .15s,box-shadow .15s}' +
      '#dx-tp-side a.dx-tp-cta:hover{transform:translateY(-1px);box-shadow:0 8px 18px -6px rgba(0,0,0,.4)}' +
      '#dx-tp-side small{display:block;margin-top:6px;font-size:10px;color:rgba(255,255,255,.6);text-align:center}' +
            '@media (max-height:700px) and (min-width:1541px){#dx-tp-side p,#dx-tp-side .dx-tp-ico{display:none}}' +
      '@media (max-width:1540px){#dx-tp-side{top:auto;bottom:0;left:0;right:0;transform:none;width:auto;flex-direction:row;gap:6px;padding:6px}' +
      '#dx-tp-side .dx-sc{flex:1;min-width:0;border-radius:12px;padding:8px 10px;display:flex;align-items:center;gap:8px}' +
      '#dx-tp-side .dx-tp-tag,#dx-tp-side p,#dx-tp-side small{display:none}#dx-tp-side .dx-tp-ico{margin:0;font-size:20px}' +
      '#dx-tp-side h3{font-size:12px;margin:0 0 4px}#dx-tp-side a.dx-tp-cta{display:inline-block;padding:5px 10px;font-size:11.5px}' +
      'body{padding-bottom:84px!important}}' +
      '@media print{#dx-tp-side{display:none}}';
    document.head.appendChild(css);
    var box = document.createElement('aside');
    box.id = 'dx-tp-side';
    box.setAttribute('aria-label', 'Sponsored partners');
    box.innerHTML =
      '<div class="dx-sc dx-sc-tp"><span class="dx-tp-tag">Partner program</span>' +
      '<div class="dx-tp-ico" aria-hidden="true">&#9992;&#65039;</div>' +
      '<div><h3>Earn up to <b>$3,000</b> promoting travel brands</h3>' +
      '<p>Join TravelPayouts and get paid for flights, hotels, tours and more you recommend.</p>' +
      '<a class="dx-tp-cta" href="https://www.travelpayouts.com/?marker=699401" target="_blank" rel="sponsored noopener">Join TravelPayouts &rarr;</a>' +
      '<small>Sponsored</small></div></div>' +
      '<div class="dx-sc dx-sc-hr"><span class="dx-tp-tag">AI for business</span>' +
      '<div class="dx-tp-ico" aria-hidden="true">&#129302;</div>' +
      '<div><h3>Stop losing <b>62%</b> of your calls</h3>' +
      '<p>Missed-call text back, AI webchat and voice assistants that capture every lead 24/7. Book a live demo today.</p>' +
      '<a class="dx-tp-cta" href="https://creativehrsolutions.co/home?am_id=smlux6738218502" target="_blank" rel="sponsored noopener">Get AI automation &rarr;</a>' +
      '<small>Sponsored</small></div></div>';
    document.body.appendChild(box);
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mount); else mount();
})();
// Amazon partner rail (tag smlux6738210a-20): Amazon card on every page, plus an Audible free-trial
// card on Journal, Shop (including tutor listings) and Tickets pages. Fixed left rail on wide
// screens; on small screens the cards sit just above the bottom partner bar. Always shown.
(function () {
  var AMZ = 'https://www.amazon.com?&linkCode=ll2&tag=smlux6738210a-20&linkId=fc2c1dc089167358f0bceafba1fb78d7&language=en_US&ref_=as_li_ss_tl';
  var AUD = 'https://www.amazon.com/hz/audible/arya/mlp?_encoding=UTF8&purchaseType=STANDARD_MTRIAL&SHOPPING_PORTAL_MODE=AUGMENTED&linkCode=ll2&tag=smlux6738210a-20&linkId=e8094007a5ab2170b3d3253482a29fd2&language=en_US&ref_=as_li_ss_tl';
  function mount() {
    if (document.getElementById('dx-amz-side')) return;
    var audible = /^\/(journal|shop|tickets|tutors)(\/|$)/.test(location.pathname);
    var css = document.createElement('style');
    css.textContent =
      '#dx-amz-side{position:fixed;left:8px;top:50%;transform:translateY(-50%);z-index:900;width:136px;display:flex;flex-direction:column;gap:8px;font-family:inherit}' +
      '#dx-amz-side .dx-ac{border-radius:14px;padding:10px;color:#fff;box-sizing:border-box;box-shadow:0 18px 40px -12px rgba(0,0,0,.5)}' +
      '#dx-amz-side .dx-ac-amz{background:linear-gradient(160deg,#131921 0%,#232f3e 60%,#37475a 100%)}' +
      '#dx-amz-side .dx-ac-aud{background:linear-gradient(160deg,#c2410c 0%,#f97316 60%,#fb923c 100%)}' +
      '#dx-amz-side .dx-tag{display:inline-block;font-size:8.5px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;background:rgba(255,255,255,.18);padding:3px 8px;border-radius:999px;margin-bottom:5px}' +
      '#dx-amz-side .dx-ico{font-size:18px;line-height:1;margin-bottom:4px}' +
      '#dx-amz-side h3{margin:0 0 4px;font-size:13px;line-height:1.25;font-weight:800;color:#fff}' +
      '#dx-amz-side h3 b{color:#ffd54a}' +
      '#dx-amz-side p{margin:0 0 8px;font-size:11px;line-height:1.45;color:rgba(255,255,255,.9)}' +
      '#dx-amz-side a.dx-cta{display:block;text-align:center;background:#ffd54a;color:#131921;font-weight:800;font-size:11.5px;padding:7px 6px;border-radius:10px;text-decoration:none;transition:transform .15s}' +
      '#dx-amz-side a.dx-cta:hover{transform:translateY(-1px)}' +
      '#dx-amz-side small{display:block;margin-top:6px;font-size:10px;color:rgba(255,255,255,.65);text-align:center}' +
            '@media (max-height:700px) and (min-width:1541px){#dx-amz-side p,#dx-amz-side .dx-ico{display:none}}' +
      '@media (max-width:1540px){#dx-amz-side{top:auto;bottom:64px;left:0;right:0;transform:none;width:auto;flex-direction:row;gap:6px;padding:0 6px}' +
      '#dx-amz-side .dx-ac{flex:1;min-width:0;border-radius:12px;padding:8px 10px;display:flex;align-items:center;gap:8px}' +
      '#dx-amz-side .dx-tag,#dx-amz-side p,#dx-amz-side small{display:none}#dx-amz-side .dx-ico{margin:0;font-size:20px}' +
      '#dx-amz-side h3{font-size:12px;margin:0 0 4px}#dx-amz-side a.dx-cta{display:inline-block;padding:5px 10px;font-size:11.5px}' +
      'body{padding-bottom:150px!important}}' +
      '@media print{#dx-amz-side{display:none}}';
    document.head.appendChild(css);
    var box = document.createElement('aside');
    box.id = 'dx-amz-side';
    box.setAttribute('aria-label', 'Sponsored: Amazon');
    box.innerHTML =
      '<div class="dx-ac dx-ac-amz"><span class="dx-tag">Today&rsquo;s deals</span>' +
      '<div class="dx-ico" aria-hidden="true">&#128722;</div>' +
      '<div><h3>Shop <b>Amazon</b> deals today</h3>' +
      '<p>Fresh daily deals on electronics, home, fashion and more. Grab them before they sell out.</p>' +
      '<a class="dx-cta" href="' + AMZ + '" target="_blank" rel="sponsored noopener">Shop now on Amazon &rarr;</a>' +
      '<small>Sponsored</small></div></div>' +
      (audible ?
      '<div class="dx-ac dx-ac-aud"><span class="dx-tag">Audible free trial</span>' +
      '<div class="dx-ico" aria-hidden="true">&#127911;</div>' +
      '<div><h3>Try <b>Audible</b> free &mdash; start today</h3>' +
      '<p>Pick your first audiobook free and start listening tonight. Cancel anytime.</p>' +
      '<a class="dx-cta" href="' + AUD + '" target="_blank" rel="sponsored noopener">Start my free trial &rarr;</a>' +
      '<small>Sponsored</small></div></div>' : '');
    document.body.appendChild(box);
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mount); else mount();
})();

// Keep buying guidance and sourcing information reachable from existing site pages.
(function () {
  function addEditorialLinks() {
    var footer = document.querySelector('.site-footer .wrap, body > footer');
    if (!footer || footer.querySelector('a[href="/about/"]')) return;
    var links = document.createElement('p');
    links.innerHTML = '<a href="/guides/">Buying guides &amp; tools</a> · <a href="/about/">About &amp; editorial standards</a>';
    footer.appendChild(links);
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', addEditorialLinks);
  else addEditorialLinks();
})();
