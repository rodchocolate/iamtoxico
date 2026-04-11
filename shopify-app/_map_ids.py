#!/usr/bin/env python3
"""Dump all Printify products with their external (Shopify) IDs so we can match."""
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

for shop in shops:
    sid = shop['id']
    print(f"\n=== Shop: {shop['title']} (ID: {sid}) ===")
    products = c.get_products(sid)
    for p in products:
        ext = p.get('external', {})
        ext_id = ext.get('id', 'N/A') if isinstance(ext, dict) else 'N/A'
        ext_handle = ext.get('handle', '') if isinstance(ext, dict) else ''
        print(f"  Printify: {p['id']}  |  Title: {p.get('title','?')[:60]}  |  ExtID: {ext_id}  |  Handle: {ext_handle}")
