#!/usr/bin/env python3
"""Refresh the hoop/backpack mockup URLs in index.html's tiles-data block.

Those tiles point at scratch-preview mockups; rerun after Printify re-renders
to swap in current images, then rebuild the per-design pages.

    python3 scripts/refresh_index_mockups.py
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "shopify-app"))
from resolve_printify_sources import load_printify_env  # noqa: E402
from printify_connector import PrintifyConnector  # noqa: E402

SCRATCH = 22994552
SOURCES = {"Hoop Shorts": "{d} — Hoop Shorts", "Backpack": "{d} — Backpack 01"}


def main() -> int:
    load_printify_env()
    c = PrintifyConnector()
    by_title = {p["title"]: p for p in c.get_products(SCRATCH)}
    path = ROOT / "index.html"
    html = path.read_text(encoding="utf-8")
    m = re.search(r'(<script type="application/json" id="tiles-data">)(.*?)(</script>)', html, re.S)
    if not m:
        raise SystemExit("index.html tiles-data block not found")
    data = json.loads(m.group(2))
    swapped = 0
    for row in data.get("rows", []):
        design = row["label"].title()
        for tile in row.get("tiles", []):
            for suffix, tpl in SOURCES.items():
                if not tile.get("t", "").endswith(suffix):
                    continue
                p = by_title.get(tpl.format(d=design))
                if not p:
                    continue
                imgs = [i["src"] for i in p.get("images", []) if i.get("src")]
                if not imgs:
                    continue
                front = next((s for s in imgs if "camera_label=front" in s), imgs[0])
                back = next((s for s in imgs if "camera_label=back" in s), front)
                if tile.get("f") != front or tile.get("b") != back:
                    tile["f"], tile["b"] = front, back
                    swapped += 1
    new_html = html[:m.start()] + m.group(1) + json.dumps(data, indent=2) + m.group(3) + html[m.end():]
    path.write_text(new_html, encoding="utf-8")
    print(f"index.html: {swapped} tiles refreshed")
    if swapped:
        import build_design_pages
        build_design_pages.main()
    return 0


if __name__ == "__main__":
    sys.exit(main())
