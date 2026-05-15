#!/usr/bin/env python3
"""Fan a single source image across all 33 templates in data/templates.json
and emit a dated preview page at project root: YYYYMMDD_N.html.

Mirrors preview.html's exact chrome (dark/graffiti bg, Space Grotesk header,
3-col card grid with front/back hover). Each card is a different template
mockup of the same source image, rendered by Printify.

Preview-slot pattern: one persistent product per template is kept in the
staging shop, tagged preview-slot-<template-hash>. On each drop the slot's
print areas are mutated in place to use the new image; Printify re-renders
mockups; the script polls until mockup URLs are available.

Usage:
    python3 scripts/new_drop.py /path/to/image.png
    python3 scripts/new_drop.py /path/to/image.png --dry-run
    python3 scripts/new_drop.py /path/to/image.png --no-wait
"""

from __future__ import annotations

import argparse
import base64
import copy
import json
import re
import sys
import time
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import requests

ROOT = Path(__file__).resolve().parent.parent
SHOPIFY_APP = ROOT / "shopify-app"

if str(SHOPIFY_APP) not in sys.path:
    sys.path.insert(0, str(SHOPIFY_APP))

from printify_connector import PrintifyConnector  # type: ignore
from resolve_printify_sources import load_printify_env  # type: ignore


DEFAULT_TEMPLATES = ROOT / "data" / "templates.json"
DEFAULT_STAGING_SHOP_ID = 22994552
DEFAULT_LIVE_SHOP_ID = 26651009

FRONT_LABELS = (
    "front", "person-front-1", "person-front-2", "person-front",
    "man-front", "on-person-front", "on-person-1-front", "lifestyle-man",
)
BACK_LABELS = (
    "back", "person-back", "man-back", "on-person-back",
    "on-person-1-back", "lifestyle-woman", "context", "right", "left",
)

POLL_INTERVAL_SEC = 6
POLL_TIMEOUT_SEC = 600


def upload_image_from_file(api_key: str, file_path: Path) -> Dict[str, Any]:
    """Upload a local image to Printify via base64. Returns the upload record
    (includes the new image id used in print_areas)."""
    contents = base64.b64encode(file_path.read_bytes()).decode("ascii")
    response = requests.post(
        "https://api.printify.com/v1/uploads/images.json",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={"file_name": file_path.name, "contents": contents},
        timeout=120,
    )
    response.raise_for_status()
    return response.json()


def clean_title(raw: str) -> str:
    cleaned = re.sub(r"^(Copy of\s+)+", "", raw or "", flags=re.IGNORECASE)
    cleaned = cleaned.replace("(AOP)", "").strip()
    return cleaned or "Untitled"


def derive_card_title(members: Sequence[Dict[str, Any]]) -> str:
    candidates = [clean_title(m.get("title", "")) for m in members]
    for c in candidates:
        if c and not (c or "").lower().startswith("copy of"):
            return c
    return candidates[0] if candidates else "Untitled"


def short_meta(template: Dict[str, Any]) -> str:
    layout = template.get("layout", "")
    placements = re.findall(r"([a-z_]+)(?:/[a-z_]+)*@", layout)
    if not placements:
        return "single"
    seen: set = set()
    ordered: List[str] = []
    for placement in placements:
        if placement not in seen:
            ordered.append(placement)
            seen.add(placement)
    return "/".join(ordered[:3])


def pick_member(members: Sequence[Dict[str, Any]], staging_shop_id: int) -> Dict[str, Any]:
    staging = [m for m in members if m.get("shop_id") == staging_shop_id]
    if staging:
        non_copy = [
            m for m in staging
            if not (m.get("title") or "").lower().startswith("copy of")
        ]
        return (non_copy or staging)[0]
    return members[0]


def select_mockup_url(images: Sequence[Dict[str, Any]], labels: Sequence[str]) -> str:
    for label in labels:
        token = f"camera_label={label}"
        for image in images:
            src = str(image.get("src", ""))
            if token in src:
                return src
    for image in images:
        src = str(image.get("src", ""))
        if src:
            return src
    return ""


