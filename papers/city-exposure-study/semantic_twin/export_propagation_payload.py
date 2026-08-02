"""Stage one of the propagation walkthrough blend: trace, and write a payload.

This produces the numbers a Blender scene needs to show how the estimator
works at one site, and nothing else. It runs the same tracer, the same walk
builder, the same surface binding and the same body coupler as
``run_exposure.py``, so what the blend draws is what the study computed rather
than an illustration of it.

Two things are traced per site. Every walk location is traced at production ray
count and reduced to its scalars, which is what colours the walk. One hero
location is traced again with a :class:`PathRecorder` attached, which keeps the
polyline of a capped number of rays. The recorder is a passive observer and the
test suite asserts that attaching it returns a bit identical result, so the rays
in the blend are the rays that were integrated.

Run from the ``semantic_twin`` directory::

    python export_propagation_payload.py --site korenmarkt
    python export_propagation_payload.py --site newyork_timessquare --locations 60

Then hand the payload to Blender::

    ~/blender-4.5/blender --background --python propagation_blender.py -- \
        --payload outputs/propagation_viz/korenmarkt_payload.npz \
        --blend outputs/propagation_viz/korenmarkt_propagation.blend
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time
from typing import Any

import numpy as np

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from run_exposure import (  # noqa: E402
    GROUND_DATUM_M,
    MODELS,
    PHANTOM,
    PHANTOM_MASS_KG,
    REFERENCE_S0_W_M2,
    ground_datum,
    site_mesh,
)
from semantic_twin.propagation import (  # noqa: E402
    TERMINATIONS,
    MitsubaGeometry,
    PathRecorder,
    SbrTracer,
    TraceConfig,
)
from semantic_twin.propagation.exposure import BodyCoupler  # noqa: E402
from semantic_twin.propagation.scene import CLASS_NAMES, classify_faces, load_bindings  # noqa: E402
from semantic_twin.propagation.walk import build_walk, stratified_subset  # noqa: E402

CONFIG = SCRIPT_DIR / "config"
OUTPUT = SCRIPT_DIR / "outputs" / "propagation_viz"

#: The blend is meant to be opened on a laptop, so the shell that gets drawn is
#: smaller than the shell that gets traced. Occlusion at the far edge of a 250 m
#: crop changes the numbers and is why the crop is 250 m, but it is off camera
#: and carrying it would triple the file for nothing visible. The traced radius
#: is recorded in the payload so the blend can say which is which.
DEFAULT_DRAW_RADIUS_M = 110.0


#: Height above head, in metres, of each site population, read off the models
#: rather than restated here. MONOSTATIC_SBR.md section 2.7.
HEIGHT_BAND_M: dict[str, tuple[float, float]] = {
    name: model.height_band_m for name, model in MODELS.items() if model.height_band_m is not None
}

RANGE_BAND_M: dict[str, tuple[float, float]] = {
    name: model.range_band_m for name, model in MODELS.items() if model.range_band_m is not None
}


def network_markers(name: str, count: int, rng: np.random.Generator) -> dict[str, np.ndarray]:
    """Where the illumination model's sources sit, as points to draw.

    The model is a density on direction alone. It says how much power arrives
    from each elevation and nothing about range, because range was integrated
    out when it was derived, so drawing it needs the source geometry rather than
    the density. The only defensible choice is the geometry whose elevations
    reproduce the law the tracer actually integrates, and getting there took two
    corrections, of which the second reversed the first.

    Under the corrected law of section 2.7 the source population is simply the
    one the bands describe: heights uniform on the height band, drawn
    independently of position, and horizontal ranges uniform by area on the
    range band. That is what this function draws, and binning its elevations
    recovers `Q_S` to Poisson error.

    What it must not draw is the construction that reproduces the *uncorrected*
    `1/sin^3(el)` law, which is heights with density proportional to `h^2` and
    then ranges uniform by area inside `h*cot(el_max)` to `h*cot(el_min)`, each
    height getting its own annulus. That does reproduce `1/sin^3` exactly, and
    it was in this function until 2026-08-02, but the ranges it needs are 7.7 to
    803 m rather than 25 to 250 m, so it describes no deployment and it is not
    the population the bands name. ``tests/test_propagation.py`` pins it as
    rejected.

    Positions are relative to the observer's head, so the caller adds the
    standpoint.
    """
    if name not in HEIGHT_BAND_M:
        return {"positions": np.zeros((0, 3)), "height_band_m": np.zeros(2), "range_m": np.zeros(2)}
    low_h, high_h = HEIGHT_BAND_M[name]
    near, far = RANGE_BAND_M[name]

    height = rng.uniform(low_h, high_h, size=count)
    # Uniform areal density on the annulus is uniform in the squared radius.
    radius = np.sqrt(rng.uniform(near**2, far**2, size=count))
    azimuth = rng.uniform(0.0, 2.0 * np.pi, size=count)
    positions = np.column_stack([radius * np.cos(azimuth), radius * np.sin(azimuth), height])
    return {
        "positions": positions,
        "height_band_m": np.array([low_h, high_h]),
        "range_m": np.array([near, far]),
    }


def sphere_triangulation(grid: np.ndarray) -> np.ndarray:
    """Triangulate the direction grid, so the angular spectrum can be a surface.

    Done here rather than in the Blender stage because Blender ships its own
    Python without SciPy. The convex hull of points on a sphere is their
    Delaunay triangulation on that sphere, and the grid is a Fibonacci
    spiral, so the hull is well conditioned and no degenerate facet appears.
    """
    from scipy.spatial import ConvexHull

    hull = ConvexHull(np.asarray(grid, dtype=np.float64))
    simplices = hull.simplices
    # ConvexHull does not promise outward winding, so orient each facet by its
    # own centroid. A lobe lit from outside with inward normals reads as a hole.
    centroid = grid[simplices].mean(axis=1)
    a, b, c = grid[simplices[:, 0]], grid[simplices[:, 1]], grid[simplices[:, 2]]
    outward = np.einsum("ij,ij->i", np.cross(b - a, c - a), centroid) > 0.0
    return np.where(outward[:, None], simplices, simplices[:, ::-1])


def crop_for_drawing(
    vertices: np.ndarray, faces: np.ndarray, radius_m: float
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Faces whose centroid is inside ``radius_m``, reindexed to a compact vertex set."""
    centroid = vertices[faces].mean(axis=1)
    keep = np.linalg.norm(centroid[:, :2], axis=1) <= radius_m
    kept = faces[keep]
    used, remapped = np.unique(kept, return_inverse=True)
    return vertices[used], remapped.reshape(kept.shape), np.flatnonzero(keep)


