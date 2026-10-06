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

  // ---- 404: forward old /shop/<slug> URLs to the static product page ----
  var legacy = location.pathname.match(/^\/shop\/([^\/]+)\/?$/);
  if (page === 'notfound' && legacy && legacy[1] !== 'product') {
    location.replace('/shop/product/?p=' + encodeURIComponent(legacy[1]));
    return;
  }

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
    var run = function () {
      (source || loadProducts()).then(function (all) {
        var q = tokens(form.q.value);
        var items = all.filter(function (slug) {
          var parts = slug.split('-');
          if (keywords.length && !keywords.some(function (k) { return parts.some(function (p) { return p.indexOf(k) === 0; }); })) return false;
          return q.every(function (w) { return slug.indexOf(w) !== -1; });
        });
        paginate(items, function (slug) {
          return '<a class="card product-card" href="/shop/product/?p=' + encodeURIComponent(slug) + '"><span class="product-thumb"><img data-img-slug="' + esc(slug) + '" loading="lazy" referrerpolicy="no-referrer" alt=""></span><h3>' + esc(titleCase(slug)) + '</h3><span class="muted">View product →</span></a>';
        }, results, $('[data-load-more]'), $('[data-result-count]'), 'products', 60);
      });
    };
    form.addEventListener('submit', function (e) { e.preventDefault(); run(); });
    form.q.addEventListener('input', function () { clearTimeout(run.t); run.t = setTimeout(run, 200); });
    run();
  }

  if (page === 'product') {
    var slug = params.get('p') || '';
    var name = titleCase(slug) || 'Product not found';
    document.title = name + ' — Dealux';
    $('[data-product-name]').textContent = name;
    $('[data-product] img[data-img-slug]').setAttribute('data-img-slug', slug);
    fillImages($('[data-product]'));
    var link = $('[data-product-link]');
    detailsFor(slug).then(function (d) {
      if (d[0]) { $('[data-product-name]').textContent = d[0]; document.title = d[0] + ' — Dealux'; }
      $('[data-product-brand]').textContent = [money(d[1], d[2]), d[3] && 'by ' + d[3]].filter(Boolean).join(' · ');
      if (d[5]) {
        link.href = d[5];
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
      var q = bf.q.value.trim().toLowerCase(), c = bf.category.value, n = 0;
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
            '<span class="eyebrow">' + esc(titleCase(p[2] || 'journal')) + ' · ' + p[3] + '</span><h3>' + esc(p[1]) + '</h3></a>';
        }, jr, $('[data-load-more]'), $('[data-result-count]'), 'articles', 24, initial);
      });
    };
    jf.addEventListener('input', function () { clearTimeout(runJournal.t); runJournal.t = setTimeout(function () { runJournal(); }, 150); });
    jf.addEventListener('submit', function (e) { e.preventDefault(); runJournal(); });
    $('[data-load-more]').onclick = function () { runJournal(48); };
    if (jf.q.value || jf.topic.value) runJournal();
  }
})();
