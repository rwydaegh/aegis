"""Background precompute of averaging matrices so the first compute is fast."""

from __future__ import annotations

import os
import threading

from flask import Flask


def setup_precompute_G(app: Flask, cache: dict) -> None:
    """Register a before_request hook that background-precomputes averaging matrices.

    Uses before_request instead of module-level startup because gunicorn's
    preload_app forks after create_app, so a thread started here would run in
    the master and its cache wouldn't be shared.
    """
    max_triangles = int(os.environ.get("AEGIS_G_MAX_TRIANGLES", 100_000))
    started = {"done": False}

    @app.before_request
    def _maybe_precompute_G():
        if started["done"]:
            return
        started["done"] = True
        threading.Thread(
            target=_precompute_all_bodies,
            args=(app, cache, max_triangles),
            daemon=True,
            name="precompute-G",
        ).start()


def _precompute_all_bodies(app: Flask, cache: dict, max_triangles: int) -> None:
    """Fill the G-matrix cache for every loaded body within the triangle budget."""
    from aegis.engine import DosimetryEngine

    for name, entry in list(cache.get("bodies", {}).items()):
        body = entry["body"]
        if body.n_triangles > max_triangles:
            app.logger.info("G(%s) skipped (%d > %d tri)", name, body.n_triangles, max_triangles)
            continue
        for area in (4e-4, 1e-4):
            _precompute_one(app, name, body, area, DosimetryEngine)


def _precompute_one(app: Flask, name: str, body, area: float, DosimetryEngine) -> None:
    """Precompute and cache one averaging matrix if not already present."""
    from aegis.geometry.averaging import precompute_averaging_matrix

    key = (DosimetryEngine._body_cache_key(body), area)
    with DosimetryEngine._G_lock:
        already_cached = key in DosimetryEngine._G_cache
    if already_cached:
        return
    try:
        G = precompute_averaging_matrix(body.centroids, body.areas, area)
        with DosimetryEngine._G_lock:
            DosimetryEngine._G_cache[key] = G
        app.logger.info("G(%s, %dcm2) ready (%d nnz)", name, area * 1e4, G.nnz)
    except Exception as e:
        app.logger.warning("G(%s) failed: %s", name, e)
