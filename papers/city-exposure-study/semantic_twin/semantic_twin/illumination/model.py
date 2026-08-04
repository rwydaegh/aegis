"""What an illumination law is, and the two shapes one can take.

This study has had two illumination laws at once for most of its life and the
choice between them was a string compared in a switch. That hid the one fact a
reader needs: they are alternatives, they answer the same physical question, and
they answer it in shapes that are not interchangeable.

The band law says base stations sit in a height band and a range band. Marginalise
that population over range and you get an angular density `Q(u)`, a function of
direction alone, and an escaping ray is credited by reading it at the exit
direction.

The facade tip law says base stations sit on the rooflines the geometry actually
has. Those sources occupy no solid angle, so `Q(u)` is zero almost everywhere and
reading a density at an exit direction returns nothing. Worse, a density that
depends on direction alone has already assumed the sources are far enough away
that position does not matter, and the skyline sits 18 to 70 m from the head
while a last bounce can be tens of metres away. So the facade tip law is reached
by connecting to a site from the vertex where the question is asked.

## What the two genuinely share

Read them rather than their names and the shared part is small and precise.

Both are a **named base station population that can write down what it is**. That
is :class:`IlluminationModel`, and it is the whole root protocol: ``name``,
``law``, ``family``, and :meth:`describe`. It exists because
``docs/2026-08-03_161712_LAW_CHANGE.md`` is 270 lines of which-numbers-survive
tables, written by hand because no result on disk said which law produced it.

Both also normalise so the study's `chi` is a pure number, but they normalise
different things. The band law divides by the integral of its density over 4 pi.
The facade tip law divides by the site count, so the answer does not move when
the set is sampled more finely. Same intent, different arithmetic, and merging
them would be a fiction.

What they do **not** share is an evaluation signature, and pretending otherwise
is the mistake this module exists to avoid. So the root protocol splits in two:

- :class:`AngularIllumination` adds the direction density. The escape estimator
  consumes this and nothing else.
- :class:`PlacedIllumination` adds explicit site positions. The next event
  estimator consumes this and nothing else.

:func:`credited_by` reads which of the two a model satisfies and returns the
estimators that can run against it, so "can this law feed that estimator" is a
call rather than a convention.

## Adding a law

Write one class. Subclass :class:`ElevationLaw` for a direction density,
implement :meth:`ElevationLaw.profile`, set ``law`` and ``family``, and decorate
it with :func:`register_law`. Nothing else in the package changes and the
contract tests in ``tests/test_illumination.py`` pick it up from the registry.
"""

from __future__ import annotations

import dataclasses
import math
from dataclasses import dataclass
from typing import Any, ClassVar, Protocol, runtime_checkable

import numpy as np

#: The default elevation quadrature. Every published normalisation constant was
#: computed at this count, so it is a number with numbers hanging off it rather
#: than a tuning knob.
QUADRATURE = 200_001


@runtime_checkable
class IlluminationModel(Protocol):
    """A named base station population that can say what it is.

    The smallest thing the band law and the facade tip law both genuinely
    satisfy. Everything past this differs between them, which is why the
    evaluation methods live on the two protocols below and not here.

    ``law`` is the fine grained tag written into every manifest, for example
    ``uniform_sites_band`` or ``facade_tip``. ``family`` is which of
    :data:`semantic_twin.runconfig.LAWS` it belongs to, so a reader grouping
    results does not have to know the fine grained vocabulary. Isotropic has an
    empty family on purpose: it places no sources, which is exactly why it is the
    one column of ``LAW_CHANGE.md`` that survives every law change.
    """

    name: str
    law: str
    family: str

    def describe(self) -> dict[str, Any]:
        """Everything that decides what this model does, as plain JSON values.

        Written beside a result so the result can name the law that made it.
        """


