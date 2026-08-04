"""How much of the multipath surplus is the square, and how much is the seed.

The study reports one number per square: the bounces add +0.30 dB at one and
+0.57 dB at another. Those came from one run each. A ratio of two Monte Carlo
estimates has a spread, and a difference of 0.27 dB between two squares means
nothing until the spread is smaller than that.

This runs the same pilot squares over several seeds and reports the spread. The
seed moves three things at once, which is what makes it the right knob: the ray
directions, the roulette draws, and which rooftop point each vertex connects to.
Everything else, the walk and the source set, is fixed by the site.

What to read: if the seed-to-seed standard deviation is well under the gap
between the squares, the ranking is real. If it is comparable, the study can
report the pooled number and not the ordering.

Run from the ``semantic_twin`` directory::

    ../../../.venv/bin/python measure_surplus_spread.py
    ../../../.venv/bin/python measure_surplus_spread.py --seeds 5 --locations 8
"""

from __future__ import annotations

from typing import Any

import json
import time

import numpy as np

from semantic_twin import paths
from semantic_twin.illumination import ISOTROPIC, ROOFTOP
from semantic_twin.propagation.geometry import MitsubaGeometry
from semantic_twin.walk.site import site_walk
from semantic_twin.materials import classify_faces, load_table
from semantic_twin.illumination.roofline import silhouette
from semantic_twin.illumination.sources import build_source_set
from semantic_twin.transport.tracer import SbrTracer, TraceConfig
from semantic_twin.transport.next_event import NextEventEstimator
from semantic_twin.walk.ground import measure_ground_datum

ROOT = paths.root()
CONFIG = paths.config_dir()


def one_seed(site: str, seed: int, args: Any) -> float:
    """The median surplus over the held out standpoints, at one seed."""
    geometry = MitsubaGeometry(paths.site_mesh(site, args.crop_m), variant=args.variant)
    datum = measure_ground_datum(geometry, radius_m=args.walk_radius_m)
    walk, _ = site_walk(geometry, site, stride_m=args.walk_stride_m)
    points = np.asarray(walk.points)

    # The split is fixed by the site, not by the seed, so what moves between
    # runs is the estimator and nothing about which standpoints were asked.
    order = np.random.default_rng(0).permutation(points.shape[0])
    held = max(2, round(points.shape[0] * args.held_out_fraction))
    evaluate, pool = points[order[:held]], points[order[held:]]
    index = np.linspace(0, pool.shape[0] - 1, min(args.builders, pool.shape[0])).round().astype(int)

    sources = build_source_set(
        geometry,
        pool[index],
        silhouette,
        azimuths=args.azimuths,
        elevations=args.elevations,
        cell_m=args.cell_m,
        site_lift_m=args.site_lift_m,
    )
    face_class = classify_faces(geometry.vertices, geometry.faces, datum.z_m)
    binding = load_table(CONFIG, args.frequency_hz)
    config = TraceConfig(
        frequency_hz=args.frequency_hz,
        rays=args.rays,
        max_bounces=args.max_bounces,
        seed=seed,
    )
    tracer = SbrTracer(geometry, face_class, binding.permittivity, binding.rms_height_m, config)

    estimator = NextEventEstimator(
        tracer=tracer,
        geometry=geometry,
        sources=sources,
        samples=args.connections,
        max_order=args.max_bounces,
        diagnostic_models={"isotropic": ISOTROPIC, "rooftop": ROOFTOP},
    )
    surplus = []
    for i, origin in enumerate(evaluate):
        result = estimator.estimate(
            origin,
            ground_z_m=datum.z_m,
            seed=seed + i,
        )
        surplus.append(10.0 * np.log10(result.surplus) if result.direct > 0.0 else np.nan)
    return float(np.nanmedian(surplus))


def run(args: Any) -> None:

    started = time.perf_counter()
    rows = []
    for site in args.sites:
        values = []
        for seed in range(7, 7 + args.seeds):
            values.append(one_seed(site, seed, args))
            print(f"{site:24s} seed {seed}  {values[-1]:+.3f} dB", flush=True)
        values = np.array(values)
        rows.append(
            {
                "site": site,
                "seeds": args.seeds,
                "surplus_db_mean": float(values.mean()),
                "surplus_db_std": float(values.std(ddof=1)) if values.size > 1 else 0.0,
                "surplus_db_min": float(values.min()),
                "surplus_db_max": float(values.max()),
                "per_seed_db": values.tolist(),
            }
        )

    print()
    print(f"{'site':24s} {'mean':>8s} {'sd':>8s} {'range':>16s}")
    for row in rows:
        print(
            f"{row['site']:24s} {row['surplus_db_mean']:+8.3f} {row['surplus_db_std']:8.3f} "
            f"{row['surplus_db_min']:+7.3f} to {row['surplus_db_max']:+.3f}"
        )
    if len(rows) == 2:
        gap = abs(rows[0]["surplus_db_mean"] - rows[1]["surplus_db_mean"])
        worst = max(r["surplus_db_std"] for r in rows)
        print(f"\ngap between the squares {gap:.3f} dB, worst seed spread {worst:.3f} dB")

    out = ROOT / "outputs" / "next_event" / "surplus_seed_spread.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"rows": rows, "seconds": time.perf_counter() - started}, indent=2) + "\n")
    print(f"wrote {out.relative_to(ROOT)}")
