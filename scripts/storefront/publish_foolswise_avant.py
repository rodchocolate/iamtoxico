#!/usr/bin/env python3
"""Publish real avant (hoodie, blueprint 592) products for the 29 foolswise
designs — the site's avant tiles for these were mock images with no product.
Mirrors publish_avant.py (originals), but two-phase to avoid the serial
wait_for_publish stall: create+publish all first, then poll all in one sweep.

    python3 scripts/storefront/publish_foolswise_avant.py ski   # one (test)
    python3 scripts/storefront/publish_foolswise_avant.py all
"""
import base64
import json
import sys
import time
from pathlib import Path

REPO = Path("/Users/melodiclabs/hermes-runtime/rooot/iamtoxico.com")
sys.path.insert(0, str(REPO / "shopify-app"))
sys.path.insert(0, str(REPO / "scripts"))
from printify_connector import PrintifyConnector
import new_drop
import publish_apres_tops as pub

# fw-designs/<num>.png -> design name (mapping confirmed via avant-apres grid)
FOOLSWISE = {
    "01": "Base", "02": "Summer", "03": "Winter", "04": "Spring", "05": "Fall",
    "06": "Birthday", "07": "Nightclub", "08": "Extra", "09": "Stripclub",
    "10": "Casino", "11": "Racetrack", "12": "Srt8", "13": "Ski",
    "14": "Snowboard", "15": "Aspen", "16": "Whistler", "17": "Ibiza",
    "18": "Miami", "19": "Snowbird", "20": "Hollywood", "21": "Kauai",
    "22": "Robben Island", "23": "Oaxaca", "24": "Sedona", "25": "Oregon",
    "26": "Vermentino", "27": "Champagne", "28": "Candlelight", "29": "Botanical",
}
STATE = Path("/tmp/foolswise_avant_published.json")
POLL_TOTAL_SEC = 1800
POLL_INTERVAL_SEC = 30

only = (sys.argv[1] if len(sys.argv) > 1 else "ski").lower()
targets = [(n, d) for n, d in FOOLSWISE.items()
           if only == "all" or d.lower() == only]
if not targets:
    raise SystemExit(f"unknown design {only!r}")

c = PrintifyConnector()
shop = json.load(open(REPO / "data" / "instant_drop.json"))["live_shop_id"]

prods = c.get_products(shop)
src_meta = next(p for p in prods if "hoodie single" in (p.get("title", "") or "").lower()
                and (p.get("external") or {}).get("handle"))
source = c.get_product(shop, src_meta["id"])
price = next((v["price"] for v in source.get("variants", []) if v.get("is_enabled")), 6500)
print(f"source hoodie: {src_meta['title']} | price {price}c", flush=True)

state = json.loads(STATE.read_text()) if STATE.exists() else {}

# phase 1: create + publish everything (no waiting between products)
pending = {}
for num, design in targets:
    slug = "toxico-" + design.lower().replace(" ", "-") + "-avant"
    if slug in state and state[slug].get("url"):
        print(f"[{design}] already: {state[slug]['url']}", flush=True)
        continue
    data = (REPO / "fw-designs" / f"{num}.png").read_bytes()
    up = c._request("POST", "/uploads/images.json",
                    {"file_name": f"{slug}.png",
                     "contents": base64.b64encode(data).decode("ascii")})
    print_areas = new_drop.build_print_areas_with_image(source, up["id"])
    variants = pub.build_variants(source.get("variants", []), price)
    payload = {"title": f"Toxico {design} Avant", "description": f"{design} — iamtoxico.",
               "blueprint_id": source["blueprint_id"],
               "print_provider_id": source["print_provider_id"],
               "variants": variants, "print_areas": print_areas,
               "tags": ["toxico", "avant", "foolswise-avant", slug]}
    product = c.create_product(shop, payload)
    c.publish_product(shop, product["id"], {"title": True, "description": True,
                                            "images": True, "variants": True, "tags": True,
                                            "keyFeatures": True, "shipping_template": True})
    pending[slug] = {"design": design, "id": product["id"]}
    print(f"[{design}] created {product['id']}, publish fired", flush=True)

# phase 2: one polling sweep over all pending until handle + front mockup
deadline = time.monotonic() + POLL_TOTAL_SEC
while pending and time.monotonic() < deadline:
    done = []
    for slug, meta in pending.items():
        try:
            product = c.get_product(shop, meta["id"])
        except Exception:
            continue
        handle = (product.get("external") or {}).get("handle") or ""
        fimg = next((im.get("src") for im in (product.get("images") or [])
                     if im.get("is_default") or im.get("position") == "front"), "")
        if handle and fimg:
            url = handle if handle.startswith("http") else f"https://shop.iamtoxico.com/products/{handle}"
            state[slug] = {"design": meta["design"], "id": meta["id"],
                           "handle": handle, "url": url, "img": fimg}
            STATE.write_text(json.dumps(state, indent=1))
            done.append(slug)
            print(f"[{meta['design']}] PUBLISHED -> {url}", flush=True)
    for s in done:
        del pending[s]
    if pending:
        time.sleep(POLL_INTERVAL_SEC)

if pending:
    print(f"TIMEOUT waiting on: {sorted(pending)}", flush=True)
print("FOOLSWISE AVANT DONE", flush=True)
