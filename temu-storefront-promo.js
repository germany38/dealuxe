document.addEventListener("DOMContentLoaded", function() {
  // Your exact promotional copy and active storefront link
  const promoHTML = `
    <div class="temu-storefront-bonus" style="background: #fff5eb; border: 2px solid #ff6600; padding: 18px; border-radius: 8px; margin-bottom: 25px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
      <h4 style="color: #ff6600; margin-top: 0; margin-bottom: 8px; font-size: 1.15em; display: flex; align-items: center; gap: 6px; font-weight: 700;">✨ Discover Amazing Finds 🎁</h4>
      <p style="font-size: 0.95em; line-height: 1.5; color: #333; margin: 0 0 14px 0;">
        Don’t miss out on the special coupon bundle waiting for you. 🌟 Packed with top-notch products at unbeatable prices. Click my link to enjoy, shop, and save big!
      </p>
      <a href="https://temu.to/k/pvakusmcr5a" target="_blank" rel="noopener noreferrer" style="display: block; text-align: center; background: #ff6600; color: #ffffff; padding: 12px 15px; text-decoration: none; font-weight: bold; border-radius: 6px; font-size: 1em; text-transform: uppercase; letter-spacing: 0.5px;">
        Shop My Storefront 🛍️✨
      </a>
    </div>
  `;

  // 1. INJECT INTO BLOG ARTICLE SIDEBARS
  const sidebars = document.querySelectorAll('aside, .sidebar, [class*="sidebar"]');
  sidebars.forEach(sidebar => {
    const container = document.createElement('div');
    container.innerHTML = promoHTML;
    sidebar.insertBefore(container.firstChild, sidebar.firstChild);
  });

  // 2. FEATURE ON ALL PRODUCT PAGES
  const productContainers = document.querySelectorAll('.product-details, [class*="product-info"], main article');
  productContainers.forEach(container => {
    if (window.location.pathname.includes('/shop/') && !container.querySelector('.temu-storefront-bonus')) {
      const productPromo = document.createElement('div');
      productPromo.style.cssText = "margin-top: 20px; margin-bottom: 20px;";
      productPromo.innerHTML = promoHTML;
      container.appendChild(productPromo);
    }
  });
});
