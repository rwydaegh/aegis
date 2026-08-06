"""Diagnostic benchmark for separate and batched body coupling.

The benchmark consumes stored angular spectra and compares one
``BodyCoupler.couple`` call per spectrum with ``BodyCoupler.couple_many``.  It
is deliberately separate from the exposure runner: it measures the adapter's
execution cost and does not trace a scene or write production exposure rows.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import pathlib
import platform
import time
from collections.abc import Callable, Sequence
from importlib import metadata
from typing import Any

import numpy as np

from semantic_twin import paths

from .coupler import BodyCoupler

SCHEMA = "walk-body-batching-benchmark-v1"
PHANTOM_MASS_KG = 72.4
FREQUENCY_HZ = 15.0e9
REFERENCE_S0_W_M2 = 1.0

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]
DEFAULT_RUNS = PROJECT_ROOT / "outputs" / "angular_convergence_4096_atlas_v2" / "runs"
DEFAULT_SPECTRA = tuple(DEFAULT_RUNS / f"cells4096_rays1600000_seed{seed}" / "spectra.npz" for seed in (7, 8, 9))
DEFAULT_OUTPUT = PROJECT_ROOT / "outputs" / "benchmarks" / "walk_body_batching.json"
_DEFAULT_COUPLER_FACTORY = BodyCoupler


@dataclasses.dataclass(frozen=True)
class BodyBenchmarkConfig:
    """Inputs and execution options for one diagnostic benchmark."""

    spectra: tuple[pathlib.Path, ...]
    point: int = 0
    repeat: int = 2
    chunk_cells: int = 512
    phantom: pathlib.Path | None = None
    frequency_hz: float = FREQUENCY_HZ
    body_mass_kg: float = PHANTOM_MASS_KG
    reference_s0_w_m2: float = REFERENCE_S0_W_M2

    def __post_init__(self) -> None:
        object.__setattr__(self, "spectra", tuple(pathlib.Path(path) for path in self.spectra))
        if self.phantom is not None:
            object.__setattr__(self, "phantom", pathlib.Path(self.phantom))


@dataclasses.dataclass(frozen=True)
class SpectrumBatch:
    """The selected spectra and shared angular geometry loaded from disk."""

    local_grid: np.ndarray
    spectra: np.ndarray
    solid_angle: float
    inputs: tuple[dict[str, object], ...]


def _file_sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _version(name: str) -> str:
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return "unavailable"


def _load_batch(paths_to_spectra: Sequence[pathlib.Path], point: int) -> SpectrumBatch:
    grids: list[np.ndarray] = []
    spectra: list[np.ndarray] = []
    solid_angles: list[float] = []
    input_records: list[dict[str, object]] = []
    for path in paths_to_spectra:
        resolved = pathlib.Path(path).resolve()
        with np.load(resolved) as artifact:
            grid = np.asarray(artifact["local_grid"], dtype=np.float64)
            rho = np.asarray(artifact["rho_rooftop"], dtype=np.float64)
            solid_angle = float(artifact["solid_angle"])
            index = np.asarray(artifact["index"], dtype=np.int64)
        if not 0 <= point < rho.shape[0]:
            raise IndexError(f"point {point} is outside {resolved}")
        grids.append(grid)
        spectra.append(rho[point])
        solid_angles.append(solid_angle)
        input_records.append(
            {
                "path": str(resolved),
                "sha256": _file_sha256(resolved),
                "stored_index": int(index[point]),
            }
        )
    if not spectra:
        raise ValueError("at least one spectrum is required")
    if any(not np.array_equal(grid, grids[0]) for grid in grids[1:]):
        raise ValueError("input spectra use different angular grids")
    if any(value != solid_angles[0] for value in solid_angles[1:]):
        raise ValueError("input spectra use different solid angles")
    return SpectrumBatch(grids[0], np.stack(spectra), solid_angles[0], tuple(input_records))


def _default_phantom() -> pathlib.Path:
    return paths.aegis_data_dir() / "duke.stl"


def _couple_and_time(
    coupler: Any,
    batch: SpectrumBatch,
    config: BodyBenchmarkConfig,
) -> tuple[list[float], list[float], tuple[Any, ...], tuple[Any, ...]]:
    separate_times: list[float] = []
    batched_times: list[float] = []
    expected: tuple[Any, ...] = ()
    actual: tuple[Any, ...] = ()
    for _ in range(config.repeat):
        started = time.perf_counter()
        expected = tuple(
            coupler.couple(batch.local_grid, rho, batch.solid_angle, config.reference_s0_w_m2) for rho in batch.spectra
        )
        separate_times.append(time.perf_counter() - started)

        started = time.perf_counter()
        actual = coupler.couple_many(
            batch.local_grid,
            batch.spectra,
            batch.solid_angle,
            config.reference_s0_w_m2,
            chunk_cells=config.chunk_cells,
        )
        batched_times.append(time.perf_counter() - started)
    if not expected or not actual:
        raise AssertionError("benchmark did not execute")
    return separate_times, batched_times, expected, actual


def _absolute_errors(expected: tuple[Any, ...], actual: tuple[Any, ...]) -> dict[str, float]:
    if len(expected) != len(actual):
        raise ValueError("separate and batched coupling returned different result counts")
    fields = dataclasses.fields(expected[0])
    return {
        field.name: max(
            abs(float(getattr(left, field.name)) - float(getattr(right, field.name)))
            for left, right in zip(actual, expected, strict=True)
        )
        for field in fields
    }


def benchmark(
    config: BodyBenchmarkConfig,
    *,
    coupler: Any | None = None,
    coupler_factory: Callable[..., Any] | None = None,
    benchmark_source: pathlib.Path | None = None,
) -> dict[str, object]:
    """Run the benchmark and return its JSON-compatible report.

    ``coupler`` and ``coupler_factory`` are injection points for a small
    synthetic fixture. The normal CLI leaves both unset, which constructs the
    configured AEGIS ``BodyCoupler`` and therefore retains the production
    diagnostic behaviour without requiring a GPU.
    """
    if config.repeat < 1:
        raise ValueError("repeat must be positive")
    if config.chunk_cells < 1:
        raise ValueError("chunk_cells must be positive")
    batch = _load_batch(config.spectra, config.point)
    if coupler is not None and coupler_factory is not None:
        raise ValueError("pass either coupler or coupler_factory, not both")
    if coupler is None:
        factory = coupler_factory or BodyCoupler
        phantom = config.phantom
        if phantom is None:
            phantom = _default_phantom() if factory is _DEFAULT_COUPLER_FACTORY else pathlib.Path("duke.stl")
        coupler = factory(str(phantom), config.frequency_hz, body_mass_kg=config.body_mass_kg)

    separate_times, batched_times, expected, actual = _couple_and_time(coupler, batch, config)
    separate_median = float(np.median(separate_times))
    batched_median = float(np.median(batched_times))
    source = pathlib.Path(benchmark_source or pathlib.Path(__file__)).resolve()
    return {
        "schema": SCHEMA,
        "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "host": platform.node(),
        "platform": platform.platform(),
        "python": platform.python_version(),
        "versions": {name: _version(name) for name in ("numpy", "aegis", "aegis-semantic-twin")},
        "source_sha256": {
            "benchmark": _file_sha256(source),
            "body_coupler": _file_sha256(PROJECT_ROOT / "semantic_twin" / "exposure" / "coupler.py"),
            "row_execution": _file_sha256(PROJECT_ROOT / "semantic_twin" / "exposure" / "execution.py"),
        },
        "inputs": list(batch.inputs),
        "spectra": int(batch.spectra.shape[0]),
        "cells": int(batch.spectra.shape[1]),
        "body_triangles": int(coupler.body.n_triangles),
        "repeat": int(config.repeat),
        "chunk_cells": int(config.chunk_cells),
        "separate_seconds": separate_times,
        "batched_seconds": batched_times,
        "separate_median_seconds": separate_median,
        "batched_median_seconds": batched_median,
        "speedup": separate_median / batched_median,
        "maximum_absolute_error_by_field": _absolute_errors(expected, actual),
    }


def write_report(report: dict[str, object], output: pathlib.Path) -> None:
    """Write one report atomically so an interrupted diagnostic never wins."""
    output = pathlib.Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n")
    temporary.replace(output)
