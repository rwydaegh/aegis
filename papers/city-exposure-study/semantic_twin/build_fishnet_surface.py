"""Build the visible surface set at one panorama centre with the fishnet cutter.

This is the thin runner for ``semantic_twin/scene/fishnet/``.  It reads the support
mesh, the recovered pose, the perspective label and confidence maps, the mesh
first-hit buffer from ``raycast_mesh_depth.py`` and, when available, the
mesh-versus-monocular depth decisions from ``compare_mesh_depth.py``.  It writes
one NPZ surface set per view plus a manifest with the measured triangle counts
and round-trip fidelity.  No Blender, no rendering.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from collections import Counter

import numpy as np
import trimesh

ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from semantic_twin.pano_geometry import panorama_to_world_matrix  # noqa: E402
from semantic_twin.scene.fishnet import (  # noqa: E402
    PAINT_REASONS,
    REJECTION_REASONS,
    aggregate_occlusion_budget,
    angular_tolerance_deg,
    build_fishnet,
    build_region_map,
    class_fidelity,
    occlusion_budget,
    occlusion_fidelity,
    paintability,
    rasterize_fishnet,
    save_fishnet,
)
from semantic_twin.scene.pinhole import CameraPose, PinholeView  # noqa: E402
from semantic_twin.vision.project import adaptive_semantic_tiles  # noqa: E402

# Classes whose pixels belong to the dynamic layer.  Their depth agrees with
# the wall behind them often enough that class, not distance, has to reject them.
TRANSIENT_WORDS = {
    "person",
    "rider",
    "bicyclist",
    "motorcyclist",
    "animal",
    "bird",
    "car",
    "truck",
    "bus",
    "tram",
    "vehicle",
    "motorcycle",
    "bicycle",
    "boat",
    "caravan",
    "trailer",
    "outdoor table",
}

# Classes that are not support surfaces: sky has no surface at all, and street
# furniture is reconstructed as its own proxy geometry by the object pipeline.
NON_SURFACE_WORDS = {
    "sky",
    "pole",
    "bollard",
    "bench",
    "trash can",
    "traffic light",
    "traffic sign",
    "street light",
    "fire hydrant",
    "bike rack",
    "car mount",
    "railing",
    "unknown",
}


# The propagation stage treats a face as fully visible with its area scaled by
# visible_fraction, with no sub-cell mask.  That holds while the occluded share
# of the projected support area stays small.  Korenmarkt is the easy case: a
# wide open square captured at pitch zero.  A narrow street with scaffolding,
# street trees and parked vehicles is not, so the budget is measured per site
# and a site above this fraction has to have the assumption revisited there.
SUB_CELL_REVIEW_FRACTION = 0.05


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mesh", type=pathlib.Path, required=True)
    parser.add_argument("--pose", type=pathlib.Path, required=True)
    parser.add_argument("--views", type=pathlib.Path, required=True, help="directory with h+00_YYY_labels.npy")
    parser.add_argument("--mesh-depth", type=pathlib.Path, required=True)
    parser.add_argument("--depth-compare", type=pathlib.Path)
    parser.add_argument("--semantics-json", type=pathlib.Path, required=True)
    parser.add_argument("--out", type=pathlib.Path, required=True)
    parser.add_argument("--yaws", type=int, nargs="+", default=[0, 90, 180, 270])
    parser.add_argument("--min-confidence", type=float, default=0.35)
    parser.add_argument("--boundary-tolerance-px", type=float, default=1.5)
    parser.add_argument("--min-region-pixels", type=int, default=64)
    parser.add_argument("--depth-break-ratio", type=float, default=0.15)
    parser.add_argument("--min-piece-area-px", type=float, default=1.0)
    parser.add_argument("--baseline", action="store_true", help="also count the image-tile quadtree for comparison")
    return parser.parse_args()


def main() -> None:
    args = arguments()
    args.out.mkdir(parents=True, exist_ok=True)
    mesh = trimesh.load(args.mesh, process=False)
    pose_document = json.loads(args.pose.read_text())
    pose = CameraPose(
        np.asarray(pose_document["position_enu_m"], dtype=np.float64),
        panorama_to_world_matrix(
            float(pose_document["heading_deg"]),
            pitch_deg=float(pose_document["pitch_correction_deg"]),
            roll_deg=float(pose_document["roll_correction_deg"]),
        ),
    )
    taxonomy = json.loads(args.semantics_json.read_text())["entity_id2label"]
    names = {int(key): value for key, value in taxonomy.items()}
    transient = {key for key, value in names.items() if any(word in value.casefold() for word in TRANSIENT_WORDS)}
    excluded = {
        key
        for key, value in names.items()
        if key not in transient and any(word in value.casefold() for word in NON_SURFACE_WORDS)
    }

    views = []
    budgets = []
    for yaw in args.yaws:
        stem = f"h+00_{yaw:03d}"
        labels = np.load(args.views / f"{stem}_labels.npy").astype(np.int64)
        confidence = np.load(args.views / f"{stem}_confidence.npy").astype(np.float64)
        depth = np.load(args.mesh_depth / f"{stem}.npz")
        range_m = depth["range_m"].astype(np.float64)
        range_m[range_m <= 0.0] = np.nan
        face_ids = depth["face_ids"].astype(np.int64)
        decision = None
        if args.depth_compare is not None:
            candidate = args.depth_compare / f"{stem}.npz"
            if candidate.exists():
                decision = np.load(candidate)["decision"]

        view = PinholeView(yaw_deg=float(yaw), width=labels.shape[1], height=labels.shape[0])
        reason = paintability(
            labels,
            confidence,
            range_m,
            transient_class_ids=transient,
            excluded_class_ids=excluded,
            min_confidence=args.min_confidence,
            decision=decision,
        )
        regions = build_region_map(
            labels,
            reason,
            range_m,
            depth_break_ratio=args.depth_break_ratio,
            min_region_pixels=args.min_region_pixels,
        )
        surface = build_fishnet(
            mesh.vertices,
            mesh.faces,
            face_ids,
            regions,
            pose,
            view,
            confidence=confidence,
            boundary_tolerance_px=args.boundary_tolerance_px,
            min_piece_area_px=args.min_piece_area_px,
        )
        save_fishnet(surface, args.out / f"{stem}_fishnet.npz")

        raster = rasterize_fishnet(surface, view.shape)
        fidelity = class_fidelity(raster, regions)
        occlusion = occlusion_fidelity(raster, face_ids, regions)
        budget = occlusion_budget(surface)
        budgets.append(budget)
        counts = Counter(int(item) for item in surface.face_class)
        record = {
            "view": stem,
            "shape": list(labels.shape),
            "triangles": surface.triangle_count,
            "vertices": int(surface.vertices.shape[0]),
            "surface_area_m2": float(surface.face_area_m2.sum()),
            "solid_angle_sr": float(surface.face_solid_angle_sr.sum()),
            "boundary_tolerance_px": args.boundary_tolerance_px,
            "boundary_tolerance_deg": angular_tolerance_deg(args.boundary_tolerance_px, view),
            "region_report": regions.report,
            "fishnet_report": surface.report,
            "class_fidelity": fidelity,
            "occlusion_fidelity": occlusion,
            "occlusion_budget": budget,
            "paint_reason_pixels": {
                name: int(np.count_nonzero(reason == code)) for name, code in PAINT_REASONS.items()
            },
            "triangles_by_class": {names.get(key, str(key)): value for key, value in sorted(counts.items())},
            "rejected_by_reason": {
                name: int(np.count_nonzero(surface.rejected_reason == code)) for name, code in REJECTION_REASONS.items()
            },
        }
        if args.baseline:
            paintable = reason == PAINT_REASONS["paintable"]
            record["baseline_image_tiles"] = len(adaptive_semantic_tiles(labels, paintable))
        views.append(record)
        print(
            f"[fishnet] {stem}: {surface.triangle_count} triangles from "
            f"{int(surface.report['visible_source_triangles'])} visible support triangles, "
            f"class change {fidelity['changed_fraction']:.4%}, "
            f"phantom {occlusion['phantom_fraction']:.4%}, deleted {occlusion['deleted_fraction']:.4%}, "
            f"occlusion budget {budget['occlusion_budget_fraction']:.3%}",
            flush=True,
        )

    site_budget = aggregate_occlusion_budget(budgets)
    print(
        f"[fishnet] site occlusion budget {site_budget['occlusion_budget_fraction']:.3%} "
        f"(within cell {site_budget['within_cell_fraction']:.3%}, "
        f"absent {site_budget['absent_surface_fraction']:.3%}, "
        f"deferred to other layers {site_budget['deferred_surface_fraction']:.3%}) "
        f"over {site_budget['views']} crops",
        flush=True,
    )
    if site_budget["occlusion_budget_fraction"] > SUB_CELL_REVIEW_FRACTION:
        print(
            f"[fishnet] this site is above the {SUB_CELL_REVIEW_FRACTION:.0%} budget at which treating a face as "
            "fully visible with area scaled by visible_fraction has to be revisited",
            file=sys.stderr,
            flush=True,
        )

    manifest = {
        "method": "support triangles projected into image space and cut at simplified semantic islands",
        "mesh": str(args.mesh),
        "pose": str(args.pose),
        "views_directory": str(args.views),
        "mesh_depth": str(args.mesh_depth),
        "depth_compare": str(args.depth_compare) if args.depth_compare else None,
        "min_confidence": args.min_confidence,
        "min_region_pixels": args.min_region_pixels,
        "depth_break_ratio": args.depth_break_ratio,
        "min_piece_area_px": args.min_piece_area_px,
        "transient_classes": sorted(names[key] for key in transient),
        "non_surface_classes": sorted(names[key] for key in excluded),
        "site_occlusion_budget": site_budget,
        "sub_cell_review_fraction": SUB_CELL_REVIEW_FRACTION,
        "views": views,
    }
    (args.out / "fishnet_manifest.json").write_text(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
