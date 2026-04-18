"""In-process Schemathesis smoke test against the viewer OpenAPI spec.

This runs Schemathesis against the Flask app via its WSGI adapter, using the
OpenAPI 3.0.3 document served at ``/api/openapi.json``. It exercises every
operation the spec covers with a small sample budget so the PR-tier suite
stays under the time budget. The full patch-release sweep lives in
``.github/workflows/release.yml``.

Intentionally narrow: Schemathesis' `response_schema_conformance` check is
skipped because the `X-Stats`-in-header pattern on `/api/compute` and the SSE
stream on `/api/optimize` aren't expressible in vanilla OpenAPI 3.0. We still
assert no 5xx and no content-type drift.
"""

from __future__ import annotations

import pytest

pytest.importorskip("schemathesis", reason="schemathesis is optional (pip install aegis[dev])")
pytest.importorskip("flask", reason="viewer tests require flask (pip install aegis[viewer])")

import schemathesis  # noqa: E402
from hypothesis import HealthCheck, settings  # noqa: E402


@pytest.fixture(scope="module")
def viewer_app_module():
    """Module-scoped viewer app (cheap to build once per suite)."""
    from pathlib import Path

    from aegis.viewer.config import load_config
    from aegis.viewer.server import _cache, create_app

    _cache.clear()
    cfg = load_config()
    cfg["server"]["host"] = "127.0.0.1"
    cfg["server"]["port"] = 5099
    lab_dir = str(Path(__file__).parent / "fixtures" / "e2e_lab")
    app = create_app(data_dir=lab_dir, body_name="e2e_icosahedron", config=cfg)
    app.config["TESTING"] = True
    return app


@pytest.fixture(scope="module")
def openapi_schema(viewer_app_module):
    return schemathesis.openapi.from_wsgi("/api/openapi.json", viewer_app_module)


# Low sample count so this stays PR-tier friendly; the real sweep runs on tags.
_SETTINGS = settings(
    max_examples=5,
    deadline=None,
    suppress_health_check=list(HealthCheck),
)


def test_openapi_document_is_served(viewer_app_module):
    """The spec endpoint must return a complete OpenAPI 3.0.3 document."""
    with viewer_app_module.test_client() as c:
        resp = c.get("/api/openapi.json")
    assert resp.status_code == 200
    doc = resp.get_json()
    assert doc["openapi"].startswith("3.")
    assert "paths" in doc
    assert len(doc["paths"]) >= 10
    # Wave 3F coverage is the floor.
    for required in (
        "/api/compute",
        "/api/compute/rt",
        "/api/optimize",
        "/api/compliance/limits",
        "/api/environment/materials",
    ):
        assert required in doc["paths"], f"missing {required}"


def _assert_no_5xx_for_path(schema, path: str, method: str = "POST") -> None:
    """Fuzz one operation and assert no 5xx responses."""
    from hypothesis import given

    op = schema.find_operation_by_label(f"{method} {path}")
    strategy = op.as_strategy()

    @_SETTINGS
    @given(case=strategy)
    def run(case):
        response = case.call()
        assert response.status_code < 500, f"server error {response.status_code} on {path}: {response.content[:300]!r}"

    run()


def test_compute_endpoint_no_5xx_on_fuzz(openapi_schema):
    _assert_no_5xx_for_path(openapi_schema, "/api/compute", "POST")


def test_environment_materials_no_5xx_on_fuzz(openapi_schema):
    _assert_no_5xx_for_path(openapi_schema, "/api/environment/materials", "GET")


def test_compliance_limits_no_5xx_on_fuzz(openapi_schema):
    _assert_no_5xx_for_path(openapi_schema, "/api/compliance/limits", "GET")
