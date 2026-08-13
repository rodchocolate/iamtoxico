#!/usr/bin/env python3
"""Restructure the toxico storefront (originals line, first pass):
  - index.html  -> a landing page (edhardy/ecko structure, toxico aesthetic)
  - originals.html -> the design grid (swatch-first per design, 3-across, tiles
    link to in-house product pages), color-ordered like designs.html
  - product/<handle>.html -> simple in-house product page (swatch first,
    front/back photos, buy -> Shopify)
  - repoints "originals" nav (/ -> originals.html) on the other pages
"""
import json, re, html as H, glob, sys
from pathlib import Path
sys.path.insert(0, "/private/tmp/claude-501/-Users-melodiclabs/dc8710a6-f1c6-441a-af70-95bb90920b0c/scratchpad")
from color_group import classify

REPO = Path("/Users/melodiclabs/hermes-runtime/rooot/iamtoxico.com")
cm = json.load(open("/tmp/colormap.json"))
COLOR = {k.lower(): v for k, v in cm["color"].items()}
GORDER = cm["order"]
def rank(g): return GORDER.index(g) if g in GORDER else len(GORDER)

ORIG_SWATCH = {
    "arctic river": "bg-graffiti-2.jpg", "cyan glow": "pattern.png",
    "frozen sky": "bg-graffiti-12.jpg", "hold cards": "bg-graffiti-5.jpg",
    "hot oil": "bg-graffiti-1.jpg", "toxico": "toxico.png",
}
META = {"tagline": "deviant but proper", "description": "the sporting life — morally casual, tastefully bold"}

# originals data (extracted once from the pre-restructure index.html grid)
data = json.load(open("/tmp/originals_data.json"))
rows = data["rows"]  # [{label, tiles:[{t,y,f,b,u}], href}]

# inject the just-published avant (hoodie) as the FIRST product on each original
# (matches foolswise order: swatch, avant, apres, harem, hoop, bookpack)
try:
    _avant = {v["design"].lower(): v for v in json.load(open("/tmp/avant_published.json")).values()}
    for r in rows:
        a = _avant.get(r["label"].lower())
        if a and a.get("url") and not any("avant" in (t.get("t", "") or "").lower() for t in r["tiles"]):
            r["tiles"].insert(0, {"t": f'{r["label"].title()} Avant', "y": "$120",
                                  "f": a.get("img", ""), "b": "", "u": a["url"]})
except FileNotFoundError:
    pass

def slug_of(u):
    return u.rstrip("/").split("/")[-1] if u else ""

