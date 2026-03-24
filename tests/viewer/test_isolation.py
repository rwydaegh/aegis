"""Tests for multi-user isolation: thread-safe state in engine, compute, and pipeline."""

from __future__ import annotations

import threading

import numpy as np
import pytest

from aegis.engine import DosimetryEngine
from aegis.geometry.mesh import BodyMesh
from aegis.paths import PropagationPaths
from aegis.result import DosimetryResult
from aegis.tissue.dielectric import SKIN_28GHZ

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_flat_mesh(n: int = 20) -> BodyMesh:
    """Minimal flat mesh for fast tests."""
    rng = np.random.default_rng(0)
    s = np.sqrt(2e-4)
    cx = rng.uniform(0, 1, n)
    cy = rng.uniform(0, 1, n)
    z = np.zeros(n)
    verts = np.zeros((n, 3, 3))
    verts[:, 0, :] = np.column_stack([cx, cy, z])
    verts[:, 1, :] = np.column_stack([cx + s, cy, z])
    verts[:, 2, :] = np.column_stack([cx, cy + s, z])
    normals = np.tile([0.0, 0.0, 1.0], (n, 1))
    centroids = np.mean(verts, axis=1)
    areas = 0.5 * s * s * np.ones(n)
    return BodyMesh(vertices=verts, normals=normals, centroids=centroids, areas=areas, name="flat")


def _make_paths() -> PropagationPaths:
    return PropagationPaths.from_powers(
        k_hat=np.array([[0.0, 0.0, -1.0]]),
        power=np.array([1.0]),
    )


# ---------------------------------------------------------------------------
# Subtask A: compute_with_timings returns (DosimetryResult, dict)
# ---------------------------------------------------------------------------


class TestComputeWithTimings:
    def setup_method(self):
        self.engine = DosimetryEngine(SKIN_28GHZ)
        self.body = _make_flat_mesh()
        self.paths = _make_paths()

    def test_returns_tuple(self):
        out = self.engine.compute_with_timings(self.body, self.paths, level=2)
        assert isinstance(out, tuple), "compute_with_timings must return a tuple"
        assert len(out) == 2, "tuple must have exactly 2 elements"

    def test_first_element_is_dosimetry_result(self):
        result, timings = self.engine.compute_with_timings(self.body, self.paths, level=2)
        assert isinstance(result, DosimetryResult)

    def test_second_element_is_dict(self):
        result, timings = self.engine.compute_with_timings(self.body, self.paths, level=2)
        assert isinstance(timings, dict)

    def test_timings_contains_averaging_keys(self):
        result, timings = self.engine.compute_with_timings(self.body, self.paths, level=2)
        assert "avg_build_G_4cm2_ms" in timings
        assert "avg_matvec_4cm2_ms" in timings

    def test_timings_contains_kernel_ms_for_mode(self):
        result, timings = self.engine.compute_with_timings(self.body, self.paths, mode="spatial")
        assert "kernel_ms" in timings

    def test_result_is_correct(self):
        result, timings = self.engine.compute_with_timings(self.body, self.paths, level=2)
        assert result.p_abs > 0
        assert result.fidelity_level == 2

    def test_compute_still_returns_dosimetry_result(self):
        """Legacy compute() must still return DosimetryResult (not a tuple)."""
        result = self.engine.compute(self.body, self.paths, level=2)
        assert isinstance(result, DosimetryResult), "compute() must still return DosimetryResult"

    def test_timings_are_per_call_not_shared(self):
        """Each call to compute_with_timings must return an independent timings dict."""
        _, t1 = self.engine.compute_with_timings(self.body, self.paths, level=2)
        _, t2 = self.engine.compute_with_timings(self.body, self.paths, level=2)
        assert t1 is not t2, "timings dicts from different calls must be distinct objects"

    def test_concurrent_calls_have_independent_timings(self):
        """Concurrent compute_with_timings calls must not share timing state."""
        results = {}
        errors = []

        def run(key):
            try:
                _, timings = self.engine.compute_with_timings(self.body, self.paths, level=2)
                results[key] = timings
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=run, args=(i,)) for i in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Concurrent calls raised: {errors}"
        assert len(results) == 4
        # Each timings dict must be its own object
        timings_ids = {id(v) for v in results.values()}
        assert len(timings_ids) == 4, "Each concurrent call must produce a distinct timings dict"


