"""Tests for /api/optimize SSE endpoint."""

import json
import threading

import numpy as np
import pytest
from flask import Flask


@pytest.fixture()
def app():
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.secret_key = "test"
    cache = {}
    cache_lock = threading.RLock()

    from aegis.viewer.routes.optimize import register

    register(app, cache, cache_lock)
    return app


@pytest.fixture()
def client(app):
    return app.test_client()


class TestOptimizeEndpoint:
    def test_mimo_peak_streams_events(self, client):
        rng = np.random.default_rng(42)
        n_tri, n_ant = 50, 16
        G_tilde = (rng.standard_normal((n_tri, 3, n_ant)) + 1j * rng.standard_normal((n_tri, 3, n_ant))) * 0.01
        G_tilde[0, :, :] = 0.5 * np.ones((3, n_ant))
        x_init = np.conj(G_tilde[0, 0, :]) / np.linalg.norm(G_tilde[0, 0, :])

        resp = client.post(
            "/api/optimize",
            json={
                "mode": "mimo_peak",
                "G_tilde_real": G_tilde.real.tolist(),
                "G_tilde_imag": G_tilde.imag.tolist(),
                "x_init_real": x_init.real.tolist(),
                "x_init_imag": x_init.imag.tolist(),
                "p_max": 1.0,
                "max_iters": 5,
            },
        )
        assert resp.status_code == 200
        assert "text/event-stream" in resp.content_type

        events = []
        for line in resp.data.decode().split("\n"):
            if line.startswith("data: "):
                events.append(json.loads(line[6:]))

        assert len(events) >= 2
        # Check iteration events have expected fields
        iter_events = [e for e in events if "iter" in e and not e.get("done")]
        assert len(iter_events) >= 1
        assert "sab_b64" in iter_events[0]
        assert "objective" in iter_events[0]

    def test_missing_mode_returns_400(self, client):
        resp = client.post("/api/optimize", json={})
        assert resp.status_code == 400

    def test_unknown_mode_returns_400(self, client):
        resp = client.post("/api/optimize", json={"mode": "bogus"})
        assert resp.status_code == 400


class TestCancelEndpoint:
    def test_cancel_returns_json(self, client):
        resp = client.post("/api/optimize/cancel")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "cancelled" in data
