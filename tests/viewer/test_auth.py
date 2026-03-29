"""Tests for the session-based password gate."""

from __future__ import annotations

import os
import struct

import pytest

pytest.importorskip("flask", reason="Flask not installed (viewer extra)")


def _make_minimal_stl_bytes(name: str = "test") -> bytes:
    """Return a minimal valid binary STL with one triangle."""
    header = name.encode("ascii")[:80].ljust(80, b"\x00")
    n_triangles = 1
    triangle = struct.pack(
        "<fff fff fff fff H",
        0.0,
        0.0,
        1.0,  # normal
        0.0,
        0.0,
        0.0,  # v0
        1.0,
        0.0,
        0.0,  # v1
        0.0,
        1.0,
        0.0,  # v2
        0,  # attr byte count
    )
    return header + struct.pack("<I", n_triangles) + triangle


@pytest.fixture
def client(tmp_path):
    """Flask test client with AEGIS_GATE_PASSWORD set."""
    (tmp_path / "test.stl").write_bytes(_make_minimal_stl_bytes("test"))

    os.environ["AEGIS_GATE_PASSWORD"] = "test-password-123"
    os.environ["FLASK_SECRET_KEY"] = "test-secret-key"

    from aegis.viewer.server import _cache, create_app

    _cache.clear()
    app = create_app(data_dir=str(tmp_path), body_name="test")
    app.config["TESTING"] = True

    with app.test_client() as c:
        yield c

    os.environ.pop("AEGIS_GATE_PASSWORD", None)
    os.environ.pop("FLASK_SECRET_KEY", None)


def test_api_returns_401_without_auth(client):
    resp = client.get("/api/config")
    assert resp.status_code == 401


def test_auth_endpoint_accepts_correct_password(client):
    resp = client.post("/api/auth", json={"password": "test-password-123"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert "expires_at" in data


def test_auth_endpoint_rejects_wrong_password(client):
    resp = client.post("/api/auth", json={"password": "wrong"})
    assert resp.status_code == 401


def test_authenticated_request_succeeds(client):
    client.post("/api/auth", json={"password": "test-password-123"})
    resp = client.get("/api/config")
    assert resp.status_code == 200


def test_health_exempt_from_auth(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200


def test_auth_exempt_from_auth(client):
    resp = client.post("/api/auth", json={"password": "wrong"})
    assert resp.status_code == 401  # wrong password, not redirect
