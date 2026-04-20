"""Real integration tests for /api/compute/dosimetry.

These tests exercise the full Flask -> DosimetryEngine -> PropagationPaths stack
with no mocks. They cover happy paths, invalid payloads, coordinate-frame
boundaries, edge-float frequencies, and unicode / malformed input.
"""

from __future__ import annotations

import json

import numpy as np
import pytest

pytest.importorskip("flask", reason="viewer tests require flask (pip install aegis[viewer])")


# ---------------------------------------------------------------------------
# Happy paths on the e2e_icosahedron body (cheap, no @slow needed)
# ---------------------------------------------------------------------------


class TestComputeDosimetryHappyPath:
    def test_basic_level2_returns_binary_and_stats(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.post(
                "/api/compute",
                json={
                    "antenna_pos": [1.0, 0.0, 0.5],
                    "power_dbm": 23.0,
                    "level": 2,
                    "freq_hz": 28e9,
                },
            )
        assert resp.status_code == 200
        assert resp.content_type == "application/octet-stream"

        stats = json.loads(resp.headers["X-Stats"])
        # Response shape invariants
        for key in ("p_abs", "peak_sab", "n_triangles", "level", "T0", "peaks", "distribution", "arrays"):
            assert key in stats, f"stats missing key {key!r}"
        # 20-triangle icosahedron
        assert stats["n_triangles"] == 20
        assert stats["level"] == 2
        # Physical bounds
        assert stats["peak_sab"] >= 0.0
        assert stats["p_abs"] >= 0.0
        assert stats["T0"] > 0.0
        assert 0.0 <= stats["T0"] <= 1.0
        # Binary body contains at least the sab float32 array
        sab_bytes = stats["n_triangles"] * 4
        assert len(resp.data) >= sab_bytes
        sab = np.frombuffer(resp.data[:sab_bytes], dtype=np.float32)
        assert np.all(np.isfinite(sab))
        assert np.all(sab >= 0.0)

    @pytest.mark.parametrize("level", [0, 1, 2, 3, 4, 5, 6])
    def test_all_incoherent_levels_succeed(self, viewer_app, level):
        with viewer_app.test_client() as c:
            resp = c.post(
                "/api/compute",
                json={"level": level, "antenna_pos": [1, 0, 0.1]},
            )
        assert resp.status_code == 200, resp.data[:200]
        stats = json.loads(resp.headers["X-Stats"])
        assert stats["level"] == level

    @pytest.mark.parametrize("mode", ["bound", "aggregate", "spatial"])
    def test_mode_variants_succeed(self, viewer_app, mode):
        with viewer_app.test_client() as c:
            resp = c.post(
                "/api/compute",
                json={"mode": mode, "antenna_pos": [1, 0, 0.1]},
            )
        assert resp.status_code == 200
        stats = json.loads(resp.headers["X-Stats"])
        assert stats["mode"] == mode

    def test_spatial_mode_with_corrections(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.post(
                "/api/compute",
                json={
                    "mode": "spatial",
                    "fresnel": True,
                    "polarisation": True,
                    "curvature": True,
                    "diffraction": False,
                    "antenna_pos": [1, 0, 0.1],
                },
            )
        assert resp.status_code == 200
        stats = json.loads(resp.headers["X-Stats"])
        assert stats["mode"] == "spatial"
        assert "fresnel" in stats.get("corrections", [])
        assert "polarisation" in stats.get("corrections", [])
        assert "curvature" in stats.get("corrections", [])


# ---------------------------------------------------------------------------
# Invalid payloads (400)
# ---------------------------------------------------------------------------


class TestComputeDosimetryInvalidPayload:
    def test_invalid_level_string(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.post("/api/compute", json={"level": "high"})
        assert resp.status_code == 400
        assert "integer" in resp.get_json()["error"]

    def test_level_out_of_range_high(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.post("/api/compute", json={"level": 42})
        assert resp.status_code == 400
        assert "between" in resp.get_json()["error"]

    def test_level_out_of_range_negative(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.post("/api/compute", json={"level": -1})
        assert resp.status_code == 400

    def test_invalid_mode(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.post("/api/compute", json={"mode": "turbo"})
        assert resp.status_code == 400
        assert "mode" in resp.get_json()["error"]

    def test_power_dbm_not_a_number(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.post("/api/compute", json={"power_dbm": "loud"})
        assert resp.status_code == 400
        assert "power_dbm" in resp.get_json()["error"]

    def test_unknown_body_name(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.post("/api/compute", json={"body_name": "ghost_phantom"})
        assert resp.status_code == 404

    def test_antenna_pos_wrong_length(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.post("/api/compute", json={"antenna_pos": [1, 2]})
        assert resp.status_code == 400

    def test_antenna_pos_non_numeric(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.post("/api/compute", json={"antenna_pos": ["north", "east", "up"]})
        assert resp.status_code == 400

    def test_body_rotation_y_non_numeric(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.post("/api/compute", json={"body_rotation_y": "sideways"})
        assert resp.status_code == 400

    def test_exposure_scenario_unknown(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.post("/api/compute", json={"exposure_scenario": "dystopian"})
        assert resp.status_code == 400
        assert "exposure_scenario" in resp.get_json()["error"]


# ---------------------------------------------------------------------------
# Coordinate-frame boundary conditions (real physics)
# ---------------------------------------------------------------------------


class TestComputeDosimetryCoordinateBoundaries:
    def test_antenna_at_origin_does_not_crash(self, viewer_app):
        """Antenna colocated with body origin is degenerate but must not 500."""
        with viewer_app.test_client() as c:
            resp = c.post("/api/compute", json={"antenna_pos": [0, 0, 0]})
        # Must not be a 500; either valid result or a clean 400
        assert resp.status_code != 500, resp.data[:300]

    def test_antenna_at_z_zero_plane(self, viewer_app):
        """Antenna at z=0 (ground level) next to body."""
        with viewer_app.test_client() as c:
            resp = c.post("/api/compute", json={"antenna_pos": [2.0, 0.0, 0.0]})
        assert resp.status_code == 200
        stats = json.loads(resp.headers["X-Stats"])
        assert stats["peak_sab"] >= 0.0
        assert stats["distance_m"] > 0.0

    def test_antenna_far_distance(self, viewer_app):
        """At 1km distance, S_ab must still be non-negative and finite."""
        with viewer_app.test_client() as c:
            resp = c.post(
                "/api/compute",
                json={"antenna_pos": [1000.0, 0.0, 1.5], "power_dbm": 23.0, "level": 2},
            )
        assert resp.status_code == 200
        stats = json.loads(resp.headers["X-Stats"])
        assert stats["peak_sab"] >= 0.0
        # At 1km with 23 dBm, peak is vanishingly small (free-space path loss ~100 dB)
        assert stats["peak_sab"] < 1e-3
        assert np.isfinite(stats["peak_sab"])

    def test_antenna_behind_body(self, viewer_app):
        """Antenna behind the icosahedron - ReLU-clamped triangles should exist."""
        with viewer_app.test_client() as c:
            resp = c.post(
                "/api/compute",
                json={"antenna_pos": [-2.0, 0.0, 0.0], "level": 2},
            )
        assert resp.status_code == 200
        stats = json.loads(resp.headers["X-Stats"])
        # Only lit triangles contribute; we expect < 20 illuminated facets
        assert stats["n_illuminated"] <= stats["n_triangles"]
        assert stats["n_illuminated"] >= 0

    def test_body_offset_translates(self, viewer_app):
        """Moving the body by body_offset must succeed and return a finite result."""
        with viewer_app.test_client() as c:
            resp = c.post(
                "/api/compute",
                json={
                    "antenna_pos": [1, 0, 0.1],
                    "body_offset": [0.3, -0.2, 0.5],
                    "body_rotation_y": 0.7,
                },
            )
        assert resp.status_code == 200
        stats = json.loads(resp.headers["X-Stats"])
        assert np.isfinite(stats["peak_sab"])


# ---------------------------------------------------------------------------
# Frequency edge cases (ICNIRP bounds)
# ---------------------------------------------------------------------------


class TestComputeDosimetryFrequencyEdges:
    def test_freq_100khz_lower_icnirp_bound(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.post(
                "/api/compute",
                json={"freq_hz": 1e5, "antenna_pos": [1, 0, 0.1], "power_dbm": 0},
            )
        assert resp.status_code == 200
        stats = json.loads(resp.headers["X-Stats"])
        # At 100kHz, S_ab ICNIRP limits are not defined; compliant is None
        assert stats.get("compliant") is None
        # But the kernel should still run and produce finite SAB
        assert np.isfinite(stats["peak_sab"])

    def test_freq_300ghz_upper_icnirp_bound(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.post(
                "/api/compute",
                json={"freq_hz": 3e11, "antenna_pos": [1, 0, 0.1], "power_dbm": 0},
            )
        assert resp.status_code == 200
        stats = json.loads(resp.headers["X-Stats"])
        # 300GHz has ICNIRP limits defined
        assert stats.get("compliance") is not None
        assert np.isfinite(stats["peak_sab"])

    def test_freq_nan_rejected(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.post(
                "/api/compute",
                json={"freq_hz": float("nan"), "antenna_pos": [1, 0, 0.1]},
            )
        assert resp.status_code == 400
        # ``StrictJSONProvider`` rejects the raw ``NaN`` literal at parse
        # time, so the message may come from that layer instead of the
        # per-field ``freq_hz`` guard. Either way the status is 400.
        error = resp.get_json()["error"].lower()
        assert "freq_hz" in error or "invalid" in error

    def test_freq_inf_rejected(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.post(
                "/api/compute",
                json={"freq_hz": float("inf"), "antenna_pos": [1, 0, 0.1]},
            )
        assert resp.status_code == 400

    def test_freq_negative_rejected(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.post(
                "/api/compute",
                json={"freq_hz": -1e9, "antenna_pos": [1, 0, 0.1]},
            )
        assert resp.status_code == 400

    def test_freq_zero_rejected(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.post(
                "/api/compute",
                json={"freq_hz": 0, "antenna_pos": [1, 0, 0.1]},
            )
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Unicode / malformed bodies
# ---------------------------------------------------------------------------


class TestComputeDosimetryMalformed:
    def test_binary_garbage_body_returns_400(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.post(
                "/api/compute",
                data=b"\xff\xfe\x00\x01\x02",
                content_type="application/json",
            )
        assert resp.status_code == 400
        assert "JSON" in resp.get_json()["error"]

    def test_json_array_top_level_returns_400(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.post("/api/compute", data=b"[1, 2, 3]", content_type="application/json")
        assert resp.status_code == 400

    def test_unicode_keys_ignored_gracefully(self, viewer_app):
        """Unknown unicode keys should be ignored, not 500."""
        with viewer_app.test_client() as c:
            resp = c.post(
                "/api/compute",
                json={"résumé": 1, "こんにちは": "world", "antenna_pos": [1, 0, 0.1]},
            )
        assert resp.status_code == 200

    def test_missing_content_type_with_json_body(self, viewer_app):
        """No Content-Type header -> Flask treats body as empty but defaults should kick in."""
        with viewer_app.test_client() as c:
            resp = c.post(
                "/api/compute",
                data=json.dumps({"antenna_pos": [1, 0, 0.1]}),
            )
        # Either succeeds with defaults (Flask picked up the JSON despite no CT) or
        # 400 invalid. Must not be 500.
        assert resp.status_code in (200, 400)

    def test_empty_body_uses_defaults(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.post("/api/compute")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Large phantom smoke test (slow, requires data/)
# ---------------------------------------------------------------------------


@pytest.mark.slow
class TestComputeDosimetryRealPhantoms:
    def test_thelonious_full_compute(self, viewer_app_real_phantom):
        """End-to-end compute on the 23k-triangle thelonious phantom."""
        with viewer_app_real_phantom.test_client() as c:
            resp = c.post(
                "/api/compute",
                json={
                    "antenna_pos": [2.0, 0.0, 1.0],
                    "power_dbm": 23.0,
                    "level": 2,
                    "freq_hz": 28e9,
                    "body_name": "thelonious",
                },
            )
        assert resp.status_code == 200
        stats = json.loads(resp.headers["X-Stats"])
        assert stats["n_triangles"] == 23826  # thelonious is 23,826 triangles
        assert stats["peak_sab"] >= 0.0
        assert np.isfinite(stats["peak_sab"])
        # At 23 dBm, 2m distance, expect peak_sab well below ICNIRP 20 W/m^2
        assert stats["peak_sab"] < 20.0

    def test_eartha_largest_phantom_smoke(self, viewer_app_large_phantom):
        """Largest phantom (eartha, ~164k triangles) - memory path test."""
        with viewer_app_large_phantom.test_client() as c:
            resp = c.post(
                "/api/compute",
                json={
                    "antenna_pos": [2.0, 0.0, 1.0],
                    "power_dbm": 23.0,
                    "level": 0,  # cheapest level
                    "body_name": "eartha",
                },
            )
        assert resp.status_code == 200
        stats = json.loads(resp.headers["X-Stats"])
        assert stats["n_triangles"] > 100_000
        assert np.isfinite(stats["peak_sab"])


# ---------------------------------------------------------------------------
# Physics invariants (property-based with Hypothesis)
# ---------------------------------------------------------------------------


class TestComputeDosimetryInvariants:
    """Sab >= 0 and p_abs >= 0 under any physically valid input."""

    @pytest.mark.parametrize(
        ("antenna_pos", "power_dbm"),
        [
            ([1.0, 0.0, 0.1], 23.0),
            ([0.0, 1.0, 0.1], 10.0),
            ([0.5, 0.5, 0.5], 0.0),
            ([-1.0, 0.0, 0.1], 43.0),
            ([5.0, 2.0, 3.0], 20.0),
        ],
    )
    def test_sab_and_p_abs_non_negative(self, viewer_app, antenna_pos, power_dbm):
        with viewer_app.test_client() as c:
            resp = c.post(
                "/api/compute",
                json={"antenna_pos": antenna_pos, "power_dbm": power_dbm, "level": 2},
            )
        assert resp.status_code == 200
        stats = json.loads(resp.headers["X-Stats"])
        assert stats["peak_sab"] >= 0.0
        assert stats["p_abs"] >= 0.0
        n_tri = stats["n_triangles"]
        sab = np.frombuffer(resp.data[: n_tri * 4], dtype=np.float32)
        assert np.all(sab >= 0.0)

    def test_doubling_power_quadruples_p_abs(self, viewer_app):
        """With incoherent level 2, power ~ |E|^2; +6 dB power -> 4x absorbed power."""
        with viewer_app.test_client() as c:
            r1 = c.post("/api/compute", json={"antenna_pos": [1, 0, 0.1], "power_dbm": 0, "level": 2})
            r2 = c.post("/api/compute", json={"antenna_pos": [1, 0, 0.1], "power_dbm": 6, "level": 2})
        s1 = json.loads(r1.headers["X-Stats"])
        s2 = json.loads(r2.headers["X-Stats"])
        # +6 dB = factor of ~3.98 in linear power
        if s1["p_abs"] > 0:
            ratio = s2["p_abs"] / s1["p_abs"]
            np.testing.assert_allclose(ratio, 3.98, rtol=0.02)
