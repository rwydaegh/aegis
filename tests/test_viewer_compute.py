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


def test_compute_dosimetry_forwards_diffraction_model_and_inter_body():
    body = make_flat_mesh(12)

    with patch(
        "aegis.viewer.compute.DosimetryEngine.compute_with_timings",
        return_value=(_fake_result(body.n_triangles), {}),
    ) as compute_mock:
        compute_dosimetry(
            body,
            antenna_pos=np.array([0.0, 0.0, 2.0]),
            mode="spatial",
            corrections={"diffraction_model": "fock", "inter_body": "off"},
        )

    kwargs = compute_mock.call_args.kwargs
    assert kwargs["diffraction_model"] == "fock"
    assert kwargs["inter_body"] == "off"
    # An active gate still needs curvature data even without the curvature flag.
    assert "curvature_H" in kwargs


def test_compute_dosimetry_forwards_self_shadow():
    # Regression: the /api/compute route dropped self_shadow from its
    # corrections dict, so the engine never received it (production no-op).
    body = make_flat_mesh(12)

    with patch(
        "aegis.viewer.compute.DosimetryEngine.compute_with_timings",
        return_value=(_fake_result(body.n_triangles), {}),
    ) as compute_mock:
        compute_dosimetry(
            body,
            antenna_pos=np.array([0.0, 0.0, 2.0]),
            mode="spatial",
            corrections={"diffraction_model": "fock", "inter_body": "off", "self_shadow": True},
        )

    assert compute_mock.call_args.kwargs["self_shadow"] is True


def test_compute_dosimetry_self_shadow_off_not_forwarded():
    body = make_flat_mesh(12)

    with patch(
        "aegis.viewer.compute.DosimetryEngine.compute_with_timings",
        return_value=(_fake_result(body.n_triangles), {}),
    ) as compute_mock:
        compute_dosimetry(
            body,
            antenna_pos=np.array([0.0, 0.0, 2.0]),
            mode="spatial",
            corrections={"diffraction_model": "fock", "self_shadow": False},
        )

    # Off is the engine default, so the kwarg is simply omitted.
    assert "self_shadow" not in compute_mock.call_args.kwargs


def test_route_parses_self_shadow():
    from aegis.viewer.routes.compute.dosimetry import _parse_mode_level_corrections

    dcfg = {"default_level": 2}
    _, _, corr_on, err = _parse_mode_level_corrections({"mode": "spatial", "self_shadow": "true"}, dcfg)
    assert err is None
    assert corr_on["self_shadow"] is True
    _, _, corr_def, err = _parse_mode_level_corrections({"mode": "spatial"}, dcfg)
    assert err is None
    assert corr_def["self_shadow"] is False


def test_compute_dosimetry_none_model_skips_curvature_injection():
    body = make_flat_mesh(12)

    with patch(
        "aegis.viewer.compute.DosimetryEngine.compute_with_timings",
        return_value=(_fake_result(body.n_triangles), {}),
    ) as compute_mock:
        compute_dosimetry(
            body,
            antenna_pos=np.array([0.0, 0.0, 2.0]),
            mode="spatial",
            corrections={"diffraction_model": "none"},
        )

    kwargs = compute_mock.call_args.kwargs
    assert kwargs["diffraction_model"] == "none"
    assert "curvature_H" not in kwargs


def test_route_parses_diffraction_model_and_inter_body():
    from aegis.viewer.routes.compute.dosimetry import _parse_mode_level_corrections

    dcfg = {"default_level": 2}
    _, mode, corrections, err = _parse_mode_level_corrections(
        {"mode": "spatial", "diffraction_model": "gelu", "inter_body": "specular1"}, dcfg
    )
    assert err is None
    assert mode == "spatial"
    assert corrections["diffraction_model"] == "gelu"
    assert corrections["inter_body"] == "specular1"


def test_route_maps_legacy_diffraction_bool_to_model():
    from aegis.viewer.routes.compute.dosimetry import _parse_mode_level_corrections

    dcfg = {"default_level": 2}
    _, _, corr_true, err = _parse_mode_level_corrections({"mode": "spatial", "diffraction": True}, dcfg)
    assert err is None
    assert corr_true["diffraction_model"] == "fock"

    _, _, corr_false, err = _parse_mode_level_corrections({"mode": "spatial", "diffraction": False}, dcfg)
    assert err is None
    assert corr_false["diffraction_model"] == "none"


