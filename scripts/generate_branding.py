"""One-off generator for a YouTube channel banner + profile picture.
Dark navy/purple gradient with neon cyan/pink glow accents. Not part of the
render/upload pipeline -- run manually whenever branding needs a refresh.
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import find_font

OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "branding")

NAVY_DARK = (10, 12, 26)
PURPLE_DARK = (35, 12, 54)
NEON_CYAN = (0, 229, 255)
NEON_PINK = (255, 47, 208)
WHITE = (255, 255, 255)

CHANNEL_NAME = "DAILY LIFE VIDEOS"
TAGLINE = "psychology facts in 60 seconds"
MONOGRAM = "DL"


def glow_text(base_rgba, text, font, fill, glow_color, center, glow_radius=18, glow_boost=1.0):
    layer = Image.new("RGBA", base_rgba.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    bbox = draw.textbbox((0, 0), text, font=font)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    pos = (center[0] - w / 2 - bbox[0], center[1] - h / 2 - bbox[1])

    glow_layer = Image.new("RGBA", base_rgba.size, (0, 0, 0, 0))
    gdraw = ImageDraw.Draw(glow_layer)
    gdraw.text(pos, text, font=font, fill=(*glow_color, 255))
    glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(glow_radius))
    if glow_boost != 1.0:
        alpha = glow_layer.split()[3].point(lambda a: min(255, int(a * glow_boost)))
        glow_layer.putalpha(alpha)
    base_rgba.alpha_composite(glow_layer)

    draw.text(pos, text, font=font, fill=(*fill, 255))
    base_rgba.alpha_composite(layer)


def glow_ellipse(base_rgba, bbox, color, blur=60, alpha=110):
    layer = Image.new("RGBA", base_rgba.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    draw.ellipse(bbox, fill=(*color, alpha))
    layer = layer.filter(ImageFilter.GaussianBlur(blur))
    base_rgba.alpha_composite(layer)


def make_background(size, black, white_):
    grad = Image.linear_gradient("L").resize(size)
    return ImageOps.colorize(grad, black=black, white=white_).convert("RGBA")


def make_banner(path):
    size = (2560, 1440)
    bg = make_background(size, NAVY_DARK, PURPLE_DARK)

    glow_ellipse(bg, (-300, -300, 500, 500), NEON_CYAN, blur=180, alpha=90)
    glow_ellipse(bg, (2100, 1000, 2900, 1800), NEON_PINK, blur=200, alpha=90)

    title_font = ImageFont.truetype(find_font(), 150)
    tagline_font = ImageFont.truetype(find_font(), 54)

    cx, cy = size[0] / 2, size[1] / 2
    glow_text(bg, CHANNEL_NAME, title_font, WHITE, NEON_CYAN, (cx, cy - 40), glow_radius=22, glow_boost=1.3)

    draw = ImageDraw.Draw(bg)
    line_w = 520
    draw.line([(cx - line_w / 2, cy + 90), (cx + line_w / 2, cy + 90)], fill=(*NEON_PINK, 220), width=4)

    glow_text(bg, TAGLINE, tagline_font, (230, 230, 240), NEON_PINK, (cx, cy + 150), glow_radius=10, glow_boost=0.9)

    bg.convert("RGB").save(path, "PNG")


def make_profile(path):
    size = (800, 800)
    bg = make_background(size, PURPLE_DARK, NAVY_DARK)

    center = (size[0] / 2, size[1] / 2)
    glow_ellipse(bg, (150, 150, 650, 650), NEON_CYAN, blur=140, alpha=70)

    draw = ImageDraw.Draw(bg)
    ring_r = 360
    draw.ellipse(
        (center[0] - ring_r, center[1] - ring_r, center[0] + ring_r, center[1] + ring_r),
        outline=(*NEON_CYAN, 200), width=6,
    )

    mono_font = ImageFont.truetype(find_font(), 340)
    glow_text(bg, MONOGRAM, mono_font, WHITE, NEON_PINK, center, glow_radius=26, glow_boost=1.4)

    bg.convert("RGB").save(path, "PNG")


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    banner_path = os.path.join(OUT_DIR, "banner.png")
    profile_path = os.path.join(OUT_DIR, "profile.png")
    make_banner(banner_path)
    make_profile(profile_path)
    print(f"Wrote {banner_path}")
    print(f"Wrote {profile_path}")


if __name__ == "__main__":
    main()
