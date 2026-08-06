"""Live, focus-tracking per-triangle body map for the Coherent Exposure Studio.

The precomputed body-map packs (``_bodymap``) are frozen at one beamforming
focus, so they do not move when the user steers the beam. This module serves a
*live* per-triangle deposited map instead: it loads the precoder-free field
channel ``G_tilde`` (T, 3, M) and applies the current precoder ``x`` on the fly,

    S_ab(triangle) = sum_axis |G_tilde @ x|^2,

so the served map tracks focus / beam / ECBF budget exactly the way the field
slice does. Fork-free: imports only ``aegis.*`` plus numpy. Channel packs are
produced offline by ``scripts/studio_precompute.py --channel``.
"""

from __future__ import annotations

import threading

import numpy as np

from ._config import studio_data_dir

_CHANNEL_KEY = "_studio_channel"

# Default corridor UE (mid-corridor, 14 m). Packs for this position keep the
# original unsuffixed name; other positions carry a ``_ue{idx}`` suffix so the
# UE slider can switch standing positions. Mirrors studio_precompute._ue_suffix.
DEFAULT_UE_IDX = 4


def ue_suffix(ue_idx: int) -> str:
    """Pack-name suffix for the UE the body stands at ('' for the default UE)."""
    return "" if int(ue_idx) == DEFAULT_UE_IDX else f"_ue{int(ue_idx)}"


def read_g_tilde(npz) -> np.ndarray:
    """Reconstruct the complex64 channel from a pack in either storage format.

    Old packs store ``g_tilde`` as complex64. New packs halve the on-disk size by
    storing the real and imaginary parts as two float16 arrays (``g_tilde_re`` /
    ``g_tilde_im``); we expand them back to complex64 here so every consumer sees
    the same array regardless of how the pack was written. float16 is ample for
    the served maps: it perturbs the deposited / worst-case / ECBF quantities by
    <1e-4 relative (the dominant exposure subspace is preserved). It does NOT
    preserve the tiny / null-space eigenvalues of the exposure operator Q, so any
    future consumer needing that genuine small-eigenvalue structure must rebuild
    from a full-precision source, not from a float16 pack.
    """
    if "g_tilde" in npz.files:
        return np.asarray(npz["g_tilde"], dtype=np.complex64)
    re = np.asarray(npz["g_tilde_re"], dtype=np.float32)
    im = np.asarray(npz["g_tilde_im"], dtype=np.float32)
    return (re + 1j * im).astype(np.complex64)


def channel_path(
    condition: str, array_n: int, freq_ghz: float, seed: int, mesh: str = "thelonious", ue_idx: int = DEFAULT_UE_IDX
):
    """Path to the field-channel pack for a scenario (may not exist).

    The channel is per-phantom (G_tilde is the body's tissue channel), so the
    stem carries the mesh as a prefix, and per-UE (the body stands at a corridor
    position), so non-default positions carry a ``_ue{idx}`` suffix.
    """
    stem = f"{mesh}_{condition}_bs{int(array_n)}_{float(freq_ghz):g}_seed{int(seed)}{ue_suffix(ue_idx)}"
    return studio_data_dir() / "channel" / f"{stem}.npz"


def load_channel(
    condition: str,
    array_n: int,
    freq_ghz: float,
    seed: int,
    mesh: str = "thelonious",
    cache: dict | None = None,
    cache_lock: threading.RLock | None = None,
    ue_idx: int = DEFAULT_UE_IDX,
):
    """Load ``(g_tilde (T, 3, M) complex, areas (T,))`` for a scenario, cached.

    Returns ``None`` when the pack is absent (the caller emits the
    not-precomputed sentinel). The channel pack is the largest studio artifact
    (~150 MB), so the in-process cache keyed by stem avoids re-reading it on
    every focus nudge.
    """
    path = channel_path(condition, array_n, freq_ghz, seed, mesh, ue_idx)
    if not path.is_file():
        return None
    stem = path.stem
    if cache is not None and cache_lock is not None:
        with cache_lock:
            store = cache.setdefault(_CHANNEL_KEY, {})
            if stem in store:
                return store[stem]
    with np.load(path) as d:
        g_tilde = read_g_tilde(d)
        areas = np.asarray(d["areas"], dtype=float)
    value = (g_tilde, areas)
    if cache is not None and cache_lock is not None:
        with cache_lock:
            cache.setdefault(_CHANNEL_KEY, {})[stem] = value
    return value


def deposited_sab(g_tilde: np.ndarray, x: np.ndarray) -> np.ndarray:
    """Per-triangle deposited S_ab = sum_axis |G_tilde @ x|^2 (matches the precompute)."""
    return (np.abs(np.einsum("tim,m->ti", g_tilde, x)) ** 2).sum(axis=1)


def compute_live_bodymap(g_tilde: np.ndarray, x: np.ndarray) -> dict:
    """Deposited per-triangle S_ab under precoder ``x`` as a served body-map dict.

    Mirrors the precomputed body-map payload (values list + vmin/vmax/units/
    quantity) so the frontend reuses the same body-map path.
    """
    sab = np.asarray(deposited_sab(g_tilde, x), dtype=np.float32)
    return {
        "values": sab.tolist(),
        "vmin": float(sab.min()),
        "vmax": float(sab.max()),
        "units": "W/m^2 per W",
        "quantity": "deposited",
    }
