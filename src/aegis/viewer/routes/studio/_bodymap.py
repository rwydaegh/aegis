"""Per-triangle body-map serving for the Coherent Exposure Studio.

Serves the precomputed body-map packs. The served quantities (floor, mrt,
worstcase, amp) already encode the precoder, so ``beam`` is advisory and the
single-realisation packs ignore ``realisation``. Fork-free.
"""

from __future__ import annotations

import threading

import numpy as np

from ._config import studio_data_dir

_BODYMAP_KEY = "_studio_bodymap"


def get_bodymap(
    condition: str,
    array_n: int,
    beam: str,
    quantity: str,
    frequency_ghz: float,
    realisation: int = 0,
    cache: dict | None = None,
    cache_lock: threading.RLock | None = None,
) -> dict:
    """Return a served body map, or a not-precomputed sentinel.

    On hit returns ``{values, vmin, vmax, units, quantity, provenance}``. On
    miss returns ``{not_precomputed: True, error, stem}`` (the endpoint turns
    this into a 409-style payload).
    """
    freq_tag = f"{float(frequency_ghz):g}"
    stem = f"{condition}_bs{int(array_n)}_{quantity}_{freq_tag}"
    path = studio_data_dir() / "bodymaps" / f"{stem}.npz"

    if not path.is_file():
        return {
            "not_precomputed": True,
            "error": f"body-map pack not precomputed: {stem}",
            "stem": stem,
        }

    def _build():
        with np.load(path) as d:
            return {
                "values": d["values"].astype(np.float32).tolist(),
                "vmin": float(d["vmin"]),
                "vmax": float(d["vmax"]),
                "units": str(d["units"]),
                "quantity": str(d["quantity"]),
                "provenance": str(d["provenance"]),
            }

    if cache is None:
        return _build()
    with cache_lock:
        store = cache.setdefault(_BODYMAP_KEY, {})
        if stem in store:
            return store[stem]
    value = _build()
    with cache_lock:
        cache.setdefault(_BODYMAP_KEY, {})[stem] = value
    return value
