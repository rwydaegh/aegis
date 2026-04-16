"""Base station API routes: load, list, and compute dosimetry from cell towers.

Split into submodules:

- ``_geocode`` — forward/reverse geocoding + country/region mapping
- ``_fidelity`` — fidelity tier + ``_bs_summary`` JSON serializer
- ``_data`` — data-source resolution and list handler
- ``_load`` — POST /api/basestations/load
- ``_compute`` — POST /api/basestations/compute
- ``_compute_mimo`` — POST /api/basestations/compute_mimo
"""

from __future__ import annotations

import threading

from flask import Flask

from ._compute import _handle_basestations_compute
from ._compute_mimo import _handle_basestations_compute_mimo
from ._data import _handle_basestations_list
from ._fidelity import _bs_summary, _compute_fidelity_tier
from ._geocode import _resolve_belgian_region, geocode_location
from ._load import _handle_basestations_load

__all__ = [
    "_bs_summary",
    "_compute_fidelity_tier",
    "_handle_basestations_compute",
    "_handle_basestations_compute_mimo",
    "_handle_basestations_list",
    "_handle_basestations_load",
    "_resolve_belgian_region",
    "geocode_location",
    "register",
]


def register(app: Flask, cache: dict, cache_lock: threading.RLock) -> None:
    """Register base station API routes."""

    @app.route("/api/basestations/load", methods=["POST"])
    def api_basestations_load():
        return _handle_basestations_load(cache, cache_lock)

    @app.route("/api/basestations/list")
    def api_basestations_list():
        return _handle_basestations_list(cache, cache_lock)

    @app.route("/api/basestations/compute", methods=["POST"])
    def api_basestations_compute():
        return _handle_basestations_compute(cache, cache_lock)

    @app.route("/api/basestations/compute_mimo", methods=["POST"])
    def api_basestations_compute_mimo():
        return _handle_basestations_compute_mimo(cache, cache_lock)
