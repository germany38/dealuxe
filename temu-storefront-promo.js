(function() {
  function injectTemuWidget() {
    // Prevent duplicate boxes from loading
    if (document.getElementById('global-temu-bonus-widget')) return;

    // Create the widget container
    const widget = document.createElement('div');
    widget.id = 'global-temu-bonus-widget';
    
    // Inject the styled card with your active affiliate link
    widget.innerHTML = `
      <div style="background: #fff5eb; border: 2px solid #ff6600; padding: 16px; border-radius: 12px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; box-shadow: 0 10px 25px rgba(255, 102, 0, 0.15); position: relative; max-width: 320px;">
        <button onclick="document.getElementById('global-temu-bonus-widget').style.display='none'" style="position: absolute; top: 8px; right: 10px; background: none; border: none; font-size: 16px; cursor: pointer; color: #999; font-weight: bold;">&times;</button>
        <h4 style="color: #ff6600; margin-top: 0; margin-bottom: 6px; font-size: 1.1em; display: flex; align-items: center; gap: 6px; font-weight: 700;">✨ Discover Amazing Finds 🎁</h4>
        <p style="font-size: 0.88em; line-height: 1.4; color: #333; margin: 0 0 12px 0;">
          Don’t miss out on the special coupon bundle waiting for you. 🌟 Packed with top-notch products at unbeatable prices.
        </p>
        <a href="https://temu.to" target="_blank" rel="noopener noreferrer" style="display: block; text-align: center; background: #ff6600; color: #ffffff; padding: 10px 12px; text-decoration: none; font-weight: bold; border-radius: 6px; font-size: 0.9em; text-transform: uppercase; letter-spacing: 0.5px; box-shadow: 0 4px 10px rgba(255, 102, 0, 0.3);">
          Shop My Storefront 🛍️✨
        </a>
      </div>
    `;

    // Modern styling to stick it to the bottom-right corner of the window
    widget.style.cssText = "position: fixed; bottom: 20px; right: 20px; z-index: 999999; max-width: 320px; box-sizing: border-box; display: block;";

    // Responsive design: center it on small phone screens automatically
    const styleTag = document.createElement('style');
    styleTag.innerHTML = `
      @media (max-width: 480px) {
        #global-temu-bonus-widget {
          right: 10px !important;
          left: 10px !important;
          bottom: 15px !important;
          max-width: calc(100% - 20px) !important;
        }
      }
    `;
    document.head.appendChild(styleTag);
    document.body.appendChild(widget);
  }

  // Force compilation checks to load instantly or delay safely
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', injectTemuWidget);
  } else {
    injectTemuWidget();
  }
  // Safety fallback for delayed image shifts
  setTimeout(injectTemuWidget, 800);
})();
