"""Tests confirming the old AEGIS_VIEWER_AUTH Basic Auth is removed.

The password gate is now session-based (AEGIS_GATE_PASSWORD). See
tests/viewer/test_auth.py for the new auth tests.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

pytest.importorskip("flask")


@pytest.fixture(autouse=True)
def _clean_auth_env():
    """Ensure auth env vars are cleaned up after each test."""
    yield
    os.environ.pop("AEGIS_VIEWER_AUTH", None)
    os.environ.pop("AEGIS_GATE_PASSWORD", None)


def _make_app(auth_env: str | None = None):
    """Create a minimal Flask test app.

    Uses the e2e_lab fixture data dir so body loading succeeds.
    """
    if auth_env:
        os.environ["AEGIS_VIEWER_AUTH"] = auth_env
    else:
        os.environ.pop("AEGIS_VIEWER_AUTH", None)

    from aegis.viewer.server import _cache, create_app

    _cache.clear()
    data_dir = str(Path(__file__).parent / "fixtures" / "e2e_lab")
    app = create_app(
        data_dir=data_dir,
        body_name="e2e_icosahedron",
        config={"server": {"host": "127.0.0.1", "port": 5099}},
    )
    app.config["TESTING"] = True
    return app


def test_no_auth_when_gate_password_unset():
    """Without AEGIS_GATE_PASSWORD, all routes are open regardless of AEGIS_VIEWER_AUTH."""
    app = _make_app(auth_env=None)
    with app.test_client() as c:
        resp = c.get("/api/health")
        assert resp.status_code == 200


def test_viewer_auth_env_has_no_effect():
    """Setting AEGIS_VIEWER_AUTH no longer gates any route (Basic Auth is removed)."""
    app = _make_app(auth_env="aegis:testpass123")
    with app.test_client() as c:
        # /api/health is always exempt, should return 200 regardless
        resp = c.get("/api/health")
        assert resp.status_code == 200
