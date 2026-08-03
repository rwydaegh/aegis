"""Does pinning Dr.Jit to one thread per worker recover the pool's scaling.

``dr.thread_count()`` defaults to the core count, so ``trace_standpoints``
spawning ``os.cpu_count()`` processes gives cores squared threads on cores. The
measured scaling is 1.30x from one worker to four on four cores, which is what
a saturated machine looks like: one worker already uses every core.

If the internal threading is what the pool is fighting, pinning each worker to a
single Dr.Jit thread should recover close to linear scaling in the worker count.
If it does not, the ceiling is somewhere else and the pool is not the problem.

The pinned run patches ``_worker_setup`` rather than the module under test, so
nothing in the repository changes to take this measurement.
"""

from __future__ import annotations

import argparse
import os
import pathlib
import sys
import time

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))


_ORIGINAL_SETUP = None


def pinned_setup(worker_tracer, worker_models):
    """Module level so ``spawn`` can pickle it. A closure cannot cross that boundary."""
    import drjit as worker_dr

    from semantic_twin.propagation import tracer as worker_tracer_module

    worker_dr.set_thread_count(1)
    # The child imports this module fresh, so a module global set in the parent
    # arrives as None. The child's own tracer module is unpatched, so its
    # _worker_setup is the original.
    return worker_tracer_module._worker_setup(worker_tracer, worker_models)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mesh", required=True)
    parser.add_argument("--rays", type=int, default=200_000)
    parser.add_argument("--standpoints", type=int, default=12)
    parser.add_argument("--workers", type=int, nargs="+", default=[1, 2, 4])
    parser.add_argument("--ground-z", type=float, default=51.0234375)
    args = parser.parse_args()

    import drjit as dr

    from semantic_twin.propagation import tracer as tracer_module
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

    global _ORIGINAL_SETUP
    original = tracer_module._worker_setup
    _ORIGINAL_SETUP = original

    print(f"cores {os.cpu_count()}, drjit default threads {dr.thread_count()}, {args.standpoints} standpoints")
    for label, setup in (("as shipped", original), ("pinned to 1", pinned_setup)):
        tracer_module._worker_setup = setup
        for workers in args.workers:
            started = time.perf_counter()
            rows = list(trace_standpoints(tracer, standpoints, models, workers=workers))
            seconds = time.perf_counter() - started
            print(
                f"  {label:12s} workers={workers:2d}  {seconds:7.2f} s  "
                f"{args.standpoints / seconds:6.3f} standpoints/s  "
                f"sky sum {sum(r[1].sky_fraction for r in rows):.9f}",
                flush=True,
            )
    tracer_module._worker_setup = original


if __name__ == "__main__":
    main()
