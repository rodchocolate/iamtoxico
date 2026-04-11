#!/usr/bin/env python3
"""Dump staging shop products to JSON for preview.html."""
import json, os, sys

sys.path.insert(0, os.path.dirname(__file__))

# Read API key directly
env_path = os.path.join(os.path.dirname(__file__), '.env')
api_key = None
with open(env_path) as f:
    for line in f:
        if line.startswith('PRINTIFY_API_KEY='):
            api_key = line.split('=', 1)[1].strip()
            break

from printify_connector import PrintifyConnector
pc = PrintifyConnector(api_key)

# Staging shop
staging = pc.get_products('22994552')
# Live shop
live = pc.get_products('26651009')

out = []
for shop_label, products in [('staging', staging), ('live', live)]:
    for p in products:
        imgs = p.get('images', [])
        first_img = imgs[0].get('src', '') if imgs else ''
        # Get all variant SKUs
        skus = list(set(v.get('sku', '') for v in p.get('variants', []) if v.get('sku')))
        out.append({
            'id': p['id'],
            'title': p['title'],
            'image': first_img,
            'shop': shop_label,
            'images': [i.get('src', '') for i in imgs],
            'skus': skus,
            'description': p.get('description', ''),
        })

print(json.dumps(out, indent=2))
