import json
from pathlib import Path

CATALOG_PATH = Path(__file__).resolve().parent / 'data' / 'catalog.json'
IDS_TO_REMOVE = [
    'printify-6929b4c9e07f035cf5020be6',
    'new-balance-990v6',
    'new-balance-550',
    'printify-68585bdd2c35f6107c04a28f',
    'printify-6929f81786aa459b86021fb1',
    'printify-690d4152cbcaca97250c276b'
]

try:
    with open(CATALOG_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)

    products = data.get('products')
    if not isinstance(products, list):
        raise ValueError('catalog.json is missing a valid products list')

    original_count = len(products)
    data['products'] = [p for p in products if p.get('id') not in IDS_TO_REMOVE]
    new_count = len(data['products'])
    removed_count = original_count - new_count

    with open(CATALOG_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
        f.write('\n')

    print(f"Successfully removed {removed_count} items.")
    print(f"Original count: {original_count}")
    print(f"New count: {new_count}")

except Exception as e:
    print(f"Error: {e}")