# ---------- shared style + nav ----------
FONT = "@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600;700&display=swap');"
BASE = f"""
  {FONT}
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ font-family:'Space Grotesk',sans-serif; color:#fff; background:#0b0b0b url('bg-graffiti-10.jpg') center/cover no-repeat fixed; min-height:100vh; }}
  body::before {{ content:''; position:fixed; inset:0; background:rgba(0,0,0,.55); z-index:0; }}
  header,main,footer,section {{ position:relative; z-index:1; }}
  a {{ color:inherit; }}
  header {{ padding:1.5rem 2rem; display:flex; align-items:center; justify-content:space-between; gap:1rem; flex-wrap:wrap; max-width:1280px; margin:0 auto; }}
  header h1 {{ font-size:3rem; font-weight:700; letter-spacing:.04em; text-transform:lowercase; }}
  header h1 a {{ text-decoration:none; }}
  nav.crosslink {{ display:flex; flex-wrap:wrap; gap:.25rem 1.1rem; }}
  nav.crosslink a {{ color:#888; text-decoration:none; font-size:.9rem; }}
  nav.crosslink a:hover {{ color:#ffc800; }}
  nav.crosslink a.active {{ color:#ffc800; font-weight:600; }}
  main {{ padding:1rem 2rem 4rem; max-width:1280px; margin:0 auto; }}
  .row-label {{ font-size:1.4rem; opacity:.55; text-transform:uppercase; letter-spacing:.12em; margin:1.8rem 0 .6rem; }}
  a.collection-link {{ color:inherit; text-decoration:none; }} a.collection-link:hover {{ color:#ffc800; text-decoration:underline; }}
  .grid {{ display:grid; grid-auto-flow:column; grid-auto-columns:calc((100% - 2.8rem)/3); gap:1.4rem; overflow-x:auto; scroll-snap-type:x mandatory; padding-bottom:1rem; scrollbar-width:thin; }}
  .card {{ background:rgba(255,255,255,.06); border:1px solid rgba(255,255,255,.1); border-radius:12px; overflow:hidden; position:relative; scroll-snap-align:start; transition:transform .25s,border-color .25s; }}
  .card:hover {{ transform:translateY(-4px); border-color:rgba(255,255,255,.25); }}
  .card .img-wrap {{ position:relative; width:100%; aspect-ratio:1; overflow:hidden; background:#1a1a1a; }}
  .card .img-wrap a.img-link {{ display:block; width:100%; height:100%; }}
  .card .img-wrap img {{ width:100%; height:100%; object-fit:cover; transition:opacity .3s; }}
  .card .img-wrap img.back {{ position:absolute; inset:0; opacity:0; }}
  .card.has-back:hover .img-wrap img.front {{ opacity:0; }}
  .card.has-back:hover .img-wrap img.back {{ opacity:1; }}
  .card .info {{ padding:.9rem 1rem; }}
  .card .title {{ font-size:.85rem; font-weight:600; margin-bottom:.2rem; }}
  .card .meta {{ font-size:.7rem; opacity:.65; text-transform:lowercase; }}
  a.card {{ text-decoration:none; }}
  footer {{ text-align:center; padding:2rem; color:rgba(255,255,255,.3); font-size:.78rem; }}
  @media (max-width:768px){{ header h1{{font-size:2.2rem;}} main{{padding:1rem 1rem 3rem;}} .grid{{grid-auto-columns:calc((100% - .8rem)/2); gap:.8rem;}} }}
"""

NAV = [("/originals.html","originals"),("/foolswise.html","foolswise"),("/designs.html","designs"),
       ("/scratch/","scratch"),("/avant-apres.html","avant·apres"),("/harem.html","harem"),
       ("/hoop.html","hoop"),("/bookpack.html","bookpack")]
def nav_html(active):
    return '<nav class="crosslink">'+"".join(
        f'<a href="{h}"{" class=\"active\"" if l==active else ""}>{l}</a>' for h,l in NAV)+'</nav>'

def page(title, active, body, extra_style=""):
    return (f"<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n<meta charset=\"UTF-8\">\n"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">\n"
            "<meta name=\"robots\" content=\"noindex, nofollow\">\n"
            f"<title>iamtoxico — {title}</title>\n<style>{BASE}{extra_style}</style>\n</head>\n<body>\n"
            f"<header>\n  <h1><a href=\"/\">iamtoxico</a></h1>\n  {nav_html(active)}\n</header>\n"
            f"{body}\n"
            "<footer>&copy; 2025 iamtoxico</footer>\n<script defer src='/cart.js'></script>\n</body>\n</html>\n")

