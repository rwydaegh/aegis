from __future__ import annotations

import numpy as np

from semantic_twin.vision.project import (
    adaptive_semantic_tiles,
    edge_aware_smooth_depth,
    plane_fit_error,
    rasterize_tiles,
)


def test_adaptive_tiles_preserve_every_valid_pixel() -> None:
    labels = np.array(
        [
            [1, 1, 1, 1, 2],
            [1, 1, 1, 1, 2],
            [1, 1, 3, 3, 2],
            [1, 1, 3, 3, 2],
        ],
        dtype=np.uint16,
    )
    valid = np.ones_like(labels, dtype=bool)
    valid[1, 4] = False

    tiles = adaptive_semantic_tiles(labels, valid)
    reconstructed = rasterize_tiles(tiles, labels.shape)

    assert np.array_equal(reconstructed[valid], labels[valid])
    assert np.all(reconstructed[~valid] == -1)


def test_uniform_image_collapses_to_one_tile() -> None:
    labels = np.full((16, 32), 7, dtype=np.uint16)
    tiles = adaptive_semantic_tiles(labels, np.ones_like(labels, dtype=bool))

    assert len(tiles) == 1
    assert (tiles[0].width, tiles[0].height, tiles[0].class_id) == (32, 16, 7)


def test_plane_fit_accepts_perspective_samples_on_tilted_plane() -> None:
    camera = np.zeros(3)
    rays = np.array(
        [
            [-0.4, -0.3, 1.0],
            [0.0, -0.3, 1.0],
            [0.4, -0.3, 1.0],
            [-0.4, 0.0, 1.0],
            [0.0, 0.0, 1.0],
            [0.4, 0.0, 1.0],
            [-0.4, 0.3, 1.0],
            [0.0, 0.3, 1.0],
            [0.4, 0.3, 1.0],
        ]
    )
    plane_normal = np.array([0.55, -0.2, 1.0])
    plane_offset = 8.0
    distances = plane_offset / (rays @ plane_normal)
    points = camera + distances[:, None] * rays

    error, fitted_normal = plane_fit_error(points)

    assert error < 1e-12
    assert np.isclose(abs(fitted_normal @ (plane_normal / np.linalg.norm(plane_normal))), 1.0)


def test_plane_fit_detects_depth_discontinuity() -> None:
    points = np.array(
        [
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [1.0, 1.0, 0.0],
            [0.5, 0.5, 0.4],
        ]
    )

    error, _normal = plane_fit_error(points)

    assert error > 0.1


def test_edge_aware_smoothing_reduces_staircase_without_blending_blocker() -> None:
    depth = np.array([[10.0, 10.2, 10.0, 30.0, 30.1], [10.1, 10.0, 10.2, 30.2, 30.0]])
    smoothed = edge_aware_smooth_depth(depth, np.ones_like(depth, dtype=bool), iterations=4)
    assert np.std(smoothed[:, :3]) < np.std(depth[:, :3])
    assert np.min(smoothed[:, 3:]) > 29.0
    assert np.max(smoothed[:, :3]) < 11.0
