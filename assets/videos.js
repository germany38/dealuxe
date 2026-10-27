// Video cards: click the poster to play inline; "Show more videos" pages through /data/videos.json.
(function () {
  function esc(s) {
    return String(s || '').replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; });
  }

  document.addEventListener('click', function (e) {
    var thumb = e.target.closest('.video-thumb');
    if (!thumb) return;
    var card = thumb.closest('.video-card');
    var img = thumb.querySelector('img');
    var v = document.createElement('video');
    v.className = 'video-player';
    v.controls = true;
    v.autoplay = true;
    v.playsInline = true;
    if (img) v.poster = img.src;
    v.src = card.getAttribute('data-src');
    thumb.replaceWith(v);
    v.play().catch(function () {});
  });

  var more = document.querySelector('[data-video-more]');
  var grid = document.querySelector('[data-video-grid]');
  if (!more || !grid) return;
  var skip = (more.getAttribute('data-skip') || '').split(',');
  var list = null, pos = 0;

  function card(v) {
    var img = v.poster ? '<img src="' + esc(v.poster) + '" alt="' + esc(v.name) + '" loading="lazy">'
                       : '<span class="video-noposter">' + esc(v.brand) + '</span>';
    return '<div class="card video-card" data-src="' + esc(v.src) + '">' +
      '<button class="video-thumb" type="button" aria-label="Play ' + esc(v.name) + '">' + img + '<span class="video-play">▶</span></button>' +
      '<span class="eyebrow">' + esc(v.brand) + '</span>' +
      '<h3><a href="/videos/' + esc(v.slug) + '/">' + esc(v.name) + '</a></h3>' +
      '<p class="muted">' + esc(v.desc) + '</p>' +
      (v.deal ? '<p class="promo-note">' + esc(v.deal) + '</p>' : '') +
      '<div class="product-actions"><a class="btn btn-ghost" href="/videos/' + esc(v.slug) + '/">Details</a>' +
      '<a class="btn btn-gold" href="' + esc(v.link) + '" target="_blank" rel="nofollow sponsored noopener">Get offer →</a></div></div>';
  }

  function show() {
    var next = list.slice(pos, pos + 24);
    pos += 24;
    grid.insertAdjacentHTML('beforeend', next.map(card).join(''));
    if (pos >= list.length) more.hidden = true;
  }

  more.addEventListener('click', function () {
    if (list) return show();
    more.disabled = true;
    fetch('/data/videos.json').then(function (r) { return r.json(); }).then(function (all) {
      list = all.filter(function (v) { return skip.indexOf(v.slug) < 0; });
      more.disabled = false;
      show();
    }).catch(function () { more.disabled = false; });
  });
})();
