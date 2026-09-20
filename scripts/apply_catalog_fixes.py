#!/usr/bin/env python3
"""Apply approved catalog.json fixes:
 1. Backfill url for the 209(+1 measured=210) matched url-less rows from shopify_variants.json.
 2. Apply 3 Zimmerli price fixes.
 3. Rename 2 duplicate id rows (dedup).
Held/no-action buckets (38 no-handle rows, 19 missing_target page builds,
13 unreproducible malformed, AFF-BX-001) are explicitly NOT touched here.

Usage: python3 apply_catalog_fixes.py --root <path> [--live]
Default is dry-run: prints a diff summary, writes nothing.
"""
from __future__ import annotations
import argparse
import json
import re
import sys
from pathlib import Path


def slugify(name: str) -> str:
    s = name.lower()
    s = s.replace('\u2014', ' ').replace('\u2013', ' ')
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = re.sub(r"-+", "-", s).strip('-')
    return s


PRICE_FIXES = {
    "AFF-ZM-232": 382,
    "AFF-ZM-233": 382,
    "AFF-ZM-234": 216,
}

ID_RENAMES = {
    # (old_id, sku) -> new_id
    ("aff-zimmerli-soft-lounge", "AFF-ZM-232"): "aff-zimmerli-soft-lounge-cloud",
    ("aff-zimmerli-soft-lounge", "AFF-ZM-233"): "aff-zimmerli-soft-lounge-blue-melange",
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--live", action="store_true")
    args = ap.parse_args()

    root = Path(args.root)
    catalog_path = root / "data" / "catalog.json"
    sv_path = root / "data" / "shopify_variants.json"

    catalog = json.loads(catalog_path.read_text())
    sv = json.loads(sv_path.read_text())
    shop = sv["shop"]
    handles = sv["products"]

    prods = catalog["products"]

    url_backfilled = []
    price_fixed = []
    id_renamed = []

    for p in prods:
        # --- 1. URL backfill ---
        if (
            p.get("status") == "active"
            and p.get("source") == "printify"
            and (p.get("url", "") == "" or "url" not in p)
        ):
            slug = slugify(p["name"])
            if slug in handles:
                new_url = f"{shop}/products/{slug}"
                url_backfilled.append((p["id"], p.get("url", "<missing>"), new_url))
                p["url"] = new_url

        # --- 2. Price fixes ---
        sku = p.get("sku")
        if sku in PRICE_FIXES and p.get("price") == 0:
            new_price = PRICE_FIXES[sku]
            price_fixed.append((p["id"], sku, p["price"], new_price))
            p["price"] = new_price

        # --- 3. Id renames (dedup) ---
        key = (p.get("id"), p.get("sku"))
        if key in ID_RENAMES:
            new_id = ID_RENAMES[key]
            id_renamed.append((p["id"], sku, new_id))
            p["id"] = new_id

    print(f"URL backfill matched:      {len(url_backfilled)}")
    print(f"Price fixes applied:       {len(price_fixed)}")
    print(f"Id renames applied:        {len(id_renamed)}")
    print()
    print("-- price fixes --")
    for i, sku, old, new in price_fixed:
        print(f"  {i} ({sku}): {old} -> {new}")
    print("-- id renames --")
    for old_id, sku, new_id in id_renamed:
        print(f"  {old_id} ({sku}) -> {new_id}")
    print("-- sample url backfills (first 10) --")
    for i, old, new in url_backfilled[:10]:
        print(f"  {i}: {old!r} -> {new}")

    if args.live:
        catalog_path.write_text(json.dumps(catalog, indent=2, ensure_ascii=True) + "\n")
        print(f"\nWROTE {catalog_path}")
    else:
        print("\nDRY RUN — no file written. Pass --live to write.")

    return {
        "url_backfilled": len(url_backfilled),
        "price_fixed": len(price_fixed),
        "id_renamed": len(id_renamed),
    }


if __name__ == "__main__":
    main()
