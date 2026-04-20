"""Regression tests: non-finite JSON literals (NaN/Infinity) are rejected at
the parser, not per-field per-route.

Python's :mod:`json` accepts ``NaN``/``Infinity``/``-Infinity`` by default as
a non-standard RFC 8259 extension. Before ``StrictJSONProvider`` was installed
in ``aegis.viewer.server._app``, every scalar-float field on every route had
to grow its own ``math.isfinite`` guard to avoid silently propagating NaN
into the numeric pipeline. This test pins the choke-point behaviour so a
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
    cfg["server"]["port"] = 5101
    lab_dir = str(Path(__file__).parent / "fixtures" / "e2e_lab")
    app = create_app(data_dir=lab_dir, body_name="e2e_icosahedron", config=cfg)
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


# Routes that accept a JSON body through ``get_json_dict``. A body containing
# any non-finite literal must 400 with a clear message, not silently fall
# through to defaults and produce a 200/500 downstream.
_ROUTES_WITH_JSON_BODY = [
    "/api/environment/osm",
    "/api/environment/3dtiles",
    "/api/environment/geojson",
    "/api/terrain/elevation",
    "/api/basestations/load",
    "/api/basestations/compute",
    "/api/basestations/compute_mimo",
    "/api/mimo/compute",
    "/api/lsp-heatmap",
    "/api/parametric-body",
    "/api/optimize",
]
# Note: ``/api/compliance/spatial`` gates on "base stations loaded" *before*
# calling ``get_json_dict``, so its 400 comes from that state check rather
# than from JSON parsing. Excluded here; covered by other routes.


@pytest.mark.parametrize("endpoint", _ROUTES_WITH_JSON_BODY)
@pytest.mark.parametrize("literal", ["NaN", "Infinity", "-Infinity"])
def test_non_finite_literal_in_json_body_returns_400(viewer_client, endpoint, literal):
    """POSTing a body with a raw ``NaN``/``Infinity`` literal must 400.

    ``data=`` is used (not ``json=``) so the Python client doesn't pre-validate
    the payload; the server sees the literal bytes and must reject at parse.
    """
    body = f'{{"freq_hz": {literal}}}'
    resp = viewer_client.post(endpoint, data=body, content_type="application/json")
    assert resp.status_code == 400, (
        f"{endpoint} returned {resp.status_code} for body with {literal!r} literal; "
        "expected 400 from StrictJSONProvider parser rejection."
    )
    payload = resp.get_json()
    assert payload is not None
    assert "invalid json body" in payload.get("error", "").lower(), (
        f"Expected an 'Invalid JSON body' error, got: {payload!r}"
    )


def test_strict_provider_rejects_nested_nan(viewer_client):
    """A NaN nested inside an object or array must still be rejected."""
    body = '{"betas": [1.0, NaN, 3.0]}'
    resp = viewer_client.post("/api/parametric-body", data=body, content_type="application/json")
    assert resp.status_code == 400


def test_valid_finite_body_still_parses(viewer_client):
    """Sanity check: a body with only finite numbers must not regress."""
    resp = viewer_client.post(
        "/api/terrain/elevation",
        json={"lat": 51.05, "lon": 3.73},
    )
    # The endpoint itself may 4xx/5xx on the content, but not at JSON parse.
    assert resp.status_code != 400 or "invalid json body" not in ((resp.get_json() or {}).get("error", "").lower())
