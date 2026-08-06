"""Stable JSON serialization for computed material-study artifacts."""

from __future__ import annotations

import json
import math
import numbers
from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np

# NumPy's X86_V3 and X86_V4 math loops can differ in the last binary digit.
# Thirteen significant decimal digits keep the useful precision while making
# publication artifacts byte-identical across those CPU implementations.
PUBLICATION_SIGNIFICANT_DIGITS = 13


def _canonical_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _canonical_value(item) for key, item in value.items()}
    if isinstance(value, np.ndarray):
        return _canonical_value(value.tolist())
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_canonical_value(item) for item in value]
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if isinstance(value, numbers.Integral):
        return int(value)
    if isinstance(value, numbers.Real):
        scalar = float(value)
        if math.isfinite(scalar):
            return float(f"{scalar:.{PUBLICATION_SIGNIFICANT_DIGITS}g}")
        return scalar
    return value


def publication_json(payload: Any, *, indent: int = 1) -> str:
    """Encode computed results with stable 13-significant-digit floats."""
    return json.dumps(_canonical_value(payload), indent=indent)