def trace_site(args: argparse.Namespace) -> dict[str, Any]:
    started = time.perf_counter()
    mesh = site_mesh(args.site, args.crop_m)
    geometry = MitsubaGeometry(mesh, variant=args.variant)
    datum = GROUND_DATUM_M if args.site == "korenmarkt" else ground_datum(geometry)
    face_class = classify_faces(geometry.vertices, geometry.faces, datum)
    binding = load_bindings(CONFIG, args.frequency_hz)
    print(f"{args.site}: {geometry.face_count} triangles, ground datum {datum:.3f} m", flush=True)

    config = TraceConfig(
        frequency_hz=args.frequency_hz,
        rays=args.rays,
        local_cells=args.local_cells,
        max_bounces=args.max_bounces,
        seed=args.seed,
    )
    tracer = SbrTracer(geometry, face_class, binding.permittivity, binding.rms_height_m, config)

    walk = build_walk(geometry, ground_datum_m=datum, radius_m=args.walk_radius_m, spacing_m=3.0, seed=args.seed)
    picks = stratified_subset(walk, args.locations)
    points, datums = walk.points[picks], walk.ground_z_m[picks]
    print(f"walk: {len(walk)} candidates, tracing {picks.size}", flush=True)

    coupler = BodyCoupler(PHANTOM, args.frequency_hz, body_mass_kg=PHANTOM_MASS_KG)

    scalars: list[dict[str, float]] = []
    for index, (point, ground) in enumerate(zip(points, datums, strict=True)):
        result = tracer.trace(point, MODELS, ground_z_m=float(ground), seed=args.seed + index)
        row = result.scalars()
        for name in MODELS:
            body = coupler.couple(result.local_grid, result.rho[name], result.local_solid_angle, REFERENCE_S0_W_M2)
            row[f"{name}_peak_sab_w_m2"] = body.peak_sab_w_m2
            row[f"{name}_sar_wb_w_kg"] = body.sar_wb_w_kg
        scalars.append(row)
        if index % 10 == 0:
            print(f"  [{index + 1}/{picks.size}] chi_rooftop={row['chi_rooftop']:.4f}", flush=True)

    # The hero is the location whose rooftop susceptibility sits nearest the
    # median, so the rays drawn are a typical standpoint and not the best or
    # worst one in the set.
    rooftop = np.array([row["chi_rooftop"] for row in scalars])
    hero = int(np.argmin(np.abs(rooftop - np.median(rooftop))))
    print(f"hero location {hero}, chi_rooftop {rooftop[hero]:.4f} against median {np.median(rooftop):.4f}", flush=True)

    recorder = PathRecorder(capacity=args.paths, sky_distance_m=args.draw_radius_m * 1.6)
    hero_result = tracer.trace(
        points[hero], MODELS, ground_z_m=float(datums[hero]), seed=args.seed + hero, recorder=recorder
    )
    record = recorder.result()
    print(f"recorded {len(record)} paths, {record.vertices.shape[0]} vertices", flush=True)

    hero_body = {
        name: coupler.couple(
            hero_result.local_grid, hero_result.rho[name], hero_result.local_solid_angle, REFERENCE_S0_W_M2
        )
        for name in MODELS
    }
    body_sab = body_field(coupler, hero_result, "rooftop")

    rng = np.random.default_rng(args.seed)
    network = {name: network_markers(name, args.sources, rng) for name in MODELS}

    vertices, faces, kept = crop_for_drawing(geometry.vertices, geometry.faces, args.draw_radius_m)
    print(f"drawing {faces.shape[0]} of {geometry.face_count} triangles inside {args.draw_radius_m:g} m", flush=True)

    payload: dict[str, Any] = {
        "mesh_vertices": vertices.astype(np.float32),
        "mesh_faces": faces.astype(np.int32),
        "mesh_face_class": face_class[kept].astype(np.int8),
        "walk_points": points.astype(np.float32),
        "walk_ground_z_m": datums.astype(np.float32),
        "path_vertices": record.vertices.astype(np.float32),
        "path_offsets": record.offsets.astype(np.int32),
        "path_throughput": record.throughput.astype(np.float32),
        "path_face_class": record.face_class.astype(np.int8),
        "path_exit_direction": record.exit_direction.astype(np.float32),
        "path_bounces": record.bounces.astype(np.int16),
        "path_termination": record.termination.astype(np.int8),
        "hero_index": np.array(hero),
        "hero_point": points[hero].astype(np.float32),
        "local_grid": hero_result.local_grid.astype(np.float32),
        "local_grid_faces": sphere_triangulation(hero_result.local_grid).astype(np.int32),
        "body_vertices": body_sab["vertices"].astype(np.float32),
        "body_faces": body_sab["faces"].astype(np.int32),
        "body_sab_w_m2": body_sab["sab"].astype(np.float32),
    }
    for name in MODELS:
        payload[f"rho_{name}"] = hero_result.rho[name].astype(np.float32)
        payload[f"walk_chi_{name}"] = np.array([row[f"chi_{name}"] for row in scalars], dtype=np.float32)
        payload[f"walk_peak_sab_{name}"] = np.array([row[f"{name}_peak_sab_w_m2"] for row in scalars], dtype=np.float32)
        payload[f"network_{name}"] = network[name]["positions"].astype(np.float32)

    manifest = {
        "site": args.site,
        "mesh": str(mesh.relative_to(SCRIPT_DIR)),
        "traced_crop_radius_m": args.crop_m,
        "drawn_radius_m": args.draw_radius_m,
        "traced_triangles": geometry.face_count,
        "drawn_triangles": int(faces.shape[0]),
        "ground_datum_m": datum,
        "frequency_hz": args.frequency_hz,
        "reference_s0_w_m2": REFERENCE_S0_W_M2,
        "class_names": list(CLASS_NAMES),
        "terminations": list(TERMINATIONS),
        "locations": int(picks.size),
        "walk_candidates": len(walk),
        "trace_config": config.as_dict(),
        "surface_binding": binding.as_dict(),
        "hero": {
            "index": hero,
            "point_enu_m": points[hero].tolist(),
            "sky_fraction": hero_result.sky_fraction,
            "mean_bounces": hero_result.mean_bounces,
            "recorded_paths": len(record),
            "susceptibility": hero_result.susceptibility,
            "susceptibility_direct": hero_result.susceptibility_direct,
            "body": {name: value.as_dict() for name, value in hero_body.items()},
        },
        "walk_summary": {
            name: {
                "median_chi": float(np.median([row[f"chi_{name}"] for row in scalars])),
                "min_chi": float(np.min([row[f"chi_{name}"] for row in scalars])),
                "max_chi": float(np.max([row[f"chi_{name}"] for row in scalars])),
            }
            for name in MODELS
        },
        "network_height_band_m": {name: network[name]["height_band_m"].tolist() for name in MODELS},
        "seconds": time.perf_counter() - started,
        "storage_note": (
            "The path polylines here are a capped visualisation buffer, not a path table. "
            "The estimator itself still writes none, and PathRecorder is asserted to leave "
            "every traced number bit identical."
        ),
    }
    return {"payload": payload, "manifest": manifest}


