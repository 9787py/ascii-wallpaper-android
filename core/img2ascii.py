#!/usr/bin/env python3
import argparse
import math
import os

from PIL import (Image, ImageChops, ImageColor, ImageDraw, ImageFilter,
                 ImageFont, ImageOps, ImageStat)

import bgmaker

RAMP = " .:-=+*#%@"
MODES = ("original", "natural", "shadow", "shadow2", "detail", "structure",
         "retinex", "edge", "twotone", "braille", "halfblock", "auto")
FIT_MODES = ("auto", "contain", "cover", "stretch")
BRAILLE_FONT_CANDIDATES = (
    r"C:\Windows\Fonts\seguisym.ttf",
    r"C:\Windows\Fonts\DejaVuSans.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/System/Library/Fonts/Apple Symbols.ttf",
)


def pixel_data(image):
    reader = getattr(image, "get_flattened_data", image.getdata)
    return reader()


def font_size(value):
    try:
        value = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError("font size must be an integer")
    if not 1 <= value <= 256:
        raise argparse.ArgumentTypeError("font size must be between 1 and 256")
    return value


def luminance(rgb):
    r, g, b = rgb
    return 0.299 * r + 0.587 * g + 0.114 * b


def open_source(path, bg_color):
    src = Image.open(path)
    src = ImageOps.exif_transpose(src)
    if src.mode in ("RGBA", "LA") or (src.mode == "P" and "transparency" in src.info):
        src = src.convert("RGBA")
        base = Image.new("RGBA", src.size, bg_color + (255,))
        base.alpha_composite(src)
        src = base
    return src.convert("RGB")


def resolve_fit(source_size, target_size, fit, sample_aspect=1.0):
    if fit not in FIT_MODES:
        raise ValueError(f"Unknown fit mode: {fit}")
    if fit != "auto":
        return fit
    source_ratio = source_size[0] / max(1, source_size[1])
    target_ratio = target_size[0] * sample_aspect / max(1, target_size[1])
    ratio_difference = abs(math.log(source_ratio / target_ratio))
    return "cover" if ratio_difference <= 0.12 else "contain"


