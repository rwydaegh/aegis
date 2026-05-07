"""FastAPI app + HTTP routes. WS endpoint added in Task 12."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
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

    from .ws_protocol import event

    @app.websocket("/stream")
    async def ws_stream(websocket: WebSocket):
        await websocket.accept()
        app.state.ws_clients.add(websocket)
        try:
            while True:
                data = await websocket.receive_json()
                kind = data.get("type")
                if kind == "ping":
                    await websocket.send_json(event(state, "pong"))
                elif kind == "batch_flush":
                    await _handle_batch_flush(app, data)
                elif kind == "clarification_reply":
                    await _handle_clarification_reply(app, data)
                elif kind == "cancel_annotation":
                    await _handle_cancel(app, data)
                else:
                    await websocket.send_json(event(state, "error", reason=f"unknown type {kind}"))
        except WebSocketDisconnect:
            return
        finally:
            app.state.ws_clients.discard(websocket)

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


async def _handle_batch_flush(app, data: dict) -> None:
    state = app.state.state
    if state.in_flight:
        state.queue_next_batch_new(data)
        return
    state.in_flight = True
    try:
        await _process_batch(app, data)
    finally:
        state.in_flight = False
        # Drain queued (clarifications first). Re-check after each item, since
        # a clarification reply arriving DURING the drain (which sets in_flight=True)
        # would be re-queued and must be picked up before we return.
        while True:
            pending = state.drain_next_batch()
            if not pending:
                break
            for queued in pending:
                state.in_flight = True
                try:
                    await _process_batch(app, queued)
                finally:
                    state.in_flight = False


async def _process_batch(app, data: dict) -> None:
    from .annotation import Annotation, AnnotationStatus
    from .ws_protocol import annotation_status_event, diff_update_event

    state = app.state.state
    annotations = [Annotation.from_dict(d) for d in data["annotations"]]
    for ann in annotations:
        ann.batch_id = data["batch_id"]
        ann.status = AnnotationStatus.IN_PROGRESS
        state.add_annotation(ann)
        await _broadcast(app, annotation_status_event(state, id=ann.id, status="in_progress"))

    if app.state.claude_session is None:
        from .ws_protocol import build_status_event

        for ann in annotations:
            ann.status = AnnotationStatus.DONE
            ann.one_liner = "(stub)"
            await _broadcast(
                app, annotation_status_event(state, id=ann.id, status="done", one_liner="(stub)")
            )
        await _broadcast(app, diff_update_event(state, hunk=""))
        await _broadcast(
            app, build_status_event(state, ok=state.last_build_ok, error_tail=state.last_build_error)
        )
        return

    # Real path: snapshot, send to Claude, persist hunks, update diff sidebar.
    if app.state.snapshot_mgr is not None:
        app.state.snapshot_mgr.take_snapshot(data["batch_id"])
    import base64

    page_pngs = {int(p): base64.b64decode(b64) for p, b64 in data.get("page_pngs", {}).items()}
    build_text = "ok" if state.last_build_ok else f"broken: {state.last_build_error[:500]}"
    statuses, _fb = await app.state.claude_session.send_batch(
        pass_=state.current_pass,
        annotations=annotations,
        page_pngs=page_pngs,
        build_status_text=build_text,
    )
    if app.state.hunk_mgr is not None:
        app.state.hunk_mgr.persist_for_batch(data["batch_id"], [a.id for a in annotations])
    if app.state.snapshot_mgr is not None:
        app.state.snapshot_mgr.record_post_sha(data["batch_id"])
    # Compute diff for sidebar (Task 13 will refine).
    if app.state.snapshot_mgr is not None and app.state.hunk_mgr is not None:
        from .diff_view import current_diff

        diff = current_diff(app.state.paper_dir, data["batch_id"])
        app.state.current_diff = diff
        await _broadcast(app, diff_update_event(state, hunk=diff))

    from .annotation import AnnotationStatus as AS

    for ann in annotations:
        info = statuses.get(ann.id, {})
        ann.status = AS(info.get("status", "needs_clarification"))
        ann.one_liner = info.get("one_liner")
        ann.clarification = info.get("clarification")
        await _broadcast(
            app,
            annotation_status_event(
                state,
                id=ann.id,
                status=ann.status.value,
                one_liner=ann.one_liner,
                clarification=ann.clarification,
            ),
        )


async def _handle_clarification_reply(app, data: dict) -> None:
    """Wired in Task 13."""
    raise NotImplementedError("Task 13")


async def _handle_cancel(app, data: dict) -> None:
    import time
    import uuid
    from .annotation import Annotation, AnnotationStatus
    from .ws_protocol import annotation_status_event

    state = app.state.state
    ann = state.get_annotation(data["annotation_id"])
    if ann is None:
        return
    if ann.status == AnnotationStatus.PENDING:
        ann.status = AnnotationStatus.REJECTED
        await _broadcast(app, annotation_status_event(state, id=ann.id, status="rejected"))
    elif ann.status == AnnotationStatus.NEEDS_CLARIFICATION:
        # Per spec: close the bubble, mark done with "user cancelled", and queue a follow-up
        # informing Claude so future reasoning has context.
        ann.status = AnnotationStatus.DONE
        ann.one_liner = "user cancelled"
        await _broadcast(
            app,
            annotation_status_event(
                state,
                id=ann.id,
                status="done",
                one_liner="user cancelled",
            ),
        )
        followup = Annotation(
            id=str(uuid.uuid4()),
            page=ann.page,
            shape=ann.shape,
            points=ann.points,
            text=f"(user cancelled clarification on {ann.id}; no edit needed)",
            mode=ann.mode,
            status=AnnotationStatus.PENDING,
            pass_=ann.pass_,
            created_at=int(time.time() * 1000),
            parent_id=ann.id,
            reply="(cancelled)",
        )
        payload = {
            "type": "batch_flush",
            "batch_id": str(uuid.uuid4()),
            "annotations": [followup.to_dict()],
            "page_pngs": {},
        }
        if state.in_flight:
            state.queue_next_batch_clarification(payload)
        else:
            await _handle_batch_flush(app, payload)
    # done / rejected / in_progress: cancel is a no-op; reject is the explicit path.