def body_field(coupler: BodyCoupler, result: Any, model: str) -> dict[str, np.ndarray]:
    """Per triangle absorbed power density on the phantom, plus its geometry.

    ``BodyMesh`` holds a triangle soup, ``(n_triangles, 3, 3)``, so the faces
    handed to Blender are the trivial index triples. That triples the vertex
    count against a shared mesh and it is the right trade here, because
    ``Sab`` is a per triangle quantity and a shared vertex would have to average
    across the faces that meet at it.
    """
    from aegis.paths import PropagationPaths

    power = result.rho[model] * result.local_solid_angle * REFERENCE_S0_W_M2
    keep = power > 0.0
    paths = PropagationPaths.from_powers(-result.local_grid[keep], power[keep])
    dosimetry = coupler.engine.compute(coupler.body, paths, level=coupler.level, body_mass=coupler.body_mass_kg)
    corners = np.asarray(coupler.body.vertices, dtype=np.float64)
    count = corners.shape[0]
    return {
        "vertices": corners.reshape(-1, 3),
        "faces": np.arange(3 * count, dtype=np.int64).reshape(count, 3),
        "sab": np.asarray(dosimetry.sab, dtype=np.float64),
    }


def arguments(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", default="korenmarkt")
    parser.add_argument("--crop-m", type=int, default=250, help="Traced crop radius, the converged one")
    parser.add_argument("--draw-radius-m", type=float, default=DEFAULT_DRAW_RADIUS_M)
    parser.add_argument("--locations", type=int, default=60)
    parser.add_argument("--walk-radius-m", type=float, default=60.0)
    parser.add_argument("--paths", type=int, default=1200, help="Ray polylines kept at the hero location")
    parser.add_argument("--sources", type=int, default=400, help="Illumination source markers per model")
    parser.add_argument("--rays", type=int, default=200_000)
    parser.add_argument("--local-cells", type=int, default=512)
    parser.add_argument("--max-bounces", type=int, default=4)
    parser.add_argument("--frequency-hz", type=float, default=15.0e9)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--variant", default="llvm_ad_rgb")
    parser.add_argument("--out", type=pathlib.Path, default=OUTPUT)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = arguments(argv)
    args.out.mkdir(parents=True, exist_ok=True)
    bundle = trace_site(args)
    payload_path = args.out / f"{args.site}_payload.npz"
    np.savez_compressed(payload_path, **bundle["payload"])
    manifest_path = args.out / f"{args.site}_manifest.json"
    manifest_path.write_text(json.dumps(bundle["manifest"], indent=2, default=float) + "\n")
    size_mb = payload_path.stat().st_size / 1e6
    print(f"[done] {payload_path} ({size_mb:.1f} MB) and {manifest_path.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
