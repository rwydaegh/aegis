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
