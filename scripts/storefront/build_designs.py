#!/usr/bin/env python3
"""designs.html — all source images, three color-ordered sections:
  originals (6, mapped bg-graffiti/pattern/toxico), foolswise (29 fw-designs),
  scratch (29, extracted from the drop emails). Every tile shows the raw source
  image; no hover swap (mapping is confirmed)."""
import json, sys
from pathlib import Path
sys.path.insert(0, "/private/tmp/claude-501/-Users-melodiclabs/dc8710a6-f1c6-441a-af70-95bb90920b0c/scratchpad")
from color_group import classify

REPO = Path("/Users/melodiclabs/hermes-runtime/rooot/iamtoxico.com")
cm = json.load(open("/tmp/colormap.json"))
COLOR = {k.lower(): v for k, v in cm["color"].items()}
GORDER = cm["order"]
def rank(g): return GORDER.index(g) if g in GORDER else len(GORDER)
def norm(g): return " + ".join(sorted(x.strip() for x in g.split("+"))) if "+" in g else g

THEMES = ["Base","Summer","Winter","Spring","Fall","Birthday","Nightclub","Extra","Stripclub",
          "Casino","Racetrack","SRT8","Ski","Snowboard","Aspen","Whistler","Ibiza","Miami",
          "Snowbird","Hollywood","Kauai","Robben Island","Oaxaca","Sedona","Oregon","Vermentino",
          "Champagne","Candlelight","Botanical"]

ORIG_MAP = {
    "arctic river": "bg-graffiti-2.jpg", "frozen sky": "bg-graffiti-12.jpg",
    "hot oil": "bg-graffiti-1.jpg", "hold cards": "bg-graffiti-5.jpg",
    "cyan glow": "pattern.png", "toxico": "toxico.png",
}
scratch = json.load(open("/tmp/scratch_src.json"))  # slug -> {file,name}

fw = (REPO / "foolswise.html").read_text()
style = fw[fw.index("<style>"):fw.index("</style>") + 8]
style += """
<style>
  header nav.crosslink { display:flex; flex-wrap:wrap; gap:.25rem 1.1rem; margin-top:.5rem; }
  header nav.crosslink a { color:#888; text-decoration:none; font-size:.85rem; }
  header nav.crosslink a:hover { color:#ffc800; }
  header nav.crosslink a.active { color:#ffc800; font-weight:600; }
  .grid { display:grid; grid-template-columns:repeat(3,1fr); grid-auto-flow:row; gap:1.4rem; overflow:visible; scroll-snap-type:none; padding-bottom:0; }
  .card { scroll-snap-align:none; }
  .card:hover .img-wrap img.front { opacity:1; }
  @media (max-width:768px){ .grid { grid-template-columns:repeat(2,1fr); gap:.8rem; } }
</style>"""

def tile(name, img):
    return (f'<div class="card"><div class="img-wrap">'
            f'<a class="img-link" href="{img}" target="_blank" rel="noopener">'
            f'<img class="front" src="{img}" alt="{name}" loading="lazy"></a></div>'
            f'<div class="info"><div class="title">{name}</div>'
            f'<div class="meta">source</div></div></div>')

def color_of_local(img):
    p = REPO / img
    try: return norm(classify(str(p))) if p.exists() else "mono"
    except Exception: return "mono"

def section(title, count_note, tiles_data):
    # tiles_data: list of (name, img, colorgroup) -> color-ordered grid
    tiles_data = sorted(tiles_data, key=lambda t: (rank(t[2]), t[2], t[0].lower()))
    grid = "".join(tile(n, i) for n, i, _ in tiles_data)
    return (f'<div class="row-label" style="font-size:2rem;color:#fff;opacity:.9;margin-top:2.2rem">{title} '
            f'<span style="opacity:.4;font-size:.9rem">{count_note}</span></div>\n'
            f'<div class="grid">{grid}</div>')

# originals (color from confirmed design color)
orig = [(n, ORIG_MAP[n], COLOR.get(n, "mono")) for n in ORIG_MAP]
# foolswise
fwd = [(THEMES[n-1].lower(), f"fw-designs/{n:02d}.png", COLOR.get(THEMES[n-1].lower(), "mono")) for n in range(1, 30)]
# scratch (classify each image)
scr = [(v["name"], v["file"], color_of_local(v["file"])) for v in scratch.values()]

NAV = [("/", "originals"), ("foolswise.html", "foolswise"), ("designs.html", "designs"),
       ("avant-apres.html", "avant·apres"), ("harem.html", "harem"), ("hoop.html", "hoop"), ("bookpack.html", "bookpack")]
nav = "".join(f'<a href="{h}"{" class=\"active\"" if h == "designs.html" else ""}>{l}</a>' for h, l in NAV)

body = ("<div class=\"row-label\" style=\"font-size:2rem;color:#fff;opacity:.9\">originals "
        f"<span style=\"opacity:.4;font-size:.9rem\">{len(orig)} source</span></div>\n"
        f"<div class=\"grid\">{''.join(tile(n,i) for n,i,_ in sorted(orig, key=lambda t:(rank(t[2]),t[2],t[0])))}</div>\n"
        + section("foolswise", f"{len(fwd)} source", fwd) + "\n"
        + section("scratch", f"{len(scr)} source", scr))

html = ("<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n<meta charset=\"UTF-8\">\n"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">\n"
        "<meta name=\"robots\" content=\"noindex, nofollow\">\n"
        "<title>toxico &mdash; designs</title>\n" + style + "\n</head>\n<body>\n"
        "<header>\n  <h1>designs</h1>\n  <nav class=\"crosslink\">" + nav + "</nav>\n</header>\n"
        "<main id=\"main\">\n" + body + "\n</main>\n"
        "<footer>&copy; 2025 toxico &mdash; elevated loungewear for the sporting life</footer>\n</body>\n</html>\n")
(REPO / "designs.html").write_text(html)
print(f"wrote designs.html: {len(orig)} originals + {len(fwd)} foolswise + {len(scr)} scratch = {len(orig)+len(fwd)+len(scr)} tiles")
