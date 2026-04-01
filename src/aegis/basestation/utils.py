"""Shared utilities for the basestation module."""

from __future__ import annotations

import re

import numpy as np


def _sanitize_label(label: str) -> str:
    """Replace special characters with underscores for pattern key lookup."""
    return re.sub(r"[() .&/\\-]", "_", label)


def _safe_float(val, default: float = 0.0) -> float:
    """Convert to float, returning default for NaN/None."""
    try:
        f = float(val)
        return default if np.isnan(f) else f
    except (TypeError, ValueError):
        return default
