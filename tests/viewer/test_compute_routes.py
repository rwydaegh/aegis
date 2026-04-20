"""Tests for compute-related viewer routes.

Covers: /api/compute, /api/scenes, /api/scene/load, /api/voxels/hull-mesh,
/api/compute/rt, /api/compute/sionna-rt, /api/compute/voxel-rt,
/api/export/dosimetry-csv, /api/compliance/report, /api/channel-presets,
/api/gpu/status.

All expensive computations (DosimetryEngine, ray tracing, Modal) are mocked.
"""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

pytest.importorskip("flask", reason="Flask not installed (viewer extra)")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_dosimetry_result(n_triangles: int = 20):
    """Return a mock DosimetryResult with plausible values."""
    sab = np.random.default_rng(0).uniform(0, 20, n_triangles).astype(np.float64)
    ns = SimpleNamespace(
        sab=sab,
        sab_averaged=sab * 0.8,
        sab_1cm2_averaged=None,
        sinc=sab * 2.0,
        sinc_averaged=sab * 1.5,
        p_abs=float(np.sum(sab * 1e-4)),
        peak_sab=float(np.max(sab)),
        peak_sab_averaged=float(np.max(sab * 0.8)),
        sar_wb=0.001,
        fidelity_level=2,
        freq_hz=28e9,
    )

    def _ckw(*, body=None):
        sinc_wb = None
        if body is not None and ns.sinc is not None:
            sinc_wb = float(np.sum(ns.sinc * body.areas) / np.sum(body.areas))
        return {
            "sab_4cm2": ns.peak_sab_averaged,
            "sab_1cm2": None,
            "sar_wb": ns.sar_wb,
            "sinc_local": float(np.max(ns.sinc_averaged)),
            "sinc_whole_body": sinc_wb,
        }

    ns.compliance_kwargs = _ckw
    return ns


def _mock_compute_dosimetry(body, **kwargs):
    """Replacement for compute_dosimetry that returns plausible data."""
    from aegis.viewer.compute import resolve_skin_model

    tissue = kwargs.get("tissue") or resolve_skin_model("itis", 28e9)
    result = _mock_dosimetry_result(body.n_triangles)
    level = kwargs.get("level", 2)
    mode = kwargs.get("mode")
    corrections = kwargs.get("corrections")

    corr_list = []
    if corrections:
        corr_list = [k for k, v in corrections.items() if v]

    extra = {
        "S_inc": 5.0,
        "distance_m": 3.5,
        "n_paths": 1,
        "timings": {"kernel_ms": 1.0},
    }
    return result, body, tissue, level, mode, corr_list, extra


COMPUTE_PATCH = "aegis.viewer.routes.compute.compute_dosimetry"


# ---------------------------------------------------------------------------
# POST /api/compute
# ---------------------------------------------------------------------------


