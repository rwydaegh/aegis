"""Test GLB phantom serving route."""
import struct

import pytest


def _make_minimal_glb(path):
    """Write a minimal valid GLB (empty scene)."""
    import json

    gltf_json = json.dumps(
        {"asset": {"version": "2.0"}, "scene": 0, "scenes": [{"nodes": []}]}
    ).encode()
    while len(gltf_json) % 4 != 0:
        gltf_json += b" "
    json_chunk = struct.pack("<II", len(gltf_json), 0x4E4F534A) + gltf_json
    total = 12 + len(json_chunk)
    header = struct.pack("<III", 0x46546C67, 2, total)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(header + json_chunk)


@pytest.fixture
def app_with_glb(tmp_path):
    """Create a test app with a GLB phantom in a temp directory."""
    phantom_dir = tmp_path / "phantoms"
    phantom_dir.mkdir()
    _make_minimal_glb(phantom_dir / "test_body.glb")

    data_dir = tmp_path / "data"
    data_dir.mkdir()

    from aegis.viewer.config import load_config
    from aegis.viewer.server import create_app

    cfg = load_config()
    cfg["body"]["phantom_dir"] = str(phantom_dir)
    app = create_app(data_dir=str(data_dir), config=cfg)
    app.config["TESTING"] = True
    return app.test_client()


def test_serve_glb(app_with_glb):
    resp = app_with_glb.get("/api/phantom/test_body.glb")
    assert resp.status_code == 200
    assert resp.content_type == "model/gltf-binary"
    assert resp.data[:4] == b"glTF"


def test_serve_glb_404(app_with_glb):
    resp = app_with_glb.get("/api/phantom/nonexistent.glb")
    assert resp.status_code == 404
