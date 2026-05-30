"""Regression: a non-string body_name must never cause a 500.

Schemathesis fuzzing found that POSTing ``{"body_name": []}`` to
``/api/compute/rt`` raised ``TypeError: unhashable type: 'list'`` when the
list was used as a dict key in the body cache, surfacing as a 500. Every
compute/optimize/basestation route resolves ``body_name`` the same way, so
the guard (and this test) cover all of them. Any non-string body_name must
produce a clean 4xx (or a 501 when an optional backend is absent), never a
500.
"""

from __future__ import annotations

import pytest

pytest.importorskip("flask", reason="viewer tests require flask (pip install aegis[viewer])")

# Documented endpoints that resolve body_name from the request body. These are
# exactly the paths schemathesis fuzzes from /api/openapi.json.
_BODY_NAME_ENDPOINTS = [
    "/api/compute",
    "/api/compute/rt",
    "/api/compute/sionna-rt",
    "/api/compute/voxel-rt",
    "/api/optimize",
    "/api/basestations/compute",
    "/api/basestations/compute_mimo",
]


@pytest.mark.parametrize("endpoint", _BODY_NAME_ENDPOINTS)
@pytest.mark.parametrize("bad_body_name", [[], {}, 0, [1, 2], {"x": 1}])
def test_non_string_body_name_never_500(viewer_app, endpoint, bad_body_name):
    with viewer_app.test_client() as c:
        resp = c.post(endpoint, json={"body_name": bad_body_name})
    # The whole point: an unhashable / wrong-typed body_name must not crash.
    assert resp.status_code != 500, (
        f"{endpoint} returned 500 for body_name={bad_body_name!r}: {resp.get_data(as_text=True)[:200]}"
    )
    # Response must be valid JSON with an error message (schema contract).
    payload = resp.get_json()
    assert isinstance(payload, dict)
    assert "error" in payload
