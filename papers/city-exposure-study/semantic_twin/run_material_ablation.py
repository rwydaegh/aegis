"""Trace the same walk under different facade material models and read off the decibels.

The point of the experiment is a single comparison held as fair as it can be
made. One mesh, one walk, one seed for the ray tracer, one body, one carrier.
Only the facade material model changes between rows, and every row is traced
rather than argued.

The rows, in the order they answer the question.

``brick`` is the pipeline as it stands. The Vistas ``Building`` prior resolves to
brick under an argmax, and the geometric fallback sends every facade to brick
anyway, so this is what every city in this study is currently traced with.

``prior_draw`` keeps that same fixed prior and stops taking its argmax, drawing a
material per face instead. Any gap between this and ``brick`` is the cost of the
argmax alone, with no new evidence of any kind.

``vlm_panorama`` and ``vlm_texture`` replace the fixed prior with the composition
a vision model read off the street level capture and off the photogrammetric
texture respectively.

The pure rows bracket what any material model can do, since a facade cannot be
more reflective than metal or less than timber.

    python3 run_material_ablation.py --locations 120
"""

from __future__ import annotations

import argparse
import json
import pathlib
import time
from typing import Any

import numpy as np

from semantic_twin.propagation import ISOTROPIC, ROOFTOP, STREET_SMALL_CELL, MitsubaGeometry, SbrTracer, TraceConfig
from semantic_twin.propagation.exposure import BodyCoupler, describe
from semantic_twin.propagation.material_posterior import bind_posterior
from semantic_twin.propagation.scene import CLASS_NAMES, classify_faces, load_bindings
from semantic_twin.propagation.walk import build_walk, stratified_subset

ROOT = pathlib.Path(__file__).resolve().parent
MESH = ROOT / "data" / "geometry" / "korenmarkt" / "inhouse_leaf_130m_f64.ply"
CONFIG = ROOT / "config"
OUTPUT = ROOT / "outputs" / "material_vlm"
GROUND_DATUM_M = 50.83747424667166
PHANTOM = "/home/user/aegis/data/duke.stl"
PHANTOM_MASS_KG = 72.4
MODELS = {"isotropic": ISOTROPIC, "rooftop": ROOFTOP, "street_small_cell": STREET_SMALL_CELL}


def pure(material: str) -> dict[str, float]:
    return {material: 1.0}


