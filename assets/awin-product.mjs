const escape = (value) => String(value).replace(/[&<>"']/g, (char) => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
})[char]);

const labels = {
  merchant: 'Merchant', category: 'Category', merchant_category: 'Merchant category',
  product_brand: 'Brand', product_type: 'Product type', colour: 'Colour', condition: 'Condition', stock_status: 'Stock',
  delivery_cost: 'Delivery cost', rrp_price: 'Recommended retail price', ean: 'EAN', mpn: 'MPN',
  merchant_product_category_path: 'Merchant category path',
};

export function awinDetails(details, currency) {
  if (!details) return '';
  const entries = Object.entries(labels).filter(([key]) => details[key]).map(([key, label]) => {
    const value = details[key] + (['delivery_cost', 'rrp_price'].includes(key) ? ` ${currency}` : '');
    return `<dt>${label}</dt><dd>${escape(value)}</dd>`;
  });
  const deal = details.power_deal
    ? `<p class="power-deal"><span class="power-deal-badge">⚡ Power Deal</span> ${escape(details.power_deal)}</p>` : '';
  return deal + `<p class="muted"><a href="/shop/brand/${escape(details.brand_slug)}/">Browse this brand</a> · ` +
    `<a href="/shop/type/${escape(details.type_slug)}/">Browse this product type</a></p>` +
    `<details class="product-specifications"><summary>Product details</summary><dl>${entries.join('')}</dl></details>`;
}

export function awinAvailability(details) {
  if (!details) return { availability: 'https://schema.org/InStock' };
  const status = details.stock_status?.toLowerCase().replace(/[\s_-]/g, '');
  const label = { instock: 'InStock', outofstock: 'OutOfStock', preorder: 'PreOrder', backorder: 'BackOrder' }[status];
  return label ? { availability: `https://schema.org/${label}` } : {};
}
