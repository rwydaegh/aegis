from __future__ import annotations

import json
from types import SimpleNamespace

import numpy as np

from semantic_twin.exposure import BodyExposure
from semantic_twin.exposure.body_benchmark import (
    SCHEMA,
    BodyBenchmarkConfig,
    benchmark,
    write_report,
)
from semantic_twin.cli.body_benchmark import arguments, config_from_args


class _SyntheticCoupler:
    def __init__(self) -> None:
        self.body = SimpleNamespace(n_triangles=3)

    @staticmethod
    def _couple(rho: np.ndarray, solid_angle: float, reference: float) -> BodyExposure:
        arriving = float(np.sum(rho * solid_angle * reference))
        return BodyExposure(
            reference, arriving, arriving / reference, arriving + 1.0, arriving / 3.0, arriving * 2.0, arriving
        )

    def couple(self, _grid: np.ndarray, rho: np.ndarray, solid_angle: float, reference: float) -> BodyExposure:
        return self._couple(rho, solid_angle, reference)

    def couple_many(
        self,
        _grid: np.ndarray,
        spectra: np.ndarray,
        solid_angle: float,
        reference: float,
        *,
        chunk_cells: int,
    ) -> tuple[BodyExposure, ...]:
        assert chunk_cells == 2
        return tuple(self._couple(rho, solid_angle, reference) for rho in spectra)


def test_synthetic_benchmark_pins_schema_and_cli_options(tmp_path) -> None:
    path = tmp_path / "synthetic.npz"
    np.savez(
        path,
        local_grid=np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0], [-1.0, 0.0, 0.0]]),
        rho_rooftop=np.array([[0.1, 0.2, 0.3, 0.4], [0.4, 0.3, 0.2, 0.1]]),
        solid_angle=0.5,
        index=np.array([17, 23]),
    )
    args = arguments(
        [
            "--spectra",
            str(path),
            "--point",
            "1",
            "--repeat",
            "1",
            "--chunk-cells",
            "2",
        ]
    )
    config = config_from_args(args)
    report = benchmark(config, coupler=_SyntheticCoupler())

    assert report["schema"] == SCHEMA
    assert report["inputs"][0]["stored_index"] == 23
    assert report["spectra"] == 1
    assert report["cells"] == 4
    assert report["body_triangles"] == 3
    assert report["repeat"] == 1
    assert report["chunk_cells"] == 2
    assert report["speedup"] > 0.0
    assert all(error == 0.0 for error in report["maximum_absolute_error_by_field"].values())

    output = tmp_path / "report.json"
    write_report(report, output)
    assert json.loads(output.read_text()) == report


def test_invalid_benchmark_options_fail_before_coupling(tmp_path) -> None:
    config = BodyBenchmarkConfig((tmp_path / "missing.npz",), repeat=0)
    try:
        benchmark(config, coupler=_SyntheticCoupler())
    except ValueError as error:
        assert str(error) == "repeat must be positive"
    else:
        raise AssertionError("invalid repeat was accepted")
