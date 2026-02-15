
import os
import sys
import json

# Add current directory to path to allow imports if needed, 
# though we are in the same directory as printify_connector.py
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from printify_connector import PrintifyConnector

def load_env_file(filepath):
    """Simple .env loader"""
    try:
        with open(filepath, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()
    except FileNotFoundError:
        print(f"Warning: {filepath} not found")

def scan_products():
    # Load environment variables
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
    load_env_file(env_path)
    
    api_key = os.getenv("PRINTIFY_API_KEY")
    if not api_key:
        print("Error: PRINTIFY_API_KEY not found in environment or .env file")
        return

    try:
        connector = PrintifyConnector(api_key)
        shops = connector.get_shops()
        
        print(f"Found {len(shops)} shops.")
        
        keywords = ["robe", "blanket hoodie", "hoodie blanket"]
        found_products = []

        for shop in shops:
            shop_id = shop['id']
            shop_title = shop['title']
            print(f"Scanning shop: {shop_title} (ID: {shop_id})...")
            
            products = connector.get_products(shop_id)
            print(f"  - Found {len(products)} total products in shop.")
            
            for product in products:
                title = product.get('title', '').lower()
                description = product.get('description', '').lower()
                
                # Check for keywords
                if any(k in title for k in keywords):
                    print(f"  [MATCH] Found potential match: {product['title']}")
                    found_products.append({
                        'shop_id': shop_id,
                        'shop_title': shop_title,
                        'product': product
                    })
        
        print("\n" + "="*50)
        print(f"SCAN COMPLETE. Found {len(found_products)} matches.")
        print("="*50)
        
        for item in found_products:
            p = item['product']
            print(f"\nProduct: {p['title']}")
            print(f"ID: {p['id']}")
            print(f"Shop: {item['shop_title']}")
            if p.get('images'):
                print(f"Image: {p['images'][0].get('src')}")
            print(f"External ID: {p.get('external', {}).get('id', 'N/A')}")
            
            # We could also output JSON for easy addition to catalog
            
    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    scan_products()
