#!/usr/bin/env python3
"""Publish avant (hoodie, blueprint 592) products for the 6 originals, reusing
instant_drop's proven Printify helpers. Design source = each original's confirmed
pattern file. Run with an arg to publish ONE (test) or 'all'."""
import json, base64, sys, time
from pathlib import Path
REPO = Path("/Users/melodiclabs/hermes-runtime/rooot/iamtoxico.com")
sys.path.insert(0, str(REPO / "shopify-app"))
sys.path.insert(0, str(REPO / "scripts"))
from printify_connector import PrintifyConnector
import new_drop
import publish_apres_tops as pub

ORIG = {  # design -> confirmed source pattern (already deployed at site root)
    "Arctic River": "bg-graffiti-2.jpg", "Cyan Glow": "pattern.png",
    "Frozen Sky": "bg-graffiti-12.jpg", "Hold Cards": "bg-graffiti-5.jpg",
    "Hot Oil": "bg-graffiti-1.jpg", "Toxico": "toxico.png",
}
only = sys.argv[1] if len(sys.argv) > 1 else "Arctic River"

c = PrintifyConnector()
cfg = json.load(open(REPO / "data" / "instant_drop.json"))
shop = cfg["live_shop_id"]

# source hoodie (any live "Hoodie Single") -> its print-area layout is the template
prods = c.get_products(shop)
src_meta = next(p for p in prods if "hoodie single" in (p.get("title", "") or "").lower()
                and (p.get("external") or {}).get("handle"))
source = c.get_product(shop, src_meta["id"])
price = next((v["price"] for v in source.get("variants", []) if v.get("is_enabled")), 6500)
print(f"source hoodie: {src_meta['title']} | price {price}c | variants {len(source.get('variants',[]))}", flush=True)

targets = ORIG.items() if only == "all" else [(only, ORIG[only])]
state = {}
sf = Path("/tmp/avant_published.json")
if sf.exists():
    state = json.loads(sf.read_text())

for design, img in targets:
    slug = design.lower().replace(" ", "-") + "-avant"
    if slug in state:
        print(f"[{design}] already: {state[slug]}", flush=True); continue
    data = (REPO / img).read_bytes()
    up = c._request("POST", "/uploads/images.json",
                    {"file_name": f"{slug}.png", "contents": base64.b64encode(data).decode("ascii")})
    image_id = up["id"]
    print_areas = new_drop.build_print_areas_with_image(source, image_id)
    variants = pub.build_variants(source.get("variants", []), price)
    payload = {"title": f"{design} Avant", "description": f"{design} — iamtoxico.",
               "blueprint_id": source["blueprint_id"], "print_provider_id": source["print_provider_id"],
               "variants": variants, "print_areas": print_areas,
               "tags": ["toxico", "avant", "originals-avant", slug]}
    product = c.create_product(shop, payload)
    print(f"[{design}] created {product['id']}, publishing…", flush=True)
    c.publish_product(shop, product["id"], {"title": True, "description": True, "images": True,
                                            "variants": True, "tags": True, "keyFeatures": True,
                                            "shipping_template": True})
    product = pub.wait_for_publish(c, shop, product["id"])
    handle = (product.get("external") or {}).get("handle") or ""
    url = handle if handle.startswith("http") else (f"https://1tap6m-et.myshopify.com/products/{handle}" if handle else "")
    # front mockup
    fimg = ""
    for im in (product.get("images") or []):
        if im.get("is_default") or im.get("position") == "front":
            fimg = im.get("src"); break
    state[slug] = {"design": design, "id": product["id"], "handle": handle, "url": url, "img": fimg}
    sf.write_text(json.dumps(state, indent=1))
    print(f"[{design}] PUBLISHED -> {url}  (mockup {'yes' if fimg else 'pending'})", flush=True)

print("AVANT DONE", flush=True)