def test_route_rejects_invalid_diffraction_model(viewer_app):
    from aegis.viewer.routes.compute.dosimetry import _parse_mode_level_corrections

    dcfg = {"default_level": 2}
    # jsonify (used to build the 400 response) needs an application context.
    with viewer_app.app_context():
        _, _, _, err = _parse_mode_level_corrections({"mode": "spatial", "diffraction_model": "bogus"}, dcfg)
    assert err is not None
    _resp, status = err
    assert status == 400


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


def test_compute_dosimetry_multi_antenna_higher_power():
    """Two co-located antennas produce more total path power than one, and n_paths == 2."""
    body = make_flat_mesh(8)

    single_antenna = [{"position": [0.0, 0.0, 2.0], "power_dbm": 23.0}]
    two_antennas = [
        {"position": [0.0, 0.0, 2.0], "power_dbm": 23.0},
        {"position": [0.1, 0.0, 2.0], "power_dbm": 23.0},
    ]

    with patch(
        "aegis.viewer.compute.DosimetryEngine.compute_with_timings",
        return_value=(_fake_result(body.n_triangles), {}),
    ):
        *_, extra_single = compute_dosimetry(
            body,
            antenna_pos=np.array([0.0, 0.0, 2.0]),
            antennas=single_antenna,
        )
        *_, extra_two = compute_dosimetry(
            body,
            antenna_pos=np.array([0.0, 0.0, 2.0]),
            antennas=two_antennas,
        )

    assert extra_two["n_paths"] == 2
    assert extra_two["S_inc"] > extra_single["S_inc"]


def test_compute_dosimetry_empty_antennas_returns_zero():
    """Empty antennas list produces one zero-power path and S_inc == 0."""
    body = make_flat_mesh(8)

    with patch(
        "aegis.viewer.compute.DosimetryEngine.compute_with_timings",
        return_value=(_fake_result(body.n_triangles), {}),
    ):
        *_, extra = compute_dosimetry(
            body,
            antenna_pos=np.array([0.0, 0.0, 2.0]),
            antennas=[],
        )

    assert extra["n_paths"] == 1
    assert extra["S_inc"] == 0.0
    assert extra["n_antennas"] == 0


def test_compute_dosimetry_antennas_with_array_gain():
    """A 4x4 isotropic array at broadside provides 256x gain over a 1x1 isotropic element."""
    body = make_flat_mesh(8)

    antenna_1x1 = [
        {
            "position": [0.0, 0.0, 2.0],
            "power_dbm": 0.0,
            "array_config": {
                "n_h": 1,
                "n_v": 1,
                "element_pattern": "isotropic",
                "broadside": [0.0, 0.0, -1.0],
            },
        }
    ]
    antenna_4x4 = [
        {
            "position": [0.0, 0.0, 2.0],
            "power_dbm": 0.0,
            "array_config": {
                "n_h": 4,
                "n_v": 4,
                "element_pattern": "isotropic",
                "broadside": [0.0, 0.0, -1.0],
            },
        }
    ]

    with patch(
        "aegis.viewer.compute.DosimetryEngine.compute_with_timings",
        return_value=(_fake_result(body.n_triangles), {}),
    ):
        *_, extra_1x1 = compute_dosimetry(
            body,
            antenna_pos=np.array([0.0, 0.0, 2.0]),
            antennas=antenna_1x1,
        )
        *_, extra_4x4 = compute_dosimetry(
            body,
            antenna_pos=np.array([0.0, 0.0, 2.0]),
            antennas=antenna_4x4,
        )

    # 4x4 = 16 elements, |AF|^2 = 16^2 = 256 at exact broadside.
    # Body center is slightly off-axis so ratio may be ~255; allow 1% tolerance.
    ratio = extra_4x4["S_inc"] / extra_1x1["S_inc"]
    np.testing.assert_allclose(ratio, 256.0, rtol=1e-2)
