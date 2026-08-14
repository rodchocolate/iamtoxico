"""foolswise back lookbook — 8.5x11 saddle-stitch booklet PDF for Staples.

32 pages (multiple of 4): cover, 29 design pages (color order from
foolswise.html), contact page, back cover. 300dpi with 1/8" bleed.
Design pages: name + swatch, hero avant back, row of other product backs.
"""
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps

REPO = Path('/Users/melodiclabs/hermes-runtime/rooot/iamtoxico.com')
OUT = Path('/Users/melodiclabs/Library/Mobile Documents/com~apple~CloudDocs/rooot/FOOLSWISE_BACK_LOOKBOOK_8.5x11.pdf')
FONT = str(Path(__file__).resolve().parent / "SpaceGrotesk.ttf")

DPI = 300
BLEED = int(0.125 * DPI)              # 38px
W, H = 2550 + 2*BLEED, 3300 + 2*BLEED # 2626 x 3376
MARGIN = BLEED + int(0.5 * DPI)       # 1/2" inside trim

NAMES = {'15':'aspen','1':'base','6':'birthday','29':'botanical','28':'candlelight',
 '10':'casino','27':'champagne','8':'extra','5':'fall','20':'hollywood','17':'ibiza',
 '21':'kauai','18':'miami','7':'nightclub','23':'oaxaca','25':'oregon','11':'racetrack',
 '22':'robben island','24':'sedona','13':'ski','19':'snowbird','14':'snowboard',
 '4':'spring','12':'srt8','9':'stripclub','2':'summer','26':'vermentino',
 '16':'whistler','3':'winter'}
ORDER = [("03","blue"),("13","blue"),("14","blue"),("19","blue"),("29","blue"),
 ("05","orange"),("20","orange"),("24","orange"),("27","orange"),("04","purple"),
 ("06","purple"),("16","purple"),("17","aqua + pink"),("18","aqua + pink"),
 ("07","blue + purple"),("21","blue + purple"),("08","pink"),("09","pink"),
 ("11","red"),("12","red"),("15","aqua + blue"),("02","aqua + orange"),
 ("22","blue + orange"),("23","blue + red"),("25","green + orange"),
 ("10","green + yellow"),("01","mono"),("28","pink + purple"),("26","yellow")]
HERO_HASH = '4003c4cb'  # avant (hoodie) back

def font(size, weight=600):
    f = ImageFont.truetype(FONT, size)
    try: f.set_variation_by_axes([weight])
    except Exception: pass
    return f

def text(d, xy, s, size, fill, weight=600, anchor='la'):
    d.text(xy, s, font=font(size, weight), fill=fill, anchor=anchor)

def fit(img, box_w, box_h):
    return ImageOps.contain(img, (box_w, box_h))

pages = []

# ---- cover: black, 29 swatches grid + wordmark ----
cov = Image.new('RGB', (W, H), '#0b0b0b')
d = ImageDraw.Draw(cov)
gw, gh, cols = 5, 6, 5
cell = (W - 2*MARGIN - (cols-1)*24) // cols
x0, y0 = MARGIN, MARGIN + 360
for i, (num, _) in enumerate(ORDER):
    sw = Image.open(REPO / f'fw-designs/{num}.png').convert('RGB')
    sw = ImageOps.fit(sw, (cell, cell))
    r, c = divmod(i, cols)
    cov.paste(sw, (x0 + c*(cell+24), y0 + r*(cell+24)))
text(d, (MARGIN, MARGIN - 10), 'iamtoxico', 150, '#ffffff', 700)
text(d, (W - MARGIN, MARGIN + 40), 'foolswise', 84, '#ffc800', 500, anchor='ra')
pages.append(cov)

# ---- design pages ----
for num, color in ORDER:
    n = str(int(num))
    assets = REPO / f'20260809_{n}_assets'
    page = Image.new('RGB', (W, H), '#ffffff')
    d = ImageDraw.Draw(page)
    # header: name left, swatch right
    text(d, (MARGIN, MARGIN), NAMES[n], 110, '#0b0b0b', 700)
    text(d, (MARGIN, MARGIN + 150), color, 54, '#888888', 400)
    sw = ImageOps.fit(Image.open(REPO / f'fw-designs/{num}.png').convert('RGB'), (300, 300))
    page.paste(sw, (W - MARGIN - 300, MARGIN))
    # hero: avant back
    hero_h = int(H * 0.52)
    hero = fit(Image.open(assets / f'{HERO_HASH}_back_01.jpg').convert('RGB'), W - 2*MARGIN, hero_h)
    page.paste(hero, ((W - hero.width)//2, MARGIN + 380))
    # bottom row: other product backs
    others = sorted(p for p in assets.glob('*_back_*.jpg') if not p.name.startswith(HERO_HASH))
    if others:
        row_y = MARGIN + 380 + hero_h + 60
        bw = (W - 2*MARGIN - (len(others)-1)*30) // len(others)
        bh = H - MARGIN - row_y
        for i, op in enumerate(others):
            im = fit(Image.open(op).convert('RGB'), bw, bh)
            page.paste(im, (MARGIN + i*(bw+30) + (bw-im.width)//2, row_y + (bh-im.height)//2))
    pages.append(page)

# ---- contact page ----
pg = Image.new('RGB', (W, H), '#0b0b0b')
d = ImageDraw.Draw(pg)
text(d, (W//2, H//2 - 60), 'iamtoxico.com', 110, '#ffffff', 600, anchor='mm')
text(d, (W//2, H//2 + 80), 'foolswise collection', 54, '#888888', 400, anchor='mm')
pages.append(pg)

# ---- back cover ----
bc = Image.new('RGB', (W, H), '#0b0b0b')
d = ImageDraw.Draw(bc)
tox = ImageOps.fit(Image.open(REPO / 'fw-designs/01.png').convert('RGB'), (700, 700))
bc.paste(tox, ((W-700)//2, (H-700)//2 - 100))
text(d, (W//2, H - MARGIN - 40), 'iamtoxico', 66, '#ffffff', 600, anchor='mm')
pages.append(bc)

assert len(pages) == 32 and len(pages) % 4 == 0
pages[0].save(OUT, save_all=True, append_images=pages[1:],
              resolution=DPI, quality=90)
print(f'{len(pages)} pages -> {OUT}')
print(f'{OUT.stat().st_size/1e6:.1f} MB')
