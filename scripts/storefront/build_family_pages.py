#!/usr/bin/env python3
"""Build per-family gallery pages (avant+apres / harem / hoop / bookpack) from
the clean design data collected off index + foolswise + scratch. Mirrors the
foolswise dark-grid chrome; each tile = a design's mockup linking to the live
Shopify product (or, for scratch-preview designs, opening the mockup image)."""
import json, re
from pathlib import Path

REPO = Path("/Users/melodiclabs/hermes-runtime/rooot/iamtoxico.com")
data = json.load(open("/tmp/famdata.json"))
cm = json.load(open("/tmp/colormap.json"))
COLOR = cm["color"]          # design -> color group
GORDER = cm["order"]         # foolswise group order


def group_rank(g):
    return GORDER.index(g) if g in GORDER else len(GORDER)


# reuse foolswise's <style> block for identical chrome, then override the
# slider into a 3-across wrapping grid + fix the front/back hover (no back img).
fw = (REPO / "foolswise.html").read_text()
style = fw[fw.index("<style>"):fw.index("</style>") + 8]
style += """
<style>
  header nav.crosslink { display:flex; flex-wrap:wrap; gap:.25rem 1.1rem; margin-top:.5rem; }
  header nav.crosslink a { color:#888; text-decoration:none; font-size:.85rem; }
  header nav.crosslink a:hover { color:#ffc800; }
  header nav.crosslink a.active { color:#ffc800; font-weight:600; }
  /* 3-across rows instead of the horizontal slider */
  .grid { display:grid; grid-template-columns:repeat(3,1fr); grid-auto-flow:row;
          gap:1.4rem; overflow:visible; scroll-snap-type:none; padding-bottom:0; }
  .card { scroll-snap-align:none; }
  .card:hover .img-wrap img.front { opacity:1; }   /* tiles have no back image */
  @media (max-width:768px){ .grid { grid-template-columns:repeat(2,1fr); gap:.8rem; } }
</style>"""

# pages: (filename, title, [(section-label, family-key), ...])
PAGES = [
    ("avant-apres.html", "avant · apres", [("avant", "avant"), ("apres", "apres")]),
    ("harem.html",       "harem",         [("harem", "harem")]),
    ("hoop.html",        "hoop",          [("hoop", "hoop")]),
    ("bookpack.html",    "bookpack",      [("bookpack", "bookpack")]),
]
NAV = [("/", "originals"), ("foolswise.html", "foolswise"),
       ("avant-apres.html", "avant·apres"), ("harem.html", "harem"),
       ("hoop.html", "hoop"), ("bookpack.html", "bookpack")]


def tile(design, info):
    img, url, live = info["img"], info["url"], info["live"]
    href = url if (live and url) else img
    meta = "shop &rarr;" if (live and url) else "preview"
    return (f'<div class="card"><div class="img-wrap">'
            f'<a class="img-link" href="{href}">'
            f'<img class="front" src="{img}" alt="{design}" loading="lazy"></a></div>'
            f'<div class="info"><div class="title">{design}</div>'
            f'<div class="meta">{meta}</div></div></div>')


def grouped_body(fam):
    """One continuous 3-across grid, tiles ordered by color (foolswise's group
    order; unknown groups last), then design name — so like colors sit together
    without fragmenting the grid with a label every 1-2 tiles."""
    d = data[fam]
    names = sorted(d, key=lambda n: (group_rank(COLOR.get(n, "mono")),
                                     COLOR.get(n, "mono"), n.lower()))
    return '<div class="grid">' + "".join(tile(n, d[n]) for n in names) + '</div>'


for fname, title, sections in PAGES:
    nav = "".join(
        f'<a href="{h}"{" class=\"active\"" if h == fname else ""}>{lbl}</a>'
        for h, lbl in NAV)
    body = []
    for label, fam in sections:
        n = len(data[fam])
        if len(sections) > 1:   # section header only when >1 family on the page
            body.append(f'<div class="row-label" style="font-size:2rem;color:#fff;opacity:.9;'
                        f'margin-top:2.2rem">{label} '
                        f'<span style="opacity:.4;font-size:.9rem">{n} designs</span></div>')
        else:
            body.append(f'<div class="row-label" style="opacity:.4;font-size:.9rem;'
                        f'text-transform:none;letter-spacing:0">{n} designs</div>')
        body.append(grouped_body(fam))
    html = ("<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n<meta charset=\"UTF-8\">\n"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">\n"
            "<meta name=\"robots\" content=\"noindex, nofollow\">\n"
            f"<title>toxico &mdash; {title}</title>\n" + style + "\n</head>\n<body>\n"
            f"<header>\n  <h1>{title}</h1>\n  <nav class=\"crosslink\">{nav}</nav>\n</header>\n"
            "<main id=\"main\">\n" + "\n".join(body) + "\n</main>\n"
            "<footer>&copy; 2025 toxico &mdash; elevated loungewear for the sporting life</footer>\n"
            "</body>\n</html>\n")
    (REPO / fname).write_text(html)
    print(f"wrote {fname}: {sum(len(data[f]) for _, f in sections)} tiles across {len(sections)} section(s)")

# report scratch-preview image paths (to verify they deploy)
for fam in data:
    for k, v in data[fam].items():
        if not v["live"]:
            print(f"  scratch tile {fam}/{k}: {v['img']}")
