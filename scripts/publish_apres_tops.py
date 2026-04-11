#!/usr/bin/env python3
"""Clone a proven Apres top template for each live Harem family.

This script uses the staged Cyan Glow Fashion Hoodie (AOP) as the layout
template, swaps in the upload image from each live Harem Pant, optionally
publishes the resulting tops to Shopify, syncs catalog.json with the real
Shopify URLs, and can create a simple Shopify discount code for pant+top sets.
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


ROOT = Path(__file__).resolve().parent.parent
SHOPIFY_APP = ROOT / "shopify-app"
CATALOG_PATH = ROOT / "data" / "catalog.json"

if str(SHOPIFY_APP) not in sys.path:
    sys.path.insert(0, str(SHOPIFY_APP))

from printify_connector import PrintifyConnector  # type: ignore
from shopify_connector import ShopifyConnector  # type: ignore


DEFAULT_TEMPLATE_SHOP_ID = 22994552
DEFAULT_TEMPLATE_PRODUCT_ID = "69b57f19ef961127590bc947"
DEFAULT_TARGET_SHOP_ID = 26651009
DEFAULT_TOP_PRICE_DOLLARS = 120.0
DEFAULT_SET_PRICE_DOLLARS = 200.0
DEFAULT_PATTERN_SCALE_MULTIPLIER = 1.25
DEFAULT_BRICK_OFFSET = 0.5
DEFAULT_SHOPIFY_DOMAIN = "1tap6m-et.myshopify.com"
DEFAULT_DISCOUNT_CODE = "APRESSET200"
DEFAULT_DISCOUNT_TITLE = "Apres Set 200"


def load_shopify_app_env() -> None:
    env_path = SHOPIFY_APP / ".env"
    if not env_path.is_file():
        return

    with open(env_path, encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def family_from_pant_title(title: str) -> str:
    suffix = " Harem Pant"
    if title.endswith(suffix):
        return title[: -len(suffix)].strip()
    return title.strip()


def apres_title_from_family(family: str) -> str:
    return f"{family} Apres"


def slugify(value: str) -> str:
    lowered = value.lower()
    slug = []
    previous_dash = False
    for char in lowered:
        if char.isalnum():
            slug.append(char)
            previous_dash = False
            continue
        if not previous_dash:
            slug.append("-")
            previous_dash = True
    return "".join(slug).strip("-")


def load_catalog(path: Path = CATALOG_PATH) -> Dict[str, Any]:
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def save_catalog(catalog: Dict[str, Any], path: Path = CATALOG_PATH) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(catalog, handle, indent=2)
        handle.write("\n")


def live_harem_titles_from_catalog(catalog: Dict[str, Any]) -> List[str]:
    titles: List[str] = []
    for product in catalog.get("products", []):
        if product.get("source") != "printify":
            continue
        name = product.get("name")
        if isinstance(name, str) and name.endswith("Harem Pant"):
            titles.append(name)
    return titles


def pick_primary_image(product_detail: Dict[str, Any]) -> str:
    images = product_detail.get("images", [])
    for image in images:
        if image.get("is_default") and image.get("src"):
            return image["src"]
    for image in images:
        if image.get("position") == "front" and image.get("src"):
            return image["src"]
    for image in images:
        if image.get("src"):
            return image["src"]
    return ""


def extract_upload_id(product_detail: Dict[str, Any]) -> str:
    upload_ids: List[str] = []
    for area in product_detail.get("print_areas", []):
        for placeholder in area.get("placeholders", []):
            for image in placeholder.get("images", []):
                image_id = image.get("id")
                if image_id:
                    upload_ids.append(str(image_id))

    if not upload_ids:
        raise ValueError(f"No reusable upload ids found for product {product_detail.get('id')}")

    return Counter(upload_ids).most_common(1)[0][0]


def build_variants(template_variants: Iterable[Dict[str, Any]], price_cents: int) -> List[Dict[str, Any]]:
    variants: List[Dict[str, Any]] = []
    for variant in template_variants:
        if not variant.get("is_available", True):
            continue
        entry: Dict[str, Any] = {
            "id": variant["id"],
            "price": price_cents,
            "is_enabled": bool(variant.get("is_enabled", True)),
        }
        if variant.get("is_default"):
            entry["is_default"] = True
        variants.append(entry)
    return variants


def build_image_payload(
    image: Dict[str, Any],
    upload_id: str,
    scale_multiplier: float,
    brick_offset: Optional[float],
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "id": upload_id,
        "x": image.get("x", 0.5),
        "y": image.get("y", 0.5),
        "scale": image.get("scale", 1.0) * scale_multiplier,
        "angle": image.get("angle", 0),
    }

    pattern = copy.deepcopy(image.get("pattern"))
    if pattern or brick_offset is not None:
        pattern = pattern or {"spacing_x": 1, "spacing_y": 1, "angle": 0, "offset": 0}
        if brick_offset is not None:
            pattern["offset"] = brick_offset
        payload["pattern"] = pattern

    return payload


def build_print_areas(
    template_print_areas: Iterable[Dict[str, Any]],
    upload_id: str,
    scale_multiplier: float,
    brick_offset: Optional[float],
) -> List[Dict[str, Any]]:
    areas: List[Dict[str, Any]] = []
    for area in template_print_areas:
        placeholders: List[Dict[str, Any]] = []
        for placeholder in area.get("placeholders", []):
            images = placeholder.get("images", [])
            if not images:
                continue
            placeholders.append(
                {
                    "position": placeholder["position"],
                    "images": [
                        build_image_payload(image, upload_id, scale_multiplier, brick_offset)
                        for image in images
                    ],
                }
            )

        areas.append(
            {
                "variant_ids": list(area.get("variant_ids", [])),
                "placeholders": placeholders,
            }
        )
    return areas


def build_product_payload(
    template_product: Dict[str, Any],
    title: str,
    upload_id: str,
    price_dollars: float,
    scale_multiplier: float,
    brick_offset: Optional[float],
) -> Dict[str, Any]:
    family = title.removesuffix(" Apres")
    price_cents = int(round(price_dollars * 100))
    return {
        "title": title,
        "description": (
            f"{family} Apres. All-over fashion hoodie cut on the proven Subliminator blank, "
            "paired with the matching Harem Pant for the full toxico set."
        ),
        "blueprint_id": template_product["blueprint_id"],
        "print_provider_id": template_product["print_provider_id"],
        "variants": build_variants(template_product.get("variants", []), price_cents),
        "print_areas": build_print_areas(
            template_product.get("print_areas", []),
            upload_id,
            scale_multiplier,
            brick_offset,
        ),
        "tags": [family, "Apres", "AOP", "Set Top", "toxico"],
    }


def build_catalog_entry(product_detail: Dict[str, Any], price_dollars: float) -> Dict[str, Any]:
    entry: Dict[str, Any] = {
        "id": f"printify-{product_detail['id']}",
        "printify_id": product_detail["id"],
        "name": product_detail["title"],
        "price": price_dollars,
        "category": "activewear",
        "margin_tier": "pod",
        "image": pick_primary_image(product_detail),
        "source": "printify",
        "status": "active",
    }
    external = product_detail.get("external")
    if isinstance(external, dict) and external.get("handle"):
        entry["url"] = external["handle"]
    return entry


def upsert_catalog_entries(catalog: Dict[str, Any], entries: Iterable[Dict[str, Any]]) -> Dict[str, int]:
    products = catalog.setdefault("products", [])
    by_name = {
        product.get("name"): index
        for index, product in enumerate(products)
        if isinstance(product.get("name"), str)
    }

    added = 0
    updated = 0

    for entry in entries:
        name = entry["name"]
        if name in by_name:
            products[by_name[name]].update(entry)
            updated += 1
            continue
        products.append(entry)
        by_name[name] = len(products) - 1
        added += 1

    return {"added": added, "updated": updated}


def coerce_shopify_product_id(product_detail: Dict[str, Any]) -> Optional[int]:
    external = product_detail.get("external")
    if not isinstance(external, dict):
        return None
    external_id = external.get("id")
    if not external_id:
        return None
    try:
        return int(external_id)
    except (TypeError, ValueError):
        return None


def build_set_price_rule(
    title: str,
    pant_product_ids: List[int],
    top_product_ids: List[int],
    set_price_dollars: float,
    item_price_dollars: float,
) -> Dict[str, Any]:
    discount_dollars = round((item_price_dollars * 2) - set_price_dollars, 2)
    return {
        "title": title,
        "target_type": "line_item",
        "target_selection": "entitled",
        "allocation_method": "each",
        "allocation_limit": 1,
        "value_type": "fixed_amount",
        "value": f"-{discount_dollars:.2f}",
        "customer_selection": "all",
        "starts_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "prerequisite_product_ids": pant_product_ids,
        "entitled_product_ids": top_product_ids,
        "prerequisite_quantity_range": {"greater_than_or_equal_to": 1},
    }


def load_shopify_connector(shop_domain: Optional[str]) -> ShopifyConnector:
    if shop_domain:
        connector = ShopifyConnector.load_token(shop_domain)
        if connector:
            return connector

    tokens = ShopifyConnector._load_tokens_file()
    if not tokens:
        raise ValueError("No saved Shopify token found in shopify_tokens.json")

    preferred = shop_domain or DEFAULT_SHOPIFY_DOMAIN
    if preferred in tokens:
        connector = ShopifyConnector.load_token(preferred)
        if connector:
            return connector

    first_domain = sorted(tokens.keys())[0]
    connector = ShopifyConnector.load_token(first_domain)
    if not connector:
        raise ValueError(f"Unable to load Shopify token for {first_domain}")
    return connector


def wait_for_publish(connector: PrintifyConnector, shop_id: int, product_id: str, attempts: int = 10) -> Dict[str, Any]:
    detail = connector.get_product(shop_id, product_id)
    for _ in range(attempts):
        external = detail.get("external")
        if isinstance(external, dict) and external.get("handle") and external.get("id"):
            return detail
        time.sleep(2)
        detail = connector.get_product(shop_id, product_id)
    return detail


def ensure_apres_products(
    connector: PrintifyConnector,
    template_product: Dict[str, Any],
    target_shop_id: int,
    pant_titles: List[str],
    top_price_dollars: float,
    scale_multiplier: float,
    brick_offset: Optional[float],
    apply_changes: bool,
    publish_products: bool,
) -> List[Dict[str, Any]]:
    shop_products = connector.get_products(target_shop_id)
    by_title = {product.get("title"): product for product in shop_products}
    results: List[Dict[str, Any]] = []

    for pant_title in pant_titles:
        source_product = by_title.get(pant_title)
        if not source_product:
            raise ValueError(f"Live pant '{pant_title}' not found in Printify shop {target_shop_id}")

        family = family_from_pant_title(pant_title)
        top_title = apres_title_from_family(family)
        existing_top = by_title.get(top_title)

        source_detail = connector.get_product(target_shop_id, source_product["id"])
        upload_id = extract_upload_id(source_detail)

        if existing_top and not apply_changes:
            results.append(
                {
                    "family": family,
                    "title": top_title,
                    "action": "exists",
                    "product_id": existing_top["id"],
                    "upload_id": upload_id,
                }
            )
            continue

        if existing_top and apply_changes:
            top_detail = connector.get_product(target_shop_id, existing_top["id"])
            action = "existing"
        else:
            payload = build_product_payload(
                template_product,
                top_title,
                upload_id,
                top_price_dollars,
                scale_multiplier,
                brick_offset,
            )

            if not apply_changes:
                results.append(
                    {
                        "family": family,
                        "title": top_title,
                        "action": "would-create",
                        "upload_id": upload_id,
                        "payload": payload,
                    }
                )
                continue

            top_detail = connector.create_product(target_shop_id, payload)
            action = "created"

        if publish_products and apply_changes:
            connector.publish_product(
                target_shop_id,
                top_detail["id"],
                {
                    "title": True,
                    "description": True,
                    "images": True,
                    "variants": True,
                    "tags": True,
                    "keyFeatures": True,
                    "shipping_template": True,
                },
            )
            top_detail = wait_for_publish(connector, target_shop_id, top_detail["id"])
            action = f"{action}+published"

        results.append(
            {
                "family": family,
                "title": top_title,
                "action": action,
                "product_id": top_detail["id"],
                "upload_id": upload_id,
                "product": top_detail,
            }
        )

        if action.startswith("created"):
            by_title[top_title] = {"id": top_detail["id"], "title": top_title}

    return results


def sync_catalog(
    catalog_path: Path,
    pant_products: List[Dict[str, Any]],
    top_products: List[Dict[str, Any]],
    pant_price_dollars: float,
    top_price_dollars: float,
) -> Dict[str, int]:
    catalog = load_catalog(catalog_path)
    entries = [
        build_catalog_entry(product, pant_price_dollars)
        for product in pant_products
    ] + [
        build_catalog_entry(product, top_price_dollars)
        for product in top_products
    ]
    stats = upsert_catalog_entries(catalog, entries)
    save_catalog(catalog, catalog_path)
    return stats


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--template-shop-id", type=int, default=DEFAULT_TEMPLATE_SHOP_ID)
    parser.add_argument("--template-product-id", default=DEFAULT_TEMPLATE_PRODUCT_ID)
    parser.add_argument("--target-shop-id", type=int, default=DEFAULT_TARGET_SHOP_ID)
    parser.add_argument("--title", action="append", dest="titles", help="Specific live Harem Pant title to process. Repeat for multiple titles.")
    parser.add_argument("--price", type=float, default=DEFAULT_TOP_PRICE_DOLLARS, help="Top price in dollars.")
    parser.add_argument("--set-price", type=float, default=DEFAULT_SET_PRICE_DOLLARS, help="Pant+top set price in dollars.")
    parser.add_argument("--pattern-scale-multiplier", type=float, default=DEFAULT_PATTERN_SCALE_MULTIPLIER)
    parser.add_argument("--brick-offset", type=float, default=None, help="Optional brick pattern offset, e.g. 0.5.")
    parser.add_argument("--sync-catalog", action="store_true", help="Update data/catalog.json with live pant and top entries.")
    parser.add_argument("--catalog-path", type=Path, default=CATALOG_PATH)
    parser.add_argument("--publish", action="store_true", help="Publish created tops to the connected Shopify store.")
    parser.add_argument("--apply", action="store_true", help="Make remote changes. Without this flag the script runs in dry-run mode.")
    parser.add_argument("--create-discount-code", action="store_true", help="Create or update a Shopify set discount code once products are live.")
    parser.add_argument("--discount-code", default=DEFAULT_DISCOUNT_CODE)
    parser.add_argument("--discount-title", default=DEFAULT_DISCOUNT_TITLE)
    parser.add_argument("--shopify-domain", default=DEFAULT_SHOPIFY_DOMAIN)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    load_shopify_app_env()

    printify = PrintifyConnector()
    template = printify.get_product(args.template_shop_id, args.template_product_id)
    catalog = load_catalog(args.catalog_path)
    pant_titles = args.titles or live_harem_titles_from_catalog(catalog)
    if not pant_titles:
        raise ValueError("No live Harem Pant titles found to process")

    dry_run = not args.apply
    brick_offset = args.brick_offset

    results = ensure_apres_products(
        connector=printify,
        template_product=template,
        target_shop_id=args.target_shop_id,
        pant_titles=pant_titles,
        top_price_dollars=args.price,
        scale_multiplier=args.pattern_scale_multiplier,
        brick_offset=brick_offset,
        apply_changes=not dry_run,
        publish_products=args.publish,
    )

    print(json.dumps(results, indent=2))

    if dry_run:
        return 0

    target_products = printify.get_products(args.target_shop_id)
    target_by_title = {product.get("title"): product for product in target_products}
    pant_products = [
        printify.get_product(args.target_shop_id, target_by_title[title]["id"])
        for title in pant_titles
    ]
    top_titles = [apres_title_from_family(family_from_pant_title(title)) for title in pant_titles]
    top_products = [
        printify.get_product(args.target_shop_id, target_by_title[title]["id"])
        for title in top_titles
        if title in target_by_title
    ]

    if args.sync_catalog:
        stats = sync_catalog(
            catalog_path=args.catalog_path,
            pant_products=pant_products,
            top_products=top_products,
            pant_price_dollars=DEFAULT_TOP_PRICE_DOLLARS,
            top_price_dollars=args.price,
        )
        print(json.dumps({"catalog": stats}, indent=2))

    if args.create_discount_code:
        shopify = load_shopify_connector(args.shopify_domain)
        pant_ids = [product_id for product_id in (coerce_shopify_product_id(product) for product in pant_products) if product_id]
        top_ids = [product_id for product_id in (coerce_shopify_product_id(product) for product in top_products) if product_id]
        if not pant_ids or not top_ids:
            raise ValueError("Cannot create set pricing without published Shopify pant and top products")

        rule_data = build_set_price_rule(
            title=args.discount_title,
            pant_product_ids=pant_ids,
            top_product_ids=top_ids,
            set_price_dollars=args.set_price,
            item_price_dollars=args.price,
        )

        existing_rule = shopify.find_price_rule_by_title(args.discount_title)
        if existing_rule:
            rule = shopify.update_price_rule(existing_rule["id"], {**rule_data, "id": existing_rule["id"]})
            action = "updated"
        else:
            rule = shopify.create_price_rule(rule_data)
            action = "created"
        code = shopify.ensure_discount_code(rule["id"], args.discount_code)
        print(json.dumps({"discount_rule": action, "price_rule_id": rule["id"], "discount_code": code}, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())