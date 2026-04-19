"""Metamorphic relation: incoherent sab is additive over disjoint path sets.

Monograph: Eq. 5.4 (sec:matrix):

    S_ab = T0 * ReLU(M) @ s,

where `s` is the per-path power vector and M is the (M_tri x N) matrix
of per-(triangle, path) incidence cosines. The expression is linear
in `s`. Splitting the columns of M (equivalently, the entries of s)
into two disjoint groups A and B gives

    S_ab(A union B) = S_ab(A) + S_ab(B).

Similarly, Levels 3 and 4 extend this to Sum_i T_eff_i(mu_{j,i}) *
ReLU(mu_{j,i}) * S_i, still linear in the per-path powers.

Applies to: Levels 2, 3, 4 (q=0).
Does NOT apply to the coherent levels 7 and 8: the coherent Sab has
cross-terms between paths by design (Theorem 4.1 squared norm).
"""

from __future__ import annotations

import numpy as np
import pytest
from conftest import make_icosahedron
from hypothesis import given, settings
from hypothesis import strategies as st

from aegis.engine import DosimetryEngine
from aegis.paths import PropagationPaths
from aegis.tissue.dielectric import SKIN_28GHZ


def _random_paths(seed: int, n: int) -> PropagationPaths:
    rng = np.random.default_rng(seed)
    k_hat = rng.standard_normal((n, 3))
    k_hat /= np.linalg.norm(k_hat, axis=1, keepdims=True)
    power = rng.uniform(0.1, 3.0, size=n)
    return PropagationPaths.from_powers(k_hat=k_hat, power=power)


@pytest.mark.parametrize("level", [2, 3, 4])
@pytest.mark.parametrize("seed_pair", [(0, 1), (17, 42), (100, 200)])
def test_superposition_two_disjoint_sets(level: int, seed_pair: tuple[int, int]) -> None:
    """sab(A union B) equals sab(A) + sab(B) element-wise.

    A and B are generated with different seeds so their directions and
    powers are uncorrelated.
    """
    seed_a, seed_b = seed_pair
    paths_a = _random_paths(seed_a, n=5)
    paths_b = _random_paths(seed_b, n=4)
    paths_ab = PropagationPaths.concatenate([paths_a, paths_b])

    body = make_icosahedron()
    engine = DosimetryEngine(SKIN_28GHZ)
    kwargs = {"q": 0.0} if level == 4 else {}

    sab_a = np.asarray(engine.compute_sab(body, paths_a, level=level, **kwargs))
    sab_b = np.asarray(engine.compute_sab(body, paths_b, level=level, **kwargs))
    sab_ab = np.asarray(engine.compute_sab(body, paths_ab, level=level, **kwargs))

    np.testing.assert_allclose(sab_ab, sab_a + sab_b, rtol=1e-12, atol=1e-14)


@pytest.mark.parametrize("level", [2, 3, 4])
def test_superposition_three_way(level: int) -> None:
    """Additivity holds for three disjoint path sets (by induction of the
    two-set relation, but worth exercising to catch off-by-one seam bugs
    between concatenate calls)."""
    a = _random_paths(1, n=3)
    b = _random_paths(2, n=3)
    c = _random_paths(3, n=3)
    abc = PropagationPaths.concatenate([a, b, c])

    body = make_icosahedron()
    engine = DosimetryEngine(SKIN_28GHZ)
    kwargs = {"q": 0.0} if level == 4 else {}

    s_a = np.asarray(engine.compute_sab(body, a, level=level, **kwargs))
    s_b = np.asarray(engine.compute_sab(body, b, level=level, **kwargs))
    s_c = np.asarray(engine.compute_sab(body, c, level=level, **kwargs))
    s_abc = np.asarray(engine.compute_sab(body, abc, level=level, **kwargs))

    np.testing.assert_allclose(s_abc, s_a + s_b + s_c, rtol=1e-12, atol=1e-14)


@given(
    n_a=st.integers(min_value=1, max_value=8),
    n_b=st.integers(min_value=1, max_value=8),
    seed_a=st.integers(min_value=0, max_value=2**31 - 1),
    seed_b=st.integers(min_value=0, max_value=2**31 - 1),
)
@settings(max_examples=25, deadline=5000)
def test_superposition_hypothesis_level3(n_a: int, n_b: int, seed_a: int, seed_b: int) -> None:
    """Hypothesis sweep over arbitrary path-set sizes and contents."""
    paths_a = _random_paths(seed_a, n=n_a)
    paths_b = _random_paths(seed_b, n=n_b)
    paths_ab = PropagationPaths.concatenate([paths_a, paths_b])

    body = make_icosahedron()
    engine = DosimetryEngine(SKIN_28GHZ)

    sab_a = np.asarray(engine.compute_sab(body, paths_a, level=3))
    sab_b = np.asarray(engine.compute_sab(body, paths_b, level=3))
    sab_ab = np.asarray(engine.compute_sab(body, paths_ab, level=3))

    np.testing.assert_allclose(sab_ab, sab_a + sab_b, rtol=1e-11, atol=1e-13)
