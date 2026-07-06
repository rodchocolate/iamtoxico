#!/usr/bin/env python3
"""Create + publish the style-expansion products on the LIVE shop (26651009),
cloned from the reviewed scratch previews. Approved by Jason 2026-07-06:
6 originals x Hoop Shorts ($80); 6 originals + 14 drop designs x Backpack ($100).
Idempotent: skips live titles that already exist.

    python3 scripts/publish_style_expansion.py
"""
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "shopify-app"))
from resolve_printify_sources import load_printify_env  # noqa: E402
from printify_connector import PrintifyConnector  # noqa: E402

LIVE, SCRATCH = 26651009, 22994552
HOOP_PRICE_CENTS = 8000
BACKPACK_PRICE_CENTS = 10000
ORIGINALS = ["Arctic River", "Cyan Glow", "Frozen Sky", "Hold Cards", "Hot Oil", "Toxico"]
DROPS = ["fwrx", "crispus", "fenway reigns", "art", "jackpot", "cat", "windwards", "dumb",
         "faeded", "woodworking", "Lee canyon", "eddy", "glown", "green"]


def slim(im):
    return {k: im[k] for k in ("id", "x", "y", "scale", "angle", "pattern") if k in im}


def main() -> int:
    load_printify_env()
    c = PrintifyConnector()
    scratch_by_title = {p["title"]: p for p in c.get_products(SCRATCH)}
    live_titles = {p["title"] for p in c.get_products(LIVE)}

    jobs = []
    for d in ORIGINALS:
        jobs.append((f"{d} — Hoop Shorts", f"{d} Hoop Shorts", HOOP_PRICE_CENTS, "hoop"))
        jobs.append((f"{d} — Backpack 01", f"{d} Backpack", BACKPACK_PRICE_CENTS, "backpack"))
    for d in DROPS:
        jobs.append((f"{d} — Backpack 01", f"{d} Backpack", BACKPACK_PRICE_CENTS, "backpack"))

    def make(job):
        src_title, live_title, price_cents, style = job
        if live_title in live_titles:
            return f"skip (exists): {live_title}"
        src = scratch_by_title.get(src_title)
        if not src:
            return f"MISSING SOURCE: {src_title}"
        try:
            d = c.get_product(SCRATCH, src["id"])
            areas = []
            for pa in d["print_areas"]:
                phs = [{"position": ph["position"], "images": [slim(im) for im in ph["images"]]}
                       for ph in pa["placeholders"] if ph.get("images")]
                areas.append({"variant_ids": pa["variant_ids"], "placeholders": phs})
            variants = [{"id": v["id"], "price": price_cents,
                         "is_enabled": bool(v.get("is_enabled", True))}
                        for v in d.get("variants", []) if v.get("is_available", True)]
            p = c.create_product(LIVE, {
                "title": live_title,
                "description": f"{live_title} — toxico.",
                "blueprint_id": d["blueprint_id"],
                "print_provider_id": d["print_provider_id"],
                "variants": variants,
                "print_areas": areas,
                "tags": ["toxico", "style-expansion", style],
            })
            c.publish_product(LIVE, p["id"], {
                "title": True, "description": True, "images": True,
                "variants": True, "tags": True, "keyFeatures": True,
                "shipping_template": True})
            return f"created+published {p['id']}: {live_title}"
        except Exception as e:  # noqa: BLE001
            return f"FAILED {live_title}: {e}"

    t0 = time.monotonic()
    with ThreadPoolExecutor(max_workers=10) as ex:
        for line in ex.map(make, jobs):
            print(line, flush=True)
    print(f"done {time.monotonic() - t0:.0f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
