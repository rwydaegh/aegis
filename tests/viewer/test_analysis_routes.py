"""Tests for untested analysis route endpoints.

Covers: /api/compliance/limits, /api/compliance/summary, /api/tissue/spectrum.

The existing /api/compliance/power-sweep and /api/compliance/frequency-sweep
tests live in tests/test_viewer_analysis_routes.py.
"""

from __future__ import annotations

import pytest

pytest.importorskip("flask", reason="Flask not installed (viewer extra)")


# ---------------------------------------------------------------------------
# GET /api/compliance/limits
# ---------------------------------------------------------------------------


class TestComplianceLimits:
    def test_returns_limits_at_28ghz(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.get("/api/compliance/limits?freq_hz=28e9")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["freq_hz"] == 28e9
        assert data["scenario"] == "general_public"
        assert data["sab_4cm2"] > 0
        # sab_1cm2 is None below 30 GHz (ICNIRP threshold)
        assert data["sab_1cm2"] is None

    def test_occupational_scenario(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.get("/api/compliance/limits?freq_hz=28e9&scenario=occupational")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["scenario"] == "occupational"
        # Occupational limits are higher than general public
        resp_gp = c.get("/api/compliance/limits?freq_hz=28e9&scenario=general_public")
        data_gp = resp_gp.get_json()
        assert data["sab_4cm2"] >= data_gp["sab_4cm2"]

    def test_missing_freq_hz_returns_400(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.get("/api/compliance/limits")
        assert resp.status_code == 400
        assert "freq_hz" in resp.get_json()["error"]

    def test_negative_freq_hz_returns_400(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.get("/api/compliance/limits?freq_hz=-1")
        assert resp.status_code == 400
        assert "positive" in resp.get_json()["error"]

    def test_zero_freq_hz_returns_400(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.get("/api/compliance/limits?freq_hz=0")
        assert resp.status_code == 400

    def test_returns_all_limit_fields(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.get("/api/compliance/limits?freq_hz=28e9")
        data = resp.get_json()
        for field in ("sab_4cm2", "sab_1cm2", "sar_wb", "sinc_local", "sinc_whole_body"):
            assert field in data, f"Missing field: {field}"

    def test_low_frequency_returns_400_or_limits(self, viewer_app):
        """Frequencies below 6 GHz may be outside ICNIRP 2020 S_ab range."""
        with viewer_app.test_client() as c:
            resp = c.get("/api/compliance/limits?freq_hz=1e9")
        # Either valid limits or 400 (frequency range error)
        assert resp.status_code in (200, 400)


# ---------------------------------------------------------------------------
# GET /api/compliance/summary
# ---------------------------------------------------------------------------


class TestComplianceSummary:
    def test_summary_without_prior_compute(self, viewer_app):
        """Without a prior compute, summary returns a placeholder message."""
        with viewer_app.test_client() as c:
            resp = c.get("/api/compliance/summary")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "text" in data
        assert "Compliance" in data["text"]
        # Should mention that compliance was not evaluated
        assert "not evaluated" in data["text"].lower() or "outside" in data["text"].lower()

    def test_summary_with_cached_compliance(self, viewer_app):
        """Inject a compliance result into session-scoped cache, verify summary text."""
        from aegis.viewer.server import _cache, _cache_lock

        compliance = {
            "overall_pass": True,
            "margin_db": 5.3,
            "scenario": "general_public",
            "freq_hz": 28e9,
            "checks": [
                {
                    "label": "S_ab 4 cm2",
                    "value": 5.0,
                    "limit": 10.0,
                    "unit": "W/m2",
                    "pass": True,
                    "ratio": 0.5,
                },
            ],
        }

        with viewer_app.test_client() as c:
            with c.session_transaction() as sess:
                sess["session_id"] = "test-session"
            with _cache_lock:
                _cache["test-session:_last_compliance_result"] = compliance
            resp = c.get("/api/compliance/summary")
            assert resp.status_code == 200
            data = resp.get_json()
            assert "PASS" in data["text"]
            assert "28.0 GHz" in data["text"]
            assert "General Public" in data["text"]
            with _cache_lock:
                _cache.pop("test-session:_last_compliance_result", None)

    def test_summary_with_tx_power_param(self, viewer_app):
        from aegis.viewer.server import _cache, _cache_lock

        compliance = {
            "overall_pass": False,
            "margin_db": -2.0,
            "scenario": "occupational",
            "freq_hz": 28e9,
            "checks": [
                {
                    "label": "S_ab 4 cm2",
                    "value": 15.0,
                    "limit": 10.0,
                    "unit": "W/m2",
                    "pass": False,
                    "ratio": 1.5,
                },
            ],
        }

        with viewer_app.test_client() as c:
            with c.session_transaction() as sess:
                sess["session_id"] = "test-session"
            with _cache_lock:
                _cache["test-session:_last_compliance_result"] = compliance
            resp = c.get("/api/compliance/summary?tx_power_dbm=40")
            data = resp.get_json()
            assert "TX power: 40.0 dBm" in data["text"]
            assert "FAIL" in data["text"]
            with _cache_lock:
                _cache.pop("test-session:_last_compliance_result", None)

    def test_summary_fail_result(self, viewer_app):
        from aegis.viewer.server import _cache, _cache_lock

        compliance = {
            "overall_pass": False,
            "margin_db": -3.0,
            "scenario": "general_public",
            "freq_hz": 28e9,
            "checks": [
                {
                    "label": "S_ab 4 cm2",
                    "value": 25.0,
                    "limit": 10.0,
                    "unit": "W/m2",
                    "pass": False,
                    "ratio": 2.5,
                },
            ],
        }

        with viewer_app.test_client() as c:
            with c.session_transaction() as sess:
                sess["session_id"] = "test-session"
            with _cache_lock:
                _cache["test-session:_last_compliance_result"] = compliance
            resp = c.get("/api/compliance/summary")
            data = resp.get_json()
            assert "FAIL" in data["text"]
            assert "Overall: FAIL" in data["text"]
            with _cache_lock:
                _cache.pop("test-session:_last_compliance_result", None)


# ---------------------------------------------------------------------------
# GET /api/tissue/spectrum
# ---------------------------------------------------------------------------


class TestTissueSpectrum:
    def test_default_params(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.get("/api/tissue/spectrum")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["tissue"] == "Skin"
        assert data["skin_model"] == "itis"
        assert len(data["freqs_hz"]) == 100
        assert len(data["eps_r"]) == 100
        assert len(data["sigma"]) == 100
        assert len(data["T0"]) == 100

    def test_custom_tissue(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.get("/api/tissue/spectrum?tissue=Muscle")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["tissue"] == "Muscle"

    def test_custom_frequency_range(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.get("/api/tissue/spectrum?f_min=10e9&f_max=50e9&n=50")
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data["freqs_hz"]) == 50
        assert data["freqs_hz"][0] == pytest.approx(10e9)
        assert data["freqs_hz"][-1] == pytest.approx(50e9)

    def test_n_clamped_to_range(self, viewer_app):
        with viewer_app.test_client() as c:
            # n below 10 gets clamped to 10
            resp = c.get("/api/tissue/spectrum?n=3")
        assert resp.status_code == 200
        assert len(resp.get_json()["freqs_hz"]) == 10

    def test_n_clamped_max(self, viewer_app):
        with viewer_app.test_client() as c:
            # n above 1000 gets clamped to 1000
            resp = c.get("/api/tissue/spectrum?n=5000")
        assert resp.status_code == 200
        assert len(resp.get_json()["freqs_hz"]) == 1000

    def test_negative_f_min_returns_400(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.get("/api/tissue/spectrum?f_min=-1")
        assert resp.status_code == 400
        assert "positive" in resp.get_json()["error"]

    def test_f_min_gte_f_max_returns_400(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.get("/api/tissue/spectrum?f_min=100e9&f_max=10e9")
        assert resp.status_code == 400
        assert "less than" in resp.get_json()["error"]

    def test_christ2021_skin_model(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.get("/api/tissue/spectrum?skin_model=christ2021")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["skin_model"] == "christ2021"
        # Should still return valid arrays
        assert all(v > 0 for v in data["eps_r"])

    def test_eps_r_and_sigma_are_positive(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.get("/api/tissue/spectrum")
        data = resp.get_json()
        assert all(v > 0 for v in data["eps_r"])
        assert all(v > 0 for v in data["sigma"])

    def test_T0_in_valid_range(self, viewer_app):
        """Fresnel transmission coefficient T0 should be between 0 and 1."""
        with viewer_app.test_client() as c:
            resp = c.get("/api/tissue/spectrum")
        data = resp.get_json()
        for t0 in data["T0"]:
            assert 0 < t0 <= 1.0

    def test_unknown_tissue_returns_400(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.get("/api/tissue/spectrum?tissue=Unobtainium")
        assert resp.status_code == 400

    def test_christ2025_skin_model(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.get("/api/tissue/spectrum?skin_model=christ2025")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["skin_model"] == "christ2025"
        assert all(v > 0 for v in data["eps_r"])
        assert all(v > 0 for v in data["sigma"])

    def test_nict_skin_model(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.get("/api/tissue/spectrum?skin_model=nict")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["skin_model"] == "nict"
        assert len(data["freqs_hz"]) == 100
        assert all(v > 0 for v in data["eps_r"])

    def test_unknown_skin_model_falls_back(self, viewer_app):
        """Unknown skin model for Skin tissue falls through to default branch."""
        with viewer_app.test_client() as c:
            resp = c.get("/api/tissue/spectrum?skin_model=unknown_model")
        # Route should still return 200 (falls through to the else branch which
        # keeps original itis values)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["skin_model"] == "unknown_model"

    def test_non_skin_tissue_ignores_skin_model(self, viewer_app):
        """skin_model parameter should only affect Skin tissue."""
        with viewer_app.test_client() as c:
            resp = c.get("/api/tissue/spectrum?tissue=Muscle&skin_model=christ2025")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["tissue"] == "Muscle"
        # Even with christ2025, non-Skin tissue should return valid data
        assert all(v > 0 for v in data["eps_r"])

    def test_equal_f_min_f_max_returns_400(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.get("/api/tissue/spectrum?f_min=28e9&f_max=28e9")
        assert resp.status_code == 400

    def test_zero_f_max_returns_400(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.get("/api/tissue/spectrum?f_max=0")
        assert resp.status_code == 400

    @pytest.mark.parametrize(
        "query",
        [
            "f_min=NaN&f_max=1e10",
            "f_min=1e9&f_max=NaN",
            "f_min=NaN&f_max=NaN",
            "f_min=1e9&f_max=Infinity",
            "f_min=-Infinity&f_max=1e10",
            "f_min=Infinity&f_max=Infinity",
        ],
    )
    def test_non_finite_freqs_return_400(self, viewer_app, query):
        """NaN/Inf in f_min or f_max must be rejected, not silently produce NaN payload."""
        with viewer_app.test_client() as c:
            resp = c.get(f"/api/tissue/spectrum?{query}&n=10")
        assert resp.status_code == 400
        assert "finite" in resp.get_json()["error"]


# ---------------------------------------------------------------------------
# GET /api/compliance/limits - extended
# ---------------------------------------------------------------------------


class TestComplianceLimitsExtended:
    def test_limits_at_60ghz(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.get("/api/compliance/limits?freq_hz=60e9")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["freq_hz"] == 60e9
        assert data["sab_4cm2"] > 0

    def test_limits_vary_with_frequency(self, viewer_app):
        """Limits at different frequencies should potentially differ."""
        with viewer_app.test_client() as c:
            resp_28 = c.get("/api/compliance/limits?freq_hz=28e9")
            resp_60 = c.get("/api/compliance/limits?freq_hz=60e9")
        # Both should succeed
        assert resp_28.status_code == 200
        assert resp_60.status_code == 200
        # sinc_local may differ at different frequencies
        d28 = resp_28.get_json()
        d60 = resp_60.get_json()
        assert d28["freq_hz"] != d60["freq_hz"]

    def test_non_numeric_freq_hz_ignored(self, viewer_app):
        """Flask type=float returns None for non-numeric strings, triggering 400."""
        with viewer_app.test_client() as c:
            resp = c.get("/api/compliance/limits?freq_hz=abc")
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# GET /api/compliance/summary - extended
# ---------------------------------------------------------------------------


class TestComplianceSummaryExtended:
    def test_summary_with_multiple_checks(self, viewer_app):
        """Summary with multiple compliance checks renders all of them."""
        from aegis.viewer.server import _cache, _cache_lock

        compliance = {
            "overall_pass": True,
            "margin_db": 3.0,
            "scenario": "general_public",
            "freq_hz": 28e9,
            "checks": [
                {
                    "label": "S_ab 4 cm2",
                    "value": 5.0,
                    "limit": 10.0,
                    "unit": "W/m2",
                    "pass": True,
                    "ratio": 0.5,
                },
                {
                    "label": "S_ab 1 cm2",
                    "value": 8.0,
                    "limit": 20.0,
                    "unit": "W/m2",
                    "pass": True,
                    "ratio": 0.4,
                },
            ],
        }

        with viewer_app.test_client() as c:
            with c.session_transaction() as sess:
                sess["session_id"] = "test-session"
            with _cache_lock:
                _cache["test-session:_last_compliance_result"] = compliance
            resp = c.get("/api/compliance/summary")
            data = resp.get_json()
            assert "S_ab 4 cm2" in data["text"]
            assert "S_ab 1 cm2" in data["text"]
            assert "PASS" in data["text"]
            assert "Margin: +3.0 dB" in data["text"]
            with _cache_lock:
                _cache.pop("test-session:_last_compliance_result", None)

    def test_summary_no_margin(self, viewer_app):
        """Summary when margin_db is None."""
        from aegis.viewer.server import _cache, _cache_lock

        compliance = {
            "overall_pass": True,
            "margin_db": None,
            "scenario": "general_public",
            "freq_hz": 28e9,
            "checks": [],
        }

        with viewer_app.test_client() as c:
            with c.session_transaction() as sess:
                sess["session_id"] = "test-session"
            with _cache_lock:
                _cache["test-session:_last_compliance_result"] = compliance
            resp = c.get("/api/compliance/summary")
            data = resp.get_json()
            assert "Margin:" not in data["text"]
            with _cache_lock:
                _cache.pop("test-session:_last_compliance_result", None)

    def test_summary_overall_pass_none_shows_na(self, viewer_app):
        """Regression: overall_pass=None (no applicable checks) must show N/A, not FAIL."""
        from aegis.viewer.server import _cache, _cache_lock

        compliance = {
            "overall_pass": None,
            "margin_db": None,
            "scenario": "general_public",
            "freq_hz": 3.5e9,
            "checks": [],
        }

        with viewer_app.test_client() as c:
            with c.session_transaction() as sess:
                sess["session_id"] = "test-session"
            with _cache_lock:
                _cache["test-session:_last_compliance_result"] = compliance
            resp = c.get("/api/compliance/summary")
            data = resp.get_json()
            assert "N/A" in data["text"]
            assert "FAIL" not in data["text"]
            with _cache_lock:
                _cache.pop("test-session:_last_compliance_result", None)


# ---------------------------------------------------------------------------
# GET /api/compliance/power-sweep (from analysis routes)
# ---------------------------------------------------------------------------


class TestPowerSweepInViewer:
    """Power sweep tests using the full viewer app fixture."""

    def test_basic_power_sweep(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.get("/api/compliance/power-sweep?sab_4cm2=10&freq_hz=28e9&ref_power_dbm=23")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "power_dbm" in data
        assert "margin_db" in data
        assert "compliant" in data
        assert "p_max_compliant_dbm" in data
        assert len(data["power_dbm"]) == len(data["margin_db"])
        assert len(data["power_dbm"]) == len(data["compliant"])

    def test_missing_required_params(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.get("/api/compliance/power-sweep")
        assert resp.status_code == 400
        assert "required" in resp.get_json()["error"]

    def test_negative_freq_hz(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.get("/api/compliance/power-sweep?sab_4cm2=10&freq_hz=-1&ref_power_dbm=23")
        assert resp.status_code == 400
        assert "positive" in resp.get_json()["error"]

    def test_occupational_scenario(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.get("/api/compliance/power-sweep?sab_4cm2=10&freq_hz=28e9&ref_power_dbm=23&scenario=occupational")
        assert resp.status_code == 200

    def test_custom_n_points_clamped(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.get("/api/compliance/power-sweep?sab_4cm2=10&freq_hz=28e9&ref_power_dbm=23&n_points=5")
        assert resp.status_code == 200
        data = resp.get_json()
        # n_points clamped to minimum 10
        assert len(data["power_dbm"]) >= 10

    def test_compliant_at_low_power(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.get("/api/compliance/power-sweep?sab_4cm2=0.001&freq_hz=28e9&ref_power_dbm=0")
        data = resp.get_json()
        # Very low sab at 0 dBm should be compliant
        assert data["compliant"][0] is True

    def test_with_optional_quantities(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.get(
                "/api/compliance/power-sweep"
                "?sab_4cm2=10&freq_hz=28e9&ref_power_dbm=23"
                "&sab_1cm2=15&sinc_local=20&sar_wb=0.01"
            )
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# GET /api/compliance/frequency-sweep (from analysis routes)
# ---------------------------------------------------------------------------


class TestFrequencySweepInViewer:
    """Frequency sweep tests using the full viewer app fixture."""

    def test_basic_frequency_sweep(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.get("/api/compliance/frequency-sweep?sab_4cm2=10")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "freq_ghz" in data
        assert "margin_db" in data
        assert "compliant" in data
        assert len(data["freq_ghz"]) == len(data["margin_db"])

    def test_missing_sab_4cm2(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.get("/api/compliance/frequency-sweep")
        assert resp.status_code == 400
        assert "required" in resp.get_json()["error"]

    def test_occupational_scenario(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.get("/api/compliance/frequency-sweep?sab_4cm2=10&scenario=occupational")
        assert resp.status_code == 200

    def test_with_optional_quantities(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.get("/api/compliance/frequency-sweep?sab_4cm2=10&sinc_local=5&sinc_wb=2&sab_1cm2=15&sar_wb=0.01")
        assert resp.status_code == 200

    def test_custom_n_points(self, viewer_app):
        with viewer_app.test_client() as c:
            resp = c.get("/api/compliance/frequency-sweep?sab_4cm2=10&n_points=20")
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data["freq_ghz"]) == 20
