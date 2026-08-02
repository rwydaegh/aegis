"""Compute the sky-conflict second opinion for poses that shipped without it.

`semantic_twin.align_skyline` already computes `sky_conflict`, but it needs a
first-hit ray cast, which needs `trimesh` with `embreex`. The GPU box's
alignment environment does not have that extra, so every pose it produced
carries `{"unavailable": ...}` in place of the number, and the diagnostic that
is meant to be an independent check on registration was never on disk. This
backfills it in place.

Why it is worth having. The sky conflict counts the directions the segmentation
calls sky for which the support mesh returns a first hit. It shares no term, no
parameter and no smoothing with the skyline objective, so it is an independent
witness on the same pose, and it separates poses that the skyline residual
cannot: across the shipped set the residual ranges of the conflicting and
non-conflicting halves overlap almost completely, while the median range to the
conflicting geometry differs by a factor of forty.

**Which mesh.** The conflict is only meaningful against the mesh the pose was
actually fitted to, and `pose_aligned.json` does not record a mesh path. It does
record `n_candidate_vertices`, which is a fingerprint: `candidate_vertices` is
deterministic given the mesh, the start position, the bin count, the minimum
distance and the smoothing, and all but the mesh are in the pose file. So each
site's mesh is identified by matching that count exactly against every candidate
`.ply`. The match is tight enough to separate the single and double precision
builds of the same crop radius, and it found two shipped poses whose mesh was
not the one the rest of the study defaults to. A pose whose count matches no
mesh is reported and skipped rather than guessed at.

Run from the ``semantic_twin`` directory::

    ../../../.venv/bin/python backfill_sky_conflict.py
    ../../../.venv/bin/python backfill_sky_conflict.py --site prague_staromestske
    ../../../.venv/bin/python backfill_sky_conflict.py --dry-run
"""

from __future__ import annotations

import argparse
import csv
import datetime
import json
import pathlib
import sys
from typing import Any

import numpy as np

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from semantic_twin.align_skyline import _semantic_ids, candidate_vertices, sky_conflict  # noqa: E402
from semantic_twin.support_mesh import read_binary_ply, read_binary_ply_vertices  # noqa: E402

PANORAMAS = SCRIPT_DIR / "data" / "panoramas"
GEOMETRY = SCRIPT_DIR / "data" / "geometry"
DEFAULT_SUMMARY = SCRIPT_DIR / "outputs" / "registration_sky_conflict"

# A capture set that has no geometry directory of its own borrows the site's.
GEOMETRY_ALIAS = {"korenmarkt_walk": "korenmarkt", "korenmarkt_mapillary": "korenmarkt"}

REQUIRES = "trimesh with the embreex extra, which is why the alignment runs on the GPU box shipped 'unavailable'"
METHOD = "equirectangular first-hit ray cast against the support mesh"


def pose_files(site: str | None) -> list[pathlib.Path]:
    """Every shipped pose, including the single-capture sites one level shallower."""
    found = sorted(PANORAMAS.glob("*/alignment/pose_aligned.json"))
    found += sorted(PANORAMAS.glob("*/*/alignment/pose_aligned.json"))
    if site:
        found = [p for p in found if site in p.parts]
    return found


def site_of(path: pathlib.Path) -> str:
    return path.relative_to(PANORAMAS).parts[0]


def capture_of(path: pathlib.Path) -> str:
    parts = path.relative_to(PANORAMAS).parts
    return parts[1] if len(parts) > 3 else parts[0]


def candidate_count(vertices: np.ndarray, pose: dict[str, Any]) -> int:
    """Reproduce the pruning the fit used, which is what n_candidate_vertices counted."""
    start = np.asarray(pose["skyline_start_position_enu_m"], dtype=float)
    dz_bounds = tuple(float(v) for v in pose["skyline_dz_bounds_m"])
    return len(
        candidate_vertices(
            vertices,
            start,
            1024,
            float(pose["minimum_skyline_distance_m"]),
            search_box_m=((-4.0, 4.0), (-4.0, 4.0), dz_bounds),
            smoothing_size=11,
            smoothing_percentile=float(pose["skyline_smoothing_percentile"]),
        )
    )


def identify_mesh(
    site: str,
    pose: dict[str, Any],
    vertex_cache: dict[pathlib.Path, np.ndarray],
    preferred: pathlib.Path | None,
) -> pathlib.Path | None:
    """The mesh whose candidate pruning reproduces this pose's own vertex count."""
    directory = GEOMETRY / GEOMETRY_ALIAS.get(site, site)
    target = int(pose["n_candidate_vertices"])
    order = [preferred] if preferred else []
    order += [p for p in sorted(directory.glob("*.ply")) if p != preferred]
    for mesh in order:
        if mesh is None or not mesh.exists():
            continue
        if mesh not in vertex_cache:
            vertex_cache[mesh] = read_binary_ply_vertices(mesh)
        if candidate_count(vertex_cache[mesh], pose) == target:
            return mesh
    return None


