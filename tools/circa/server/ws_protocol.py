"""WebSocket event helpers. Outbound events get a monotonic seq."""

from typing import Any
from .state import State


def event(state: State, type_: str, **fields) -> dict[str, Any]:
    return {"type": type_, "seq": state.next_seq(), **fields}


def annotation_status_event(state: State, **kw) -> dict:
    return event(state, "annotation_status", **kw)


def diff_update_event(state: State, **kw) -> dict:
    return event(state, "diff_update", **kw)


def build_status_event(state: State, **kw) -> dict:
    return event(state, "build_status", **kw)


def pdf_reloaded_event(state: State, *, pass_: int) -> dict:
    return event(state, "pdf_reloaded", **{"pass": pass_})
