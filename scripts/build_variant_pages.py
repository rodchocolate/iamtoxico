#!/usr/bin/env python3
"""Generate bags.html and hoodies.html — internal viewing pages listing every
variant of a product family across the live shop and the scratch (staging)
shop, grouped by style, so picks can be made per style.

Rerun any time to refresh mockup URLs (Printify re-renders lag product edits):
  python scripts/build_variant_pages.py
"""
from __future__ import annotations

import html
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "shopify-app"))

from resolve_printify_sources import load_printify_env  # noqa: E402
from printify_connector import PrintifyConnector  # noqa: E402

LIVE_SHOP = 26651009
SCRATCH_SHOP = 22994552

BAG_STYLES = [
    ("Backpack", re.compile(r"backpack", re.I)),
    ("Leather Travel Bag", re.compile(r"travel bag", re.I)),
    ("Laundry Bag", re.compile(r"laundry bag", re.I)),
    ("Sling Bag", re.compile(r"sling bag", re.I)),
]

HOODIE_BLUEPRINT = 592

# Per-design preview products created in the scratch shop ("<design> — <label>")
# so a bag can be picked per original and a replacement hoodie template chosen.
DESIGN_ORDER = ["Arctic River", "Cyan Glow", "Frozen Sky", "Hold Cards", "Hot Oil", "Toxico"]
BAG_LABELS = ["Backpack 01", "Backpack 02", "Leather Travel Bag 01",
              "Leather Travel Bag 02", "Laundry Bag", "Sling Bag"]
HOODIE_CANDIDATE_LABELS = ["Pullover Hoodie", "Hooded Long Sleeve Tee", "Warmup Hoodie"]
PREVIEW_RX = re.compile(
    rf"^(?P<design>{'|'.join(DESIGN_ORDER)}) — "
    rf"(?P<label>{'|'.join(BAG_LABELS + HOODIE_CANDIDATE_LABELS)})$"
)


def design_sections(scratch: list[dict], labels: list[str]) -> list[str]:
    """One row per original design, cards in fixed label order."""
    by_key = {}
    for p in scratch:
        m = PREVIEW_RX.match(p.get("title", ""))
        if m and m.group("label") in labels:
            by_key[(m.group("design"), m.group("label"))] = p
    sections = []
    for design in DESIGN_ORDER:
        cards = [card(by_key[(design, lb)], "scratch")
                 for lb in labels if (design, lb) in by_key]
        sections.append(section(design, cards))
    return sections


def mockup_urls(product: dict) -> tuple[str, str]:
    imgs = [str(i.get("src", "")) for i in product.get("images", []) if i.get("src")]
    front = next((s for s in imgs if "camera_label=front" in s), imgs[0] if imgs else "")
    back = next((s for s in imgs if "camera_label=back" in s), "")
    return front, back


def card(product: dict, shop_label: str) -> str:
    front, back = mockup_urls(product)
    title = html.escape(product.get("title", ""))
    pid = product["id"]
    published = product.get("is_published", False)
    meta = f"{shop_label} · {'published' if published else 'unpublished'}"
    img_block = (
        f'<img class="front" src="{front}" loading="lazy" alt="">'
        + (f'<img class="back" src="{back}" loading="lazy" alt="">' if back else "")
        if front else "no mockup yet"
    )
    return f"""<div class="card{' empty' if not front else ''}">
  <div class="img-wrap">{img_block}</div>
  <div class="info">
    <div class="title">{title}</div>
    <div class="meta">{meta}</div>
    <div class="pid">{pid}</div>
  </div>
</div>"""


def section(label: str, cards: list[str], wrap: bool = False) -> str:
    if not cards:
        return ""
    cls = "grid wrap" if wrap else "grid"
    return f'<div class="row-label">{html.escape(label)}</div>\n<div class="{cls}">\n' + "\n".join(cards) + "\n</div>"


