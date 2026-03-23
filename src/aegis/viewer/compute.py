"""Dosimetry computation for the interactive viewer."""

from __future__ import annotations

import time

import numpy as np

from aegis.engine import DosimetryEngine
from aegis.geometry.mesh import BodyMesh
from aegis.paths import PropagationPaths
from aegis.tissue.dielectric import FAT_28GHZ, MUSCLE_28GHZ, SKIN_28GHZ, SKIN_60GHZ, TissueModel
from aegis.viewer.config import DEFAULTS

# Cache for curvature computation (expensive, only changes when body changes)
_curvature_cache: dict = {}


def _compute_face_curvature(body: BodyMesh) -> np.ndarray:
    """Estimate per-face mean curvature from normal variation to neighbors.

    Uses KD-tree for fast neighbor lookup: for each face, the curvature
    is estimated as the average |delta_normal| / distance to its 6 nearest
    neighbors. This gives a good proxy for the discrete mean curvature.
    """
    cache_key = id(body)
    if cache_key in _curvature_cache:
        return _curvature_cache[cache_key]

    from scipy.spatial import cKDTree

    centroids = body.centroids
    normals = body.normals
    M = body.n_triangles

    k = min(7, M)
    tree = cKDTree(centroids)
    dists, indices = tree.query(centroids, k=k)

    neighbor_normals = normals[indices]
    face_normals = normals[:, np.newaxis, :]
    delta_n = np.linalg.norm(neighbor_normals - face_normals, axis=2)
    safe_dists = np.maximum(dists, 1e-12)
    curvature_per_neighbor = delta_n / safe_dists

    H = np.mean(curvature_per_neighbor[:, 1:], axis=1)

    _curvature_cache.clear()
    _curvature_cache[cache_key] = H
    return H


# Predefined tissue presets (aligned with dielectric.py literature values)
TISSUE_PRESETS = {
    "skin_28ghz": SKIN_28GHZ,
    "skin_60ghz": SKIN_60GHZ,
    "muscle_28ghz": MUSCLE_28GHZ,
    "fat_28ghz": FAT_28GHZ,
}


def _rotation_matrix_z(angle: float) -> np.ndarray:
    """Build a rotation matrix around the Z axis (yaw in Z-up coords)."""
    c, s = np.cos(angle), np.sin(angle)
    return np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])


def _transform_body_for_viewer(
    body: BodyMesh,
    body_offset: np.ndarray,
    body_rotation_y: float,
) -> BodyMesh:
    """Apply viewer yaw (Z-up) and translation; keeps vertices, centroids, normals consistent.

    Previously, only normals and centroids were rotated while vertices stayed fixed, which
    breaks triangle geometry and mis-places coherent phases. Offset must move the mesh,
    not only the aim point used for k_hat.
    """
    off = np.asarray(body_offset, dtype=np.float64).reshape(3)
    rigid = abs(body_rotation_y) > 1e-9 or np.any(np.abs(off) > 1e-12)
    if not rigid:
        return body

    if abs(body_rotation_y) > 1e-9:
        R = _rotation_matrix_z(body_rotation_y)
        vertices = body.vertices @ R.T
        normals = body.normals @ R.T
        centroids = body.centroids @ R.T
    else:
        vertices = body.vertices
        normals = body.normals
        centroids = body.centroids

    vertices = vertices + off.reshape(1, 1, 3)
    centroids = centroids + off

    return BodyMesh(
        vertices=vertices,
        normals=normals,
        centroids=centroids,
        areas=body.areas,
        name=body.name,
    )


