"""Test whether the missing range term explains the two estimators' disagreement.

The study reports the same quantity twice and gets two answers. Next event
estimation says the bounces add +0.30 to +0.57 dB over line of sight. The
escape-weighted estimator the study used before says +1.10 to +2.63 dB for the
same ratio at the same squares.

The proposed reason is a missing term, not a bug. Next event connects a path
vertex to an explicit rooftop point and divides by the range between them, so a
bounce that happens far from the roofline is charged for the extra distance. The
escape estimator credits a ray the moment it leaves the crop and has no range
anywhere, so a bounced ray that travelled 120 m to reach the sky counts exactly
as much as a direct ray that travelled 30 m. The bounced term is therefore not
discounted and the surplus comes out high.

If that is the reason, then charging each escaping ray for the distance it
travelled should move the escape answer toward the next event one. If it is not
the reason, the charge will change little and something else is going on.

**It is not the reason.** Measured on 3 August over ten standpoints per site at
250 m: Korenmarkt moves from +1.79 to +1.65 dB and Brussels from +1.79 to
+1.44 dB. That is 0.13 and 0.35 dB against a gap to next event of about 1.3 dB,
so the range term is at most a quarter of the disagreement and at Korenmarkt
nearer a tenth. The result is kept because a mechanism that was going to be
asserted in the paper turns out to be a minor term, and that is worth printing.

What is left is what the two estimators take the sources to be. The escape
estimator assumes sites of uniform areal density in a band 13.5 to 43.5 m above
the head and 25 to 250 m out, which fills whatever sky is visible from wherever
you ask. Next event uses the square's own measured roofline, which is a thin
rim at a fixed elevation. A ray that bounced up a wall escapes from higher up
and sees more sky, so the assumed population credits it and the measured rim
does not. Two measurements already point the same way: every azimuth at both
squares carries a roofline, so the gap is not the assumed sources filling empty
directions; and pooled within site, the escape surplus moves -6.04 dB per unit
sky fraction against next event's -0.70.

This runs the same standpoints twice, once each way, and prints all three
numbers side by side. It changes no published output: the charge is off by
default in :class:`TraceConfig` and this script is the only caller that turns it
on.

The charge is a proxy and is described as one. The escape estimator still puts
the source population at infinity, so ``l_K`` is the distance the ray travelled
inside the crop rather than a distance to any source. What it captures is the
one thing that matters here: a bounced path is longer than a direct one, and the
spread of those lengths is what a range term would price.

Run from the ``semantic_twin`` directory::

    ../../../.venv/bin/python measure_escape_range_term.py
    ../../../.venv/bin/python measure_escape_range_term.py --sites korenmarkt --locations 8
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
from semantic_twin.transport.tracer import SbrTracer, TraceConfig
from semantic_twin.walk.ground import measure_ground_datum

ROOT = paths.root()
CONFIG = paths.config_dir()


def surplus_db(result: object, model: str) -> float:
    """``(direct + bounced) / direct`` in decibels, from one traced point."""
    whole = result.susceptibility[model]  # type: ignore[attr-defined]
    line = result.susceptibility_direct[model]  # type: ignore[attr-defined]
    return 10.0 * np.log10(whole / line) if line > 0.0 else float("nan")


def trace_both_ways(site: str, args: Any) -> dict[str, object]:
    geometry = MitsubaGeometry(paths.site_mesh(site, args.crop_m), variant=args.variant)
    datum = measure_ground_datum(geometry, radius_m=args.walk_radius_m)
    walk, provenance = site_walk(geometry, site, stride_m=args.walk_stride_m)
    points = np.asarray(walk.points)
    take = np.linspace(0, points.shape[0] - 1, min(args.locations, points.shape[0])).round().astype(int)
    points = points[take]
    print(f"{site:24s} {points.shape[0]} standpoints on the capture route", flush=True)

    face_class = classify_faces(geometry.vertices, geometry.faces, datum.z_m)
    binding = load_table(CONFIG, args.frequency_hz)
    models = {"isotropic": ISOTROPIC, "rooftop": ROOFTOP}

    plain, charged = [], []
    for index, point in enumerate(points):
        for weighted, into in ((False, plain), (True, charged)):
            config = TraceConfig(
                frequency_hz=args.frequency_hz,
                rays=args.rays,
                max_bounces=args.max_bounces,
                range_weighted_escape=weighted,
                seed=args.seed + index,
            )
            tracer = SbrTracer(geometry, face_class, binding.permittivity, binding.rms_height_m, config)
            result = tracer.trace(point, models, ground_z_m=datum.z_m, seed=args.seed + index)
            into.append(surplus_db(result, "rooftop"))
        if index % 5 == 0:
            print(f"  [{index + 1}/{points.shape[0]}] plain {plain[-1]:+.2f} charged {charged[-1]:+.2f}", flush=True)

    plain, charged = np.array(plain), np.array(charged)
    return {
        "site": site,
        "standpoints": int(points.shape[0]),
        "walk": provenance,
        "escape_surplus_db_median": float(np.nanmedian(plain)),
        "escape_surplus_db_p5": float(np.nanpercentile(plain, 5)),
        "escape_surplus_db_p95": float(np.nanpercentile(plain, 95)),
        "range_charged_surplus_db_median": float(np.nanmedian(charged)),
        "range_charged_surplus_db_p5": float(np.nanpercentile(charged, 5)),
        "range_charged_surplus_db_p95": float(np.nanpercentile(charged, 95)),
        "per_point": [
            {"escape_db": float(a), "range_charged_db": float(b)} for a, b in zip(plain, charged, strict=True)
        ],
    }


def run(args: Any) -> None:

    started = time.perf_counter()
    rows = [trace_both_ways(site, args) for site in args.sites]

    print()
    print(f"{'site':24s} {'escape':>10s} {'charged':>10s} {'moved':>8s}")
    for row in rows:
        moved = row["range_charged_surplus_db_median"] - row["escape_surplus_db_median"]
        print(
            f"{row['site']:24s} {row['escape_surplus_db_median']:+10.2f} "
            f"{row['range_charged_surplus_db_median']:+10.2f} {moved:+8.2f}"
        )

    out = ROOT / "outputs" / "next_event" / "escape_range_term.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"rows": rows, "seconds": time.perf_counter() - started}, indent=2) + "\n")
    print(f"\nwrote {out.relative_to(ROOT)}")