def page(title: str, sections: list[str]) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    body = "\n".join(s for s in sections if s)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>toxico — {html.escape(title)}</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600&display=swap');
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    font-family: 'Space Grotesk', sans-serif; color: #fff;
    background: #0b0b0b url('bg-graffiti-10.jpg') center center / cover no-repeat fixed;
    min-height: 100vh;
  }}
  body::before {{ content: ''; position: fixed; inset: 0; background: rgba(0,0,0,.55); z-index: 0; }}
  header, main, footer {{ position: relative; z-index: 1; }}
  header {{ padding: 1.5rem 2rem; display: flex; align-items: center; justify-content: space-between;
    max-width: 1280px; margin: 0 auto; }}
  header h1 {{ font-size: 1.4rem; font-weight: 600; letter-spacing: .06em; text-transform: lowercase; }}
  .badge {{ background: rgba(255,200,0,.15); color: #ffc800; font-size: .7rem; font-weight: 600;
    text-transform: uppercase; padding: .3em .7em; border-radius: 6px; letter-spacing: .08em; }}
  main {{ padding: 1rem 2rem 4rem; max-width: 1280px; margin: 0 auto; }}
  .row-label {{ font-size: 1.4rem; opacity: .55; text-transform: uppercase; letter-spacing: .12em; margin: 1.5rem 0 .6rem; }}
  .grid {{ display: grid; grid-auto-flow: column; grid-auto-columns: calc((100% - 2.8rem) / 3);
    gap: 1.4rem; overflow-x: auto; scroll-snap-type: x mandatory; padding-bottom: 1rem; scrollbar-width: thin; }}
  .grid.wrap {{ grid-auto-flow: row; grid-template-columns: repeat(3, 1fr); grid-auto-columns: unset;
    overflow-x: visible; scroll-snap-type: none; }}
  .card {{ background: rgba(255,255,255,.06); border: 1px solid rgba(255,255,255,.1);
    border-radius: 12px; overflow: hidden; position: relative; scroll-snap-align: start;
    transition: transform .25s, border-color .25s; }}
  .card:hover {{ transform: translateY(-4px); border-color: rgba(255,255,255,.25); }}
  .card .img-wrap {{ position: relative; width: 100%; aspect-ratio: 1; overflow: hidden; background: #1a1a1a; }}
  .card .img-wrap img {{ width: 100%; height: 100%; object-fit: cover; transition: opacity .3s; }}
  .card .img-wrap img.back {{ position: absolute; inset: 0; opacity: 0; }}
  .card:hover .img-wrap img.front {{ opacity: 0; }}
  .card:hover .img-wrap img.back {{ opacity: 1; }}
  .card.empty .img-wrap {{ display: flex; align-items: center; justify-content: center;
    color: rgba(255,255,255,.4); font-size: .75rem; text-transform: lowercase; letter-spacing: .05em; }}
  .card .info {{ padding: .9rem 1rem; }}
  .card .title {{ font-size: .85rem; font-weight: 600; margin-bottom: .2rem; }}
  .card .meta {{ font-size: .7rem; opacity: .65; text-transform: lowercase; }}
  .card .pid {{ font-size: .65rem; opacity: .45; font-family: monospace; margin-top: .3rem; user-select: all; }}
  footer {{ padding: 2rem; text-align: center; font-size: .7rem; opacity: .45; }}
</style>
</head>
<body>
<header><h1>toxico — {html.escape(title)}</h1><span class="badge">internal</span></header>
<main>
{body}
</main>
<footer>generated {stamp} — mockups refresh on rerun of scripts/build_variant_pages.py</footer>
<script defer src='/cart.js'></script>
</body>
</html>
"""


def build_bags(live: list[dict], scratch: list[dict]) -> str:
    """Backpack 01 decision board: originals are decided (waistband-color fill
    applied); every other design shows as a Backpack 01 card awaiting a call."""
    bp01 = {}
    for p in scratch:
        m = re.match(r"^(?P<design>.+) — Backpack 01$", p.get("title", ""))
        if m:
            bp01[m.group("design")] = p
    decided = [card(bp01[d], "scratch") for d in DESIGN_ORDER if d in bp01]
    rest = [card(bp01[d], "scratch")
            for d in sorted((k for k in bp01 if k not in DESIGN_ORDER), key=str.lower)]
    return page("bags", [
        section("originals — waistband color fill", decided),
        section("drops — dominant color fill", rest, wrap=True),
    ])


def build_puffer(scratch: list[dict]) -> str:
    by = {}
    for p in scratch:
        m = re.match(r"^(?P<design>.+) — Puffer Tile$", p.get("title", ""))
        if m:
            by[m.group("design")] = p
    cards = [card(by[d], "scratch") for d in DESIGN_ORDER if d in by]
    cards += [card(by[d], "scratch")
              for d in sorted((k for k in by if k not in DESIGN_ORDER), key=str.lower)]
    return page("puffer", [section("originals — harem tile sizing, slightly larger", cards, wrap=True)])


def build_shorts(scratch: list[dict]) -> str:
    cards = []
    by = {}
    for p in scratch:
        m = re.match(r"^(?P<design>.+) — Hoop Shorts$", p.get("title", ""))
        if m:
            by[m.group("design")] = p
    for d in DESIGN_ORDER:
        if d in by:
            cards.append(card(by[d], "scratch"))
    for d in sorted((k for k in by if k not in DESIGN_ORDER), key=str.lower):
        cards.append(card(by[d], "scratch"))
    return page("hoop shorts", [section("originals — text per staging reference", cards, wrap=True)])


def hoodie_design(title: str) -> str:
    t = re.split(r"\s+Hoodie\s+(?:Single|Mirror|Tile)", title)[0]
    t = re.split(r"\s+—\s+Apres", t)[0]
    return t.strip()


def build_hoodies(live: list[dict], scratch: list[dict]) -> str:
    sections_new = design_sections(scratch, HOODIE_CANDIDATE_LABELS)
    live_hoodies = [p for p in live if p.get("blueprint_id") == HOODIE_BLUEPRINT]
    groups: dict[str, list[str]] = {}
    order: list[str] = []
    for p in live_hoodies:
        key = hoodie_design(p.get("title", ""))
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(card(p, "live"))
    sections = ['<div class="row-label">— new template candidates —</div>']
    sections += sections_new
    sections.append('<div class="row-label">— current live hoodies —</div>')
    sections += [section(k, groups[k]) for k in order]
    template_cards = [card(p, "scratch")
                      for p in scratch if p.get("blueprint_id") == HOODIE_BLUEPRINT]
    sections.append(section("templates — scratch", template_cards))
    return page("hoodies", sections)


def main() -> int:
    load_printify_env()
    connector = PrintifyConnector()
    live = connector.get_products(LIVE_SHOP)
    scratch = connector.get_products(SCRATCH_SHOP)
    (ROOT / "bags.html").write_text(build_bags(live, scratch), encoding="utf-8")
    (ROOT / "hoodies.html").write_text(build_hoodies(live, scratch), encoding="utf-8")
    (ROOT / "shorts.html").write_text(build_shorts(scratch), encoding="utf-8")
    (ROOT / "puffer.html").write_text(build_puffer(scratch), encoding="utf-8")
    print(f"wrote bags/hoodies/shorts/puffer pages (live={len(live)} scratch={len(scratch)} products)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
