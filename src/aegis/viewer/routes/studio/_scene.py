"""Scene-geometry serving for the Coherent Exposure Studio.

Serves the precomputed scene packs (room box, scatterer cuboids, the optional
NLOS blocker, BS placement and UE positions) so the frontend can draw the real
factory blockers. Fork-free: reads only the JSON packs written offline by
``scripts/studio_precompute.py`` ``sync_scene``.

The geometry is array-size independent (scatterer placement keys off the seed
and the fixed BS corridor, not the array), so packs are keyed by
``(condition, seed)`` only. NLOS has a single realisation, so any NLOS request
resolves to seed 0.
"""

from __future__ import annotations

import json
import threading

from ._config import studio_data_dir

_SCENE_KEY = "_studio_scene"


def get_scene(
    condition: str,
    seed: int = 0,
    cache: dict | None = None,
    cache_lock: threading.RLock | None = None,
) -> dict:
    """Return the scene geometry for ``(condition, seed)``, or a not-precomputed
    sentinel.

    On hit returns the scene-pack dict (room_dims, bs_position, scatterers,
    blocker, ue_positions, ...) with a ``provenance`` string added. On miss
    returns ``{not_precomputed: True, error, stem}`` (the endpoint turns this
    into a 409). NLOS collapses to seed 0 (its single realisation).
    """
    cond = "nlos" if condition == "nlos" else "los"
    eff_seed = 0 if cond == "nlos" else int(seed)
    stem = f"{cond}_seed{eff_seed}"
    path = studio_data_dir() / "scene" / f"{stem}.json"

    if not path.is_file():
        return {
            "not_precomputed": True,
            "error": f"scene pack not precomputed: {stem}",
            "stem": stem,
        }

    def _build() -> dict:
        with path.open() as f:
            d = json.load(f)
        d["provenance"] = f"studio scene geometry | {cond} seed{eff_seed}"
        return d

    if cache is None:
        return _build()
    if cache_lock is None:
        raise ValueError("cache_lock is required when cache is provided")
    with cache_lock:
        store = cache.setdefault(_SCENE_KEY, {})
        if stem in store:
            return store[stem]
    value = _build()
    with cache_lock:
        cache.setdefault(_SCENE_KEY, {})[stem] = value
    return value
