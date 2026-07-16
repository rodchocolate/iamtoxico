#!/usr/bin/env python3
"""Generate per-design pages for the originals (index.html), mirroring the
scratch board's per-drop pages: one designs/<slug>/ page per row, and the
index row headers linked via row.href.

    python3 scripts/build_design_pages.py
"""
import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "index.html"
OUT = ROOT / "designs"


def slugify(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower()
    return s or "design"


PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>toxico — {label}</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600&display=swap');
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    font-family: 'Space Grotesk', sans-serif; color: #fff;
    background: #0b0b0b url('../../bg-graffiti-10.jpg') center center / cover no-repeat fixed;
    min-height: 100vh;
  }}
  body::before {{ content: ''; position: fixed; inset: 0; background: rgba(0,0,0,.55); z-index: 0; }}
  header, main, footer {{ position: relative; z-index: 1; }}
  header {{
    padding: 1.5rem 2rem; display: flex; align-items: baseline; gap: 1rem;
    max-width: 1280px; margin: 0 auto;
  }}
  header h1 {{ font-size: 1.6rem; font-weight: 600; letter-spacing: .04em; text-transform: lowercase; }}
  .back {{ font-size: .8rem; opacity: .6; color: #fff; text-decoration: none; }}
  .back:hover {{ opacity: 1; color: #ffc800; }}
  main {{ padding: 1rem 2rem 4rem; max-width: 1280px; margin: 0 auto; }}
  .grid {{
    display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
    gap: 1.4rem;
  }}
  .card {{
    background: rgba(255,255,255,.06); border: 1px solid rgba(255,255,255,.1);
    border-radius: 12px; overflow: hidden; position: relative; transition: transform .25s, border-color .25s;
  }}
  .card:hover {{ transform: translateY(-4px); border-color: rgba(255,255,255,.25); }}
  .card .img-wrap {{ position: relative; width: 100%; aspect-ratio: 1; overflow: hidden; background: #1a1a1a; }}
  .card .img-wrap a.img-link {{ display: block; width: 100%; height: 100%; }}
  .card .img-wrap img {{ width: 100%; height: 100%; object-fit: cover; transition: opacity .3s; }}
  .card .img-wrap img.back {{ position: absolute; inset: 0; opacity: 0; }}
  .card:hover .img-wrap img.front {{ opacity: 0; }}
  .card:hover .img-wrap img.back  {{ opacity: 1; }}
  .card .info {{ padding: .9rem 1rem; }}
  .card .title {{ font-size: .85rem; font-weight: 600; margin-bottom: .2rem; }}
  .card .meta {{ font-size: .7rem; opacity: .65; text-transform: lowercase; }}
  footer {{ text-align: center; padding: 1rem; font-size: .7rem; opacity: .5; max-width: 1280px; margin: 0 auto; }}
</style>
</head>
<body>
<header>
  <h1>{label}</h1>
  <a class="back" href="../../">← back to originals</a>
</header>
<main id="main"></main>
<footer>&copy; 2026 toxico</footer>
<script>
function tileHtml(p) {{
  let imgs = '<img class="front" src="' + p.f + '" alt="' + p.t + '" loading="lazy">' +
             (p.b ? '<img class="back" src="' + p.b + '" alt="' + p.t + ' back" loading="lazy">' : '');
  if (p.u) imgs = '<a class="img-link" href="' + p.u + '" target="_blank" rel="noopener">' + imgs + '</a>';
  return '<div class="card">' +
           '<div class="img-wrap">' + imgs + '</div>' +
           '<div class="info">' +
             '<div class="title">' + (p.t || '') + '</div>' +
             '<div class="meta">' + (p.y || '') + '</div>' +
           '</div>' +
         '</div>';
}}
document.addEventListener('DOMContentLoaded', () => {{
  const tiles = JSON.parse(document.getElementById('tiles-data').textContent);
  document.getElementById('main').innerHTML =
    '<div class="grid">' + tiles.map(tileHtml).join('') + '</div>';
}});
</script>
<script type="application/json" id="tiles-data">
{tiles_json}
</script>
</body>
</html>
"""


def main() -> None:
    html = INDEX.read_text(encoding="utf-8")
    m = re.search(r'(<script type="application/json" id="tiles-data">)(.*?)(</script>)', html, re.S)
    if not m:
        raise SystemExit("index.html tiles-data block not found")
    data = json.loads(m.group(2))
    for row in data.get("rows", []):
        slug = slugify(row["label"])
        row["href"] = f"designs/{slug}/"
        out_dir = OUT / slug
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "index.html").write_text(
            PAGE.format(label=row["label"],
                        tiles_json=json.dumps(row.get("tiles", []), indent=1)),
            encoding="utf-8")
    new_html = html[:m.start()] + m.group(1) + json.dumps(data, indent=2) + m.group(3) + html[m.end():]
    INDEX.write_text(new_html, encoding="utf-8")
    print(f"built {len(data.get('rows', []))} design pages; index hrefs updated")


if __name__ == "__main__":
    main()
