"""Composite Blender alignment renders over matching Street View crops."""

from __future__ import annotations

import argparse
import pathlib

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.ndimage import binary_dilation, binary_erosion


def label(image: Image.Image, text: str) -> Image.Image:
    result = image.copy()
    draw = ImageDraw.Draw(result)
    font = ImageFont.load_default(size=24)
    box = draw.textbbox((0, 0), text, font=font)
    draw.rectangle((12, 12, box[2] + 30, box[3] + 28), fill=(0, 0, 0, 190))
    draw.text((21, 19), text, fill=(255, 255, 255, 255), font=font)
    return result


def composite(street: Image.Image, geometry: Image.Image) -> tuple[Image.Image, Image.Image]:
    street = street.convert("RGBA")
    geometry = geometry.convert("RGBA")
    alpha = np.asarray(geometry.getchannel("A")) > 0
    edge = binary_dilation(alpha, iterations=2) & ~binary_erosion(alpha, iterations=2)

    fill = np.asarray(geometry).copy()
    fill[:, :, 3] = np.where(alpha, 105, 0).astype(np.uint8)
    overlay = Image.alpha_composite(street, Image.fromarray(fill, "RGBA"))
    pixels = np.asarray(overlay).copy()
    pixels[edge, :3] = np.array([255, 45, 205], dtype=np.uint8)
    pixels[edge, 3] = 255

    clay = Image.new("RGBA", street.size, (18, 24, 35, 255))
    opaque = np.asarray(geometry).copy()
    opaque[:, :, 3] = np.where(alpha, 255, 0).astype(np.uint8)
    clay = Image.alpha_composite(clay, Image.fromarray(opaque, "RGBA"))
    return Image.fromarray(pixels, "RGBA"), clay


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--views", type=pathlib.Path, required=True)
    parser.add_argument("--renders", type=pathlib.Path, required=True)
    parser.add_argument("--out", type=pathlib.Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    overlays = []
    for yaw in (0, 90, 180, 270):
        street = Image.open(args.views / f"h+00_{yaw:03d}.jpg").convert("RGB")
        geometry = Image.open(args.renders / f"mesh_yaw_{yaw:03d}.png")
        overlay, clay = composite(street, geometry)
        direction = f"panorama yaw {yaw}°"
        labelled = label(overlay, f"Street View + Blender mesh, {direction}")
        labelled.convert("RGB").save(args.out / f"overlay_yaw_{yaw:03d}.jpg", quality=94)
        clay = label(clay, f"Blender geometry only, {direction}")
        clay.convert("RGB").save(args.out / f"geometry_yaw_{yaw:03d}.jpg", quality=94)
        overlays.append(labelled.convert("RGB").resize((700, 700)))

    grid = Image.new("RGB", (1400, 1400), (15, 18, 24))
    for index, image in enumerate(overlays):
        grid.paste(image, ((index % 2) * 700, (index // 2) * 700))
    grid.save(args.out / "alignment_overlays_grid.jpg", quality=94)

    overview = Image.open(args.renders / "camera_overview.png").convert("RGB")
    label(overview, "Recovered Street View camera and four viewing directions").save(
        args.out / "camera_overview_labelled.jpg", quality=94
    )


if __name__ == "__main__":
    main()
