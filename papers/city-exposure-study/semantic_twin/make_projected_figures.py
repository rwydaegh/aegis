"""Overlay projected semantic triangles on matching Street View crops."""

from __future__ import annotations

import argparse
import json
import pathlib

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.ndimage import binary_dilation, binary_erosion


def font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    return ImageFont.load_default(size=size)


def title(image: Image.Image, text: str) -> None:
    draw = ImageDraw.Draw(image)
    face = font(24)
    box = draw.textbbox((0, 0), text, font=face)
    draw.rectangle((12, 12, box[2] + 30, box[3] + 28), fill=(0, 0, 0, 210))
    draw.text((21, 19), text, fill="white", font=face)


def legend(image: Image.Image, entries: list[dict]) -> None:
    draw = ImageDraw.Draw(image)
    face = font(19)
    width = 250
    height = 18 + 30 * len(entries)
    x0, y0 = image.width - width - 14, 14
    draw.rectangle((x0, y0, image.width - 14, y0 + height), fill=(0, 0, 0, 205))
    for index, entry in enumerate(entries):
        y = y0 + 12 + index * 30
        draw.rectangle((x0 + 10, y, x0 + 30, y + 20), fill=tuple(entry["rgb"]))
        draw.text((x0 + 40, y), entry["name"], fill="white", font=face)


def overlay(street: Image.Image, projected: Image.Image, *, edge_pixels: int = 2) -> tuple[Image.Image, Image.Image]:
    street = street.convert("RGBA")
    projected = projected.convert("RGBA")
    pixels = np.asarray(projected).copy()
    mask = pixels[:, :, 3] > 0
    pixels[:, :, 3] = np.where(mask, 170, 0).astype(np.uint8)
    result = Image.alpha_composite(street, Image.fromarray(pixels, "RGBA"))
    result_pixels = np.asarray(result).copy()
    if edge_pixels:
        edge = binary_dilation(mask, iterations=edge_pixels) & ~binary_erosion(mask, iterations=edge_pixels)
        result_pixels[edge, :3] = np.array([255, 255, 255], dtype=np.uint8)
        result_pixels[edge, 3] = 255

    isolated = Image.new("RGBA", street.size, (15, 18, 25, 255))
    opaque = np.asarray(projected).copy()
    opaque[:, :, 3] = np.where(mask, 255, 0).astype(np.uint8)
    isolated = Image.alpha_composite(isolated, Image.fromarray(opaque, "RGBA"))
    return Image.fromarray(result_pixels, "RGBA"), isolated


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--views", type=pathlib.Path, required=True)
    parser.add_argument("--renders", type=pathlib.Path, required=True)
    parser.add_argument("--out", type=pathlib.Path, required=True)
    parser.add_argument("--render-prefix", default="pixel_projected_yaw")
    parser.add_argument("--manifest", default="pixel_projection_manifest.json")
    parser.add_argument("--edge-pixels", type=int, default=0)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((args.renders / args.manifest).read_text())
    entries = manifest["legend"]
    figures = []
    for yaw in (0, 90, 180, 270):
        street = Image.open(args.views / f"h+00_{yaw:03d}.jpg")
        projected = Image.open(args.renders / f"{args.render_prefix}_{yaw:03d}.png")
        composite, isolated = overlay(street, projected, edge_pixels=args.edge_pixels)
        title(composite, f"Pixel-faithful first-hit semantics, panorama yaw {yaw}°")
        legend(composite, entries)
        composite.convert("RGB").save(args.out / f"projected_overlay_yaw_{yaw:03d}.jpg", quality=95)
        title(isolated, f"Projected triangles only, panorama yaw {yaw}°")
        legend(isolated, entries)
        isolated.convert("RGB").save(args.out / f"projected_only_yaw_{yaw:03d}.jpg", quality=95)
        figures.append(composite.convert("RGB").resize((700, 700)))
    grid = Image.new("RGB", (1400, 1400), (15, 18, 25))
    for index, figure in enumerate(figures):
        grid.paste(figure, ((index % 2) * 700, (index // 2) * 700))
    grid.save(args.out / "projected_semantics_grid.jpg", quality=95)


if __name__ == "__main__":
    main()
