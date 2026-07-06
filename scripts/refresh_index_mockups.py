#!/usr/bin/env python3
"""Refresh the hoop/backpack mockup URLs embedded in index.html.

The hoop and backpack rows point at scratch-preview mockups until the live
products render their own; rerun this after Printify re-renders to swap in the
current images (keyed by the P entries' k:"<Design>|<style>" field).

    python3 scripts/refresh_index_mockups.py
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "shopify-app"))
from resolve_printify_sources import load_printify_env  # noqa: E402
from printify_connector import PrintifyConnector  # noqa: E402

SCRATCH = 22994552
DESIGNS = ["Arctic River", "Cyan Glow", "Frozen Sky", "Hold Cards", "Hot Oil", "Toxico"]
SOURCES = {"hoop": "{d} — Hoop Shorts", "backpack": "{d} — Backpack 01"}


def main() -> int:
    load_printify_env()
    c = PrintifyConnector()
    by_title = {p["title"]: p for p in c.get_products(SCRATCH)}
    path = ROOT / "index.html"
    html = path.read_text(encoding="utf-8")
    swapped = 0
    for style, tpl in SOURCES.items():
        for d in DESIGNS:
            p = by_title.get(tpl.format(d=d))
            if not p:
                continue
            imgs = [i["src"] for i in p.get("images", []) if i.get("src")]
            if not imgs:
                continue
            front = next((s for s in imgs if "camera_label=front" in s), imgs[0])
            back = next((s for s in imgs if "camera_label=back" in s), front)
            def sub(m):
                return f'{m.group(1)}f:"{front}", b:"{back}"}}'
            new = re.sub(
                rf'(\{{k:"{re.escape(d)}\|{style}".*?)f:"[^"]*", b:"[^"]*"\}}',
                sub, html)
            if new != html:
                swapped += 1
                html = new
    path.write_text(html, encoding="utf-8")
    print(f"index.html: {swapped} entries refreshed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
