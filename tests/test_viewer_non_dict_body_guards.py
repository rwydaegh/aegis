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


def test_lsp_heatmap_negative_seed_is_400(viewer_client):
    """Negative seeds reach ``np.random.default_rng`` which raises a cryptic
    ``ValueError: expected non-negative integer``. The route must reject them
    up front with a clear 400, not a numpy-flavoured one (Sentry #684)."""
    resp = viewer_client.post(
        "/api/lsp-heatmap",
        json={
            "preset": "3GPP_38.901_UMi_LOS",
            "freq_ghz": 28.0,
            "antenna_pos": [0, 0, 10],
            "lsp_name": "SF_dB",
            "bounds": [-100, 100, -100, 100],
            "resolution": 32,
            "seed": -100,
        },
    )
    assert resp.status_code == 400
    assert "seed" in resp.get_json()["error"].lower()


@pytest.mark.parametrize(
    ("field", "payload_override", "expected_substr"),
    [
        ("bounds", {"bounds": [float("nan"), 50, -50, 50]}, "bounds"),
        ("bounds", {"bounds": [float("-inf"), 50, -50, 50]}, "bounds"),
        ("bounds", {"bounds": [float("inf"), 50, -50, 50]}, "bounds"),
        ("freq_ghz", {"freq_ghz": float("nan")}, "freq_ghz"),
        ("freq_ghz", {"freq_ghz": float("inf")}, "freq_ghz"),
        ("antenna_pos", {"antenna_pos": [0, 0, float("nan")]}, "antenna_pos"),
        ("antenna_pos", {"antenna_pos": [float("inf"), 0, 10]}, "antenna_pos"),
    ],
)
def test_lsp_heatmap_nonfinite_numeric_inputs_are_400(viewer_client, field, payload_override, expected_substr):
    """Non-finite floats in ``bounds``/``freq_ghz``/``antenna_pos`` must be
    rejected with a clear 400. Python's ``float(...)`` happily accepts
    ``NaN``/``Infinity`` and they would otherwise cascade into a NaN-filled
    200 response (issue #700)."""
    payload = {
        "preset": "3GPP_38.901_UMi_LOS",
        "freq_ghz": 28.0,
        "antenna_pos": [0, 0, 10],
        "lsp_name": "SF_dB",
        "bounds": [-50, 50, -50, 50],
        "resolution": 32,
        "seed": 42,
    }
    payload.update(payload_override)
    resp = viewer_client.post("/api/lsp-heatmap", json=payload)
    assert resp.status_code == 400, (
        f"/api/lsp-heatmap returned {resp.status_code} for non-finite {field}; "
        "expected 400 from the finite-value guard."
    )
    body = resp.get_json()
    assert body is not None
    assert expected_substr in body.get("error", "").lower()


@pytest.mark.parametrize("bad_user", [None, 42, "hello", [1, 2, 3]])
def test_mimo_compute_non_dict_user_is_400(viewer_client, bad_user):
    """``/api/mimo/compute`` must reject non-dict elements inside ``users``.

    Previously, ``_validate_users_cfg`` ran ``"id" in u`` on every element,
    which raises ``TypeError`` when ``u`` is ``None``/``int`` (not a container)
    and silently accepts strings/lists — letting downstream ``u.get("phantom", ...)``
    crash with ``AttributeError`` for a 500. The guard now rejects at the
    validator with a clear 400.
    """
    # ``array`` is validated before ``users``; supply a minimal stub so the
    # request reaches ``_validate_users_cfg``.
    payload = {
        "array": {"n_elements": [2, 2], "spacing": 0.5, "position": [0.0, 0.0, 2.0]},
        "users": [bad_user],
    }
    resp = viewer_client.post("/api/mimo/compute", json=payload)
    assert resp.status_code == 400, (
        f"/api/mimo/compute returned {resp.status_code} for users=[{bad_user!r}]; "
        "expected 400 from the element-type guard."
    )
    body = resp.get_json()
    assert body is not None
    assert "each user" in body.get("error", "").lower()


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
