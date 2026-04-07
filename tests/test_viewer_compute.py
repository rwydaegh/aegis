"""Tests for viewer dosimetry geometry (rigid transforms)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pytest

pytest.importorskip("flask")

import numpy as np  # noqa: E402
from conftest import make_flat_mesh, make_single_triangle  # noqa: E402

from aegis.viewer.compute import (
    _compute_face_curvature,
    _curvature_cache,
    _resolve_channel_preset_dir,
    _transform_body_for_viewer,
    compute_dosimetry,
)  # noqa: E402


def _fake_result(n_triangles: int) -> SimpleNamespace:
    sab = np.zeros(n_triangles, dtype=np.float64)
    return SimpleNamespace(
        sab=sab,
        sab_averaged=None,
        sab_1cm2_averaged=None,
        sinc=None,
        sinc_averaged=None,
        p_abs=0.0,
        peak_sab=0.0,
        fidelity_level=2,
        freq_hz=28e9,
    )


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


def test_compute_dosimetry_returns_transformed_body():
    body = make_flat_mesh(8)

    with patch(
        "aegis.viewer.compute.DosimetryEngine.compute_with_timings",
        return_value=(_fake_result(body.n_triangles), {}),
    ):
        _, transformed_body, *_ = compute_dosimetry(
            body,
            antenna_pos=np.array([0.0, 0.0, 2.0]),
            body_offset=np.array([0.2, -0.1, 0.3]),
            body_rotation_y=0.4,
        )

    assert transformed_body is not body
    assert transformed_body.n_triangles == body.n_triangles
    assert not np.allclose(transformed_body.centroids, body.centroids)
    np.testing.assert_allclose(transformed_body.centroids, np.mean(transformed_body.vertices, axis=1))


def test_compute_dosimetry_keeps_diffraction_independent_from_curvature():
    body = make_flat_mesh(12)

    with patch(
        "aegis.viewer.compute.DosimetryEngine.compute_with_timings",
        return_value=(_fake_result(body.n_triangles), {}),
    ) as compute_mock:
        compute_dosimetry(
            body,
            antenna_pos=np.array([0.0, 0.0, 2.0]),
            mode="spatial",
            corrections={"diffraction": True},
        )

    kwargs = compute_mock.call_args.kwargs
    assert kwargs["diffraction"] is True
    assert kwargs.get("curvature") is not True
    assert "curvature_H" in kwargs


def test_curvature_cache_key_distinguishes_meshes_with_same_area_spectrum():
    body_flat = make_flat_mesh(16)
    tilted_vertices = body_flat.vertices.copy()

    for i in range(0, body_flat.n_triangles, 2):
        tri = tilted_vertices[i]
        center = np.mean(tri, axis=0)
        angle = 0.45
        c, s = np.cos(angle), np.sin(angle)
        rot_x = np.array([[1.0, 0.0, 0.0], [0.0, c, -s], [0.0, s, c]])
        tilted_vertices[i] = (tri - center) @ rot_x.T + center

    body_tilted = body_flat.from_arrays(tilted_vertices, name="tilted_flat")
    np.testing.assert_allclose(body_flat.areas, body_tilted.areas)

    _curvature_cache.clear()
    H_flat = _compute_face_curvature(body_flat)
    H_tilted = _compute_face_curvature(body_tilted)
    _curvature_cache.clear()

    assert not np.allclose(H_flat, H_tilted)


def test_compute_face_curvature_single_triangle_returns_zero():
    body = make_single_triangle()

    _curvature_cache.clear()
    H = _compute_face_curvature(body)
    _curvature_cache.clear()

    assert H.shape == (1,)
    np.testing.assert_allclose(H, 0.0)


def test_resolve_channel_preset_dir_keeps_relative_subpath(monkeypatch, tmp_path):
    data_root = tmp_path / "data"
    monkeypatch.setenv("AEGIS_DATA_DIR", str(data_root))

    cfg = {"dosimetry": {"stochastic": {"preset_dir": "custom/channel_presets"}}}

    assert _resolve_channel_preset_dir(cfg) == data_root / "custom/channel_presets"


def test_resolve_channel_preset_dir_default_config_exists():
    """Default preset_dir from DEFAULTS config resolves to an existing directory."""
    resolved = _resolve_channel_preset_dir()
    assert resolved.is_dir(), f"Default preset dir does not exist: {resolved}"
