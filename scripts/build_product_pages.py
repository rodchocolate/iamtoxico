#!/usr/bin/env python3
"""Generate in-site product pages for every Shopify product linked anywhere on
the site, then repoint those tile links to the local pages.

- Handles are harvested from product links in all site HTML (tiles JSON `u`/
  `buy` fields, img-link/buy anchors, preview.html P array).
- Title + price come from data/shopify_variants.json (run
  scripts/sync_shopify_variants.py first); front/back mockups come from the
  tile that linked the product, falling back to the Shopify product image.
- Pages use the originals product-page layout (gallery + info + buy); the buy
  button keeps the Shopify URL so cart.js opens the on-site size picker.
- Existing product/<handle>.html files are never overwritten.

    python3 scripts/build_product_pages.py
"""
from __future__ import annotations

import html as H
import json
import re
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SHOP = "https://shop.iamtoxico.com"
PRODUCT_URL = re.compile(r'https?://[a-z0-9-]+\.myshopify\.com/products/([a-zA-Z0-9-]+)')

NAV = '''<nav class="global-nav">
    <div class="nav-brand"><a href="/">iamtoxico</a></div>
    <div class="nav-links">
      <div class="nav-group collections">
        <a href="/originals.html">originals</a> <span class="dot">&middot;</span>
        <a href="/foolswise.html">foolswise</a> <span class="dot">&middot;</span>
        <a href="/scratch/">scratch</a> <span class="dot">&middot;</span>
        <a href="/designs.html">designs</a>
      </div>
      <div class="nav-group families">
        <a href="/avant-apres.html">avant/apres</a> <span class="dot">&middot;</span>
        <a href="/harem.html">harem</a> <span class="dot">&middot;</span>
        <a href="/hoop.html">hoops</a> <span class="dot">&middot;</span>
        <a href="/bookpack.html">bookpack</a>
      </div>
    </div>
  </nav>'''

STYLE = """
  .pmain { display:grid; grid-template-columns:1fr 1fr; gap:2.5rem; margin-top:1rem; }
  .gallery .main { width:100%; aspect-ratio:1; background:#1a1a1a; border-radius:12px; overflow:hidden; border:1px solid rgba(255,255,255,.1); }
  .gallery .main img { width:100%; height:100%; object-fit:cover; }
  .thumbs { display:flex; gap:.6rem; margin-top:.7rem; }
  .thumbs img { width:70px; height:70px; object-fit:cover; border-radius:8px; border:1px solid rgba(255,255,255,.15); cursor:pointer; opacity:.6; transition:opacity .2s; }
  .thumbs img:hover, .thumbs img.sel { opacity:1; border-color:#ffc800; }
  .pinfo h2 { font-size:2rem; font-weight:700; text-transform:lowercase; }
  .pinfo .price { font-size:1.4rem; color:#ffc800; margin:.6rem 0 1.2rem; }
  .buy { display:inline-block; background:#ffc800; color:#0b0b0b; font-weight:700; text-transform:lowercase; letter-spacing:.03em; padding:.9rem 2.2rem; border-radius:10px; text-decoration:none; }
  .buy:hover { background:#fff; }
  @media (max-width:768px){ .pmain{ grid-template-columns:1fr; gap:1.2rem; } }
"""

THUMB = ('<img src="{src}" alt="{alt}" data-src="{src}" class="{cls}" '
         "onclick=\"document.getElementById('pm').src=this.dataset.src;"
         "document.querySelectorAll('.thumbs img').forEach(t=>t.classList.remove('sel'));"
         "this.classList.add('sel')\">")

PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="robots" content="noindex, nofollow">
<title>iamtoxico — {title_lc}</title>
<link rel="stylesheet" href="/style.css">
<style>{style}</style>
</head>
<body>
<header>
  {nav}
