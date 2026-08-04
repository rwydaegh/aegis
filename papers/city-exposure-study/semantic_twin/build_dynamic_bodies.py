"""Place SAM 3D Body reconstructions into scene ENU as a transient layer.

Reads the camera-frame reconstructions written by ``infer_sam3_body.py``, the
recovered panorama pose, the support mesh, and, when it is trustworthy, the
fused depth evidence.  Writes one ``DynamicBodyArtifact`` per person.

Bodies never enter the static semantic atlas.  The fishnet already withholds
their pixels as ``transient_object``, and this is the layer that puts back what
was withheld, as posable geometry rather than as paint on the wall behind them.
No exposure is computed here.

Range comes from evidence rather than from the model's apparent-size guess
whenever the depth fusion is usable, and the correction is radial so the bearing
the segmenter measured is preserved.  Everything the placement is unsure about
is carried in ``BodyUncertainty`` instead of being averaged away.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

import numpy as np
import trimesh

ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from raycast_mesh_depth import first_hit_range  # noqa: E402
from semantic_twin.vision.bodies import (  # noqa: E402
    BodyUncertainty,
    build_dynamic_body_artifact,
    camera_basis_from_pose,
    enu_to_camera,
    project_camera_points,
    range_corrected_translation,
)
from semantic_twin.pano_geometry import panorama_to_world_matrix  # noqa: E402

# Decision codes written by compare_mesh_depth.py.  Only these two mean the
# distance test ran and produced a number worth using for a person's range.
USABLE_DEPTH_DECISIONS = (1, 2, 5)


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reconstructions", type=pathlib.Path, required=True, help="output of infer_sam3_body.py")
    parser.add_argument("--pose", type=pathlib.Path, required=True)
    parser.add_argument("--mesh", type=pathlib.Path, required=True)
    parser.add_argument("--depth-compare", type=pathlib.Path, help="fused decisions, used only when not degraded")
    parser.add_argument("--mesh-depth", type=pathlib.Path, help="mesh first-hit buffers, for the range upper bound")
    parser.add_argument("--out", type=pathlib.Path, required=True)
    parser.add_argument("--fov-deg", type=float, default=90.0)
    return parser.parse_args()


def _view_yaw_pitch(view_id: str) -> tuple[float, float]:
    """Read the crop orientation back out of its ``hSSS_YYY`` stem."""
    pitch, yaw = view_id.split("_")
    return float(yaw), float(pitch[1:])


def _mask(document: np.lib.npyio.NpzFile) -> np.ndarray:
    shape = tuple(int(value) for value in document["mask_shape"])
    return np.unpackbits(document["instance_mask"], count=shape[0] * shape[1]).reshape(shape).astype(bool)


def _evidence_range_m(
    view_id: str,
    mask: np.ndarray,
    depth_compare: pathlib.Path | None,
    mesh_depth: pathlib.Path | None,
) -> tuple[float | None, float | None, str]:
    """Range to the person from the depth fusion, plus the mesh upper bound.

    A person stands in front of whatever the mesh puts behind them, so the mesh
    first hit over their mask is an upper bound and never a measurement.  The
    fused monocular range is a measurement, but only where the fusion says its
    distance test actually ran.
    """
    mesh_range = None
    if mesh_depth is not None and (mesh_depth / f"{view_id}.npz").exists():
        with np.load(mesh_depth / f"{view_id}.npz") as document:
            behind = np.asarray(document["range_m"], dtype=np.float64)[mask]
        behind = behind[np.isfinite(behind) & (behind > 0.0)]
        if behind.size:
            mesh_range = float(np.median(behind))
    if depth_compare is None or not (depth_compare / f"{view_id}.npz").exists():
        return None, mesh_range, "no_depth_fusion"
    with np.load(depth_compare / f"{view_id}.npz") as document:
        withheld = "depth_evidence" in document.files and not bool(document["depth_evidence"])
        if withheld:
            return None, mesh_range, "depth_fusion_degraded"
        decision = np.asarray(document["decision"])[mask]
        scaled = np.asarray(document["unidepth_scaled_range_m"], dtype=np.float64)[mask]
    usable = np.isin(decision, USABLE_DEPTH_DECISIONS) & np.isfinite(scaled) & (scaled > 0.0)
    if usable.sum() < 32:
        return None, mesh_range, "too_few_usable_depth_pixels"
    return float(np.median(scaled[usable])), mesh_range, "fused_monocular_depth"


def main() -> None:
    args = arguments()
    args.out.mkdir(parents=True, exist_ok=True)
    pose = json.loads(args.pose.read_text())
    origin = np.asarray(pose["position_enu_m"], dtype=np.float64)
    rotation = panorama_to_world_matrix(
        float(pose["heading_deg"]),
        pitch_deg=float(pose["pitch_correction_deg"]),
        roll_deg=float(pose["roll_correction_deg"]),
    )
    pose_residual_deg = float(pose.get("skyline_score_mean_deg", 0.0))
    mesh = trimesh.load(args.mesh, process=False, force="mesh")

    records: list[dict[str, object]] = []
    for path in sorted(args.reconstructions.glob("*.npz")):
        with np.load(path, allow_pickle=False) as document:
            metadata = json.loads(str(document["metadata_json"].item()))
            vertices = document["vertices_camera_raw_m"]
            faces = document["faces"]
            keypoints = document["keypoints_camera_raw_m"]
            keypoints_px = document["keypoints_image_px"]
            intrinsics = document["intrinsics"]
            raw_translation = document["pred_cam_t_m"]
            mask = _mask(document)

        view_id = metadata["view_id"]
        yaw_deg, pitch_deg = _view_yaw_pitch(view_id)
        basis = camera_basis_from_pose(rotation, yaw_deg, pitch_deg)
        evidence_range, mesh_range, range_source = _evidence_range_m(view_id, mask, args.depth_compare, args.mesh_depth)
        translation, range_provenance, disagreement = range_corrected_translation(raw_translation, evidence_range)

        source_view_id = f"{args.pose.parent.name}/{view_id}"
        common = {
            "body_id": metadata["body_id"],
            "source_view_id": source_view_id,
            "vertices_camera_raw_m": vertices,
            "faces": faces,
            "keypoints_camera_raw_m": keypoints,
            "pred_cam_t_m": translation,
            "camera_origin_enu_m": origin,
            "camera_basis_enu": basis,
        }
        # The body stands on the ground, so the floor ray goes down from above
        # the placed body rather than from the camera, which would hit the body.
        unfloored = build_dynamic_body_artifact(**common)
        above = np.array(
            [
                float(unfloored.vertices_enu_m[:, 0].mean()),
                float(unfloored.vertices_enu_m[:, 1].mean()),
                float(unfloored.vertices_enu_m[:, 2].max()) + 1.0,
            ]
        )
        drop, _face = first_hit_range(mesh, above, np.array([[0.0, 0.0, -1.0]]))
        floor_point = None if not np.isfinite(drop[0]) else np.array([above[0], above[1], above[2] - float(drop[0])])
        floor_std = (
            None if floor_point is None else abs(float(unfloored.vertices_enu_m[:, 2].min()) - float(floor_point[2]))
        )

        # Round trip through ENU and back, so the residual tests the placement
        # rather than only the intrinsics it started from.
        reprojected = project_camera_points(enu_to_camera(unfloored.keypoints_enu_m, origin, basis), intrinsics)
        finite = np.all(np.isfinite(keypoints_px[:, :2]), axis=1)
        rmse = (
            float(np.sqrt(np.mean(np.sum((reprojected[finite] - keypoints_px[finite, :2]) ** 2, axis=1))))
            if finite.any()
            else None
        )
        body_range = float(np.linalg.norm(translation))
        artifact = build_dynamic_body_artifact(
            **common,
            support_floor_point_enu_m=floor_point,
            uncertainty=BodyUncertainty(
                reconstruction_std_m=disagreement,
                camera_pose_std_m=(
                    body_range * float(np.tan(np.deg2rad(pose_residual_deg))) if pose_residual_deg > 0.0 else None
                ),
                floor_std_m=floor_std,
                reprojection_rmse_px=rmse,
                depth_mesh_disagreement_m=(
                    abs(evidence_range - mesh_range) if evidence_range is not None and mesh_range is not None else None
                ),
            ),
        )
        artifact.save(args.out / f"{artifact.body_id}.npz")
        records.append(
            {
                "body_id": artifact.body_id,
                "view": view_id,
                "range_source": range_source,
                "range_provenance": range_provenance,
                "sam_range_m": float(np.linalg.norm(raw_translation)),
                "evidence_range_m": evidence_range,
                "mesh_upper_bound_range_m": mesh_range,
                "placed_range_m": body_range,
                "placement_provenance": artifact.placement_provenance,
                "floor_shift_m": float(artifact.floor_shift_enu_m[2]),
                "stature_m": float(np.ptp(artifact.vertices_enu_m[:, 2])),
                "centroid_enu_m": artifact.vertices_enu_m.mean(axis=0).tolist(),
                "uncertainty": {
                    "reconstruction_std_m": artifact.uncertainty.reconstruction_std_m,
                    "camera_pose_std_m": artifact.uncertainty.camera_pose_std_m,
                    "floor_std_m": artifact.uncertainty.floor_std_m,
                    "reprojection_rmse_px": artifact.uncertainty.reprojection_rmse_px,
                    "depth_mesh_disagreement_m": artifact.uncertainty.depth_mesh_disagreement_m,
                },
            }
        )
        print(
            f"[bodies] {artifact.body_id}: range {body_range:.2f} m ({range_provenance}), "
            f"stature {records[-1]['stature_m']:.2f} m, floor shift {records[-1]['floor_shift_m']:+.2f} m, "
            f"reprojection {'n/a' if rmse is None else f'{rmse:.1f} px'}",
            flush=True,
        )

    (args.out / "dynamic_bodies_manifest.json").write_text(
        json.dumps(
            {
                "layer": "transient, never baked into the static semantic atlas",
                "exposure": "not computed here",
                "pose": str(args.pose),
                "mesh": str(args.mesh),
                "reconstructions": str(args.reconstructions),
                "depth_compare": str(args.depth_compare) if args.depth_compare else None,
                "bodies": records,
            },
            indent=2,
        )
    )
    print(f"[bodies] placed {len(records)} bodies", flush=True)


if __name__ == "__main__":
    main()