@runtime_checkable
class AngularIllumination(IlluminationModel, Protocol):
    """A population marginalised into a density on direction alone.

    The escape estimator weights a ray by :meth:`density` at the direction it
    leaves the crop, so this is the whole interface it needs. `chi` equals one in
    free space only because the density integrates to one over 4 pi, and every
    susceptibility the study reports is a pure number only because of that.

    The elevation window is part of the interface because every reduction over
    one of these laws needs it: a band measure has to know where to put its
    edges, and a Monte Carlo check has to know which directions are supposed to
    return zero. Azimuthal structure, if a law has any, lives inside the window.
    """

    elevation_min_deg: float
    elevation_max_deg: float

    def weight(self, directions: np.ndarray) -> np.ndarray:
        """Unnormalised `Q_S(u)` on dOmega, zero outside the support."""

    def knots(self) -> tuple[float, ...]:
        """Interior elevations where the law changes branch, in radians.

        Quadrature over a piecewise smooth law has to put an abscissa on each
        kink. A law with no kinks returns an empty tuple.
        """

    def normalisation(self, quadrature: int = QUADRATURE) -> float:
        """``integral of weight over 4 pi``. The constant :meth:`density` divides by."""

    def density(self, directions: np.ndarray, normalisation: float | None = None) -> np.ndarray:
        """`Q_S(u)` in sr^-1, integrating to 1 over the sphere."""


@runtime_checkable
class PlacedIllumination(IlluminationModel, Protocol):
    """A population kept as explicit points, reached by connecting to one.

    The next event estimator draws a site, casts one ray at it from the vertex
    asking the question, and takes the contribution if that ray is clear. So it
    needs positions and a count, and it never needs a density.
    """

    def sites(self) -> np.ndarray:
        """``(N, 3)`` source positions in scene coordinates."""

    def __len__(self) -> int:
        """How many sites. Every estimator here divides by it."""


#: Every law class, keyed by its ``law`` tag. Populated by :func:`register_law`.
#:
#: The registry is what makes a law tag on disk reversible. A manifest says
#: ``uniform_sites_band`` and this says which class that was.
LAW_REGISTRY: dict[str, type] = {}


def register_law(cls: type) -> type:
    """Record a law class under its own tag. Used as a decorator.

    Two classes claiming one tag is a mistake worth failing on, because the tag
    is what a manifest carries and a duplicate makes an old result ambiguous.
    """
    tag = getattr(cls, "law", "")
    if not tag:
        raise ValueError(f"{cls.__name__} has no law tag to register under")
    if tag in LAW_REGISTRY and LAW_REGISTRY[tag] is not cls:
        raise ValueError(f"law tag {tag!r} is already held by {LAW_REGISTRY[tag].__name__}")
    LAW_REGISTRY[tag] = cls
    return cls


def credited_by(model: IlluminationModel) -> tuple[str, ...]:
    """Which estimators can consume this model, named as ``runconfig.ESTIMATORS``.

    A law that satisfies neither protocol returns an empty tuple, and that is the
    honest answer rather than an error: it is a population nothing can yet score.
    """
    estimators = []
    if isinstance(model, AngularIllumination):
        estimators.append("escape")
    if isinstance(model, PlacedIllumination):
        estimators.append("next_event")
    return tuple(estimators)


