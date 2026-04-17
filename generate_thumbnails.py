"""
Generate 1280x720 thumbnails for each article in the JSON export.
Background: recurring self-storage theme (boxes, warehouse silhouette).
Only the article title changes per thumbnail.
Adds a `thumbnail` field (base64 PNG, data URI) to each article.
"""

import base64
import io
import json
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

SRC = Path("articles-export-2026-04-17_batch2_lille_cleaned.json")
DST = Path("articles-export-2026-04-17_batch2_lille_with_thumbnails.json")

W, H = 1280, 720

# Brand palette (storage / garde-meuble theme)
NAVY = (18, 35, 64)
NAVY_DARK = (10, 20, 40)
ORANGE = (245, 145, 32)
ORANGE_LIGHT = (255, 179, 71)
WHITE = (255, 255, 255)
OFFWHITE = (235, 240, 250)
BOX_FILL = (214, 168, 110)
BOX_EDGE = (140, 98, 55)

FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REG = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


def vertical_gradient(size, top, bottom):
    w, h = size
    base = Image.new("RGB", (1, h))
    px = base.load()
    for y in range(h):
        t = y / (h - 1)
        px[0, y] = (
            int(top[0] + (bottom[0] - top[0]) * t),
            int(top[1] + (bottom[1] - top[1]) * t),
            int(top[2] + (bottom[2] - top[2]) * t),
        )
    return base.resize((w, h))


def draw_storage_boxes(draw):
    """Stylised storage boxes/containers stacked in the lower-right corner."""
    # Stacked container rows (three rows)
    rows = [
        {"y": 520, "boxes": [(820, 140), (970, 140), (1120, 140)]},
        {"y": 380, "boxes": [(895, 140), (1045, 140)]},
        {"y": 240, "boxes": [(970, 140)]},
    ]
    for row in rows:
        y = row["y"]
        for x, w in row["boxes"]:
            # Container body
            draw.rectangle([x, y, x + w, y + 130], fill=BOX_FILL, outline=BOX_EDGE, width=3)
            # Door ridges
            for i in range(1, 6):
                rx = x + int(w * i / 6)
                draw.line([(rx, y + 10), (rx, y + 120)], fill=BOX_EDGE, width=1)
            # Top handle
            draw.rectangle([x + w // 2 - 12, y - 6, x + w // 2 + 12, y], fill=BOX_EDGE)
            # Lock
            draw.rectangle([x + w // 2 - 5, y + 60, x + w // 2 + 5, y + 75], fill=NAVY)


def draw_padlock(draw, cx, cy, size=46, color=ORANGE):
    """Simple padlock icon for branding feel."""
    # Shackle (arc approximation via two arcs)
    r = size // 2
    draw.arc([cx - r, cy - r - r // 2, cx + r, cy + r // 2], start=180, end=360, fill=color, width=6)
    # Body
    draw.rounded_rectangle(
        [cx - r, cy, cx + r, cy + r + 8], radius=4, fill=color
    )


def wrap_title(title, font, max_width, draw):
    """Word-wrap a title to fit within max_width pixels. Returns list of lines."""
    words = title.split()
    lines = []
    current = []
    for word in words:
        test = " ".join(current + [word])
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current.append(word)
        else:
            if current:
                lines.append(" ".join(current))
            current = [word]
    if current:
        lines.append(" ".join(current))
    return lines


def fit_title(title, draw, max_width, max_lines=4):
    """Pick the largest font size so the title fits in max_lines."""
    for size in (64, 58, 52, 48, 44, 40, 36):
        font = ImageFont.truetype(FONT_BOLD, size)
        lines = wrap_title(title, font, max_width, draw)
        if len(lines) <= max_lines:
            return font, lines, size
    return font, lines, size  # fallback


def build_background():
    """Create the recurring background (same for every thumbnail)."""
    bg = vertical_gradient((W, H), NAVY, NAVY_DARK)

    # Subtle diagonal accent strip
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    od.polygon([(0, 640), (W, 540), (W, 720), (0, 720)], fill=(245, 145, 32, 30))
    bg = Image.alpha_composite(bg.convert("RGBA"), overlay).convert("RGB")

    draw = ImageDraw.Draw(bg)

    # Grid of faint dots (warehouse floor feel)
    for y in range(40, H, 48):
        for x in range(40, W, 48):
            draw.ellipse([x, y, x + 2, y + 2], fill=(255, 255, 255, 20))

    # Storage boxes decor (right side)
    draw_storage_boxes(draw)

    # Orange accent bar (left edge)
    draw.rectangle([0, 0, 12, H], fill=ORANGE)

    # Brand block (top-left)
    draw_padlock(draw, 80, 75, size=38, color=ORANGE)
    brand_font = ImageFont.truetype(FONT_BOLD, 26)
    draw.text((125, 55), "location-gardemeuble.fr", font=brand_font, fill=WHITE)
    tag_font = ImageFont.truetype(FONT_REG, 16)
    draw.text((125, 90), "Self-stockage & garde-meuble", font=tag_font, fill=ORANGE_LIGHT)

    # Footer bar
    draw.rectangle([0, H - 60, W, H], fill=(0, 0, 0, 0))
    foot_font = ImageFont.truetype(FONT_REG, 18)
    draw.text((40, H - 42), "Analyse du marche 2026  -  Hauts-de-France", font=foot_font, fill=OFFWHITE)

    return bg


def render_thumbnail(base_bg, title):
    img = base_bg.copy()
    draw = ImageDraw.Draw(img)

    # Title box on the left (avoid the container stack on the right)
    margin_left = 60
    text_max_w = 680  # leave room for boxes on the right

    # Small label above title
    label_font = ImageFont.truetype(FONT_BOLD, 22)
    draw.text((margin_left, 180), "MARCHE DU SELF-STOCKAGE", font=label_font, fill=ORANGE)

    # Orange underline
    draw.rectangle([margin_left, 214, margin_left + 80, 218], fill=ORANGE)

    font, lines, size = fit_title(title, draw, text_max_w, max_lines=5)

    line_h = int(size * 1.15)
    total_h = line_h * len(lines)
    y = 260 + max(0, (260 - total_h) // 2)
    for line in lines:
        # Slight shadow for legibility
        draw.text((margin_left + 2, y + 2), line, font=font, fill=(0, 0, 0))
        draw.text((margin_left, y), line, font=font, fill=WHITE)
        y += line_h

    return img


def main():
    with SRC.open("r", encoding="utf-8") as f:
        articles = json.load(f)

    base_bg = build_background()

    for art in articles:
        # Use a shorter, cleaner title (strip " en 2026 : ..." subtitle if too long)
        title = art["title"]
        # Prefer a punchy form: keep part before the first " : "
        if " : " in title and len(title) > 80:
            title = title.split(" : ")[0]

        img = render_thumbnail(base_bg, title)
        buf = io.BytesIO()
        img.save(buf, format="PNG", optimize=True)
        b64 = base64.b64encode(buf.getvalue()).decode("ascii")
        art["thumbnail"] = f"data:image/png;base64,{b64}"

    with DST.open("w", encoding="utf-8") as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)

    # Also save one preview PNG to inspect visually
    preview = render_thumbnail(base_bg, articles[0]["title"].split(" : ")[0])
    preview.save("thumbnail_preview.png")
    print(f"Wrote {DST} with {len(articles)} articles.")
    print("Preview: thumbnail_preview.png")


if __name__ == "__main__":
    main()
