"""Draw the SYNAPSE mark at every size Brave Core uses and write PNG/ICO files.

The mark is the same as sites/browser/icon.svg in the SYNAPSE repo: a black
rounded square with a white six-node "synapse" star. It is drawn with Pillow
at 8x size and scaled down, so no SVG renderer is needed.

Usage: python make_icons.py <out_dir>
"""
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

SS = 8  # supersampling factor


def draw_mark(size: int, background: bool = True, mono: str | None = None) -> Image.Image:
    big = size * SS
    img = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    fg = (255, 255, 255, 255)
    if background:
        d.rounded_rectangle([0, 0, big - 1, big - 1], radius=int(big * 224 / 1024), fill=(10, 10, 10, 255))
    else:
        fg = (0, 0, 0, 255) if mono == "black" else (255, 255, 255, 255)
    # Geometry from icon.svg: 32x32 design grid placed at (160,160) scale 22 in a 1024 box.
    unit = big * 22 / 1024
    off = big * 160 / 1024
    if not background:  # glyph only: use the full box
        unit = big / 32
        off = 0

    def p(x, y):
        return (off + x * unit, off + y * unit)

    lines = [
        (16, 11.6, 16, 6.4), (19.81, 13.8, 24.31, 11.2), (19.81, 18.2, 24.31, 20.8),
        (16, 20.4, 16, 25.6), (12.19, 18.2, 7.69, 20.8), (12.19, 13.8, 7.69, 11.2),
    ]
    w = max(1, int(2.4 * unit))
    for x1, y1, x2, y2 in lines:
        d.line([p(x1, y1), p(x2, y2)], fill=fg, width=w)
    circles = [(16, 3.8, 2.6), (26.57, 9.9, 2.2), (26.57, 22.1, 2.6), (16, 28.2, 2.2),
               (5.43, 22.1, 2.6), (5.43, 9.9, 2.2), (16, 16, 3.4)]
    for cx, cy, r in circles:
        x, y = p(cx, cy)
        rr = r * unit
        d.ellipse([x - rr, y - rr, x + rr, y + rr], fill=fg)
    return img.resize((size, size), Image.LANCZOS)


def wordmark(height: int, color=(20, 20, 20, 255)) -> Image.Image:
    """Mark plus the word SYNAPSE, for product_logo_name_* images."""
    mark = draw_mark(height)
    font = None
    for name in ("segoeuib.ttf", "seguisb.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf"):
        try:
            font = ImageFont.truetype(name, int(height * 0.62))
            break
        except OSError:
            continue
    if font is None:
        font = ImageFont.load_default()
    text = "SYNAPSE"
    tmp = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    l, t, r, b = tmp.textbbox((0, 0), text, font=font)
    gap = int(height * 0.3)
    img = Image.new("RGBA", (height + gap + (r - l) + 2, height), (0, 0, 0, 0))
    img.paste(mark, (0, 0), mark)
    ImageDraw.Draw(img).text((height + gap - l, (height - (b - t)) // 2 - t), text, font=font, fill=color)
    return img


def main(out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    for s in (16, 22, 24, 32, 48, 64, 128, 256):
        draw_mark(s).save(out / f"mark_{s}.png")
    draw_mark(22, background=False, mono="black").save(out / "mark_22_mono.png")
    draw_mark(64, background=False, mono="white").save(out / "mark_white.png")
    wordmark(22).save(out / "name_22.png")
    wordmark(22, (255, 255, 255, 255)).save(out / "name_22_white.png")
    wordmark(48).save(out / "name_48.png")
    wordmark(44).save(out / "name_44.png")
    wordmark(96).save(out / "name_96.png")
    wordmark(96, (255, 255, 255, 255)).save(out / "name_44_white_2x.png")
    big = draw_mark(256)
    big.save(out / "synapse.ico", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    # Windows Start tiles: 150x150 and 70x70 with transparent padding.
    for name, s, m in (("Logo.png", 150, 88), ("SmallLogo.png", 70, 44)):
        tile = Image.new("RGBA", (s, s), (0, 0, 0, 0))
        mk = draw_mark(m)
        tile.paste(mk, ((s - m) // 2, (s - m) // 2), mk)
        tile.save(out / name)
    print("icons written to", out)


if __name__ == "__main__":
    main(Path(sys.argv[1]))
