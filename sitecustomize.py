"""Repo-local Python startup tweaks for src-layout development.

Running ``python -m aegis...`` from the repository root starts a fresh
interpreter without pytest's ``pythonpath`` adjustments. Insert ``src`` on
``sys.path`` early so subprocess CLIs resolve the local package consistently.
"""

from __future__ import annotations

import sys
from pathlib import Path


_ROOT = Path(__file__).resolve().parent
_SRC = _ROOT / "src"

if _SRC.is_dir():
    src_str = str(_SRC)
    if src_str not in sys.path:
        sys.path.insert(0, src_str)