# ---------- product pages ----------
PROD_DIR = REPO / "product"; PROD_DIR.mkdir(exist_ok=True)
PROD_STYLE = """
  .pmain { display:grid; grid-template-columns:1fr 1fr; gap:2.5rem; margin-top:1rem; }
  .gallery .main { width:100%; aspect-ratio:1; background:#1a1a1a; border-radius:12px; overflow:hidden; border:1px solid rgba(255,255,255,.1); }
  .gallery .main img { width:100%; height:100%; object-fit:cover; }
  .thumbs { display:flex; gap:.6rem; margin-top:.7rem; }
  .thumbs img { width:70px; height:70px; object-fit:cover; border-radius:8px; border:1px solid rgba(255,255,255,.15); cursor:pointer; opacity:.6; transition:opacity .2s; }
  .thumbs img:hover, .thumbs img.sel { opacity:1; border-color:#ffc800; }
  .pinfo h2 { font-size:2rem; font-weight:700; text-transform:lowercase; }
  .pinfo .price { font-size:1.4rem; color:#ffc800; margin:.6rem 0 1.2rem; }
  .pinfo .design { opacity:.7; margin-bottom:1.6rem; }
  .pinfo .design a { color:#ffc800; }
  .buy { display:inline-block; background:#ffc800; color:#0b0b0b; font-weight:700; text-transform:lowercase; letter-spacing:.03em; padding:.9rem 2.2rem; border-radius:10px; text-decoration:none; }
  .buy:hover { background:#fff; }
  .pinfo .note { font-size:.8rem; opacity:.5; margin-top:1rem; }
  @media (max-width:768px){ .pmain{ grid-template-columns:1fr; gap:1.2rem; } }
"""
def product_page(design, p):
    sw = ORIG_SWATCH[design.lower()]
    imgs = [(sw, "pattern"), (p["f"], "front")] + ([(p["b"], "back")] if p.get("b") else [])
    thumbs = "".join(f'<img src="{s}" alt="{lbl}" data-src="{s}" class="{"sel" if i==1 else ""}" onclick="document.getElementById(\'pm\').src=this.dataset.src;document.querySelectorAll(\'.thumbs img\').forEach(t=>t.classList.remove(\'sel\'));this.classList.add(\'sel\')">'
                     for i,(s,lbl) in enumerate(imgs))
    body = (f'<main>\n<div class="pmain">\n'
            f'<div class="gallery"><div class="main"><img id="pm" src="{p["f"]}" alt="{H.escape(p["t"])}"></div>'
            f'<div class="thumbs">{thumbs}</div></div>\n'
            f'<div class="pinfo"><h2>{H.escape(p["t"].lower())}</h2>'
            f'<div class="price">{p.get("y","")}</div>'
            f'<div class="design">design: <a href="/designs/{design.lower().replace(" ","-")}/">{design.lower()}</a></div>'
            f'<a class="buy" href="{p["u"]}" target="_blank" rel="noopener">buy</a>'
            f'</div>\n</div>\n</main>')
    return page(p["t"].lower(), "originals", body, PROD_STYLE)

for row in rows:
    for p in row["tiles"]:
        sl = slug_of(p["u"])
        if sl:
            (PROD_DIR / f"{sl}.html").write_text(product_page(row["label"], p))
n_prod = sum(len(r["tiles"]) for r in rows)

# ---------- originals.html (swatch-first, color-ordered sections) ----------
def ptile(p):
    sl = slug_of(p["u"]); href = f"product/{sl}.html"
    back = f'<img class="back" src="{p["b"]}" alt="{H.escape(p["t"])} back" loading="lazy">' if p.get("b") else ""
    cls = "card has-back" if p.get("b") else "card"
    return (f'<a class="{cls}" href="{href}"><div class="img-wrap">'
            f'<img class="front" src="{p["f"]}" alt="{H.escape(p["t"])}" loading="lazy">{back}</div>'
            f'<div class="info"><div class="title">{H.escape(p["t"])}</div>'
            f'<div class="meta">{p.get("y","")}</div></div></a>')
def swatch_tile(design):
    sw = ORIG_SWATCH[design.lower()]
    return (f'<a class="card" href="/designs/{design.lower().replace(" ","-")}/"><div class="img-wrap">'
            f'<img class="front" src="{sw}" alt="{design} pattern" loading="lazy"></div>'
            f'<div class="info"><div class="title">{design.lower()}</div><div class="meta">pattern</div></div></a>')

