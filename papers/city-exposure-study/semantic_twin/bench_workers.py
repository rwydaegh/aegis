"""Eight worker processes, each starting Dr.Jit's own thread pool, on eight cores.

``trace_standpoints`` spawns ``os.cpu_count()`` processes and every one of them
loads the mesh into an LLVM backend that threads internally. The question is
whether the second level of parallelism is buying anything or only contending,
and the way to answer it is throughput in standpoints per second rather than
load average.

Dr.Jit's thread count is set per process, so the sweep runs the cross product of
worker count and per worker thread count and reports the best.
"""

from __future__ import annotations

import argparse
import os
import pathlib
import sys
import time

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mesh", required=True)
    parser.add_argument("--rays", type=int, default=200_000)
    parser.add_argument("--standpoints", type=int, default=16)
    parser.add_argument("--workers", type=int, nargs="+", default=[1, 2, 4, 8])
    parser.add_argument("--threads", type=int, nargs="+", default=[0])
    parser.add_argument("--ground-z", type=float, default=51.0234375)
    args = parser.parse_args()

    from semantic_twin.propagation.directions import ISOTROPIC, ROOFTOP, STREET_SMALL_CELL
    from semantic_twin.propagation.geometry import MitsubaGeometry
    from semantic_twin.propagation.tracer import (
        DEFAULT_MAX_BOUNCES,
        SbrTracer,
        TraceConfig,
        trace_standpoints,
    )

    models = {"isotropic": ISOTROPIC, "rooftop": ROOFTOP, "street_small_cell": STREET_SMALL_CELL}
    geometry = MitsubaGeometry(args.mesh)
    faces = geometry.faces.shape[0]
    tracer = SbrTracer(
        geometry,
        np.zeros(faces, dtype=np.int64),
        np.array([complex(5.31, -0.24)], dtype=np.complex128),
        np.array([0.0015], dtype=np.float64),
        TraceConfig(rays=args.rays, batch=args.rays, max_bounces=DEFAULT_MAX_BOUNCES, seed=7),
    )

    rng = np.random.default_rng(3)
    angle = rng.uniform(0.0, 2.0 * np.pi, args.standpoints)
    radius = 30.0 * np.sqrt(rng.uniform(0.0, 1.0, args.standpoints))
    points = np.column_stack(
        [radius * np.cos(angle), radius * np.sin(angle), np.full(args.standpoints, 52.5)]
    )
    standpoints = [(p, args.ground_z, 7 + i) for i, p in enumerate(points)]

    print(f"cores {os.cpu_count()}, {args.standpoints} standpoints, {args.rays} rays")
    for threads in args.threads:
        if threads:
            os.environ["DRJIT_NUM_THREADS"] = str(threads)
        label = f"threads={threads or 'default'}"
        for workers in args.workers:
            started = time.perf_counter()
            rows = list(trace_standpoints(tracer, standpoints, models, workers=workers))
            seconds = time.perf_counter() - started
            checksum = sum(r[1].sky_fraction for r in rows)
            print(
                f"  {label:18s} workers={workers:2d}  {seconds:7.2f} s  "
                f"{args.standpoints / seconds:6.3f} standpoints/s  sky sum {checksum:.9f}",
                flush=True,
            )


if __name__ == "__main__":
    main()
