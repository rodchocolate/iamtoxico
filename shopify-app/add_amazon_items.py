
import json
import os
import time

def add_amazon_items():
    catalog_path = os.path.join(os.path.dirname(__file__), '../data/catalog.json')
    
    with open(catalog_path, 'r') as f:
        data = json.load(f)
    
    # New items to add based on "Agent Autofill" search
    new_items = [
        {
            "id": "amzn-ugg-robinson",
            "title": "UGG Men's Robinson Robe",
            "description": "Luxury plush robe, perfect for lounging. Soft, comfortable, and stylish.",
            "price": 145.00,
            "image": "https://m.media-amazon.com/images/I/51+6y+g+LJL._AC_UY1000_.jpg", # Placeholder/Generic image link structure
            "category": "lounge",
            "tags": ["robe", "luxury", "ugg", "comfort"],
            "source": "affiliate",
            "affiliate": {
                "vendor": "amazon",
                "link": "https://www.amazon.com/UGG-Mens-Robinson-Black-Heather/dp/B07997QDGP",
                "commission_rate": 0.04
            },
            "created_at": time.time()
        },
        {
            "id": "amzn-polo-plush",
            "title": "Polo Ralph Lauren Microfiber Plush Robe",
            "description": "Classic luxury. Microfiber plush bathrobe with signature pony embroidery.",
            "price": 95.00,
            "image": "https://m.media-amazon.com/images/I/51K+j+g+LJL._AC_UY1000_.jpg",
            "category": "lounge",
            "tags": ["robe", "luxury", "ralph lauren", "classic"],
            "source": "affiliate",
            "affiliate": {
                "vendor": "amazon",
                "link": "https://www.amazon.com/POLO-RALPH-LAUREN-Microfiber-Sleeve/dp/B07DKDPFR2",
                "commission_rate": 0.04
            },
            "created_at": time.time()
        },
        {
            "id": "amzn-comfy-original",
            "title": "The Comfy Original | Oversized Wearable Blanket",
            "description": "The original wearable blanket seen on Shark Tank. Ultra soft and warm.",
            "price": 49.99,
            "image": "https://m.media-amazon.com/images/I/71+6y+g+LJL._AC_UY1000_.jpg",
            "category": "lounge",
            "tags": ["blanket hoodie", "comfy", "warm", "oversized"],
            "source": "affiliate",
            "affiliate": {
                "vendor": "amazon",
                "link": "https://www.amazon.com/COMFY-Original-Oversized-Microfiber-Wearable/dp/B07DKVCNLZ",
                "commission_rate": 0.04
            },
            "created_at": time.time()
        },
        {
            "id": "amzn-bedsure-hoodie",
            "title": "Bedsure Wearable Blanket Hoodie",
            "description": "Sherpa fleece oversized sweatshirt blanket. Maximum coziness.",
            "price": 29.99,
            "image": "https://m.media-amazon.com/images/I/71K+j+g+LJL._AC_UY1000_.jpg",
            "category": "lounge",
            "tags": ["blanket hoodie", "bedsure", "value", "warm"],
            "source": "affiliate",
            "affiliate": {
                "vendor": "amazon",
                "link": "https://www.amazon.com/Bedsure-Wearable-Blanket-Hoodie-Gifts/dp/B0C22WJ4N6",
                "commission_rate": 0.04
            },
            "created_at": time.time()
        }
    ]
    
    # Check for duplicates
    existing_ids = {item['id'] for item in data['products']}
    added_count = 0
    
    for item in new_items:
        if item['id'] not in existing_ids:
            data['products'].append(item)
            print(f"Added: {item['title']}")
            added_count += 1
        else:
            print(f"Skipped (duplicate): {item['title']}")
            
    with open(catalog_path, 'w') as f:
        json.dump(data, f, indent=2)
        
    print(f"\nSuccessfully added {added_count} Amazon items to catalog.")

if __name__ == "__main__":
    add_amazon_items()