# ---------------------------------------------------------------------------
# Subtask B: threading locks on curvature and voxel caches
# ---------------------------------------------------------------------------


class TestCurvatureCacheLock:
    def test_lock_exists(self):
        from aegis.viewer.compute import _curvature_cache_lock

        assert isinstance(_curvature_cache_lock, type(threading.Lock()))

    def test_concurrent_curvature_calls_are_safe(self):
        """Multiple threads computing curvature for the same body must not corrupt the cache."""
        from aegis.viewer.compute import _compute_face_curvature

        body = _make_flat_mesh(50)
        results = []
        errors = []

        def run():
            try:
                H = _compute_face_curvature(body)
                results.append(H)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=run) for _ in range(6)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Curvature cache raised: {errors}"
        assert len(results) == 6
        # All results should be numerically identical (same body)
        for H in results[1:]:
            np.testing.assert_array_equal(H, results[0])


class TestVoxelSceneCacheLock:
    def test_lock_exists(self):
        from aegis.viewer.raytracer import _voxel_scene_cache_lock

        assert isinstance(_voxel_scene_cache_lock, type(threading.Lock()))

    def test_clear_voxel_scene_cache_acquires_lock(self):
        """clear_voxel_scene_cache must use the lock (no deadlock, clears dict)."""
        from aegis.viewer.raytracer import _voxel_scene_cache, clear_voxel_scene_cache

        _voxel_scene_cache["test_key"] = object()
        clear_voxel_scene_cache()
        assert len(_voxel_scene_cache) == 0


# ---------------------------------------------------------------------------
# Subtask C: pipeline process isolation
# ---------------------------------------------------------------------------


class TestPipelineIsolation:
    def test_active_processes_is_dict(self):
        from aegis.viewer.pipeline import _active_processes

        assert isinstance(_active_processes, dict)

    def test_pipeline_mutex_exists(self):
        from aegis.viewer.pipeline import _pipeline_mutex

        assert isinstance(_pipeline_mutex, type(threading.Lock()))

    def test_cancel_pipeline_accepts_session_id(self):
        """cancel_pipeline must accept a session_id parameter."""
        from aegis.viewer.pipeline import cancel_pipeline

        # No process registered -> returns False, no exception
        killed = cancel_pipeline(session_id="test-session-abc")
        assert killed is False

    def test_cancel_pipeline_default_session(self):
        """cancel_pipeline with no args uses 'default' session_id."""
        from aegis.viewer.pipeline import cancel_pipeline

        killed = cancel_pipeline()
        assert killed is False

    def test_cancel_pipeline_only_kills_own_session(self):
        """cancel_pipeline for session A must not kill session B's process."""
        # Simulate two processes in the dict with a mock

        from aegis.viewer.pipeline import _active_processes, cancel_pipeline

        class _MockProc:
            """Minimal mock that tracks termination calls."""

            def __init__(self):
                self.terminated = False

            def terminate(self):
                self.terminated = True

            def wait(self, timeout=None):
                pass

            def poll(self):
                return None

        mock_a = _MockProc()
        mock_b = _MockProc()
        _active_processes["session-A"] = mock_a  # type: ignore[assignment]
        _active_processes["session-B"] = mock_b  # type: ignore[assignment]

        try:
            cancel_pipeline(session_id="session-A")
            assert mock_a.terminated, "session-A process should have been terminated"
            assert not mock_b.terminated, "session-B process must not be touched"
            assert "session-A" not in _active_processes
            assert "session-B" in _active_processes
        finally:
            _active_processes.pop("session-A", None)
            _active_processes.pop("session-B", None)

    def test_run_pipeline_busy_when_mutex_locked(self):
        """run_pipeline must yield 'ERROR: pipeline busy' when mutex is already held."""
        from aegis.viewer.pipeline import _pipeline_mutex, run_pipeline

        _pipeline_mutex.acquire()
        try:
            lines = list(
                run_pipeline(
                    location="Test City",
                    radius=30,
                    api_key="fake-key",
                    output_dir=pytest.importorskip("pathlib").Path("/tmp"),
                    session_id="test-busy",
                )
            )
        finally:
            _pipeline_mutex.release()

        assert any("pipeline busy" in line for line in lines)
