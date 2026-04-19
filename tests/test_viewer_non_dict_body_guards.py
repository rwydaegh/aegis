"""Regression tests: non-dict JSON bodies must 400, not 500.

The 4408cbc commit introduced ``get_json_dict()`` to reject non-dict top-level
JSON bodies (array/scalar/null) on ``/api/environment/combine`` and
``/api/optimize``. The rest of the route surface still called
``body = request.get_json(silent=True) or {}`` followed by ``body.get(...)``,
which raised ``AttributeError`` when a client posted e.g. ``[1, 2, 3]`` — the
whole request then surfaced as a 500 with a stack trace.

This test pins the boundary behaviour for the remaining migrated routes so a
future revert would be caught immediately.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("flask", reason="viewer tests require flask (pip install aegis[viewer])")


@pytest.fixture(scope="module")
def viewer_client():
    from aegis.viewer.config import load_config
    from aegis.viewer.server import _cache, create_app

    _cache.clear()
    cfg = load_config()
    cfg["server"]["host"] = "127.0.0.1"
    cfg["server"]["port"] = 5099
    lab_dir = str(Path(__file__).parent / "fixtures" / "e2e_lab")
    app = create_app(data_dir=lab_dir, body_name="e2e_icosahedron", config=cfg)
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


# Routes that accept a JSON body and must reject non-dict payloads with 400.
# We post a top-level JSON array; the handler should reject the shape before
# any downstream logic runs. 404/409 is also acceptable when the route gates
# on cached state before reaching the body parser (export-scene, from-voxels).
_ROUTES_NON_DICT_MUST_NOT_500 = [
    "/api/environment/osm",
    "/api/environment/3dtiles",
    "/api/environment/geojson",
    "/api/environment/export-scene",
    "/api/environment/from-voxels",
    "/api/terrain/elevation",
    "/api/basestations/load",
    "/api/basestations/compute",
    "/api/basestations/compute_mimo",
    "/api/mimo/compute",
    "/api/bug-report",
    "/api/lsp-heatmap",
    "/api/parametric-body",
    "/api/compliance/spatial",
]


@pytest.mark.parametrize("endpoint", _ROUTES_NON_DICT_MUST_NOT_500)
def test_array_body_does_not_500(viewer_client, endpoint):
    """POSTing a top-level JSON array must never crash the server (5xx)."""
    resp = viewer_client.post(endpoint, json=[1, 2, 3])
    assert resp.status_code < 500, (
        f"{endpoint} returned {resp.status_code} for a top-level array body; "
        "expected 4xx (bad-request) from the shape-check guard."
    )


@pytest.mark.parametrize("endpoint", _ROUTES_NON_DICT_MUST_NOT_500)
def test_scalar_body_does_not_500(viewer_client, endpoint):
    """POSTing a top-level JSON scalar must never 500."""
    resp = viewer_client.post(endpoint, json=42)
    assert resp.status_code < 500


def test_bug_report_null_description_is_400(viewer_client):
    """``{"description": null}`` previously crashed on ``None.strip()``.

    ``payload.get("description", "")`` returns ``None`` when the stored value
    is ``None`` (the default only applies if the key is missing). The fix
    coerces a missing/null description to the empty string before ``.strip()``.
    """
    resp = viewer_client.post("/api/bug-report", json={"description": None})
    assert resp.status_code == 400
    body = resp.get_json()
    assert body is not None
    assert "description" in body.get("error", "").lower()