def build_print_areas_with_image(
    source_detail: Dict[str, Any],
    new_image_id: str,
) -> List[Dict[str, Any]]:
    """Clone the source product's print_areas, swapping every placeholder's
    image id for new_image_id while preserving x/y/scale/angle/pattern."""
    areas: List[Dict[str, Any]] = []
    for print_area in source_detail.get("print_areas", []):
        placeholders: List[Dict[str, Any]] = []
        for placeholder in print_area.get("placeholders", []):
            new_images: List[Dict[str, Any]] = []
            for image in placeholder.get("images", []):
                if "-" in str(image.get("id", "")):
                    continue
                entry: Dict[str, Any] = {"id": new_image_id}
                for key in ("x", "y", "scale", "angle", "pattern"):
                    if key in image:
                        entry[key] = copy.deepcopy(image[key])
                new_images.append(entry)
            if new_images:
                placeholders.append({
                    "position": placeholder["position"],
                    "images": new_images,
                })
        if placeholders:
            areas.append({
                "variant_ids": list(print_area.get("variant_ids", [])),
                "placeholders": placeholders,
            })
    return areas


def build_variants(source_detail: Dict[str, Any]) -> List[Dict[str, Any]]:
    variants: List[Dict[str, Any]] = []
    for variant in source_detail.get("variants", []):
        if not variant.get("is_available", True):
            continue
        entry: Dict[str, Any] = {
            "id": variant["id"],
            "price": variant.get("price", 0),
            "is_enabled": bool(variant.get("is_enabled", True)),
        }
        if variant.get("is_default"):
            entry["is_default"] = True
        variants.append(entry)
    return variants


def find_slot(products: Sequence[Dict[str, Any]], slot_tag: str) -> Optional[Dict[str, Any]]:
    for product in products:
        if slot_tag in (product.get("tags") or []):
            return product
    return None


def ensure_slot(
    connector: PrintifyConnector,
    staging_shop_id: int,
    template: Dict[str, Any],
    source_detail: Dict[str, Any],
    new_image_id: str,
    slot_tag: str,
    drop_tag: str,
    existing_staging_products: List[Dict[str, Any]],
) -> Dict[str, Any]:
    print_areas = build_print_areas_with_image(source_detail, new_image_id)
    title_base = derive_card_title(template["members"])
    tags = ["toxico", "drop-preview", slot_tag, drop_tag]
    existing = find_slot(existing_staging_products, slot_tag)
    if existing:
        update_payload = {
            "title": f"{title_base} — drop slot",
            "print_areas": print_areas,
            "tags": tags,
        }
        return connector.update_product(staging_shop_id, existing["id"], update_payload)
    create_payload = {
        "title": f"{title_base} — drop slot",
        "description": f"Auto-generated preview slot for template {template['hash']}.",
        "blueprint_id": template["blueprint_id"],
        "print_provider_id": template["print_provider_id"],
        "variants": build_variants(source_detail),
        "print_areas": print_areas,
        "tags": tags,
    }
    return connector.create_product(staging_shop_id, create_payload)


def wait_for_mockups(
    connector: PrintifyConnector,
    shop_id: int,
    product_id: str,
    timeout_sec: int = POLL_TIMEOUT_SEC,
    interval_sec: int = POLL_INTERVAL_SEC,
) -> Dict[str, Any]:
    start = time.monotonic()
    while True:
        product = connector.get_product(shop_id, product_id)
        images = product.get("images") or []
        if any(image.get("src") for image in images):
            return product
        if time.monotonic() - start > timeout_sec:
            return product
        time.sleep(interval_sec)


def next_output_path(root: Path, today_str: str) -> Path:
    n = 1
    while True:
        candidate = root / f"{today_str}_{n}.html"
        if not candidate.exists():
            return candidate
        n += 1


PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>toxico — {date_label} drop #{n}</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600&display=swap');
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}

  body {{
    font-family: 'Space Grotesk', sans-serif;
    color: #fff;
    background: #0b0b0b url('bg-graffiti-10.jpg') center center / cover no-repeat fixed;
    min-height: 100vh;
  }}
  body::before {{
    content: '';
    position: fixed; inset: 0;
    background: rgba(0,0,0,.55);
    z-index: 0;
  }}
  header, main, footer {{ position: relative; z-index: 1; }}

  header {{
    padding: 1.5rem 2rem;
    display: flex; align-items: center; justify-content: space-between;
    max-width: 1280px; margin: 0 auto;
  }}
  header h1 {{
    font-size: 1.4rem; font-weight: 600;
    letter-spacing: .06em; text-transform: lowercase;
  }}
  .badge {{
    background: rgba(255,200,0,.15); color: #ffc800;
    font-size: .7rem; font-weight: 600; text-transform: uppercase;
    padding: .3em .7em; border-radius: 6px; letter-spacing: .08em;
  }}

  main {{ padding: 1rem 2rem 4rem; max-width: 1280px; margin: 0 auto; }}

  #grid {{
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 1.4rem;
  }}

  .card {{
    background: rgba(255,255,255,.06);
    border: 1px solid rgba(255,255,255,.1);
    border-radius: 12px;
    overflow: hidden;
    transition: transform .25s, border-color .25s;
    position: relative;
  }}
  .card:hover {{
    transform: translateY(-4px);
    border-color: rgba(255,255,255,.25);
  }}
  .card .img-wrap {{
    position: relative;
    width: 100%; aspect-ratio: 1;
    overflow: hidden; background: #1a1a1a;
  }}
  .card .img-wrap img {{
    width: 100%; height: 100%; object-fit: cover;
    transition: opacity .3s;
  }}
  .card .img-wrap img.back {{
    position: absolute; inset: 0; opacity: 0;
  }}
  .card:hover .img-wrap img.front {{ opacity: 0; }}
  .card:hover .img-wrap img.back  {{ opacity: 1; }}

  .card.empty .img-wrap {{
    display: flex; align-items: center; justify-content: center;
    color: rgba(255,255,255,.4); font-size: .75rem;
    text-transform: lowercase; letter-spacing: .05em;
  }}

  .card .info {{ padding: .9rem 1rem; }}
  .card .title {{
    font-size: .85rem; font-weight: 600;
    margin-bottom: .2rem;
  }}
  .card .meta {{
    font-size: .7rem; opacity: .65;
    text-transform: lowercase;
  }}

  footer {{
    text-align: center; padding: 1rem;
    font-size: .7rem; opacity: .5;
    max-width: 1280px; margin: 0 auto;
  }}

  @media (max-width: 600px) {{
    #grid {{
      grid-template-columns: repeat(2, 1fr);
      gap: .8rem;
    }}
    .card .info {{ padding: .6rem .7rem; }}
    .card .title {{ font-size: .78rem; }}
  }}
</style>
</head>
<body>

<header>
  <h1>toxico — {date_label} drop #{n}</h1>
  <span class="badge">drop preview</span>
</header>

<main>
  <div id="grid"></div>
</main>

<footer>&copy; 2026 toxico &mdash; drop {date_label} #{n} &mdash; not public</footer>

<script>
const P = [
{entries}
];

const grid = document.getElementById('grid');

