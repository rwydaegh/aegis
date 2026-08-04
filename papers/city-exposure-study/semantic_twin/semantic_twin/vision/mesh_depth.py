"""Render first-hit metric range from the recovered panorama camera into a mesh.

This is deliberately a depth *hypothesis*, not ground truth.  Comparing it to
the independent monocular estimates exposes foreground blockers, broken tile
surfaces, and camera-pose errors before semantic evidence is painted onto a
surface.

The rays are the same ones ``semantic_twin/fishnet.py`` inverts when it maps a
cut piece back onto its triangle's plane, so the depth buffer and the cutter
cannot drift apart.  Casting is vectorised over the whole crop through
``trimesh``, with Embree when it is installed, which is why this no longer needs
Blender.
"""

from __future__ import annotations

import json
import pathlib
from dataclasses import dataclass

import numpy as np
import trimesh

from semantic_twin.pano_geometry import PerspectiveView, panorama_to_world_matrix, perspective_directions


def first_hit_range(
    mesh: trimesh.Trimesh,
    origin: np.ndarray,
    directions: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Range in metres and triangle index of the first hit along each ray.

    Range is ``nan`` and the index is ``-1`` where a ray escapes.  The rays are
    unit vectors, so the reported distance is a true Euclidean range rather than
    a depth along the view axis.
    """
    origin = np.asarray(origin, dtype=np.float64)
    directions = np.asarray(directions, dtype=np.float64)
    if origin.shape != (3,):
        raise ValueError("origin must be one three-vector")
    if directions.ndim != 2 or directions.shape[1] != 3:
        raise ValueError("directions must have shape (n, 3)")
    origins = np.broadcast_to(origin, directions.shape)
    locations, ray_index, triangle_index = mesh.ray.intersects_location(origins, directions, multiple_hits=False)
    range_m = np.full(len(directions), np.nan, dtype=np.float32)
    face_ids = np.full(len(directions), -1, dtype=np.int32)
    if len(ray_index):
        range_m[ray_index] = np.linalg.norm(locations - origin, axis=1)
        face_ids[ray_index] = triangle_index
    return range_m, face_ids


def ground_offset_m(mesh: trimesh.Trimesh, position: np.ndarray, target_height_m: float) -> float:
    """Vertical shift putting the camera ``target_height_m`` above the mesh ground.

    A diagnostic, not a registration fix.  The pose pipeline applies one
    scene-wide terrain constant to every camera, and this measures what that
    constant costs at one panorama by casting straight down against the support
    mesh.  Callers that use it have to record the offset they applied.
    """
    down = np.array([[0.0, 0.0, -1.0]])
    range_m, _face_ids = first_hit_range(mesh, np.asarray(position, dtype=np.float64), down)
    if not np.isfinite(range_m[0]):
        raise ValueError("no support-mesh ground under the camera")
    return float(target_height_m - range_m[0])


@dataclass(frozen=True)
class MeshDepthConfig:
    mesh: pathlib.Path
    pose: pathlib.Path
    views: pathlib.Path
    out: pathlib.Path
    yaws: tuple[int, ...] = (0, 90, 180, 270)
    pitch: float = 0.0
    fov_deg: float = 90.0
    ground_lock_height_m: float | None = None


def render_mesh_depth(config: MeshDepthConfig) -> None:
    from PIL import Image

    args = config
    args.out.mkdir(parents=True, exist_ok=True)
    mesh = trimesh.load(args.mesh, process=False, force="mesh")
    pose = json.loads(args.pose.read_text())
    camera = np.asarray(pose["position_enu_m"], dtype=np.float64)
    rotation = panorama_to_world_matrix(
        float(pose["heading_deg"]),
        pitch_deg=float(pose["pitch_correction_deg"]),
        roll_deg=float(pose["roll_correction_deg"]),
    )
    ground_lock = None
    if args.ground_lock_height_m is not None:
        ground_lock = ground_offset_m(mesh, camera, args.ground_lock_height_m)
        camera = camera + np.array([0.0, 0.0, ground_lock])
        print(f"[mesh-depth] ground lock moved the camera {ground_lock:+.3f} m")

    manifest = []
    for yaw in args.yaws:
        # The image is only used for the dimensions. The depth models and the
        # segmenter consume exactly this crop, so its pixels correspond
        # one-to-one with this map.
        name = f"h{args.pitch:+03.0f}_{yaw:03d}"
        with Image.open(args.views / f"{name}.jpg") as image:
            width, height = image.size
        view = PerspectiveView(name, float(yaw), args.pitch, args.fov_deg)
        local = perspective_directions(view, width, height).reshape(-1, 3)
        range_m, face_ids = first_hit_range(mesh, camera, local @ rotation.T)
        np.savez_compressed(
            args.out / f"{name}.npz",
            range_m=range_m.reshape(height, width),
            face_ids=face_ids.reshape(height, width),
        )
        manifest.append(
            {
                "view": name,
                "shape": [height, width],
                "hit_fraction": float(np.isfinite(range_m).mean()),
                "median_range_m": float(np.nanmedian(range_m)),
            }
        )
        print(f"[mesh-depth] {name}: {manifest[-1]['hit_fraction']:.1%} rays hit")
    (args.out / "manifest.json").write_text(
        json.dumps(
            {
                "mesh": str(args.mesh),
                "pose": str(args.pose),
                "camera_position_enu_m": camera.tolist(),
                "ground_lock_height_m": args.ground_lock_height_m,
                "ground_lock_offset_m": ground_lock,
                "views": manifest,
            },
            indent=2,
        )
    )
