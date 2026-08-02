"""Direction grids and the canonical illumination weights.

The tracer needs two things from this module. A near equal solid angle grid on
the sphere, used as the local arrival axis `u_loc` and as the binning axis for
exit directions, and the angular incident power density `Q_S(u_ext)` of the
external network, normalised as a probability density on the sphere so that
the integral over 4 pi is one.

Normalising `Q` to one is what makes every susceptibility in this package a
pure number that equals 1 in free space, and it keeps the absolute scale in a
single explicit factor `S0` that the caller owns.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

GOLDEN_ANGLE = np.pi * (3.0 - np.sqrt(5.0))


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


def nearest_cell(directions: np.ndarray, grid: np.ndarray, *, block: int = 65536) -> np.ndarray:
    """Index of the nearest grid direction for each row of ``directions``."""
    out = np.empty(directions.shape[0], dtype=np.int64)
    for start in range(0, directions.shape[0], block):
        stop = min(start + block, directions.shape[0])
        out[start:stop] = np.argmax(directions[start:stop] @ grid.T, axis=1)
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

    ``weight(u)`` returns `Q_S(u)` in sr^-1, integrating to 1 over 4 pi. The
    elevation support and the elevation law come from MONOSTATIC_SBR.md
    section 2.7, which derives the law from a uniform areal site density rather
    than picking a flat elevation band.
    """

    name: str
    elevation_min_deg: float
    elevation_max_deg: float
    law: str
    description: str

    def weight(self, directions: np.ndarray) -> np.ndarray:
        """Unnormalised density on dOmega, before the constant is divided out."""
        elevation = np.arcsin(np.clip(directions[:, 2], -1.0, 1.0))
        low = np.radians(self.elevation_min_deg)
        high = np.radians(self.elevation_max_deg)
        inside = (elevation >= low) & (elevation <= high)
        sine = np.sin(np.clip(elevation, low, high))
        cosine = np.cos(np.clip(elevation, low, high))
        if self.law == "isotropic":
            raw = np.ones_like(elevation)
        elif self.law == "uniform_sites":
            raw = 1.0 / sine**3
        elif self.law == "uniform_sites_pathloss":
            raw = 1.0 / (sine * cosine**2)
        else:
            raise ValueError(f"unknown elevation law {self.law!r}")
        return np.where(inside, raw, 0.0)

    def normalisation(self, quadrature: int = 200_001) -> float:
        """``integral of the unnormalised weight over 4 pi``, by quadrature in elevation.

        Doing this in closed form in elevation rather than on the direction grid
        matters: the ``1/sin^3`` law puts most of its mass in the first few
        degrees above the horizon, which a few hundred cell direction grid
        cannot resolve.
        """
        low = np.radians(self.elevation_min_deg)
        high = np.radians(self.elevation_max_deg)
        elevation = np.linspace(low, high, quadrature)
        cosine = np.cos(elevation)
        sine = np.sin(elevation)
        if self.law == "isotropic":
            raw = np.ones_like(elevation)
        elif self.law == "uniform_sites":
            raw = 1.0 / sine**3
        elif self.law == "uniform_sites_pathloss":
            raw = 1.0 / (sine * cosine**2)
        else:
            raise ValueError(f"unknown elevation law {self.law!r}")
        return float(2.0 * np.pi * np.trapezoid(raw * cosine, elevation))

    def density(self, directions: np.ndarray, normalisation: float | None = None) -> np.ndarray:
        """`Q_S(u)` in sr^-1, integrating to 1 over the sphere."""
        total = self.normalisation() if normalisation is None else normalisation
        if total <= 0.0:
            raise ValueError(f"illumination model {self.name!r} has no support")
        return self.weight(directions) / total


ISOTROPIC = IlluminationModel(
    name="isotropic",
    elevation_min_deg=-90.0,
    elevation_max_deg=90.0,
    law="isotropic",
    description="Uniform over 4 pi. Equals 1 in free space by construction.",
)

ROOFTOP = IlluminationModel(
    name="rooftop",
    elevation_min_deg=3.1,
    elevation_max_deg=60.1,
    law="uniform_sites",
    description=(
        "Macro sites of uniform areal density, height above head 13.5 to 43.5 m, "
        "horizontal range 25 to 250 m. Density on dOmega goes as 1/sin^3(el). "
        "MONOSTATIC_SBR.md section 2.7."
    ),
)

STREET_SMALL_CELL = IlluminationModel(
    name="street_small_cell",
    elevation_min_deg=0.95,
    elevation_max_deg=33.0,
    law="uniform_sites",
    description=(
        "Street furniture small cells, height above head 2.5 to 6.5 m, horizontal "
        "range 10 to 150 m. MONOSTATIC_SBR.md section 2.7."
    ),
)

MODELS: dict[str, IlluminationModel] = {model.name: model for model in (ISOTROPIC, ROOFTOP, STREET_SMALL_CELL)}
