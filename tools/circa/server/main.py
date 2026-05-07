"""FastAPI app + HTTP routes. WS endpoint added in Task 12."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, PlainTextResponse, JSONResponse

from .state import State


def build_app(
    paper_dir: Path,
    state: State,
    claude_session,
    pdf_builder,
    snapshot_mgr,
    hunk_mgr,
) -> FastAPI:
    app = FastAPI()
    app.state.paper_dir = paper_dir
    app.state.state = state
    app.state.claude_session = claude_session
    app.state.pdf_builder = pdf_builder
    app.state.snapshot_mgr = snapshot_mgr
    app.state.hunk_mgr = hunk_mgr
    app.state.ws_clients = set()  # populated in Task 12; broadcast registry

    @app.get("/state")
    async def get_state():
        return {
            "server_instance_id": state.server_instance_id,
            "pass": state.current_pass,
            "in_flight": state.in_flight,
            "last_seq": state.last_seq,
            "annotations": [a.to_dict() for a in state.all_annotations()],
            "build_status": {"ok": state.last_build_ok, "error_tail": state.last_build_error},
            "current_diff": getattr(app.state, "current_diff", ""),
        }

    @app.get("/pdf")
    async def get_pdf():
        p = paper_dir / "paper.pdf"
        if not p.exists():
            raise HTTPException(status_code=404, detail="paper.pdf not found")
        return FileResponse(p, media_type="application/pdf")

    @app.get("/tex")
    async def get_tex():
        return PlainTextResponse((paper_dir / "paper.tex").read_text())

    @app.post("/rebuild")
    async def post_rebuild():
        if state.in_flight:
            return JSONResponse({"reason": "batch in-flight"}, status_code=409)
        if pdf_builder is None:
            raise HTTPException(503, "pdf_builder not initialized")
        result = await pdf_builder.build()
        state.last_build_ok = result.ok
        state.last_build_error = result.error_tail
        if not result.ok:
            return JSONResponse(
                {"ok": False, "error": result.error_tail, "timed_out": result.timed_out},
                status_code=408 if result.timed_out else 500,
            )
        new_pass = state.next_pass()
        state.drop_annotations_below_pass(new_pass)
        await _broadcast(app, _pdf_reloaded(state, new_pass))
        await _broadcast(app, _build_status(state, ok=True, error_tail=""))
        return {"ok": True, "pass": new_pass}

    @app.post("/reject/{annotation_id}")
    async def post_reject(annotation_id: str):
        if hunk_mgr is None:
            raise HTTPException(503, "hunk_mgr not initialized")
        try:
            hunk_mgr.apply_reverse(annotation_id)
        except RuntimeError as e:
            return JSONResponse({"reason": str(e)}, status_code=409)
        from .annotation import AnnotationStatus

        ann = state.get_annotation(annotation_id)
        if ann:
            ann.status = AnnotationStatus.PENDING
        return {"ok": True}

    return app


# Broadcast scaffolding — Task 12 plugs the WS in.
async def _broadcast(app, event: dict) -> None:
    for ws in list(app.state.ws_clients):
        try:
            await ws.send_json(event)
        except Exception:
            app.state.ws_clients.discard(ws)


def _pdf_reloaded(state, new_pass):
    from .ws_protocol import pdf_reloaded_event

    return pdf_reloaded_event(state, pass_=new_pass)


def _build_status(state, ok, error_tail):
    from .ws_protocol import build_status_event

    return build_status_event(state, ok=ok, error_tail=error_tail)


def run_server(
    paper_dir: Path, port: int, build_timeout_s: int, batch_timeout_s: int, pdfcomment_enabled: bool
) -> None:
    raise NotImplementedError("wired in Task 14")
