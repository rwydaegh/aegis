"""Tests for viewer dosimetry geometry (rigid transforms)."""

from __future__ import annotations

import numpy as np
from conftest import make_single_triangle

from aegis.viewer.compute import _transform_body_for_viewer


def test_transform_preserves_centroid_vertex_consistency():
    body = make_single_triangle()
    out = _transform_body_for_viewer(body, np.array([0.05, -0.1, 0.2]), 0.65)

    for i in range(out.n_triangles):
        np.testing.assert_allclose(
            out.centroids[i],
            np.mean(out.vertices[i], axis=0),
            rtol=1e-14,
        )
    norms = np.linalg.norm(out.normals, axis=1)
    np.testing.assert_allclose(norms, 1.0, atol=1e-12)


def test_transform_noop_returns_same_instance():
    body = make_single_triangle()
    out = _transform_body_for_viewer(body, np.zeros(3), 0.0)
    assert out is body
