"""Dosimetry computation for the interactive viewer."""

from __future__ import annotations

import functools
import hashlib
import math
import os
import threading
import time
from pathlib import Path

import numpy as np
import yaml

from aegis.constants import EPS_0
from aegis.defaults import DEFAULT_FREQ_HZ, DEFAULT_POWER_DBM
from aegis.engine import DosimetryEngine
from aegis.geometry.mesh import BodyMesh
from aegis.paths import PropagationPaths
from aegis.tissue.cole_cole import debye_permittivity
from aegis.tissue.dielectric import TissueModel
from aegis.viewer.config import DEFAULTS


@functools.lru_cache(maxsize=1)
def _load_phantom_masses() -> dict[str, float]:
    """Load phantom masses from data/phantoms.yaml (cached)."""
    data_dir = Path(os.environ.get("AEGIS_DATA_DIR", str(Path(__file__).resolve().parents[3] / "data")))
    path = Path(data_dir) / "phantoms.yaml"
    if not path.exists():
        return {
            "thelonious": 17.4,
            "duke": 72.4,
            "eartha": 56.0,
            "ella": 58.7,
            "adult_male": 73.0,
            "adult_female": 60.0,
            "boy_6y": 19.0,
            "girl_8y": 30.0,
        }
    with open(path) as f:
        data = yaml.safe_load(f)
    return {name: info["mass_kg"] for name, info in data.items()}


# Cache for curvature computation (expensive, only changes when body changes)
_curvature_cache: dict = {}
_curvature_cache_lock = threading.Lock()
_CURVATURE_CACHE_MAX = 8


def _curvature_cache_key(body: BodyMesh) -> int:
    """Rigid-transform-invariant cache key for viewer curvature estimates."""
    edge_vecs = np.roll(body.vertices, -1, axis=1) - body.vertices
    edge_lengths = np.sort(np.linalg.norm(edge_vecs, axis=2), axis=1)
    centered = body.centroids - body.centroids.mean(axis=0, keepdims=True)
    radii = np.sort(np.linalg.norm(centered, axis=1))
    normal_svals = np.linalg.svd(body.normals, compute_uv=False)

    h = hashlib.sha256(body.areas.astype(np.float32).tobytes())
    h.update(edge_lengths.astype(np.float32).tobytes())
    h.update(radii.astype(np.float32).tobytes())
    h.update(normal_svals.astype(np.float32).tobytes())
    digest = h.digest()[:8]
    return hash((int.from_bytes(digest, "little"), body.n_triangles))


def _compute_face_curvature(body: BodyMesh) -> np.ndarray:
    """Estimate per-face mean curvature from normal variation to neighbors.

    Uses KD-tree for fast neighbor lookup: for each face, the curvature
    is estimated as the average |delta_normal| / distance to its 6 nearest
    neighbors. This gives a good proxy for the discrete mean curvature.

    The result is invariant to rigid transforms: translation preserves all
    inter-centroid distances and rotation preserves both distances and
    |delta_normal| (since ||R n_i - R n_j|| = ||n_i - n_j||). Cache using a
    rigid-transform-invariant key so translated/rotated bodies hit the cache
    without letting unrelated meshes collide.
    """
    cache_key = _curvature_cache_key(body)

    with _curvature_cache_lock:
        if cache_key in _curvature_cache:
            return _curvature_cache[cache_key]

    from scipy.spatial import cKDTree

    centroids = body.centroids
    normals = body.normals
    M = body.n_triangles
    if M <= 1:
        return np.zeros(M, dtype=np.float64)

    k = min(7, M)
    tree = cKDTree(centroids)
    dists, indices = tree.query(centroids, k=k)

    neighbor_normals = normals[indices]
    face_normals = normals[:, np.newaxis, :]
    delta_n = np.linalg.norm(neighbor_normals - face_normals, axis=2)
    safe_dists = np.maximum(dists, 1e-12)
    curvature_per_neighbor = delta_n / safe_dists

    H = np.mean(curvature_per_neighbor[:, 1:], axis=1)

    with _curvature_cache_lock:
        while len(_curvature_cache) >= _CURVATURE_CACHE_MAX:
            _curvature_cache.pop(next(iter(_curvature_cache)))
        _curvature_cache[cache_key] = H
    return H


# ---------------------------------------------------------------------------
# Skin model registry
# ---------------------------------------------------------------------------

