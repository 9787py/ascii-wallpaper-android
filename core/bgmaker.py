#!/usr/bin/env python3
import argparse
import os
import re
import sys

from PIL import Image, ImageColor, ImageDraw, ImageFont, ImageOps

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ASCII_DIR = os.path.join(SCRIPT_DIR, "ascii")
COLORS_FILE = os.path.join(SCRIPT_DIR, "colors.txt")
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "Walls")
BG_W, BG_H = 3840, 2160
IMG_W, IMG_H = 1280, 720
FONT_SIZE = 32

FONT_CANDIDATES = [
    ("Cascadia Mono", r"C:\Windows\Fonts\CascadiaMono.ttf"),
    ("Consolas", r"C:\Windows\Fonts\consola.ttf"),
    ("DejaVu Sans Mono", r"C:\Windows\Fonts\DejaVuSansMono.ttf"),
    ("Courier New", r"C:\Windows\Fonts\cour.ttf"),
    ("Lucida Console", r"C:\Windows\Fonts\lucon.ttf"),
    ("DejaVu Sans Mono", "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"),
    ("Liberation Mono", "/usr/share/fonts/truetype/liberation2/LiberationMono-Regular.ttf"),
    ("Menlo", "/System/Library/Fonts/Menlo.ttc"),
]


def find_font():
    for name, path in FONT_CANDIDATES:
        if os.path.exists(path):
            return name, path
    sys.exit("No monospace font found. Use --font to specify a .ttf path")


def parse_size(value):
    try:
        width, height = (int(v) for v in value.lower().split("x"))
    except (ValueError, AttributeError):
        raise argparse.ArgumentTypeError("size must be in WxH format")
    if width <= 0 or height <= 0:
        raise argparse.ArgumentTypeError("width and height must be positive")
    return width, height


def load_colors(distro):
    with open(COLORS_FILE, encoding="utf-8") as f:
        for line in f:
            parts = line.split()
            if parts and parts[0].lower() == distro.lower():
                return parts[1:]
    return None


def find_logo(distro):
    path = os.path.join(ASCII_DIR, f"{distro}.txt")
    if os.path.exists(path):
        return path
    for name in os.listdir(ASCII_DIR):
        if name.lower() == f"{distro}.txt":
            return os.path.join(ASCII_DIR, name)
    return None


def parse_ascii(text, colors):
    lines = []
    for raw in text.splitlines():
        line = []
        color = colors[0]
        for part in re.split(r"(\$[1-9])", raw):
            if not part:
                continue
            if part.startswith("$") and len(part) > 1:
                idx = int(part[1]) - 1
                color = colors[idx] if idx < len(colors) else "#ffffff"
            else:
                line.append((part.replace("$$", "$"), color))
        lines.append(line)
    return lines


def render_ascii(lines, font):
    ascent, descent = font.getmetrics()
    line_h = ascent + descent
    char_w = font.getbbox("M")[2]
    width = max(sum(len(seg) for seg, _ in line) for line in lines) * char_w
    height = len(lines) * line_h
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    for y, line in enumerate(lines):
        x = 0
        for text, color in line:
            draw.text((x, y * line_h), text, font=font, fill=color)
            x += len(text) * char_w
    return img


def main():
    ap = argparse.ArgumentParser(
        description="Generate wallpapers from fastfetch ASCII distro logos")
    ap.add_argument("--logo", required=True,
                    help="Distro name (matches ascii/ folder)")
    ap.add_argument("--colors",
                    help="Override colors for $1, $2, ... (#hex,#hex,...)")
    ap.add_argument("--bg", default="black",
                    help="Background color (hex or name), default black")
    ap.add_argument("--font", help="Path to a monospace TTF font")
    ap.add_argument("--size", type=parse_size, default=(BG_W, BG_H),
                    help="Output size WxH, default 3840x2160")
    args = ap.parse_args()

    distro = args.logo
    logo = find_logo(distro)
    if not logo:
        print(f"Logo not found for: {distro}")
        available = sorted(n[:-4] for n in os.listdir(ASCII_DIR)
                           if n.endswith(".txt"))
        print("Available:", ", ".join(available))
        sys.exit(1)

    if args.colors:
        colors = [color.strip() for color in args.colors.split(",")
                  if color.strip()]
        if not colors:
            ap.error("--colors must contain at least one color")
    else:
        colors = load_colors(distro)
        if not colors:
            colors = ["#ffffff"]
            print(f"Warning: no colors found for {distro}, using white")
        else:
            print("Colors:", ",".join(colors))

    if args.font:
        font_name, font_path = os.path.basename(args.font), args.font
    else:
        font_name, font_path = find_font()
    print("Font:", font_name)

    try:
        font = ImageFont.truetype(font_path, size=FONT_SIZE)
        colors = [ImageColor.getrgb(color) for color in colors]
        bg_color = ImageColor.getrgb(args.bg)
    except (OSError, ValueError) as exc:
        ap.error(str(exc))
    with open(logo, encoding="utf-8") as f:
        text = f.read()

    art = render_ascii(parse_ascii(text, colors), font)
    art = ImageOps.contain(art, (IMG_W, IMG_H), Image.LANCZOS)

    out_w, out_h = args.size
    bg = Image.new("RGB", (out_w, out_h), bg_color)
    bg.paste(art, ((out_w - art.width) // 2, (out_h - art.height) // 2), art)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    out = os.path.join(OUTPUT_DIR, f"{distro}.png")
    bg.save(out)
    print(f"Saved to {out}")


if __name__ == "__main__":
    main()
