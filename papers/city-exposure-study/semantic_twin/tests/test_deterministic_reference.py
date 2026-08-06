"""Tests for deterministic first-bounce triangle quadrature."""

from __future__ import annotations

import numpy as np
import pytest

from semantic_twin.transport.deterministic_reference import _triangle_centroids


def test_triangle_subdivision_preserves_area_and_centroids() -> None:
    vertices = np.array([[0.0, 0.0, 0.0], [2.0, 0.0, 0.0], [0.0, 1.0, 0.0]])
    faces = np.array([[0, 1, 2]])

    points, normals, weights, face = _triangle_centroids(vertices, faces, 8)

    assert points.shape == (64, 3)
    assert np.sum(weights) == pytest.approx(1.0)
    assert np.average(points, axis=0, weights=weights) == pytest.approx(np.array([2.0 / 3.0, 1.0 / 3.0, 0.0]))
    assert normals == pytest.approx(np.tile([0.0, 0.0, 1.0], (64, 1)))
    assert np.all(face == 0)


def test_triangle_subdivision_rejects_zero_resolution() -> None:
    with pytest.raises(ValueError, match="positive"):
        _triangle_centroids(np.zeros((3, 3)), np.array([[0, 1, 2]]), 0)
