"""Metamorphic relation: at normal incidence (mu = 1), sab is
polarisation-universal and equals S_inc * T0 exactly.

Monograph: appendix "Peak Sab is polarisation-universal"
(around line 5378 of monograph_v2.tex) and sec:exact-bounds:

    At theta = 0 (normal incidence), Delta T = 0, so T_eff(0) = T0
    for any polarisation and Sab(0) = S_inc * T0.

    max over (theta, polarisation) of Sab = S_inc * T0, with equality
    at normal incidence. The bound is exact, not approximate.

The Level 4 kernel computes

    T_eff = T_avg(mu) + 0.5 * q * (T_p(mu) - T_s(mu)).

At mu = 1, T_s = T_p = T0 (every Fresnel formula reduces to the
normal-incidence case), so T_eff = T0 regardless of q. The ReLU gate
is 1 at mu = 1, so sab = S_inc * T_eff = S_inc * T0.

Applies to: Levels 2, 3, 4.
Level 2 uses a constant T0, so this is tautological at Level 2 but
worth including as a baseline regression case. Level 3 exercises the
Fresnel machinery; Level 4 exercises the polarisation-correction term.
"""

from __future__ import annotations

import numpy as np
import pytest
from conftest import make_flat_mesh

from aegis.engine import DosimetryEngine
from aegis.paths import PropagationPaths
from aegis.tissue.dielectric import FAT_28GHZ, MUSCLE_28GHZ, SKIN_28GHZ, SKIN_60GHZ


@pytest.mark.parametrize(
    "tissue",
    [SKIN_28GHZ, SKIN_60GHZ, MUSCLE_28GHZ, FAT_28GHZ],
    ids=["skin28", "skin60", "muscle28", "fat28"],
)
@pytest.mark.parametrize("level", [2, 3])
@pytest.mark.parametrize("s_inc", [0.1, 1.0, 17.3])
def test_peak_sab_at_normal_incidence(tissue, level: int, s_inc: float) -> None:
    """A flat +z-facing mesh hit head-on from -z gets sab = S_inc * T0 everywhere.

    Every triangle has mu = 1 exactly, so sab should equal S_inc * T0.
    """
    mesh = make_flat_mesh(50)  # all triangles have normal = +z
    paths = PropagationPaths.from_powers(
        k_hat=np.array([[0.0, 0.0, -1.0]]),
        power=np.array([s_inc]),
    )

    engine = DosimetryEngine(tissue)
    sab = np.asarray(engine.compute_sab(mesh, paths, level=level))

    expected = s_inc * tissue.T0
    np.testing.assert_allclose(sab, expected, rtol=1e-12, atol=1e-14)


@pytest.mark.parametrize(
    "q",
    [-1.0, -0.5, -0.1, 0.0, 0.1, 0.5, 1.0],
    ids=lambda v: f"q={v:+.1f}",
)
@pytest.mark.parametrize("s_inc", [1.0, 5.0])
def test_peak_sab_polarisation_universal_level4(q: float, s_inc: float) -> None:
    """Level 4 at mu=1 gives sab = S_inc * T0 for ALL q in [-1, 1].

    This is the key content of the "peak is polarisation-universal"
    result in the monograph. The Fresnel splitting T_p - T_s vanishes
    at normal incidence, so the polarisation-correction term in T_eff
    vanishes independently of q.
    """
    mesh = make_flat_mesh(30)
    paths = PropagationPaths.from_powers(
        k_hat=np.array([[0.0, 0.0, -1.0]]),
        power=np.array([s_inc]),
    )

    engine = DosimetryEngine(SKIN_28GHZ)
    sab = np.asarray(engine.compute_sab(mesh, paths, level=4, q=q))

    expected = s_inc * SKIN_28GHZ.T0
    np.testing.assert_allclose(sab, expected, rtol=1e-12, atol=1e-14)


def test_peak_sab_bound_elsewhere() -> None:
    """For any mu in [0, 1], sab at Level 3 is <= S_inc * T0.

    Monograph App "Peak Sab is polarisation-universal" establishes
    T_eff(theta) * cos(theta) <= T0 as an exact bound. We verify it
    across a range of incidence angles for skin at 28 GHz.

    This is adjacent to the metamorphic relation above: the relation
    "sab(mu=1) = S_inc * T0" is the equality case of the bound
    "sab(mu) <= S_inc * T0" proved in the monograph.
    """
    mesh = make_flat_mesh(20)

    # Sweep incidence angles from 0 to nearly grazing
    engine = DosimetryEngine(SKIN_28GHZ)
    s_inc = 2.0

    for theta_deg in [0, 10, 30, 45, 60, 75, 85]:
        theta = np.radians(theta_deg)
        # k_hat propagates downward-and-sideways toward the +z mesh
        k_hat = np.array([[np.sin(theta), 0.0, -np.cos(theta)]])
        paths = PropagationPaths.from_powers(k_hat=k_hat, power=np.array([s_inc]))
        sab = np.asarray(engine.compute_sab(mesh, paths, level=3))

        bound = s_inc * SKIN_28GHZ.T0
        assert sab.max() <= bound + 1e-12, (
            f"Peak sab={sab.max():.6g} exceeds bound S_inc*T0={bound:.6g} at theta={theta_deg} deg"
        )
