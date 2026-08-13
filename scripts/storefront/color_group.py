"""Group images by dominant color; top-two combo when no color holds >= 2/3."""
import colorsys
import sys
from PIL import Image

BUCKETS = [  # (name, hue_lo, hue_hi) in degrees
    ("red", 345, 361), ("red", 0, 15), ("orange", 15, 40), ("yellow", 40, 70),
    ("green", 70, 160), ("aqua", 160, 200), ("blue", 200, 250),
    ("purple", 250, 290), ("pink", 290, 345),
]

def bucket_of(h_deg, s, v):
    # pink also claims light desaturated reds
    for name, lo, hi in BUCKETS:
        if lo <= h_deg < hi:
            if name == "red" and v > 0.75 and s < 0.55:
                return "pink"
            return name
    return None

def classify(path, thresh=2 / 3):
    im = Image.open(path).convert("RGB").resize((64, 64))
    counts = {}
    colorful = 0
    for r, g, b in im.getdata():
        h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
        if s < 0.22 or v < 0.12:      # neutral: greys, blacks, washed whites
            continue
        name = bucket_of(h * 360, s, v)
        if name:
            counts[name] = counts.get(name, 0) + 1
            colorful += 1
    if colorful < 64 * 64 * 0.05:     # essentially monochrome
        return "mono"
    ranked = sorted(counts.items(), key=lambda x: -x[1])
    top, n = ranked[0]
    if n / colorful >= thresh or len(ranked) == 1:
        return top
    return f"{top}+{ranked[1][0]}"

if __name__ == "__main__":
    for p in sys.argv[1:]:
        print(p, classify(p))
