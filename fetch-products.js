const fs = require('fs');
const path = require('path');

// Safe fallbacks for local testing. GitHub Actions will inject these automatically later.
const APP_KEY = process.env.PARTNERIZE_APP_KEY || 'p3tew145y3tag41n';
const API_KEY = process.env.PARTNERIZE_API_KEY || 'bF7CTSJb';
const PUBLISHER_ID = '1110l46445'; 
const CAMREF = '1100l6vIBH';

async function updateProductDatabase() {
  try {
    console.log('Step 1: Connecting to Partnerize to find your approved merchant feeds...');
    
    // We fetch your available feeds dynamically so you don't have to hardcode a Feed ID
    const feedListResponse = await fetch(`https://partnerize.com{PUBLISHER_ID}/feed`, {
      method: 'GET',
      headers: {
        'Authorization': `Basic ${Buffer.from(`\({APP_KEY}:\){API_KEY}`).toString('base64')}`,
        'Content-Type': 'application/json'
      }
    });

    if (!feedListResponse.ok) {
      throw new Error(`Failed to fetch feed list. Status: ${feedListResponse.status}`);
    }

    const feedsData = await feedListResponse.json();
    
    // Extract the first active feed ID found in your account
    const activeFeed = feedsData.feeds && feedsData.feeds[0];
    if (!activeFeed) {
      throw new Error('No active product feeds found. Make sure you are fully approved by the merchant in PartnerBoost.');
    }
    
    const dynamicFeedId = activeFeed.feed_metadata_id || activeFeed.feed_id;
    console.log(`Found active Feed ID: ${dynamicFeedId} (${activeFeed.name || 'Merchant Catalog'})`);

    console.log('Step 2: Exporting raw product items from the feed...');
    
    // Download the data payload directly in JSON format
    const productResponse = await fetch(`https://partnerize.com{PUBLISHER_ID}/feed/${dynamicFeedId}/export?user_api_key=${API_KEY}&format=json`, {
      method: 'GET',
      headers: {
        'Authorization': `Basic ${Buffer.from(`\({APP_KEY}:\){API_KEY}`).toString('base64')}`,
        'Content-Type': 'application/json'
      }
    });

    if (!productResponse.ok) {
      throw new Error(`Failed to download product catalog. Status: ${productResponse.status}`);
    }

    const rawProducts = await productResponse.json();
    console.log(`Successfully retrieved ${rawProducts.length || 0} raw items.`);

    console.log('Step 3: Injected tracking parameters and cleaning up data fields...');
    
    // Format the products cleanly for your front-end framework
    const enrichedProducts = rawProducts.map(item => {
      // Get the raw product destination link (e.g. Amazon product page)
      const baseDestination = item.destination_url || item.url || '';
      // Securely url-encode it so the prf.hn wrapper doesn't break
      const cleanDestination = encodeURIComponent(baseDestination);
      
      return {
        id: item.product_id || item.asin || Math.random().toString(36).substr(2, 9),
        title: item.product_name || item.title || 'Premium Deal',
        description: item.product_description || item.description || 'View details on storefront.',
        brand: item.brand || 'Featured',
        category: item.category || 'Deals',
        price: item.price || item.advertised_price || 'Check Price',
        imageUrl: item.image_url || item.image_thumb_url || '',
        // Your tracking parameter is built perfectly here:
        affiliateLink: `https://prf.hn{CAMREF}/destination:${cleanDestination}`
      };
    });

    // Make sure the directory structure exists before writing the file
    const targetDir = path.join(__dirname, 'src', 'data');
    if (!fs.existsSync(targetDir)){
        fs.mkdirSync(targetDir, { recursive: true });
    }

    // Save the finalized data file
    fs.writeFileSync(path.join(targetDir, 'products.json'), JSON.stringify(enrichedProducts, null, 2));
    console.log('Pipeline complete! Your tracking-safe products.json has been written to ./src/data/products.json.');
    
  } catch (error) {
    console.error('Pipeline Error:', error.message);
    process.exit(1);
  }
}

updateProductDatabase();
