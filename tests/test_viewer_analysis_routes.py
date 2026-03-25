"""Tests for compliance analysis API routes."""

import threading

import pytest
from flask import Flask


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


class TestLinkBudget:
    def test_basic(self, client):
        resp = client.get("/api/compliance/link-budget?tx_power_dbm=23&antenna_gain_dbi=15&distance_m=5&freq_hz=28e9")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "sinc" in data
        assert "sab_estimate" in data
        assert "compliant" in data
        assert "margin_db" in data
        assert "max_tx_power_dbm" in data

    def test_missing_params(self, client):
        resp = client.get("/api/compliance/link-budget?tx_power_dbm=23")
        assert resp.status_code == 400

    def test_inverse_square(self, client):
        resp1 = client.get("/api/compliance/link-budget?tx_power_dbm=23&antenna_gain_dbi=0&distance_m=1&freq_hz=28e9")
        resp2 = client.get("/api/compliance/link-budget?tx_power_dbm=23&antenna_gain_dbi=0&distance_m=2&freq_hz=28e9")
        d1 = resp1.get_json()
        d2 = resp2.get_json()
        ratio = d1["sinc"] / d2["sinc"]
        assert abs(ratio - 4.0) < 0.01
