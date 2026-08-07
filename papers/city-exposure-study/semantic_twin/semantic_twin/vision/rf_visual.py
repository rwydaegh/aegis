"""Pixel-registered visual evidence for one RF interaction point."""

from __future__ import annotations

import pathlib

from PIL import Image, ImageDraw


def render_hit_evidence(
    image_path: pathlib.Path,
    output_path: pathlib.Path,
    *,
    x: int,
    y: int,
    footprint_radius_px: int = 4,
    zoom_radius_px: int = 12,
) -> pathlib.Path:
    """Render a full view and nearest-neighbour zoom without hiding the hit pixel."""
    source = Image.open(image_path).convert("RGB")
    width, height = source.size
    if not 0 <= x < width or not 0 <= y < height:
        raise ValueError(f"hit ({x}, {y}) lies outside {width}x{height} image")
    if footprint_radius_px < 0 or zoom_radius_px < 1:
        raise ValueError("footprint radius must be nonnegative and zoom radius positive")

    annotated = source.copy()
    draw = ImageDraw.Draw(annotated)
    crosshair = (255, 55, 55)
    footprint = (255, 220, 0)
    arm = max(10, footprint_radius_px + 6)
    gap = 2
    draw.line((x - arm, y, x - gap, y), fill=crosshair, width=2)
    draw.line((x + gap, y, x + arm, y), fill=crosshair, width=2)
    draw.line((x, y - arm, x, y - gap), fill=crosshair, width=2)
    draw.line((x, y + gap, x, y + arm), fill=crosshair, width=2)
    if footprint_radius_px:
        r = footprint_radius_px
        draw.ellipse((x - r, y - r, x + r, y + r), outline=footprint, width=1)

    crop_left = max(0, x - zoom_radius_px)
    crop_top = max(0, y - zoom_radius_px)
    crop_right = min(width, x + zoom_radius_px + 1)
    crop_bottom = min(height, y + zoom_radius_px + 1)
    crop = source.crop((crop_left, crop_top, crop_right, crop_bottom))
    zoom = crop.resize((height, height), Image.Resampling.NEAREST)
    zoom_draw = ImageDraw.Draw(zoom)
    cell_left = round((x - crop_left) * height / crop.width)
    cell_top = round((y - crop_top) * height / crop.height)
    cell_right = round((x - crop_left + 1) * height / crop.width) - 1
    cell_bottom = round((y - crop_top + 1) * height / crop.height) - 1
    zoom_draw.rectangle((cell_left, cell_top, cell_right, cell_bottom), outline=(0, 255, 255), width=2)

    header = 30
    canvas = Image.new("RGB", (width + height, height + header), (20, 20, 20))
    canvas.paste(annotated, (0, header))
    canvas.paste(zoom, (width, header))
    labels = ImageDraw.Draw(canvas)
    labels.text((6, 8), f"Full view: hit ({x}, {y}), radius {footprint_radius_px}px", fill="white")
    labels.text((width + 6, 8), f"Nearest-neighbour zoom: cyan = exact pixel ({x}, {y})", fill="white")

    output = pathlib.Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output)
    return output
