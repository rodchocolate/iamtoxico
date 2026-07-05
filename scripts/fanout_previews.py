"""Fan the 6 original designs onto bag + hoodie-candidate templates (scratch
shop). Idempotent: skips titles that already exist."""
import sys, time
from concurrent.futures import ThreadPoolExecutor

REPO = "/Users/melodiclabs/hermes-runtime/rooot/iamtoxico.com"
sys.path.insert(0, REPO + "/scripts"); sys.path.insert(0, REPO + "/shopify-app")
from resolve_printify_sources import load_printify_env
from printify_connector import PrintifyConnector
import new_drop

SCRATCH = 22994552
DESIGNS = {
    "Arctic River": "6929eeb040561a7af702832b",
    "Cyan Glow": "6929f8f976f5a88f2f06dbd6",
    "Frozen Sky": "6929ef8b586758307ea66554",
    "Hold Cards": "6929f0ed76f5a88f2f06db08",
    "Hot Oil": "6929f7a430ad44ebe1ea721a",
    "Toxico": "685855589b0b5c3f611d779f",
}
SOURCES = {
    # bags — numbering matches the live "01/02" products' layouts
    "Backpack 01": "6a07958c8aacac07a3008be7",
    "Backpack 02": "6a07958dd5a67e96790937f4",
    "Leather Travel Bag 01": "6a07958014136fc0de0e016f",
    "Leather Travel Bag 02": "6a07958a1f2208ca9b041c0c",
    "Laundry Bag": "6a0795885d21d707320f7881",
    "Sling Bag": "6a0795860852663cf009cb91",
    # hoodie template candidates
    "Pullover Hoodie": "6a0795bd44285bcfb5080ace",
    "Hooded Long Sleeve Tee": "6a0795b3ff25cd2032040457",
    "Warmup Hoodie": "6a0795a79f1ed1ddb00ecc29",
}

def slug(s):
    return "-".join(s.lower().split())

def main():
    load_printify_env()
    c = PrintifyConnector()
    existing = {p["title"] for p in c.get_products(SCRATCH)}
    details = {label: c.get_product(SCRATCH, pid) for label, pid in SOURCES.items()}

    jobs = []
    for design, image_id in DESIGNS.items():
        for label, detail in details.items():
            title = f"{design} — {label}"
            if title in existing:
                jobs.append((title, None)); continue
            payload = {
                "title": title,
                "description": f"{design} on {label} — variant preview.",
                "blueprint_id": detail["blueprint_id"],
                "print_provider_id": detail["print_provider_id"],
                "variants": new_drop.build_variants(detail),
                "print_areas": new_drop.build_print_areas_with_image(detail, image_id),
                "tags": ["toxico", "variant-preview", slug(design), slug(label)],
            }
            jobs.append((title, payload))

    def make(job):
        title, payload = job
        if payload is None:
            return f"skip (exists): {title}"
        try:
            p = c.create_product(SCRATCH, payload)
            return f"created {p['id']}: {title}"
        except Exception as e:
            return f"FAILED {title}: {e}"

    t0 = time.monotonic()
    with ThreadPoolExecutor(max_workers=8) as ex:
        for line in ex.map(make, jobs):
            print(line, flush=True)
    print(f"done in {time.monotonic()-t0:.0f}s")

main()
