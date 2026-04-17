"""Tests for compliance analysis API routes."""

import json
import threading
from unittest.mock import patch

import pytest

pytest.importorskip("flask")
from flask import Flask  # noqa: E402


@pytest.fixture
def app():
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.secret_key = "test-secret-key"
    cache = {}
    cache_lock = threading.Lock()
    from aegis.viewer.routes.analysis import register

    register(app, cache, cache_lock)
    return app


@pytest.fixture
def client(app):
    return app.test_client()


class TestPowerSweep:
    def test_returns_arrays(self, client):
        resp = client.get(
            "/api/compliance/power-sweep?sab_4cm2=10&freq_hz=28e9&ref_power_dbm=23&scenario=general_public"
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert "power_dbm" in data
        assert "margin_db" in data
        assert "p_max_compliant_dbm" in data
        assert len(data["power_dbm"]) == len(data["margin_db"])

    def test_missing_params(self, client):
        resp = client.get("/api/compliance/power-sweep")
        assert resp.status_code == 400

    def test_compliant_at_low_power(self, client):
        resp = client.get("/api/compliance/power-sweep?sab_4cm2=1&freq_hz=28e9&ref_power_dbm=0")
        data = resp.get_json()
        assert data["compliant"][0] is True


class TestFrequencySweep:
    def test_returns_arrays(self, client):
        resp = client.get("/api/compliance/frequency-sweep?sab_4cm2=10&sinc_local=5&scenario=general_public")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "freq_ghz" in data
        assert "margin_db" in data
        assert len(data["freq_ghz"]) == len(data["margin_db"])

    def test_missing_params(self, client):
        resp = client.get("/api/compliance/frequency-sweep")
        assert resp.status_code == 400


class TestJsonSafeOutput:
    """Regression: compliance routes must produce valid JSON (no Infinity/NaN)."""

    def test_power_sweep_no_infinity(self, client):
        """Power sweep with zero sab should return null, not Infinity."""
        resp = client.get("/api/compliance/power-sweep?sab_4cm2=0&freq_hz=28e9&ref_power_dbm=23")
        assert resp.status_code == 200
        raw = resp.get_data(as_text=True)
        assert "Infinity" not in raw
        assert "NaN" not in raw
        # Verify it parses as standard JSON
        json.loads(raw)

    def test_frequency_sweep_no_infinity(self, client):
        """Frequency sweep with only sar_wb produces inf margin at all freqs."""
        resp = client.get("/api/compliance/frequency-sweep?sar_wb=0.01")
        assert resp.status_code == 200
        raw = resp.get_data(as_text=True)
        assert "Infinity" not in raw
        assert "NaN" not in raw
        json.loads(raw)


class TestSpatialComplianceInputValidation:
    """Reject nonsensical inputs before spending compute on them."""

    class _FakeBaseStation:
        def __init__(self, lat, lon):
            self.latitude = lat
            self.longitude = lon
            self.eirp_dbm = 53.0
            self.freq_hz = 26e9
            self.height_m = 25.0

    def _post_with_basestations(self, client, body):
        """POST to /api/compliance/spatial with a preloaded base station."""
        station = self._FakeBaseStation(51.05, 3.72)
        with patch("aegis.viewer.server.scoped_cache_get", return_value=[station]):
            return client.post("/api/compliance/spatial", json=body)

    def test_rejects_inverted_bbox(self, client):
        resp = self._post_with_basestations(client, {"bbox": [20.0, 10.0, 55.0, 50.0]})
        assert resp.status_code == 400
        assert "bbox" in resp.get_json()["error"].lower()

    def test_rejects_zero_area_bbox(self, client):
        resp = self._post_with_basestations(client, {"bbox": [10.0, 10.0, 50.0, 55.0]})
        assert resp.status_code == 400

    def test_rejects_negative_receiver_height(self, client):
        resp = self._post_with_basestations(
            client,
            {"bbox": [3.6, 3.8, 51.0, 51.1], "receiver_height_m": -1.0},
        )
        assert resp.status_code == 400
        assert "receiver_height" in resp.get_json()["error"].lower()

    def test_rejects_implausibly_large_receiver_height(self, client):
        resp = self._post_with_basestations(
            client,
            {"bbox": [3.6, 3.8, 51.0, 51.1], "receiver_height_m": 10000.0},
        )
        assert resp.status_code == 400
