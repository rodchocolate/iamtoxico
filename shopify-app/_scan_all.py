#!/usr/bin/env python3
"""One-shot: dump all Printify products with titles + image URLs."""
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
shops = c.get_shops()
print(f"Shops: {len(shops)}")

for shop in shops:
    sid = shop['id']
    print(f"\n=== Shop: {shop['title']} (ID: {sid}) ===")
    products = c.get_products(sid)
    print(f"Products: {len(products)}")
    for p in products:
        imgs = p.get('images', [])
        print(f"\n  ID:    {p['id']}")
        print(f"  Title: {p.get('title', '(no title)')}")
        desc = (p.get('description') or '')[:120].replace('\n', ' ')
        print(f"  Desc:  {desc}")
        print(f"  Images: {len(imgs)}")
        for i, img in enumerate(imgs[:6]):
            print(f"    [{i}] {img.get('src', '')[:100]}")
