"""Unit tests for sentry_webhook helpers (no Flask app needed)."""

from __future__ import annotations

from aegis.viewer.routes.sentry_webhook import _extract_breadcrumbs, _extract_exception


def _make_event(breadcrumbs: list[dict]) -> dict:
    return {"entries": [{"type": "breadcrumbs", "data": {"values": breadcrumbs}}]}


def test_extract_breadcrumbs_generic_uses_message_when_data_empty():
    # Regression: operator precedence bug caused `msg or json.dumps(data)[:80] if data else cat`
    # to evaluate as `(msg or ...) if data else cat`, dropping the message whenever `data` was
    # falsy (empty dict). Result: breadcrumb text collapsed to the category name.
    event = _make_event(
        [
            {
                "category": "transaction",
                "message": "starting render",
                "data": {},
                "timestamp": "2026-04-21T00:00:00Z",
            }
        ]
    )
    out = _extract_breadcrumbs(event)
    assert out == ["`2026-04-21T00:00:00Z` **transaction:** starting render"]


def test_extract_breadcrumbs_generic_uses_message_when_data_present():
    event = _make_event(
        [
            {
                "category": "custom",
                "message": "hello",
                "data": {"a": 1},
                "timestamp": "ts",
            }
        ]
    )
    out = _extract_breadcrumbs(event)
    assert out == ["`ts` **custom:** hello"]


def test_extract_breadcrumbs_generic_falls_back_to_data_then_category():
    event = _make_event(
        [
            {"category": "c1", "data": {"x": 1}, "timestamp": "t1"},
            {"category": "c2", "data": {}, "timestamp": "t2"},
        ]
    )
    out = _extract_breadcrumbs(event)
    assert out[0] == '`t1` **c1:** {"x": 1}'
    assert out[1] == "`t2` **c2:** c2"


def test_extract_breadcrumbs_fetch_formats_request_line():
    event = _make_event(
        [
            {
                "category": "fetch",
                "data": {"method": "GET", "url": "/api/x", "status_code": 200},
                "timestamp": "ts",
            }
        ]
    )
    assert _extract_breadcrumbs(event) == ["`ts` **fetch:** GET /api/x -> 200"]


def test_extract_breadcrumbs_missing_entry_returns_empty():
    assert _extract_breadcrumbs({"entries": []}) == []
    assert _extract_breadcrumbs({}) == []


def test_extract_exception_formats_top_frames():
    event = {
        "entries": [
            {
                "type": "exception",
                "data": {
                    "values": [
                        {
                            "type": "ValueError",
                            "value": "boom",
                            "stacktrace": {
                                "frames": [
                                    {"filename": "a.py", "lineNo": 1, "function": "f"},
                                    {"filename": "b.py", "lineNo": 2, "function": "g"},
                                ]
                            },
                        }
                    ]
                },
            }
        ]
    }
    out = _extract_exception(event)
    assert out is not None
    assert "ValueError: boom" in out
    assert "at g (b.py:2)" in out
    assert "at f (a.py:1)" in out


def test_extract_exception_returns_none_when_missing():
    assert _extract_exception({"entries": []}) is None
