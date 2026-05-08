from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from server.main import build_app
from server.state import State


@pytest.fixture
def client(paper_dir: Path):
    app = build_app(
        paper_dir, State(), claude_session=None, pdf_builder=None, snapshot_mgr=None, hunk_mgr=None
    )
    with TestClient(app) as c:
        yield c, app


def test_get_state_basic(client):
    c, app = client
    r = c.get("/state")
    assert r.status_code == 200
    d = r.json()
    assert "server_instance_id" in d
    assert d["pass"] == 1
    assert d["in_flight"] is False
    assert d["last_seq"] == 0


def test_get_pdf_404_when_absent(client):
    c, _ = client
    assert c.get("/pdf").status_code == 404


def test_get_pdf_returns_bytes(client, paper_dir):
    (paper_dir / "paper.pdf").write_bytes(b"%PDF-1.4 fake")
    c, _ = client
    assert c.get("/pdf").content == b"%PDF-1.4 fake"


def test_get_tex(client):
    c, _ = client
    assert "Hello circa." in c.get("/tex").text


def test_rebuild_returns_409_when_in_flight(client):
    c, app = client
    app.state.state.in_flight = True
    r = c.post("/rebuild")
    assert r.status_code == 409


def test_reject_404_when_no_hunk_mgr(client):
    c, _ = client
    r = c.post("/reject/abc")
    assert r.status_code == 503


def test_fix_inline_fence_markers_splits_trailing_prose(tmp_path):
    from server.main import _fix_inline_fence_markers

    tex = tmp_path / "paper.tex"
    tex.write_text(
        "before\n"
        "% [circa:abc-123:end] trailing prose here\n"
        "% [circa:def-456:end] more trailing\n"
        "% [circa:abe-789:begin] also-bad\n"
        "after\n"
    )
    changed = _fix_inline_fence_markers(tex)
    assert changed is True
    out = tex.read_text()
    assert "% [circa:abc-123:end]\ntrailing prose here\n" in out
    assert "% [circa:def-456:end]\nmore trailing\n" in out
    assert "% [circa:abe-789:begin]\nalso-bad\n" in out


def test_fix_inline_fence_markers_noop_when_clean(tmp_path):
    from server.main import _fix_inline_fence_markers

    tex = tmp_path / "paper.tex"
    tex.write_text("% [circa:abc-123:begin]\nfoo\n% [circa:abc-123:end]\n")
    assert _fix_inline_fence_markers(tex) is False


def test_fix_inline_fence_markers_handles_merged_id(tmp_path):
    from server.main import _fix_inline_fence_markers

    tex = tmp_path / "paper.tex"
    tex.write_text("% [circa:abc-1+def-2:end] trailing\n")
    _fix_inline_fence_markers(tex)
    assert tex.read_text() == "% [circa:abc-1+def-2:end]\ntrailing\n"
