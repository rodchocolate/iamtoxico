"""Bake Shopify variant data into data/shopify_variants.json for cart.js.

Pulls the store's public /products.json (paginated, no auth) and writes a
handle-keyed map of variants (Shopify variant id, size, price, availability).
cart.js loads this file to run the on-site size picker + cart; checkout is a
cart permalink built from these variant ids.

Run after publishing/unpublishing products, then deploy:
  python3 scripts/sync_shopify_variants.py
"""
from __future__ import annotations

import json
import pathlib
import sys
import urllib.request

SHOP = "https://iamtoxico.myshopify.com"
OUT = pathlib.Path(__file__).resolve().parent.parent / "data" / "shopify_variants.json"


def fetch_all_products() -> list[dict]:
    products, page = [], 1
    while True:
        url = f"{SHOP}/products.json?limit=250&page={page}"
        with urllib.request.urlopen(url, timeout=30) as r:
            batch = json.load(r).get("products", [])
        products.extend(batch)
        if len(batch) < 250:
            return products
        page += 1


def size_label(variant: dict) -> str:
    # option1 is the size axis on apparel; single-variant goods say "Default Title"
    label = (variant.get("option1") or variant.get("title") or "").strip()
    return "" if label.lower() == "default title" else label


def main() -> int:
    products = fetch_all_products()
    out: dict[str, dict] = {}
    for p in products:
        variants = [
            {
                "id": v["id"],
                "s": size_label(v),
                "p": v.get("price", ""),
                "a": bool(v.get("available", True)),
            }
            for v in p.get("variants", [])
        ]
        if not variants:
            continue
        out[p["handle"]] = {
            "t": p.get("title", p["handle"]),
            "v": variants,
        }
    OUT.write_text(
        json.dumps({"shop": SHOP, "products": out}, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    print(f"{len(out)} products -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