ordered = sorted(rows, key=lambda r: (rank(COLOR.get(r["label"].lower(), "mono")), r["label"].lower()))
sections = []
for r in ordered:
    anchor = r["label"].lower().replace(" ", "-")
    sections.append(f'<div class="row-label" id="{anchor}">{r["label"].lower()}</div>')
    grid = swatch_tile(r["label"]) + "".join(ptile(p) for p in r["tiles"])
    sections.append(f'<div class="grid">{grid}</div>')
originals_body = '<main id="main">\n' + "\n".join(sections) + '\n</main>'
(REPO / "originals.html").write_text(page("originals", "originals", originals_body))

# ---------- landing index.html ----------
LAND_STYLE = """
  html { scroll-behavior:smooth; }
  .hero { position:relative; height:82vh; min-height:520px; display:flex; flex-direction:column; align-items:center; justify-content:center; text-align:center; overflow:hidden; cursor:pointer; }
  .hero-bg { position:absolute; inset:0; background-size:cover; background-position:center; opacity:0; transition:opacity 1.4s ease; z-index:-2; }
  .hero-bg.show { opacity:1; }
  .hero .overlay { position:absolute; inset:0; background:rgba(0,0,0,.5); z-index:-1; }
  .hero .brand { font-size:clamp(3rem,12vw,8rem); font-weight:700; text-transform:lowercase; letter-spacing:.04em; line-height:.9; }
  .hero .ctas { margin-top:2rem; display:flex; gap:1rem; flex-wrap:wrap; justify-content:center; }
  .btn { padding:.85rem 2rem; border-radius:10px; text-decoration:none; font-weight:700; text-transform:lowercase; letter-spacing:.03em; }
  .btn.primary { background:#ffc800; color:#0b0b0b; } .btn.primary:hover { background:#fff; }
  .btn.ghost { border:1px solid rgba(255,255,255,.5); color:#fff; } .btn.ghost:hover { border-color:#ffc800; color:#ffc800; }
  .sec { max-width:1280px; margin:0 auto; padding:2.5rem 2rem; }
  .sec h2 { font-size:1.4rem; text-transform:uppercase; letter-spacing:.12em; opacity:.6; margin-bottom:1.2rem; }
  .collections a.card .img-wrap { aspect-ratio:4/3; }
  .collections .title { font-size:1.05rem; text-transform:lowercase; }
  .blurb { text-align:center; padding:3rem 2rem; }
  .blurb .d { font-size:1.6rem; font-weight:600; text-transform:lowercase; }
  .blurb .t { margin-top:.6rem; opacity:.6; text-transform:lowercase; letter-spacing:.08em; }
"""
# hero rotates through the actual pattern swatches (toxico first), used as-is
CYCLE = ["toxico.png", "bg-graffiti-2.jpg", "pattern.png", "bg-graffiti-12.jpg",
         "bg-graffiti-5.jpg", "bg-graffiti-1.jpg"] + [f"fw-designs/{n:02d}.png" for n in range(1, 30)]
ROTATE_JS = ("<script>(function(){var SW=" + json.dumps(CYCLE) + ";"
             "var a=document.querySelector('.bgA'),b=document.querySelector('.bgB');"
             "a.style.backgroundImage=\"url('\"+SW[0]+\"')\";a.classList.add('show');"
             "var i=0,cur=a,nxt=b;setInterval(function(){i=(i+1)%SW.length;"
             "nxt.style.backgroundImage=\"url('\"+SW[i]+\"')\";nxt.classList.add('show');"
             "cur.classList.remove('show');var t=cur;cur=nxt;nxt=t;},4500);})();</script>")

# all product rows: originals (in-house links) + foolswise (shopify links), color-ordered like designs.html
def orig_row(r):
    return swatch_tile(r["label"]) + "".join(ptile(p) for p in r["tiles"])
combined = [(r["label"].lower(), COLOR.get(r["label"].lower(), "mono"), orig_row(r),
             f'/designs/{r["label"].lower().replace(" ", "-")}/') for r in rows]