SKIN_MODELS = [
    {"id": "itis", "label": "Homogeneous - IT’IS database (v5)"},
    {"id": "christ2021", "label": "Homogeneous - Gabriel × 1.2 (Christ 2021)"},
    {"id": "christ2025", "label": "Homogeneous - Christ 2025 Dermis"},
    {"id": "nict", "label": "Homogeneous - NICT Measurements"},
]

_nict_data: dict | None = None


def _load_nict_data() -> dict:
    """Load and cache NICT skin measurement CSV."""
    global _nict_data
    if _nict_data is not None:
        return _nict_data

    import csv

    # Search for CSV: AEGIS_DATA_DIR env var, then CWD/data, then relative to source
    import os
    import re
    from pathlib import Path

    candidates = []
    env_dir = os.environ.get("AEGIS_DATA_DIR")
    if env_dir:
        candidates.append(Path(env_dir) / "measurements-Skin.csv")
    candidates.append(Path("data") / "measurements-Skin.csv")
    candidates.append(Path(__file__).parent.parent.parent.parent / "data" / "measurements-Skin.csv")
    csv_path = next((p for p in candidates if p.exists()), candidates[-1])
    freq_hz_list, eps_r_list, sigma_list = [], [], []

    with open(csv_path) as f:
        reader = csv.reader(f)
        next(reader)  # skip header
        for row in reader:
            if len(row) >= 4 and row[0].strip():
                try:

                    def parse(s, _re=re):
                        return float(_re.sub(r"\.E", "E", s.strip()))

                    freq_hz_list.append(parse(row[0]))
                    eps_r_list.append(parse(row[1]))
                    sigma_list.append(parse(row[3]))
                except ValueError:
                    continue

    _nict_data = {
        "log_freq": np.log10(np.array(freq_hz_list)),
        "log_eps_r": np.log10(np.array(eps_r_list)),
        "log_sigma": np.log10(np.array(sigma_list)),
    }
    return _nict_data


def resolve_skin_model(name: str, freq_hz: float) -> TissueModel:
    """Compute skin TissueModel from a named data source at a given frequency."""
    if name == "itis":
        return TissueModel.from_database("Skin", freq_hz)

    if name == "christ2021":
        base = TissueModel.from_database("Skin", freq_hz)
        return TissueModel(
            name="Skin (Gabriel × 1.2)",
            eps_r=base.eps_r * 1.2,
            sigma=base.sigma * 1.2,
            freq_hz=freq_hz,
        )

    if name == "christ2025":
        eps = debye_permittivity(
            freq_hz,
            eps_inf=7.88,
            eps_static=47.0,
            sigma=5.19,
            tau_s=8.35e-12,
        )
        omega = 2 * np.pi * freq_hz
        return TissueModel(
            name="Skin (Christ 2025 Dermis)",
            eps_r=float(eps.real),
            sigma=float(-eps.imag * omega * EPS_0),
            freq_hz=freq_hz,
        )

    if name == "nict":
        data = _load_nict_data()
        log_f = np.log10(freq_hz)
        log_f_clamped = np.clip(log_f, data["log_freq"][0], data["log_freq"][-1])
        eps_r = 10 ** float(np.interp(log_f_clamped, data["log_freq"], data["log_eps_r"]))
        sigma = 10 ** float(np.interp(log_f_clamped, data["log_freq"], data["log_sigma"]))
        return TissueModel(
            name="Skin (NICT)",
            eps_r=eps_r,
            sigma=sigma,
            freq_hz=freq_hz,
        )

    raise ValueError(f"Unknown skin model: {name!r}")


def _resolve_channel_preset_dir(config: dict | None = None, preset_dir: str | Path | None = None) -> Path:
    """Resolve channel preset directories against AEGIS data roots."""
    if preset_dir is None:
        cfg = config or DEFAULTS
        preset_dir = cfg.get("dosimetry", {}).get("stochastic", {}).get("preset_dir", "channel_presets")

    preset_path = Path(preset_dir)
    if preset_path.is_absolute():
        return preset_path

    data_root = Path(os.environ.get("AEGIS_DATA_DIR", str(Path(__file__).resolve().parents[3] / "data")))
    return data_root / preset_path


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


_SPEED_OF_LIGHT = 299_792_458.0  # m/s


