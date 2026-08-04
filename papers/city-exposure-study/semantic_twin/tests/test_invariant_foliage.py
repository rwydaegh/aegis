"""What a participating medium has to obey, and where the module argues with itself.

Two kinds of check live here.

The first is an identity with a name. A slab of optical depth ``tau`` seen from
below, under directions drawn uniformly in solid angle, transmits ``E_2(tau)``,
the second exponential integral, because a ray at cosine ``mu`` traverses
``tau/mu`` and ``E_2(tau)`` is exactly ``integral of exp(-tau/mu) dmu`` over the
unit interval. That single number ties together the free flight sampling, the
canopy hull parity flag and the escape credit, and it is available in closed
form from SciPy, so nothing about it is calibrated against this repository.

The second is consistency. When one module computes the same physical quantity
twice by different routes, the two answers have to agree. No external reference
is needed and no judgement is involved, which makes it the cheapest real test
there is.
"""

from __future__ import annotations

import numpy as np
import pytest
from scipy.special import expn

from semantic_twin.materials.foliage import (
    CanopyCanyonGeometry,
    FoliageMedium,
    FoliageTracer,
    ret_parameters,
    slab_transmission,
)
from semantic_twin.illumination import ISOTROPIC

#: The canopy hull spans this half width, so a ray leaving the observation point
#: at any elevation above about a hundredth of a degree enters the slab through
#: its base and leaves through its top rather than out of a side. The remainder
#: is one part in ten thousand of the sphere.
HALF_WIDTH_M = 50_000.0
OBSERVER_Z_M = 1.5
CANOPY_BASE_M = 2.0
CANOPY_DEPTH_M = 6.0
RAYS = 200_000


def slab_geometry() -> CanopyCanyonGeometry:
    """Ground, no facades, and a canopy slab wide enough to be a slab."""
    return CanopyCanyonGeometry(
        street_width_m=2.0 * HALF_WIDTH_M,
        street_length_m=2.0 * HALF_WIDTH_M,
        facade_height_m=0.0,
        canopy_half_width_m=HALF_WIDTH_M,
        canopy_base_m=CANOPY_BASE_M,
        canopy_depth_m=CANOPY_DEPTH_M,
    )


_CACHE: dict[tuple[float, float, float, int], object] = {}


def trace_slab(optical_depth: float, *, albedo: float = 0.0, observer_z_m: float = OBSERVER_Z_M, seed: int = 5):
    """One sweep point under a purely absorbing slab.

    The ground is given the permittivity of air so it reflects nothing. That
    leaves exactly one route to a credited escape, straight up through the slab,
    which is what makes the answer an identity rather than a sum of terms.
    """
    key = (optical_depth, albedo, observer_z_m, seed)
    if key in _CACHE:
        return _CACHE[key]
    geometry = slab_geometry()
    medium = FoliageMedium(
        extinction_per_m=optical_depth / CANOPY_DEPTH_M,
        albedo=albedo,
        forward_fraction=0.0,
        phase_beamwidth_deg=180.0,
    )
    tracer = FoliageTracer(
        geometry,
        permittivity=np.full(4, complex(1.0, 0.0)),
        rms_height_m=np.full(4, 1.0),
        frequency_hz=15.0e9,
        medium=medium,
        rays=RAYS,
        seed=seed,
    )
    _CACHE[key] = tracer.trace(np.array([0.0, 0.0, observer_z_m]), {"isotropic": ISOTROPIC})
    return _CACHE[key]


@pytest.mark.parametrize("optical_depth", [0.5, 1.0, 2.0])
def test_the_slab_reproduces_the_second_exponential_integral(optical_depth):
    """``chi`` under an absorbing slab is ``E_2(tau) / 2``, and nothing else.

    Half, because only the upward half of the sphere sees the slab at all and
    the downward half is killed at the ground. The three depths span a factor of
    nine in transmitted power, 0.327 down to 0.037, so a wrong exponent or a
    misplaced cosine cannot survive all three by accident.
    """
    result = trace_slab(optical_depth)
    expected = 0.5 * float(expn(2, optical_depth))
    assert result.susceptibility["isotropic"] == pytest.approx(expected, rel=0.03)