def compute_dosimetry(
    body: BodyMesh,
    antenna_pos: np.ndarray,
    body_offset: np.ndarray | None = None,
    body_rotation_y: float = 0.0,
    level: int | None = 2,
    mode: str | None = None,
    corrections: dict | None = None,
    tissue: TissueModel | None = None,
    power_dbm: float = 30.0,
    n_paths: int = 1,
    config: dict | None = None,
    stochastic: dict | None = None,
) -> dict:
    """Run dosimetry from a single antenna position toward the body.

    Parameters
    ----------
    body : the body mesh
    antenna_pos : (3,) antenna position in scene coordinates [meters]
    body_offset : (3,) translation applied to all triangle vertices [meters]
    body_rotation_y : yaw angle [radians], Three.js Y-rotation mapped to Z-rotation in Z-up
    level : fidelity level 0-8 (legacy API, used when mode is None)
    mode : computation mode (bound, aggregate, spatial)
    corrections : dict of correction flags (fresnel, polarisation, curvature, diffraction)
    tissue : tissue model (defaults to skin at 28 GHz)
    power_dbm : transmit power [dBm]
    n_paths : number of synthetic paths (1 = single plane wave)
    config : viewer config dict

    Returns
    -------
    dict with keys: sab (float32 bytes), p_abs, peak_sab, compliant, n_illuminated
    """
    timings: dict[str, float] = {}
    t_total = time.perf_counter()

    cfg = config or DEFAULTS
    dos_cfg = cfg["dosimetry"]
    sp_cfg = dos_cfg["synthetic_paths"]

    if tissue is None:
        tissue = SKIN_28GHZ

    antenna_pos = np.asarray(antenna_pos, dtype=np.float64)
    body_offset = np.asarray(body_offset, dtype=np.float64) if body_offset is not None else np.zeros(3)

    t0 = time.perf_counter()
    rotated_body = _transform_body_for_viewer(body, body_offset, body_rotation_y)
    body_center = rotated_body.centroids.mean(axis=0)
    timings["body_transform_ms"] = (time.perf_counter() - t0) * 1e3

    # Direction from antenna to body
    direction = body_center - antenna_pos
    dist = np.linalg.norm(direction)
    if dist < 1e-6:
        dist = 1.0
    k_hat = direction / dist

    # Power at body surface (free-space path loss)
    tx_power_w = 10 ** ((power_dbm - 30) / 10)
    # Effective isotropic power density at distance
    S_inc = tx_power_w / (4 * np.pi * dist**2) if dist > 0.1 else tx_power_w

    if stochastic:
        from pathlib import Path

        from aegis.channel import generate_channel, load_preset

        preset_dir = Path(cfg.get("dosimetry", {}).get("stochastic", {}).get("preset_dir", "data/channel_presets"))
        if not preset_dir.is_absolute():
            preset_dir = Path(__file__).resolve().parents[2] / preset_dir
        preset = load_preset(stochastic["preset"], preset_dir)
        paths = generate_channel(
            preset["params"],
            freq_ghz=stochastic.get("freq_ghz", 28),
            antenna_pos=antenna_pos,
            body_center=body_center,
            power_dbm=power_dbm,
            seed=stochastic.get("seed", 42),
            overrides=stochastic.get("overrides"),
        )
    elif n_paths == 1:
        # Single plane wave
        paths = PropagationPaths.from_powers(
            k_hat=k_hat[np.newaxis, :],
            power=np.array([S_inc]),
        )
    else:
        # Multiple synthetic paths with some angular spread
        rng = np.random.default_rng(sp_cfg["seed"])
        k_hats = np.tile(k_hat, (n_paths, 1))
        # Add angular jitter
        jitter = rng.normal(0, sp_cfg["angular_jitter_std"], size=(n_paths, 3))
        k_hats += jitter
        norms = np.linalg.norm(k_hats, axis=1, keepdims=True)
        k_hats = k_hats / np.where(norms > 0, norms, 1.0)

        # Power decreases for scattered paths
        powers = np.full(n_paths, S_inc)
        lo, hi = sp_cfg["scatter_power_range"]
        powers[1:] *= rng.uniform(lo, hi, size=n_paths - 1)

        paths = PropagationPaths.from_powers(k_hat=k_hats, power=powers)

    engine = DosimetryEngine(tissue)
    t0 = time.perf_counter()

    if mode is not None:
        # New mode-based API from frontend
        corr = corrections or {}
        if mode == "bound":
            A_ab = body.total_area * dos_cfg["convex_body_area_factor"]
            D_max = dos_cfg["level0_D_max"]
            result = engine.compute(rotated_body, paths, mode="bound", A_ab=A_ab, D_max=D_max)
        elif mode == "aggregate":
            A_ab = body.total_area * dos_cfg["convex_body_area_factor"]
            result = engine.compute(rotated_body, paths, mode="aggregate", A_ab=A_ab)
        else:
            # spatial mode with correction flags
            mode_kwargs: dict = {"mode": "spatial"}
            mode_kwargs["fresnel"] = corr.get("fresnel", True)
            if corr.get("polarisation"):
                mode_kwargs["polarisation"] = True
                mode_kwargs["q"] = 1.0  # short dipole TM-polarized
            if corr.get("curvature") or corr.get("diffraction"):
                mode_kwargs["curvature"] = True
                mode_kwargs["curvature_H"] = _compute_face_curvature(rotated_body)
            if corr.get("diffraction"):
                mode_kwargs["diffraction"] = True
            result = engine.compute(rotated_body, paths, **mode_kwargs)
    else:
        # Legacy level-based API
        if level is None:
            level = 2
        extra_kwargs: dict = {}
        if level <= 1:
            extra_kwargs["A_ab"] = body.total_area * dos_cfg["convex_body_area_factor"]
            if level == 0:
                extra_kwargs["D_max"] = dos_cfg["level0_D_max"]
            result = engine.compute(rotated_body, paths, level=level, **extra_kwargs)
        elif level <= 6:
            mode_kwargs2: dict = {"mode": "spatial"}
            if level == 2:
                mode_kwargs2["fresnel"] = False
            if level >= 4:
                mode_kwargs2["polarisation"] = True
                mode_kwargs2["q"] = 1.0
            if level >= 5:
                mode_kwargs2["curvature"] = True
                mode_kwargs2["curvature_H"] = _compute_face_curvature(rotated_body)
            if level == 6:
                mode_kwargs2["diffraction"] = True
            result = engine.compute(rotated_body, paths, **mode_kwargs2)
        else:
            result = engine.compute(rotated_body, paths, level=level, **extra_kwargs)

    timings["engine_compute_ms"] = (time.perf_counter() - t0) * 1e3
    timings["total_ms"] = (time.perf_counter() - t_total) * 1e3

    # Pull fine-grained timings from engine
    from aegis.engine import _last_timings as engine_timings

    timings.update(engine_timings)

    extra = {
        "S_inc": float(S_inc),
        "distance_m": float(dist),
        "timings": timings,
    }

    corr_list = None
    if mode is not None:
        corr = corrections or {}
        corr_list = [k for k in ("fresnel", "polarisation", "curvature", "diffraction") if corr.get(k)]

    return result, body, tissue, level, mode, corr_list, extra
