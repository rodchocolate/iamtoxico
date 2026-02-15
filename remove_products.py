import json
import os

file_path = '/Users/jasonjenkins/Desktop/alpha/toxico/data/catalog.json'
ids_to_remove = [
    'printify-6929b4c9e07f035cf5020be6',
    'new-balance-990v6',
    'new-balance-550',
    'printify-68585bdd2c35f6107c04a28f',
    'printify-6929f81786aa459b86021fb1',
    'printify-690d4152cbcaca97250c276b'
]

try:
    with open(file_path, 'r') as f:
        data = json.load(f)

    original_count = len(data['products'])
    data['products'] = [p for p in data['products'] if p['id'] not in ids_to_remove]
    new_count = len(data['products'])
    removed_count = original_count - new_count

    with open(file_path, 'w') as f:
        json.dump(data, f, indent=2)

    print(f"Successfully removed {removed_count} items.")
    print(f"Original count: {original_count}")
    print(f"New count: {new_count}")

except Exception as e:
    print(f"Error: {e}")
