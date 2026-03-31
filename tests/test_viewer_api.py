"""Flask JSON routes for the React viewer (built assets in viewer/static/).

The legacy HTML template `_legacy_index.html` is only used when `static/index.html`
is missing. These tests hit stable API endpoints shared by the React client.
"""

from __future__ import annotations

import pytest

pytest.importorskip("flask")


def test_api_health(viewer_app):
    with viewer_app.test_client() as c:
        resp = c.get("/api/health")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "ok"
        assert "version" in data


def test_api_levels_lists_all_fidelity_levels(viewer_app):
    with viewer_app.test_client() as c:
        resp = c.get("/api/levels")
        assert resp.status_code == 200
        levels = resp.get_json()
        assert len(levels) == 9
        assert levels[0]["level"] == 0
        assert levels[8]["level"] == 8
        assert "description" in levels[2]


def test_api_viewer_config_returns_json(viewer_app):
    with viewer_app.test_client() as c:
        resp = c.get("/api/viewer-config")
        assert resp.status_code == 200
        cfg = resp.get_json()
        assert "server" in cfg


def test_api_body_info_when_mesh_loaded(viewer_app):
    with viewer_app.test_client() as c:
        resp = c.get("/api/body/info")
        assert resp.status_code == 200
        info = resp.get_json()
        assert info["n_triangles"] > 0
        assert "bounding_box" in info
