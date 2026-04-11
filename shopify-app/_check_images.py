#!/usr/bin/env python3
"""Check Printify uploaded images + get full product details for staging shop."""
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

# Check uploaded images
print("=== Uploaded Images ===")
try:
    images = c.get_uploaded_images()
    if isinstance(images, list):
        for img in images:
            print(f"  ID: {img.get('id')}  |  File: {img.get('file_name','')}  |  URL: {str(img.get('preview_url',''))[:80]}")
    elif isinstance(images, dict):
        for img in images.get('data', []):
            print(f"  ID: {img.get('id')}  |  File: {img.get('file_name','')}  |  URL: {str(img.get('preview_url',''))[:80]}")
except Exception as e:
    print(f"  Error: {e}")

# Get full product details for new staging products (the ones that might be tops)
STAGING_SHOP = 22994552
interesting = [
    '69b643840855e0c5540e8d53',  # Copy of Hold Cards (NEW)
    '69b5d9e92d744e51f402f54a',  # Copy of Copy of Copy of Unisex Zip Hoodie
    '69b5d9e63ebd6ece8a035ad0',  # Copy of Copy of Unisex Zip Hoodie
    '69b5d6d1dc49b25f9c065607',  # Copy of Unisex Zip Hoodie
    '69b5d69d2d744e51f402f4dc',  # Unisex Zip Hoodie
    '69b57f2f8c4577fcee0f2bd9',  # Copy of Fashion Hoodie
    '69b57f19ef961127590bc947',  # Fashion Hoodie
    '69a8c6a97bde8fb9d700535c',  # Windbreaker
    '69a8c15a291e3fbf690b4ce6',  # Copy of Copy of Sports Warmup
    '69a8c0a3c9c0eae143032bff',  # Copy of Sports Warmup
    '69a8c0649091fb07d5009557',  # Sports Warmup
]

print("\n=== Staging Products Detail ===")
for pid in interesting:
    try:
        p = c.get_product(STAGING_SHOP, pid)
        # Get print area image IDs
        print_areas = p.get('print_areas', [])
        pa_images = []
        for pa in print_areas:
            for placeholder in pa.get('placeholders', []):
                for img in placeholder.get('images', []):
                    pa_images.append(img.get('id', ''))
        print(f"\n  ID: {pid}")
        print(f"  Title: {p.get('title','?')[:60]}")
        print(f"  Blueprint: {p.get('blueprint_id')}")
        print(f"  Print Provider: {p.get('print_provider_id')}")
        print(f"  Print Area Image IDs: {pa_images}")
    except Exception as e:
        print(f"\n  ID: {pid} — Error: {e}")
