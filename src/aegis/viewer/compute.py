"""Dosimetry computation for the interactive viewer."""

from __future__ import annotations

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
    level: int = 2,
    tissue: TissueModel | None = None,
    power_dbm: float = 30.0,
    n_paths: int = 1,
    config: dict | None = None,
) -> dict:
    """Run dosimetry from a single antenna position toward the body.

    Parameters
    ----------
    body : the body mesh
    antenna_pos : (3,) antenna position in scene coordinates [meters]
    body_offset : (3,) translation applied to all triangle vertices [meters]
    body_rotation_y : yaw angle [radians], Three.js Y-rotation mapped to Z-rotation in Z-up
    level : fidelity level 0-6
    tissue : tissue model (defaults to skin at 28 GHz)
    power_dbm : transmit power [dBm]
    n_paths : number of synthetic paths (1 = single plane wave)
    config : viewer config dict

    Returns
    -------
    dict with keys: sab (float32 bytes), p_abs, peak_sab, compliant, n_illuminated
    """
    cfg = config or DEFAULTS
    dos_cfg = cfg["dosimetry"]
    sp_cfg = dos_cfg["synthetic_paths"]

    if tissue is None:
        tissue = SKIN_28GHZ

    antenna_pos = np.asarray(antenna_pos, dtype=np.float64)
    body_offset = np.asarray(body_offset, dtype=np.float64) if body_offset is not None else np.zeros(3)

    rotated_body = _transform_body_for_viewer(body, body_offset, body_rotation_y)
    body_center = rotated_body.centroids.mean(axis=0)

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

    if n_paths == 1:
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

    # Levels 0-1 need precomputed geometry parameters
    extra_kwargs: dict = {}
    if level <= 1:
        # A_ab = total surface area for convex bodies (monograph eq. 2.23)
        extra_kwargs["A_ab"] = body.total_area * dos_cfg["convex_body_area_factor"]
    if level == 0:
        # D_max ~ 4 is a reasonable bound for human bodies (sphere = 4)
        extra_kwargs["D_max"] = dos_cfg["level0_D_max"]

    # Level 4: short dipole is TM-polarized (theta-hat), q = 1.0
    if level == 4:
        extra_kwargs["q"] = 1.0

    # Levels 5-6: compute surface curvature from the mesh
    if level >= 5:
        extra_kwargs["curvature_H"] = _compute_face_curvature(rotated_body)

    result = engine.compute(rotated_body, paths, level=level, **extra_kwargs)

    sab_bytes = result.sab.astype(np.float32).tobytes()

    threshold = dos_cfg["compliance_threshold"]

    return {
        "sab_bytes": sab_bytes,
        "p_abs": float(result.p_abs),
        "p_abs_mw": float(result.p_abs * 1e3),
        "peak_sab": float(result.peak_sab),
        "compliant": bool(result.peak_sab < threshold),
        "n_illuminated": int(np.sum(result.sab > 0)),
        "n_triangles": body.n_triangles,
        "level": level,
        "S_inc": float(S_inc),
        "distance_m": float(dist),
        "T0": float(tissue.T0),
    }