@dataclass(frozen=True, kw_only=True)
class ElevationLaw:
    """Shared machinery for a density that is uniform in azimuth.

    Every angular law in this study is azimuthally symmetric, so the whole law is
    one function of elevation plus the window it is supported on. A subclass
    supplies :meth:`profile` and, if it is piecewise, :meth:`knots`. Normalisation,
    support clipping and the density itself are the same arithmetic for all of
    them and live here once.

    Normalising to one over 4 pi is what keeps the absolute scale in a single
    explicit factor `S0` that the caller owns.
    """

    name: str
    description: str = ""
    elevation_min_deg: float = -90.0
    elevation_max_deg: float = 90.0

    law: ClassVar[str] = ""
    family: ClassVar[str] = ""
    #: Present on every law so a caller can read them off any model without
    #: asking what kind it is. Only the band laws set them.
    height_band_m: ClassVar[tuple[float, float] | None] = None
    range_band_m: ClassVar[tuple[float, float] | None] = None

    def profile(self, elevation: np.ndarray) -> np.ndarray:
        """The unnormalised law on dOmega, evaluated inside the support.

        ``elevation`` is in radians and is already clipped to the support by
        every caller, which is what keeps ``1/sin`` and the slant range bounds
        finite everywhere.
        """
        raise NotImplementedError(f"{type(self).__name__} has no elevation profile")

    def knots(self) -> tuple[float, ...]:
        """Interior elevations where the law changes branch, in radians."""
        return ()

    def parameters(self) -> dict[str, Any]:
        """The law's own free parameters, for :meth:`describe`."""
        return {}

    # ------------------------------------------------------------- evaluation

    def weight(self, directions: np.ndarray) -> np.ndarray:
        """Unnormalised density on dOmega, before the constant is divided out."""
        elevation = np.arcsin(np.clip(directions[:, 2], -1.0, 1.0))
        low = np.radians(self.elevation_min_deg)
        high = np.radians(self.elevation_max_deg)
        inside = (elevation >= low) & (elevation <= high)
        return np.where(inside, self.profile(np.clip(elevation, low, high)), 0.0)

    def integrate(self, quadrature: int = QUADRATURE) -> float:
        """``integral of the unnormalised weight over 4 pi``, by quadrature in elevation.

        Doing this in closed form in elevation rather than on the direction grid
        matters: the ``1/sin^3`` law puts most of its mass in the first few
        degrees above the horizon, which a few hundred cell direction grid cannot
        resolve.

        Piecewise laws hand over their knots and each one is inserted into the
        abscissae, so no trapezoid ever straddles a kink.
        """
        low = np.radians(self.elevation_min_deg)
        high = np.radians(self.elevation_max_deg)
        elevation = np.linspace(low, high, quadrature)
        for knot in self.knots():
            if low < knot < high:
                elevation = np.insert(elevation, int(np.searchsorted(elevation, knot)), knot)
        return float(2.0 * np.pi * np.trapezoid(self.profile(elevation) * np.cos(elevation), elevation))

    def normalisation(self, quadrature: int = QUADRATURE) -> float:
        """:meth:`integrate`, computed once per model and quadrature and kept.

        The value depends on the model and on the quadrature and on nothing else.
        A 200001 point trapezoid is a fifth of a second across the three shipped
        models, which was being spent again at every observation point of every
        sweep. The memo lives outside the dataclass fields, so it changes neither
        equality nor the hash, and the cached value is the value the quadrature
        returns.
        """
        cached = self.__dict__.get("_normalisation_memo")
        if cached is not None and cached[0] == quadrature:
            return cached[1]
        value = self.integrate(quadrature)
        object.__setattr__(self, "_normalisation_memo", (quadrature, value))
        return value

    def density(self, directions: np.ndarray, normalisation: float | None = None) -> np.ndarray:
        """`Q_S(u)` in sr^-1, integrating to 1 over the sphere."""
        total = self.normalisation() if normalisation is None else normalisation
        if total <= 0.0:
            raise ValueError(f"illumination model {self.name!r} has no support")
        return self.weight(directions) / total

    # ------------------------------------------------------------- provenance

    def describe(self) -> dict[str, Any]:
        """What this model is, flat enough to sit in a manifest."""
        return {
            "name": self.name,
            "law": self.law,
            "family": self.family,
            "kind": "angular",
            "elevation_deg": [self.elevation_min_deg, self.elevation_max_deg],
            "description": self.description,
            **self.parameters(),
        }

    # ------------------------------------------------------------- restriction

    def over(self, elevation_min_deg: float, elevation_max_deg: float, *, name: str = "") -> ElevationLaw:
        """The same law read over a narrower elevation window.

        The profile and the knots are untouched, only the window moves. This is
        what an elevation probe is, and it is what a band by band reference
        integral needs, and both used to be done by writing through a frozen
        dataclass from outside it.

        The write is still a write, because a band law derives its own window
        from its bands and would otherwise put it straight back.
        """
        clone = dataclasses.replace(self, name=name or f"{self.name}_{elevation_min_deg:g}_{elevation_max_deg:g}")
        object.__setattr__(clone, "elevation_min_deg", float(elevation_min_deg))
        object.__setattr__(clone, "elevation_max_deg", float(elevation_max_deg))
        return clone


@register_law
@dataclass(frozen=True, kw_only=True)
class Isotropic(ElevationLaw):
    """Uniform over 4 pi. Equals 1 in free space by construction.

    It places no sources, so it has no law family and it is the one result column
    that survives every change of illumination law.
    """

    law: ClassVar[str] = "isotropic"
    family: ClassVar[str] = ""

    def profile(self, elevation: np.ndarray) -> np.ndarray:
        return np.ones_like(elevation)


def solid_angle_of_band(low_deg: float, high_deg: float) -> float:
    """Steradians between two elevations. Handy in a closed form, and exact."""
    return float(2.0 * math.pi * (math.sin(math.radians(high_deg)) - math.sin(math.radians(low_deg))))
