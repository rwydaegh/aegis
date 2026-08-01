from __future__ import annotations

import pathlib

import numpy as np
from PIL import Image
from semantic_twin.panorama import stitch_tiles, zoom_dimensions


def test_zoom_dimensions_reach_native_resolution() -> None:
    metadata = {"imageWidth": 16384, "imageHeight": 8192}
    assert zoom_dimensions(metadata, 5) == (16384, 8192)
    assert zoom_dimensions(metadata, 4) == (8192, 4096)
    assert zoom_dimensions(metadata, 0) == (512, 256)


def test_stitch_tiles_crops_padded_edges(tmp_path: pathlib.Path) -> None:
    paths = {}
    colours = {(0, 0): (255, 0, 0), (1, 0): (0, 255, 0), (0, 1): (0, 0, 255), (1, 1): (255, 255, 0)}
    for key, colour in colours.items():
        path = tmp_path / f"{key[0]}_{key[1]}.jpg"
        Image.new("RGB", (4, 4), colour).save(path, quality=100, subsampling=0)
        paths[key] = path
    image = stitch_tiles(paths, width=7, height=6, tile_width=4, tile_height=4)
    assert image.size == (7, 6)
    pixels = np.asarray(image)
    assert pixels[1, 1, 0] > 240
    assert pixels[1, 5, 1] > 240
    assert pixels[5, 1, 2] > 240
