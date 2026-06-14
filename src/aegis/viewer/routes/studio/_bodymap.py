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


def _resolve_pack(condition: str, array_n: int, quantity: str, freq_tag: str, statistic: str):
    """Resolve the (stem, path) for a body-map request.

    ``statistic`` selects the single realisation (the default body-map pack) or
    an ensemble statistic over the LOS seeds (``mean``/``p95``, served from the
    ensemble dir). The mean pack carries the seed count K in its name, so it is
    matched by glob. Returns ``(stem, path_or_none)``; ``path_or_none`` is None
    when no pack matches (the caller emits the not-precomputed sentinel).
    """
    base = f"{condition}_bs{int(array_n)}_{quantity}_{freq_tag}"
    if statistic == "single":
        path = studio_data_dir() / "bodymaps" / f"{base}.npz"
        return base, (path if path.is_file() else None)

    ens = studio_data_dir() / "ensemble"
    if statistic == "p95":
        path = ens / f"{base}_p95.npz"
        return f"{base}_p95", (path if path.is_file() else None)
    if statistic == "mean":
        # The mean pack name carries the seed count (e.g. ..._mean6.npz).
        hits = sorted(ens.glob(f"{base}_mean*.npz"))
        return f"{base}_mean", (hits[0] if hits else None)
    return base, None


def get_bodymap(
    condition: str,
    array_n: int,
    beam: str,
    quantity: str,
    frequency_ghz: float,
    realisation: int = 0,
    statistic: str = "single",
    cache: dict | None = None,
    cache_lock: threading.RLock | None = None,
) -> dict:
    """Return a served body map, or a not-precomputed sentinel.

    On hit returns ``{values, vmin, vmax, units, quantity, provenance}``. On
    miss returns ``{not_precomputed: True, error, stem}`` (the endpoint turns
    this into a 409-style payload). ``statistic`` is ``single`` (default),
    ``mean`` or ``p95``; the ensemble statistics are LOS-only and miss cleanly
    for NLOS or any uncovered combination.
    """
    freq_tag = f"{float(frequency_ghz):g}"
    stem, path = _resolve_pack(condition, array_n, quantity, freq_tag, statistic)

    if path is None:
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
