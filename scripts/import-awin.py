#!/usr/bin/env python3
"""Import AWIN content into Netlify Database and publish static shop projections.

Run: python3 scripts/import-awin.py data/feeds/awin-products.csv
Stable AWIN merchant/product IDs prevent duplicates. Generates an immutable,
forward-only seed migration only when catalog records change. The deployed shop
continues to use its existing static indexes and server-rendered product pages.
"""
import csv, collections, datetime, glob, hashlib, html, importlib.util, json, os, re, sys
from decimal import Decimal
from urllib.parse import urlparse, parse_qs
spec = importlib.util.spec_from_file_location('cj', os.path.join(os.path.dirname(__file__), 'import-cj-links.py'))
cj = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cj)

# Feed taxonomy mapped to the shop's existing department/type navigation.
GROUPS = {
('automotive','car-accessories'): 'Tyres|Wheels|Car Accessories|Motorcycles|Motorsport|Car Parts|Auto Care|GPS & Sat Nav|Vehicles, Parts and Accessories|Vehicle Servicing|Vehicle Security|New & Used Cars|In-Car Entertainment',
('clothing','clothing-other'): "General Clothing|Baby Clothes|Men's Suits|Men's Clothing|Women's Suits|Women's Clothing|Children's Clothing|Women's Underwear|Men's Underwear|Men's Socks|Girls' Clothes|Boys' Clothes|Maternity|Socks & Hosiery",
('clothing','tops'): "Novelty T-Shirts|Men's Tops|Women's Tops",
('clothing','bottoms'): "Men's Trousers|Women's Trousers",
('clothing','outerwear'): "Men's Outerwear|Women's Outerwear",
('clothing','dresses'): "Women's Dresses & Skirts",
('clothing','swimwear-activewear'): "Men's Sportswear|Sportswear & Swimwear|Women's Sportswear|Women's Swimwear|Men's Swimwear",
('shoes-bags','fashion-accessories'): "Accessories|Women's Accessories|Clothing Accessories|Men's Accessories|Children's Accessories|Men's Watches|Women's Watches|Glasses",
('shoes-bags','shoes'): "Shoes|Women's Footwear|Men's Footwear|Children's Footwear",
('shoes-bags','bags'): 'Bags|Laptop Bags',
('jewelry','jewelry-sets'): "Women's Jewellery|Men's Jewellery",
('home-decor','decor-accents'): 'Furniture Accessories|Furniture|Decorations|House Accessories|Home Accessories|Living Room',
('home-decor','lamps'): 'Lighting',
('bedroom','beds-headboards'): 'Beds|Mattresses',
('accent-furniture','accent-tables'): 'Tables',
('accent-furniture','accent-chairs'): 'Chairs',
('living-room','sofas-sectionals'): 'Sofas',
('living-room','dividers-storage'): 'Storage',
('home-decor','home-textiles'): 'Curtains & Blinds|Home Textiles',
('home-decor','wall-art'): 'Art',
('home-decor','holiday-decor'): "Valentine's Day",
('home-decor','plants-flowers'): 'Flowers|Plants & Seeds',
('home-garden','garden-patio'): 'Garden & Leisure|Sheds & Garden Furniture|Garden Tools|Garden|Agricultural Products|Lawn Mowers|Barbecues & Accessories',
('home-garden','home-essentials'): 'Cleaning|DIY|Laundry & Cleaning|Power Tools|Bathrooms & Accessories|General Household|Hand Tools|Combination Sets|Home Security|Flooring & Carpeting|Showers|Painting & Decorating|Bathrooms|Bespoke Bathrooms',
('home-garden','kitchen-dining'): 'Kitchen Units|Kitchen|Glassware|Crockery|Cookware & Utensils|Cutlery|Bespoke Kitchens',
('electronics','appliances'): 'Refrigeration|Heating & Cooling|Appliance Spares|Small Appliances|Bodycare Appliances|Other Appliances|Haircare Appliances|Coffee Makers|Grills|Fans|Cooking|Electric Kettles|Fridges',
('electronics','vacuums-floor-care'): 'Vacuum Cleaners|Vacuum Cleaner Accessories',
('hair-beauty','beauty-care'): 'Fragrance|Cosmetics & Skincare|Skincare|Haircare Products|Haircare|Cosmetics|Shaving',
('wellness','medical-supplies'): 'Health|Support Aids|Medical|Oral Health|Bodycare & Fitness|Lifestyle|Bathroom Scales|Contact Lenses',
('wellness','vitamins-supplements'): 'Vitamins & Supplements|Nutrition',
('sports-outdoors','sports-outdoor-gear'): 'Fitness Equipment|Outdoor Adventure|Fitness|Fishing|Trampolines|Boxing|Golf|Basketball|Football|Water Sports|Snooker, Pool & Billiards|Cycling|Tennis|Table Tennis|Badminton|Squash|Swimming Accessories|Other Sports|Winter Sports|Other Team Sports|Racket Sports',
('toys-hobbies','toys-games'): 'Toys|Other Toys|Dolls|Outdoor Toys|Action Figures|Toy Models|Electronic & RC Toys|Soft Toys|Creative & Construction|Musical Toys',
('toys-hobbies','baby-nursery'): 'Baby Toys|Baby Products',
('toys-hobbies','arts-crafts'): 'Arts & Crafts',
('education','learning-games'): 'Games, Puzzles & Learning',
('toys-hobbies','costumes'): 'Fancy Dress',
('toys-hobbies','pet-supplies'): 'Pets',
('toys-hobbies','party-supplies'): 'Birthday Gifts|Gifts|Christmas Gifts|Novelty Gifts|Other Occasions|Personalised Gifts|Greeting Cards|Wedding Gifts|Anniversary Gifts',
('food-snacks','pantry-food'): 'Food',
('food-snacks','snack-bars'): 'Chocolate|Cakes, Snacks & Sweets',
('food-snacks','gift-baskets'): 'Hampers',
('food-snacks','drinks'): 'Drinks',
('education','workbooks'): 'Books|Magazine Subscriptions',
('office','office-school-supplies'): 'Calendars|Office Supplies',
('experiences','hotels-stays'): 'Accommodation',
('experiences','shows-attractions'): 'Theatre|Tourist Attractions|Experiences',
('travel','flights-car-rentals'): 'Holidays|Airport Parking|Cruises|Car Hire',
('cameras-photo','photo-video-accessories'): 'Photography|Camcorders|Bodies',
('cameras-photo','cameras-film'): 'Cameras',
('electronics','software-apps'): 'Software',
('services','web-hosting-marketing'): 'Web Hosting',
('services','finance-insurance'): 'Finance',
('fan-shop','fan-gear'): 'Collectibles|Sports Memorabilia',
('toys-hobbies','video-games'): 'Video Gaming|Video Games|Console|Handhelds|UMDs',
('electronics','gaming-accessories'): 'Console Accessories|Joysticks and Gaming',
('electronics','tvs'): 'Televisions|Standard (4:3) TV',
('electronics','home-theater'): 'Audio Equipment|Audio Systems|Home Entertainment|Headphones|HiFi Speakers|Streaming Media Devices|Portable Audio|Radios|DVDs|Blu-Ray|CDs|Music|Musical Instruments',
('electronics','tech-accessories'): 'Keyboards|Gadgets|Cables|Mobile Phones|Networking|Cables, Parts & Power Supplies|Television Accessories|Other Gadgets|Electronic Gadgets|Computers|Other Telephones|Monitors|Mobile Phone Accessories|Peripherals|Headsets|Mice|Bluetooth Adapters|Batteries|Hubs & Switches|Handsets|All-In-One Printers|Controller Cards|Laptops|Computer Components|Storage Media|Remote Controls|Power Supplies|Memory Card Reader|CPUs|Motherboards|Wireless Routers|Scanners|Microphones|Computer Cases|Home Telephone Accessories|Printer Consumables|Printers|Projector Accessories|WebCams|Memory Stick|Video Conferencing|Graphics Cards|IP Phones|Modems|Input Devices|Memory|Fax Machines|Blank Media|Wireless & Networking|Pay Monthly',
}
CATEGORY = {c: pair for pair, cats in GROUPS.items() for c in cats.split('|')}

