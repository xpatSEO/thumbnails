"""
Generate thumbnails as PNG files and clean content_html.

- Writes 1280x720 PNGs to `thumbnails/<slug>.png`.
- Adds a `thumbnail` field to each article set to the relative file path.
- In `content_html`, removes every <a> tag except those whose href is
  exactly the allowed URL. For removed anchors the inner text is preserved.
"""

import json
from pathlib import Path

from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont

SRC = Path("articles-export-2026-04-17_batch2_lille_cleaned.json")
DST = Path("articles-export-2026-04-17_batch2_lille_with_thumbnails.json")
THUMB_DIR = Path("thumbnails")

ALLOWED_HREF = "https://www.location-gardemeuble.fr/garde-meuble-lille-59000-r"

W, H = 1280, 720

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
    rows = [
        {"y": 520, "boxes": [(820, 140), (970, 140), (1120, 140)]},
        {"y": 380, "boxes": [(895, 140), (1045, 140)]},
        {"y": 240, "boxes": [(970, 140)]},
    ]
    for row in rows:
        y = row["y"]
        for x, w in row["boxes"]:
            draw.rectangle([x, y, x + w, y + 130], fill=BOX_FILL, outline=BOX_EDGE, width=3)
            for i in range(1, 6):
                rx = x + int(w * i / 6)
                draw.line([(rx, y + 10), (rx, y + 120)], fill=BOX_EDGE, width=1)
            draw.rectangle([x + w // 2 - 12, y - 6, x + w // 2 + 12, y], fill=BOX_EDGE)
            draw.rectangle([x + w // 2 - 5, y + 60, x + w // 2 + 5, y + 75], fill=NAVY)


def draw_padlock(draw, cx, cy, size=46, color=ORANGE):
    r = size // 2
    draw.arc([cx - r, cy - r - r // 2, cx + r, cy + r // 2], start=180, end=360, fill=color, width=6)
    draw.rounded_rectangle([cx - r, cy, cx + r, cy + r + 8], radius=4, fill=color)


def wrap_title(title, font, max_width, draw):
    words = title.split()
    lines, current = [], []
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
    for size in (64, 58, 52, 48, 44, 40, 36):
        font = ImageFont.truetype(FONT_BOLD, size)
        lines = wrap_title(title, font, max_width, draw)
        if len(lines) <= max_lines:
            return font, lines, size
    return font, lines, size


def build_background():
    bg = vertical_gradient((W, H), NAVY, NAVY_DARK)

    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    od.polygon([(0, 640), (W, 540), (W, 720), (0, 720)], fill=(245, 145, 32, 30))
    bg = Image.alpha_composite(bg.convert("RGBA"), overlay).convert("RGB")

    draw = ImageDraw.Draw(bg)

    for y in range(40, H, 48):
        for x in range(40, W, 48):
            draw.ellipse([x, y, x + 2, y + 2], fill=(255, 255, 255, 20))

    draw_storage_boxes(draw)

    draw.rectangle([0, 0, 12, H], fill=ORANGE)

    draw_padlock(draw, 80, 75, size=38, color=ORANGE)
    brand_font = ImageFont.truetype(FONT_BOLD, 26)
    draw.text((125, 55), "location-gardemeuble.fr", font=brand_font, fill=WHITE)
    tag_font = ImageFont.truetype(FONT_REG, 16)
    draw.text((125, 90), "Self-stockage & garde-meuble", font=tag_font, fill=ORANGE_LIGHT)

    foot_font = ImageFont.truetype(FONT_REG, 18)
    draw.text((40, H - 42), "Analyse du marche 2026  -  Hauts-de-France", font=foot_font, fill=OFFWHITE)

    return bg


def render_thumbnail(base_bg, title):
    img = base_bg.copy()
    draw = ImageDraw.Draw(img)

    margin_left = 60
    text_max_w = 680

    label_font = ImageFont.truetype(FONT_BOLD, 22)
    draw.text((margin_left, 180), "MARCHE DU SELF-STOCKAGE", font=label_font, fill=ORANGE)
    draw.rectangle([margin_left, 214, margin_left + 80, 218], fill=ORANGE)

    font, lines, size = fit_title(title, draw, text_max_w, max_lines=5)

    line_h = int(size * 1.15)
    total_h = line_h * len(lines)
    y = 260 + max(0, (260 - total_h) // 2)
    for line in lines:
        draw.text((margin_left + 2, y + 2), line, font=font, fill=(0, 0, 0))
        draw.text((margin_left, y), line, font=font, fill=WHITE)
        y += line_h

    return img


def clean_html_links(html):
    """Remove every <a> tag except those pointing to ALLOWED_HREF.
    For removed anchors, preserve their inner text/HTML."""
    soup = BeautifulSoup(html, "html.parser")
    for a in soup.find_all("a"):
        href = a.get("href", "")
        if href == ALLOWED_HREF:
            continue
        a.unwrap()  # remove the <a> tag but keep its children
    return str(soup)


def main():
    THUMB_DIR.mkdir(exist_ok=True)

    with SRC.open("r", encoding="utf-8") as f:
        articles = json.load(f)

    base_bg = build_background()

    for art in articles:
        # Clean HTML
        art["content_html"] = clean_html_links(art["content_html"])

        # Thumbnail
        title = art["title"]
        if " : " in title and len(title) > 80:
            title = title.split(" : ")[0]

        img = render_thumbnail(base_bg, title)
        out_path = THUMB_DIR / f"{art['slug']}.png"
        img.save(out_path, format="PNG", optimize=True)
        art["thumbnail"] = str(out_path).replace("\\", "/")

    with DST.open("w", encoding="utf-8") as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)

    print(f"Wrote {DST} with {len(articles)} articles.")
    print(f"PNGs written to {THUMB_DIR}/ ({len(articles)} files).")


if __name__ == "__main__":
    main()
