#!/usr/bin/env python3
"""Fix the 6 avant hoodies: rebuild print-areas KEEPING the pocket text raster
(keep_image_ids) so the pocket shows the text label, not a design swatch.
Updates the existing products in place (same handle) + republishes."""
import json, base64, sys
from pathlib import Path
REPO = Path("/Users/melodiclabs/hermes-runtime/rooot/iamtoxico.com")
sys.path.insert(0, str(REPO / "shopify-app")); sys.path.insert(0, str(REPO / "scripts"))
from printify_connector import PrintifyConnector
import new_drop, publish_apres_tops as pub

ORIG = {"Arctic River": "bg-graffiti-2.jpg", "Cyan Glow": "pattern.png",
        "Frozen Sky": "bg-graffiti-12.jpg", "Hold Cards": "bg-graffiti-5.jpg",
        "Hot Oil": "bg-graffiti-1.jpg", "Toxico": "toxico.png"}
c = PrintifyConnector()
cfg = json.load(open(REPO / "data" / "instant_drop.json")); shop = cfg["live_shop_id"]
POCKET_TEXT = cfg["pocket_text_image_id"]
prods = c.get_products(shop)
src = next(p for p in prods if "hoodie single" in (p.get("title", "") or "").lower()
          and (p.get("external") or {}).get("handle"))
source = c.get_product(shop, src["id"])
price = next((v["price"] for v in source.get("variants", []) if v.get("is_enabled")), 12000)
state = json.load(open("/tmp/avant_published.json"))
print(f"keeping pocket text {POCKET_TEXT}; updating {len(state)} avant products", flush=True)

for slug, v in state.items():
    design = v["design"]
    data = (REPO / ORIG[design]).read_bytes()
    up = c._request("POST", "/uploads/images.json",
                    {"file_name": f"{slug}.png", "contents": base64.b64encode(data).decode("ascii")})
    print_areas = new_drop.build_print_areas_with_image(source, up["id"], keep_image_ids=[POCKET_TEXT])
    variants = pub.build_variants(source.get("variants", []), price)
    payload = {"title": f"{design} Avant", "description": f"{design} — iamtoxico.",
               "blueprint_id": source["blueprint_id"], "print_provider_id": source["print_provider_id"],
               "variants": variants, "print_areas": print_areas,
               "tags": ["toxico", "avant", "originals-avant", slug]}
    c.update_product(shop, v["id"], payload)
    c.publish_product(shop, v["id"], {"title": True, "description": True, "images": True,
                                      "variants": True, "tags": True, "keyFeatures": True,
                                      "shipping_template": True})
    p = pub.wait_for_publish(c, shop, v["id"])
    for im in (p.get("images") or []):
        if im.get("is_default") or im.get("position") == "front":
            v["img"] = im.get("src"); break
    print(f"  [{design}] pocket-text fixed + republished", flush=True)

json.dump(state, open("/tmp/avant_published.json", "w"), indent=1)
print("POCKET FIX DONE", flush=True)
