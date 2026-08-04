"""The command that registers one panorama against a site's support mesh.

It reads the segmented entity raster and the provider's pose, fits the skyline
objective of :mod:`~semantic_twin.vision.register` from several independent
optimiser seeds, runs the independent sky conflict check of
:mod:`~semantic_twin.vision.conflict`, and writes ``pose_aligned.json``.

That file is the input to every piece of image evidence in the study, and
:class:`~semantic_twin.vision.provenance.Registration` is what reads it back.
Note that this command writes the residual, the ensemble covariance and the sky
conflict but takes no view on whether the pose is usable. The admission gate
lives with the provenance types, so one place decides and every consumer asks
it::

    ../../../.venv/bin/python -m semantic_twin.cli.align \\
        --mesh data/geometry/korenmarkt/inhouse_leaf_130m_f64.ply \\
        --semantics data/panoramas/korenmarkt/semantics/panorama_semantics.npz \\
        --semantics-json data/panoramas/korenmarkt/semantics/semantics.json \\
        --pose data/panoramas/korenmarkt/pose.json \\
        --out data/panoramas/korenmarkt/alignment
"""

from __future__ import annotations

import json
import pathlib
from dataclasses import dataclass
from typing import Any

import numpy as np
from PIL import Image, ImageDraw

from ..pano_geometry import (
    directions_to_equirectangular,
    panorama_to_world_matrix,
    streetview_orientation_prior,
)
from ..scene.camera_ground import ground_elevation
from ..scene.mesh import read_binary_ply
from .conflict import sky_conflict
from .register import (
    SkylineSettings,
    _bounds,
    candidate_vertices,
    mesh_skyline,
    observed_skyline,
    profile_intervals,
    seed_study,
    signed_skyline_residual,
    skyline_cost,
)

STRUCTURAL_LABELS = frozenset({"building", "wall", "bridge", "tunnel"})


@dataclass(frozen=True)
class AlignmentConfig:
    """Inputs for registering one panorama against its support mesh."""

    mesh: pathlib.Path
    semantics: pathlib.Path
    semantics_json: pathlib.Path
    pose: pathlib.Path
    panorama: pathlib.Path | None
    out: pathlib.Path
    bins: int
    maxiter: int
    minimum_skyline_distance: float
    skyline_percentile: float
    smoothing_size: int
    dz_bounds: tuple[float, float]
    fit_bias: tuple[float, float]
    seeds: tuple[int, ...]
    ground_from_mesh: bool
    ground_patch_m: float
    camera_height_m: float | None
    sky_conflict: bool
    sky_conflict_width: int
    profile: bool
    profile_tolerance_deg: float


def draw_diagnostic(
    panorama_path: pathlib.Path,
    output: pathlib.Path,
    local_observed: np.ndarray,
    vertices: np.ndarray,
    camera: np.ndarray,
    heading: float,
    pitch: float,
    roll: float,
    settings: SkylineSettings,
) -> None:
    Image.MAX_IMAGE_PIXELS = None
    with Image.open(panorama_path) as source:
        image = source.resize((2048, 1024)).convert("RGB")
    draw = ImageDraw.Draw(image)
    obs_u, obs_v = directions_to_equirectangular(local_observed)
    observed = [(int(u * image.width), int(v * image.height)) for u, v in zip(obs_u, obs_v, strict=True)]
    for point in observed:
        draw.ellipse((point[0] - 2, point[1] - 2, point[0] + 2, point[1] + 2), fill=(0, 255, 255))

    model = mesh_skyline(
        vertices,
        camera,
        settings.n_bins,
        settings.minimum_distance_m,
        smoothing_size=settings.smoothing_size,
        smoothing_percentile=settings.smoothing_percentile,
    )
    azimuth = (np.arange(settings.n_bins) / settings.n_bins - 0.5) * 2.0 * np.pi
    cp = np.cos(model)
    world = np.stack([np.sin(azimuth) * cp, np.cos(azimuth) * cp, np.sin(model)], axis=1)
    rotation = panorama_to_world_matrix(heading, pitch_deg=pitch, roll_deg=roll)
    local = world @ rotation
    model_u, model_v = directions_to_equirectangular(local)
    order = np.argsort(model_u)
    predicted = [(int(model_u[i] * image.width), int(model_v[i] * image.height)) for i in order]
    draw.line(predicted, fill=(255, 40, 190), width=3)
    image.save(output, quality=94)