def backfill(site: str | None, *, width: int, dry_run: bool, summary: pathlib.Path) -> int:
    vertex_cache: dict[pathlib.Path, np.ndarray] = {}
    mesh_cache: dict[pathlib.Path, tuple[np.ndarray, np.ndarray]] = {}
    chosen: dict[str, pathlib.Path] = {}
    today = datetime.date.today().isoformat()
    rows: list[dict[str, Any]] = []
    unmatched: list[str] = []

    for path in pose_files(site):
        name = site_of(path)
        pose = json.loads(path.read_text())
        capture = path.parent.parent
        semantics = capture / "semantics" / "panorama_semantics.npz"
        document = capture / "semantics" / "semantics.json"
        if not semantics.exists() or not document.exists():
            print(f"[skip] {capture.name}: no semantics beside the pose", flush=True)
            continue

        mesh = identify_mesh(name, pose, vertex_cache, chosen.get(name))
        if mesh is None:
            unmatched.append(str(path))
            print(f"[unmatched] {name}/{capture.name}: no mesh reproduces n_candidate_vertices", flush=True)
            continue
        chosen[name] = mesh
        if mesh not in mesh_cache:
            mesh_cache[mesh] = read_binary_ply(mesh)
            print(f"[mesh] {name} -> {mesh.name}", flush=True)
        vertices, faces = mesh_cache[mesh]

        entity = np.load(semantics)["entity"]
        sky_id, structural_ids, _ = _semantic_ids(json.loads(document.read_text()))
        conflict = sky_conflict(
            vertices,
            faces,
            entity,
            sky_id,
            structural_ids,
            np.asarray(pose["position_enu_m"], dtype=float),
            heading_deg=float(pose["heading_deg"]),
            pitch_deg=float(pose["pitch_correction_deg"]),
            roll_deg=float(pose["roll_correction_deg"]),
            width=width,
            height=width // 2,
        ).as_dict()

        start = np.asarray(pose["skyline_start_position_enu_m"], dtype=float)
        dz = float(pose["position_enu_m"][2] - start[2])
        lo, hi = (float(v) for v in pose["skyline_dz_bounds_m"])
        conflict.update(
            {
                "method": METHOD,
                "requires": REQUIRES,
                "computed_by": "backfill_sky_conflict.py",
                "computed_on": today,
                "mesh": str(mesh.relative_to(SCRIPT_DIR)),
                "mesh_identified_by": (
                    "candidate_vertices reproduces this pose's own n_candidate_vertices, "
                    "which separates the single and double precision builds of one crop radius"
                ),
                "replaces": "the {'unavailable'} stub written when the alignment ran without embreex",
            }
        )
        if not dry_run:
            pose["sky_conflict"] = conflict
            path.write_text(json.dumps(pose, indent=2) + "\n")

        rows.append(
            {
                "site": name,
                "capture": capture.name,
                "pose_file": str(path.relative_to(SCRIPT_DIR)),
                "mesh": str(mesh.relative_to(SCRIPT_DIR)),
                "skyline_residual_deg": pose["skyline_score_mean_deg"],
                "dz_m": dz,
                "dz_bound_low_m": lo,
                "dz_bound_high_m": hi,
                "dz_slack_to_bound_m": min(abs(dz - lo), abs(dz - hi)),
                "skyline_dz_at_bound": bool(pose["skyline_dz_at_bound"]),
                "n_skyline_samples": pose["n_observed_structural_skyline_samples"],
                "sky_with_mesh_hit_fraction": conflict["sky_with_mesh_hit_fraction"],
                "sky_with_distant_mesh_hit_fraction": conflict["sky_with_distant_mesh_hit_fraction"],
                "structure_without_mesh_hit_fraction": conflict["structure_without_mesh_hit_fraction"],
                "disagreement": conflict["disagreement"],
                "conflict_median_range_m": conflict["conflict_median_range_m"],
                "n_sky_directions": conflict["n_sky_directions"],
                "n_directions": conflict["n_directions"],
            }
        )
        print(
            f"  {name}/{capture.name[:26]:26} res {rows[-1]['skyline_residual_deg']:6.2f} "
            f"slack {rows[-1]['dz_slack_to_bound_m']:6.3f} "
            f"conflict {conflict['sky_with_mesh_hit_fraction'] * 100:6.2f}% "
            f"range {conflict['conflict_median_range_m']:7.2f} m",
            flush=True,
        )

    if rows and not dry_run:
        summary.parent.mkdir(parents=True, exist_ok=True)
        document = {
            "generated_on": today,
            "generator": "backfill_sky_conflict.py",
            "method": METHOD,
            "requires": REQUIRES,
            "grid": [width // 2, width],
            "min_elevation_deg": -60.0,
            "minimum_range_m": 8.0,
            "mesh_identified_by": "candidate_vertices reproduces each pose's own n_candidate_vertices",
            "reading": (
                "sky_with_mesh_hit_fraction is the fraction of directions the segmentation calls sky "
                "for which the support mesh returns a first hit. A healthy pose sits below a few percent "
                "with the few conflicts tens of metres away. A pose above 0.5 with a conflict range under "
                "a metre has the camera inside the geometry, and its skyline residual is not an error bar."
            ),
            "poses": rows,
        }
        summary.with_suffix(".json").write_text(json.dumps(document, indent=2) + "\n")
        with summary.with_suffix(".csv").open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        print(f"\nwrote {summary.with_suffix('.json')} and {summary.with_suffix('.csv')}")

    print(f"\n{len(rows)} poses, {len(unmatched)} unmatched")
    return 1 if unmatched else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", help="restrict to one site key")
    parser.add_argument("--width", type=int, default=512, help="equirectangular grid width, height is half")
    parser.add_argument("--summary", type=pathlib.Path)
    parser.add_argument("--dry-run", action="store_true", help="compute and print, write nothing")
    args = parser.parse_args(argv)
    # A one-site run must not overwrite the whole-cohort table with one row,
    # which it silently did once. Restricting the input restricts the output.
    summary = args.summary or (
        DEFAULT_SUMMARY.with_name(f"{DEFAULT_SUMMARY.name}_{args.site}") if args.site else DEFAULT_SUMMARY
    )
    return backfill(args.site, width=args.width, dry_run=args.dry_run, summary=summary)


if __name__ == "__main__":
    sys.exit(main())
