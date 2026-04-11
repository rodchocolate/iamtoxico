#!/usr/bin/env python3
"""Rename harem pants on Printify (live shop) and check live shop details."""
import os, sys, json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from printify_connector import PrintifyConnector

def load_env():
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                os.environ[k.strip()] = v.strip()

load_env()
c = PrintifyConnector()

LIVE_SHOP = 26651009

# First, get full details of live products to see their print area images
products = c.get_products(LIVE_SHOP)
print("=== Live Shop Products (detail) ===")
for p in products:
    det = c.get_product(LIVE_SHOP, p['id'])
    print_areas = det.get('print_areas', [])
    pa_images = []
    for pa in print_areas:
        for placeholder in pa.get('placeholders', []):
            for img in placeholder.get('images', []):
                pa_images.append(img.get('id', ''))
    ext = det.get('external', {})
    print(f"  ID: {p['id']}  Title: {det['title']}  ExtID: {ext.get('id','N/A')}  ArtworkIDs: {pa_images}")

# Now rename them
renames = {
    '69a4628646730b56700a6ae1': 'Toxico Harem Pant',
    '69a462891ec5ca402c037d02': 'Arctic River Harem Pant',
    '69a4628c9f7e893e8a0e5219': 'Hot Oil Harem Pant',
    '69a4628f94ca9fbf1d020f6e': 'Cyan Glow Harem Pant',
    '69a46294eb470f86b105fab3': 'Hold Cards Harem Pant',
    '69a4629b7fc2996b8d0abe8e': 'Frozen Sky Harem Pant',
}

print("\n=== Renaming Harem Pants ===")
for pid, new_title in renames.items():
    try:
        result = c.update_product(LIVE_SHOP, pid, {"title": new_title})
        print(f"  OK: {pid} -> {new_title}")
    except Exception as e:
        print(f"  FAIL: {pid} -> {new_title}: {e}")
