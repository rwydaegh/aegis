"""The band law: base stations in a height band and a range band.

This is the law every number published by this study was written under, and it is
not the method any more. `docs/2026-08-03_161712_LAW_CHANGE.md` records the
replacement and the reason: the four numbers that set a band were arbitrary, and
sweeping the outer range cap over its defensible span moved the headline by
7.8 dB against a between city spread of 4.93 dB. The largest lever in the study
was a number nobody could cite.

It is kept as a control, not as a candidate. A control has to be reproducible to
the last bit, so nothing here is corrected, tightened or tidied into a different
number.

## The three profiles

Take sites of uniform areal density on the ground, each at a height drawn
independently of its position, and ask how many sit per steradian in the
direction ``el``. A site at slant range `r` seen at elevation `el` has height
``r sin(el)`` and horizontal range ``r cos(el)``, so the height band and the
range band each cap `r` from one side. The count in a solid angle element is then
the radial integral of ``r^2 dr`` between those caps, which is
``(far^3 - near^3)/3``. That is :class:`BandLaw`.

Weight every site by its own free space spreading ``1/r^2`` and the integrand
becomes ``dr``, so the count turns into the plain depth ``far - near``. That is
:class:`BandPathlossLaw`.

:class:`FixedHeightLaw` is the uncorrected predecessor, derived for sites at one
single height above the head. Its only free parameter is the elevation window,
and a height band written next to it plays no part in the number. Giving it the
window of a height band it does not describe is exactly the defect
`MONOSTATIC_SBR.md` section 2.7 records. It is kept because every number
published before 2026-08-02 was computed under it.

## The law that was removed

``uniform_sites_pathloss``, ``1/(sin cos^2)``, is gone. It was declared as a law
and no model instance ever used it, so nothing was ever published through it, and
the docstring claiming it was kept for reproducibility was reproducing nothing.
`CODE_AUDIT.md` section 6.3 also shows the expression is wrong on its own terms:
it spreads in the horizontal range rather than the slant range, which is a factor
of four too large at 60 degrees. An abandoned idea that is also incorrect is not
a control. Git keeps it.

The state it was in cannot recur here. A law tag and a law class are now the same
object, registered together by :func:`~.model.register_law`, so a tag with no
implementation behind it is not something you can write down.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, ClassVar

import numpy as np

from .model import ElevationLaw, register_law


@register_law
@dataclass(frozen=True, kw_only=True)
class FixedHeightLaw(ElevationLaw):
    """Sites at one fixed height above the head, over a written elevation window.

    ``1/sin^3(el)``. Uncorrected, kept so numbers published before 2026-08-02 can
    be reproduced. The window is a free parameter here, which is the whole
    difference from :class:`BandLaw`: this law cannot derive a window because it
    has no bands to derive one from.
    """

    law: ClassVar[str] = "uniform_sites"
    family: ClassVar[str] = "band"

    def profile(self, elevation: np.ndarray) -> np.ndarray:
        sine = np.sin(elevation)
        return 1.0 / sine**3


@register_law
@dataclass(frozen=True, kw_only=True)
class BandLaw(ElevationLaw):
    """Sites of uniform areal density inside a height band and a range band.

    The elevation window is not a free parameter and that is the point of the
    class. It is ``[atan(h_min/d_max), atan(h_max/d_min)]``, the two directions in
    which the two bands only just still intersect, and it is derived from the
    bands rather than written down beside them.

    Two interior knots, where a range cap takes over from a height cap, so the
    profile is piecewise smooth rather than smooth.
    """

    law: ClassVar[str] = "uniform_sites_band"
    family: ClassVar[str] = "band"

    height_band_m: tuple[float, float] | None = None
    range_band_m: tuple[float, float] | None = None

    def __post_init__(self) -> None:
        if self.height_band_m is None or self.range_band_m is None:
            raise ValueError(f"{self.law!r} needs both a height band and a range band")
        low_h, high_h = self.height_band_m
        low_d, high_d = self.range_band_m
        if not (0.0 < low_h <= high_h) or not (0.0 < low_d <= high_d):
            raise ValueError(f"{self.name!r} has a degenerate height or range band")
        # Setting these rather than taking them is the point. A hand written
        # window and a band that does not imply it is exactly the defect
        # section 2.7 records.
        object.__setattr__(self, "elevation_min_deg", math.degrees(math.atan2(low_h, high_d)))
        object.__setattr__(self, "elevation_max_deg", math.degrees(math.atan2(high_h, low_d)))

    def slant_range_bounds(self, elevation: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Nearest and furthest site this direction can hold, given both bands."""
        sine = np.sin(elevation)
        cosine = np.cos(elevation)
        low_h, high_h = self.height_band_m  # type: ignore[misc]
        low_d, high_d = self.range_band_m  # type: ignore[misc]
        near = np.maximum(low_h / sine, low_d / cosine)
        far = np.minimum(high_h / sine, high_d / cosine)
        return near, far

    def profile(self, elevation: np.ndarray) -> np.ndarray:
        near, far = self.slant_range_bounds(elevation)
        # The clamp is not decoration and it is not dead. Inside the window
        # ``far >= near`` holds exactly, since the window is defined by where the
        # two caps cross. It does not hold in floating point at the two
        # endpoints, because the window is stored in degrees and converted back
        # with ``radians``, so the caps that meet exactly there no longer do.
        # Measured on street_small_cell, both endpoints come out at -6.2e-10.
        # Without the clamp the density is negative at its own support edge.
        return np.maximum(far**3 - near**3, 0.0) / 3.0

    def knots(self) -> tuple[float, ...]:
        low_h, high_h = self.height_band_m  # type: ignore[misc]
        low_d, high_d = self.range_band_m  # type: ignore[misc]
        return (math.atan2(high_h, high_d), math.atan2(low_h, low_d))

    def parameters(self) -> dict[str, Any]:
        return {
            "height_band_m": list(self.height_band_m),  # type: ignore[arg-type]
            "range_band_m": list(self.range_band_m),  # type: ignore[arg-type]
        }


@register_law
@dataclass(frozen=True, kw_only=True)
class BandPathlossLaw(BandLaw):
    """The same population with every site weighted by its own ``1/r^2`` spreading.

    `r` is the slant range, so the radial integrand loses its ``r^2`` and the
    density on dOmega is the plain slant range depth of the band rather than its
    cube. Equal EIRP per site, no power control.
    """

    law: ClassVar[str] = "uniform_sites_band_pathloss"
    family: ClassVar[str] = "band"

    def profile(self, elevation: np.ndarray) -> np.ndarray:
        near, far = self.slant_range_bounds(elevation)
        return np.maximum(far - near, 0.0)
