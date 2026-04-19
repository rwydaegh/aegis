"""Metamorphic relation: per-triangle incoherent sab is invariant under
uniform geometric scaling of the mesh.

Monograph: Eq. 2.5, Eq. 5.4.

    Sab(r) = S_inc * T_eff(mu) * ReLU(mu).

None of T_eff, mu, or S_inc depend on vertex positions or triangle
areas. Normals are unit vectors, so scaling all vertices by lambda > 0
leaves normals unchanged. Therefore per-triangle sab is invariant. The
total absorbed power scales as lambda^2 because

    P_abs = sum(sab * areas),    areas -> lambda^2 * areas.

Applies to: Levels 2, 3, 4 (q=0).
Does NOT apply to Levels 7 and 8: the coherent kernel depends on
exp(-i k_0 k_hat . r_centroid), which is not scale-invariant. Levels 5
and 6 depend on curvature H, which scales as 1/lambda, so sab is not
scale-invariant there either. Those levels are skipped.
"""

from __future__ import annotations

import numpy as np
import pytest
from conftest import make_icosahedron
from hypothesis import given, settings
from hypothesis import strategies as st

from aegis.engine import DosimetryEngine
from aegis.geometry.mesh import BodyMesh
from aegis.paths import PropagationPaths
from aegis.tissue.dielectric import SKIN_28GHZ


def _scale_mesh(mesh: BodyMesh, factor: float) -> BodyMesh:
    """Uniformly scale vertex positions and centroids by `factor`.

    Areas scale by factor^2 (2D measure on the surface). Normals are
    unit vectors; they are unchanged.
    """
    return BodyMesh(
        vertices=mesh.vertices * factor,
        normals=mesh.normals,
        centroids=mesh.centroids * factor,
        areas=mesh.areas * (factor * factor),
        name=f"{mesh.name}_scaled",
    )


@pytest.mark.parametrize("level", [2, 3, 4])
@pytest.mark.parametrize("factor", [0.1, 0.5, 1.0, 2.0, 10.0, 100.0])
def test_per_triangle_sab_invariant_under_scaling(level: int, factor: float) -> None:
    """Per-triangle sab is identical before and after mesh scaling.

    The mesh is uniformly scaled about the origin. Paths are unchanged.
    """
    body = make_icosahedron()
    rng = np.random.default_rng(54321)
    k_hat = rng.standard_normal((7, 3))
    k_hat /= np.linalg.norm(k_hat, axis=1, keepdims=True)
    power = rng.uniform(0.2, 4.0, size=7)
    paths = PropagationPaths.from_powers(k_hat=k_hat, power=power)

    engine = DosimetryEngine(SKIN_28GHZ)
    kwargs = {"q": 0.0} if level == 4 else {}
    sab_ref = np.asarray(engine.compute_sab(body, paths, level=level, **kwargs))
    sab_scaled = np.asarray(engine.compute_sab(_scale_mesh(body, factor), paths, level=level, **kwargs))

    np.testing.assert_allclose(sab_scaled, sab_ref, rtol=1e-13, atol=1e-15)


@pytest.mark.parametrize("level", [2, 3])
@pytest.mark.parametrize("factor", [0.5, 2.0, 5.0])
def test_total_power_scales_as_factor_squared(level: int, factor: float) -> None:
    """P_abs = sum(sab * areas) scales exactly as factor^2."""
    body = make_icosahedron()
    rng = np.random.default_rng(777)
    k_hat = rng.standard_normal((5, 3))
    k_hat /= np.linalg.norm(k_hat, axis=1, keepdims=True)
    power = rng.uniform(0.5, 2.0, size=5)
    paths = PropagationPaths.from_powers(k_hat=k_hat, power=power)

    engine = DosimetryEngine(SKIN_28GHZ)
    p_ref = engine.compute(body, paths, level=level).p_abs
    p_scaled = engine.compute(_scale_mesh(body, factor), paths, level=level).p_abs

    # spatial averaging matrix changes under scaling because it is
    # target-area based. compute.p_abs is sum(sab*areas) of the raw sab,
    # independent of the averaging matrix, so this relation is exact.
    assert abs(p_scaled - factor * factor * p_ref) <= 1e-12 * (factor * factor * p_ref + 1e-30)


@given(
    factor=st.floats(min_value=1e-3, max_value=1e3, allow_nan=False, allow_infinity=False),
    seed=st.integers(min_value=0, max_value=2**31 - 1),
)
@settings(max_examples=25, deadline=5000)
def test_mesh_scaling_hypothesis(factor: float, seed: int) -> None:
    """Hypothesis sweep across many scale factors, Level 3."""
    body = make_icosahedron()
    rng = np.random.default_rng(seed)
    k_hat = rng.standard_normal((6, 3))
    k_hat /= np.linalg.norm(k_hat, axis=1, keepdims=True)
    power = rng.uniform(0.1, 5.0, size=6)
    paths = PropagationPaths.from_powers(k_hat=k_hat, power=power)

    engine = DosimetryEngine(SKIN_28GHZ)
    sab_ref = np.asarray(engine.compute_sab(body, paths, level=3))
    sab_scaled = np.asarray(engine.compute_sab(_scale_mesh(body, factor), paths, level=3))

    np.testing.assert_allclose(sab_scaled, sab_ref, rtol=1e-12, atol=1e-14)
