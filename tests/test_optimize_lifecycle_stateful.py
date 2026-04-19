"""Hypothesis ``RuleBasedStateMachine`` for the ``/api/optimize`` lifecycle.

Models the optimize route as a small finite-state machine that mutates
server-side session bookkeeping (``_cancel_events``), the session-scoped
cache, and the "most recent terminal event" the client would display as
the current run summary.

Uses the real Flask ``test_client`` + real ``run_optimization`` loop. The
synthesized ``mimo_peak`` payload keeps each iteration under a millisecond
so 50 Hypothesis examples x 30 steps finishes in a couple of seconds.

Invariants:

- at most one cancel-event registered per session at any step boundary
- the previous run's cancel event is ``set()`` when a new run starts
- after a terminal event is yielded, ``_cancel_events`` has popped the sid
- ``/api/optimize/cancel`` without a running job returns ``{"cancelled": False}``
- the "current summary" always reflects the last terminal event, never an
  older run's final state
"""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from hypothesis import HealthCheck, settings
from hypothesis import strategies as st
from hypothesis.stateful import (
    RuleBasedStateMachine,
    invariant,
    precondition,
    rule,
)

pytest.importorskip("flask", reason="viewer tests require flask (pip install aegis[viewer])")

_E2E_LAB_DIR = str(Path(__file__).parent / "fixtures" / "e2e_lab")

# Fixed session id for every state-machine step so ``_cancel_events`` behaves
# as a single-slot dict (matches a real client's cookie-backed session).
_SID = "hypothesis-optimize-sid"


def _sse_events(resp) -> list[dict[str, Any]]:
    """Parse an SSE response body into a list of event dicts."""
    out: list[dict[str, Any]] = []
    for line in resp.data.decode().split("\n"):
        if line.startswith("data: "):
            out.append(json.loads(line[6:]))
    return out


def _is_terminal(ev: dict[str, Any]) -> bool:
    """Matches the backend's own terminal conditions."""
    return bool(ev.get("done") or ev.get("error") or ev.get("cancelled") or ev.get("converged"))


def _synth_mimo_payload(n_tri: int, n_ant: int, p_max: float, max_iters: int, seed: int) -> dict[str, Any]:
    rng = np.random.default_rng(seed)
    G = (rng.standard_normal((n_tri, 3, n_ant)) + 1j * rng.standard_normal((n_tri, 3, n_ant))) * 0.01
    x_init = np.conj(G[0, 0, :]) / np.linalg.norm(G[0, 0, :])
    return {
        "mode": "mimo_peak",
        "G_tilde_real": G.real.tolist(),
        "G_tilde_imag": G.imag.tolist(),
        "x_init_real": x_init.real.tolist(),
        "x_init_imag": x_init.imag.tolist(),
        "p_max": float(p_max),
        "max_iters": int(max_iters),
    }


