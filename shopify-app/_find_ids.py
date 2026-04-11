#!/usr/bin/env python3
"""Search for user's 20-digit IDs across all Printify product variants."""
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

TARGET_IDS = [
    '16839957101917140556',
    '31609932620536031742',
    '13877295961474854639',
    '31367937769936021297',
    '10273080794575885554',
]

for shop in c.get_shops():
    sid = shop['id']
    print(f"\n=== Shop: {shop['title']} (ID: {sid}) ===")
    products = c.get_products(sid)
    for p in products:
        det = c.get_product(sid, p['id'])
        # Check all variant IDs, SKUs, external IDs
        for v in det.get('variants', []):
            vid = str(v.get('id', ''))
            vsku = str(v.get('sku', ''))
            vext = str(v.get('external_id', ''))
            for tid in TARGET_IDS:
                if tid in (vid, vsku, vext):
                    print(f"  MATCH: {tid} -> Product: {det['title'][:50]}  VarID: {vid}  SKU: {vsku}")
        
        # Check product-level external
        ext = det.get('external', {})
        if isinstance(ext, dict):
            eid = str(ext.get('id', ''))
            for tid in TARGET_IDS:
                if tid == eid:
                    print(f"  MATCH (ext): {tid} -> Product: {det['title'][:50]}")
        
        # Check product ID itself
        for tid in TARGET_IDS:
            if tid == str(p['id']):
                print(f"  MATCH (pid): {tid} -> Product: {det['title'][:50]}")

print("\n=== Done ===")