def test_the_slab_answer_is_not_degenerate():
    """The identity must actually be doing work.

    An estimator that credited everything would give 0.5 and one that credited
    nothing would give 0. Both are far from every target above, which is what
    makes the test above sharp.
    """
    values = [0.5 * float(expn(2, tau)) for tau in (0.5, 1.0, 2.0)]
    assert values[0] / values[-1] > 8.0
    assert all(0.01 < v < 0.2 for v in values)


def test_a_thicker_slab_never_transmits_more():
    """Monotone in optical depth, checked on the estimator and not on the maths."""
    measured = [trace_slab(tau).susceptibility["isotropic"] for tau in (0.5, 1.0, 2.0)]
    assert measured[0] > measured[1] > measured[2] > 0.0


@pytest.mark.parametrize("frequency_ghz", [1.3, 11.2, 28.8, 61.5])
@pytest.mark.parametrize("depth_m", [1.0, 4.5])
@pytest.mark.xfail(
    strict=True,
    reason="docs/BUGS.md finding 4: foliage.py:239 uses 8.686 dB per neper where "
    "ITU-R P.833-10 equation (12) makes exp(-tau) a power transmittance, so the "
    "factor is 4.343 and the module disagrees with its own slab_transmission by two",
)
def test_the_two_routes_from_extinction_to_decibels_agree(frequency_ghz, depth_m):
    """One module, one sigma, two answers that must be the same answer.

    ``specific_attenuation_db_per_m`` converts the tabulated ``sigma_tau`` to dB
    per metre directly. ``slab_transmission`` exponentiates the same ``sigma_tau``
    and the loss of that transmittance is also dB per metre. No external
    reference is involved, so whichever factor is right, these two cannot both
    be. They differ by exactly two, at every frequency and every depth.
    """
    parameters = ret_parameters(frequency_ghz * 1e9)
    medium = FoliageMedium(
        extinction_per_m=parameters.sigma_tau_per_m,
        albedo=parameters.albedo,
        forward_fraction=parameters.alpha,
        phase_beamwidth_deg=parameters.phase_beamwidth_deg,
    )
    from_the_slab = -10.0 * np.log10(slab_transmission(medium, depth_m)) / depth_m
    assert parameters.specific_attenuation_db_per_m == pytest.approx(from_the_slab, rel=1e-9)


#: Half way up the slab, so an observer there has half the optical depth above
#: it and the identity still applies with ``tau`` halved.
INSIDE_Z_M = CANOPY_BASE_M + 0.5 * CANOPY_DEPTH_M


@pytest.mark.xfail(
    strict=True,
    reason="docs/BUGS.md finding 9: foliage.py:775 leaves the inside-canopy flag False "
    "for an observer that starts inside the hull, so the parity is inverted for the "
    "whole trace, the medium is transparent on the way out and opaque everywhere else",
)
def test_an_observer_inside_the_canopy_obeys_the_same_identity():
    """Standing under the branches is a physical place to stand.

    The identity does not care where the observation point is, only how much
    optical depth lies between it and the sky. Half way up a slab of two, the
    target is ``E_2(1) / 2``, which is 0.074 and nothing like zero.

    The estimator returns exactly zero. The parity flag starts on the wrong side,
    so the way out through the real medium is free of collisions and everything
    beyond the hull, where there is no medium at all, collides and is absorbed.
    Nothing raises and no counter looks odd, which is why this needs a target
    rather than a sanity check.
    """
    result = trace_slab(2.0, observer_z_m=INSIDE_Z_M)
    expected = 0.5 * float(expn(2, 1.0))
    assert result.susceptibility["isotropic"] == pytest.approx(expected, rel=0.05)


def test_the_same_observer_just_below_the_canopy_obeys_it():
    """The control for the test above, and the reason it names a parity flag.

    Move the observation point out of the hull, keep the same optical depth
    above it by halving the slab, and the estimator lands on the same target. So
    the medium is right, the geometry is right, and what is wrong is which side
    of the hull the trace thinks it started on.
    """
    result = trace_slab(1.0, observer_z_m=OBSERVER_Z_M)
    expected = 0.5 * float(expn(2, 1.0))
    assert result.susceptibility["isotropic"] == pytest.approx(expected, rel=0.05)
