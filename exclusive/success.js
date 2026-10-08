(function () {
  var sid = new URLSearchParams(location.search).get('session_id');
  var title = document.getElementById('ex-s-title');
  var msg = document.getElementById('ex-s-msg');
  var dl = document.getElementById('ex-s-dl');
  function fail(t, m) { title.textContent = t; msg.textContent = m; }
  if (!sid) return fail('Missing checkout reference', 'Open the link from your Stripe receipt, or contact us with your receipt and we’ll send your PDF.');
  var tries = 0;
  function check() {
  fetch('/api/exclusive/session?session_id=' + encodeURIComponent(sid))
    .then(function (r) { return r.json().then(function (d) { return { ok: r.ok, status: r.status, d: d }; }); })
    .then(function (res) {
      // Payment can take a few seconds to settle; keep checking before giving up.
      if (res.status === 402 && ++tries < 10) return setTimeout(check, 3000);
      if (!res.ok) return fail('We couldn’t confirm this purchase', res.d.error || 'Please contact us with your Stripe receipt.');
      title.textContent = 'Thank you! Your PDF is ready';
      msg.textContent = res.d.title + ' — your download should start automatically.';
      dl.href = '/api/exclusive/download?session_id=' + encodeURIComponent(sid);
      dl.classList.remove('hidden');
      setTimeout(function () { location.href = dl.href; }, 800);
    })
    .catch(function () { fail('Something went wrong', 'Please refresh this page to try again.'); });
  }
  check();
})();
