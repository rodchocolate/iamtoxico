#!/usr/bin/env python3
"""Export a Gemini-friendly rename brief for Printify products.

The brief combines:
- current product titles and external handles
- product mockup URLs from Printify
- uploaded artwork previews
- candidate local source assets recovered from the standing library

This is read-only. Use it to prepare rename suggestions before touching live data.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List

ROOT = Path(__file__).resolve().parent.parent
SHOPIFY_APP = ROOT / "shopify-app"
SCRIPTS = Path(__file__).resolve().parent
if str(SHOPIFY_APP) not in sys.path:
    sys.path.insert(0, str(SHOPIFY_APP))
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from printify_connector import PrintifyConnector
from resolve_printify_sources import (
    build_local_asset_index,
    coerce_uploaded_images,
    extract_print_area_images,
    load_printify_env,
    resolve_uploaded_image_candidates,
)


DEFAULT_IMAGES_ROOT = ROOT / "docs" / "design" / "reference-images"
DEFAULT_LOG_PATH = ROOT / "fetch_images.log"
DEFAULT_OUTPUT_PATH = ROOT / "data" / "rename_brief.json"


def extract_mockup_urls(product_detail: Dict[str, Any], limit: int = 4) -> List[str]:
    urls = []
    for image in product_detail.get("images", []):
        src = image.get("src")
        if src and src not in urls:
            urls.append(src)
        if len(urls) >= limit:
            break
    return urls


def build_rename_record(product_detail: Dict[str, Any],
                        uploaded_images: Dict[str, Dict[str, Any]],
                        asset_index: Dict[str, set[str]]) -> Dict[str, Any]:
    artwork = []
    seen_candidates = []
    seen_paths = set()

    for usage in extract_print_area_images(product_detail):
        upload_record = uploaded_images.get(usage["id"], {})
        candidate_paths = resolve_uploaded_image_candidates(upload_record, asset_index)
        for path in candidate_paths:
            if path not in seen_paths:
                seen_paths.add(path)
                seen_candidates.append(path)

        artwork.append({
            "upload_id": usage["id"],
            "position": usage["position"],
            "file_name": upload_record.get("file_name"),
            "preview_url": upload_record.get("preview_url"),
            "candidate_source_paths": candidate_paths,
        })

    external = product_detail.get("external") or {}
    return {
        "product_id": str(product_detail.get("id", "")),
        "current_title": product_detail.get("title"),
        "external_id": external.get("id"),
        "external_handle": external.get("handle"),
        "blueprint_id": product_detail.get("blueprint_id"),
        "print_provider_id": product_detail.get("print_provider_id"),
        "mockup_urls": extract_mockup_urls(product_detail),
        "artwork": artwork,
        "candidate_source_paths": seen_candidates,
        "rename_prompt": (
            "Propose 3 concise product names based on the source artwork and mockups. "
            "Avoid generic filler like Copy Of. Prefer names that feel editorial, memorable, and usable in Shopify."
        ),
    }


def export_rename_brief(connector: PrintifyConnector,
                        shop_id: int,
                        images_root: Path,
                        log_path: Path,
                        product_ids: Iterable[str] | None = None) -> Dict[str, Any]:
    asset_index = build_local_asset_index(images_root, log_path)
    uploaded_images = {
        str(item.get("id")): item
        for item in coerce_uploaded_images(connector.get_uploaded_images())
        if item.get("id")
    }

    selected_ids = {str(product_id) for product_id in product_ids or []}
    products = connector.get_products(shop_id)
    if selected_ids:
        products = [product for product in products if str(product.get("id")) in selected_ids]

    records = []
    for product in products:
        product_id = str(product.get("id"))
        detail = connector.get_product(shop_id, product_id)
        records.append(build_rename_record(detail, uploaded_images, asset_index))

    return {
        "shop_id": shop_id,
        "record_count": len(records),
        "images_root": str(images_root),
        "log_path": str(log_path),
        "records": records,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--shop-id",
        type=int,
        default=int(os.getenv("PRINTIFY_SHOP_ID", "22994552")),
        help="Printify shop ID to inspect (default: env PRINTIFY_SHOP_ID or 22994552)",
    )
    parser.add_argument(
        "--product-id",
        dest="product_ids",
        action="append",
        default=[],
        help="Optional product ID to export. Repeat for multiple products.",
    )
    parser.add_argument(
        "--images-root",
        type=Path,
        default=DEFAULT_IMAGES_ROOT,
        help="Local standing-library root to scan for source images.",
    )
    parser.add_argument(
        "--log-path",
        type=Path,
        default=DEFAULT_LOG_PATH,
        help="fetch_images.log path used to re-link staging assets to source files.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="JSON file to write the rename brief to.",
    )
    return parser.parse_args()


def main() -> int:
    load_printify_env()
    connector = PrintifyConnector()
    args = parse_args()
    brief = export_rename_brief(
        connector=connector,
        shop_id=args.shop_id,
        images_root=args.images_root,
        log_path=args.log_path,
        product_ids=args.product_ids,
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as output_file:
        json.dump(brief, output_file, indent=2)
        output_file.write("\n")

    print(f"Wrote rename brief for {brief['record_count']} product(s) to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())