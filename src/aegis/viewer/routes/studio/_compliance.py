"""ICNIRP compliance scalars for the Coherent Exposure Studio.

Given the live precoder ``x`` and the precomputed field channel ``G_tilde``,
derives the exposure-compliance readouts the coherent-operator paper reports:

  - ``p_abs``      total absorbed power (per watt transmitted),
  - ``sar_wb``     whole-body SAR = p_abs / body mass,
  - ``pssar_4cm2`` the 4 cm^2 spatially-averaged peak absorbed power density
                   (the ICNIRP psSAR proxy), and the peak / mean ratio ``eta``,
  - ``signal_rel`` served signal relative to the matched-filter (MRT) beam.

The 4 cm^2 averaging matrix is the expensive part (a KD-tree neighbour build over
the full-resolution mesh), so it is cached per ``(mesh, ue, area)`` in the shared
viewer cache: it depends only on the body geometry, not the beam or focus, so one
build serves every beam / focus / budget nudge. This is why the compliance panel
is an opt-in toggle (the first build for a mesh costs a few seconds; every
subsequent read is a sparse matrix-vector product).

Fork-free: imports only ``aegis.*`` plus stdlib / numpy / scipy.
"""

from __future__ import annotations

import functools
import os
import threading
from pathlib import Path

import numpy as np

from ._channel import DEFAULT_UE_IDX, deposited_sab
from ._config import _REPO_ROOT
from ._paths import _cache_get, load_phantom

_AVGMAT_KEY = "_studio_avgmat"

# ICNIRP psSAR spatial-averaging area (matches AVERAGING_AREA_M2 in
# scripts/build_replay_artifact.py and aegis.geometry.averaging's default).
AVERAGING_AREA_M2 = 4e-4

# Fallback masses mirror data/phantoms.yaml; the file is the source of truth and
# is read first. Kept so a checkout without the yaml still reports SAR_wb.
_FALLBACK_MASS_KG = {
    "thelonious": 17.4,
    "duke": 72.4,
    "eartha": 56.0,
    "ella": 58.7,
}


def _phantoms_yaml() -> Path:
    """Path to data/phantoms.yaml (honours AEGIS_DATA_DIR, else the repo data dir)."""
    data_dir = os.environ.get("AEGIS_DATA_DIR")
    base = Path(data_dir) if data_dir else _REPO_ROOT / "data"
    return base / "phantoms.yaml"


@functools.lru_cache(maxsize=1)
def _phantom_masses() -> dict[str, float]:
    """Per-phantom whole-body mass [kg] from data/phantoms.yaml, cached."""
    path = _phantoms_yaml()
    if not path.is_file():
        return dict(_FALLBACK_MASS_KG)
    try:
        import yaml

        with open(path) as f:
            data = yaml.safe_load(f) or {}
        return {k: float(v["mass_kg"]) for k, v in data.items() if isinstance(v, dict) and "mass_kg" in v}
    except Exception:
        return dict(_FALLBACK_MASS_KG)


def body_mass_kg(mesh: str) -> float | None:
    """Whole-body mass [kg] for a phantom, or ``None`` if unknown (so SAR_wb skips)."""
    return _phantom_masses().get(str(mesh))


def averaging_matrix(
    mesh: str,
    ue_idx: int = DEFAULT_UE_IDX,
    cache: dict | None = None,
    cache_lock: threading.RLock | None = None,
    target_area_m2: float = AVERAGING_AREA_M2,
):
    """Row-stochastic 4 cm^2 averaging matrix ``G`` for a phantom, cached.

    ``G @ sab`` gives the spatially-averaged per-triangle absorbed power density,
    so ``max(G @ sab)`` is the psSAR. ``G`` depends only on the body geometry
    (centroids + areas), so it is keyed by ``(mesh, ue, area)`` and reused across
    every beam / focus the user steers. The build is the dominant cost (see the
    module docstring), hence the cache. Raises :class:`FileNotFoundError` when the
    phantom pack is absent (``load_phantom`` does).
    """
    from aegis.geometry.averaging import precompute_averaging_matrix

    def _build():
        phantom = load_phantom(mesh, cache, cache_lock, ue_idx)
        return precompute_averaging_matrix(
            np.asarray(phantom["centroids"], dtype=float),
            np.asarray(phantom["areas"], dtype=float),
            target_area_m2,
        )

    sub_key = (str(mesh), int(ue_idx), float(target_area_m2))
    return _cache_get(cache, cache_lock, _AVGMAT_KEY, sub_key, _build)


def compute_scalars(
    g_tilde: np.ndarray,
    areas: np.ndarray,
    x: np.ndarray,
    h: np.ndarray,
    x_mrt: np.ndarray,
    g_avg,
    body_mass: float | None,
) -> dict:
    """Compliance scalars for precoder ``x`` against the field channel ``g_tilde``.

    ``g_avg`` is the cached 4 cm^2 averaging matrix; ``h`` is the signal channel
    at the focus and ``x_mrt`` the matched-filter precoder, used for the
    signal-relative-to-MRT ratio. All densities carry the studio's "per watt
    transmitted" normalisation (the precoders are unit-power), so ``p_abs`` is the
    absorbed-power fraction and ``sar_wb`` is W/kg per transmitted watt.
    """
    x = np.asarray(x).reshape(-1)
    areas = np.asarray(areas, dtype=float).reshape(-1)
    sab = np.asarray(deposited_sab(g_tilde, x), dtype=float).reshape(-1)
    if sab.shape[0] != areas.shape[0]:
        raise ValueError(f"sab/areas length mismatch: {sab.shape[0]} vs {areas.shape[0]}")

    p_abs = float(np.sum(sab * areas))
    total_area = float(areas.sum())
    mean_apd = p_abs / total_area if total_area > 0 else 0.0

    sab_avg = np.asarray(g_avg @ sab).ravel()
    if sab_avg.shape[0] != sab.shape[0]:
        raise ValueError(f"averaging matrix shape mismatch: {sab_avg.shape[0]} vs {sab.shape[0]}")
    pssar_4cm2 = float(sab_avg.max()) if sab_avg.size else 0.0
    peak_sab = float(sab.max()) if sab.size else 0.0
    eta = pssar_4cm2 / mean_apd if mean_apd > 0 else 0.0

    h = np.asarray(h).reshape(-1)
    x_mrt = np.asarray(x_mrt).reshape(-1)
    s_x = float(np.abs(h @ x) ** 2)
    s_mrt = float(np.abs(h @ x_mrt) ** 2)
    signal_rel = s_x / s_mrt if s_mrt > 0 else 0.0

    sar_wb = (p_abs / body_mass) if (body_mass is not None and body_mass > 0) else None

    return {
        "p_abs_w": p_abs,
        "sar_wb": sar_wb,
        "pssar_4cm2": pssar_4cm2,
        "peak_sab": peak_sab,
        "mean_sab": mean_apd,
        "eta_4cm2": eta,
        "signal_rel": signal_rel,
        "body_mass_kg": body_mass,
        "averaging_area_cm2": float(AVERAGING_AREA_M2 * 1e4),
        "units": {
            "p_abs_w": "W per W tx",
            "sar_wb": "W/kg per W tx",
            "pssar_4cm2": "W/m^2 per W tx",
            "peak_sab": "W/m^2 per W tx",
            "mean_sab": "W/m^2 per W tx",
            "eta_4cm2": "-",
            "signal_rel": "-",
        },
    }
