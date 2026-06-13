"""Ray-pack and phantom loading for the Coherent Exposure Studio.

Reads the precomputed NPZ packs resolved by :mod:`._config` and caches them in
the shared viewer cache so repeated requests for the same scene reuse the
in-memory arrays. Fork-free: only ``aegis.*`` and numpy are imported.
"""

from __future__ import annotations

import threading

import numpy as np

from ._config import studio_data_dir

_PATHS_KEY = "_studio_paths"
_PHANTOM_KEY = "_studio_phantom"


def _cache_get(cache: dict | None, lock, top_key: str, sub_key, builder):
    """Memoise ``builder()`` under ``cache[top_key][sub_key]`` (lock-guarded)."""
    if cache is None:
        return builder()
    with lock:
        store = cache.setdefault(top_key, {})
        if sub_key in store:
            return store[sub_key]
    value = builder()
    with lock:
        cache.setdefault(top_key, {})[sub_key] = value
    return value


def load_paths(
    condition: str,
    array_n: int,
    seed: int,
    cache: dict | None = None,
    cache_lock: threading.RLock | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, int]:
    """Load one ray pack and return ``(k_hat, psi, element_index, n_elements)``.

    ``k_hat`` is ``(N, 3)`` float64, ``psi`` is ``(N, 3)`` complex, and
    ``element_index`` is ``(N,)`` int64. Raises :class:`FileNotFoundError` when
    the requested pack is not on disk.
    """
    sub_key = (str(condition), int(array_n), int(seed))

    def _build():
        path = studio_data_dir() / "rays" / f"bs{int(array_n)}_{condition}_seed{int(seed)}.npz"
        if not path.is_file():
            raise FileNotFoundError(f"ray pack not found: {path}")
        with np.load(path) as d:
            k_hat = np.ascontiguousarray(d["k_hat"], dtype=np.float64)
            psi = np.ascontiguousarray(d["psi"], dtype=complex)
            element_index = np.ascontiguousarray(d["element_index"], dtype=np.int64)
            n_elements = int(d["n_elements"])
        return k_hat, psi, element_index, n_elements

    return _cache_get(cache, cache_lock, _PATHS_KEY, sub_key, _build)


def load_phantom(
    name: str = "thelonious",
    cache: dict | None = None,
    cache_lock: threading.RLock | None = None,
) -> dict:
    """Load a phantom pack: vertices, faces, centroids, normals, areas.

    All arrays are in the e11 world frame (Z-up, metres). Cached in the shared
    viewer cache keyed by phantom name.
    """

    def _build():
        path = studio_data_dir() / "phantom" / f"{name}.npz"
        if not path.is_file():
            raise FileNotFoundError(f"phantom pack not found: {path}")
        with np.load(path) as d:
            return {
                "vertices": np.ascontiguousarray(d["vertices"], dtype=np.float64),
                "faces": np.ascontiguousarray(d["faces"], dtype=np.int32),
                "centroids": np.ascontiguousarray(d["centroids"], dtype=np.float64),
                "normals": np.ascontiguousarray(d["normals"], dtype=np.float64),
                "areas": np.ascontiguousarray(d["areas"], dtype=np.float64),
            }

    return _cache_get(cache, cache_lock, _PHANTOM_KEY, str(name), _build)


def unique_directions(
    k_hat: np.ndarray,
    psi: np.ndarray,
    element_index: np.ndarray,
    top_k: int = 200,
) -> dict:
    """Collapse paths to per-unique-direction power for ray glyphs.

    Groups paths by identical arrival direction (float32 bit pattern, the same
    quantisation :func:`aegis.hotspot.collapse_paths` uses), sums ``|psi|^2``
    within each group, and returns the ``top_k`` directions by power.
    """
    k_hat = np.asarray(k_hat, dtype=float)
    psi = np.asarray(psi)
    keys = (
        np.ascontiguousarray(k_hat.astype(np.float32))
        .view([("kx", np.float32), ("ky", np.float32), ("kz", np.float32)])
        .ravel()
    )
    _uniq, first_idx, inverse = np.unique(keys, return_index=True, return_inverse=True)
    n_u = first_idx.shape[0]
    power = np.zeros(n_u, dtype=float)
    np.add.at(power, inverse, np.sum(np.abs(psi) ** 2, axis=1))
    dirs = k_hat[first_idx]  # representative direction per group
    order = np.argsort(power)[::-1][: int(top_k)]
    dirs_top = dirs[order]
    return {
        "directions": dirs_top.tolist(),
        "power": power[order].tolist(),
        "k_hat": dirs_top.tolist(),
    }
