#!/usr/bin/env python3
"""Split foolswise.html's 29 stacked family blocks into individual
foolswise/<slug>/index.html pages (mirrors build_design_pages.py's pattern for
originals), then repoint index.html + foolswise.html row-label hrefs from the
flat /foolswise.html to /foolswise/<slug>/.

Run:  python3 scripts/build_foolswise_pages.py
"""
from __future__ import annotations

import html as H
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FW_HTML = ROOT / "foolswise.html"
INDEX = ROOT / "index.html"
OUT = ROOT / "foolswise"

NAV = FW_HTML.read_text(encoding="utf-8")
NAV_BLOCK = re.search(r'(<header>.*?</header>)', NAV, re.S).group(1)

PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="robots" content="noindex, nofollow">
<title>toxico &mdash; {label_esc}</title>
<link rel="stylesheet" href="/style.css">
</head>
<body>
{nav}
<main id="main">
<div class="row-label" style="font-size:1rem;opacity:.7">{label_esc}</div>
{grid}
</main>
<footer>&copy; 2025 iamtoxico</footer>
<script defer src="/cart.js"></script>
</body>
</html>
"""


def slugify(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower()
    return s or "family"


def find_balanced_div(text: str, start: int) -> tuple[str, int]:
    """text[start:] must begin with '<div'; return (whole div incl closing tag, end index)."""
    assert text.startswith("<div", start)
    depth = 0
    i = start
    tag_re = re.compile(r"<div\b|</div>")
    while True:
        m = tag_re.search(text, i)
        if not m:
            raise ValueError("unbalanced divs")
        if m.group(0) == "<div" or m.group(0).startswith("<div"):
            depth += 1
        else:
            depth -= 1
        i = m.end()
        if depth == 0:
            return text[start:i], i


def main() -> None:
    fw_html = FW_HTML.read_text(encoding="utf-8")
    m = re.search(r'<main id="main">(.*?)</main>', fw_html, re.S)
    body = m.group(1)

    # nav row-label (color group headers) vs family row-label (has "NN &mdash; name")
    family_label_re = re.compile(
        r'<div class="row-label"[^>]*>(\d+\s*&mdash;\s*[^<]+)</div>'
    )

    families = []  # list of (num, name, label_raw, grid_html)
    for lm in family_label_re.finditer(body):
        label_raw = lm.group(1).strip()
        num, name = re.split(r"\s*&mdash;\s*", label_raw, maxsplit=1)
        grid_start = body.find('<div class="grid">', lm.end())
        if grid_start == -1 or grid_start > lm.end() + 5:
            # must immediately follow (allow no gap)
            pass
        grid_html, _ = find_balanced_div(body, grid_start)
        families.append((num.strip(), name.strip(), label_raw, grid_html))

    print(f"found {len(families)} foolswise families")

    # relative asset/product refs in foolswise.html (site root) become one level
    # deeper at foolswise/<slug>/index.html; rewrite them to site-absolute paths.
    def make_root_relative(grid: str) -> str:
        grid = re.sub(r'(href|src)="fw-designs/', r'\1="/fw-designs/', grid)
        grid = re.sub(r'(href|src)="(\d{8}_\d+_assets/)', r'\1="/\2', grid)
        return grid

    OUT.mkdir(exist_ok=True)
    slug_map = {}
    for num, name, label_raw, grid_html in families:
        slug = slugify(name)
        slug_map[label_raw] = slug
        out_dir = OUT / slug
        out_dir.mkdir(parents=True, exist_ok=True)
        page = PAGE.format(
            label_esc=H.escape(f"{num} — {name}", quote=False),
            nav=NAV_BLOCK,
            grid=make_root_relative(grid_html),
        )
        (out_dir / "index.html").write_text(page, encoding="utf-8")

    # repoint homepage row-label hrefs: /foolswise.html -> /foolswise/<slug>/
    # Homepage rows look like: <a class="collection-link" href="/foolswise.html">ski &rarr;</a>
    idx_html = INDEX.read_text(encoding="utf-8")
    name_to_slug = {name.lower(): slugify(name) for _, name, _, _ in families}

    # match href="/foolswise.html">LABEL &rarr;  (LABEL may be "color group\nNN — name")
    row_re = re.compile(r'href="(/foolswise\.html)">([^<]+?)\s*&rarr;')

    def repoint(m: re.Match) -> str:
        label_text = m.group(2).strip()
        # family name is whatever follows the last "&mdash;", else the whole label
        name_part = re.split(r"&mdash;", label_text)[-1].strip().lower()
        if name_part in name_to_slug:
            return f'href="/foolswise/{name_to_slug[name_part]}/">{m.group(2)} &rarr;'
        return m.group(0)

    new_idx, n = row_re.subn(repoint, idx_html)
    INDEX.write_text(new_idx, encoding="utf-8")
    print(f"index.html: repointed {n} foolswise family hrefs")

    print(f"built {len(families)} foolswise family pages under foolswise/<slug>/")


if __name__ == "__main__":
    main()
