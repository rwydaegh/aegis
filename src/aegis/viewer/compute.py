"""Dosimetry computation for the interactive viewer."""

from __future__ import annotations

import numpy as np

from aegis.engine import DosimetryEngine
from aegis.geometry.mesh import BodyMesh
from aegis.paths import PropagationPaths
from aegis.tissue.dielectric import SKIN_28GHZ, TissueModel

# Predefined tissue presets
TISSUE_PRESETS = {
    "skin_28ghz": SKIN_28GHZ,
    "skin_60ghz": TissueModel("Skin 60 GHz", eps_r=7.9, sigma=36.4, freq_hz=60e9),
}


def compute_dosimetry(
    body: BodyMesh,
    antenna_pos: np.ndarray,
    body_offset: np.ndarray | None = None,
    level: int = 2,
    tissue: TissueModel | None = None,
    power_dbm: float = 30.0,
    n_paths: int = 1,
) -> dict:
    """Run dosimetry from a single antenna position toward the body.

    Parameters
    ----------
    body : the body mesh
    antenna_pos : (3,) antenna position in scene coordinates [meters]
    body_offset : (3,) translation applied to the body [meters]
    level : fidelity level 0-6
    tissue : tissue model (defaults to skin at 28 GHz)
    power_dbm : transmit power [dBm]
    n_paths : number of synthetic paths (1 = single plane wave)

    Returns
    -------
    dict with keys: sab (float32 bytes), p_abs, peak_sab, compliant, n_illuminated
    """
    if tissue is None:
        tissue = SKIN_28GHZ

    antenna_pos = np.asarray(antenna_pos, dtype=np.float64)
    body_offset = np.asarray(body_offset, dtype=np.float64) if body_offset is not None else np.zeros(3)

    # Body center (average of centroids), shifted by offset
    body_center = body.centroids.mean(axis=0) + body_offset

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
        rng = np.random.default_rng(42)
        k_hats = np.tile(k_hat, (n_paths, 1))
        # Add angular jitter
        jitter = rng.normal(0, 0.15, size=(n_paths, 3))
        k_hats += jitter
        norms = np.linalg.norm(k_hats, axis=1, keepdims=True)
        k_hats = k_hats / np.where(norms > 0, norms, 1.0)

        # Power decreases for scattered paths
        powers = np.full(n_paths, S_inc)
        powers[1:] *= rng.uniform(0.1, 0.5, size=n_paths - 1)

        paths = PropagationPaths.from_powers(k_hat=k_hats, power=powers)

    engine = DosimetryEngine(tissue)

    # Levels 0-1 need precomputed geometry parameters
    extra_kwargs: dict = {}
    if level <= 1:
        # Cauchy formula: A_ab = A_total / 4 for convex bodies
        extra_kwargs["A_ab"] = body.total_area / 4.0
    if level == 0:
        # D_max ~ 4 is a reasonable bound for human bodies (sphere = 4)
        extra_kwargs["D_max"] = 4.0

    result = engine.compute(body, paths, level=level, **extra_kwargs)

    sab_bytes = result.sab.astype(np.float32).tobytes()

    return {
        "sab_bytes": sab_bytes,
        "p_abs": float(result.p_abs),
        "p_abs_mw": float(result.p_abs * 1e3),
        "peak_sab": float(result.peak_sab),
        "compliant": bool(result.peak_sab < 10.0),
        "n_illuminated": int(np.sum(result.sab > 0)),
        "n_triangles": body.n_triangles,
        "level": level,
        "S_inc": float(S_inc),
        "distance_m": float(dist),
        "T0": float(tissue.T0),
    }
