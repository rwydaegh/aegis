"""What did correcting the elevation law cost, and does the crop finding survive?

The rooftop and small cell models were re derived on 2026-08-02. The old pair
put a fixed site height into a `1/sin^3(el)` weight and then widened the
support using a height band that the weight knows nothing about. The corrected
pair takes the height band and the range band as the model and derives both the
shape and the support from them. MONOSTATIC_SBR.md section 2.7.

Every directional number produced before that date is under the old law, and the
two are not close: the old rooftop model puts 62 percent of its measure below 5
degrees of elevation and the corrected one puts 9 percent. Since the crop radius
finding is a statement about power arriving near the horizon, the correction
could plausibly erase it, shrink it or leave it alone, and which of those it
does is a measurement.

The measurement is cheap because it needs no extra tracing. One trace deposits
into every model at once, so tracing a site with all seven variants attached
gives the old law and the new one from the same rays and the same seed, with
their difference free of Monte Carlo noise between them.

    python run_law_comparison.py --site korenmarkt --crops 130 250
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time

import numpy as np

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from semantic_twin.exposure.study import GROUND_DATUM_M, ground_datum, site_mesh  # noqa: E402
from semantic_twin.propagation import (  # noqa: E402
    DEFAULT_MAX_BOUNCES,
    VARIANTS,
    MitsubaGeometry,
    SbrTracer,
    TraceConfig,
)
from semantic_twin.materials import classify_faces, load_table  # noqa: E402
from semantic_twin.walk.grid import build_walk  # noqa: E402
from semantic_twin.walk.model import stratified_subset  # noqa: E402

CONFIG = SCRIPT_DIR / "config"
OUTPUT = SCRIPT_DIR / "outputs" / "law_comparison"

#: Corrected model -> the model it replaces. Only these pairs are comparable,
#: because only these differ in the law and in nothing else.
PAIRS = {"rooftop": "rooftop_fixed_height", "street_small_cell": "street_small_cell_fixed_height"}


def trace_site(site: str, crop_m: int, args: argparse.Namespace) -> dict[str, np.ndarray]:
    """Susceptibility under every variant, at standpoints held fixed across crops.

    The standpoints come from the smallest crop in the sweep so that changing
    the radius changes only the surroundings. A walk rebuilt per radius would
    move the observers as well, and the two effects are not separable after
    the fact.
    """
    mesh = site_mesh(site, crop_m)
    geometry = MitsubaGeometry(mesh)
    datum = GROUND_DATUM_M if site == "korenmarkt" else ground_datum(geometry)
    face_class = classify_faces(geometry.vertices, geometry.faces, datum)
    binding = load_table(CONFIG, args.frequency_hz)
    config = TraceConfig(
        frequency_hz=args.frequency_hz,
        rays=args.rays,
        local_cells=512,
        max_bounces=DEFAULT_MAX_BOUNCES,
        seed=args.seed,
    )
    tracer = SbrTracer(geometry, face_class, binding.permittivity, binding.rms_height_m, config)

    anchor = MitsubaGeometry(site_mesh(site, args.anchor_crop_m))
    anchor_datum = GROUND_DATUM_M if site == "korenmarkt" else ground_datum(anchor)
    walk = build_walk(anchor, ground_datum_m=anchor_datum, radius_m=args.walk_radius_m, spacing_m=3.0, seed=args.seed)
    picks = stratified_subset(walk, args.locations)
    points, datums = walk.points[picks], walk.ground_z_m[picks]

    rows = []
    for index, (point, ground) in enumerate(zip(points, datums, strict=True)):
        result = tracer.trace(point, VARIANTS, ground_z_m=float(ground), seed=args.seed + index)
        rows.append(result.scalars())
    # Union rather than rows[0]. A fully enclosed standpoint has an exactly zero
    # direct term, and scalars() then omits the multipath gain key entirely, so
    # keying off the first row drops every site that has one such standpoint.
    # Madrid, Prague and Brussels each have one.
    keys = {key for row in rows for key in row}
    return {key: np.array([row.get(key, np.nan) for row in rows]) for key in sorted(keys)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", default="korenmarkt")
    parser.add_argument("--crops", type=int, nargs="+", default=[130, 250])
    parser.add_argument("--anchor-crop-m", type=int, default=130)
    parser.add_argument("--locations", type=int, default=40)
    parser.add_argument("--walk-radius-m", type=float, default=60.0)
    parser.add_argument("--rays", type=int, default=150_000)
    parser.add_argument("--frequency-hz", type=float, default=15.0e9)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--out", type=pathlib.Path, default=OUTPUT)
    args = parser.parse_args(argv)

    started = time.perf_counter()
    args.out.mkdir(parents=True, exist_ok=True)
    by_crop = {}
    for crop in args.crops:
        print(f"[trace] {args.site} at {crop} m", flush=True)
        by_crop[crop] = trace_site(args.site, crop, args)

    report: dict[str, object] = {
        "site": args.site,
        "crops_m": args.crops,
        "anchor_crop_m": args.anchor_crop_m,
        "locations": args.locations,
        "rays": args.rays,
        "note": (
            "Old and new law come from the same rays at each crop, so the level "
            "difference between them carries no Monte Carlo noise. The crop "
            "difference within one law does."
        ),
    }

    print(f"\n{'model':32s} " + " ".join(f"{c:>12d} m" for c in args.crops))
    for new, old in PAIRS.items():
        for name in (old, new):
            medians = [float(np.median(by_crop[c][f"chi_{name}"])) for c in args.crops]
            print(f"{name:32s} " + " ".join(f"{m:14.5f}" for m in medians))
            report[name] = {
                "median_by_crop": dict(zip([str(c) for c in args.crops], medians, strict=True)),
                "crop_correction_db": (
                    10.0 * np.log10(medians[-1] / medians[0]) if medians[0] > 0.0 and medians[-1] > 0.0 else None
                ),
            }
        shift = [
            10.0 * np.log10(np.median(by_crop[c][f"chi_{new}"]) / np.median(by_crop[c][f"chi_{old}"]))
            for c in args.crops
        ]
        report[f"{new}_law_shift_db"] = dict(zip([str(c) for c in args.crops], shift, strict=True))
        print(f"{'  new against old, dB':32s} " + " ".join(f"{s:14.3f}" for s in shift))
        print(
            f"{'  crop correction, dB':32s} "
            f"old {report[old]['crop_correction_db']:+.3f}   new {report[new]['crop_correction_db']:+.3f}\n"
        )

    isotropic = [float(np.median(by_crop[c]["chi_isotropic"])) for c in args.crops]
    report["isotropic"] = {"median_by_crop": dict(zip([str(c) for c in args.crops], isotropic, strict=True))}
    print(f"{'isotropic, unchanged by the law':32s} " + " ".join(f"{m:14.5f}" for m in isotropic))

    report["seconds"] = time.perf_counter() - started
    path = args.out / f"{args.site}_law_comparison.json"
    path.write_text(json.dumps(report, indent=2, default=float) + "\n")
    print(f"\n[done] {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
