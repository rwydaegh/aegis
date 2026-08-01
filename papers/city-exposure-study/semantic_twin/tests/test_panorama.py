from __future__ import annotations

import pathlib

import numpy as np
import pytest
from PIL import Image
from semantic_twin.panorama import (
    pose_from_metadata,
    stitch_tiles,
    streetview_orientation_source,
    zoom_dimensions,
)


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


def test_orientation_source_separates_a_missing_solution_from_a_level_camera() -> None:
    assert streetview_orientation_source({"tilt": 102.32776, "roll": 4.2383833}).startswith("map tiles")
    assert streetview_orientation_source({"tilt": 90.0, "roll": 0.0}).startswith("degenerate")
    assert streetview_orientation_source({"heading": 12.0}).startswith("absent")


def test_pose_altitude_prefers_the_ground_under_this_camera() -> None:
    scene = {
        "enu_origin": {"lat": 51.0, "lon": 3.0},
        "camera_ground_z_m": 50.0,
        "camera_height_m": 2.5,
    }
    metadata = {"lat": 51.0, "lng": 3.0, "heading": 10.0, "tilt": 102.0, "roll": 4.0}
    scene_only = pose_from_metadata(metadata, scene)
    assert scene_only.position_enu_m[2] == 52.5

    vertices = np.array([[-9.0, -9.0, 50.7], [9.0, -9.0, 50.7], [9.0, 9.0, 50.7], [-9.0, 9.0, 50.7]])
    faces = np.array([[0, 1, 2], [0, 2, 3]])
    measured = pose_from_metadata(metadata, scene, support_mesh=(vertices, faces))
    assert measured.position_enu_m[2] == pytest.approx(53.2)
    assert measured.provenance["ground_minus_scene_constant_m"] == pytest.approx(0.7)
    assert measured.orientation_source.startswith("map tiles")
