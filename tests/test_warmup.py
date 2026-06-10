"""Boot-time kernel warm-up (src/aegis/viewer/warmup.py).

The warm-up compiles the dosimetry numba kernels at worker start so the first
real lab/viewer compute does not pay ~60 s of JIT. The critical invariant is
that the warm-up mesh stays NON-CONVEX: a convex mesh hits the short-circuit in
``geometry.visibility._is_convex`` and the most expensive kernel (the self-shadow
visibility bake) never compiles, silently defeating the warm-up.
"""

import pytest


def test_warmup_mesh_is_nonconvex():
    pytest.importorskip("scipy")
    from aegis.geometry.visibility import _is_convex
    from aegis.viewer.warmup import _warmup_mesh

    mesh = _warmup_mesh()
    assert mesh.n_triangles == 40  # two icosahedra
    assert _is_convex(mesh) is False, "warm-up mesh must be non-convex to compile the self-shadow bake"


@pytest.mark.slow
def test_warm_kernels_runs():
    # Cold this compiles every kernel (~60 s); kept out of the fast suite.
    pytest.importorskip("numba")
    pytest.importorskip("flask")
    from aegis.viewer.warmup import warm_kernels

    warm_kernels()  # best-effort, must complete without raising
