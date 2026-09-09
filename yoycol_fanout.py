"""Yoycol harvest + fan-out — templates → store-product payloads.

Step 2 of YOYCOL_DESIGNER_AUTOMATION_SPEC (iCloud rooot): pure-API path that
turns saved designer templates (designCodes) into store-product mappings.
No browser automation involved; artwork creation stays in the web designer.

Stages:
  harvest   pull all product_templates + per-blank variants (skuCode, size,
            color, base salesPrice), download preview images, write
            ~/hermes-runtime/state/yoycol/harvest.json
  plan      build POST /self_store/products payloads from the harvest —
            writes plan.json, prints a summary. Never calls the API.
  push      dry-run by default (prints what WOULD be created). --live POSTs,
            skipping any storeProductId that already exists (idempotent).
            All products are created with visibility=false — nothing goes
            publicly visible until reviewed.

Pricing: retail = base salesPrice x PRICE_MULT rounded up to a whole dollar,
unless the blank's spuCode has an override in PRICE_MAP. Placeholder rule
until the margins worker exists — review plan.json before --live.

Titles: display titles are Jason's wording (same policy as templates.json
display_name). Until TITLE_MAP is filled in, titles fall back to
"<designCode> <blank spuCode>" so nothing assistant-authored reaches a
listing. Fill TITLE_MAP, re-run plan, then push.

Usage:
  python3 yoycol_fanout.py harvest
  python3 yoycol_fanout.py plan
  python3 yoycol_fanout.py push [--live]
"""
from __future__ import annotations

import json
import math
import os
import sys
import urllib.request
from pathlib import Path

import yoycol_api as api

STATE_DIR = Path.home() / "hermes-runtime" / "state" / "yoycol"
PREVIEW_DIR = STATE_DIR / "previews"
HARVEST = STATE_DIR / "harvest.json"
PLAN = STATE_DIR / "plan.json"

PRICE_MULT = 4.0            # base x4 ≈ 75% margin, matches the live line
PRICE_MAP: dict[str, float] = {
    # "3MPXDL48": 78.0,     # per-blank spuCode retail overrides go here
}
TITLE_MAP: dict[str, str] = {
    # "PDKYH": "…",         # designCode → Jason's display title
}


def _retail(base: float, spu: str) -> float:
    if spu in PRICE_MAP:
        return PRICE_MAP[spu]
    return float(math.ceil(base * PRICE_MULT))


def _paged(path: str, key: str = "records"):
    page = 1
    while True:
        d = api.get(path, {"page": page, "pageSize": 100})
        recs = d.get(key) or d.get("data", {}).get(key) or []
        yield from recs
        if page >= int(d.get("pages") or d.get("data", {}).get("pages") or 1):
            return
        page += 1


def harvest() -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    templates = list(_paged("/product_templates"))
    blanks: dict[int, dict] = {}
    for t in templates:
        pid = t["productId"]
        if pid not in blanks:
            d = api.get(f"/catalog/products/{pid}")
            blanks[pid] = d.get("data", d)
    out = {"templates": [], "blanks": {}}
    for pid, d in blanks.items():
        prod = d.get("product", d)
        variants = d.get("variants", [])
        out["blanks"][str(pid)] = {
            "spuCode": prod.get("spuCode"),
            "name": prod.get("name"),
            "variantCount": prod.get("variantCount"),
            "variants": [
                {
                    "skuCode": v["skuCode"],
                    "size": v.get("size"),
                    "color": v.get("color"),
                    "basePrice": v.get("salesPrice"),
                    "currency": v.get("currency", "USD"),
                    "online": v.get("onlineStatus", True),
                }
                for v in variants
            ],
        }
    for t in templates:
        prev_url = t.get("previewImage") or ""
        prev_path = ""
        if prev_url:
            prev_path = str(PREVIEW_DIR / f"{t['designCode']}.jpg")
            if not os.path.exists(prev_path):
                try:
                    urllib.request.urlretrieve(prev_url, prev_path)
                except OSError as e:
                    print(f"  preview download failed for {t['designCode']}: {e}", file=sys.stderr)
                    prev_path = ""
        out["templates"].append(
            {
                "designCode": t["designCode"],
                "designName": t.get("designName"),
                "templateId": t.get("id"),
                "productId": t["productId"],
                "productName": t.get("productName"),
                "previewUrl": prev_url,
                "previewLocal": prev_path,
                "createdAt": t.get("createdAt"),
            }
        )
    HARVEST.write_text(json.dumps(out, indent=1, ensure_ascii=False))
    print(f"harvested {len(out['templates'])} templates across {len(blanks)} blanks -> {HARVEST}")


def plan() -> None:
    h = json.loads(HARVEST.read_text())
    payloads = []
    missing_titles = []
    for t in h["templates"]:
        blank = h["blanks"][str(t["productId"])]
        code = t["designCode"]
        title = TITLE_MAP.get(code)
        if not title:
            title = f"{code} {blank['spuCode']}"
            missing_titles.append(code)
        variants = [v for v in blank["variants"] if v["online"]]
        payloads.append(
            {
                "storeProductId": f"yoycol-{code}",
                "title": title,
                "spuCode": f"yoycol-{code}",
                "handle": f"yoycol-{code.lower()}",
                "image": t["previewUrl"],
                "visibility": False,
                "isThird": True,
                "variants": [
                    {
                        "variantId": f"yoycol-{code}-{v['skuCode']}",
                        "title": " / ".join(x for x in (v["color"], v["size"]) if x),
                        "skuCode": v["skuCode"],
                        "designCode": code,
                        "retailPrice": f"{_retail(v['basePrice'], blank['spuCode']):.2f}",
                        "image": t["previewUrl"],
                    }
                    for v in variants
                ],
            }
        )
    PLAN.write_text(json.dumps(payloads, indent=1, ensure_ascii=False))
    print(f"planned {len(payloads)} store products -> {PLAN}")
    for p in payloads:
        lo = min(float(v["retailPrice"]) for v in p["variants"])
        hi = max(float(v["retailPrice"]) for v in p["variants"])
        rng = f"${lo:.0f}" if lo == hi else f"${lo:.0f}-{hi:.0f}"
        print(f"  {p['storeProductId']}: {len(p['variants'])} variants, retail {rng}  '{p['title']}'")
    if missing_titles:
        print(f"NOTE: {len(missing_titles)} placeholder titles (fill TITLE_MAP): {', '.join(missing_titles)}")


def push(live: bool) -> None:
    payloads = json.loads(PLAN.read_text())
    existing = {p.get("storeProductId") for p in _paged("/self_store/products")}
    todo = [p for p in payloads if p["storeProductId"] not in existing]
    skipped = len(payloads) - len(todo)
    if skipped:
        print(f"skipping {skipped} already-pushed products")
    if not live:
        for p in todo:
            print(f"DRY RUN would create {p['storeProductId']} ({len(p['variants'])} variants)")
        print(f"dry run only — rerun with --live to create {len(todo)} store products (visibility=false)")
        return
    for p in todo:
        r = api.request("POST", "/self_store/products", body=p)
        print(f"created {p['storeProductId']}: {json.dumps(r)[:120]}")


def _main() -> int:
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "harvest":
        harvest()
    elif cmd == "plan":
        plan()
    elif cmd == "push":
        push("--live" in sys.argv[2:])
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
