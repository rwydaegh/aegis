"""Dependency-contract tests.

These guard cross-layer packaging assumptions that unit tests cannot see: the
test/dev environment always installs every accelerator, so a dependency missing
from a *shipped* extra (e.g. the production Docker image) degrades silently
rather than failing a test. The self-shadow toggle hung in production for
exactly this reason: numba lived only in the optional 'fast' extra, the viewer
image installed '.[viewer,body]', and the @njit bakes fell back to pure Python.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import numpy as np
import pytest

from aegis.geometry.mesh import BodyMesh

_PYPROJECT = Path(__file__).resolve().parents[1] / "pyproject.toml"


def _viewer_extra_deps() -> list[str]:
    data = tomllib.loads(_PYPROJECT.read_text())
    return data["project"]["optional-dependencies"]["viewer"]


def test_viewer_extra_requires_numba():
    # The viewer UI exposes self-shadowing and inter-body reflection, whose
    # @njit visibility/occlusion bakes are unusable without the JIT. numba must
    # therefore be a hard viewer dependency, not an optional accelerator, so no
    # install path (Dockerfile included) can ship the viewer without it.
    deps = " ".join(_viewer_extra_deps()).lower()
    assert "numba" in deps, "viewer extra must declare numba (self-shadow/occlusion need the JIT)"


def test_self_shadow_bake_fails_fast_without_numba(monkeypatch):
    # Without numba the bake must raise immediately, not silently run a
    # pure-Python ray-cast that pins a worker for minutes.
    from aegis.geometry import visibility

    monkeypatch.setattr(visibility, "NUMBA_AVAILABLE", False)
    body = BodyMesh.sphere(radius=0.2, n_subdivisions=1)
    with pytest.raises(RuntimeError, match="numba"):
        visibility.directional_clearance(body, np.array([[1.0, 0.0, 0.0]]))


def test_numba_actually_importable():
    # The dev/test environment itself must have numba so the JIT paths are
    # exercised (catches a broken local install). NUMBA_AVAILABLE reflects a
    # successful import at module load.
    from aegis.geometry import visibility

    assert visibility.NUMBA_AVAILABLE is True
