"""Coherent Exposure Studio API routes (data layer).

Phase 1a is the data layer only: config resolution (``_config``) and this
blueprint stub. ``register`` is intentionally a no-op for now; the studio
endpoints (pack listing, body-map serving) arrive in a later task. The stub
exists so the viewer app can wire the studio in without conditional imports.

The runtime studio is fork-free: it reads precomputed packs resolved by
``_config.studio_data_dir`` and never imports the paper fork or the ray tracer.
"""

from __future__ import annotations

import threading

from flask import Flask

from ._config import available_packs, paper_fork_paths_dir, studio_data_dir

__all__ = [
    "available_packs",
    "paper_fork_paths_dir",
    "register",
    "studio_data_dir",
]


def register(app: Flask, cache: dict, cache_lock: threading.RLock) -> None:
    """Register Coherent Exposure Studio API routes.

    No-op stub for Phase 1a. Endpoints are added in a later task; this keeps
    the registration call site stable in the meantime.
    """
    return None
