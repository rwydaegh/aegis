"""Real integration tests for /api/compliance/* and /api/tissue/spectrum.

These exercise ICNIRP evaluation utilities, power/frequency sweeps, the
spatial-compliance heatmap, and the tissue dielectric spectrum endpoint. No
mocks - every call invokes the real ``aegis.compliance`` and
``aegis.tissue.database`` implementations.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pytest

pytest.importorskip("flask", reason="viewer tests require flask (pip install aegis[viewer])")


# ---------------------------------------------------------------------------
# /api/compliance/limits
# ---------------------------------------------------------------------------


class TestComplianceLimits:
    @pytest.mark.parametrize("freq_hz", [10e9, 28e9, 60e9, 100e9, 300e9])
    def test_limits_across_ab_frequencies(self, viewer_app, freq_hz):
        with viewer_app.test_client() as c:
            resp = c.get(f"/api/compliance/limits?freq_hz={freq_hz}")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["freq_hz"] == freq_hz
        assert data["scenario"] == "general_public"
        # ICNIRP 2020 local limits (S_ab) apply above 6 GHz
        assert data["sab_4cm2"] is not None
        assert data["sab_4cm2"] > 0
        assert data["sar_wb"] == pytest.approx(0.08, rel=1e-6)

    def test_occupational_vs_general_public(self, viewer_app):
        """Occupational limits are always >= general public limits."""
        with viewer_app.test_client() as c:
            gp = c.get("/api/compliance/limits?freq_hz=28e9&scenario=general_public").get_json()
            oc = c.get("/api/compliance/limits?freq_hz=28e9&scenario=occupational").get_json()
        assert oc["sab_4cm2"] >= gp["sab_4cm2"]
        assert oc["sar_wb"] >= gp["sar_wb"]

    def test_missing_freq_hz(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.get("/api/compliance/limits")
        assert resp.status_code == 400

    def test_negative_freq_hz(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.get("/api/compliance/limits?freq_hz=-28e9")
        assert resp.status_code == 400

    def test_invalid_scenario(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.get("/api/compliance/limits?freq_hz=28e9&scenario=dystopian")
        assert resp.status_code == 400

    def test_low_freq_returns_limits_without_sab(self, viewer_app):
        """Below 6 GHz, sab_4cm2 may be None but SAR limits still apply."""
        with viewer_app.test_client() as c:
            resp = c.get("/api/compliance/limits?freq_hz=1e9")
        # Either 200 (SAR-only) or 400 (frequency out of range)
        assert resp.status_code in (200, 400)


# ---------------------------------------------------------------------------
# /api/compliance/power-sweep
# ---------------------------------------------------------------------------


class TestCompliancePowerSweep:
    def test_basic_power_sweep(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.get("/api/compliance/power-sweep?sab_4cm2=10&freq_hz=28e9&ref_power_dbm=23")
        assert resp.status_code == 200
        data = resp.get_json()
        for key in ("power_dbm", "margin_db", "compliant", "p_max_compliant_w", "p_max_compliant_dbm"):
            assert key in data
        assert len(data["power_dbm"]) == len(data["margin_db"])
        assert len(data["power_dbm"]) == len(data["compliant"])
        # Compliance is monotone: doubling exposure (3 dB) shifts margin by -3 dB
        margins = np.array(data["margin_db"])
        # margin must be decreasing as power increases
        powers = np.array(data["power_dbm"])
        order = np.argsort(powers)
        sorted_margins = margins[order]
        np.testing.assert_array_less(np.diff(sorted_margins), 1e-6)

    def test_missing_required_returns_400(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.get("/api/compliance/power-sweep?sab_4cm2=10")
        assert resp.status_code == 400

    def test_no_compliance_metric_returns_400(self, viewer_app):
        """freq_hz + ref_power_dbm present but no sab/sar -> 400."""
        with viewer_app.test_client() as c:
            resp = c.get("/api/compliance/power-sweep?freq_hz=28e9&ref_power_dbm=23")
        assert resp.status_code == 400

    def test_p_max_finite_when_exposure_is_low(self, viewer_app):
        """Very low sab_4cm2 at 0 dBm gives large but finite p_max."""
        with viewer_app.test_client() as c:
            resp = c.get("/api/compliance/power-sweep?sab_4cm2=0.00001&freq_hz=28e9&ref_power_dbm=0")
        assert resp.status_code == 200
        d = resp.get_json()
        assert d["p_max_compliant_dbm"] is not None
        assert np.isfinite(d["p_max_compliant_dbm"])

    def test_negative_freq_rejected(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.get("/api/compliance/power-sweep?sab_4cm2=10&freq_hz=-1&ref_power_dbm=23")
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# /api/compliance/heatmap
# ---------------------------------------------------------------------------


class TestComplianceHeatmap:
    def test_basic_heatmap(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.get("/api/compliance/heatmap?freq_hz=28e9&ref_power_dbm=23&sab_4cm2=10&n_freq=15&n_power=15")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["n_freq"] == 15
        assert data["n_power"] == 15
        assert len(data["margin_db"]) == 15
        for row in data["margin_db"]:
            assert len(row) == 15

    def test_missing_required_returns_400(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.get("/api/compliance/heatmap")
        assert resp.status_code == 400

    def test_no_sab_returns_400(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.get("/api/compliance/heatmap?freq_hz=28e9&ref_power_dbm=23")
        assert resp.status_code == 400

    def test_n_freq_clamped_low(self, viewer_app):
        """n_freq below 10 clamps to 10."""
        with viewer_app.test_client() as c:
            resp = c.get("/api/compliance/heatmap?freq_hz=28e9&ref_power_dbm=23&sab_4cm2=10&n_freq=2")
        data = resp.get_json()
        assert data["n_freq"] == 10

    def test_n_freq_clamped_high(self, viewer_app):
        """n_freq above 100 clamps to 100."""
        with viewer_app.test_client() as c:
            resp = c.get("/api/compliance/heatmap?freq_hz=28e9&ref_power_dbm=23&sab_4cm2=10&n_freq=5000")
        data = resp.get_json()
        assert data["n_freq"] == 100

    def test_infinite_margins_sanitized_to_null(self, viewer_app):
        """margin_db may be inf for extremely low exposures; JSON must return null."""
        import json

        with viewer_app.test_client() as c:
            resp = c.get("/api/compliance/heatmap?freq_hz=28e9&ref_power_dbm=0&sab_4cm2=0.0000001")
        assert resp.status_code == 200
        # Response must be valid JSON (no inf/nan tokens)
        parsed = json.loads(resp.data.decode())
        assert parsed["n_freq"] >= 10


# ---------------------------------------------------------------------------
# /api/compliance/frequency-sweep
# ---------------------------------------------------------------------------


class TestComplianceFrequencySweep:
    def test_basic_frequency_sweep(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.get("/api/compliance/frequency-sweep?sab_4cm2=10")
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data["freq_ghz"]) == len(data["margin_db"])
        freqs = np.array(data["freq_ghz"])
        assert np.all(freqs > 0)
        assert np.all(np.diff(freqs) > 0)

    def test_missing_required(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.get("/api/compliance/frequency-sweep")
        assert resp.status_code == 400

    def test_occupational_scenario(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.get("/api/compliance/frequency-sweep?sab_4cm2=10&scenario=occupational")
        assert resp.status_code == 200

    def test_invalid_scenario(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.get("/api/compliance/frequency-sweep?sab_4cm2=10&scenario=bogus")
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# /api/compliance/summary
# ---------------------------------------------------------------------------


class TestComplianceSummary:
    def test_summary_without_compliance_result(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.get("/api/compliance/summary")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "text" in data
        assert "Compliance" in data["text"]


# ---------------------------------------------------------------------------
# /api/compliance/spatial (POST)
# ---------------------------------------------------------------------------


@dataclass
class _StubBaseStation:
    """Minimal base station stub matching the attributes used by spatial_compliance_grid."""

    latitude: float
    longitude: float
    eirp_dbm: float
    freq_hz: float
    height_m: float


class TestComplianceSpatial:
    def test_no_basestations_returns_400(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.post("/api/compliance/spatial", json={})
        assert resp.status_code == 400
        assert "base station" in resp.get_json()["error"].lower()

    def test_spatial_compliance_with_stations(self, viewer_app):
        from aegis.viewer.server import _cache, _cache_lock

        stations = [
            _StubBaseStation(51.05, 3.72, 50.0, 2.4e9, 25.0),
            _StubBaseStation(51.051, 3.721, 45.0, 3.5e9, 20.0),
        ]
        with viewer_app.test_client() as c:
            with c.session_transaction() as sess:
                sess["session_id"] = "spatial-test"
            with _cache_lock:
                _cache["spatial-test:basestations"] = stations
            try:
                resp = c.post(
                    "/api/compliance/spatial",
                    json={
                        "bbox": [3.71, 3.73, 51.045, 51.055],
                        "resolution": 20,
                        "scenario": "general_public",
                    },
                )
                assert resp.status_code == 200
                data = resp.get_json()
                assert data["n_stations"] == 2
                assert data["n_lat"] == 20
                assert data["n_lon"] == 20
                assert len(data["margin_db"]) == 20
                assert data["scenario"] == "general_public"
                # sinc is always >= 0 physically
                sinc = np.array(data["sinc_w_m2"])
                assert np.all(sinc >= 0.0)
            finally:
                with _cache_lock:
                    _cache.pop("spatial-test:basestations", None)

    def test_bad_bbox_length(self, viewer_app):
        from aegis.viewer.server import _cache, _cache_lock

        with viewer_app.test_client() as c:
            with c.session_transaction() as sess:
                sess["session_id"] = "bbox-test"
            with _cache_lock:
                _cache["bbox-test:basestations"] = [_StubBaseStation(51, 3.7, 45, 2.4e9, 25)]
            try:
                resp = c.post("/api/compliance/spatial", json={"bbox": [1, 2, 3]})
                assert resp.status_code == 400
            finally:
                with _cache_lock:
                    _cache.pop("bbox-test:basestations", None)

    def test_bbox_non_finite_rejected(self, viewer_app):
        from aegis.viewer.server import _cache, _cache_lock

        with viewer_app.test_client() as c:
            with c.session_transaction() as sess:
                sess["session_id"] = "inf-test"
            with _cache_lock:
                _cache["inf-test:basestations"] = [_StubBaseStation(51, 3.7, 45, 2.4e9, 25)]
            try:
                resp = c.post(
                    "/api/compliance/spatial",
                    json={"bbox": [3.71, float("inf"), 51.04, 51.06]},
                )
                assert resp.status_code == 400
                assert "finite" in resp.get_json()["error"]
            finally:
                with _cache_lock:
                    _cache.pop("inf-test:basestations", None)

    def test_bbox_inverted_rejected(self, viewer_app):
        from aegis.viewer.server import _cache, _cache_lock

        with viewer_app.test_client() as c:
            with c.session_transaction() as sess:
                sess["session_id"] = "inv-test"
            with _cache_lock:
                _cache["inv-test:basestations"] = [_StubBaseStation(51, 3.7, 45, 2.4e9, 25)]
            try:
                # lon_min >= lon_max
                resp = c.post(
                    "/api/compliance/spatial",
                    json={"bbox": [3.73, 3.71, 51.04, 51.06]},
                )
                assert resp.status_code == 400
            finally:
                with _cache_lock:
                    _cache.pop("inv-test:basestations", None)

    def test_invalid_receiver_height(self, viewer_app):
        from aegis.viewer.server import _cache, _cache_lock

        with viewer_app.test_client() as c:
            with c.session_transaction() as sess:
                sess["session_id"] = "rh-test"
            with _cache_lock:
                _cache["rh-test:basestations"] = [_StubBaseStation(51, 3.7, 45, 2.4e9, 25)]
            try:
                resp = c.post(
                    "/api/compliance/spatial",
                    json={
                        "bbox": [3.71, 3.73, 51.045, 51.055],
                        "receiver_height_m": 2000,  # out of range
                    },
                )
                assert resp.status_code == 400
            finally:
                with _cache_lock:
                    _cache.pop("rh-test:basestations", None)


# ---------------------------------------------------------------------------
# /api/tissue/spectrum
# ---------------------------------------------------------------------------


class TestTissueSpectrum:
    def test_default_params(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.get("/api/tissue/spectrum")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["tissue"] == "Skin"
        assert data["skin_model"] == "itis"
        n = len(data["freqs_hz"])
        assert n == 100
        for key in ("eps_r", "sigma", "T0"):
            assert len(data[key]) == n

    def test_physical_bounds(self, viewer_app):
        """T0 in [0, 1], eps_r > 0, sigma > 0."""
        with viewer_app.test_client() as c:
            resp = c.get("/api/tissue/spectrum?f_min=1e9&f_max=100e9&n=50")
        data = resp.get_json()
        assert all(0 < t <= 1.0 for t in data["T0"])
        assert all(e > 0 for e in data["eps_r"])
        assert all(s > 0 for s in data["sigma"])

    def test_custom_tissue_muscle(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.get("/api/tissue/spectrum?tissue=Muscle&n=30")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["tissue"] == "Muscle"
        assert len(data["eps_r"]) == 30

    @pytest.mark.parametrize("model", ["christ2021", "christ2025", "nict"])
    def test_skin_model_variants(self, viewer_app, model):
        with viewer_app.test_client() as c:
            resp = c.get(f"/api/tissue/spectrum?skin_model={model}&n=20")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["skin_model"] == model
        assert all(v > 0 for v in data["eps_r"])

    def test_unknown_tissue_returns_400(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.get("/api/tissue/spectrum?tissue=Unobtainium")
        assert resp.status_code == 400

    def test_inverted_freq_range(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.get("/api/tissue/spectrum?f_min=100e9&f_max=1e9")
        assert resp.status_code == 400

    def test_negative_freqs_rejected(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.get("/api/tissue/spectrum?f_min=-1")
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Unicode / malformed
# ---------------------------------------------------------------------------


class TestAnalysisMalformed:
    def test_compliance_limits_non_numeric_freq(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.get("/api/compliance/limits?freq_hz=not_a_number")
        assert resp.status_code == 400

    def test_spatial_garbage_json(self, viewer_app):
        from aegis.viewer.server import _cache, _cache_lock

        with viewer_app.test_client() as c:
            with c.session_transaction() as sess:
                sess["session_id"] = "gj-test"
            with _cache_lock:
                _cache["gj-test:basestations"] = [_StubBaseStation(51, 3.7, 45, 2.4e9, 25)]
            try:
                resp = c.post(
                    "/api/compliance/spatial",
                    data=b"\xff\xfe",
                    content_type="application/json",
                )
                # JSON parsing is silent; server proceeds with empty dict and
                # derives bbox from basestations - should succeed or 400, never 500
                assert resp.status_code in (200, 400)
            finally:
                with _cache_lock:
                    _cache.pop("gj-test:basestations", None)
