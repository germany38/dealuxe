(function () {
  var q = document.getElementById('ex-q');
  var grid = document.getElementById('ex-grid');
  var count = document.getElementById('ex-count');
  var cards = Array.prototype.slice.call(grid.querySelectorAll('.ex-card'));
  var chips = Array.prototype.slice.call(document.querySelectorAll('.ex-chip'));
  var cat = '';
  var params = new URLSearchParams(location.search);
  if (params.get('q')) q.value = params.get('q');

  function apply() {
    var term = q.value.trim().toLowerCase();
    var shown = 0;
    cards.forEach(function (c) {
      var ok = (!cat || c.dataset.cat === cat) && (!term || c.dataset.search.indexOf(term) !== -1);
      c.style.display = ok ? '' : 'none';
      if (ok) shown++;
    });
    count.textContent = shown.toLocaleString() + ' resources';
  }
  chips.forEach(function (b) {
    b.addEventListener('click', function () {
      chips.forEach(function (x) { x.classList.remove('active'); });
      b.classList.add('active');
      cat = b.dataset.filter;
      apply();
    });
  });
  q.addEventListener('input', apply);
  apply();
})();
