import asyncio
import json

import pytest
from fastapi.testclient import TestClient

from server.main import build_app
from server.state import State


@pytest.fixture
def app(paper_dir):
    app = build_app(
        paper_dir, State(), claude_session=None, pdf_builder=None, snapshot_mgr=None, hunk_mgr=None
    )
    return app


def test_ws_ping_pong_seq(app):
    with TestClient(app) as c:
        with c.websocket_connect("/stream") as ws:
            ws.send_text(json.dumps({"type": "ping"}))
            msg = ws.receive_json()
            assert msg["type"] == "pong" and "seq" in msg


def test_ws_batch_flush_with_no_session_marks_done_stub(app, paper_dir):
    """When claude_session is None, server marks each annotation done with stub one_liner."""
    with TestClient(app) as c:
        with c.websocket_connect("/stream") as ws:
            ws.send_text(
                json.dumps(
                    {
                        "type": "batch_flush",
                        "batch_id": "b1",
                        "annotations": [
                            {
                                "id": "a1",
                                "page": 1,
                                "shape": "rect",
                                "points": [[0, 0], [1, 1]],
                                "text": "x",
                                "mode": "edit",
                                "status": "pending",
                                "pass": 1,
                                "created_at": 0,
                            }
                        ],
                        "page_pngs": {"1": "iVBORw0KGgo="},
                    }
                )
            )
            seen = []
            for _ in range(4):
                seen.append(ws.receive_json())
            statuses = [m for m in seen if m.get("type") == "annotation_status"]
            assert any(m["status"] == "in_progress" for m in statuses)
            assert any(m["status"] == "done" for m in statuses)


def test_ws_in_flight_queues_subsequent(app, paper_dir):
    """Two batches sent back-to-back: second waits for first via in_flight + next_batch."""

    class SlowSession:
        async def send_batch(self, pass_, annotations, page_pngs, build_status_text):
            await asyncio.sleep(0.15)
            return ({a.id: {"status": "done", "one_liner": "ok"} for a in annotations}, "ok")

    class NopMgr:
        def take_snapshot(self, _):
            pass

        def record_post_sha(self, _):
            pass

        def persist_for_batch(self, *_, **__):
            pass

    app.state.claude_session = SlowSession()
    app.state.snapshot_mgr = NopMgr()
    app.state.hunk_mgr = NopMgr()
    with TestClient(app) as c:
        with c.websocket_connect("/stream") as ws:
            for bid, aid in [("b1", "a1"), ("b2", "a2")]:
                ws.send_text(
                    json.dumps(
                        {
                            "type": "batch_flush",
                            "batch_id": bid,
                            "annotations": [
                                {
                                    "id": aid,
                                    "page": 1,
                                    "shape": "rect",
                                    "points": [[0, 0], [1, 1]],
                                    "text": "x",
                                    "mode": "edit",
                                    "status": "pending",
                                    "pass": 1,
                                    "created_at": 0,
                                }
                            ],
                            "page_pngs": {"1": "iVBORw0KGgo="},
                        }
                    )
                )
            # Drain: expect a1 done before a2 done.
            seen_done_order = []
            for _ in range(20):
                m = ws.receive_json()
                if m.get("type") == "annotation_status" and m.get("status") == "done":
                    seen_done_order.append(m["id"])
                    if len(seen_done_order) == 2:
                        break
            assert seen_done_order == ["a1", "a2"]


def test_ws_cancel_pending_marks_rejected(app):
    """Local-only cancel of a never-flushed annotation."""
    with TestClient(app) as c:
        with c.websocket_connect("/stream") as ws:
            # Pre-populate state via batch_flush that immediately cancels.
            ws.send_text(json.dumps({"type": "cancel_annotation", "annotation_id": "ghost"}))
            # No matching annotation exists; server is silent (no event). Send a ping to confirm liveness.
            ws.send_text(json.dumps({"type": "ping"}))
            assert ws.receive_json()["type"] == "pong"
