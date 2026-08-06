"""Every illumination law is a probability density on the sphere.

That single sentence is the contract the whole package is built on. `chi` equals
one in free space only because ``density`` integrates to one over 4 pi, and
every susceptibility the study reports is a pure number only because of that.

The models are discovered by walking the module rather than listed here, so a
law added tomorrow inherits the check without anyone remembering to extend the
list. The integration is adaptive quadrature over elevation with the branch
knots handed in as break points, which shares no code with the trapezoid
``IlluminationModel.normalisation`` runs, so this is a second opinion and not a
restatement.
"""

from __future__ import annotations

import math

import numpy as np
import pytest
from scipy.integrate import quad

from semantic_twin import illumination as D
from semantic_twin.illumination import IlluminationModel


def discover_models() -> dict[str, IlluminationModel]:
    """Every model the package ships, plus one per law that ships none.

    Read off :data:`semantic_twin.illumination.VARIANTS` and the law registry
    rather than by scanning a module namespace. A law is a registered class now,
    so "which laws exist" is a question with an answer, and a law that no shipped
    model uses still gets integrated here rather than never being integrated at
    all. ``tests/test_illumination.py`` carries the same guarantee from the other
    side, by refusing to let a registered law have no fixture.
    """
    found: dict[str, IlluminationModel] = dict(D.VARIANTS)
    covered = {model.law for model in found.values()}
    for law, cls in D.LAW_REGISTRY.items():
        if law in covered:
            continue
        name = f"orphan_{law}"
        note = "built by the test suite, because the package ships no model for this law"
        if issubclass(cls, D.BandLaw):
            found[name] = cls(
                name=name,
                description=note,
                height_band_m=D.ROOFTOP_HEIGHT_BAND_M,
                range_band_m=D.ROOFTOP_RANGE_BAND_M,
            )
        else:
            found[name] = cls(name=name, description=note, elevation_min_deg=3.0, elevation_max_deg=60.0)
    return found


MODELS = discover_models()
NAMES = sorted(MODELS)


def sphere_integral(model: IlluminationModel) -> float:
    """``integral density dOmega`` over 4 pi, by adaptive quadrature.

    Azimuthally symmetric, so the azimuth integral is the factor 2 pi and what
    is left is one dimensional in elevation with the ``cos`` of the measure.
    """

    def integrand(elevation: float) -> float:
        direction = np.array([[math.cos(elevation), 0.0, math.sin(elevation)]])
        return float(model.density(direction)[0] * math.cos(elevation))

    low = math.radians(model.elevation_min_deg)
    high = math.radians(model.elevation_max_deg)
    breaks = sorted(k for k in model.knots() if low < k < high)
    total, _ = quad(integrand, low, high, points=breaks or None, limit=400, epsabs=1e-12, epsrel=1e-12)
    return 2.0 * math.pi * total


def test_the_discovery_actually_found_the_laws():
    """A walk that finds nothing turns every test below into a pass."""
    assert len(MODELS) >= 7
    assert set(D.VARIANTS) <= set(MODELS)
    assert set(D.MODELS) <= set(MODELS)
    assert {m.law for m in MODELS.values()} == set(D.LAWS)


@pytest.mark.parametrize("name", NAMES)
def test_the_density_integrates_to_one_over_the_sphere(name):
    """The normalisation contract, checked against a different quadrature.

    A law whose measure is not one silently rescales every susceptibility
    computed under it, and because the study only ever reports ratios between
    sites computed under the same law, nothing downstream would notice.
    """
    assert sphere_integral(MODELS[name]) == pytest.approx(1.0, rel=2e-6)


@pytest.mark.parametrize("name", NAMES)
def test_the_density_is_never_negative(name):
    """A density that dips below zero is not a density.

    Sampled on a Fibonacci grid, which lands cells inside the support, on both
    edges of it and well outside, so the clipping in ``weight`` is exercised
    rather than avoided.
    """
    model = MODELS[name]
    grid = D.fibonacci_sphere(4096)
    value = model.density(grid)
    assert np.all(np.isfinite(value))
    assert np.all(value >= 0.0)


@pytest.mark.parametrize("name", NAMES)
def test_the_density_vanishes_outside_its_own_support(name):
    """Nothing may arrive from an elevation the model says holds no sites.

    Skipped for the isotropic law, whose support is the whole sphere and which
    therefore has no outside to test.
    """
    model = MODELS[name]
    if model.elevation_min_deg <= -90.0 and model.elevation_max_deg >= 90.0:
        pytest.skip("isotropic support is the whole sphere")
    outside = []
    if model.elevation_min_deg > -90.0:
        outside.append(model.elevation_min_deg - 1e-6)
        outside.append(0.5 * (model.elevation_min_deg - 90.0))
    if model.elevation_max_deg < 90.0:
        outside.append(model.elevation_max_deg + 1e-6)
        outside.append(0.5 * (model.elevation_max_deg + 90.0))
    elevation = np.radians(np.array(outside))
    direction = np.column_stack([np.cos(elevation), np.zeros_like(elevation), np.sin(elevation)])
    assert np.all(model.density(direction) == 0.0)


@pytest.mark.parametrize("name", NAMES)
def test_the_elevation_bands_partition_the_measure(name):
    """Bands that cover the support must sum to one, and match band by band.

    This is the reduction every figure in the study reads, so it gets checked
    against the same adaptive quadrature rather than against itself. Twenty
    bands, uneven by construction because the support is uneven, so a band that
    quietly picked up its neighbour's mass would move the total.
    """
    model = MODELS[name]
    edges = np.linspace(model.elevation_min_deg, model.elevation_max_deg, 21)
    measure = D.elevation_band_measure(model, edges)
    assert measure.sum() == pytest.approx(1.0, rel=1e-4)

    reference = []
    for i in range(edges.size - 1):
        # A band law derives its own window from its bands, so narrowing one is
        # the law's own move rather than a write through a frozen dataclass.
        piece = model.over(float(edges[i]), float(edges[i + 1]), name=f"{model.name}_band{i}")
        raw, _ = quad(
            lambda el, p=piece: float(p.weight(np.array([[math.cos(el), 0.0, math.sin(el)]]))[0] * math.cos(el)),
            math.radians(edges[i]),
            math.radians(edges[i + 1]),
            points=[k for k in model.knots() if math.radians(edges[i]) < k < math.radians(edges[i + 1])] or None,
            limit=400,
            epsabs=1e-14,
            epsrel=1e-12,
        )
        reference.append(2.0 * math.pi * raw / model.normalisation())
    assert measure == pytest.approx(np.array(reference), rel=2e-3, abs=1e-9)


def test_the_measure_below_a_cut_agrees_with_the_quadrature():
    """The crop radius argument turns on this number, so it gets its own check."""
    for name in NAMES:
        model = MODELS[name]
        cut = float(np.clip(20.0, model.elevation_min_deg, model.elevation_max_deg))
        piece = model.over(model.elevation_min_deg, cut, name=f"{model.name}_below")
        raw, _ = quad(
            lambda el, p=piece: float(p.weight(np.array([[math.cos(el), 0.0, math.sin(el)]]))[0] * math.cos(el)),
            math.radians(model.elevation_min_deg),
            math.radians(cut),
            points=[k for k in model.knots() if math.radians(model.elevation_min_deg) < k < math.radians(cut)] or None,
            limit=400,
            epsabs=1e-14,
            epsrel=1e-12,
        )
        expected = 2.0 * math.pi * raw / model.normalisation()
        assert D.measure_below(model, 20.0) == pytest.approx(expected, rel=3e-3, abs=1e-9)
