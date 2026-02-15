#!/usr/bin/env python3
"""
Fetch product images from Printify and update catalog.json.
"""

import os
import json
import requests
from pathlib import Path
from dotenv import load_dotenv

# Load environment
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

PRINTIFY_TOKEN = os.getenv('PRINTIFY_TOKEN')
PRINTIFY_SHOP_ID = os.getenv('PRINTIFY_SHOP_ID', '22994552')
CATALOG_PATH = Path(__file__).parent.parent / 'data' / 'catalog.json'

def fetch_printify_products():
    """Fetch all products from Printify with images."""
    url = f"https://api.printify.com/v1/shops/{PRINTIFY_SHOP_ID}/products.json"
    headers = {
        "Authorization": f"Bearer {PRINTIFY_TOKEN}",
        "Content-Type": "application/json"
    }
    
    print(f"Fetching Printify products from shop {PRINTIFY_SHOP_ID}...")
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        products = data.get('data', [])
        print(f"Found {len(products)} Printify products\n")
        
        # Extract product info with images
        printify_items = []
        for p in products:
            images = p.get('images', [])
            primary_image = None
            for img in images:
                if img.get('is_default'):
                    primary_image = img.get('src')
                    break
            if not primary_image and images:
                primary_image = images[0].get('src')
            
            item = {
                'id': p.get('id'),
                'title': p.get('title'),
                'description': p.get('description'),
                'image': primary_image,
                'images': [img.get('src') for img in images if img.get('src')],
                'visible': p.get('visible', False),
                'is_locked': p.get('is_locked', False)
            }
            printify_items.append(item)
            
            img_preview = primary_image[:60] + '...' if primary_image and len(primary_image) > 60 else primary_image
            print(f"  ✓ {p.get('title')}")
            print(f"    Image: {img_preview or 'NO IMAGE'}")
        
        return printify_items
    
    except requests.exceptions.RequestException as e:
        print(f"Error fetching Printify products: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response: {e.response.text[:500]}")
        return []

def update_catalog_images(printify_products):
    """Update catalog.json with Printify images."""
    
    # Load catalog
    with open(CATALOG_PATH, 'r') as f:
        catalog = json.load(f)
    
    updated = 0
    
    print("\n--- Matching Printify products to catalog ---\n")
    
    # Match Printify products to catalog by name similarity
    for product in catalog['products']:
        if product.get('source') in ('printify', 'internal'):
            product_name = product.get('name', '').lower()
            
            for pp in printify_products:
                pp_title = pp.get('title', '').lower()
                
                # Matching logic
                name_words = [w for w in product_name.split() if len(w) > 3]
                title_words = [w for w in pp_title.split() if len(w) > 3]
                
                # Check for word overlap
                matches = sum(1 for w in name_words if w in pp_title)
                
                if matches >= 2 or product_name in pp_title or pp_title in product_name:
                    if pp.get('image'):
                        old_image = product.get('image')
                        product['image'] = pp['image']
                        if old_image != pp['image']:
                            print(f"  ✓ {product['name']}")
                            print(f"    -> {pp['image'][:60]}...")
                            updated += 1
                        break
    
    # Save updated catalog
    with open(CATALOG_PATH, 'w') as f:
        json.dump(catalog, f, indent=2)
    
    print(f"\n=== Updated {updated} products with Printify images ===")
    return updated

def main():
    if not PRINTIFY_TOKEN:
        print("Error: PRINTIFY_TOKEN not found in .env")
        print(f"Checked: {env_path}")
        return
    
    print("=" * 60)
    print("iamtoxico Printify Image Sync")
    print("=" * 60 + "\n")
    
    # Fetch Printify products
    printify_products = fetch_printify_products()
    
    if printify_products:
        # Save raw Printify data for reference
        output_path = Path(__file__).parent.parent / 'data' / 'printify_products.json'
        with open(output_path, 'w') as f:
            json.dump(printify_products, f, indent=2)
        print(f"\nSaved raw Printify data to: {output_path}")
        
        # Update catalog with images
        update_catalog_images(printify_products)
    else:
        print("No Printify products found or error occurred.")
    
    print("\n" + "=" * 60)
    print("Done!")

if __name__ == "__main__":
    main()
