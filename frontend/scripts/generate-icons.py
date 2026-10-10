# Generate PWA icons (graduation cap) untuk Study Agent.
# Jalankan: <python> frontend/scripts/generate-icons.py
# Butuh Pillow (sudah ada via reportlab). Output ke frontend/public/icons/.

from pathlib import Path

from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parents[1] / "public" / "icons"
BG = (17, 24, 39)       # #111827
FG = (255, 255, 255)


def draw_cap(draw: ImageDraw.ImageDraw, cx: float, cy: float, size: float) -> None:
    half = size / 2
    # Mortarboard (diamond)
    draw.polygon(
        [(cx, cy - half * 0.5), (cx + half, cy), (cx, cy + half * 0.5), (cx - half, cy)],
        fill=FG,
    )
    # Base (trapezoid)
    bw = half * 0.6
    draw.polygon(
        [
            (cx - bw, cy + half * 0.12),
            (cx + bw, cy + half * 0.12),
            (cx + bw * 0.72, cy + half * 0.72),
            (cx - bw * 0.72, cy + half * 0.72),
        ],
        fill=FG,
    )
    # Tassel
    line_w = max(2, int(size * 0.035))
    draw.line([(cx + half * 0.72, cy), (cx + half * 0.9, cy + half * 0.58)], fill=FG, width=line_w)
    r = size * 0.07
    tx, ty = cx + half * 0.9, cy + half * 0.58
    draw.ellipse([tx - r, ty - r, tx + r, ty + r], fill=FG)


def make_icon(px: int, maskable: bool) -> Image.Image:
    img = Image.new("RGBA", (px, px), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    if maskable:
        # Full bleed (safe zone ~80%) untuk maskable.
        draw.rectangle([0, 0, px, px], fill=BG)
        cap = px * 0.5
    else:
        radius = int(px * 0.22)
        draw.rounded_rectangle([0, 0, px, px], radius=radius, fill=BG)
        cap = px * 0.58
    draw_cap(draw, px / 2, px / 2, cap)
    return img


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    make_icon(192, False).save(OUT / "icon-192.png")
    make_icon(512, False).save(OUT / "icon-512.png")
    make_icon(192, True).save(OUT / "icon-maskable-192.png")
    make_icon(512, True).save(OUT / "icon-maskable-512.png")
    make_icon(180, False).save(OUT / "apple-touch-icon.png")
    print(f"Icons generated in {OUT}")


if __name__ == "__main__":
    main()
