"""A grating far below the wavelength is a uniform slab, and it knows which one.

This is the referee that energy conservation cannot be. Shrink the period of a
lamellar grating well below the wavelength and the field stops resolving the
stripes. What is left is a slab with two known permittivities: the arithmetic
mean of the profile for the field along the stripes, and the harmonic mean for
the field across them. Both are exact limits with no fitted constant in them,
and the two differ here by a factor of 1.9, which is a wide target.

The harmonic mean is the one that tests the Fourier factorisation. The field
across the stripes has a discontinuous normal component, so the product
``eps * E`` cannot be factorised term by term, and the whole point of Li's
inverse rule is to handle that. Laurent's rule still converges, slowly, from the
wrong side, which is what makes the defect survive every check that is not this
one.

Two independent statements are made about the same solve.

The limit. The reference is the same solver on a homogeneous layer, which takes
the analytic branch and never forms a convolution matrix, so the comparison
isolates the factorisation and holds the scattering matrix machinery, the branch
cut and the order bookkeeping fixed on both sides.

The convergence. A truncated modal series that is reported as an answer has to
have stopped moving by the truncation it is reported at. That needs no reference
at all, and it is the sharper of the two: doubling the retained orders from 16
to 32 moves the across-stripe reflectance by 4 percent of itself today and by 3
parts in a million under the inverse rule.

Why the period is one four hundredth of a wavelength rather than something
rounder. A subwavelength grating slab is not exactly a homogeneous slab. Its two
faces carry evanescent boundary layers, and for the across-stripe field those
are worth a correction that was measured here to fall linearly with the period,
+3.24 percent at one fiftieth, +0.78 at one two hundredth, +0.39 at one four
hundredth. That correction is physics, not solver error, so the period is set
small enough that it sits well inside the tolerance and the tolerance still
leaves a factor of twelve to the defect.
"""

from __future__ import annotations

import numpy as np
import pytest

from semantic_twin.materials.masonry.rcwa import Layer, solve

EPS_MORTAR = complex(1.0, 0.0)
EPS_BRICK = complex(5.31, 0.0)
FILL = 0.5

FREQUENCY_HZ = 15.0e9
WAVELENGTH_M = 299_792_458.0 / FREQUENCY_HZ
PERIOD_M = WAVELENGTH_M / 400.0
THICKNESS_M = 0.010
SAMPLES = 1024

ARITHMETIC = FILL * EPS_BRICK + (1.0 - FILL) * EPS_MORTAR
HARMONIC = 1.0 / (FILL / EPS_BRICK + (1.0 - FILL) / EPS_MORTAR)


def stripes() -> np.ndarray:
    """One period of the profile, sampled across ``x`` and uniform in ``y``."""
    x = (np.arange(SAMPLES) + 0.5) / SAMPLES
    return np.where(x < FILL, EPS_BRICK, EPS_MORTAR)[None, :]


_CACHE: dict[tuple[str, int], tuple[float, float]] = {}


def reflect(permittivity, polarisation: str, m_max: int) -> tuple[float, float]:
    """``(reflectance, transmittance)`` of a free standing slab of that layer."""
    key = (polarisation, m_max) if isinstance(permittivity, np.ndarray) else (f"ref{permittivity}", m_max)
    if key in _CACHE:
        return _CACHE[key]
    solution = solve(
        [
            Layer(permittivity=complex(1.0, 0.0)),
            Layer(permittivity=permittivity, thickness_m=THICKNESS_M),
            Layer(permittivity=complex(1.0, 0.0)),
        ],
        period_x_m=PERIOD_M,
        period_y_m=PERIOD_M,
        frequency_hz=FREQUENCY_HZ,
        theta_deg=0.0,
        phi_deg=0.0,
        polarisation=polarisation,
        harmonics=(m_max, 0),
    )
    _CACHE[key] = (solution.total_reflectance, solution.total_transmittance)
    return _CACHE[key]


def test_the_two_effective_media_are_a_wide_target():
    """Guard on the referee itself.

    If the arithmetic and harmonic means gave nearly the same reflectance, a
    solver could land on either and the tests below would prove nothing. They
    are a factor of three apart in reflected power.
    """
    assert ARITHMETIC.real / HARMONIC.real > 1.8
    along, _ = reflect(ARITHMETIC, "te", 1)
    across, _ = reflect(HARMONIC, "tm", 1)
    assert along / across > 2.5


