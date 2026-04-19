"""Test /api/parametric-body route."""

import json
from pathlib import Path

import pytest

pytest.importorskip("flask")


@pytest.fixture
def app_client(tmp_path):
    """Create a test Flask client."""
    from aegis.viewer.server import create_app

    data_dir = str(tmp_path / "data")
    Path(data_dir).mkdir()
    app = create_app(data_dir=data_dir)
    app.config["TESTING"] = True
    return app.test_client()


def test_parametric_unknown_model(app_client):
    """Unknown model type returns 400."""
    resp = app_client.post(
        "/api/parametric-body",
        data=json.dumps({"model": "nonexistent"}),
        content_type="application/json",
    )
    assert resp.status_code == 400
    assert b"model must be one of" in resp.data


def test_parametric_anny_not_implemented(app_client):
    """Anny model returns 400 with not-implemented message."""
    resp = app_client.post(
        "/api/parametric-body",
        data=json.dumps({"model": "anny"}),
        content_type="application/json",
    )
    assert resp.status_code == 400
    assert b"Anny" in resp.data


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("betas", ["abc"]),
        ("betas", [[1, 2], [3]]),
        ("pose", ["abc"]),
        ("pose", [[1, 2], [3]]),
    ],
)
def test_parametric_rejects_non_numeric_or_ragged(app_client, field, value):
    """Non-numeric strings or ragged nested lists for betas/pose must return 400, not 500.

    ``np.array(..., dtype=np.float64)`` raises ValueError for these inputs;
    the route previously let it propagate as a 500 AttributeError to the client.
    """
    resp = app_client.post(
        "/api/parametric-body",
        data=json.dumps({field: value}),
        content_type="application/json",
    )
    assert resp.status_code == 400
    payload = json.loads(resp.data)
    assert field in payload.get("error", "")