def _build_cluster_viz(viz_out: dict) -> list[dict]:
    """Compute FBS/LBS positions for each cluster and return visualization data.

    Each cluster becomes a dict with keys: fbs, lbs, power, is_los.
    Positions are in Z-up server coordinates.
    """
    n = viz_out["n_clusters"]
    is_los = viz_out["is_los"]
    antenna = np.array(viz_out["antenna_pos"])
    body_c = np.array(viz_out["body_center"])
    dist = np.linalg.norm(body_c - antenna)

    clusters = []
    for i in range(n):
        power = viz_out["cluster_power"][i]

        if is_los and i == 0:
            # LOS cluster: direct path, no scatterers
            clusters.append(
                {
                    "fbs": None,
                    "lbs": None,
                    "power": power,
                    "is_los": True,
                }
            )
            continue

        # Arrival direction at body (propagation direction, Z-up)
        arr_az = viz_out["cluster_az"][i]
        arr_el = viz_out["cluster_el"][i]
        cos_el = math.cos(arr_el)
        arr_dir = np.array([cos_el * math.cos(arr_az), cos_el * math.sin(arr_az), math.sin(arr_el)])

        # Departure direction from antenna (propagation direction, Z-up)
        dep_az = viz_out["cluster_dep_az"][i]
        dep_el = viz_out["cluster_dep_el"][i]
        cos_dep_el = math.cos(dep_el)
        dep_dir = np.array([cos_dep_el * math.cos(dep_az), cos_dep_el * math.sin(dep_az), math.sin(dep_el)])

        # Excess path length from cluster delay
        delay_s = viz_out["cluster_delay"][i]
        d_excess = delay_s * _SPEED_OF_LIGHT
        # Clamp excess to something visually reasonable (at most 2x the direct distance)
        d_excess = min(d_excess, dist * 2.0)

        # Split excess equally between FBS and LBS legs
        r_fbs = max(d_excess * 0.5, dist * 0.15)
        r_lbs = max(d_excess * 0.5, dist * 0.15)
        # Clamp so scatterers stay between antenna and body
        r_fbs = min(r_fbs, dist * 0.8)
        r_lbs = min(r_lbs, dist * 0.8)

        fbs = (antenna + dep_dir * r_fbs).tolist()
        lbs = (body_c - arr_dir * r_lbs).tolist()

        clusters.append(
            {
                "fbs": fbs,
                "lbs": lbs,
                "power": power,
                "is_los": False,
            }
        )

    return clusters


