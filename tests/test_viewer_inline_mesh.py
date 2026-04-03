"""Test that /api/compute accepts inline mesh binary."""

import json
from pathlib import Path

import numpy as np
import pytest

pytest.importorskip("flask")

from aegis.geometry.mesh import BodyMesh  # noqa: E402


@pytest.fixture
def app_client(tmp_path):
    """Create a test Flask client with a minimal data directory."""
    from aegis.viewer.server import create_app

    data_dir = str(tmp_path / "data")
    Path(data_dir).mkdir()
    app = create_app(data_dir=data_dir)
    app.config["TESTING"] = True
    return app.test_client()


def test_compute_with_inline_mesh(app_client):
    """Compute endpoint accepts inline binary mesh instead of body_name."""
    body = BodyMesh.sphere(radius=0.3, n_subdivisions=3)  # 1280 triangles
    flat_v = body.vertices.reshape(-1, 3).astype(np.float32)  # (N_tri*3, 3)
    flat_n = np.repeat(body.normals, 3, axis=0).astype(np.float32)  # (N_tri*3, 3)
    mesh_binary = flat_v.tobytes() + flat_n.tobytes()

    params = {
        "antennaPos": [0, 0, 2],
        "mode": "spatial",
        "fresnel": True,
        "powerDbm": 23.0,
        "freqGhz": 28.0,
        "n_triangles": body.n_triangles,
    }

    resp = app_client.post(
        "/api/compute",
        data=mesh_binary,
        headers={
            "Content-Type": "application/octet-stream",
            "X-Compute-Params": json.dumps(params),
        },
    )
    assert resp.status_code == 200
    assert resp.content_type == "application/octet-stream" or "sab" in (resp.get_json() or {})


def test_compute_with_inline_mesh_rejects_oversized(app_client):
    """Reject inline mesh binary exceeding 5 MB."""
    big_binary = b"\x00" * (6 * 1024 * 1024)
    params = {"antennaPos": [0, 0, 2], "mode": "bound", "n_triangles": 1}
    resp = app_client.post(
        "/api/compute",
        data=big_binary,
        headers={
            "Content-Type": "application/octet-stream",
            "X-Compute-Params": json.dumps(params),
        },
    )
    assert resp.status_code in (400, 413)
