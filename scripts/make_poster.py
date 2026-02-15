#!/usr/bin/env python3
"""
Make a simple poster from a source image with a word overlay (e.g., DREAMER),
using a high-contrast treatment similar to previous tees.

Usage:
  python scripts/make_poster.py \
    --image docs/design/reference-images/prize-fighters/black/joe-gans_bain.jpg \
    --word DREAMER \
    --out posters/joe-gans_dreamer.jpg \
    [--width 2400] [--pad 80] [--bg #000000] [--fg #FFFFFF] [--font-size 220]

Outputs a flattened RGB JPG.
"""
from __future__ import annotations
import argparse
from pathlib import Path
from PIL import Image, ImageOps, ImageFilter, ImageDraw, ImageFont


def load_font(size: int) -> ImageFont.FreeTypeFont:
    # Try Impact-like fonts; fall back to DejaVuSans-Bold.
    candidates = [
        "/System/Library/Fonts/Supplemental/Impact.ttf",
        "/Library/Fonts/Impact.ttf",
        "/System/Library/Fonts/Supplemental/Arial Black.ttf",
        "/Library/Fonts/Arial Black.ttf",
        "/System/Library/Fonts/Supplemental/DejaVuSans-Bold.ttf",
        "/Library/Fonts/DejaVuSans-Bold.ttf",
    ]
    for p in candidates:
        try:
            return ImageFont.truetype(p, size=size)
        except Exception:
            continue
    return ImageFont.load_default()


def place_word(canvas: Image.Image, word: str, fg: str, pad: int, font_size: int) -> None:
    draw = ImageDraw.Draw(canvas)
    W, H = canvas.size
    font = load_font(font_size)

    # Measure text and shrink if it overflows width - 2*pad
    text = word.upper()
    max_w = W - 2 * pad
    w, h = draw.textbbox((0, 0), text, font=font)[2:]
    while w > max_w and font_size > 24:
        font_size -= 8
        font = load_font(font_size)
        w, h = draw.textbbox((0, 0), text, font=font)[2:]

    # Position text at bottom with baseline above padding
    x = (W - w) // 2
    y = H - pad - h

    # Add subtle outline for legibility
    outline = 3
    for dx in (-outline, 0, outline):
        for dy in (-outline, 0, outline):
            if dx == 0 and dy == 0:
                continue
            draw.text((x + dx, y + dy), text, font=font, fill="#000000")
    draw.text((x, y), text, font=font, fill=fg)