fwtext = (REPO / "foolswise.html").read_text()
for label, grid_inner in re.findall(
        r'<div class="row-label"[^>]*>(.*?)</div>\s*<div class="grid">(.*?)</div>\s*(?=<div class="row-label|</main>)',
        fwtext, re.S):
    name = re.sub(r'<[^>]+>', '', label).strip()
    name = re.sub(r'^\d+\s*&mdash;\s*', '', name).split('(')[0].strip().lower()
    combined.append((name, COLOR.get(name, "mono"), grid_inner, "/foolswise.html"))

# scratch drops: real live products (buy via the shopify product page 'u'); drop puffer tiles
def color_of(img):
    p = REPO / img
    try:
        g = classify(str(p)); return " + ".join(sorted(x.strip() for x in g.split("+"))) if "+" in g else g
    except Exception:
        return "mono"
def shop_tile(t):
    return (f'<a class="card" href="{t["u"]}" target="_blank" rel="noopener"><div class="img-wrap">'
            f'<img class="front" src="{t["f"]}" alt="{H.escape(t.get("t",""))}" loading="lazy"></div>'
            f'<div class="info"><div class="title">{H.escape(t.get("t",""))}</div>'
            f'<div class="meta">{t.get("y","")}</div></div></a>')
name_to_src = {v["name"]: v["file"] for v in json.load(open("/tmp/scratch_src.json")).values()}
n_scratch = 0
for pg in sorted(glob.glob(str(REPO / "scratch" / "*" / "index.html"))):
    dname = re.sub(r'-drop-\d+$', '', Path(pg).parent.name).replace('-', ' ')
    m = re.search(r'id="tiles-data">\s*(\[.*?\])\s*</script>', open(pg).read(), re.S)
    if not m:
        continue
    try:
        tiles = json.loads(m.group(1))
    except Exception:
        continue
    tiles = [t for t in tiles if t.get("u") and "puffer" not in (t.get("t", "") or "").lower()]
    if not tiles:
        continue
    sw = name_to_src.get(dname)
    swtile = ("" if not sw else
              f'<a class="card" href="{sw}"><div class="img-wrap">'
              f'<img class="front" src="{sw}" alt="{dname} pattern" loading="lazy"></div>'
              f'<div class="info"><div class="title">{dname}</div><div class="meta">pattern</div></div></a>')
    combined.append((dname, color_of(sw) if sw else "mono",
                     swtile + "".join(shop_tile(t) for t in tiles),
                     f'/scratch/{Path(pg).parent.name}/'))
    n_scratch += 1

combined.sort(key=lambda x: (rank(x[1]), x[1], x[0]))
prod_rows_html = "\n".join(
    f'<div class="row-label"><a class="collection-link" href="{href}">{name} &rarr;</a></div>\n'
    f'<div class="grid">{grid}</div>' for name, _, grid, href in combined)

land_body = ('<section class="hero" onclick="location.hash=\'products\'">\n'
             '  <div class="hero-bg bgA"></div>\n  <div class="hero-bg bgB"></div>\n  <div class="overlay"></div>\n'
             '</section>\n'
             f'<main id="products">\n{prod_rows_html}\n</main>')
land = (f"<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n<meta charset=\"UTF-8\">\n"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">\n"
        "<meta name=\"robots\" content=\"noindex, nofollow\">\n"
        f"<title>iamtoxico</title>\n<style>{BASE}{LAND_STYLE}</style>\n</head>\n<body>\n"
        f"<header>\n  <h1><a href=\"/\">iamtoxico</a></h1>\n  {nav_html('')}\n</header>\n"
        f"{land_body}\n<footer>&copy; 2025 iamtoxico</footer>\n{ROTATE_JS}\n<script defer src='/cart.js'></script>\n</body>\n</html>\n")
(REPO / "index.html").write_text(land)

print(f"built: index.html (landing, {len(combined)} product rows), originals.html ({len(rows)} designs), {n_prod} product pages")
