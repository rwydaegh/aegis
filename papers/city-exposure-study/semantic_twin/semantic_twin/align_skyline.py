"""Refine Street View pose by matching its segmented skyline to the tile mesh.

Inhouse metadata gives a strong horizontal/orientation prior but no altitude. This
optimizer compares the panorama's sky boundary with the angular envelope of the
photogrammetry vertices. Ground-level tile noise is therefore absent from the
objective, which is the reason skyline registration is preferred here.
"""

from __future__ import annotations

import argparse
import json
import pathlib

import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import median_filter
from scipy.optimize import differential_evolution

from .pano_geometry import (
    directions_to_equirectangular,
    panorama_to_world_matrix,
    streetview_orientation_prior,
)


def read_binary_ply_vertices(path: pathlib.Path) -> np.ndarray:
    """Read vertices from the compact binary PLY emitted by export_scenes.py."""
    with path.open("rb") as stream:
        first = stream.readline().decode().strip()
        if first != "ply":
            raise ValueError(f"not a PLY file: {path}")
        count = None
        binary_little = False
        while True:
            line = stream.readline().decode().strip()
            if line == "format binary_little_endian 1.0":
                binary_little = True
            if line.startswith("element vertex "):
                count = int(line.rsplit(" ", 1)[1])
            if line == "end_header":
                break
        if not binary_little or count is None:
            raise ValueError("expected binary_little_endian PLY with vertices")
        return np.fromfile(stream, dtype="<f4", count=count * 3).reshape(count, 3)


