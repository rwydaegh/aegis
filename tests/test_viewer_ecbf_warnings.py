"""Tests that ECBF infeasibility warnings are captured and surfaced."""

from __future__ import annotations

import warnings
from types import SimpleNamespace
from unittest.mock import patch

import pytest

pytest.importorskip("flask")

import numpy as np  # noqa: E402
from conftest import make_flat_mesh  # noqa: E402

from aegis.viewer.compute import collect_ecbf_warnings, compute_dosimetry  # noqa: E402
from aegis.viewer.routes.compute._responses import _run_dosimetry  # noqa: E402


def _fake_result(n_triangles: int) -> SimpleNamespace:
    sab = np.zeros(n_triangles, dtype=np.float64)
    return SimpleNamespace(
        sab=sab,
        sab_averaged=None,
        sab_1cm2_averaged=None,
        sinc=None,
        sinc_averaged=None,
        p_abs=0.0,
        peak_sab=0.0,
        fidelity_level=8,
        freq_hz=28e9,
    )


def _build_warning_record(message: str) -> warnings.WarningMessage:
    return warnings.WarningMessage(
        message=UserWarning(message),
        category=UserWarning,
        filename=__file__,
        lineno=1,
    )


class TestCollectEcbfWarnings:
    def test_keeps_ecbf_messages(self):
        out = collect_ecbf_warnings(
            [
                _build_warning_record("ECBF constraint infeasible: minimum achievable P_abs (1 W) exceeds 0.5 W"),
                _build_warning_record("ECBF lambda bracket expansion exceeded 1e20"),
                _build_warning_record("ECBF bisection solver failed"),
            ]
        )
        assert len(out) == 3
        assert all("ECBF" in msg for msg in out)

    def test_keeps_absorption_and_infeasible_messages(self):
        out = collect_ecbf_warnings(
            [
                _build_warning_record("Constraint infeasible at this freq"),
                _build_warning_record("Cannot satisfy absorption budget"),
            ]
        )
        assert len(out) == 2

    def test_drops_unrelated_messages(self):
        out = collect_ecbf_warnings(
            [
                _build_warning_record("RuntimeWarning: divide by zero"),
                _build_warning_record("DeprecationWarning: numpy thing"),
            ]
        )
        assert out == []

    def test_handles_empty_list(self):
        assert collect_ecbf_warnings([]) == []


class TestRunDosimetryCapturesEcbfWarning:
    def test_appends_warning_to_out_list(self):
        body = make_flat_mesh(4)
        tissue = SimpleNamespace(freq_hz=28e9, T0=0.5, eps_r=10.0, sigma=1.5)
        paths = SimpleNamespace(n_paths=1)

        def fake_compute(body, paths, **kw):  # noqa: ARG001
            warnings.warn("ECBF constraint infeasible: minimum achievable P_abs", stacklevel=2)
            return _fake_result(body.n_triangles)

        with patch("aegis.engine.DosimetryEngine") as mock_engine_cls:
            mock_engine_cls.return_value = SimpleNamespace(compute=fake_compute)
            captured: list[str] = []
            result, err = _run_dosimetry(tissue, body, paths, {"level": 8}, ecbf_warnings_out=captured)

        assert err is None
        assert result is not None
        assert len(captured) == 1
        assert "ECBF" in captured[0]

    def test_omits_unrelated_warnings(self):
        body = make_flat_mesh(4)
        tissue = SimpleNamespace(freq_hz=28e9, T0=0.5, eps_r=10.0, sigma=1.5)
        paths = SimpleNamespace(n_paths=1)

        def fake_compute(body, paths, **kw):  # noqa: ARG001
            warnings.warn("RuntimeWarning: deprecated numpy api", stacklevel=2)
            return _fake_result(body.n_triangles)

        with patch("aegis.engine.DosimetryEngine") as mock_engine_cls:
            mock_engine_cls.return_value = SimpleNamespace(compute=fake_compute)
            captured: list[str] = []
            _run_dosimetry(tissue, body, paths, {"level": 2}, ecbf_warnings_out=captured)

        assert captured == []

    def test_no_capture_when_out_list_omitted(self):
        body = make_flat_mesh(4)
        tissue = SimpleNamespace(freq_hz=28e9, T0=0.5, eps_r=10.0, sigma=1.5)
        paths = SimpleNamespace(n_paths=1)

        def fake_compute(body, paths, **kw):  # noqa: ARG001
            warnings.warn("ECBF constraint infeasible", stacklevel=2)
            return _fake_result(body.n_triangles)

        with patch("aegis.engine.DosimetryEngine") as mock_engine_cls:
            mock_engine_cls.return_value = SimpleNamespace(compute=fake_compute)
            result, err = _run_dosimetry(tissue, body, paths, {"level": 8})

        assert err is None
        assert result is not None


class TestComputeDosimetrySurfacesEcbfWarning:
    def test_extra_includes_ecbf_warnings_when_emitted(self):
        body = make_flat_mesh(8)
        antenna_pos = np.array([5.0, 0.0, 0.0])

        def fake_run(*args, **kwargs):  # noqa: ARG001
            warnings.warn(
                "ECBF constraint infeasible: minimum achievable P_abs (1.5 W) exceeds 0.5 W",
                stacklevel=2,
            )
            return _fake_result(body.n_triangles), {}

        with patch("aegis.viewer.compute._run_engine_compute", side_effect=fake_run):
            _, _, _, _, _, _, extra = compute_dosimetry(body, antenna_pos=antenna_pos, level=8, power_dbm=43.0)

        assert "ecbf_warnings" in extra
        assert len(extra["ecbf_warnings"]) == 1
        assert "infeasible" in extra["ecbf_warnings"][0]

    def test_extra_omits_ecbf_warnings_when_clean(self):
        body = make_flat_mesh(8)
        antenna_pos = np.array([5.0, 0.0, 0.0])

        def fake_run(*args, **kwargs):  # noqa: ARG001
            return _fake_result(body.n_triangles), {}

        with patch("aegis.viewer.compute._run_engine_compute", side_effect=fake_run):
            _, _, _, _, _, _, extra = compute_dosimetry(body, antenna_pos=antenna_pos, level=2, power_dbm=43.0)

        assert "ecbf_warnings" not in extra
