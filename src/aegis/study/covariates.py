"""Per-city covariates: the morphology and deployment statistics that explain
the cross-city spread of the exposure CDF.

The ten-city figure alone gives a spread with no mechanism. These covariates
(building heights, site geometry, geometric LOS fraction, serving distance) are
cheap to compute from artifacts the run already has (city mesh, candidate roofs,
sites, trajectories), and let the report regress the spread instead of stating a
grand mean.
"""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np

_FALLBACK_MASS_KG = {
    "thelonious": 17.4,
    "duke": 72.4,
    "eartha": 29.9,
    "ella": 58.7,
}


def data_dir() -> Path:
    """The AEGIS data directory: AEGIS_DATA_DIR, else the repo's data/.

    Resolved from this file rather than the cwd so batch jobs launched from
    anywhere (HPC scratch dirs, cron) find the phantom meshes.
    """
    env = os.environ.get("AEGIS_DATA_DIR")
    return Path(env) if env else Path(__file__).resolve().parents[3] / "data"


def phantom_mass_kg(name: str) -> float | None:
    """Whole-body mass [kg] for a phantom, from data/phantoms.yaml when present."""
    path = data_dir() / "phantoms.yaml"
    if path.is_file():
        try:
            import yaml

            data = yaml.safe_load(path.read_text()) or {}
            entry = data.get(name)
            if isinstance(entry, dict) and "mass_kg" in entry:
                return float(entry["mass_kg"])
        except Exception:
            pass
    return _FALLBACK_MASS_KG.get(name)


def _segment_blocked(tri_v0, tri_e1, tri_e2, p0, p1) -> bool:
    """True if the open segment p0 -> p1 intersects any mesh triangle
    (vectorized Moller-Trumbore over all triangles)."""
    d = np.asarray(p1, dtype=float) - np.asarray(p0, dtype=float)
    seg_len = np.linalg.norm(d)
    if seg_len < 1e-9:
        return False
    d = d / seg_len

    h = np.cross(d, tri_e2)
    a = np.einsum("ij,ij->i", tri_e1, h)
    ok = np.abs(a) > 1e-12
    if not np.any(ok):
        return False
    f = np.zeros_like(a)
    f[ok] = 1.0 / a[ok]
    s = np.asarray(p0, dtype=float) - tri_v0
    u = f * np.einsum("ij,ij->i", s, h)
    q = np.cross(s, tri_e1)
    v = f * (q @ d)
    t = f * np.einsum("ij,ij->i", tri_e2, q)
    eps = 1e-9
    hit = ok & (u >= -eps) & (v >= -eps) & (u + v <= 1.0 + eps) & (t > 1e-3) & (t < seg_len - 1e-3)
    return bool(np.any(hit))


def _mesh_tris(mesh):
    v = np.asarray(mesh.vertices, dtype=float)
    t = np.asarray(mesh.triangles, dtype=int)
    tri = v[t]
    return tri[:, 0], tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]


def city_covariates(city, sites, agents, radius_m, torso_z=1.1) -> dict:
    """Morphology + deployment covariates for one built city.

    LOS fraction and serving distance are geometric (segment raycast against the
    traced mesh, mid-walk position, nearest site), deliberately independent of
    the RT solver so they stay comparable across solver settings.
    """
    cand = np.asarray(city.candidates, dtype=float)
    area_km2 = np.pi * (float(radius_m) / 1e3) ** 2

    cov: dict = {
        "n_buildings": int(cand.shape[0]),
        "building_density_km2": float(cand.shape[0] / area_km2) if area_km2 > 0 else None,
        "roof_height_mean_m": float(cand[:, 2].mean()) if cand.size else None,
        "roof_height_p90_m": float(np.percentile(cand[:, 2], 90)) if cand.size else None,
    }

    pos = np.array([np.asarray(s.position, dtype=float) for s in sites]) if sites else np.zeros((0, 3))
    cov["n_sites"] = int(pos.shape[0])
    cov["site_height_mean_m"] = float(pos[:, 2].mean()) if pos.size else None
    if pos.shape[0] >= 2:
        d2 = np.linalg.norm(pos[:, None, :2] - pos[None, :, :2], axis=2)
        np.fill_diagonal(d2, np.inf)
        cov["isd_mean_m"] = float(d2.min(axis=1).mean())
    else:
        cov["isd_mean_m"] = None

    if pos.shape[0] == 0 or not agents:
        cov["los_fraction"] = None
        cov["serving_distance_mean_m"] = None
        return cov

    v0, e1, e2 = _mesh_tris(city.mesh)
    n_los = 0
    n_tot = 0
    serve_d = []
    for a in agents:
        traj = np.asarray(a.trajectory.positions, dtype=float)
        if traj.shape[0] == 0:
            continue
        xy = traj[traj.shape[0] // 2]
        p_body = np.array([xy[0], xy[1], torso_z])
        d_sites = np.linalg.norm(pos[:, :2] - p_body[:2], axis=1)
        k = int(np.argmin(d_sites))
        serve_d.append(float(np.linalg.norm(pos[k] - p_body)))
        n_tot += 1
        if not _segment_blocked(v0, e1, e2, pos[k], p_body):
            n_los += 1
    cov["los_fraction"] = float(n_los / n_tot) if n_tot else None
    cov["serving_distance_mean_m"] = float(np.mean(serve_d)) if serve_d else None
    return cov
