"""Tests for viewer HTTP Basic Auth."""

import base64
import os
from pathlib import Path

import pytest

pytest.importorskip("flask")


@pytest.fixture(autouse=True)
def _clean_auth_env():
    """Ensure AEGIS_VIEWER_AUTH is cleaned up after each test."""
    yield
    os.environ.pop("AEGIS_VIEWER_AUTH", None)


def _make_app(auth_env: str | None = None):
    """Create a minimal Flask test app with auth configured.

    Uses the e2e_lab fixture data dir so body loading succeeds.
    """
    if auth_env:
        os.environ["AEGIS_VIEWER_AUTH"] = auth_env
    else:
        os.environ.pop("AEGIS_VIEWER_AUTH", None)

    from aegis.viewer.server import create_app

    # Use the test fixture directory which has a small STL
    data_dir = str(Path(__file__).parent / "fixtures" / "e2e_lab")
    app = create_app(
        data_dir=data_dir,
        body_name="e2e_icosahedron",
        config={"server": {"host": "127.0.0.1", "port": 5099}},
    )
    app.config["TESTING"] = True
    return app


def test_no_auth_when_unset():
    """Without AEGIS_VIEWER_AUTH, all routes are open."""
    app = _make_app(auth_env=None)
    with app.test_client() as c:
        resp = c.get("/api/health")
        assert resp.status_code == 200


def test_auth_rejects_without_credentials():
    """With AEGIS_VIEWER_AUTH set, requests without credentials get 401."""
    app = _make_app(auth_env="aegis:testpass123")
    with app.test_client() as c:
        resp = c.get("/api/health")
        assert resp.status_code == 401


def test_auth_accepts_correct_credentials():
    """Correct Basic Auth credentials pass through."""
    app = _make_app(auth_env="aegis:testpass123")
    creds = base64.b64encode(b"aegis:testpass123").decode()
    with app.test_client() as c:
        resp = c.get("/api/health", headers={"Authorization": f"Basic {creds}"})
        assert resp.status_code == 200


def test_auth_rejects_wrong_credentials():
    """Wrong credentials get 401."""
    app = _make_app(auth_env="aegis:testpass123")
    creds = base64.b64encode(b"aegis:wrongpass").decode()
    with app.test_client() as c:
        resp = c.get("/api/health", headers={"Authorization": f"Basic {creds}"})
        assert resp.status_code == 401
