import json
import os
import re
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent
CATALOG_PATH = ROOT / 'data' / 'catalog.json'
QUEUE_PATH = ROOT / 'PRODUCTS_TO_ADD.md'
QUEUE_LINE_PATTERN = re.compile(r'^(?:\d+\.\s+|-\s+)(https?://\S+)')


def extract_queue_links(lines):
    links = []
    seen = set()
    for raw_line in lines:
        match = QUEUE_LINE_PATTERN.match(raw_line.strip())
        if not match:
            continue
        url = match.group(1)
        if url in seen:
            continue
        seen.add(url)
        links.append(url)
    return links


def slugify(value):
    slug = re.sub(r'[^a-z0-9]+', '-', value.lower()).strip('-')
    return slug or 'item'

def get_page_metadata(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Basic Metadata
        title = soup.find('meta', property='og:title')
        title = title['content'] if title and title.has_attr('content') else (soup.title.string.strip() if soup.title and soup.title.string else url)
        
        image = soup.find('meta', property='og:image')
        image_url = image['content'] if image and image.has_attr('content') else None
        
        description = soup.find('meta', property='og:description')
        desc = description['content'] if description and description.has_attr('content') else ''
        
        # Price extraction (specific to Zimmerli or generic)
        price = 0
        currency = 'USD'
        
        # Try to find price in JSON-LD
        json_ld = soup.find('script', type='application/ld+json')
        if json_ld:
            try:
                data = json.loads(json_ld.string)
                if isinstance(data, list):
                    data = data[0]
                if 'offers' in data:
                    price = data['offers'].get('price', 0)
                    currency = data['offers'].get('priceCurrency', 'USD')
            except (json.JSONDecodeError, TypeError, ValueError):
                pass
                
        # Fallback price search
        if not price:
            price_elem = soup.select_one('.price, .product-price, [data-price]')
            if price_elem:
                price_text = price_elem.get_text()
                price_match = re.search(r'[\d\.]+', price_text)
                if price_match:
                    price = float(price_match.group())

        # Categorize based on URL or title
        category = 'loungewear' # Default
        if 'boxer' in title.lower() or 'underwear' in url:
            category = 'underwear'
        elif 'pullover' in title.lower() or 'hoodie' in title.lower():
            category = 'loungewear'
        elif 'pyjama' in title.lower() or 'sleep' in title.lower():
            category = 'loungewear'

        return {
            'name': title.split('|')[0].strip(),
            'description': desc,
            'image': image_url,
            'price': price,
            'currency': currency,
            'category': category,
            'url': url
        }
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

def process_queue():
    with open(QUEUE_PATH, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    links = extract_queue_links(lines)
    
    if not links:
        print("No links found in queue.")
        return

    print(f"Found {len(links)} links to process...")
    
    with open(CATALOG_PATH, 'r', encoding='utf-8') as f:
        catalog = json.load(f)

    products = catalog.setdefault('products', [])
    if not isinstance(products, list):
        raise ValueError("catalog.json is missing a valid products list")
    
    new_products = []
    
    for url in links:
        if 'collections' in url:
            print(f"Skipping collection page for now: {url}")
            continue
            
        print(f"Processing: {url}")
        data = get_page_metadata(url)
        if data:
            product_id = f"aff-zimmerli-{slugify(data['name'].replace('zimmerli-', ''))[:40]}"
            
            new_product = {
                "id": product_id,
                "sku": f"AFF-ZM-{len(products) + len(new_products) + 1:03d}",
                "name": data['name'],
                "subtitle": "zimmerli \u00b7 swiss made",
                "category": data['category'],
                "price": float(data['price']) if data['price'] else 0,
                "currency": data['currency'],
                "url": data['url'],
                "image": data['image'],
                "activities": ["spa", "romantic", "leisure"],
                "vibes": ["luxury", "indulgent", "comfort"],
                "source": "affiliate",
                "affiliate": {
                    "network": "direct",
                    "program": "zimmerli",
                    "commission": "10%"
                },
                "active": True
            }
            
            # Check if exists
            if not any(p.get('url') == url for p in products):
                new_products.append(new_product)
                print(f"✓ Added: {data['name']}")
            else:
                print(f"⚠ Duplicate: {data['name']}")
        
        time.sleep(1) # Be nice to the server

    if new_products:
        products.extend(new_products)
        with open(CATALOG_PATH, 'w', encoding='utf-8') as f:
            json.dump(catalog, f, indent=2)
            f.write('\n')
        print(f"\nSuccessfully added {len(new_products)} products to catalog.")
    else:
        print("\nNo new products added.")

if __name__ == "__main__":
    process_queue()
