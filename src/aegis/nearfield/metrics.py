"""ICNIRP exposure metrics from a surface absorbed-power-density field.

Given the per-triangle absorbed power density ``S_ab`` [W/m^2] this module
returns the classic ICNIRP 2020 quantities:

* ``sar_wb``      - whole-body SAR [W/kg] = (integral of S_ab) / body mass
* ``pssar_10g``   - peak spatial-average SAR over 10 g [W/kg]
* ``peak_apd``    - peak absorbed power density [W/m^2]
* ``apd_4cm2``    - peak 4 cm^2 spatial-average APD [W/m^2] (>6 GHz metric)
* ``apd_1cm2``    - peak 1 cm^2 spatial-average APD [W/m^2]

psSAR10g is obtained from the surface field through the closed-form reduction of
``theory/psSAR10g.tex``. The volumetric SAR at depth z under a surface point is
``SAR(z) = (2 alpha / rho) S_ab e^{-2 alpha z}`` (eq. SAR-depth). Mass-averaging
over an axis-aligned 10 g cube of side ``L = (m/rho)^{1/3}`` gives (eq.
slab-SAR-h)

    <SAR>_cube = (2 alpha / rho) * <S_ab>_{A=L^2} * h(2 alpha L),
    h(u) = (1 - e^{-u}) / u,

so psSAR10g is the spatial maximum of the L^2-area-averaged S_ab scaled by the
depth-efficiency factor. The L^2 averaging reuses the AEGIS spatial-averaging
matrix with target area L^2. Below 6 GHz h(2 alpha L) is well below 1 and is the
correction that the thin-skin shortcut omits.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np

from aegis.constants import C_0
from aegis.geometry.averaging import precompute_averaging_matrix

# 10 g averaging mass prescribed by ICNIRP 2020 / IEEE C95.3.
PSSAR_MASS_KG = 0.01


def h_depth_efficiency(u):
    """h(u) = (1 - e^{-u}) / u, the fraction of surface SAR surviving averaging.

    Numerically stable at u -> 0 (limit 1). Works on scalars or arrays.
    """
    u = np.asarray(u, dtype=np.float64)
    small = u < 1e-6
    safe = np.where(small, 1.0, u)
    return np.where(small, 1.0 - 0.5 * u, (1.0 - np.exp(-safe)) / safe)


def cube_side_length(rho: float, mass_kg: float = PSSAR_MASS_KG) -> float:
    """Side length L of the cubic averaging volume [m]."""
    return float((mass_kg / rho) ** (1.0 / 3.0))


@dataclass
class IcnirpMetrics:
    """ICNIRP 2020 exposure metrics for one configuration."""

    p_abs_w: float
    sar_wb: float
    pssar_10g: float
    peak_apd: float
    apd_4cm2: float
    apd_1cm2: float
    peak_surface_sar: float  # (2 alpha / rho) * peak S_ab, the z=0 local SAR

    def as_dict(self) -> dict:
        return asdict(self)


def alpha_field(n_tilde: complex, freq_hz: float) -> float:
    """Field attenuation rate alpha = k0 * kappa [1/m], with n_tilde = n - j kappa."""
    k0 = 2.0 * np.pi * freq_hz / C_0
    kappa = -float(np.imag(n_tilde))
    return k0 * kappa


class MetricsEvaluator:
    """Reusable metric evaluator that caches the mesh-dependent averaging matrices.

    The averaging matrices depend only on the mesh geometry, so they are built
    once and reused across an entire sweep of source positions/orientations.
    """

    def __init__(self, centroids, areas, rho: float):
        self.centroids = np.asarray(centroids, dtype=np.float64)
        self.areas = np.asarray(areas, dtype=np.float64)
        self.rho = float(rho)
        self.L = cube_side_length(rho)
        # Averaging matrices (row-stochastic, area-weighted) for the three areas.
        self._G_cube = precompute_averaging_matrix(self.centroids, self.areas, self.L**2)
        self._G_4cm2 = precompute_averaging_matrix(self.centroids, self.areas, 4e-4)
        self._G_1cm2 = precompute_averaging_matrix(self.centroids, self.areas, 1e-4)

    def evaluate(self, sab, n_tilde: complex, freq_hz: float, body_mass_kg: float) -> IcnirpMetrics:
        """Compute all metrics for an absorbed-power-density field ``sab`` (M,)."""
        sab = np.asarray(sab, dtype=np.float64)
        alpha = alpha_field(n_tilde, freq_hz)
        u_cube = 2.0 * alpha * self.L
        h = float(h_depth_efficiency(u_cube))

        p_abs = float(np.sum(sab * self.areas))
        sar_wb = p_abs / body_mass_kg

        sab_cube_avg = self._G_cube @ sab
        pssar_10g = (2.0 * alpha / self.rho) * float(sab_cube_avg.max()) * h
        peak_surface_sar = (2.0 * alpha / self.rho) * float(sab.max())

        return IcnirpMetrics(
            p_abs_w=p_abs,
            sar_wb=sar_wb,
            pssar_10g=pssar_10g,
            peak_apd=float(sab.max()),
            apd_4cm2=float((self._G_4cm2 @ sab).max()),
            apd_1cm2=float((self._G_1cm2 @ sab).max()),
            peak_surface_sar=peak_surface_sar,
        )

    def evaluate_batch(self, sab, n_tilde: complex, freq_hz: float, body_mass_kg: float) -> dict:
        """Vectorised metrics for a batch ``sab`` of shape (B, M).

        Returns a dict of (B,) arrays for each metric. Reuses the cached
        averaging matrices, so the whole sweep shares one set of KD-tree builds.
        """
        sab = np.asarray(sab, dtype=np.float64)  # (B, M)
        alpha = alpha_field(n_tilde, freq_hz)
        h = float(h_depth_efficiency(2.0 * alpha * self.L))
        scale = 2.0 * alpha / self.rho

        p_abs = sab @ self.areas  # (B,)
        # scipy sparse @ (M, B) -> (M, B); peak over triangles per column.
        cube_avg = (self._G_cube @ sab.T).max(axis=0)
        apd_4 = (self._G_4cm2 @ sab.T).max(axis=0)
        apd_1 = (self._G_1cm2 @ sab.T).max(axis=0)
        peak = sab.max(axis=1)

        return {
            "p_abs_w": p_abs,
            "sar_wb": p_abs / body_mass_kg,
            "pssar_10g": scale * np.asarray(cube_avg) * h,
            "peak_apd": peak,
            "apd_4cm2": np.asarray(apd_4),
            "apd_1cm2": np.asarray(apd_1),
            "peak_surface_sar": scale * peak,
        }


def compute_metrics(sab, centroids, areas, n_tilde, freq_hz, rho, body_mass_kg) -> IcnirpMetrics:
    """One-shot convenience wrapper (rebuilds averaging matrices each call)."""
    return MetricsEvaluator(centroids, areas, rho).evaluate(sab, n_tilde, freq_hz, body_mass_kg)
