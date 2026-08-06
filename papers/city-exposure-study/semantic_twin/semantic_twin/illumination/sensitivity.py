"""Reweighting of harvested transport by an illumination law.

The sensitivity and law-ordering commands use the same reduced trace. This
module owns its elevation grid and the operation that maps an illumination law
onto that trace, so neither command imports the other as a library.
"""

from __future__ import annotations

import pathlib

import numpy as np

from .model import IlluminationModel

NORMALISATION_QUADRATURE = 20_001


def elevation_centres(bins: int) -> np.ndarray:
    """Centres of equal elevation bins covering the whole sphere."""
    edges = np.linspace(-90.0, 90.0, bins + 1)
    return 0.5 * (edges[:-1] + edges[1:])


def density_on(model: IlluminationModel, elevation_deg: np.ndarray) -> np.ndarray:
    """Sample an illumination density on a uniform elevation axis."""
    elevation = np.radians(elevation_deg)
    directions = np.column_stack([np.cos(elevation), np.zeros_like(elevation), np.sin(elevation)])
    return model.density(directions, model.normalisation(NORMALISATION_QUADRATURE))


def isotropic_density(elevation_deg: np.ndarray) -> np.ndarray:
    """The uniform density on the sphere, sampled on an elevation axis."""
    return np.full(elevation_deg.shape, 1.0 / (4.0 * np.pi))


class Reweighter:
    """Hold one site's reduced trace and evaluate new illumination laws on it."""

    def __init__(self, path: pathlib.Path) -> None:
        data = np.load(path, allow_pickle=False)
        self.fine = data["fine"].astype(np.float64)
        self.direct = data["direct"].astype(np.float64)
        self.crop = data["crop"].astype(np.float64)
        self.crop_range_edges_m = data["crop_range_edges_m"]
        self.traced_chi = data["traced_chi"]
        self.traced_models = [str(value) for value in data["traced_models"]]
        self.points = data["points"]
        self.index = data["index"]
        self.crop_radius_m = float(data["crop_radius_m"])
        self.elevation_deg = elevation_centres(int(data["elevation_bins"]))
        self.crop_elevation_deg = elevation_centres(int(data["crop_elevation_bins"]))

    @property
    def locations(self) -> int:
        return int(self.fine.shape[0])

    def chi(self, model: IlluminationModel | None) -> np.ndarray:
        """Return susceptibility per standpoint. ``None`` is isotropic."""
        weight = isotropic_density(self.elevation_deg) if model is None else density_on(model, self.elevation_deg)
        return self.fine @ weight

    def chi_direct(self, model: IlluminationModel | None) -> np.ndarray:
        """Return direct susceptibility per standpoint."""
        weight = isotropic_density(self.elevation_deg) if model is None else density_on(model, self.elevation_deg)
        return self.direct @ weight

    def chi_built(self, model: IlluminationModel) -> tuple[np.ndarray, np.ndarray]:
        """Evaluate a band law with all sources and with unbuilt sources refused."""
        h_min, h_max = model.height_band_m  # type: ignore[misc]
        d_min, d_max = model.range_band_m  # type: ignore[misc]
        elevation = np.radians(self.crop_elevation_deg)
        sine = np.sin(elevation)
        cosine = np.cos(elevation)
        total = model.normalisation(NORMALISATION_QUADRATURE)
        lower = self.crop_range_edges_m[:-1]

        with np.errstate(divide="ignore", invalid="ignore"):
            near = np.maximum(h_min / sine, d_min / cosine)
            far_full = np.minimum(h_max / sine, d_max / cosine)
            cap = np.minimum(d_max, lower[None, :])
            far_built = np.minimum(h_max / sine[:, None], cap / cosine[:, None])
        inside = sine > 0.0
        weight_full = np.where(inside, np.maximum(far_full**3 - near**3, 0.0) / 3.0, 0.0) / total
        weight_built = np.where(inside[:, None], np.maximum(far_built**3 - near[:, None] ** 3, 0.0) / 3.0, 0.0) / total
        published = self.crop.sum(axis=2) @ weight_full
        built = np.einsum("pej,ej->p", self.crop, weight_built)
        return published, built