def observed_skyline(
    entity: np.ndarray,
    sky_id: int,
    n_bins: int,
    structural_ids: set[int] | None = None,
) -> np.ndarray:
    """Bottom edge of the top-connected sky, as panorama-local unit rays."""
    height, width = entity.shape
    columns = np.linspace(0, width - 1, n_bins, dtype=np.int32)
    sky = entity[:, columns] == sky_id
    limit = int(height * 0.72)
    rows = np.arange(limit)[:, None]
    # A pole or cable can punch a tiny hole in otherwise connected sky. The
    # bottommost sky pixel is robust to that and the median removes tree gaps.
    boundary = np.max(np.where(sky[:limit], rows, -1), axis=0)
    boundary[boundary < 0] = int(height * 0.25)
    boundary = median_filter(boundary.astype(float), size=11, mode="wrap")
    if structural_ids:
        sample_row = np.clip(np.rint(boundary + max(2, height // 256)).astype(int), 0, height - 1)
        support = np.isin(entity[sample_row, columns], list(structural_ids))
    else:
        support = np.ones(n_bins, dtype=bool)
    u = (columns + 0.5) / width
    v = (boundary + 0.5) / height
    yaw = (u - 0.5) * 2.0 * np.pi
    pitch = (0.5 - v) * np.pi
    cp = np.cos(pitch)
    rays = np.stack([np.sin(yaw) * cp, np.cos(yaw) * cp, np.sin(pitch)], axis=1)
    return rays[support]


def mesh_skyline(
    vertices: np.ndarray,
    camera: np.ndarray,
    n_bins: int,
    minimum_distance_m: float = 8.0,
) -> np.ndarray:
    delta = vertices - camera
    horizontal = np.hypot(delta[:, 0], delta[:, 1])
    keep = horizontal > minimum_distance_m
    azimuth = np.arctan2(delta[keep, 0], delta[keep, 1])
    elevation = np.arctan2(delta[keep, 2], horizontal[keep])
    bins = np.floor((azimuth / (2.0 * np.pi) + 0.5) * n_bins).astype(int) % n_bins
    skyline = np.full(n_bins, -np.pi / 2.0)
    np.maximum.at(skyline, bins, elevation)
    valid = skyline > -np.pi / 2.0
    if not np.all(valid):
        x = np.arange(n_bins)
        xp = x[valid]
        fp = skyline[valid]
        skyline = np.interp(x, np.r_[xp - n_bins, xp, xp + n_bins], np.tile(fp, 3))
    # The photogrammetry contains thin wires and isolated high vertices. A
    # wider angular median retains sustained roof structure while rejecting
    # narrow spikes that are absent from the structural semantic mask.
    return median_filter(skyline, size=11, mode="wrap")


def candidate_vertices(
    vertices: np.ndarray,
    camera: np.ndarray,
    n_bins: int,
    minimum_distance_m: float = 8.0,
) -> np.ndarray:
    """Retain geometry near the initial angular envelope plus a sparse safety set."""
    delta = vertices - camera
    horizontal = np.hypot(delta[:, 0], delta[:, 1])
    keep = horizontal > minimum_distance_m
    azimuth = np.arctan2(delta[:, 0], delta[:, 1])
    elevation = np.arctan2(delta[:, 2], np.maximum(horizontal, 1e-8))
    bins = np.floor((azimuth / (2.0 * np.pi) + 0.5) * n_bins).astype(int) % n_bins
    initial = mesh_skyline(vertices, camera, n_bins, minimum_distance_m)
    keep &= elevation > initial[bins] - np.radians(4.0)
    keep[::40] = True
    return vertices[keep]


def fit_pose(
    vertices: np.ndarray,
    local_skyline: np.ndarray,
    position: np.ndarray,
    heading_deg: float,
    pitch_prior_deg: float,
    roll_prior_deg: float,
    *,
    n_bins: int,
    maxiter: int,
    minimum_distance_m: float,
) -> tuple[np.ndarray, float]:
    def objective(params: np.ndarray) -> float:
        dx, dy, dz, yaw, pitch_delta, roll_delta = params
        camera = position + np.array([dx, dy, dz])
        model = mesh_skyline(vertices, camera, n_bins, minimum_distance_m)
        rotation = panorama_to_world_matrix(
            heading_deg + yaw,
            pitch_deg=pitch_prior_deg + pitch_delta,
            roll_deg=roll_prior_deg + roll_delta,
        )
        world = local_skyline @ rotation.T
        azimuth = np.arctan2(world[:, 0], world[:, 1])
        elevation = np.arcsin(np.clip(world[:, 2], -1.0, 1.0))
        index = ((azimuth / (2.0 * np.pi) + 0.5) * n_bins) % n_bins
        lo = np.floor(index).astype(int)
        hi = (lo + 1) % n_bins
        frac = index - lo
        predicted = model[lo] * (1.0 - frac) + model[hi] * frac
        residual = np.abs(predicted - elevation)
        cutoff = np.quantile(residual, 0.8)
        robust_error = np.mean(np.minimum(residual, cutoff))
        orientation_prior = 0.001 * ((pitch_delta / 3.0) ** 2 + (roll_delta / 3.0) ** 2)
        return float(robust_error + orientation_prior)

    result = differential_evolution(
        objective,
        bounds=[(-4.0, 4.0), (-4.0, 4.0), (-1.5, 3.0), (-20.0, 20.0), (-6.0, 6.0), (-6.0, 6.0)],
        seed=0xAE615,
        popsize=7,
        maxiter=maxiter,
        polish=True,
        updating="immediate",
    )
    return result.x, float(result.fun)


def draw_diagnostic(
    panorama_path: pathlib.Path,
    output: pathlib.Path,
    local_observed: np.ndarray,
    vertices: np.ndarray,
    camera: np.ndarray,
    heading: float,
    pitch: float,
    roll: float,
    n_bins: int,
    minimum_distance_m: float,
) -> None:
    Image.MAX_IMAGE_PIXELS = None
    with Image.open(panorama_path) as source:
        image = source.resize((2048, 1024)).convert("RGB")
    draw = ImageDraw.Draw(image)
    obs_u, obs_v = directions_to_equirectangular(local_observed)
    observed = [(int(u * image.width), int(v * image.height)) for u, v in zip(obs_u, obs_v, strict=True)]
    for point in observed:
        draw.ellipse((point[0] - 2, point[1] - 2, point[0] + 2, point[1] + 2), fill=(0, 255, 255))

    model = mesh_skyline(vertices, camera, n_bins, minimum_distance_m)
    azimuth = (np.arange(n_bins) / n_bins - 0.5) * 2.0 * np.pi
    cp = np.cos(model)
    world = np.stack([np.sin(azimuth) * cp, np.cos(azimuth) * cp, np.sin(model)], axis=1)
    rotation = panorama_to_world_matrix(heading, pitch_deg=pitch, roll_deg=roll)
    local = world @ rotation
    model_u, model_v = directions_to_equirectangular(local)
    order = np.argsort(model_u)
    predicted = [(int(model_u[i] * image.width), int(model_v[i] * image.height)) for i in order]
    draw.line(predicted, fill=(255, 40, 190), width=3)
    image.save(output, quality=94)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mesh", type=pathlib.Path, required=True)
    parser.add_argument("--semantics", type=pathlib.Path, required=True)
    parser.add_argument("--semantics-json", type=pathlib.Path, required=True)
    parser.add_argument("--pose", type=pathlib.Path, required=True)
    parser.add_argument("--panorama", type=pathlib.Path, required=True)
    parser.add_argument("--out", type=pathlib.Path, required=True)
    parser.add_argument("--bins", type=int, default=1024)
    parser.add_argument("--maxiter", type=int, default=35)
    parser.add_argument("--minimum-skyline-distance", type=float, default=8.0)
    args = parser.parse_args()

    entity = np.load(args.semantics)["entity"]
    semantics_doc = json.loads(args.semantics_json.read_text())
    id2label = {int(k): v for k, v in semantics_doc["entity_id2label"].items()}
    sky_id = next((i for i, label in id2label.items() if label.casefold() == "sky"), None)
    if sky_id is None:
        raise SystemExit("segmentation vocabulary has no sky class")
    pose = json.loads(args.pose.read_text())
    initial_position = np.asarray(pose["position_enu_m"], dtype=float)
    initial_heading = float(pose["heading_deg"])
    pitch_prior, roll_prior = streetview_orientation_prior(
        float(pose.get("tilt_deg", 90.0)),
        float(pose.get("roll_deg", 0.0)),
    )
    vertices = read_binary_ply_vertices(args.mesh)
    structural_ids = {
        class_id for class_id, label in id2label.items() if label.casefold() in {"building", "wall", "bridge", "tunnel"}
    }
    candidates = candidate_vertices(
        vertices,
        initial_position,
        args.bins,
        args.minimum_skyline_distance,
    )
    observed = observed_skyline(entity, sky_id, args.bins, structural_ids)
    if len(observed) < args.bins // 8:
        raise SystemExit(f"only {len(observed)} structurally supported skyline samples")
    params, score = fit_pose(
        candidates,
        observed,
        initial_position,
        initial_heading,
        pitch_prior,
        roll_prior,
        n_bins=args.bins,
        maxiter=args.maxiter,
        minimum_distance_m=args.minimum_skyline_distance,
    )
    dx, dy, dz, yaw, pitch_delta, roll_delta = params
    pitch = pitch_prior + pitch_delta
    roll = roll_prior + roll_delta
    aligned = dict(pose)
    aligned.update(
        {
            "position_enu_m": (initial_position + params[:3]).tolist(),
            "heading_deg": initial_heading + yaw,
            "pitch_correction_deg": pitch,
            "roll_correction_deg": roll,
            "pitch_metadata_prior_deg": pitch_prior,
            "roll_metadata_prior_deg": roll_prior,
            "pitch_metadata_delta_deg": pitch_delta,
            "roll_metadata_delta_deg": roll_delta,
            "skyline_score_mean_rad": score,
            "skyline_score_mean_deg": float(np.degrees(score)),
            "initial_pose": pose,
            "alignment_method": "streetview_orientation_prior_plus_segmented_structural_skyline",
            "n_candidate_vertices": len(candidates),
            "n_observed_structural_skyline_samples": len(observed),
            "minimum_skyline_distance_m": args.minimum_skyline_distance,
        }
    )
    args.out.mkdir(parents=True, exist_ok=True)
    pose_path = args.out / "pose_aligned.json"
    pose_path.write_text(json.dumps(aligned, indent=2))
    draw_diagnostic(
        args.panorama,
        args.out / "skyline_alignment.jpg",
        observed,
        vertices,
        np.asarray(aligned["position_enu_m"]),
        float(aligned["heading_deg"]),
        float(aligned["pitch_correction_deg"]),
        float(aligned["roll_correction_deg"]),
        args.bins,
        args.minimum_skyline_distance,
    )
    print(f"[align] correction xyz={params[:3].round(3).tolist()} m")
    print(f"[align] residual correction ypr={params[3:].round(3).tolist()} deg")
    print(f"[align] total pitch/roll={[round(pitch, 3), round(roll, 3)]} deg")
    print(f"[align] mean robust skyline error={np.degrees(score):.3f} deg")
    print(f"[align] -> {pose_path}")


if __name__ == "__main__":
    main()
