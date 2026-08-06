"""Hotspot metrology: peak location, FWHM, half-max footprint, enhancement.

The measures follow the hybridizer conventions (peak + FWHM per axis from
1D cuts through the peak) extended with area and volume based half-max
sizes that do not depend on cut orientation, plus the enhancement ratios
the paper argues from (peak over spatial mean, focused over unfocused).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


def fwhm_1d(coords: np.ndarray, values: np.ndarray) -> tuple[float, float, float]:
    """Full width at half maximum of the global peak of a 1D profile.

    Uses linear interpolation for the half-max crossings nearest the peak.

    Returns
    -------
    (fwhm, left, right) : floats
        Width and crossing coordinates. NaN if a crossing is outside the
        profile (peak truncated by the window).
    """
    coords = np.asarray(coords, dtype=float)
    values = np.asarray(values, dtype=float)
    i_pk = int(np.argmax(values))
    half = values[i_pk] / 2.0

    left = np.nan
    for i in range(i_pk, 0, -1):
        if values[i - 1] < half <= values[i]:
            t = (half - values[i - 1]) / (values[i] - values[i - 1])
            left = coords[i - 1] + t * (coords[i] - coords[i - 1])
            break

    right = np.nan
    for i in range(i_pk, len(values) - 1):
        if values[i + 1] < half <= values[i]:
            t = (half - values[i + 1]) / (values[i] - values[i + 1])
            right = coords[i + 1] - t * (coords[i + 1] - coords[i])
            break

    return (right - left, left, right)


@dataclass
class HotspotReport:
    """Summary of one reconstructed hotspot."""

    peak_value: float
    peak_index: tuple
    peak_position: np.ndarray
    fwhm_m: dict = field(default_factory=dict)  # per axis label
    halfmax_equiv_diameter_m: float = np.nan
    core_equiv_diameter_m: float = np.nan  # connected half-max patch at the peak
    peak_over_mean: float = np.nan
    peak_over_median: float = np.nan

    def fwhm_lambda(self, wavelength: float) -> dict:
        return {k: v / wavelength for k, v in self.fwhm_m.items()}


def _connected_halfmax_size(intensity, peak_idx, cell_measure, dim):
    """Equivalent size of the half-max region *connected to the peak*.

    Isolates the focal core from any disconnected background pedestal so the
    reported spot size reflects the few-wavelength focus, not far-flung
    bright patches. Falls back to the global half-max count if scipy.ndimage
    is unavailable.
    """
    mask = intensity >= intensity.flat[np.ravel_multi_index(peak_idx, intensity.shape)] / 2
    try:
        from scipy.ndimage import label
    except Exception:
        n = int(np.count_nonzero(mask))
        measure = n * cell_measure
        return _equiv_diameter(measure, dim)
    lab, _ = label(mask)
    core = lab == lab[peak_idx]
    measure = int(np.count_nonzero(core)) * cell_measure
    return _equiv_diameter(measure, dim)


def _equiv_diameter(measure, dim):
    if measure <= 0:
        return np.nan
    if dim == 2:  # area -> disc diameter
        return 2 * np.sqrt(measure / np.pi)
    return (6 * measure / np.pi) ** (1 / 3)  # volume -> sphere diameter


def analyse_slice(plane, intensity: np.ndarray) -> HotspotReport:
    """Hotspot metrics for a 2D slice (intensity shaped like the plane)."""
    intensity = np.asarray(intensity, dtype=float)
    i, j = np.unravel_index(int(np.argmax(intensity)), intensity.shape)
    peak = float(intensity[i, j])
    pos = plane.coords[i, j]

    fwhm_u, _, _ = fwhm_1d(plane.u, intensity[:, j])
    fwhm_v, _, _ = fwhm_1d(plane.v, intensity[i, :])

    du = plane.u[1] - plane.u[0] if plane.n1 > 1 else 0.0
    dv = plane.v[1] - plane.v[0] if plane.n2 > 1 else 0.0
    area = float(np.count_nonzero(intensity >= peak / 2) * du * dv)
    equiv_d = 2 * np.sqrt(area / np.pi) if area > 0 else np.nan
    core_d = _connected_halfmax_size(intensity, (i, j), du * dv, dim=2)

    return HotspotReport(
        peak_value=peak,
        peak_index=(i, j),
        peak_position=pos,
        fwhm_m={"u": float(fwhm_u), "v": float(fwhm_v)},
        halfmax_equiv_diameter_m=float(equiv_d),
        core_equiv_diameter_m=float(core_d),
        peak_over_mean=peak / float(np.mean(intensity)),
        peak_over_median=peak / float(np.median(intensity)),
    )


def analyse_volume(volume, intensity: np.ndarray) -> HotspotReport:
    """Hotspot metrics for a 3D reconstruction (intensity shaped like volume)."""
    intensity = np.asarray(intensity, dtype=float)
    idx = np.unravel_index(int(np.argmax(intensity)), intensity.shape)
    peak = float(intensity[idx])
    pos = np.array([volume.x[idx[0]], volume.y[idx[1]], volume.z[idx[2]]])

    fx, _, _ = fwhm_1d(volume.x, intensity[:, idx[1], idx[2]])
    fy, _, _ = fwhm_1d(volume.y, intensity[idx[0], :, idx[2]])
    fz, _, _ = fwhm_1d(volume.z, intensity[idx[0], idx[1], :])

    dx = volume.x[1] - volume.x[0] if len(volume.x) > 1 else 0.0
    dy = volume.y[1] - volume.y[0] if len(volume.y) > 1 else 0.0
    dz = volume.z[1] - volume.z[0] if len(volume.z) > 1 else 0.0
    vol = float(np.count_nonzero(intensity >= peak / 2) * dx * dy * dz)
    equiv_d = (6 * vol / np.pi) ** (1 / 3) if vol > 0 else np.nan
    core_d = _connected_halfmax_size(intensity, idx, dx * dy * dz, dim=3)

    return HotspotReport(
        peak_value=peak,
        peak_index=idx,
        peak_position=pos,
        fwhm_m={"x": float(fx), "y": float(fy), "z": float(fz)},
        halfmax_equiv_diameter_m=float(equiv_d),
        core_equiv_diameter_m=float(core_d),
        peak_over_mean=peak / float(np.mean(intensity)),
        peak_over_median=peak / float(np.median(intensity)),
    )


def speckle_contrast(intensity: np.ndarray) -> float:
    """std/mean of intensity. Fully developed speckle gives 1.0."""
    intensity = np.asarray(intensity, dtype=float)
    return float(np.std(intensity) / np.mean(intensity))