def variants(analysis: dict[str, Any]) -> dict[str, dict[str, float] | None]:
    composition = analysis["composition"]
    return {
        "brick": None,
        # A posterior with all its mass on brick has to reproduce the baseline
        # exactly. It is the control that separates a real material effect from
        # the tracer's own Monte Carlo noise, and it costs one more row.
        "pure_brick": pure("brick"),
        "prior_draw": composition["fixed_building_prior"],
        "vlm_panorama": composition["vlm_panorama"],
        "vlm_texture": composition["vlm_texture"],
        "pure_plasterboard": pure("plasterboard"),
        "pure_concrete": pure("concrete"),
        "pure_marble": pure("marble"),
        "pure_glass": pure("glass"),
        "pure_wood": pure("wood"),
        "pure_metal": pure("metal"),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=pathlib.Path, default=OUTPUT)
    parser.add_argument("--locations", type=int, default=120)
    parser.add_argument("--rays", type=int, default=400_000)
    parser.add_argument("--frequency-ghz", type=float, default=15.0)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--material-seeds", type=int, nargs="+", default=[0])
    parser.add_argument("--only", nargs="*", default=None)
    args = parser.parse_args()

    frequency = args.frequency_ghz * 1e9
    analysis = json.loads((args.out / "analysis.json").read_text())
    plan = variants(analysis)
    if args.only:
        plan = {name: plan[name] for name in args.only}

    geometry = MitsubaGeometry(MESH)
    areas = geometry.face_areas()
    geometric_class = classify_faces(geometry.vertices, geometry.faces, GROUND_DATUM_M)
    walk = build_walk(geometry, ground_datum_m=GROUND_DATUM_M, radius_m=90.0, spacing_m=3.0, seed=args.seed)
    picks = stratified_subset(walk, args.locations)
    coupler = BodyCoupler(PHANTOM, frequency, body_mass_kg=PHANTOM_MASS_KG)
    config = TraceConfig(frequency_hz=frequency, rays=args.rays, seed=args.seed)
    print(f"{len(walk)} walk candidates, tracing {picks.size} per variant")

    results: dict[str, Any] = {}
    per_location: dict[str, list[dict[str, float]]] = {}
    rows_path = args.out / "ablation_locations.jsonl"
    handle = rows_path.open("a")
    for name, posterior in plan.items():
        seeds = [0] if posterior is None else args.material_seeds
        for material_seed in seeds:
            tag = name if posterior is None else f"{name}_m{material_seed}"
            started = time.perf_counter()
            if posterior is None:
                binding = load_bindings(CONFIG, frequency)
                face_class = geometric_class
                realised = {"brick": float(areas[geometric_class == 1].sum() / areas.sum())}
                drawn = 0.0
            else:
                drawing = bind_posterior(areas, geometric_class, {"facade": posterior}, seed=1000 + material_seed)
                face_class = drawing.face_class
                binding = load_bindings(
                    CONFIG,
                    frequency,
                    class_names=drawing.class_names,
                    class_binding=drawing.class_binding,
                    class_rule="facade materials drawn per face from a posterior, other classes geometric",
                )
                realised = drawing.realised_composition
                drawn = drawing.drawn_area_fraction
            tracer = SbrTracer(geometry, face_class, binding.permittivity, binding.rms_height_m, config)
            scalars: list[dict[str, float]] = []
            for index in picks:
                point = walk.points[index]
                result = tracer.trace(
                    point, MODELS, ground_z_m=float(walk.ground_z_m[index]), seed=args.seed + 1000 * index
                )
                row = {"variant": tag, "index": int(index)}
                row.update(result.scalars())
                for model in MODELS:
                    exposure = coupler.couple(result.local_grid, result.rho[model], result.local_solid_angle, 1.0)
                    row[f"{model}_sar_wb_w_kg"] = float(exposure.sar_wb_w_kg)
                    row[f"{model}_peak_sab_w_m2"] = float(exposure.peak_sab_w_m2)
                scalars.append(row)
                handle.write(json.dumps(row) + "\n")
            handle.flush()
            summary = {
                "variant": tag,
                "posterior": posterior,
                "realised_area_composition": realised,
                "facade_area_fraction_drawn": drawn,
                "locations": len(scalars),
                "seconds": round(time.perf_counter() - started, 1),
            }
            for key in (
                "chi_isotropic",
                "chi_rooftop",
                "chi_street_small_cell",
                "mean_bounces",
                "escaped_fraction",
                "isotropic_sar_wb_w_kg",
                "rooftop_sar_wb_w_kg",
            ):
                values = np.array([row[key] for row in scalars])
                summary[key] = {
                    "median": float(np.median(values)),
                    "p10": float(np.quantile(values, 0.1)),
                    "p90": float(np.quantile(values, 0.9)),
                }
            results[tag] = summary
            per_location[tag] = scalars
            print(
                f"{tag:24s} chi_iso {summary['chi_isotropic']['median']:.5f}  "
                f"chi_roof {summary['chi_rooftop']['median']:.5f}  "
                f"bounces {summary['mean_bounces']['median']:.2f}  {summary['seconds']:.0f} s",
                flush=True,
            )
    handle.close()

    # Paired against the brick baseline. Every variant traces the same locations
    # with the same ray seeds, so the Monte Carlo error is common to both sides
    # of each ratio and cancels. The paired median is therefore far tighter than
    # the difference of the two medians, and it is the number to quote.
    reference = results.get("brick")
    if reference is not None:
        for tag, summary in results.items():
            summary["shift_db"] = {
                key: float(10 * np.log10(summary[key]["median"] / reference[key]["median"]))
                for key in ("chi_isotropic", "chi_rooftop", "chi_street_small_cell")
            }
            paired: dict[str, Any] = {}
            for key in ("chi_isotropic", "chi_rooftop", "chi_street_small_cell"):
                ratio = np.array([row[key] for row in per_location[tag]]) / np.array(
                    [row[key] for row in per_location["brick"]]
                )
                decibels = 10 * np.log10(ratio)
                paired[key] = {
                    "median_db": float(np.median(decibels)),
                    "p10_db": float(np.quantile(decibels, 0.1)),
                    "p90_db": float(np.quantile(decibels, 0.9)),
                    "locations_over_1db": int(np.count_nonzero(np.abs(decibels) > 1.0)),
                }
            summary["paired_shift_db"] = paired
    document = {
        "generator": "run_material_ablation.py",
        "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "mesh": str(MESH),
        "frequency_hz": frequency,
        "trace_config": config.as_dict(),
        "locations": int(picks.size),
        "body": describe(coupler),
        "geometric_class_area_fractions": {
            name: float(areas[geometric_class == index].sum() / areas.sum()) for index, name in enumerate(CLASS_NAMES)
        },
        "variants": results,
    }
    path = args.out / "ablation.json"
    if path.exists():
        previous = json.loads(path.read_text())
        previous["variants"].update(results)
        previous["variants"] = {k: v for k, v in previous["variants"].items()}
        document["variants"] = previous["variants"]
    path.write_text(json.dumps(document, indent=2))
    print(f"\n-> {path}")


if __name__ == "__main__":
    main()
