"""Does Times Square's spurious sub street geometry change its exposure numbers?

The quality pass passed that site's mesh by comparing a total vertical extent
against an expectation, and a total cannot see a cancellation. The mesh runs
from -220.3 m to +207.2 m about a street at -19.0 m, which is 226 m of real
tower plus two hundred metres of reconstruction failure underneath the road,
and 2.87 percent of its vertices sit more than 30 m below the pavement. Mirror
glass and animated billboards are the worst case there is for multi view stereo.

Whether that matters to exposure is a separate question from whether it is
wrong, and it is answerable rather than arguable. The spurious geometry is
below the standpoints, so most of it should be invisible to a head at 1.5 m,
but "should be" is not a measurement: a surface below the observer can still
receive a downward ray and bounce it back up, and the ground the walk builder
found may itself be part of the failure.

So trace the same standpoints twice, once against the mesh as built and once
with everything below a floor removed, and report the difference.

    python run_substreet_ablation.py --site newyork_timessquare

The control is a site with no sub street geometry at all, where the two runs
must agree exactly because the cull removes nothing.
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

from run_exposure import MODELS, ground_datum, site_mesh  # noqa: E402
from semantic_twin.propagation import (  # noqa: E402
    DEFAULT_MAX_BOUNCES,
    MitsubaGeometry,
    SbrTracer,
    TraceConfig,
)
from semantic_twin.materials import classify_faces, load_table  # noqa: E402
from semantic_twin.walk.grid import build_walk  # noqa: E402
from semantic_twin.walk.model import stratified_subset  # noqa: E402

CONFIG = SCRIPT_DIR / "config"
OUTPUT = SCRIPT_DIR / "outputs" / "substreet_ablation"


def write_culled(geometry: MitsubaGeometry, floor_z: float, path: pathlib.Path) -> tuple[pathlib.Path, int, int]:
    """A copy of the mesh with every face wholly below ``floor_z`` removed.

    Wholly below, not partly: a facade that reaches down through the floor is
    real geometry with a bad tail, and dropping it would open a hole in the
    street that changes the answer for a reason that has nothing to do with the
    defect being measured.
    """
    corners = geometry.vertices[geometry.faces]
    keep = corners[:, :, 2].max(axis=1) >= floor_z
    faces = geometry.faces[keep]
    used, remapped = np.unique(faces, return_inverse=True)
    vertices = geometry.vertices[used]
    faces = remapped.reshape(faces.shape)

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        handle.write(b"ply\nformat binary_little_endian 1.0\n")
        handle.write(f"element vertex {vertices.shape[0]}\n".encode())
        handle.write(b"property float x\nproperty float y\nproperty float z\n")
        handle.write(f"element face {faces.shape[0]}\n".encode())
        handle.write(b"property list uchar int vertex_indices\nend_header\n")
        handle.write(np.ascontiguousarray(vertices, dtype="<f4").tobytes())
        block = np.empty(faces.shape[0], dtype=[("n", "u1"), ("v", "<i4", 3)])
        block["n"] = 3
        block["v"] = faces
        handle.write(block.tobytes())
    return path, int(geometry.faces.shape[0]), int(faces.shape[0])


def trace_all(geometry: MitsubaGeometry, datum: float, points, datums, config, frequency_hz) -> dict[str, np.ndarray]:
    face_class = classify_faces(geometry.vertices, geometry.faces, datum)
    binding = load_table(CONFIG, frequency_hz)
    tracer = SbrTracer(geometry, face_class, binding.permittivity, binding.rms_height_m, config)
    rows = []
    for index, (point, ground) in enumerate(zip(points, datums, strict=True)):
        result = tracer.trace(point, MODELS, ground_z_m=float(ground), seed=config.seed + index)
        rows.append(result.scalars())
    return {key: np.array([row[key] for row in rows]) for key in rows[0]}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", default="newyork_timessquare")
    parser.add_argument("--crop-m", type=int, default=250)
    parser.add_argument("--locations", type=int, default=40)
    parser.add_argument("--walk-radius-m", type=float, default=60.0)
    parser.add_argument("--rays", type=int, default=120_000)
    parser.add_argument("--floor-below-datum-m", type=float, default=8.0)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--out", type=pathlib.Path, default=OUTPUT)
    args = parser.parse_args(argv)

    started = time.perf_counter()
    args.out.mkdir(parents=True, exist_ok=True)
    mesh = site_mesh(args.site, args.crop_m)
    geometry = MitsubaGeometry(mesh)
    datum = ground_datum(geometry, radius_m=args.walk_radius_m)
    floor_z = datum - args.floor_below_datum_m

    culled_path, before, after = write_culled(geometry, floor_z, args.out / f"{args.site}_culled.ply")
    print(f"{args.site}: datum {datum:.2f} m, floor {floor_z:.2f} m, {before} faces -> {after}", flush=True)

    walk = build_walk(geometry, ground_datum_m=datum, radius_m=args.walk_radius_m, spacing_m=3.0, seed=args.seed)
    picks = stratified_subset(walk, args.locations)
    points, datums = walk.points[picks], walk.ground_z_m[picks]
    print(f"walk: {len(walk)} candidates, tracing {picks.size} against both meshes", flush=True)

    config = TraceConfig(
        frequency_hz=15.0e9,
        rays=args.rays,
        local_cells=512,
        max_bounces=DEFAULT_MAX_BOUNCES,
        seed=args.seed,
    )
    as_built = trace_all(geometry, datum, points, datums, config, 15.0e9)
    culled = trace_all(MitsubaGeometry(culled_path), datum, points, datums, config, 15.0e9)

    report: dict[str, object] = {
        "site": args.site,
        "crop_radius_m": args.crop_m,
        "ground_datum_m": datum,
        "cull_floor_z_m": floor_z,
        "faces_before": before,
        "faces_after": after,
        "faces_removed_fraction": (before - after) / before,
        "locations": int(picks.size),
        "rays": args.rays,
        "seconds": None,
    }
    print(f"\n{'quantity':28s} {'as built':>12s} {'culled':>12s} {'shift dB':>10s}")
    for key in ("chi_isotropic", "chi_rooftop", "chi_street_small_cell", "sky_fraction"):
        a, b = as_built[key], culled[key]
        median_a, median_b = float(np.median(a)), float(np.median(b))
        shift = 10.0 * np.log10(median_b / median_a) if median_a > 0.0 and median_b > 0.0 else float("nan")
        worst = float(np.max(np.abs(10.0 * np.log10(np.maximum(b, 1e-12) / np.maximum(a, 1e-12)))))
        report[key] = {
            "median_as_built": median_a,
            "median_culled": median_b,
            "median_shift_db": shift,
            "worst_location_shift_db": worst,
            "locations_moving_over_0p5_db": int(
                np.count_nonzero(np.abs(10.0 * np.log10(np.maximum(b, 1e-12) / np.maximum(a, 1e-12))) > 0.5)
            ),
        }
        print(f"{key:28s} {median_a:12.5f} {median_b:12.5f} {shift:10.3f}")
    report["seconds"] = time.perf_counter() - started
    path = args.out / f"{args.site}_substreet.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    print(f"\n[done] {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