def sql(s):
    return "'" + str(s).replace("'", "''") + "'"

def main(path):
    rows = list(csv.DictReader(open(path, encoding='utf-8-sig')))
    unknown = {r['category'] for r in rows} - CATEGORY.keys()
    if unknown:
        raise ValueError(f'Unmapped categories: {sorted(unknown)}')
    items = {}
    for r in rows:
        u = urlparse(r['aw_deep_link'].strip()); q = parse_qs(u.query)
        assert u.scheme == 'https' and u.hostname == 'www.awin1.com' and q.get('p') and q.get('m'), 'Invalid AWIN link'
        assert Decimal(r['price']).is_finite() and Decimal(r['price']) >= 0
        assert re.fullmatch('[A-Z]{3}', r['currency'])
        brand = cj.clean_text(r['brand'] or r['merchant'])
        slug = '-'.join(['awin', cj.slugify(brand), cj.slugify(r['product_name'])[:90].strip('-'), q['m'][0], q['p'][0]])
        dept, typ = CATEGORY[r['category']]
        # These merchants label travel data plans as accommodation/networking.
        if 'esim' in r['merchant'].casefold():
            dept, typ = 'travel', 'travel-esims'
        rec = [cj.clean_text(r['product_name']), r['price'], r['currency'], brand, r['image_url'].strip(), r['aw_deep_link'].strip(), cj.clean_text(r['description'])]
        items[slug] = dict(slug=slug, brand=brand, merchant=r['merchant'], category=r['category'], dept=dept, type=typ, rec=rec)
    shards = {n: cj.read_json(f'data/img/{n}.json', {}) for n in range(64)}
    changed = [i for s,i in items.items() if shards[cj.shard_of(s)].get(s) != i['rec']]
    fingerprint = hashlib.sha256(json.dumps(items, sort_keys=True).encode()).hexdigest()[:12]
    if not glob.glob(f'netlify/database/migrations/*_import_awin_{fingerprint}.sql'):
        changed = list(items.values())
        # Persist catalog rows in Netlify Database; static files below are publication projections.
        body = '''CREATE TABLE IF NOT EXISTS awin_catalog_products (
  slug TEXT PRIMARY KEY, name TEXT NOT NULL, price NUMERIC NOT NULL,
  currency TEXT NOT NULL, brand TEXT NOT NULL, merchant TEXT NOT NULL,
  category TEXT NOT NULL, department TEXT NOT NULL, product_type TEXT NOT NULL,
  image_url TEXT NOT NULL, affiliate_url TEXT NOT NULL, description TEXT NOT NULL
);\n'''
        for start in range(0,len(changed),500):
            vals = []
            for i in changed[start:start+500]:
                r=i['rec']; vals.append('('+','.join(map(sql,[i['slug'],r[0],r[1],r[2],i['brand'],i['merchant'],i['category'],i['dept'],i['type'],r[4],r[5],r[6]]))+')')
            body += 'INSERT INTO awin_catalog_products VALUES\n'+',\n'.join(vals)+'\nON CONFLICT (slug) DO UPDATE SET name=EXCLUDED.name, price=EXCLUDED.price, currency=EXCLUDED.currency, brand=EXCLUDED.brand, merchant=EXCLUDED.merchant, category=EXCLUDED.category, department=EXCLUDED.department, product_type=EXCLUDED.product_type, image_url=EXCLUDED.image_url, affiliate_url=EXCLUDED.affiliate_url, description=EXCLUDED.description;\n'
        migration = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d%H%M%S')+f'_import_awin_{fingerprint}.sql'
        with open('netlify/database/migrations/'+migration,'x') as f: f.write(body)
    for s,i in items.items(): shards[cj.shard_of(s)][s]=i['rec']
    for n,data in shards.items(): cj.write_json(f'data/img/{n}.json',data)
    slugs = list(dict.fromkeys(open('data/products.txt').read().splitlines() + open('products.txt').read().splitlines() + list(items)))
    for p in ['products.txt','data/products.txt']:
        open(p,'w').write('\n'.join(slugs)+'\n')
    lists = collections.defaultdict(list); names={}; links={}
    for s,i in items.items():
        b=cj.slugify(i['brand']); names[b]=i['brand'];links.setdefault(b,i['rec'][5])
        for k,v in [('brand',b),('dept',i['dept']),('type',i['type'])]: lists[f'{k}-{v}'].append(s)
    # Replace only this feed's category memberships when its mapping changes.
    for p in glob.glob('data/list/dept-*.json') + glob.glob('data/list/type-*.json'):
        old = cj.read_json(p, [])
        retained = [s for s in old if s not in items]
        if retained != old: cj.write_json(p, retained)
    for key,added in lists.items():
        p=f'data/list/{key}.json'; old=cj.read_json(p,[]); have=set(old)
        cj.write_json(p,old+[s for s in added if s not in have])
    template=open('shop/brand/3w/index.html').read()
    # Keep category navigation and link to the full brand directory, without
    # copying thousands of brand links into every new brand landing page.
    template=re.sub(r'(<summary><span class="side-link side-heading">Shop by brand</span></summary>).*?(</details>)',r'\1<a class="side-link sub" href="/brands/">Browse all brands</a>\2',template,flags=re.S)
    pages=[]; counts={}
    for b,name in sorted(names.items()):
        p=f'shop/brand/{b}/index.html'; count=len(cj.read_json(f'data/list/brand-{b}.json',[])); counts[b]=count
        if os.path.exists(p):
            h=open(p).read()
            h=re.sub(r'<p class="muted">[\d,]+ products</p>',f'<p class="muted">{count:,} products</p>',h,count=1)
            h=re.sub(r'content="Shop [\d,]+ ',f'content="Shop {count:,} ',h,count=1)
        else:
            e=html.escape(name,quote=True)
            h=cj.page_from(template,f'/shop/brand/{b}/',e,f'Shop {count:,} {e} products and deals.',f'Shop {e}',f'{count:,} products',f'/data/list/brand-{b}.json')
            # The template must not retain its original active brand.
            h=h.replace('class="side-link sub active"','class="side-link sub "')
            pages.append(f'{cj.SITE}/shop/brand/{b}/')
        cj.write_page(p,h)
    for p in ['brands.json','data/brands.json']:
        brands=cj.read_json(p,[]);have={cj.slugify(b[0]) for b in brands}
        brands += [[names[b],links[b]] for b in names if b not in have]
        cj.write_json(p,sorted(brands,key=lambda b:b[0].casefold()))
    cj.update_brand_directory(counts,names)
    # Refresh every existing visible brand badge, including the home page.
    pattern=re.compile(r'(href="/shop/brand/([^/]+)/">[^<]*<span class="muted">)[\d,]+( products?)?(</span>)')
    for p in ['index.html']+glob.glob('shop/**/index.html',recursive=True):
        h=open(p).read()
        h2=pattern.sub(lambda m:m[1]+f'{counts[m[2]]:,}'+(m[3] or '')+m[4] if m[2] in counts else m[0],h)
        if h!=h2: cj.write_page(p,h2)
    # The legacy helper only handles numbered sitemaps; AWIN has its own set.
    today=datetime.date.today().isoformat(); files=[]
    slugs=list(items)
    for n,start in enumerate(range(0,len(slugs),10000),1):
        name=f'sitemap-awin-products-{n}.xml';files.append(name)
        content='<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        content+=''.join(f'<url><loc>{cj.SITE}/shop/{s}</loc></url>\n' for s in slugs[start:start+10000])+'</urlset>\n'
        open(name,'w').write(content)
    sm=open('sitemap-shop.xml').read()
    sm=sm.replace('</urlset>',''.join(f'<url><loc>{u}</loc></url>\n' for u in pages if f'<loc>{u}</loc>' not in sm)+'</urlset>')
    open('sitemap-shop.xml','w').write(sm)
    p='sitemap-index.xml';idx=open(p).read()
    for name in files:
        if f'<loc>{cj.SITE}/{name}</loc>' not in idx:
            idx=idx.replace('</sitemapindex>',f'<sitemap><loc>{cj.SITE}/{name}</loc><lastmod>{today}</lastmod></sitemap>\n</sitemapindex>')
    open(p,'w').write(idx)
    print(f'{len(items):,} AWIN products; {len(names):,} brand groups; {len(pages):,} new brand pages; {len(changed):,} new or changed records')

if __name__=='__main__': main(sys.argv[1])
