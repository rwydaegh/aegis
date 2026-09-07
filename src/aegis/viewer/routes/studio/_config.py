"""Data-layer config for the Coherent Exposure Studio.

Resolves where the studio's precomputed packs live (ray packs, phantom packs,
per-triangle body-map packs, ensemble packs) and reports what is present. The
runtime viewer reads only these packs; it never touches the paper fork or the
ray tracer. Packs are produced offline by ``scripts/studio_precompute.py``.
"""

from __future__ import annotations

import os
from pathlib import Path

# Repo root is five parents up from this file:
# src/aegis/viewer/routes/studio/_config.py -> repo/
_REPO_ROOT = Path(__file__).resolve().parents[5]

# Subdirectories of the studio data dir, one per pack kind.
_PACK_DIRS = ("rays", "phantom", "bodymaps", "ensemble", "qop", "channel")


def studio_data_dir() -> Path:
    """Resolve the studio data directory.

    Resolution order:

    1. ``AEGIS_STUDIO_PATHS`` env var (used as-is).
    2. ``AEGIS_DATA_DIR`` env var, then ``<AEGIS_DATA_DIR>/studio``.
    3. The repo's ``data/studio/``.

    The path is returned whether or not it exists; callers that scan it must
    tolerate a missing directory.
    """
    override = os.environ.get("AEGIS_STUDIO_PATHS")
    if override:
        return Path(override)
    data_dir = os.environ.get("AEGIS_DATA_DIR")
    if data_dir:
        return Path(data_dir) / "studio"
    return _REPO_ROOT / "data" / "studio"


def available_packs() -> dict[str, list[str]]:
    """Scan the studio data dir and report the packs present.

    Returns a dict keyed by pack kind (``rays``, ``phantom``, ``bodymaps``,
    ``ensemble``, ``qop``, ``channel``), each value a sorted list of pack stems
    (filenames without the ``.npz`` suffix). A missing data dir or missing subdir yields
    empty lists rather than raising, so a fresh checkout reports an empty
    structure.
    """
    root = studio_data_dir()
    out: dict[str, list[str]] = {kind: [] for kind in _PACK_DIRS}
    if not root.is_dir():
        return out
    for kind in _PACK_DIRS:
        sub = root / kind
        if sub.is_dir():
            out[kind] = sorted(p.stem for p in sub.glob("*.npz"))
    return out


def paper_fork_paths_dir() -> Path | None:
    """Return the paper fork's cached e11 ray-path dir, or None if absent.

    Used ONLY by the offline precompute script to seed ray packs from the
    coherent-exposure-operator paper. Never call this at request time: the
    runtime viewer must stay fork-free.
    """
    candidate = _REPO_ROOT / "private" / "papers" / "coherent-exposure-operator" / "data" / "e11_paths"
    return candidate if candidate.is_dir() else None
