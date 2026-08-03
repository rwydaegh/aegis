"""Direction grids and the canonical illumination weights.

The tracer needs two things from this module. A near equal solid angle grid on
the sphere, used as the local arrival axis `u_loc` and as the binning axis for
exit directions, and the angular incident power density `Q_S(u_ext)` of the
external network, normalised as a probability density on the sphere so that
the integral over 4 pi is one.

Normalising `Q` to one is what makes every susceptibility in this package a
pure number that equals 1 in free space, and it keeps the absolute scale in a
single explicit factor `S0` that the caller owns.

Five elevation laws live here. Two of them are the uncorrected pair that every
number published before 2026-08-02 was computed under, kept so those numbers
can be reproduced, and three are the corrected replacements. The correction and
its derivation are MONOSTATIC_SBR.md section 2.7.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

GOLDEN_ANGLE = np.pi * (3.0 - np.sqrt(5.0))

#: Elevation laws this module can evaluate.
#:
#: ``uniform_sites`` and ``uniform_sites_pathloss`` are the uncorrected pair.
#: Both are derived for sites at a single fixed height above the head, so their
#: only free parameter is the elevation support, and the height band a caller
#: writes next to them plays no part in the number. ``uniform_sites_band`` and
#: ``uniform_sites_band_pathloss`` are their corrected replacements, which take
#: the height band and the range band as the model and derive the support from
#: them.
LAWS = (
    "isotropic",
    "uniform_sites",
    "uniform_sites_pathloss",
    "uniform_sites_band",
    "uniform_sites_band_pathloss",
)

#: The laws whose support and shape both follow from a height band and a range
#: band rather than from a pair of hand written elevation limits.
BAND_LAWS = ("uniform_sites_band", "uniform_sites_band_pathloss")


def fibonacci_sphere(count: int) -> np.ndarray:
    """Unit vectors spread over the sphere with near equal solid angle.

    Returns an ``(count, 3)`` array. Cell solid angle is ``4*pi/count`` to
    within a few percent, which is the accuracy the deposit weights assume.
    """
    if count < 1:
        raise ValueError("count must be positive")
    index = np.arange(count, dtype=np.float64)
    z = 1.0 - (2.0 * index + 1.0) / count
    radius = np.sqrt(np.maximum(0.0, 1.0 - z * z))
    theta = GOLDEN_ANGLE * index
    return np.stack([radius * np.cos(theta), radius * np.sin(theta), z], axis=1)


def _brute_nearest_cell(directions: np.ndarray, grid: np.ndarray, block: int) -> np.ndarray:
    """Dense ``argmax`` of every dot product. The definition, and the fallback."""
    out = np.empty(directions.shape[0], dtype=np.int64)
    for start in range(0, directions.shape[0], block):
        stop = min(start + block, directions.shape[0])
        out[start:stop] = np.argmax(directions[start:stop] @ grid.T, axis=1)
    return out


#: Half width of the elevation band searched by :func:`nearest_cell`, as a
#: multiple of ``sqrt(cells)``. The covering radius of a Fibonacci lattice goes
#: as ``1/sqrt(cells)`` in angle and the cell spacing in ``z`` goes as
#: ``1/cells``, so the number of cells that can hold the answer goes as
#: ``sqrt(cells)``. The constant is set from the measured miss rate rather than
#: from that argument: 1.5 leaves no misses at all from 2e6 directions on every
#: grid between 64 and 4096 cells. It is a speed knob and nothing else, because
#: a miss is caught and answered exactly.
_BAND_CONSTANT = 1.5


def nearest_cell(directions: np.ndarray, grid: np.ndarray, *, block: int = 65536) -> np.ndarray:
    """Index of the nearest grid direction for each row of ``directions``.

    The dense form of this is one ``(rays, cells)`` matrix of dot products, and
    at the sizes this study runs, 400k rays against 512 cells for every trace,
    it was a quarter of the trace and 1.6 GB of writes. It was also the one
    part of the estimator whose speed turned on how many BLAS threads a process
    happened to get: 0.35 s on eight, 2.05 s on one, which is the number that
    matters once standpoints run in a pool. Whether it also turned on the
    answer was checked rather than assumed, and it did not, over 2e6 directions
    at seven block sizes and two thread counts.

    The band search removes both. For a grid whose ``z`` column is sorted, the
    dot product of a query ``u`` with any cell at height ``z`` is at most
    ``cos(el_u - el_z)``, so once a candidate with dot product ``b`` is in
    hand, only cells within ``arccos(b)`` in elevation can beat it. That is a
    contiguous run of cells, a few tens wide rather than the whole grid.

    The band is searched first and the bound is then checked, not assumed. Any
    ray whose bound reaches outside the band it was given is answered by the
    dense form, so the result is the dense result for every input, including
    exact ties, where both forms return the lowest index that attains the
    maximum. Grids that are not sorted in ``z``, and grids too small for a band
    to save anything, take the dense path whole.
    """
    directions = np.asarray(directions, dtype=np.float64)
    grid = np.asarray(grid, dtype=np.float64)
    rays = directions.shape[0]
    cells = grid.shape[0]
    half = max(4, int(math.ceil(_BAND_CONSTANT * math.sqrt(cells))))
    width = 2 * half + 1
    height = grid[:, 2]
    if rays == 0 or cells < width + 2 or not np.all(height[1:] <= height[:-1]):
        return _brute_nearest_cell(directions, grid, block)

    out = np.empty(rays, dtype=np.int64)
    best = np.empty(rays)
    query = directions[:, 2]
    # A Fibonacci grid is evenly spaced in height by construction, so the cell
    # at a given height is one multiply rather than a binary search. Three
    # binary searches over 400k rays cost more than the dot products do. The
    # even spacing is measured, not assumed, and a grid that fails the check
    # gets ``searchsorted`` instead.
    step = (height[0] - height[-1]) / (cells - 1)
    even = step > 0.0 and bool(np.max(np.abs(height - (height[0] - step * np.arange(cells)))) < 0.25 * step)
    if even:
        scale = 1.0 / step
        centre = np.clip(np.rint((height[0] - query) * scale).astype(np.int64), 0, cells - 1)
    else:
        # ``ascending`` is the same heights the other way round, which is what
        # ``searchsorted`` needs. Cell ``j`` is entry ``cells - 1 - j``.
        ascending = np.ascontiguousarray(height[::-1])
        centre = cells - 1 - np.clip(np.searchsorted(ascending, query), 0, cells - 1)
    first = np.clip(centre - half, 0, cells - width)

    # One band per distinct starting cell, so every dot product below is a
    # contiguous ``(rays_in_band, width)`` block that stays in cache.
    order = np.argsort(first, kind="stable")
    starts = first[order]
    unique, opens = np.unique(starts, return_index=True)
    opens = np.append(opens, rays)
    for i in range(unique.size):
        rows = order[opens[i] : opens[i + 1]]
        start = int(unique[i])
        dots = directions[rows] @ grid[start : start + width].T
        local = np.argmax(dots, axis=1)
        out[rows] = start + local
        best[rows] = dots[np.arange(local.size), local]

    # Which cells could still beat what the band found. ``arccos`` of the best
    # dot product is the elevation reach, and the epsilons only ever widen it,
    # so a rounding error here costs a dense fallback and never an answer.
    reach = np.arccos(np.clip(best, -1.0, 1.0)) + 1.0e-12
    elevation = np.arcsin(np.clip(query, -1.0, 1.0))
    top = np.sin(np.clip(elevation + reach, -0.5 * np.pi, 0.5 * np.pi)) + 1.0e-12
    bottom = np.sin(np.clip(elevation - reach, -0.5 * np.pi, 0.5 * np.pi)) - 1.0e-12
    if even:
        # One cell of slack each way, which covers the quarter cell the even
        # spacing check allows the grid to wander by. Slack widens the range
        # that has to fall inside the band, so it can only cost a fallback.
        lowest = np.maximum(np.ceil((height[0] - top) * scale).astype(np.int64) - 1, 0)
        highest = np.minimum(np.floor((height[0] - bottom) * scale).astype(np.int64) + 1, cells - 1)
    else:
        lowest = cells - np.searchsorted(ascending, top, side="right")
        highest = cells - 1 - np.searchsorted(ascending, bottom, side="left")
    missed = (lowest < first) | (highest >= first + width)
    if np.any(missed):
        out[missed] = _brute_nearest_cell(directions[missed], grid, block)
    return out


def sample_sphere(count: int, rng: np.random.Generator) -> np.ndarray:
    """Uniform directions on the sphere."""
    z = rng.uniform(-1.0, 1.0, size=count)
    phi = rng.uniform(0.0, 2.0 * np.pi, size=count)
    radius = np.sqrt(np.maximum(0.0, 1.0 - z * z))
    return np.stack([radius * np.cos(phi), radius * np.sin(phi), z], axis=1)


@dataclass(frozen=True)
class IlluminationModel:
    """An external angular power density, as a density on the unit sphere.

    ``weight(u)`` returns an unnormalised `Q_S(u)` and ``density(u)`` divides
    the quadrature constant out, so the result is in sr^-1 and integrates to 1
    over 4 pi. The elevation law comes from MONOSTATIC_SBR.md section 2.7.

    For the two band laws the elevation support is not a free parameter. It is
    ``[atan(h_min/d_max), atan(h_max/d_min)]``, the two directions in which the
    height band and the range band only just still intersect, and it is derived
    in ``__post_init__`` rather than written down beside the bands.
    """

    name: str
    law: str
    description: str
    elevation_min_deg: float = -90.0
    elevation_max_deg: float = 90.0
    height_band_m: tuple[float, float] | None = None
    range_band_m: tuple[float, float] | None = None

    def __post_init__(self) -> None:
        if self.law not in LAWS:
            raise ValueError(f"unknown elevation law {self.law!r}")
        if self.law not in BAND_LAWS:
            return
        if self.height_band_m is None or self.range_band_m is None:
            raise ValueError(f"{self.law!r} needs both a height band and a range band")
        low_h, high_h = self.height_band_m
        low_d, high_d = self.range_band_m
        if not (0.0 < low_h <= high_h) or not (0.0 < low_d <= high_d):
            raise ValueError(f"{self.name!r} has a degenerate height or range band")
        # Setting these rather than taking them is the point. A hand written
        # support and a band that does not imply it is exactly the defect
        # section 2.7 records.
        object.__setattr__(self, "elevation_min_deg", math.degrees(math.atan2(low_h, high_d)))
        object.__setattr__(self, "elevation_max_deg", math.degrees(math.atan2(high_h, low_d)))

    def _raw(self, elevation: np.ndarray) -> np.ndarray:
        """The unnormalised elevation law, on `dOmega`, inside the support.

        ``elevation`` must already lie inside ``[elevation_min_deg,
        elevation_max_deg]``. Both callers clip before calling, which is what
        keeps ``1/sin`` and the slant range bounds below finite everywhere.
        """
        if self.law == "isotropic":
            return np.ones_like(elevation)
        sine = np.sin(elevation)
        cosine = np.cos(elevation)
        if self.law == "uniform_sites":
            return 1.0 / sine**3
        if self.law == "uniform_sites_pathloss":
            return 1.0 / (sine * cosine**2)
        low_h, high_h = self.height_band_m  # type: ignore[misc]
        low_d, high_d = self.range_band_m  # type: ignore[misc]
        # Slant ranges of the nearest and furthest site that this direction can
        # hold, given both bands. A site at slant range `r` seen at elevation
        # `el` has height `r*sin(el)` and horizontal range `r*cos(el)`, so each
        # band caps `r` from one side.
        near = np.maximum(low_h / sine, low_d / cosine)
        far = np.minimum(high_h / sine, high_d / cosine)
        if self.law == "uniform_sites_band_pathloss":
            return np.maximum(far - near, 0.0)
        return np.maximum(far**3 - near**3, 0.0) / 3.0

    def weight(self, directions: np.ndarray) -> np.ndarray:
        """Unnormalised density on dOmega, before the constant is divided out."""
        elevation = np.arcsin(np.clip(directions[:, 2], -1.0, 1.0))
        low = np.radians(self.elevation_min_deg)
        high = np.radians(self.elevation_max_deg)
        inside = (elevation >= low) & (elevation <= high)
        return np.where(inside, self._raw(np.clip(elevation, low, high)), 0.0)

    def normalisation(self, quadrature: int = 200_001) -> float:
        """``integral of the unnormalised weight over 4 pi``, by quadrature in elevation.

        Doing this in closed form in elevation rather than on the direction grid
        matters: the ``1/sin^3`` law puts most of its mass in the first few
        degrees above the horizon, which a few hundred cell direction grid
        cannot resolve.

        The band laws are only piecewise smooth. Their two interior knots, where
        a range cap takes over from a height cap, are inserted into the
        abscissae so the trapezoid never straddles a kink.

        The value depends on the model and on the quadrature and on nothing
        else, so it is computed once per pair and kept. A 200001 point
        trapezoid is a fifth of a second across the three models, which was
        being spent again at every observation point of every sweep. The memo
        lives outside the dataclass fields, so it changes neither equality nor
        the hash, and the cached value is the value the quadrature returns.
        """
        cached = self.__dict__.get("_normalisation_memo")
        if cached is not None and cached[0] == quadrature:
            return cached[1]
        value = self._normalisation(quadrature)
        object.__setattr__(self, "_normalisation_memo", (quadrature, value))
        return value

    def _normalisation(self, quadrature: int) -> float:
        low = np.radians(self.elevation_min_deg)
        high = np.radians(self.elevation_max_deg)
        elevation = np.linspace(low, high, quadrature)
        for knot in self.knots():
            if low < knot < high:
                elevation = np.insert(elevation, int(np.searchsorted(elevation, knot)), knot)
        return float(2.0 * np.pi * np.trapezoid(self._raw(elevation) * np.cos(elevation), elevation))

    def knots(self) -> tuple[float, ...]:
        """Interior elevations where the band laws change branch, in radians."""
        if self.law not in BAND_LAWS:
            return ()
        low_h, high_h = self.height_band_m  # type: ignore[misc]
        low_d, high_d = self.range_band_m  # type: ignore[misc]
        return (math.atan2(high_h, high_d), math.atan2(low_h, low_d))

    def density(self, directions: np.ndarray, normalisation: float | None = None) -> np.ndarray:
        """`Q_S(u)` in sr^-1, integrating to 1 over the sphere."""
        total = self.normalisation() if normalisation is None else normalisation
        if total <= 0.0:
            raise ValueError(f"illumination model {self.name!r} has no support")
        return self.weight(directions) / total


def elevation_band_measure(
    model: IlluminationModel,
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
    quadrature error looks like a factor of six error in the physics rather
    than in the arithmetic.

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


def measure_below(model: IlluminationModel, elevation_deg: float, *, samples: int = 16_384) -> float:
    """Fraction of the illumination measure below ``elevation_deg``.

    This is the number the crop radius argument of section 9.4 turns on, so it
    is library code with a test on it rather than a figure computed once.
    """
    cut = float(np.clip(elevation_deg, model.elevation_min_deg, model.elevation_max_deg))
    edges = np.array([model.elevation_min_deg, cut, model.elevation_max_deg])
    return float(elevation_band_measure(model, edges, samples=samples)[0])


#: Height above the pedestrian head, and horizontal range, of each site
#: population. These are the model for the band laws, not a comment beside it.
ROOFTOP_HEIGHT_BAND_M = (13.5, 43.5)
ROOFTOP_RANGE_BAND_M = (25.0, 250.0)
STREET_HEIGHT_BAND_M = (2.5, 6.5)
STREET_RANGE_BAND_M = (10.0, 150.0)

ISOTROPIC = IlluminationModel(
    name="isotropic",
    law="isotropic",
    description="Uniform over 4 pi. Equals 1 in free space by construction.",
)

ROOFTOP = IlluminationModel(
    name="rooftop",
    law="uniform_sites_band",
    height_band_m=ROOFTOP_HEIGHT_BAND_M,
    range_band_m=ROOFTOP_RANGE_BAND_M,
    description=(
        "Macro sites of uniform areal density, height above head 13.5 to 43.5 m drawn "
        "independently of position, horizontal range 25 to 250 m. Density on dOmega goes "
        "as the count of sites per steradian, which is the cubed slant range depth of the "
        "height band along that direction. MONOSTATIC_SBR.md section 2.7, corrected "
        "2026-08-02."
    ),
)

STREET_SMALL_CELL = IlluminationModel(
    name="street_small_cell",
    law="uniform_sites_band",
    height_band_m=STREET_HEIGHT_BAND_M,
    range_band_m=STREET_RANGE_BAND_M,
    description=(
        "Street furniture small cells, height above head 2.5 to 6.5 m drawn independently "
        "of position, horizontal range 10 to 150 m. MONOSTATIC_SBR.md section 2.7, "
        "corrected 2026-08-02."
    ),
)

ROOFTOP_PATHLOSS = IlluminationModel(
    name="rooftop_pathloss",
    law="uniform_sites_band_pathloss",
    height_band_m=ROOFTOP_HEIGHT_BAND_M,
    range_band_m=ROOFTOP_RANGE_BAND_M,
    description=(
        "The rooftop population with every site weighted by its own free space spreading "
        "1/r^2, r the slant range. Density on dOmega is then the plain slant range depth "
        "of the height band, not its cube. Equal EIRP per site, no power control."
    ),
)

STREET_SMALL_CELL_PATHLOSS = IlluminationModel(
    name="street_small_cell_pathloss",
    law="uniform_sites_band_pathloss",
    height_band_m=STREET_HEIGHT_BAND_M,
    range_band_m=STREET_RANGE_BAND_M,
    description=(
        "The street small cell population with every site weighted by its own free space "
        "spreading 1/r^2, r the slant range."
    ),
)

#: What shipped before 2026-08-02. Every published susceptibility, every crop
#: convergence table and every cross city figure dated before then was computed
#: with these, so they are kept rather than deleted. They are the fixed height
#: law read over the support of a height band, which is the defect section 2.7
#: records.
ROOFTOP_FIXED_HEIGHT = IlluminationModel(
    name="rooftop_fixed_height",
    law="uniform_sites",
    elevation_min_deg=3.1,
    elevation_max_deg=60.1,
    description=(
        "Uncorrected rooftop model, kept so numbers published before 2026-08-02 can be "
        "reproduced. Derived for sites at one fixed height, then given the support of a "
        "height band it does not describe. MONOSTATIC_SBR.md section 2.7."
    ),
)

STREET_SMALL_CELL_FIXED_HEIGHT = IlluminationModel(
    name="street_small_cell_fixed_height",
    law="uniform_sites",
    elevation_min_deg=0.95,
    elevation_max_deg=33.0,
    description=(
        "Uncorrected street small cell model, kept so numbers published before 2026-08-02 "
        "can be reproduced. MONOSTATIC_SBR.md section 2.7."
    ),
)

#: The three the study reports. Adding to this changes the schema of every
#: streamed row, so the alternatives live in ``VARIANTS`` instead.
MODELS: dict[str, IlluminationModel] = {model.name: model for model in (ISOTROPIC, ROOFTOP, STREET_SMALL_CELL)}

#: Every model this module defines, including the path loss weighted variants
#: and the two uncorrected ones, for ablations and for reproducing old numbers.
VARIANTS: dict[str, IlluminationModel] = {
    model.name: model
    for model in (
        ISOTROPIC,
        ROOFTOP,
        STREET_SMALL_CELL,
        ROOFTOP_PATHLOSS,
        STREET_SMALL_CELL_PATHLOSS,
        ROOFTOP_FIXED_HEIGHT,
        STREET_SMALL_CELL_FIXED_HEIGHT,
    )
}