def compute_dosimetry(
    body: BodyMesh,
    antenna_pos: np.ndarray,
    body_offset: np.ndarray | None = None,
    body_rotation_y: float = 0.0,
    level: int | None = 2,
    mode: str | None = None,
    corrections: dict | None = None,
    tissue: TissueModel | None = None,
    power_dbm: float = DEFAULT_POWER_DBM,
    config: dict | None = None,
    stochastic: dict | None = None,
) -> tuple:
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
    config : viewer config dict

    Returns
    -------
    Tuple of ``(result, transformed_body, tissue, level, mode, corrections, extra)``.
    """
    timings: dict[str, float] = {}
    t_total = time.perf_counter()

    cfg = config or DEFAULTS
    dos_cfg = cfg["dosimetry"]

    if tissue is None:
        tissue = resolve_skin_model("itis", DEFAULT_FREQ_HZ)

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

    # Power at body surface (free-space path loss, clamp distance for near-field)
    tx_power_w = 10 ** ((power_dbm - 30) / 10)
    from aegis.viewer.raytracer import _DEFAULT_FSPL_DISTANCE_CLAMP_M

    d_clamped = max(dist, _DEFAULT_FSPL_DISTANCE_CLAMP_M)
    S_inc = tx_power_w / (4 * np.pi * d_clamped**2)

    cluster_viz = None
    if stochastic:
        from aegis.channel import generate_channel, load_preset

        preset_dir = _resolve_channel_preset_dir(cfg)
        preset = load_preset(stochastic["preset"], preset_dir)
        viz_out: dict = {}
        paths = generate_channel(
            preset["params"],
            freq_ghz=stochastic.get("freq_ghz", 28),
            antenna_pos=antenna_pos,
            body_center=body_center,
            power_dbm=power_dbm,
            seed=stochastic.get("seed", 42),
            overrides=stochastic.get("overrides"),
            viz_out=viz_out,
        )
        cluster_viz = _build_cluster_viz(viz_out)
    else:
        # Single plane wave
        paths = PropagationPaths.from_powers(
            k_hat=k_hat[np.newaxis, :],
            power=np.array([S_inc]),
        )

    # Resolve body mass for SAR computation
    body_mass = _load_phantom_masses().get(body.name) if body.name else None

    engine = DosimetryEngine(tissue)
    t0 = time.perf_counter()

    if mode is not None:
        # New mode-based API from frontend
        corr = corrections or {}
        if mode == "bound":
            A_ab = body.total_area * dos_cfg["convex_body_area_factor"]
            D_max = dos_cfg["level0_D_max"]
            result, engine_timings = engine.compute_with_timings(
                rotated_body, paths, mode="bound", A_ab=A_ab, D_max=D_max, body_mass=body_mass
            )
        elif mode == "aggregate":
            A_ab = body.total_area * dos_cfg["convex_body_area_factor"]
            result, engine_timings = engine.compute_with_timings(
                rotated_body, paths, mode="aggregate", A_ab=A_ab, body_mass=body_mass
            )
        else:
            # spatial mode with correction flags
            mode_kwargs: dict = {"mode": "spatial"}
            mode_kwargs["fresnel"] = corr.get("fresnel", True)
            if corr.get("polarisation"):
                mode_kwargs["polarisation"] = True
                mode_kwargs["q"] = 1.0  # short dipole TM-polarized
            if corr.get("curvature"):
                mode_kwargs["curvature"] = True
                mode_kwargs["curvature_H"] = _compute_face_curvature(rotated_body)
            if corr.get("diffraction"):
                mode_kwargs["diffraction"] = True
                if "curvature_H" not in mode_kwargs:
                    mode_kwargs["curvature_H"] = _compute_face_curvature(rotated_body)
            result, engine_timings = engine.compute_with_timings(
                rotated_body, paths, body_mass=body_mass, **mode_kwargs
            )
    else:
        # Legacy level-based API
        if level is None:
            level = 2
        extra_kwargs: dict = {}
        if level <= 1:
            extra_kwargs["A_ab"] = body.total_area * dos_cfg["convex_body_area_factor"]
            if level == 0:
                extra_kwargs["D_max"] = dos_cfg["level0_D_max"]
            result, engine_timings = engine.compute_with_timings(
                rotated_body, paths, level=level, body_mass=body_mass, **extra_kwargs
            )
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
            result, engine_timings = engine.compute_with_timings(
                rotated_body, paths, body_mass=body_mass, **mode_kwargs2
            )
        else:
            result, engine_timings = engine.compute_with_timings(
                rotated_body, paths, level=level, body_mass=body_mass, **extra_kwargs
            )

    timings["engine_compute_ms"] = (time.perf_counter() - t0) * 1e3
    timings["total_ms"] = (time.perf_counter() - t_total) * 1e3

    # Pull fine-grained timings from the call-local dict returned by compute_with_timings
    for key in ("kernel_ms", "avg_build_G_4cm2_ms", "avg_matvec_4cm2_ms", "avg_build_G_1cm2_ms"):
        if key in engine_timings:
            timings[key] = engine_timings[key]

    extra = {
        "S_inc": float(S_inc),
        "distance_m": float(dist),
        "timings": timings,
    }
    if cluster_viz is not None:
        extra["cluster_viz"] = cluster_viz

    corr_list = None
    if mode is not None:
        corr = corrections or {}
        corr_list = [k for k in ("fresnel", "polarisation", "curvature", "diffraction") if corr.get(k)]

    return result, rotated_body, tissue, level, mode, corr_list, extra


def generate_lsp_heatmap(
    preset_name: str,
    freq_ghz: float,
    antenna_pos: tuple[float, float, float],
    lsp_name: str = "SF_dB",
    bounds: tuple[float, float, float, float] = (-100, 100, -100, 100),
    resolution: int = 128,
    seed: int = 42,
    preset_dir: str | None = None,
) -> dict:
    """Generate an LSP heatmap for the frontend."""
    from aegis.channel.lsf import LSFModel
    from aegis.channel.presets import load_preset

    preset = load_preset(preset_name, _resolve_channel_preset_dir(DEFAULTS, preset_dir))
    model = LSFModel(preset["params"], freq_ghz, seed=seed)
    grid = model.generate_map(
        bounds=bounds,
        resolution=resolution,
        height=1.5,
        lsp_name=lsp_name,
    )

    return {
        "data": grid.tolist(),
        "bounds": list(bounds),
        "lsp_name": lsp_name,
        "vmin": float(grid.min()),
        "vmax": float(grid.max()),
        "resolution": resolution,
    }