def place_word_centered_band(
    canvas: Image.Image,
    text: str,
    band_box: tuple[int, int, int, int],
    fg: str,
    max_font_size: int,
    side_pad: int,
) -> None:
    draw = ImageDraw.Draw(canvas)
    text = text.upper()
    x0, y0, x1, y1 = band_box
    W = x1 - x0
    H = y1 - y0
    # Fit text to available width with side padding
    font_size = max_font_size
    font = load_font(font_size)
    w, h = draw.textbbox((0, 0), text, font=font)[2:]
    while (w > (W - 2 * side_pad) or h > H * 0.9) and font_size > 24:
        font_size -= 6
        font = load_font(font_size)
        w, h = draw.textbbox((0, 0), text, font=font)[2:]
    x = x0 + (W - w) // 2
    y = y0 + (H - h) // 2
    # Outline for legibility
    outline = max(2, font_size // 60)
    for dx in (-outline, 0, outline):
        for dy in (-outline, 0, outline):
            if dx == 0 and dy == 0:
                continue
            draw.text((x + dx, y + dy), text, font=font, fill="#000000")
    draw.text((x, y), text, font=font, fill=fg)


def stylize_image(img: Image.Image) -> Image.Image:
    # Convert to grayscale, boost contrast, subtle posterize, light grain.
    g = ImageOps.grayscale(img)
    g = ImageOps.autocontrast(g)
    g = ImageOps.equalize(g)
    # Slight unsharp to enhance edges
    g = g.filter(ImageFilter.UnsharpMask(radius=2, percent=150, threshold=3))
    return g


def make_proportional(
    image_path: Path,
    out_path: Path,
    word: str,
    width: int,
    bg: str,
    fg: str,
    template_path: Path | None,
    margin_frac: float,
    band_frac: float,
    stroke_px: int,
) -> Path:
    # Determine target aspect from template if available
    target_ratio = None
    if template_path and template_path.exists():
        try:
            t = Image.open(template_path)
            tw, th = t.size
            if tw > 0:
                target_ratio = th / float(tw)
        except Exception:
            target_ratio = None
    if not target_ratio:
        target_ratio = 1.25  # fallback aspect (H/W)

    height = int(round(width * target_ratio))
    canvas = Image.new("RGB", (width, height), color=bg)

    # Layout metrics
    margin = int(round(width * margin_frac))  # left/right and small top margin
    band_h = int(round(height * band_frac))
    top_margin = margin
    bottom_band_box = (margin, height - band_h - margin, width - margin, height - margin)

    # Image box occupies the area above the bottom band
    img_box = (margin, top_margin, width - margin, bottom_band_box[1] - margin)
    box_w = img_box[2] - img_box[0]
    box_h = img_box[1+2] - img_box[1] if False else img_box[3] - img_box[1]

    # Load and stylize
    src = Image.open(image_path).convert("RGB")
    styled = stylize_image(src)

    # Fit styled into img_box preserving aspect
    sw, sh = styled.size
    scale = min(box_w / sw, box_h / sh)
    nw, nh = int(sw * scale), int(sh * scale)
    styled_resized = styled.resize((nw, nh), Image.LANCZOS)

    # Optional white border around image
    if stroke_px > 0:
        bordered = ImageOps.expand(styled_resized, border=stroke_px, fill="#FFFFFF")
    else:
        bordered = styled_resized

    # Paste centered within img_box
    bx = img_box[0] + (box_w - bordered.size[0]) // 2
    by = img_box[1] + (box_h - bordered.size[1]) // 2
    canvas.paste(bordered, (bx, by))

    # Word in bottom band
    place_word_centered_band(
        canvas,
        word,
        bottom_band_box,
        fg=fg,
        max_font_size=int(width * 0.12),
        side_pad=int(width * 0.04),
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out_path, quality=92)
    return out_path


def make_tiled(
    image_path: Path,
    out_path: Path,
    word: str,
    width: int,
    bg: str,
    fg: str,
    template_path: Path | None,
    margin_frac: float,
    tile_scale: float,
    dim_bg: float,
) -> Path:
    # Aspect from template
    target_ratio = None
    if template_path and template_path.exists():
        try:
            t = Image.open(template_path)
            tw, th = t.size
            if tw > 0:
                target_ratio = th / float(tw)
        except Exception:
            target_ratio = None
    if not target_ratio:
        target_ratio = 1.25

    height = int(round(width * target_ratio))
    canvas = Image.new("RGB", (width, height), color=bg)

    # Tile area margins
    margin = int(round(width * margin_frac))
    area = (margin, margin, width - margin, height - margin)
    aw, ah = area[2] - area[0], area[3] - area[1]

    # Load and stylize tile image
    src = Image.open(image_path).convert("RGB")
    tile_img = stylize_image(src)

    # Compute tile size based on width fraction
    tw = max(64, int(width * tile_scale))
    sw, sh = tile_img.size
    scale = tw / float(sw)
    th = max(64, int(sh * scale))
    tile_resized = tile_img.resize((tw, th), Image.LANCZOS)

    # Tile across area
    for y in range(area[1], area[3], th):
        for x in range(area[0], area[2], tw):
            canvas.paste(tile_resized, (x, y))

    # Optional dim for readability
    if dim_bg > 0:
        alpha = int(max(0, min(1.0, dim_bg)) * 255)
        overlay = Image.new("RGBA", (width, height), (0, 0, 0, alpha))
        canvas = Image.alpha_composite(canvas.convert("RGBA"), overlay).convert("RGB")

    # Centered word overlay area (band around vertical center)
    band_h = int(height * 0.28)
    band_box = (margin, (height - band_h) // 2, width - margin, (height + band_h) // 2)

    # Draw text
    draw = ImageDraw.Draw(canvas)
    text = word.upper()
    max_font_size = int(width * 0.2)
    side_pad = int(width * 0.06)
    font_size = max_font_size
    font = load_font(font_size)
    w, h = draw.textbbox((0, 0), text, font=font)[2:]
    while (w > (band_box[2] - band_box[0] - 2 * side_pad) or h > band_h * 0.9) and font_size > 24:
        font_size -= 6
        font = load_font(font_size)
        w, h = draw.textbbox((0, 0), text, font=font)[2:]
    x = band_box[0] + (band_box[2] - band_box[0] - w) // 2
    y = band_box[1] + (band_box[3] - band_box[1] - h) // 2

    # Outline
    outline = max(3, font_size // 40)
    for dx in (-outline, 0, outline):
        for dy in (-outline, 0, outline):
            if dx == 0 and dy == 0:
                continue
            draw.text((x + dx, y + dy), text, font=font, fill="#000000")
    draw.text((x, y), text, font=font, fill=fg)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out_path, quality=92)
    return out_path


def make_poster(
    image_path: Path, out_path: Path, word: str, width: int, pad: int, bg: str, fg: str, font_size: int,
    mode: str = "overlay", template: Path | None = None, margin_frac: float = 0.07, band_frac: float = 0.18, stroke_px: int = 4,
    tile_scale: float = 0.35, dim_bg: float = 0.15
) -> Path:
    if mode == "proportional":
        return make_proportional(
            image_path=image_path,
            out_path=out_path,
            word=word,
            width=width,
            bg=bg,
            fg=fg,
            template_path=template,
            margin_frac=margin_frac,
            band_frac=band_frac,
            stroke_px=stroke_px,
        )
    if mode == "tiled":
        return make_tiled(
            image_path=image_path,
            out_path=out_path,
            word=word,
            width=width,
            bg=bg,
            fg=fg,
            template_path=template,
            margin_frac=margin_frac,
            tile_scale=tile_scale,
            dim_bg=dim_bg,
        )

    img = Image.open(image_path).convert("RGB")

    # Resize to requested width, keep aspect.
    w0, h0 = img.size
    scale = width / float(w0)
    new_h = int(h0 * scale)
    img = img.resize((width, new_h), Image.LANCZOS)

    # Stylize and expand canvas with padding for word.
    styled = stylize_image(img)
    pad_h = pad + int(font_size * 1.2)
    canvas = Image.new("RGB", (width, new_h + pad_h), color=bg)
    canvas.paste(styled, (0, 0))

    # Word overlay
    place_word(canvas, word, fg, pad, font_size)

    # Ensure output dir
    out_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out_path, quality=92)
    return out_path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", required=True)
    ap.add_argument("--word", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--width", type=int, default=2400)
    ap.add_argument("--pad", type=int, default=80)
    ap.add_argument("--bg", default="#000000")
    ap.add_argument("--fg", default="#FFFFFF")
    ap.add_argument("--font-size", type=int, default=220)
    ap.add_argument("--mode", choices=["overlay", "proportional", "tiled"], default="overlay")
    ap.add_argument("--template")
    ap.add_argument("--margin-frac", type=float, default=0.07)
    ap.add_argument("--band-frac", type=float, default=0.18)
    ap.add_argument("--stroke-px", type=int, default=4)
    ap.add_argument("--tile-scale", type=float, default=0.35)
    ap.add_argument("--dim-bg", type=float, default=0.15)
    args = ap.parse_args()

    out = make_poster(
        image_path=Path(args.image),
        out_path=Path(args.out),
        word=args.word,
        width=args.width,
        pad=args.pad,
        bg=args.bg,
        fg=args.fg,
        font_size=args["font_size"] if isinstance(args, dict) else args.font_size,
        mode=args.mode,
        template=Path(args.template) if args.template else None,
        margin_frac=args.margin_frac,
        band_frac=args.band_frac,
        stroke_px=args.stroke_px,
        tile_scale=args.tile_scale,
        dim_bg=args.dim_bg,
    )
    print(f"Saved: {out}")


if __name__ == "__main__":
    main()
