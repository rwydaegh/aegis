"""How much of an angular law's measure sits in a range of elevations.

Two reductions, both of them read by figures and by the crop radius argument, so
they are library code with tests on them rather than numbers computed once inside
a plotting script.

Both work on any :class:`~.model.AngularIllumination`. They assume the law is
uniform in azimuth, which every law in :mod:`~.bands` is, and they say so by
evaluating along a single azimuth.
"""

from __future__ import annotations

import numpy as np

from .model import AngularIllumination


def elevation_band_measure(
    model: AngularIllumination,
    edges_deg: np.ndarray,
    *,
    samples: int = 16_384,
    normalisation: float | None = None,
) -> np.ndarray:
    """Fraction of the illumination measure inside each elevation band.

    Integrated, never sampled at the midpoint, and the failure that forces this
    is one sided. ``1/sin^3`` is convex, so a midpoint underestimates the
    integral, and on equal count bins the top band is the widest, which is
    exactly where the underestimate is largest. Read at face value that
    quadrature error looks like a factor of six error in the physics rather than
    in the arithmetic.

    Bands that together cover the whole support sum to 1, since ``density``
    integrates to 1 over 4 pi and every law here is uniform in azimuth.
    """
    edges = np.asarray(edges_deg, dtype=np.float64)
    total = model.normalisation() if normalisation is None else normalisation
    knots = np.array(model.knots(), dtype=np.float64)
    measure = np.zeros(edges.size - 1)
    for i in range(measure.size):
        elevation = np.radians(np.linspace(edges[i], edges[i + 1], samples))
        inside = knots[(knots > elevation[0]) & (knots < elevation[-1])]
        if inside.size:
            elevation = np.sort(np.concatenate([elevation, inside]))
        directions = np.column_stack([np.cos(elevation), np.zeros_like(elevation), np.sin(elevation)])
        measure[i] = 2.0 * np.pi * np.trapezoid(model.density(directions, total) * np.cos(elevation), elevation)
    return measure


def measure_below(model: AngularIllumination, elevation_deg: float, *, samples: int = 16_384) -> float:
    """Fraction of the illumination measure below ``elevation_deg``.

    This is the number the crop radius argument of section 9.4 turns on, so it is
    library code with a test on it rather than a figure computed once.
    """
    cut = float(np.clip(elevation_deg, model.elevation_min_deg, model.elevation_max_deg))
    edges = np.array([model.elevation_min_deg, cut, model.elevation_max_deg])
    return float(elevation_band_measure(model, edges, samples=samples)[0])
