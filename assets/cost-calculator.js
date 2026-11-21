document.getElementById('cost-comparison').addEventListener('submit', function (event) {
  event.preventDefault();
  if (!this.reportValidity()) return;
  const number = name => Number(this.elements.namedItem(name).value);
  const months = number('months');
  const total = key => Math.round((number(key + '-price') * (1 - number(key + '-discount') / 100) + number(key + '-shipping') + number(key + '-tax') + number(key + '-monthly') * months) * 100) / 100;
  const a = total('a'), b = total('b');
  const result = document.getElementById('comparison-result');
  if (![a, b].every(Number.isFinite)) { result.textContent = 'These amounts are too large. Enter smaller values.'; return; }
  result.textContent = 'Offer A: ' + a.toFixed(2) + '. Offer B: ' + b.toFixed(2) + '. ' + (a === b ? 'Both offers cost the same.' : 'Offer ' + (a < b ? 'A' : 'B') + ' costs ' + Math.abs(a - b).toFixed(2) + ' less over this period.') + ' Amounts are in your chosen currency.';
});