class OptimizeLifecycleMachine(RuleBasedStateMachine):
    """State machine for /api/optimize."""

    def __init__(self) -> None:
        super().__init__()
        from aegis.viewer.config import load_config
        from aegis.viewer.routes.optimize import _cancel_events, _cancel_lock
        from aegis.viewer.server import _cache, create_app

        _cache.clear()
        cfg = load_config()
        cfg["server"]["host"] = "127.0.0.1"
        cfg["server"]["port"] = 5096
        self.app = create_app(data_dir=_E2E_LAB_DIR, body_name="e2e_icosahedron", config=cfg)
        self.app.config["TESTING"] = True

        self._cancel_events = _cancel_events
        self._cancel_lock = _cancel_lock
        # Wipe any leakage from a prior state-machine instance.
        with self._cancel_lock:
            self._cancel_events.pop(_SID, None)

        # Per-client state mirrors the UI: latest terminal event from the most
        # recent run, the iteration counter, and an "active" flag. The server
        # drains synchronously under ``test_client``, so "active" is only True
        # between a POST and the subsequent ``resp.data`` read - we always
        # drain inside the same rule to keep this deterministic.
        self.last_terminal: dict[str, Any] | None = None
        self.last_mode: str | None = None
        self.run_count = 0

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _client(self):
        c = self.app.test_client()
        with c.session_transaction() as sess:
            sess["session_id"] = _SID
        return c

    # ------------------------------------------------------------------
    # Rules
    # ------------------------------------------------------------------

    @rule(
        max_iters=st.integers(min_value=1, max_value=5),
        n_ant=st.integers(min_value=2, max_value=6),
        p_max=st.floats(min_value=0.1, max_value=10.0, allow_nan=False, allow_infinity=False),
        seed=st.integers(min_value=0, max_value=2**31 - 1),
    )
    def start_mimo_run(self, max_iters: int, n_ant: int, p_max: float, seed: int) -> None:
        """Happy-path start: drain the stream synchronously."""
        payload = _synth_mimo_payload(n_tri=10, n_ant=n_ant, p_max=p_max, max_iters=max_iters, seed=seed)
        with self._client() as c:
            resp = c.post("/api/optimize", json=payload)
            assert resp.status_code == 200, resp.data
            events = _sse_events(resp)
        self.run_count += 1
        assert len(events) >= 1
        # The server always yields at least a done/error terminal event.
        terminal = events[-1]
        assert _is_terminal(terminal), f"last event not terminal: {terminal}"
        self.last_terminal = terminal
        self.last_mode = "mimo_peak"

    @rule(
        max_iters=st.integers(min_value=1, max_value=3),
        grid_size=st.integers(min_value=1, max_value=2),
    )
    def start_placement_run(self, max_iters: int, grid_size: int) -> None:
        """Placement mode uses the free-space RT fallback (fast)."""
        with self._client() as c:
            resp = c.post(
                "/api/optimize",
                json={
                    "mode": "placement",
                    "max_iters": max_iters,
                    "grid_size": grid_size,
                    "grid_spacing": 2.0,
                    "center": [5, 0, 3],
                    "body_name": "e2e_icosahedron",
                    "level": 2,
                },
            )
            assert resp.status_code == 200, resp.data
            events = _sse_events(resp)
        self.run_count += 1
        assert len(events) >= 1
        self.last_terminal = events[-1]
        self.last_mode = "placement"

    @rule()
    def cancel(self) -> None:
        """Cancel endpoint: must succeed and return a structured response.

        Because ``test_client`` drains previous runs synchronously, the expected
        response here is always ``cancelled=False`` (no run is pending).
        """
        with self._client() as c:
            resp = c.post("/api/optimize/cancel")
        assert resp.status_code == 200
        body = resp.get_json()
        assert "cancelled" in body
        # No pending run after a drained stream.
        assert body["cancelled"] is False, body

    @rule()
    def start_preempts_pending_cancel(self) -> None:
        """Inject a dangling cancel event, then start a run.

        Mimics the shape of a mid-stream interruption where the previous
        request's Event is still registered. The start handler must ``set()``
        the dangling event (interrupt any real concurrent iterator) and
        replace it with a fresh one.
        """
        dangling = threading.Event()
        with self._cancel_lock:
            self._cancel_events[_SID] = dangling

        payload = _synth_mimo_payload(n_tri=8, n_ant=3, p_max=1.0, max_iters=2, seed=7)
        with self._client() as c:
            resp = c.post("/api/optimize", json=payload)
            assert resp.status_code == 200
            events = _sse_events(resp)

        # Contract: previous cancel event must have been fired.
        assert dangling.is_set(), "start_preempts_pending_cancel: dangling event was not set by the new start"
        self.run_count += 1
        self.last_terminal = events[-1] if events else {"error": True, "message": "no events"}
        self.last_mode = "mimo_peak"

    @rule()
    def query_summary(self) -> None:
        """Read the "current summary" the client would display.

        There is no dedicated summary endpoint; the summary is the last
        terminal event from the most recent run. We assert it is consistent
        with ``self.last_terminal`` and, if present, refers to the last mode.
        """
        if self.last_terminal is None:
            return
        # The summary must always carry a terminal marker after a finished run.
        assert _is_terminal(self.last_terminal), f"non-terminal summary: {self.last_terminal}"
        mode = self.last_terminal.get("mode")
        if mode is not None and self.last_mode is not None:
            # Either the server stamps the mode onto the final event or it
            # stamps only mid-iteration events. Both are fine, but if it IS
            # stamped, it must match the last started run's mode.
            assert mode == self.last_mode, f"summary mode {mode} != last started {self.last_mode}"

    # ------------------------------------------------------------------
    # Invariants
    # ------------------------------------------------------------------

    @invariant()
    def at_most_one_cancel_event(self) -> None:
        """Session-scoped cancel bookkeeping holds at most one entry per sid."""
        with self._cancel_lock:
            keys = list(self._cancel_events.keys())
        # We always drain within the rule, so after every rule boundary the
        # sid must have been popped (see the ``finally`` block in the route).
        assert _SID not in keys, f"cancel_events leaked sid={_SID} after a drained run: keys={keys}"

    @precondition(lambda self: self.last_terminal is not None)
    @invariant()
    def summary_is_terminal(self) -> None:
        assert self.last_terminal is not None
        assert _is_terminal(self.last_terminal), f"stored summary is non-terminal: {self.last_terminal}"

    @precondition(lambda self: self.last_terminal is not None)
    @invariant()
    def summary_has_no_stale_iter(self) -> None:
        """Terminal iter counter is either absent or non-negative and bounded.

        This catches the "iteration counter from a previous run leaks into the
        new run" bug shape called out in the roadmap.
        """
        assert self.last_terminal is not None
        it = self.last_terminal.get("iter")
        if it is not None:
            assert isinstance(it, int), f"iter is {type(it).__name__}: {it!r}"
            # Each individual run is capped at max_iters<=5 in the rules above,
            # plus 1 for placement's "done" wrap-up. Any value beyond that
            # implies the counter was not reset between runs.
            assert 0 <= it <= 20, f"iter={it} out of reasonable range for a fresh run"

    def teardown(self) -> None:  # noqa: D401
        """Clean up module-level state so sibling tests see a pristine dict."""
        with self._cancel_lock:
            self._cancel_events.pop(_SID, None)


TestOptimizeLifecycle = OptimizeLifecycleMachine.TestCase
TestOptimizeLifecycle.settings = settings(
    max_examples=50,
    stateful_step_count=30,
    deadline=None,
    suppress_health_check=[
        HealthCheck.filter_too_much,
        HealthCheck.data_too_large,
        # Flask create_app is slow-ish relative to a rule step; each machine
        # instance pays it once in __init__.
        HealthCheck.too_slow,
    ],
)


# ---------------------------------------------------------------------------
# Smoke test: one explicit walk through the machine.
# ---------------------------------------------------------------------------


def test_optimize_lifecycle_smoke() -> None:
    m = OptimizeLifecycleMachine()
    try:
        m.start_mimo_run(max_iters=2, n_ant=3, p_max=1.0, seed=0)
        m.at_most_one_cancel_event()
        m.summary_is_terminal()
        m.cancel()
        m.start_preempts_pending_cancel()
        m.at_most_one_cancel_event()
        m.query_summary()
        m.start_placement_run(max_iters=1, grid_size=1)
        m.query_summary()
    finally:
        m.teardown()


if __name__ == "__main__":
    pytest.main([__file__, "-x", "-n", "0"])