class TestComputeRoute:
    def test_basic_compute(self, viewer_app):
        with (
            viewer_app.test_client() as c,
            patch(
                "aegis.viewer.compute.compute_dosimetry",
                side_effect=_mock_compute_dosimetry,
            ),
        ):
            resp = c.post(
                "/api/compute",
                json={
                    "antenna_pos": [5, 0, 1],
                    "level": 2,
                    "power_dbm": 23,
                    "n_paths": 1,
                },
            )
        assert resp.status_code == 200
        assert resp.content_type == "application/octet-stream"
        stats = json.loads(resp.headers["X-Stats"])
        assert "p_abs" in stats
        assert "peak_sab" in stats
        assert stats["n_triangles"] > 0

    def test_missing_json_body_uses_defaults(self, viewer_app):
        with (
            viewer_app.test_client() as c,
            patch(
                "aegis.viewer.compute.compute_dosimetry",
                side_effect=_mock_compute_dosimetry,
            ),
        ):
            resp = c.post("/api/compute")
        # Should succeed with all defaults
        assert resp.status_code == 200

    def test_invalid_json_body(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.post(
                "/api/compute",
                data=b"not json",
                content_type="application/json",
            )
        assert resp.status_code == 400
        assert "JSON" in resp.get_json()["error"]

    def test_invalid_level_string(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.post("/api/compute", json={"level": "abc"})
        assert resp.status_code == 400
        assert "integer" in resp.get_json()["error"]

    def test_invalid_level_range(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.post("/api/compute", json={"level": 99})
        assert resp.status_code == 400

    def test_invalid_power_dbm_type(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.post("/api/compute", json={"power_dbm": "loud"})
        assert resp.status_code == 400
        assert "power_dbm" in resp.get_json()["error"]

    def test_unknown_body_returns_404(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.post("/api/compute", json={"body_name": "ghost_phantom"})
        assert resp.status_code == 404

    def test_invalid_antenna_pos_length(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.post("/api/compute", json={"antenna_pos": [1, 2]})
        assert resp.status_code == 400
        assert "3-element" in resp.get_json()["error"]

    def test_invalid_body_rotation_y(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.post("/api/compute", json={"body_rotation_y": "sideways"})
        assert resp.status_code == 400

    def test_invalid_mode(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.post("/api/compute", json={"mode": "turbo"})
        assert resp.status_code == 400

    def test_mode_bound(self, viewer_app):
        with (
            viewer_app.test_client() as c,
            patch(
                "aegis.viewer.compute.compute_dosimetry",
                side_effect=_mock_compute_dosimetry,
            ),
        ):
            resp = c.post("/api/compute", json={"mode": "bound", "n_paths": 1})
        assert resp.status_code == 200

    def test_mode_spatial_with_corrections(self, viewer_app):
        with (
            viewer_app.test_client() as c,
            patch(
                "aegis.viewer.compute.compute_dosimetry",
                side_effect=_mock_compute_dosimetry,
            ),
        ):
            resp = c.post(
                "/api/compute",
                json={
                    "mode": "spatial",
                    "fresnel": True,
                    "curvature": True,
                    "n_paths": 1,
                },
            )
        assert resp.status_code == 200

    def test_compute_exception_returns_500(self, viewer_app):
        with (
            viewer_app.test_client() as c,
            patch(
                "aegis.viewer.compute.compute_dosimetry",
                side_effect=RuntimeError("Engine exploded"),
            ),
        ):
            resp = c.post(
                "/api/compute",
                json={"antenna_pos": [5, 0, 1], "n_paths": 1},
            )
        assert resp.status_code == 500
        assert "exploded" in resp.get_json()["error"].lower()

    def test_stochastic_channel_params(self, viewer_app):
        with (
            viewer_app.test_client() as c,
            patch(
                "aegis.viewer.compute.compute_dosimetry",
                side_effect=_mock_compute_dosimetry,
            ),
        ):
            resp = c.post(
                "/api/compute",
                json={
                    "stochastic": True,
                    "stochastic_preset": "Freespace",
                    "stochastic_seed": 42,
                    "n_paths": 1,
                },
            )
        assert resp.status_code == 200

    def test_stochastic_preset_rejects_path_traversal(self, viewer_app):
        with viewer_app.test_client() as c:
            for bad in ("/etc/host", "/etc/resolv", "../../../etc/host", "NotAPreset"):
                resp = c.post(
                    "/api/compute",
                    json={
                        "stochastic": True,
                        "stochastic_preset": bad,
                        "stochastic_seed": 42,
                        "n_paths": 1,
                    },
                )
                assert resp.status_code == 400, f"expected 400 for {bad!r}, got {resp.status_code}"
                assert "preset" in resp.get_json()["error"].lower()

    def test_invalid_stochastic_seed(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.post(
                "/api/compute",
                json={
                    "stochastic": True,
                    "stochastic_seed": "not_a_number",
                    "n_paths": 1,
                },
            )
        assert resp.status_code == 400

    def test_invalid_freq_hz(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.post("/api/compute", json={"freq_hz": -1, "n_paths": 1})
        assert resp.status_code == 400

    def test_invalid_exposure_scenario(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.post(
                "/api/compute",
                json={"exposure_scenario": "zombie_apocalypse", "n_paths": 1},
            )
        assert resp.status_code == 400

    def test_response_has_arrays_meta(self, viewer_app):
        with (
            viewer_app.test_client() as c,
            patch(
                "aegis.viewer.compute.compute_dosimetry",
                side_effect=_mock_compute_dosimetry,
            ),
        ):
            resp = c.post(
                "/api/compute",
                json={"n_paths": 1, "quantities": ["sab", "sab_4cm2"]},
            )
        assert resp.status_code == 200
        stats = json.loads(resp.headers["X-Stats"])
        assert "arrays" in stats
        keys = [a["key"] for a in stats["arrays"]]
        assert "sab" in keys


# ---------------------------------------------------------------------------
# GET /api/scenes
# ---------------------------------------------------------------------------


class TestScenesRoute:
    def test_scenes_without_differt(self, viewer_app):
        with (
            viewer_app.test_client() as c,
            patch(
                "aegis.viewer.routes.compute.list_available_scenes",
                side_effect=ImportError("DiffeRT not installed"),
                create=True,
            ),
        ):
            # The route catches ImportError at module import time
            resp = c.get("/api/scenes")
        # May return 501 (not implemented) or a list if DiffeRT is installed
        assert resp.status_code in (200, 501)

    def test_scenes_returns_list(self, viewer_app):
        with (
            viewer_app.test_client() as c,
            patch(
                "aegis.viewer.raytracer.list_available_scenes",
                return_value=[{"name": "test_scene", "path": "/tmp/scene.xml"}],
            ),
        ):
            resp = c.get("/api/scenes")
        if resp.status_code == 200:
            data = resp.get_json()
            assert isinstance(data, list)


# ---------------------------------------------------------------------------
# POST /api/scene/load
# ---------------------------------------------------------------------------


class TestSceneLoadRoute:
    def test_missing_path_returns_400(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.post("/api/scene/load", json={})
        # Either 400 (missing path) or 501 (no DiffeRT)
        assert resp.status_code in (400, 501)

    def test_invalid_json_returns_400(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.post(
                "/api/scene/load",
                data=b"not json",
                content_type="application/json",
            )
        assert resp.status_code in (400, 501)

    def test_scene_load_returns_binary(self, viewer_app):
        mock_data = b"\x00" * 100
        mock_meta = {"n_vertices": 10, "n_triangles": 5}
        valid_path = "/opt/scenes/test/test.xml"
        with (
            viewer_app.test_client() as c,
            patch("aegis.viewer.raytracer.load_scene", return_value={}),
            patch(
                "aegis.viewer.raytracer.scene_geometry_to_binary",
                return_value=(mock_data, mock_meta),
            ),
            patch(
                "aegis.viewer.routes.compute._validate_scene_path",
                return_value=True,
            ),
        ):
            resp = c.post("/api/scene/load", json={"path": valid_path})
        if resp.status_code == 200:
            assert resp.content_type == "application/octet-stream"
            meta = json.loads(resp.headers["X-Meta"])
            assert meta["n_triangles"] == 5

    def test_scene_load_rejects_path_traversal(self, viewer_app):
        """Path traversal attempts must be rejected."""
        with (
            viewer_app.test_client() as c,
            patch(
                "aegis.viewer.routes.compute._validate_scene_path",
                return_value=False,
            ),
        ):
            resp = c.post(
                "/api/scene/load",
                json={"path": "/etc/passwd"},
            )
        # 400 (invalid scene) or 501 (no DiffeRT)
        assert resp.status_code in (400, 501)
        if resp.status_code == 400:
            data = resp.get_json()
            assert "Invalid scene path" in data["error"]


# ---------------------------------------------------------------------------
# GET /api/voxels/hull-mesh
# ---------------------------------------------------------------------------


class TestVoxelsHullMeshRoute:
    def test_no_voxels_returns_400(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.get("/api/voxels/hull-mesh")
        # 400 (no voxels) or 501 (no DiffeRT)
        assert resp.status_code in (400, 501)


# ---------------------------------------------------------------------------
# POST /api/compute/rt
# ---------------------------------------------------------------------------


class TestComputeRtRoute:
    def test_invalid_json_returns_400(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.post(
                "/api/compute/rt",
                data=b"bad",
                content_type="application/json",
            )
        # 400 or 501 (no DiffeRT)
        assert resp.status_code in (400, 501)

    def test_no_scene_or_voxels_returns_400(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.post(
                "/api/compute/rt",
                json={"antenna_pos": [5, 0, 1]},
            )
        # 400 (no scene loaded) or 501 (no DiffeRT)
        assert resp.status_code in (400, 501)

    def test_unknown_body_returns_404(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.post(
                "/api/compute/rt",
                json={"body_name": "nonexistent", "antenna_pos": [5, 0, 1]},
            )
        # 404 (body not found) or 501 (no DiffeRT)
        assert resp.status_code in (404, 501)

    def test_invalid_mode_returns_400(self, viewer_app):
        with (
            viewer_app.test_client() as c,
            patch("aegis.viewer.routes.compute._validate_scene_path", return_value=True),
        ):
            resp = c.post(
                "/api/compute/rt",
                json={
                    "antenna_pos": [5, 0, 1],
                    "mode": "invalid_mode",
                    "scene_path": "/tmp/scene.xml",
                },
            )
        assert resp.status_code in (400, 501)


# ---------------------------------------------------------------------------
# POST /api/compute/sionna-rt
# ---------------------------------------------------------------------------


class TestComputeSionnaRtRoute:
    def test_invalid_json_returns_400(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.post(
                "/api/compute/sionna-rt",
                data=b"garbage",
                content_type="application/json",
            )
        assert resp.status_code == 400

    def test_missing_scene_path_returns_400(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.post("/api/compute/sionna-rt", json={})
        assert resp.status_code == 400
        assert "scene_path" in resp.get_json()["error"].lower()

    def test_unknown_body_returns_404(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.post(
                "/api/compute/sionna-rt",
                json={"body_name": "ghost", "scene_path": "/tmp/s.xml"},
            )
        assert resp.status_code == 404

    def test_invalid_scene_path_returns_400(self, viewer_app):
        with (
            viewer_app.test_client() as c,
            patch("aegis.viewer.routes.compute._validate_scene_path", return_value=False),
        ):
            resp = c.post(
                "/api/compute/sionna-rt",
                json={
                    "scene_path": "/etc/passwd",
                    "antenna_pos": [5, 0, 1],
                },
            )
        assert resp.status_code == 400
        assert "Invalid scene path" in resp.get_json()["error"]

    def test_gpu_unavailable_returns_501(self, viewer_app):
        with (
            viewer_app.test_client() as c,
            patch("aegis.viewer.routes.compute._validate_scene_path", return_value=True),
            patch("aegis.viewer.modal_proxy.gpu_status", return_value={"warm": False, "enabled": False}),
            patch("aegis.viewer.modal_proxy.trace_sionna_bundled", return_value=None),
        ):
            resp = c.post(
                "/api/compute/sionna-rt",
                json={
                    "scene_path": "/tmp/test/test.xml",
                    "antenna_pos": [5, 0, 1],
                },
            )
        assert resp.status_code == 501


# ---------------------------------------------------------------------------
# POST /api/compute/voxel-rt
# ---------------------------------------------------------------------------


class TestComputeVoxelRtRoute:
    def test_invalid_json_returns_400(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.post(
                "/api/compute/voxel-rt",
                data=b"bad",
                content_type="application/json",
            )
        assert resp.status_code == 400

    def test_no_voxels_returns_400(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.post(
                "/api/compute/voxel-rt",
                json={"antenna_pos": [5, 0, 1]},
            )
        assert resp.status_code == 400
        assert "voxel" in resp.get_json()["error"].lower()

    def test_unknown_body_returns_404(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.post(
                "/api/compute/voxel-rt",
                json={"body_name": "ghost"},
            )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /api/export/dosimetry-csv
# ---------------------------------------------------------------------------


class TestExportDosimetryCsvRoute:
    def test_no_result_returns_404(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.get("/api/export/dosimetry-csv")
        assert resp.status_code == 404
        assert "No dosimetry result" in resp.get_json()["error"]

    def test_csv_export_after_compute(self, viewer_app):
        """Inject a mock result into session cache, verify CSV export."""
        from aegis.viewer.server import _cache, _cache_lock

        n_tri = 5
        result = _mock_dosimetry_result(n_tri)

        body = MagicMock()
        body.n_triangles = n_tri
        body.centroids = np.random.default_rng(1).uniform(-1, 1, (n_tri, 3))
        body.normals = np.tile([0, 0, 1.0], (n_tri, 1))
        body.areas = np.full(n_tri, 1e-4)

        with viewer_app.test_client() as c:
            with c.session_transaction() as sess:
                sess["session_id"] = "test-session"
            with _cache_lock:
                _cache["test-session:_last_dosimetry_result"] = result
                _cache["test-session:_last_dosimetry_body"] = body
            resp = c.get("/api/export/dosimetry-csv")
            with _cache_lock:
                _cache.pop("test-session:_last_dosimetry_result", None)
                _cache.pop("test-session:_last_dosimetry_body", None)
        assert resp.status_code == 200
        assert "text/csv" in resp.content_type
        assert "attachment" in resp.headers.get("Content-Disposition", "")

        # Parse CSV content
        text = resp.data.decode("utf-8")
        lines = text.strip().split("\n")
        header = lines[0]
        assert "cx" in header
        assert "sab_w_m2" in header
        # One header + n_tri data rows
        assert len(lines) == n_tri + 1


# ---------------------------------------------------------------------------
# GET /api/compliance/report (deprecated)
# ---------------------------------------------------------------------------


class TestComplianceReportRoute:
    def test_returns_410_gone(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.get("/api/compliance/report")
        assert resp.status_code == 410
        data = resp.get_json()
        assert "X-Stats" in data["error"]


# ---------------------------------------------------------------------------
# GET /api/channel-presets
# ---------------------------------------------------------------------------


class TestChannelPresetsRoute:
    def test_returns_list(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.get("/api/channel-presets")
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, list)
        # Each entry has name and params
        if len(data) > 0:
            entry = data[0]
            assert "name" in entry
            assert "params" in entry


# ---------------------------------------------------------------------------
# GET /api/gpu/status
# ---------------------------------------------------------------------------


class TestGpuStatusRoute:
    def test_returns_status_dict(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.get("/api/gpu/status")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "warm" in data
        assert "enabled" in data
        assert isinstance(data["warm"], bool)
        assert isinstance(data["enabled"], bool)


# ---------------------------------------------------------------------------
# Additional compute route coverage
# ---------------------------------------------------------------------------


class TestComputeRouteExtended:
    """Additional edge cases for POST /api/compute."""

    def test_mode_aggregate(self, viewer_app):
        with (
            viewer_app.test_client() as c,
            patch(
                "aegis.viewer.compute.compute_dosimetry",
                side_effect=_mock_compute_dosimetry,
            ),
        ):
            resp = c.post("/api/compute", json={"mode": "aggregate", "n_paths": 1})
        assert resp.status_code == 200

    def test_level_zero_bound(self, viewer_app):
        with (
            viewer_app.test_client() as c,
            patch(
                "aegis.viewer.compute.compute_dosimetry",
                side_effect=_mock_compute_dosimetry,
            ),
        ):
            resp = c.post("/api/compute", json={"level": 0, "n_paths": 1})
        assert resp.status_code == 200

    def test_level_six_diffraction(self, viewer_app):
        with (
            viewer_app.test_client() as c,
            patch(
                "aegis.viewer.compute.compute_dosimetry",
                side_effect=_mock_compute_dosimetry,
            ),
        ):
            resp = c.post("/api/compute", json={"level": 6, "n_paths": 1})
        assert resp.status_code == 200

    def test_invalid_freq_hz_type_string(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.post("/api/compute", json={"freq_hz": "not_a_number", "n_paths": 1})
        assert resp.status_code == 400
        assert "freq_hz" in resp.get_json()["error"]

    def test_body_offset_wrong_length(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.post("/api/compute", json={"body_offset": [1, 2], "n_paths": 1})
        assert resp.status_code == 400
        assert "3-element" in resp.get_json()["error"]

    def test_body_offset_non_numeric(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.post("/api/compute", json={"body_offset": ["a", "b", "c"], "n_paths": 1})
        assert resp.status_code == 400
        assert "numeric" in resp.get_json()["error"]

    def test_json_body_not_object_returns_400(self, viewer_app):
        """JSON body must be a dict, not a list or string."""
        with viewer_app.test_client() as c:
            resp = c.post(
                "/api/compute",
                data=b"[1, 2, 3]",
                content_type="application/json",
            )
        assert resp.status_code == 400

    def test_skin_model_itis_default(self, viewer_app):
        with (
            viewer_app.test_client() as c,
            patch(
                "aegis.viewer.compute.compute_dosimetry",
                side_effect=_mock_compute_dosimetry,
            ),
        ):
            resp = c.post("/api/compute", json={"skin_model": "itis", "n_paths": 1})
        assert resp.status_code == 200

    def test_unknown_skin_model_returns_400(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.post("/api/compute", json={"skin_model": "unobtanium", "n_paths": 1})
        assert resp.status_code == 400

    def test_quantities_sinc_local(self, viewer_app):
        """Request sinc_local quantity in the response arrays."""
        with (
            viewer_app.test_client() as c,
            patch(
                "aegis.viewer.compute.compute_dosimetry",
                side_effect=_mock_compute_dosimetry,
            ),
        ):
            resp = c.post(
                "/api/compute",
                json={"n_paths": 1, "quantities": ["sab", "sinc_local"]},
            )
        assert resp.status_code == 200
        stats = json.loads(resp.headers["X-Stats"])
        keys = [a["key"] for a in stats["arrays"]]
        assert "sab" in keys

    def test_occupational_scenario(self, viewer_app):
        with (
            viewer_app.test_client() as c,
            patch(
                "aegis.viewer.compute.compute_dosimetry",
                side_effect=_mock_compute_dosimetry,
            ),
        ):
            resp = c.post(
                "/api/compute",
                json={"exposure_scenario": "occupational", "n_paths": 1},
            )
        assert resp.status_code == 200
        stats = json.loads(resp.headers["X-Stats"])
        # Compliance section should use occupational scenario
        if stats.get("compliance"):
            assert stats["compliance"]["scenario"] == "occupational"

    def test_valid_body_offset_and_rotation(self, viewer_app):
        with (
            viewer_app.test_client() as c,
            patch(
                "aegis.viewer.compute.compute_dosimetry",
                side_effect=_mock_compute_dosimetry,
            ),
        ):
            resp = c.post(
                "/api/compute",
                json={
                    "body_offset": [0.5, 0, 0],
                    "body_rotation_y": 1.57,
                    "n_paths": 1,
                },
            )
        assert resp.status_code == 200

    def test_response_binary_data_is_float32(self, viewer_app):
        with (
            viewer_app.test_client() as c,
            patch(
                "aegis.viewer.compute.compute_dosimetry",
                side_effect=_mock_compute_dosimetry,
            ),
        ):
            resp = c.post("/api/compute", json={"n_paths": 1})
        assert resp.status_code == 200
        stats = json.loads(resp.headers["X-Stats"])
        n_triangles = stats["n_triangles"]
        sab_arr = np.frombuffer(resp.data[: n_triangles * 4], dtype=np.float32)
        assert len(sab_arr) == n_triangles
        assert np.all(np.isfinite(sab_arr))

    def test_stats_has_peaks(self, viewer_app):
        with (
            viewer_app.test_client() as c,
            patch(
                "aegis.viewer.compute.compute_dosimetry",
                side_effect=_mock_compute_dosimetry,
            ),
        ):
            resp = c.post("/api/compute", json={"n_paths": 1})
        stats = json.loads(resp.headers["X-Stats"])
        assert "peaks" in stats
        assert "sab" in stats["peaks"]

    def test_stats_has_timings(self, viewer_app):
        with (
            viewer_app.test_client() as c,
            patch(
                "aegis.viewer.compute.compute_dosimetry",
                side_effect=_mock_compute_dosimetry,
            ),
        ):
            resp = c.post("/api/compute", json={"n_paths": 1})
        stats = json.loads(resp.headers["X-Stats"])
        assert "timings" in stats
        assert "route_total_ms" in stats["timings"]


class TestExportDosimetryCsvExtended:
    """Additional CSV export coverage."""

    def test_csv_contains_all_optional_columns(self, viewer_app):
        """When sinc and sab_1cm2 are present, CSV should include them."""
        from aegis.viewer.server import _cache, _cache_lock

        n_tri = 5
        result = _mock_dosimetry_result(n_tri)
        # Ensure sab_1cm2_averaged is populated
        result.sab_1cm2_averaged = result.sab * 0.6

        body = MagicMock()
        body.n_triangles = n_tri
        body.centroids = np.random.default_rng(2).uniform(-1, 1, (n_tri, 3))
        body.normals = np.tile([0, 0, 1.0], (n_tri, 1))
        body.areas = np.full(n_tri, 1e-4)

        with viewer_app.test_client() as c:
            with c.session_transaction() as sess:
                sess["session_id"] = "test-session"
            with _cache_lock:
                _cache["test-session:_last_dosimetry_result"] = result
                _cache["test-session:_last_dosimetry_body"] = body
            resp = c.get("/api/export/dosimetry-csv")
            with _cache_lock:
                _cache.pop("test-session:_last_dosimetry_result", None)
                _cache.pop("test-session:_last_dosimetry_body", None)
        assert resp.status_code == 200
        text = resp.data.decode("utf-8")
        header = text.split("\n")[0]
        assert "sab_4cm2_w_m2" in header
        assert "sinc_w_m2" in header
        assert "sab_1cm2_w_m2" in header


class TestComputeRtExtended:
    """Additional edge cases for RT routes."""

    def test_invalid_power_dbm_returns_400(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.post(
                "/api/compute/rt",
                json={"antenna_pos": [5, 0, 1], "power_dbm": "loud"},
            )
        assert resp.status_code in (400, 501)

    def test_invalid_level_returns_400(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.post(
                "/api/compute/rt",
                json={"antenna_pos": [5, 0, 1], "level": "abc"},
            )
        assert resp.status_code in (400, 501)

    def test_level_out_of_range_returns_400(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.post(
                "/api/compute/rt",
                json={"antenna_pos": [5, 0, 1], "level": 99},
            )
        assert resp.status_code in (400, 501)

    def test_rt_caches_transformed_body_for_export(self, viewer_app):
        from aegis.paths import PropagationPaths
        from aegis.viewer.server import _cache, _cache_lock

        base_body = _cache["body"]
        fake_result = _mock_dosimetry_result(base_body.n_triangles)
        paths = PropagationPaths.from_powers(
            k_hat=np.array([[0.0, 0.0, -1.0]]),
            power=np.array([1.0]),
        )

        with (
            viewer_app.test_client() as c,
            patch("aegis.viewer.routes.compute._validate_scene_path", return_value=True),
            patch("aegis.viewer.modal_proxy.gpu_status", return_value={"warm": True}),
            patch("aegis.viewer.modal_proxy._is_enabled", return_value=False),
            patch("aegis.viewer.raytracer.compute_paths_differt", return_value=(paths, [])),
            patch("aegis.viewer.routes.compute._run_dosimetry", return_value=(fake_result, None)),
        ):
            with c.session_transaction() as sess:
                sess["session_id"] = "test-session"
            resp = c.post(
                "/api/compute/rt",
                json={
                    "scene_path": "/tmp/fake_scene.xml",
                    "antenna_pos": [5, 0, 1],
                    "body_offset": [0.25, -0.1, 0.0],
                    "body_rotation_y": 0.3,
                },
            )

        assert resp.status_code == 200
        with _cache_lock:
            exported_body = _cache["test-session:_last_dosimetry_body"]
        assert exported_body is not base_body
        assert exported_body.n_triangles == base_body.n_triangles
        assert not np.allclose(exported_body.centroids, base_body.centroids)


class TestComputeSionnaRtExtended:
    """Additional edge cases for Sionna RT."""

    def test_invalid_power_dbm_returns_400(self, viewer_app):
        with (
            viewer_app.test_client() as c,
            patch("aegis.viewer.routes.compute._validate_scene_path", return_value=True),
        ):
            resp = c.post(
                "/api/compute/sionna-rt",
                json={"scene_path": "/tmp/s.xml", "power_dbm": "loud"},
            )
        assert resp.status_code == 400

    def test_invalid_mode_returns_400(self, viewer_app):
        with (
            viewer_app.test_client() as c,
            patch("aegis.viewer.routes.compute._validate_scene_path", return_value=True),
        ):
            resp = c.post(
                "/api/compute/sionna-rt",
                json={"scene_path": "/tmp/s.xml", "mode": "turbo"},
            )
        assert resp.status_code == 400

    def test_invalid_freq_hz_returns_400(self, viewer_app):
        with (
            viewer_app.test_client() as c,
            patch("aegis.viewer.routes.compute._validate_scene_path", return_value=True),
        ):
            resp = c.post(
                "/api/compute/sionna-rt",
                json={"scene_path": "/tmp/s.xml", "freq_hz": -100},
            )
        assert resp.status_code == 400

    def test_invalid_body_offset_returns_400(self, viewer_app):
        with (
            viewer_app.test_client() as c,
            patch("aegis.viewer.routes.compute._validate_scene_path", return_value=True),
        ):
            resp = c.post(
                "/api/compute/sionna-rt",
                json={"scene_path": "/tmp/s.xml", "body_offset": [1, 2]},
            )
        assert resp.status_code == 400

    def test_invalid_exposure_scenario_returns_400(self, viewer_app):
        with (
            viewer_app.test_client() as c,
            patch("aegis.viewer.routes.compute._validate_scene_path", return_value=True),
        ):
            resp = c.post(
                "/api/compute/sionna-rt",
                json={
                    "scene_path": "/tmp/s.xml",
                    "exposure_scenario": "alien_invasion",
                },
            )
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Multi-antenna array parsing
# ---------------------------------------------------------------------------


class TestComputeAntennasArray:
    def test_compute_with_antennas_array(self, viewer_app):
        """POST /api/compute with a multi-antenna array returns 200."""
        with (
            viewer_app.test_client() as c,
            patch(
                "aegis.viewer.compute.compute_dosimetry",
                side_effect=_mock_compute_dosimetry,
            ),
        ):
            resp = c.post(
                "/api/compute",
                json={
                    "antennas": [
                        {
                            "position": [5, 0, 1],
                            "power_dbm": 23,
                            "array_config": {"n_elements": 4},
                        },
                        {
                            "position": [10, 2, 1.5],
                            "power_dbm": 20,
                            "array_config": {"n_elements": 2},
                        },
                    ],
                    "level": 2,
                },
            )
        assert resp.status_code == 200

    def test_compute_legacy_antenna_pos_still_works(self, viewer_app):
        """POST /api/compute with old-style antenna_pos and power_dbm (no antennas key) returns 200."""
        with (
            viewer_app.test_client() as c,
            patch(
                "aegis.viewer.compute.compute_dosimetry",
                side_effect=_mock_compute_dosimetry,
            ),
        ):
            resp = c.post(
                "/api/compute",
                json={
                    "antenna_pos": [5, 0, 1],
                    "power_dbm": 23,
                    "level": 2,
                },
            )
        assert resp.status_code == 200

    def test_antennas_invalid_power_dbm_returns_400(self, viewer_app):
        """POST /api/compute with a non-numeric power_dbm inside antennas returns 400 (not 500)."""
        with viewer_app.test_client() as c:
            resp = c.post(
                "/api/compute",
                json={
                    "antennas": [
                        {"position": [5, 0, 1], "power_dbm": "loud"},
                    ],
                    "level": 2,
                },
            )
        assert resp.status_code == 400
        assert "power_dbm" in resp.get_json()["error"]

    def test_antennas_invalid_array_config_returns_400(self, viewer_app):
        """POST /api/compute with a non-dict array_config returns 400 (not 500)."""
        with viewer_app.test_client() as c:
            resp = c.post(
                "/api/compute",
                json={
                    "antennas": [
                        {"position": [5, 0, 1], "power_dbm": 23, "array_config": "bogus"},
                    ],
                    "level": 2,
                },
            )
        assert resp.status_code == 400
        assert "array_config" in resp.get_json()["error"]


class TestComputeVoxelRtExtended:
    """Additional edge cases for voxel RT."""

    def test_invalid_power_dbm_returns_400(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.post(
                "/api/compute/voxel-rt",
                json={"power_dbm": "loud"},
            )
        # 400 for either invalid power or no voxels
        assert resp.status_code in (400, 404)

    def test_invalid_level_returns_400(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.post(
                "/api/compute/voxel-rt",
                json={"level": "abc"},
            )
        assert resp.status_code in (400, 404)

    def test_invalid_exposure_scenario_returns_400(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.post(
                "/api/compute/voxel-rt",
                json={"exposure_scenario": "zombie_apocalypse"},
            )
        assert resp.status_code in (400, 404)


# ---------------------------------------------------------------------------
# GET /api/export/dosimetry-json
# ---------------------------------------------------------------------------


class TestExportDosimetryJsonRoute:
    def test_no_result_returns_404(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.get("/api/export/dosimetry-json")
        assert resp.status_code == 404
        assert "No dosimetry result" in resp.get_json()["error"]

    def test_json_export_after_compute(self, viewer_app):
        """Inject a mock result, verify JSON export structure."""
        from aegis.viewer.server import _cache, _cache_lock

        n_tri = 5
        result = _mock_dosimetry_result(n_tri)
        body = MagicMock()
        body.n_triangles = n_tri
        body.name = "thelonious"
        body.centroids = np.random.default_rng(3).uniform(-1, 1, (n_tri, 3))
        body.normals = np.tile([0, 0, 1.0], (n_tri, 1))
        body.areas = np.full(n_tri, 1e-4)

        with viewer_app.test_client() as c:
            with c.session_transaction() as sess:
                sess["session_id"] = "test-session"
            with _cache_lock:
                _cache["test-session:_last_dosimetry_result"] = result
                _cache["test-session:_last_dosimetry_body"] = body
                _cache["test-session:_last_dosimetry_stats"] = None
            resp = c.get("/api/export/dosimetry-json")
            with _cache_lock:
                _cache.pop("test-session:_last_dosimetry_result", None)
                _cache.pop("test-session:_last_dosimetry_body", None)
                _cache.pop("test-session:_last_dosimetry_stats", None)
        assert resp.status_code == 200
        assert "application/json" in resp.content_type
        assert "attachment" in resp.headers.get("Content-Disposition", "")

        data = json.loads(resp.data)
        assert data["meta"]["body"] == "thelonious"
        assert data["meta"]["n_triangles"] == n_tri
        assert len(data["sab"]) == n_tri
        assert len(data["centroids"]) == n_tri
        assert len(data["normals"]) == n_tri
        assert len(data["areas"]) == n_tri
        # Optional arrays present when populated
        assert "sab_4cm2" in data
        assert "sinc" in data

    def test_json_export_includes_stats(self, viewer_app):
        """Stats dict should be included but without 'arrays' or 'path_viz' keys."""
        from aegis.viewer.server import _cache, _cache_lock

        n_tri = 3
        result = _mock_dosimetry_result(n_tri)
        body = MagicMock()
        body.n_triangles = n_tri
        body.name = "test"
        body.centroids = np.zeros((n_tri, 3))
        body.normals = np.tile([0, 0, 1.0], (n_tri, 1))
        body.areas = np.full(n_tri, 1e-4)

        stats = {
            "peak_sab": 12.0,
            "p_abs_mw": 5.0,
            "arrays": {"should_be_excluded": True},
            "path_viz": {"also_excluded": True},
        }

        with viewer_app.test_client() as c:
            with c.session_transaction() as sess:
                sess["session_id"] = "test-session"
            with _cache_lock:
                _cache["test-session:_last_dosimetry_result"] = result
                _cache["test-session:_last_dosimetry_body"] = body
                _cache["test-session:_last_dosimetry_stats"] = stats
            resp = c.get("/api/export/dosimetry-json")
            with _cache_lock:
                _cache.pop("test-session:_last_dosimetry_result", None)
                _cache.pop("test-session:_last_dosimetry_body", None)
                _cache.pop("test-session:_last_dosimetry_stats", None)
        data = json.loads(resp.data)
        assert "stats" in data
        assert "peak_sab" in data["stats"]
        assert "arrays" not in data["stats"]
        assert "path_viz" not in data["stats"]

    def test_json_export_optional_arrays_absent(self, viewer_app):
        """Optional arrays that are None should not appear in JSON."""
        from aegis.viewer.server import _cache, _cache_lock

        n_tri = 3
        result = SimpleNamespace(
            sab=np.array([1.0, 2.0, 3.0]),
            sab_averaged=None,
            sab_1cm2_averaged=None,
            sinc=None,
            sinc_averaged=None,
            p_abs=0.001,
            peak_sab=3.0,
            sar_wb=0.0001,
            fidelity_level=0,
            freq_hz=28e9,
        )
        body = MagicMock()
        body.n_triangles = n_tri
        body.name = "test"
        body.centroids = np.zeros((n_tri, 3))
        body.normals = np.tile([0, 0, 1.0], (n_tri, 1))
        body.areas = np.full(n_tri, 1e-4)

        with viewer_app.test_client() as c:
            with c.session_transaction() as sess:
                sess["session_id"] = "test-session"
            with _cache_lock:
                _cache["test-session:_last_dosimetry_result"] = result
                _cache["test-session:_last_dosimetry_body"] = body
                _cache["test-session:_last_dosimetry_stats"] = None
            resp = c.get("/api/export/dosimetry-json")
            with _cache_lock:
                _cache.pop("test-session:_last_dosimetry_result", None)
                _cache.pop("test-session:_last_dosimetry_body", None)
                _cache.pop("test-session:_last_dosimetry_stats", None)
        data = json.loads(resp.data)
        assert "sab" in data
        assert "sab_4cm2" not in data
        assert "sinc" not in data
        assert "sinc_4cm2" not in data
        assert "sab_1cm2" not in data


# ---------------------------------------------------------------------------
# GET /api/export/dosimetry-npz
# ---------------------------------------------------------------------------


class TestExportDosimetryNpzRoute:
    def test_no_result_returns_404(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.get("/api/export/dosimetry-npz")
        assert resp.status_code == 404
        assert "No dosimetry result" in resp.get_json()["error"]

    def test_npz_export_after_compute(self, viewer_app):
        """Inject a mock result, verify NPZ export contains expected arrays."""
        import io

        from aegis.viewer.server import _cache, _cache_lock

        n_tri = 5
        result = _mock_dosimetry_result(n_tri)
        body = MagicMock()
        body.n_triangles = n_tri
        body.centroids = np.random.default_rng(4).uniform(-1, 1, (n_tri, 3))
        body.normals = np.tile([0, 0, 1.0], (n_tri, 1))
        body.areas = np.full(n_tri, 1e-4)

        with viewer_app.test_client() as c:
            with c.session_transaction() as sess:
                sess["session_id"] = "test-session"
            with _cache_lock:
                _cache["test-session:_last_dosimetry_result"] = result
                _cache["test-session:_last_dosimetry_body"] = body
            resp = c.get("/api/export/dosimetry-npz")
            with _cache_lock:
                _cache.pop("test-session:_last_dosimetry_result", None)
                _cache.pop("test-session:_last_dosimetry_body", None)
        assert resp.status_code == 200
        assert "application/octet-stream" in resp.content_type
        assert "attachment" in resp.headers.get("Content-Disposition", "")

        # Parse NPZ and verify arrays
        npz = np.load(io.BytesIO(resp.data))
        assert "centroids" in npz
        assert "normals" in npz
        assert "areas" in npz
        assert "sab" in npz
        assert npz["sab"].shape == (n_tri,)
        assert npz["centroids"].shape == (n_tri, 3)
        # Optional arrays present when populated
        assert "sab_4cm2" in npz
        assert "sinc" in npz

    def test_npz_export_optional_arrays_absent(self, viewer_app):
        """Optional arrays that are None should not appear in NPZ."""
        import io

        from aegis.viewer.server import _cache, _cache_lock

        n_tri = 3
        result = SimpleNamespace(
            sab=np.array([1.0, 2.0, 3.0]),
            sab_averaged=None,
            sab_1cm2_averaged=None,
            sinc=None,
            sinc_averaged=None,
            p_abs=0.001,
            peak_sab=3.0,
            sar_wb=0.0001,
            fidelity_level=0,
            freq_hz=28e9,
        )
        body = MagicMock()
        body.n_triangles = n_tri
        body.centroids = np.zeros((n_tri, 3))
        body.normals = np.tile([0, 0, 1.0], (n_tri, 1))
        body.areas = np.full(n_tri, 1e-4)

        with viewer_app.test_client() as c:
            with c.session_transaction() as sess:
                sess["session_id"] = "test-session"
            with _cache_lock:
                _cache["test-session:_last_dosimetry_result"] = result
                _cache["test-session:_last_dosimetry_body"] = body
            resp = c.get("/api/export/dosimetry-npz")
            with _cache_lock:
                _cache.pop("test-session:_last_dosimetry_result", None)
                _cache.pop("test-session:_last_dosimetry_body", None)
        npz = np.load(io.BytesIO(resp.data))
        assert "sab" in npz
        assert "sab_4cm2" not in npz
        assert "sinc" not in npz
        assert "sinc_4cm2" not in npz
        assert "sab_1cm2" not in npz
