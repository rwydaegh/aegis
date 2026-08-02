"""Has the crop radius converged?

`ROADMAP.md` phase 4 records this as the largest known hole and says the sweep
should run before the propagation modules are built, because the answer changes
the scene every later stage consumes. This is that sweep.

The question is not whether a wider crop changes the geometry, it obviously does.
It is whether a wider crop changes the quantity the study reports. So the metric
is the exposure susceptibility itself, over a fixed set of pedestrian locations
that lie well inside the smallest crop, so that every radius is scored on the same
observers and only the surrounding scene changes.

Sky fraction is carried alongside because it is the zero bounce limit of the same
quantity and it converges from the other side: a wider crop can only ever occlude
more, never less, so sky fraction falls monotonically and its remaining slope is a
direct bound on what is still missing.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
import time

import numpy as np

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

# The registered ground datum at Korenmarkt, the same constant run_exposure.py uses.
GROUND_DATUM_M = 50.83747424667166


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", default="korenmarkt")
    parser.add_argument("--out", type=pathlib.Path, default=SCRIPT_DIR / "outputs/crop_convergence")
    parser.add_argument("--locations", type=int, default=24)
    parser.add_argument("--rays", type=int, default=200_000)
    parser.add_argument("--max-bounces", type=int, default=4)
    parser.add_argument("--observer-radius-m", type=float, default=40.0)
    parser.add_argument("--frequency-hz", type=float, default=15.0e9)
    parser.add_argument("--seed", type=int, default=11)
    return parser.parse_args()


def radius_of(path: pathlib.Path) -> float:
    match = re.search(r"_(\d+)m", path.name)
    return float(match.group(1)) if match else float("nan")


def candidate_meshes(site: str) -> list[pathlib.Path]:
    """One mesh per radius, preferring the double precision build where both exist."""
    directory = SCRIPT_DIR / "data/geometry" / site
    best: dict[float, pathlib.Path] = {}
    for path in sorted(directory.glob("inhouse_leaf_*.ply")):
        radius = radius_of(path)
        if np.isnan(radius):
            continue
        if radius not in best or path.name.endswith("_f64.ply"):
            best[radius] = path
    return [best[r] for r in sorted(best)]


def observers_unused(mesh, count: int, reach: float, height: float, seed: int) -> np.ndarray:
    """Superseded by the pipeline walk builder, kept out of the run."""
    rng = np.random.default_rng(seed)
    golden = np.pi * (3.0 - 5.0**0.5)
    index = np.arange(count)
    radius = reach * np.sqrt((index + 0.5) / count)
    angle = index * golden + rng.uniform(0.0, 2.0 * np.pi)
    points = []
    for x, y in zip(radius * np.cos(angle), radius * np.sin(angle)):
        origins = np.array([[x, y, height + 60.0]])
        hits, _, _ = mesh.ray.intersects_location(ray_origins=origins, ray_directions=np.array([[0.0, 0.0, -1.0]]))
        if len(hits) == 0:
            continue
        z = hits[:, 2]
        # Median over the hits rather than either extreme: the highest puts the
        # observer on a roof wherever the photogrammetry bridges a street, the
        # lowest puts it under an arcade.
        points.append([x, y, float(np.median(z)) + 1.5])
    return np.asarray(points, dtype=np.float64)


def main() -> None:
    args = arguments()
    from semantic_twin.propagation.directions import ISOTROPIC, ROOFTOP
    from semantic_twin.propagation.geometry import MitsubaGeometry
    from semantic_twin.propagation.scene import classify_faces, load_bindings
    from semantic_twin.propagation.tracer import SbrTracer, TraceConfig
    from semantic_twin.propagation.walk import build_walk, stratified_subset

    meshes = candidate_meshes(args.site)
    if len(meshes) < 3:
        raise SystemExit(f"need at least three radii to see a trend, found {len(meshes)}")
    print(f"[sweep] {args.site}: radii {[radius_of(p) for p in meshes]}", flush=True)

    # Observers come from the pipeline's own walk builder on the smallest crop,
    # so they are the same kind of standpoint the exposure runs use, and every
    # radius is scored on an identical set while only the surroundings change.
    smallest = MitsubaGeometry(meshes[0])
    ground = GROUND_DATUM_M
    walk = build_walk(smallest, ground_datum_m=ground, radius_m=args.observer_radius_m, spacing_m=3.0, seed=args.seed)
    picks = stratified_subset(walk, args.locations)
    points = walk.points[picks]
    datums = walk.ground_z_m[picks]
    print(f"[sweep] {len(walk)} candidates, {len(points)} observers inside {args.observer_radius_m:.0f} m", flush=True)

    models = {"isotropic": ISOTROPIC, "rooftop": ROOFTOP}
    binding = load_bindings(SCRIPT_DIR / "config", args.frequency_hz)
    rows = []
    for path in meshes:
        started = time.perf_counter()
        geometry = MitsubaGeometry(path)
        face_class = classify_faces(geometry.vertices, geometry.faces, ground)
        config = TraceConfig(
            frequency_hz=args.frequency_hz,
            rays=args.rays,
            max_bounces=args.max_bounces,
            seed=args.seed,
        )
        tracer = SbrTracer(geometry, face_class, binding.permittivity, binding.rms_height_m, config)
        chi = {name: [] for name in models}
        sky = []
        for point, datum in zip(points, datums):
            result = tracer.trace(point, models, ground_z_m=float(datum))
            for name in models:
                chi[name].append(result.susceptibility[name])
            sky.append(result.sky_fraction)
        row = {
            "mesh": path.name,
            "crop_radius_m": radius_of(path),
            "triangles": int(len(geometry.faces)),
            "observers": len(points),
            "sky_fraction_mean": float(np.mean(sky)),
            "seconds": time.perf_counter() - started,
        }
        for name in models:
            values = np.asarray(chi[name])
            row[f"chi_{name}_mean"] = float(values.mean())
            row[f"chi_{name}_median"] = float(np.median(values))
        rows.append(row)
        print(
            f"[sweep] r={row['crop_radius_m']:5.0f} m  sky {row['sky_fraction_mean']:.4f}  "
            f"chi_iso {row['chi_isotropic_mean']:.4f}  chi_roof {row['chi_rooftop_mean']:.4f}  "
            f"{row['seconds']:.0f} s",
            flush=True,
        )

    for previous, current in zip(rows, rows[1:]):
        for key in ("chi_isotropic_mean", "chi_rooftop_mean", "sky_fraction_mean"):
            before, after = previous[key], current[key]
            current[f"delta_db_{key}"] = float(10.0 * np.log10(after / before)) if before > 0 else float("nan")

    args.out.mkdir(parents=True, exist_ok=True)
    payload = {
        "site": args.site,
        "observer_radius_m": args.observer_radius_m,
        "rays": args.rays,
        "max_bounces": args.max_bounces,
        "frequency_hz": args.frequency_hz,
        "note": (
            "Observers are held fixed inside the smallest crop so every radius is scored on the same "
            "standpoints and only the surrounding scene changes. Deltas are against the next smaller radius."
        ),
        "rows": rows,
    }
    (args.out / f"{args.site}_crop_convergence.json").write_text(json.dumps(payload, indent=1) + "\n")
    print(f"[sweep] wrote {args.out / f'{args.site}_crop_convergence.json'}", flush=True)


if __name__ == "__main__":
    main()
