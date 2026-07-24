#!/usr/bin/env python3
"""Refresh preview.html entries from current Printify shop state.

The preview page is still curated manually for labels and categories, but this
script keeps its mockup URLs current and removes entries whose backing Printify
products were deleted.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

ROOT = Path(__file__).resolve().parent.parent
SHOPIFY_APP = ROOT / "shopify-app"

if str(SHOPIFY_APP) not in sys.path:
    sys.path.insert(0, str(SHOPIFY_APP))

from printify_connector import PrintifyConnector
from resolve_printify_sources import load_printify_env


DEFAULT_PREVIEW_PATH = ROOT / "preview.html"
DEFAULT_LIVE_SHOP_ID = 26651009
DEFAULT_STAGING_SHOP_ID = 22994552
ARRAY_RE = re.compile(r"const P = \[\n(?P<body>.*?)\n\];", re.DOTALL)
ENTRY_RE = re.compile(
    r'^\s*\{t:"(?P<title>[^"\\]*(?:\\.[^"\\]*)*)",\s*'
    r'y:"(?P<category>[^"\\]*(?:\\.[^"\\]*)*)",\s*'
    r's:"(?P<shop>live|staging)",\s*'
    r'(?:p:(?P<price>\d+(?:\.\d+)?),\s*)?'
    r'(?:u:"(?P<url>[^"\\]*(?:\\.[^"\\]*)*)",\s*)?'
    r'f:"(?P<front>[^"\\]*(?:\\.[^"\\]*)*)",\s*'
    r'b:"(?P<back>[^"\\]*(?:\\.[^"\\]*)*)"'
    r'(?:,\s*c:(?P<colors>\[[^\]]*\]))?'
    r'(?:,\s*g:"(?P<page>[^"]*)")?'
    r'\},\s*$'
)
MOCKUP_PRODUCT_ID_RE = re.compile(r"/mockup/(?P<product_id>[^/]+)/")
FRONT_LABELS = (
    "front",
    "person-front-1",
    "person-front-2",
    "person-front",
    "man-front",
    "on-person-front",
    "lifestyle-man",
)
BACK_LABELS = (
    "back",
    "person-back",
    "man-back",
    "on-person-back",
    "lifestyle-woman",
    "context",
)


@dataclass(frozen=True)
class PreviewEntry:
    title: str
    category: str
    shop: str
    front: str
    back: str
    raw: str


def js_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def extract_product_id(url: str) -> str | None:
    match = MOCKUP_PRODUCT_ID_RE.search(url)
    return match.group("product_id") if match else None


def parse_preview_entries(html: str) -> List[PreviewEntry]:
    """Parse P entries in file order. Order is meaningful (newest → oldest) and
    is preserved on rewrite, as are any extra fields (p, u, c, g) via `raw`."""
    match = ARRAY_RE.search(html)
    if not match:
        raise ValueError("Could not find preview product array in preview.html")

    entries: List[PreviewEntry] = []
    for raw_line in match.group("body").splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("/*"):
            continue

        entry_match = ENTRY_RE.match(raw_line)
        if not entry_match:
            raise ValueError(f"Unexpected preview entry line: {raw_line}")

        entries.append(
            PreviewEntry(
                title=entry_match.group("title").replace('\\"', '"').replace("\\\\", "\\"),
                category=entry_match.group("category").replace('\\"', '"').replace("\\\\", "\\"),
                shop=entry_match.group("shop"),
                front=entry_match.group("front").replace('\\"', '"').replace("\\\\", "\\"),
                back=entry_match.group("back").replace('\\"', '"').replace("\\\\", "\\"),
                raw=raw_line,
            )
        )

    return entries


def replace_preview_entries(html: str, entries: Sequence[PreviewEntry]) -> str:
    replacement = "const P = [\n" + "\n".join(e.raw for e in entries) + "\n];"
    return ARRAY_RE.sub(lambda _: replacement, html, count=1)


def select_mockup_url(images: Sequence[dict], preferred_labels: Iterable[str]) -> str:
    for label in preferred_labels:
        token = f"camera_label={label}"
        for image in images:
            src = str(image.get("src", ""))
            if token in src:
                return src
    return ""


def refresh_entry(entry: PreviewEntry, product: dict) -> PreviewEntry:
    images = product.get("images", [])
    front = select_mockup_url(images, FRONT_LABELS) or entry.front
    back = select_mockup_url(images, BACK_LABELS) or entry.back
    raw = entry.raw.replace(f'f:"{js_escape(entry.front)}"', f'f:"{js_escape(front)}"')
    raw = raw.replace(f'b:"{js_escape(entry.back)}"', f'b:"{js_escape(back)}"')
    return PreviewEntry(
        title=entry.title,
        category=entry.category,
        shop=entry.shop,
        front=front,
        back=back,
        raw=raw,
    )


def sync_entries(
    entries: Sequence[PreviewEntry],
    products_by_shop: Dict[str, Dict[str, dict]],
    keep_missing: bool = False,
) -> Tuple[List[PreviewEntry], List[PreviewEntry]]:
    synced: List[PreviewEntry] = []
    removed: List[PreviewEntry] = []

    for entry in entries:
        product_id = extract_product_id(entry.front) or extract_product_id(entry.back)
        if not product_id:
            if keep_missing:
                synced.append(entry)
            else:
                removed.append(entry)
            continue

        product = products_by_shop[entry.shop].get(product_id)
        if not product:
            if keep_missing:
                synced.append(entry)
            else:
                removed.append(entry)
            continue

        synced.append(refresh_entry(entry, product))

    return synced, removed


def load_products_by_id(connector: PrintifyConnector, shop_id: int) -> Dict[str, dict]:
    return {
        str(product.get("id")): product
        for product in connector.get_products(shop_id)
        if product.get("id")
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preview-file", type=Path, default=DEFAULT_PREVIEW_PATH)
    parser.add_argument("--live-shop-id", type=int, default=DEFAULT_LIVE_SHOP_ID)
    parser.add_argument("--staging-shop-id", type=int, default=DEFAULT_STAGING_SHOP_ID)
    parser.add_argument(
        "--keep-missing",
        action="store_true",
        help="Keep preview entries even if their backing Printify product no longer exists.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report changes without writing preview.html.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    load_printify_env()
    connector = PrintifyConnector()

    html = args.preview_file.read_text(encoding="utf-8")
    entries = parse_preview_entries(html)

    products_by_shop = {
        "live": load_products_by_id(connector, args.live_shop_id),
        "staging": load_products_by_id(connector, args.staging_shop_id),
    }

    synced, removed = sync_entries(entries, products_by_shop, keep_missing=args.keep_missing)

    refreshed_html = replace_preview_entries(html, synced)
    if not args.dry_run:
        args.preview_file.write_text(refreshed_html, encoding="utf-8")

    live_kept = sum(1 for e in synced if e.shop == "live")
    print(
        f"Preview refresh complete: {live_kept} live kept, {len(synced) - live_kept} staging kept, "
        f"{len(removed)} removed"
    )
    for entry in removed:
        print(f"removed\t{entry.shop}\t{entry.title}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())