@pytest.mark.parametrize("m_max", [4, 16])
def test_the_field_along_the_stripes_finds_the_arithmetic_mean(m_max):
    """The easy factorisation, and the positive control for this file.

    With the field parallel to the stripes the permittivity is continuous along
    it, Laurent's rule is the right rule, and the answer is there at four
    harmonics and does not move afterwards. Measured residual against the limit
    is 3 parts in a hundred thousand, so the tolerance below is loose by a factor
    of twenty and still fifteen hundred times tighter than the across-stripe
    error. That the solver, the reference and the limit all agree here is what
    narrows the failure below to one thing.
    """
    reference, _ = reflect(ARITHMETIC, "te", 1)
    measured, _ = reflect(stripes(), "te", m_max)
    assert measured == pytest.approx(reference, rel=5e-4)


def test_the_along_stripe_answer_has_stopped_moving():
    """Convergence in the truncation, on the polarisation that has it.

    Doubling the retained orders moves this by one part in a hundred million.
    That is what a converged modal series looks like, and it is the yardstick
    the across-stripe case is held to.
    """
    coarse, _ = reflect(stripes(), "te", 16)
    fine, _ = reflect(stripes(), "te", 32)
    assert abs(fine - coarse) / fine < 1e-3


@pytest.mark.parametrize("m_max", [8, 16])
@pytest.mark.xfail(
    strict=True,
    reason="docs/BUGS.md finding 5: rcwa.py:188-206 applies Laurent's rule where Li's "
    "inverse rule is required for the across-stripe field, so the answer converges to "
    "the right limit as 1/M instead of reaching it",
)
def test_the_field_across_the_stripes_finds_the_harmonic_mean(m_max):
    """The factorisation that needs the inverse rule.

    Measured on the shipped code: 18.9 percent high at eight harmonics and 9.7
    percent at sixteen. Under the inverse rule the same two solves land at 0.385
    and 0.391 percent, which is the boundary layer term the module docstring
    accounts for and nothing else.
    """
    reference, _ = reflect(HARMONIC, "tm", 1)
    measured, _ = reflect(stripes(), "tm", m_max)
    assert measured == pytest.approx(reference, rel=0.01)


@pytest.mark.xfail(
    strict=True,
    reason="docs/BUGS.md finding 5: under Laurent's rule the across-stripe series "
    "converges as 1/M, so the reported answer is still moving in its third digit at "
    "the production truncation",
)
def test_the_across_stripe_answer_has_stopped_moving():
    """The sharpest form of finding 5, and it needs no reference value at all.

    A truncated series that is still moving is not an answer. Doubling the
    retained orders from sixteen to thirty two moves this by 4.4 percent of
    itself today. Under the inverse rule it moves by 3 parts in a million, so
    the two regimes are fifteen thousand apart and no tolerance in between is a
    judgement call.

    The successive increments are the tell. They are 7.9e-3, 3.9e-3 and 2.0e-3,
    halving as the truncation doubles, which is the 1/M tail of the wrong rule
    rather than the exponential fall of the right one.
    """
    coarse, _ = reflect(stripes(), "tm", 16)
    fine, _ = reflect(stripes(), "tm", 32)
    assert abs(fine - coarse) / fine < 1e-3


@pytest.mark.parametrize("polarisation", ["te", "tm"])
def test_energy_is_conserved_whether_or_not_the_answer_is_right(polarisation):
    """The reason the existing energy test could never have caught this.

    A lossless structure conserves energy under either factorisation, because
    the scattering matrix stays unitary whatever permittivity matrix it was
    built from. The across-stripe reflectance is 9.7 percent wrong at this
    truncation while the sum below sits within 1e-9 of one. Keep this green: it
    is the record of what the cheap check is worth.
    """
    reflectance, transmittance = reflect(stripes(), polarisation, 16)
    assert reflectance + transmittance == pytest.approx(1.0, abs=1e-8)
    assert 0.0 < reflectance < 1.0
