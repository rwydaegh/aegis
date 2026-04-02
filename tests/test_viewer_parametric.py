"""Test /api/parametric-body route."""
import json
from pathlib import Path

import pytest


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
    assert b"Unknown model type" in resp.data


def test_parametric_anny_not_implemented(app_client):
    """Anny model returns 400 with not-implemented message."""
    resp = app_client.post(
        "/api/parametric-body",
        data=json.dumps({"model": "anny"}),
        content_type="application/json",
    )
    assert resp.status_code == 400
    assert b"Anny" in resp.data