def fit_source(image, target_size, bg_color, fit="auto", sample_aspect=1.0):
    """Fit an image to a sampling grid without accidental aspect distortion."""
    fit = resolve_fit(image.size, target_size, fit, sample_aspect)
    source_ratio = image.width / max(1, image.height) / sample_aspect
    target_ratio = target_size[0] / max(1, target_size[1])
    if fit == "stretch":
        shrinking = image.width >= target_size[0] and image.height >= target_size[1]
        resample = Image.Resampling.BOX if shrinking else Image.Resampling.LANCZOS
        return image.resize(target_size, resample)
    round_size = math.floor if fit == "contain" else math.ceil
    if (fit == "contain") == (source_ratio > target_ratio):
        width = target_size[0]
        height = max(1, round_size(width / source_ratio))
    else:
        height = target_size[1]
        width = max(1, round_size(height * source_ratio))
    shrinking = image.width >= width and image.height >= height
    resample = Image.Resampling.BOX if shrinking else Image.Resampling.LANCZOS
    fitted = image.resize((width, height), resample)
    if fit == "cover":
        left = max(0, (width - target_size[0]) // 2)
        top = max(0, (height - target_size[1]) // 2)
        return fitted.crop((left, top, left + target_size[0],
                            top + target_size[1]))
    canvas = Image.new("RGB", target_size, bg_color)
    canvas.paste(fitted, ((target_size[0] - width) // 2,
                          (target_size[1] - height) // 2))
    return canvas


def auto_background(path):
    """Estimate a quiet background color from the source image edges."""
    with Image.open(path) as image:
        image = ImageOps.exif_transpose(image).convert("RGB")
        image.thumbnail((128, 128), Image.Resampling.BOX)
        width, height = image.size
        edge = Image.new("RGB", (2 * width + 2 * height, 1))
        samples = []
        for crop in (
                image.crop((0, 0, width, 1)),
                image.crop((0, height - 1, width, height)),
                image.crop((0, 0, 1, height)),
                image.crop((width - 1, 0, width, height))):
            samples.extend(pixel_data(crop))
        edge.putdata(samples)
        return tuple(int(value) for value in ImageStat.Stat(edge).median)


def resolve_background(path, color):
    return auto_background(path) if color.lower() == "auto" else ImageColor.getrgb(color)


def _gamma_to_median(image, target):
    histogram = image.histogram()
    midpoint = max(1, (sum(histogram) + 1) // 2)
    count = 0
    median = 0
    for median, amount in enumerate(histogram):
        count += amount
        if count >= midpoint:
            break
    normalized = max(1 / 255, min(254 / 255, median / 255))
    gamma = max(0.55, min(1.8, math.log(target) / math.log(normalized)))
    return image.point([round(255 * ((value / 255) ** gamma))
                        for value in range(256)])


def clahe(image, tiles=(8, 8), clip_factor=2.5):
    """Contrast-limited adaptive histogram equalization for an L image."""
    width, height = image.size
    tiles_x = max(1, min(tiles[0], width))
    tiles_y = max(1, min(tiles[1], height))
    luts = []

    for tile_y in range(tiles_y):
        row = []
        top = tile_y * height // tiles_y
        bottom = (tile_y + 1) * height // tiles_y
        for tile_x in range(tiles_x):
            left = tile_x * width // tiles_x
            right = (tile_x + 1) * width // tiles_x
            histogram = image.crop((left, top, right, bottom)).histogram()
            pixels = max(1, (right - left) * (bottom - top))
            limit = max(1, round(clip_factor * pixels / 256))
            excess = sum(max(0, count - limit) for count in histogram)
            histogram = [min(count, limit) for count in histogram]
            share, remainder = divmod(excess, 256)
            histogram = [count + share for count in histogram]
            if remainder:
                step = 256 / remainder
                for index in range(remainder):
                    histogram[min(255, int(index * step))] += 1

            cdf = []
            total = 0
            for count in histogram:
                total += count
                cdf.append(total)
            first = next((value for value in cdf if value), 0)
            scale = pixels - first
            if scale <= 0:
                row.append(list(range(256)))
            else:
                row.append([max(0, min(255, round(
                    (value - first) * 255 / scale))) for value in cdf])
        luts.append(row)

    source = image.load()
    result = Image.new("L", image.size)
    target = result.load()
    for y in range(height):
        grid_y = (y + 0.5) * tiles_y / height - 0.5
        raw_y = math.floor(grid_y)
        if raw_y < 0:
            y0 = y1 = 0
            fy = 0
        elif raw_y >= tiles_y - 1:
            y0 = y1 = tiles_y - 1
            fy = 0
        else:
            y0, y1 = raw_y, raw_y + 1
            fy = grid_y - raw_y
        for x in range(width):
            grid_x = (x + 0.5) * tiles_x / width - 0.5
            raw_x = math.floor(grid_x)
            if raw_x < 0:
                x0 = x1 = 0
                fx = 0
            elif raw_x >= tiles_x - 1:
                x0 = x1 = tiles_x - 1
                fx = 0
            else:
                x0, x1 = raw_x, raw_x + 1
                fx = grid_x - raw_x
            value = source[x, y]
            top_value = luts[y0][x0][value] * (1 - fx) + luts[y0][x1][value] * fx
            bottom_value = luts[y1][x0][value] * (1 - fx) + luts[y1][x1][value] * fx
            target[x, y] = round(top_value * (1 - fy) + bottom_value * fy)
    return result


def detail_tone_map(gray):
    adaptive = clahe(gray)
    local = ImageChops.difference(
        gray, gray.filter(ImageFilter.GaussianBlur(radius=2)))
    local = ImageOps.autocontrast(local, cutoff=1)
    edges = ImageOps.autocontrast(
        gray.filter(ImageFilter.FIND_EDGES), cutoff=1)
    ImageDraw.Draw(edges).rectangle(
        (0, 0, edges.width - 1, edges.height - 1), outline=0)
    black = Image.new("L", gray.size, 0)
    result = adaptive
    result = ImageChops.add(result, Image.blend(black, local, 0.35))
    return ImageChops.add(result, Image.blend(black, edges, 0.20))


def multiscale_shadow_map(gray):
    """Lift shadows while retaining detail at several spatial scales."""
    base = _gamma_to_median(ImageOps.autocontrast(gray, cutoff=2), 0.56)
    neutral = Image.new("L", gray.size, 128)
    result = base
    for radius, weight in ((1.0, 0.28), (3.0, 0.18), (8.0, 0.10)):
        blurred = gray.filter(ImageFilter.GaussianBlur(radius=radius))
        detail = ImageChops.subtract(gray, blurred, offset=128)
        weighted = Image.blend(neutral, detail, weight)
        result = ImageChops.add(result, weighted, offset=-128)
    return result


def _percentile(values, fraction):
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, max(0, round(
        (len(ordered) - 1) * fraction)))]


def retinex_tone_map(gray):
    """Classic multi-scale Retinex blended with a natural global tone map."""
    pixels = list(pixel_data(gray))
    response = [0.0] * len(pixels)
    for radius in (2, 8, 24):
        blurred = list(pixel_data(gray.filter(ImageFilter.GaussianBlur(radius))))
        for index, (value, illumination) in enumerate(zip(pixels, blurred)):
            response[index] += (math.log1p(value) - math.log1p(illumination)) / 3
    low = _percentile(response, 0.02)
    high = _percentile(response, 0.98)
    scale = max(1e-6, high - low)
    normalized = Image.new("L", gray.size)
    normalized.putdata([max(0, min(255, round((value - low) * 255 / scale)))
                        for value in response])
    global_tone = _gamma_to_median(ImageOps.autocontrast(gray, cutoff=2), 0.52)
    return Image.blend(global_tone, normalized, 0.65)


def bilateral_base(gray, radius=2, sigma_spatial=1.4, sigma_range=28):
    """Small edge-preserving bilateral filter for the character grid."""
    width, height = gray.size
    source = gray.load()
    result = Image.new("L", gray.size)
    target = result.load()
    spatial = {(dx, dy): math.exp(
        -(dx * dx + dy * dy) / (2 * sigma_spatial * sigma_spatial))
        for dy in range(-radius, radius + 1)
        for dx in range(-radius, radius + 1)}
    range_denominator = 2 * sigma_range * sigma_range
    for y in range(height):
        for x in range(width):
            center = source[x, y]
            weighted = 0.0
            weights = 0.0
            for dy in range(-radius, radius + 1):
                yy = min(height - 1, max(0, y + dy))
                for dx in range(-radius, radius + 1):
                    xx = min(width - 1, max(0, x + dx))
                    value = source[xx, yy]
                    difference = value - center
                    weight = spatial[dx, dy] * math.exp(
                        -(difference * difference) / range_denominator)
                    weighted += value * weight
                    weights += weight
            target[x, y] = round(weighted / weights)
    return result


def edge_aware_tone_map(gray):
    base = bilateral_base(gray)
    compressed = _gamma_to_median(ImageOps.autocontrast(base, cutoff=2), 0.52)
    detail = ImageChops.subtract(gray, base, offset=128)
    weighted = Image.blend(Image.new("L", gray.size, 128), detail, 0.55)
    return ImageChops.add(compressed, weighted, offset=-128)


def adaptive_density(image, blank_fraction=0.18):
    """Distribute visible tones across the ramp while reserving background."""
    histogram = image.histogram()
    total = sum(histogram)
    blank_target = total * blank_fraction
    cumulative = 0
    cutoff = 0
    for cutoff, count in enumerate(histogram):
        cumulative += count
        if cumulative >= blank_target:
            break
    remaining = sum(histogram[cutoff + 1:])
    if remaining <= 0:
        return Image.new("L", image.size, 0)

    rank = 0
    lut = [0] * 256
    for value in range(cutoff + 1, 256):
        rank += histogram[value]
        # A mild power curve keeps low-level noise in sparse glyphs.
        lut[value] = round(255 * ((rank / remaining) ** 1.15))
    return image.point(lut)


def dither_density(image, levels=len(RAMP)):
    """Floyd-Steinberg error diffusion on the character-density grid."""
    width, height = image.size
    values = [float(value) for value in pixel_data(image)]
    step = 255 / (levels - 1)
    for y in range(height):
        left_to_right = y % 2 == 0
        xs = range(width) if left_to_right else range(width - 1, -1, -1)
        direction = 1 if left_to_right else -1
        for x in xs:
            index = y * width + x
            old = max(0, min(255, values[index]))
            new = round(old / step) * step
            values[index] = new
            error = old - new
            for xx, yy, share in (
                    (x + direction, y, 7 / 16),
                    (x - direction, y + 1, 3 / 16),
                    (x, y + 1, 5 / 16),
                    (x + direction, y + 1, 1 / 16)):
                if 0 <= xx < width and yy < height:
                    values[yy * width + xx] += error * share
    result = Image.new("L", image.size)
    result.putdata([round(max(0, min(255, value))) for value in values])
    return result


def tone_map(image, mode):
    """Build the luminance map used for glyph density selection."""
    gray = image.convert("L")
    if mode == "original":
        return gray
    stretched = ImageOps.autocontrast(gray, cutoff=2)
    if mode == "natural":
        return _gamma_to_median(stretched, 0.48)
    if mode == "shadow":
        local = stretched.filter(ImageFilter.UnsharpMask(
            radius=1.5, percent=160, threshold=2))
        locally_equalized = ImageOps.equalize(local)
        enhanced = Image.blend(local, locally_equalized, 0.25)
        return _gamma_to_median(enhanced, 0.60)
    if mode == "detail":
        return detail_tone_map(gray)
    if mode == "shadow2":
        return multiscale_shadow_map(gray)
    if mode == "retinex":
        return retinex_tone_map(gray)
    if mode == "edge":
        return edge_aware_tone_map(gray)
    if mode in ("structure", "twotone"):
        return _gamma_to_median(ImageOps.autocontrast(gray, cutoff=2), 0.50)
    raise ValueError(f"Unknown render mode: {mode}")


def ensure_contrast(color, background, minimum=48):
    """Keep glyph colors visible without discarding their original hue."""
    color_luma = luminance(color)
    background_luma = luminance(background)
    if abs(color_luma - background_luma) >= minimum:
        return color
    if background_luma < 128:
        target = min(255, background_luma + minimum)
        amount = (target - color_luma) / max(1, 255 - color_luma)
        return tuple(round(channel + (255 - channel) * amount)
                     for channel in color)
    target = max(0, background_luma - minimum)
    scale = target / max(1, color_luma)
    return tuple(round(channel * scale) for channel in color)


def recommend_mode(source_path, bg_color=(0, 0, 0)):
    """Recommend a conservative mode from low-resolution image statistics."""
    image = open_source(source_path, bg_color)
    image.thumbnail((160, 90), Image.Resampling.BOX)
    gray = image.convert("L")
    values = list(pixel_data(gray))
    mean = sum(values) / len(values)
    dark_fraction = sum(value < 55 for value in values) / len(values)
    spread = _percentile(values, 0.90) - _percentile(values, 0.10)
    edges = list(pixel_data(gray.filter(ImageFilter.FIND_EDGES)))
    edge_strength = sum(edges) / len(edges)
    illumination = list(pixel_data(gray.filter(ImageFilter.GaussianBlur(12))))
    illumination_spread = _percentile(illumination, 0.90) - _percentile(
        illumination, 0.10)
    if dark_fraction > 0.48:
        return "shadow2"
    if illumination_spread > 75 and mean < 150:
        return "retinex"
    if edge_strength > 38 and spread > 90:
        return "structure"
    if edge_strength > 24:
        return "edge"
    return "natural"


def _glyph_mask(font, cell_size, character):
    mask = Image.new("L", cell_size, 0)
    ImageDraw.Draw(mask).text((0, 0), character, font=font, fill=255)
    return mask


def braille_font(fallback):
    for path in BRAILLE_FONT_CANDIDATES:
        if os.path.exists(path):
            return ImageFont.truetype(path, fallback.size)
    return fallback


def braille_image(source_path, font, canvas_size, bg_color, fit):
    font = braille_font(font)
    cell_w = max(1, font.getbbox("M")[2])
    ascent, descent = font.getmetrics()
    cell_h = max(1, ascent + descent)
    cols = max(1, canvas_size[0] // cell_w)
    rows = max(1, canvas_size[1] // cell_h)
    source = fit_source(open_source(source_path, bg_color),
                        (cols * 2, rows * 4), bg_color, fit,
                        sample_aspect=2 * cell_w / cell_h)
    density = multiscale_shadow_map(source.convert("L"))
    if luminance(bg_color) >= 128:
        density = ImageOps.invert(density)
    density = adaptive_density(density, blank_fraction=0.12)
    colors = source.load()
    levels = density.load()
    thresholds = ((16, 144), (208, 80), (64, 192), (240, 112))
    bits = ((1, 8), (2, 16), (4, 32), (64, 128))
    out = Image.new("RGB", canvas_size, bg_color)
    masks = {}
    for row in range(rows):
        for col in range(cols):
            code = 0
            active = []
            for yy in range(4):
                for xx in range(2):
                    px = col * 2 + xx
                    py = row * 4 + yy
                    if levels[px, py] > thresholds[yy][xx]:
                        code |= bits[yy][xx]
                        active.append(colors[px, py])
            if not code:
                continue
            character = chr(0x2800 + code)
            if character not in masks:
                masks[character] = _glyph_mask(
                    font, (cell_w, cell_h), character)
            color = tuple(round(sum(pixel[channel] for pixel in active) /
                                len(active)) for channel in range(3))
            color = ensure_contrast(color, bg_color, minimum=40)
            out.paste(color, (col * cell_w, row * cell_h), masks[character])
    return out


def halfblock_image(source_path, font, canvas_size, bg_color, fit):
    cell_w = max(1, font.getbbox("M")[2])
    ascent, descent = font.getmetrics()
    cell_h = max(1, ascent + descent)
    cols = max(1, canvas_size[0] // cell_w)
    rows = max(1, canvas_size[1] // cell_h)
    source = fit_source(open_source(source_path, bg_color),
                        (cols, rows * 2), bg_color, fit,
                        sample_aspect=2 * cell_w / cell_h)
    pixels = source.load()
    mask = _glyph_mask(font, (cell_w, cell_h), "▀")
    out = Image.new("RGB", canvas_size, bg_color)
    draw = ImageDraw.Draw(out)
    for row in range(rows):
        for col in range(cols):
            top = pixels[col, row * 2]
            bottom = pixels[col, row * 2 + 1]
            box = (col * cell_w, row * cell_h,
                   (col + 1) * cell_w - 1, (row + 1) * cell_h - 1)
            draw.rectangle(box, fill=bottom)
            out.paste(top, (col * cell_w, row * cell_h), mask)
    return out


def ascii_image(source_path, font, canvas_size, bg_color=(0, 0, 0),
                mode="natural", dither=False, fit="auto"):
    if mode == "auto":
        mode = recommend_mode(source_path, bg_color)
    if mode == "braille":
        return braille_image(source_path, font, canvas_size, bg_color, fit)
    if mode == "halfblock":
        return halfblock_image(source_path, font, canvas_size, bg_color, fit)
    src = open_source(source_path, bg_color)
    cell_w = font.getbbox("M")[2]
    ascent, descent = font.getmetrics()
    cell_h = ascent + descent
    cols = max(1, canvas_size[0] // cell_w)
    rows = max(1, canvas_size[1] // cell_h)
    resized = fit_source(src, (cols, rows), bg_color, fit,
                         sample_aspect=cell_w / cell_h)
    density = tone_map(resized, mode)

    characters = RAMP if mode != "structure" else RAMP + "|-/\\+x_oO"
    masks = {character: _glyph_mask(font, (cell_w, cell_h), character)
             for character in characters}

    out = Image.new("RGB", canvas_size, bg_color)
    px = resized.load()
    density_px = density.load()
    n = len(RAMP)
    light_background = luminance(bg_color) >= 128
    if light_background:
        density = ImageOps.invert(density)
        density_px = density.load()
    if mode in ("shadow2", "retinex"):
        density = adaptive_density(
            density, blank_fraction=0.18 if mode == "shadow2" else 0.25)
        density_px = density.load()
    if dither:
        density = dither_density(density)
        density_px = density.load()
    output_draw = ImageDraw.Draw(out)
    for y in range(rows):
        row_y = y * cell_h
        for x in range(cols):
            c = px[x, y]
            level = density_px[x, y]
            idx = min(n - 1, int(level * n / 256))
            if idx:
                character = RAMP[idx]
                if mode == "structure" and 0 < x < cols - 1 and 0 < y < rows - 1:
                    gx = density_px[x + 1, y] - density_px[x - 1, y]
                    gy = density_px[x, y + 1] - density_px[x, y - 1]
                    if abs(gx) + abs(gy) > 42:
                        if abs(gx) > abs(gy) * 2:
                            character = "|"
                        elif abs(gy) > abs(gx) * 2:
                            character = "-"
                        else:
                            character = "/" if gx * gy > 0 else "\\"
                cell_bg = bg_color
                if mode == "twotone":
                    cell_bg = tuple(round(channel * 0.55 + background * 0.45)
                                    for channel, background in zip(c, bg_color))
                    output_draw.rectangle(
                        (x * cell_w, row_y, (x + 1) * cell_w - 1,
                         row_y + cell_h - 1), fill=cell_bg)
                ink = c if mode == "original" else ensure_contrast(c, cell_bg)
                out.paste(ink, (x * cell_w, row_y), masks[character])
    return out


def main():
    ap = argparse.ArgumentParser(
        description="Convert an image into colorized ASCII art wallpaper")
    ap.add_argument("source", help="Input image file")
    ap.add_argument("--font-size", type=font_size, default=24,
                    help="Monospace font size, smaller = more detail (default 24)")
    ap.add_argument("--bg", default="auto",
                    help="Background color or 'auto' (default auto)")
    ap.add_argument("--mode", choices=MODES,
                    default="natural", help="Tone mapping mode (default natural)")
    ap.add_argument("--dither", action="store_true",
                    help="Apply Floyd-Steinberg character-density dithering")
    ap.add_argument("--fit", choices=FIT_MODES, default="auto",
                    help="Image fitting strategy (default auto)")
    ap.add_argument("--size", type=bgmaker.parse_size, default=(3840, 2160),
                    help="Output size WxH")
    ap.add_argument("--font", help="Path to a monospace TTF font")
    args = ap.parse_args()

    font_path = args.font
    if not font_path:
        _font_name, font_path = bgmaker.find_font()

    try:
        font = ImageFont.truetype(font_path, args.font_size)
        bg = resolve_background(args.source, args.bg)
    except (OSError, ValueError) as exc:
        ap.error(str(exc))
    out_w, out_h = args.size
    render_mode = (recommend_mode(args.source, bg)
                   if args.mode == "auto" else args.mode)
    if args.mode == "auto":
        print(f"Auto selected: {render_mode}")
    dither = args.dither and render_mode not in ("braille", "halfblock")
    if args.dither and not dither:
        print(f"Dither ignored for {render_mode} mode")
    art = ascii_image(args.source, font, (out_w, out_h), bg, render_mode,
                      dither, args.fit)

    os.makedirs(bgmaker.OUTPUT_DIR, exist_ok=True)
    base = os.path.splitext(os.path.basename(args.source))[0]
    suffix = "" if render_mode == "original" else f"_{render_mode}"
    if dither:
        suffix += "_dither"
    if args.fit != "auto":
        suffix += f"_{args.fit}"
    out = os.path.join(bgmaker.OUTPUT_DIR, f"{base}_ascii{suffix}.png")
    art.save(out)
    print(f"Saved to {out}")


if __name__ == "__main__":
    main()
