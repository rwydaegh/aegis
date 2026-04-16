"""Flask server for the AEGIS interactive viewer.

Split into submodules:

- ``_cache`` — module-level cache dict, lock, and session-scoped helpers
- ``_fidelity`` — ``FIDELITY_LEVELS_API`` catalog
- ``_auth`` — password gate for protected deployments
- ``_bodies`` — body-mesh preload
- ``_voxels`` — voxel-set preload
- ``_precompute`` — background averaging-matrix warmup
- ``_app`` — ``create_app`` factory plus lightweight inline routes
"""

from __future__ import annotations

from ._app import create_app, create_app_from_env
from ._cache import (
    _cache,
    _cache_lock,
    scoped_cache_clear_session,
    scoped_cache_get,
    scoped_cache_pop,
    scoped_cache_set,
)
from ._fidelity import FIDELITY_LEVELS_API
from ._voxels import _load_and_cache_voxels_dir, _load_and_cache_voxels_single

__all__ = [
    "FIDELITY_LEVELS_API",
    "_cache",
    "_cache_lock",
    "_load_and_cache_voxels_dir",
    "_load_and_cache_voxels_single",
    "create_app",
    "create_app_from_env",
    "scoped_cache_clear_session",
    "scoped_cache_get",
    "scoped_cache_pop",
    "scoped_cache_set",
]
