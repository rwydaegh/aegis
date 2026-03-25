"""Tests for compliance analysis API routes."""

import threading

import pytest

pytest.importorskip("flask")
from flask import Flask  # noqa: E402


@pytest.fixture
def app():
    app = Flask(__name__)
    app.config["TESTING"] = True
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


