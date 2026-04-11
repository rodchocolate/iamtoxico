#!/usr/bin/env python3
"""Resolve Printify product image IDs back to candidate local source assets.

This script joins three data sources:
1. Printify product details -> print-area image IDs.
2. Printify uploads API -> uploaded file names and preview URLs.
3. Local standing library + fetch_images.log -> likely local source paths.

It does not mutate any remote state.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, DefaultDict, Dict, Iterable, List, Set
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parent.parent
SHOPIFY_APP = ROOT / "shopify-app"
if str(SHOPIFY_APP) not in sys.path:
    sys.path.insert(0, str(SHOPIFY_APP))

from printify_connector import PrintifyConnector


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff"}
DEFAULT_IMAGES_ROOT = ROOT / "docs" / "design" / "reference-images"
DEFAULT_LOG_PATH = ROOT / "fetch_images.log"
DEFAULT_OUTPUT_PATH = ROOT / "data" / "printify_source_provenance.json"
STAGING_LINE_RE = re.compile(r"^STAGING:\s+(?P<src>.+?)\s+->\s+(?P<dst>.+)$")
HASH_SUFFIX_RE = re.compile(r"__[0-9a-f]{8,}$")


def load_printify_env() -> None:
    env_path = SHOPIFY_APP / ".env"
    if not env_path.is_file():
        return

    with open(env_path, encoding="utf-8") as env_file:
        for raw_line in env_file:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def normalize_asset_key(value: str) -> str:
    stem = Path(value).stem.lower().strip()
    stem = HASH_SUFFIX_RE.sub("", stem)
    stem = re.sub(r"[^a-z0-9]+", "-", stem)
    return stem.strip("-")


def rebase_library_path(raw_path: str, repo_root: Path = ROOT) -> str:
    normalized = raw_path.replace("\\", "/")
    marker = "docs/design/reference-images/"
    if marker not in normalized:
        return raw_path

    suffix = normalized.split(marker, 1)[1]
    rebased = repo_root / "docs" / "design" / "reference-images" / suffix
    return str(rebased)


def parse_staging_log(log_path: Path, repo_root: Path = ROOT) -> Dict[str, Set[str]]:
    mapping: DefaultDict[str, Set[str]] = defaultdict(set)
    if not log_path.is_file():
        return {}

    with open(log_path, encoding="utf-8") as log_file:
        for raw_line in log_file:
            match = STAGING_LINE_RE.match(raw_line.strip())
            if not match:
                continue

            source_path = rebase_library_path(match.group("src"), repo_root)
            staged_path = rebase_library_path(match.group("dst"), repo_root)

            for key in {normalize_asset_key(source_path), normalize_asset_key(staged_path)}:
                if key:
                    mapping[key].add(source_path)

    return {key: set(values) for key, values in mapping.items()}


def build_local_asset_index(images_root: Path,
                            log_path: Path,
                            repo_root: Path = ROOT) -> Dict[str, Set[str]]:
    index: DefaultDict[str, Set[str]] = defaultdict(set)

    if images_root.is_dir():
        for asset_path in images_root.rglob("*"):
            if asset_path.suffix.lower() not in IMAGE_EXTENSIONS:
                continue
            key = normalize_asset_key(str(asset_path))
            if key:
                index[key].add(str(asset_path))

    for key, values in parse_staging_log(log_path, repo_root).items():
        index[key].update(values)

    return {key: set(values) for key, values in index.items()}


def uploaded_image_keys(upload_record: Dict[str, Any]) -> Set[str]:
    keys = set()

    file_name = str(upload_record.get("file_name", "")).strip()
    if file_name:
        key = normalize_asset_key(file_name)
        if key:
            keys.add(key)

    preview_url = str(upload_record.get("preview_url", "")).strip()
    if preview_url:
        basename = Path(unquote(urlparse(preview_url).path)).name
        key = normalize_asset_key(basename)
        if key:
            keys.add(key)

    return keys


def resolve_uploaded_image_candidates(upload_record: Dict[str, Any],
                                      asset_index: Dict[str, Set[str]]) -> List[str]:
    candidates: Set[str] = set()
    for key in uploaded_image_keys(upload_record):
        candidates.update(asset_index.get(key, set()))
    return sorted(candidates)


def coerce_uploaded_images(payload: Any) -> List[Dict[str, Any]]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        data = payload.get("data")
        if isinstance(data, list):
            return data
    return []


def extract_print_area_images(product: Dict[str, Any]) -> List[Dict[str, Any]]:
    usages: List[Dict[str, Any]] = []
    for print_area in product.get("print_areas", []):
        variant_ids = print_area.get("variant_ids", [])
        for placeholder in print_area.get("placeholders", []):
            position = placeholder.get("position")
            for image in placeholder.get("images", []):
                usages.append({
                    "id": str(image.get("id", "")),
                    "position": position,
                    "variant_ids": variant_ids,
                    "x": image.get("x"),
                    "y": image.get("y"),
                    "scale": image.get("scale"),
                    "angle": image.get("angle"),
                })
    return usages


def build_provenance_report(connector: PrintifyConnector,
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

    requested_ids = {str(product_id) for product_id in product_ids or []}
    products = connector.get_products(shop_id)
    if requested_ids:
        products = [p for p in products if str(p.get("id")) in requested_ids]

    product_reports = []
    for product in products:
        product_id = str(product.get("id"))
        detail = connector.get_product(shop_id, product_id)
        images = []

        for usage in extract_print_area_images(detail):
            upload_record = uploaded_images.get(usage["id"], {})
            images.append({
                "upload_id": usage["id"],
                "position": usage["position"],
                "variant_ids": usage["variant_ids"],
                "file_name": upload_record.get("file_name"),
                "preview_url": upload_record.get("preview_url"),
                "candidate_source_paths": resolve_uploaded_image_candidates(
                    upload_record,
                    asset_index,
                ),
            })

        product_reports.append({
            "product_id": product_id,
            "title": detail.get("title"),
            "blueprint_id": detail.get("blueprint_id"),
            "print_provider_id": detail.get("print_provider_id"),
            "external": detail.get("external", {}),
            "images": images,
        })

    return {
        "shop_id": shop_id,
        "images_root": str(images_root),
        "log_path": str(log_path),
        "uploaded_image_count": len(uploaded_images),
        "product_count": len(product_reports),
        "products": product_reports,
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
        help="Optional product ID to inspect. Repeat for multiple products.",
    )
    parser.add_argument(
        "--images-root",
        type=Path,
        default=DEFAULT_IMAGES_ROOT,
        help="Local standing-library root to scan for candidate images.",
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
        help="JSON file to write the provenance report to.",
    )
    return parser.parse_args()


def main() -> int:
    load_printify_env()
    connector = PrintifyConnector()
    args = parse_args()

    report = build_provenance_report(
        connector=connector,
        shop_id=args.shop_id,
        images_root=args.images_root,
        log_path=args.log_path,
        product_ids=args.product_ids,
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as output_file:
        json.dump(report, output_file, indent=2)
        output_file.write("\n")

    print(f"Wrote provenance for {report['product_count']} product(s) to {args.output}")
    matched_count = sum(
        1
        for product in report["products"]
        for image in product["images"]
        if image["candidate_source_paths"]
    )
    print(f"Matched {matched_count} product image placements to local candidate source paths")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())