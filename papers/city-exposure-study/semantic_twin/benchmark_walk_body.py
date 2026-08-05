"""Benchmark separate and batched body coupling on stored Korenmarkt spectra."""

from __future__ import annotations

import argparse
import dataclasses
import json
import pathlib
import platform
import time
from importlib import metadata

import numpy as np

from semantic_twin.exposure import BodyCoupler
from semantic_twin.exposure.angular_convergence import file_sha256
from semantic_twin.exposure.study import PHANTOM, PHANTOM_MASS_KG

ROOT = pathlib.Path(__file__).resolve().parent
DEFAULT_RUNS = ROOT / "outputs" / "angular_convergence_4096_atlas_v2" / "runs"
DEFAULT_SPECTRA = tuple(DEFAULT_RUNS / f"cells4096_rays1600000_seed{seed}" / "spectra.npz" for seed in (7, 8, 9))


def arguments(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spectra", type=pathlib.Path, nargs="+", default=DEFAULT_SPECTRA)
    parser.add_argument("--point", type=int, default=0, help="row within each stored full-walk spectrum")
    parser.add_argument("--repeat", type=int, default=2)
    parser.add_argument("--chunk-cells", type=int, default=512)
    parser.add_argument(
        "--output",
        type=pathlib.Path,
        default=ROOT / "outputs" / "benchmarks" / "walk_body_batching.json",
    )
    return parser.parse_args(argv)


def _version(name: str) -> str:
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return "unavailable"


def run(args: argparse.Namespace) -> dict[str, object]:
    if args.repeat < 1:
        raise ValueError("repeat must be positive")
    grids: list[np.ndarray] = []
    spectra: list[np.ndarray] = []
    solid_angles: list[float] = []
    input_records: list[dict[str, object]] = []
    for path in args.spectra:
        resolved = path.resolve()
        with np.load(resolved) as artifact:
            grid = np.asarray(artifact["local_grid"], dtype=np.float64)
            rho = np.asarray(artifact["rho_rooftop"], dtype=np.float64)
            solid_angle = float(artifact["solid_angle"])
            index = np.asarray(artifact["index"], dtype=np.int64)
        if not 0 <= args.point < rho.shape[0]:
            raise IndexError(f"point {args.point} is outside {resolved}")
        grids.append(grid)
        spectra.append(rho[args.point])
        solid_angles.append(solid_angle)
        input_records.append(
            {
                "path": str(resolved),
                "sha256": file_sha256(resolved),
                "stored_index": int(index[args.point]),
            }
        )
    if not spectra:
        raise ValueError("at least one spectrum is required")
    if any(not np.array_equal(grid, grids[0]) for grid in grids[1:]):
        raise ValueError("input spectra use different angular grids")
    if any(value != solid_angles[0] for value in solid_angles[1:]):
        raise ValueError("input spectra use different solid angles")

    coupler = BodyCoupler(PHANTOM, 15.0e9, body_mass_kg=PHANTOM_MASS_KG)
    values = np.stack(spectra)
    grid = grids[0]
    solid_angle = solid_angles[0]

    separate_times: list[float] = []
    batched_times: list[float] = []
    expected = None
    actual = None
    for _ in range(args.repeat):
        started = time.perf_counter()
        expected = tuple(coupler.couple(grid, rho, solid_angle, 1.0) for rho in values)
        separate_times.append(time.perf_counter() - started)

        started = time.perf_counter()
        actual = coupler.couple_many(grid, values, solid_angle, 1.0, chunk_cells=args.chunk_cells)
        batched_times.append(time.perf_counter() - started)
    if expected is None or actual is None:
        raise AssertionError("benchmark did not execute")
    absolute_error = {
        field.name: max(
            abs(float(getattr(left, field.name)) - float(getattr(right, field.name)))
            for left, right in zip(actual, expected, strict=True)
        )
        for field in dataclasses.fields(expected[0])
    }
    separate_median = float(np.median(separate_times))
    batched_median = float(np.median(batched_times))
    return {
        "schema": "walk-body-batching-benchmark-v1",
        "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "host": platform.node(),
        "platform": platform.platform(),
        "python": platform.python_version(),
        "versions": {name: _version(name) for name in ("numpy", "aegis", "aegis-semantic-twin")},
        "source_sha256": {
            "benchmark": file_sha256(pathlib.Path(__file__)),
            "body_coupler": file_sha256(ROOT / "semantic_twin" / "exposure" / "coupler.py"),
            "row_execution": file_sha256(ROOT / "semantic_twin" / "exposure" / "execution.py"),
        },
        "inputs": input_records,
        "spectra": int(values.shape[0]),
        "cells": int(values.shape[1]),
        "body_triangles": int(coupler.body.n_triangles),
        "repeat": int(args.repeat),
        "chunk_cells": int(args.chunk_cells),
        "separate_seconds": separate_times,
        "batched_seconds": batched_times,
        "separate_median_seconds": separate_median,
        "batched_median_seconds": batched_median,
        "speedup": separate_median / batched_median,
        "maximum_absolute_error_by_field": absolute_error,
    }


def main(argv: list[str] | None = None) -> int:
    args = arguments(argv)
    report = run(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    temporary.write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n")
    temporary.replace(args.output)
    print(json.dumps(report, indent=2, sort_keys=True))
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