def _semantic_ids(document: dict[str, Any]) -> tuple[int, set[int], dict[int, str]]:
    id2label = {int(key): value for key, value in document["entity_id2label"].items()}
    sky_id = next((index for index, label in id2label.items() if label.casefold() == "sky"), None)
    if sky_id is None:
        raise SystemExit("segmentation vocabulary has no sky class")
    structural = {index for index, label in id2label.items() if label.casefold() in STRUCTURAL_LABELS}
    return sky_id, structural, id2label


def run_alignment(config: AlignmentConfig) -> None:
    entity = np.load(config.semantics)["entity"]
    sky_id, structural_ids, _ = _semantic_ids(json.loads(config.semantics_json.read_text()))
    pose = json.loads(config.pose.read_text())
    initial_position = np.asarray(pose["position_enu_m"], dtype=float)
    initial_heading = float(pose["heading_deg"])
    pitch_prior, roll_prior = streetview_orientation_prior(
        float(pose.get("tilt_deg", 90.0)),
        float(pose.get("roll_deg", 0.0)),
    )

    vertices, faces = read_binary_ply(config.mesh)

    ground: dict[str, Any] = {}
    if config.ground_from_mesh:
        camera_height = float(config.camera_height_m or pose.get("camera_height_m", 2.5))
        sample = ground_elevation(
            vertices,
            faces,
            float(initial_position[0]),
            float(initial_position[1]),
            ceiling_z_m=float(initial_position[2]),
            patch_m=config.ground_patch_m,
        )
        ground = sample.as_dict()
        ground["camera_height_m"] = camera_height
        ground["camera_height_source"] = (
            "measured, supplied on the command line" if config.camera_height_m else "scene config"
        )
        ground["scene_constant_z_m"] = float(initial_position[2] - float(pose.get("camera_height_m", 2.5)))
        ground["correction_m"] = float(sample.elevation_m + camera_height - initial_position[2])
        initial_position = np.array([initial_position[0], initial_position[1], sample.elevation_m + camera_height])
        print(f"[align] ground under camera {sample.elevation_m:.3f} m, correction {ground['correction_m']:+.3f} m")

    settings = SkylineSettings(
        n_bins=config.bins,
        minimum_distance_m=config.minimum_skyline_distance,
        smoothing_size=config.smoothing_size,
        smoothing_percentile=config.skyline_percentile,
    )
    bias_bounds = None if config.fit_bias == (0.0, 0.0) else config.fit_bias
    dz_bounds = (float(config.dz_bounds[0]), float(config.dz_bounds[1]))
    candidates = candidate_vertices(
        vertices,
        initial_position,
        settings.n_bins,
        settings.minimum_distance_m,
        search_box_m=((-4.0, 4.0), (-4.0, 4.0), dz_bounds),
        smoothing_size=settings.smoothing_size,
        smoothing_percentile=settings.smoothing_percentile,
    )
    observed = observed_skyline(entity, sky_id, settings.n_bins, structural_ids)
    if len(observed) < settings.n_bins // 8:
        raise SystemExit(f"only {len(observed)} structurally supported skyline samples")

    fit_kwargs: dict[str, Any] = {
        "settings": settings,
        "maxiter": config.maxiter,
        "dz_bounds": dz_bounds,
        "bias_bounds_deg": bias_bounds,
    }
    ensemble = seed_study(
        candidates,
        observed,
        initial_position,
        initial_heading,
        pitch_prior,
        roll_prior,
        seeds=config.seeds,
        progress=True,
        **fit_kwargs,
    )
    best = ensemble.best
    dx, dy, dz, yaw, pitch_delta, roll_delta = best.params
    pitch = pitch_prior + pitch_delta
    roll = roll_prior + roll_delta
    camera = initial_position + best.params[:3]

    cost_kwargs = {
        "vertices": candidates,
        "local_skyline": observed,
        "position": initial_position,
        "heading_deg": initial_heading,
        "pitch_prior_deg": pitch_prior,
        "roll_prior_deg": roll_prior,
        "settings": settings,
    }
    best_vector = np.r_[best.params, best.bias_deg] if bias_bounds is not None else best.params
    reprune = candidate_vertices(
        vertices,
        camera,
        settings.n_bins,
        settings.minimum_distance_m,
        smoothing_size=settings.smoothing_size,
        smoothing_percentile=settings.smoothing_percentile,
    )
    recheck = skyline_cost(best_vector, **{**cost_kwargs, "vertices": reprune})
    signed = signed_skyline_residual(best_vector, **cost_kwargs)

    aligned = dict(pose)
    aligned.update(
        {
            "position_enu_m": camera.tolist(),
            "heading_deg": initial_heading + yaw,
            "pitch_correction_deg": pitch,
            "roll_correction_deg": roll,
            "pitch_metadata_prior_deg": pitch_prior,
            "roll_metadata_prior_deg": roll_prior,
            "pitch_metadata_delta_deg": pitch_delta,
            "roll_metadata_delta_deg": roll_delta,
            "skyline_score_mean_rad": best.cost,
            "skyline_score_mean_deg": best.residual_deg,
            "skyline_bias_deg": best.bias_deg,
            "skyline_signed_residual_median_deg": float(np.degrees(np.median(signed))),
            "skyline_smoothing_percentile": settings.smoothing_percentile,
            "skyline_dz_bounds_m": list(dz_bounds),
            "skyline_dz_at_bound": bool(min(abs(dz - dz_bounds[0]), abs(dz - dz_bounds[1])) < 0.1),
            "pose_uncertainty": ensemble.as_dict(),
            "skyline_start_position_enu_m": initial_position.tolist(),
            "candidate_prune_recheck_deg": float(np.degrees(recheck) - best.residual_deg),
            "initial_pose": pose,
            "alignment_method": "streetview_orientation_prior_plus_segmented_structural_skyline",
            "n_candidate_vertices": len(candidates),
            "n_observed_structural_skyline_samples": len(observed),
            "minimum_skyline_distance_m": settings.minimum_distance_m,
        }
    )
    if ground:
        aligned["ground_measurement"] = ground

    if config.sky_conflict:
        try:
            conflict = sky_conflict(
                vertices,
                faces,
                entity,
                sky_id,
                structural_ids,
                camera,
                heading_deg=initial_heading + yaw,
                pitch_deg=pitch,
                roll_deg=roll,
                width=config.sky_conflict_width,
                height=config.sky_conflict_width // 2,
            )
        except ImportError as exc:
            aligned["sky_conflict"] = {"unavailable": str(exc)}
            print(f"[align] sky conflict skipped: {exc}")
        else:
            aligned["sky_conflict"] = conflict.as_dict()
            print(
                f"[align] sky with mesh hit {conflict.sky_with_mesh:.4f}, "
                f"structure without mesh hit {conflict.structure_without_mesh:.4f}"
            )

    if config.profile:
        aligned["pose_profile"] = profile_intervals(
            best_vector,
            _bounds(
                dz_bounds,
                translation_m=4.0,
                yaw_deg=20.0,
                orientation_deg=6.0,
                bias_bounds_deg=bias_bounds,
            ),
            tolerance_deg=config.profile_tolerance_deg,
            **cost_kwargs,
        )

    config.out.mkdir(parents=True, exist_ok=True)
    pose_path = config.out / "pose_aligned.json"
    pose_path.write_text(json.dumps(aligned, indent=2))
    if config.panorama is not None:
        draw_diagnostic(
            config.panorama,
            config.out / "skyline_alignment.jpg",
            observed,
            vertices,
            camera,
            float(aligned["heading_deg"]),
            pitch,
            roll,
            settings,
        )
    deviation = np.sqrt(np.diag(ensemble.covariance))
    print(f"[align] correction xyz={best.params[:3].round(3).tolist()} m")
    print(f"[align] residual correction ypr={best.params[3:].round(3).tolist()} deg")
    print(f"[align] total pitch/roll={[round(pitch, 3), round(roll, 3)]} deg")
    print(f"[align] mean robust skyline error={best.residual_deg:.3f} deg, bias={best.bias_deg:+.3f} deg")
    print(
        f"[align] seed spread 1 sigma xyz={deviation[:3].round(3).tolist()} m ypr={deviation[3:6].round(3).tolist()} deg"
    )
    print(f"[align] -> {pose_path}")
