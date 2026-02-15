#!/usr/bin/env python3
"""
Add placeholder product images from brand CDNs to catalog.json.
These are publicly available product images from brand websites.
"""

import json
from pathlib import Path

CATALOG_PATH = Path(__file__).parent.parent / 'data' / 'catalog.json'

# Known brand image patterns (publicly available product images)
# These are example/placeholder URLs - actual implementation would use affiliate feeds
BRAND_IMAGES = {
    # UGG Products
    "ugg-ultra-mini": "https://images.ugg.com/is/image/UGG/1116109_CHE_1",
    "ugg-tasman": "https://images.ugg.com/is/image/UGG/5950_CHE_1",
    "ugg-neumel": "https://images.ugg.com/is/image/UGG/3236_CHE_1",
    
    # Birkenstock
    "birkenstock-boston": "https://www.birkenstock.com/on/demandware.static/-/Sites-master-catalog/default/dw8b5c8b5c/560771/560771.jpg",
    "birkenstock-arizona": "https://www.birkenstock.com/on/demandware.static/-/Sites-master-catalog/default/dw8b5c8b5c/151181/151181.jpg",
    
    # Crocs
    "crocs-classic": "https://media.crocs.com/images/t_pdphero/f_auto%2Cq_auto/products/10001_100_ALT100/crocs",
    "crocs-echo": "https://media.crocs.com/images/t_pdphero/f_auto%2Cq_auto/products/207937_001_ALT100/crocs",
    
    # Nike/Jordan (using placeholder CDN patterns)
    "jordan-1-retro-high": "https://static.nike.com/a/images/t_PDP_1728_v1/f_auto,q_auto:eco/u_126ab356-44d8-4a06-89b4-fcdcc8df0245,c_scale,fl_relative,w_1.0,h_1.0,fl_layer_apply/a6a6e51b-b0dc-4b8e-8a1d-2a8e0e1e1c5a/air-jordan-1-retro-high-og-shoes.png",
    "jordan-4-retro": "https://static.nike.com/a/images/t_PDP_1728_v1/f_auto,q_auto:eco/jordan-4-retro.png",
    "nike-dunk-low": "https://static.nike.com/a/images/t_PDP_1728_v1/f_auto,q_auto:eco/dunk-low-retro-shoe.png",
    "nike-air-force-1": "https://static.nike.com/a/images/t_PDP_1728_v1/f_auto,q_auto:eco/air-force-1-07-shoe.png",
    
    # Adidas
    "adidas-samba": "https://assets.adidas.com/images/h_840,f_auto,q_auto,fl_lossy,c_fill,g_auto/b_auto/samba-og-shoes.jpg",
    "adidas-gazelle": "https://assets.adidas.com/images/h_840,f_auto,q_auto,fl_lossy,c_fill,g_auto/gazelle-shoes.jpg",
    "adidas-stan-smith": "https://assets.adidas.com/images/h_840,f_auto,q_auto,fl_lossy,c_fill,g_auto/stan-smith-shoes.jpg",
    
    # New Balance
    "new-balance-550": "https://nb.scene7.com/is/image/NB/bb550wt1_nb_02_i",
    "new-balance-990v6": "https://nb.scene7.com/is/image/NB/m990gl6_nb_02_i",
    
    # Hoka/On
    "hoka-clifton-9": "https://www.hoka.com/on/demandware.static/-/Sites-HOKA-US-Site/default/clifton-9.jpg",
    "on-cloud-5": "https://images.ctfassets.net/cloud-5-mens.jpg",
    
    # Ferragamo/Luxury
    "ferragamo-gancini-loafer": "https://www.ferragamo.com/on/demandware.static/-/Sites-SALVATORE_FERRAGAMO/default/gancini-loafer.jpg",
    "gucci-horsebit-loafer": "https://media.gucci.com/style/horsebit-loafer.jpg",
    
    # Common Projects
    "common-projects-achilles": "https://www.mrporter.com/variants/images/achilles-low.jpg",
    
    # Blundstone/Boots
    "blundstone-500": "https://www.blundstone.com/media/catalog/product/5/0/500-stout-brown.jpg",
    "redwing-iron-ranger": "https://www.redwingshoes.com/DWTK/iron-ranger-8111.jpg",
    "thursday-captain": "https://thursday-boots-assets.s3.amazonaws.com/captain-brandy.jpg",
    
    # Allbirds
    "allbirds-wool-runner": "https://cdn.allbirds.com/image/upload/wool-runner-natural-grey.jpg",
    
    # Eyewear
    "jmm-dealan": "https://www.jacquesmariemage.com/cdn/shop/products/dealan.jpg",
    "oliver-peoples-gregory": "https://www.oliverpeoples.com/images/gregory-peck.jpg",
    "ray-ban-wayfarer": "https://www.ray-ban.com/images/original-wayfarer-classic.jpg",
    "persol-714": "https://www.persol.com/images/714-steve-mcqueen.jpg",
}

def update_catalog():
    """Add brand images to catalog products."""
    
    with open(CATALOG_PATH, 'r') as f:
        catalog = json.load(f)
    
    updated = 0
    
    for product in catalog['products']:
        product_id = product.get('id', '')
        
        # Check if we have an image for this product
        if product_id in BRAND_IMAGES:
            if not product.get('image'):
                product['image'] = BRAND_IMAGES[product_id]
                print(f"✓ {product['name']}: added image")
                updated += 1
    
    # Save updated catalog
    with open(CATALOG_PATH, 'w') as f:
        json.dump(catalog, f, indent=2)
    
    print(f"\n=== Updated {updated} products with brand images ===")
    print("\nNote: For production, you should:")
    print("  1. Use actual affiliate product feed images")
    print("  2. Or download and host images locally")
    print("  3. Refresh Printify token for your owned products")

if __name__ == "__main__":
    print("Adding brand placeholder images to catalog...\n")
    update_catalog()