</header>
<main>
<div class="pmain">
<div class="gallery"><div class="main"><img id="pm" src="{front}" alt="{title}"></div><div class="thumbs">{thumbs}</div></div>
<div class="pinfo"><h2>{title_lc}</h2><div class="price">{price}</div><a class="buy" href="{buy}">buy</a></div>
</div>
</main>
<footer>&copy; 2025 iamtoxico</footer>
<script defer src="/cart.js"></script>
</body>
</html>
"""


def money(prices: list[str]) -> str:
    vals = [float(p) for p in prices if p]
    v = min(vals) if vals else 0
    return f"${v:g}"


def harvest_images(pages: list[Path]) -> dict[str, dict]:
    """handle -> {'f': front, 'b': back} from tiles across the site."""
    out: dict[str, dict] = {}

    def feed(handle, front, back):
        if not handle or not front:
            return
        cur = out.setdefault(handle, {})
        cur.setdefault("f", front)
        if back and not cur.get("b"):
            cur["b"] = back

    obj_re = re.compile(r'\{[^{}]*\}')
    pair_re = re.compile(r'"?(t|y|f|b|u|buy)"?\s*:\s*"([^"]*)"')
    card_re = re.compile(
        r'<a class="img-link" href="([^"]+)"[^>]*>'
        r'<img class="front" src="([^"]+)"[^>]*>'
        r'(?:<img class="back" src="([^"]+)")?', re.S)

    for p in pages:
        t = p.read_text(errors="replace")
        # tile objects in JSON blocks and JS arrays (preview.html P entries)
        for m in obj_re.finditer(t):
            kv = dict(pair_re.findall(m.group(0)))
            u = kv.get("u") or kv.get("buy") or ""
            hm = PRODUCT_URL.search(u)
            if hm:
                feed(hm.group(1), kv.get("f"), kv.get("b"))
        # inline HTML cards
        for href, front, back in card_re.findall(t):
            hm = PRODUCT_URL.search(href)
            if hm:
                feed(hm.group(1), front, back)
    return out


def shopify_images() -> dict[str, str]:
    """handle -> first product image URL from the store's public products.json."""
    out, page = {}, 1
    while True:
        url = f"https://iamtoxico.myshopify.com/products.json?limit=250&page={page}"
        with urllib.request.urlopen(url, timeout=30) as r:
            batch = json.load(r).get("products", [])
        for p in batch:
            if p.get("images"):
                out[p["handle"]] = p["images"][0]["src"]
        if len(batch) < 250:
            return out
        page += 1


def main() -> None:
    variants = json.loads((ROOT / "data" / "shopify_variants.json").read_text())["products"]
    pages = [p for p in ROOT.rglob("*.html") if "_assets" not in str(p)]
    site_pages = [p for p in pages if p.parent.name != "product"]

    handles = set()
    for p in site_pages:
        handles.update(PRODUCT_URL.findall(p.read_text(errors="replace")))

    existing = {p.stem for p in (ROOT / "product").glob("*.html")}
    todo = sorted(h for h in handles if h not in existing and h in variants)
    dead = sorted(h for h in handles if h not in variants)

    imgs = harvest_images(site_pages)
    missing_imgs = [h for h in todo if h not in imgs]
    fallback = shopify_images() if missing_imgs else {}

    built = []
    for h in todo:
        v = variants[h]
        front = imgs.get(h, {}).get("f") or fallback.get(h)
        back = imgs.get(h, {}).get("b")
        if not front:
            continue
        thumbs = THUMB.format(src=H.escape(front), alt="front", cls="sel")
        if back:
            thumbs += THUMB.format(src=H.escape(back), alt="back", cls="")
        (ROOT / "product" / f"{h}.html").write_text(PAGE.format(
            title=H.escape(v["t"]), title_lc=H.escape(v["t"].lower()),
            style=STYLE, nav=NAV, front=H.escape(front), thumbs=thumbs,
            price=money([x["p"] for x in v["v"]]),
            buy=f"{SHOP}/products/{h}",
        ), encoding="utf-8")
        built.append(h)

    # repoint tile links on site pages to the local product pages
    local = existing | set(built)
    repointed = 0
    for p in site_pages:
        t = p.read_text(errors="replace")
        t2 = PRODUCT_URL.sub(
            lambda m: f"/product/{m.group(1)}.html" if m.group(1) in local else m.group(0), t)
        if t2 != t:
            p.write_text(t2, encoding="utf-8")
            repointed += 1

    print(f"site handles: {len(handles)} | built: {len(built)} | "
          f"already had pages: {len(handles & existing)} | not live (left alone): {len(dead)}")
    print(f"repointed links on {repointed} pages")
    if dead:
        print("not live:", dead[:10], "..." if len(dead) > 10 else "")


if __name__ == "__main__":
    main()