P.forEach(p => {{
  const c = document.createElement('div');
  c.className = 'card' + (p.f ? '' : ' empty');
  const imgs = p.f
    ? '<img class="front" src="' + p.f + '" alt="' + p.t + '" loading="lazy">' +
      (p.b ? '<img class="back" src="' + p.b + '" alt="' + p.t + ' back" loading="lazy">' : '')
    : 'mockup pending';
  c.innerHTML =
    '<div class="img-wrap">' + imgs + '</div>' +
    '<div class="info">' +
      '<div class="title">' + p.t + '</div>' +
      '<div class="meta">' + p.y + '</div>' +
    '</div>';
  grid.appendChild(c);
}});
</script>
</body>
</html>
"""


def _esc(value: str) -> str:
    return (value or "").replace("\\", "\\\\").replace('"', '\\"')


def format_entry(card: Dict[str, str]) -> str:
    return (
        "  {"
        f't:"{_esc(card["t"])}", '
        f'y:"{_esc(card["y"])}", '
        f'f:"{_esc(card["f"])}", '
        f'b:"{_esc(card["b"])}"'
        "},"
    )


def render_html(cards: Sequence[Dict[str, str]], date_label: str, n: int) -> str:
    entries = "\n".join(format_entry(c) for c in cards)
    return PAGE_TEMPLATE.format(date_label=date_label, n=n, entries=entries)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", type=Path, help="Source image (PNG/JPEG)")
    parser.add_argument("--templates", type=Path, default=DEFAULT_TEMPLATES)
    parser.add_argument("--staging-shop-id", type=int, default=DEFAULT_STAGING_SHOP_ID)
    parser.add_argument("--live-shop-id", type=int, default=DEFAULT_LIVE_SHOP_ID)
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Plan and emit HTML with placeholder cards; no Printify writes",
    )
    parser.add_argument(
        "--no-wait", action="store_true",
        help="Skip polling for mockups; emit HTML with placeholders where missing",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.image.is_file():
        print(f"ERROR: image not found: {args.image}", file=sys.stderr)
        return 2

    templates = json.loads(args.templates.read_text(encoding="utf-8"))
    print(f"loaded {len(templates)} templates from {args.templates.name}", flush=True)

    today_str = date.today().strftime("%Y%m%d")
    output_path = next_output_path(ROOT, today_str)
    n = int(output_path.stem.split("_")[1])
    drop_tag = f"drop-{today_str}-{n}"
    print(f"output: {output_path.name} (drop tag: {drop_tag})", flush=True)

    if args.dry_run:
        cards = [
            {
                "t": derive_card_title(t["members"]),
                "y": short_meta(t),
                "f": "",
                "b": "",
            }
            for t in templates
        ]
        output_path.write_text(render_html(cards, today_str, n), encoding="utf-8")
        print(f"dry-run wrote {output_path}", flush=True)
        return 0

    load_printify_env()
    connector = PrintifyConnector()
    api_key = connector.api_key

    print(f"uploading {args.image.name} to Printify...", flush=True)
    upload = upload_image_from_file(api_key, args.image)
    new_image_id = upload["id"]
    print(f"image id: {new_image_id}", flush=True)

    existing_staging = connector.get_products(args.staging_shop_id)
    print(f"staging shop has {len(existing_staging)} products before drop", flush=True)

    slots: List[Dict[str, Any]] = []

    for index, template in enumerate(templates, 1):
        slot_tag = f"preview-slot-{template['hash']}"
        title = derive_card_title(template["members"])
        meta = short_meta(template)
        try:
            member = pick_member(template["members"], args.staging_shop_id)
            source_detail = connector.get_product(member["shop_id"], member["product_id"])
            slot = ensure_slot(
                connector=connector,
                staging_shop_id=args.staging_shop_id,
                template=template,
                source_detail=source_detail,
                new_image_id=new_image_id,
                slot_tag=slot_tag,
                drop_tag=drop_tag,
                existing_staging_products=existing_staging,
            )
            slots.append({
                "id": str(slot["id"]),
                "title": title,
                "meta": meta,
                "hash": template["hash"],
            })
            print(
                f"[{index:02d}/{len(templates)}] slot_ready\t{template['hash']}\t{slot['id']}\t{title}",
                flush=True,
            )
        except Exception as exc:  # noqa: BLE001
            print(
                f"[{index:02d}/{len(templates)}] skip\t{template['hash']}\t{title}\t{exc}",
                flush=True,
            )
            slots.append({"id": "", "title": title, "meta": meta, "hash": template["hash"]})

    cards: List[Dict[str, str]] = []
    for index, slot in enumerate(slots, 1):
        if not slot["id"] or args.no_wait:
            cards.append({"t": slot["title"], "y": slot["meta"], "f": "", "b": ""})
            continue
        product = wait_for_mockups(connector, args.staging_shop_id, slot["id"])
        images = product.get("images") or []
        front = select_mockup_url(images, FRONT_LABELS)
        back = select_mockup_url(images, BACK_LABELS)
        cards.append({"t": slot["title"], "y": slot["meta"], "f": front, "b": back})
        status = "mockup_ready" if front else "mockup_timeout"
        print(
            f"[{index:02d}/{len(slots)}] {status}\t{slot['id']}\t{slot['title']}",
            flush=True,
        )

    output_path.write_text(render_html(cards, today_str, n), encoding="utf-8")
    print(f"wrote {output_path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
