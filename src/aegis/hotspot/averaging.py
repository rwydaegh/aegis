"""Spatial averaging of a reconstructed hotspot, and the order-of-operations
question the paper turns on.

Two distinct averages of the same field collapse a hotspot to a number, and
they are *not* the same number:

propagation-wise (coherent, field first)
    Average the complex field over a patch, then take its power:
    ``|<E>|^2 / 2Z0``. Phasors that point in different directions cancel, so
    this is what a single large patch antenna or a coherent aperture would
    read. It is the most aggressive: a fringe field that is bright but
    sign-alternating averages toward zero.

exposure-wise (incoherent, power first)
    Take the power everywhere, then average over a patch:
    ``<|E|^2 / 2Z0>``. Nothing cancels because every sample is already
    non-negative. This is what the compliance metric does (psSAR / absorbed
    power density over a 4 cm^2 square), and what a power meter scanned over
    the patch would integrate.

By Cauchy-Schwarz ``<|E|^2> >= |<E>|^2`` pointwise on any patch, so the
exposure-wise average is always the larger (or equal) of the two. The gap is
the coherence the patch throws away. The compliance limit is written on the
exposure-wise average, so that is the relevant dilution of the focal peak;
the propagation-wise average is reported alongside to show how much further a
phase-coherent reader would suppress the same spot.

A third reference level is the incoherent power floor: sum the per-direction
powers with no cross terms at all,

    S_inc = sum_u |w_u|^2 / 2Z0,

with ``w_u`` the collapsed per-direction plane-wave weight. The spatial mean
of ``|E|^2`` over a window much larger than a wavelength converges to this
value, because the cross terms oscillate and average out. It is the
"homogenised" level the hotspot relaxes to far from the focus.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from aegis.constants import Z_0


def _window_cells(pixel_m: float, patch_side_m: float) -> int:
    """Odd number of cells spanning ``patch_side_m`` at pixel pitch ``pixel_m``."""
    n = int(round(patch_side_m / pixel_m))
    n = max(1, n)
    return n + 1 if n % 2 == 0 else n


def _uniform(a: np.ndarray, size: int) -> np.ndarray:
    """Square box average, reflecting at the borders. Complex-safe."""
    from scipy.ndimage import uniform_filter

    if np.iscomplexobj(a):
        return uniform_filter(a.real, size, mode="nearest") + 1j * uniform_filter(a.imag, size, mode="nearest")
    return uniform_filter(a, size, mode="nearest")


def exposure_average(E: np.ndarray, pixel_m: float, patch_side_m: float) -> np.ndarray:
    """``<|E|^2/2Z0>`` over a square patch: power first, then average.

    ``E`` is ``(n1, n2, 3)`` complex. Returns the patch-averaged power density
    map ``(n1, n2)``. This is the compliance-style (incoherent) average; every
    sample is non-negative so nothing cancels.
    """
    E = np.asarray(E)
    S = np.sum(np.abs(E) ** 2, axis=-1) / (2 * Z_0)
    size = _window_cells(pixel_m, patch_side_m)
    return _uniform(S, size)


def propagation_average(E: np.ndarray, pixel_m: float, patch_side_m: float) -> np.ndarray:
    """``|<E>|^2/2Z0`` over a square patch: complex average, then power.

    ``E`` is ``(n1, n2, 3)`` complex. Returns ``(n1, n2)``. This is the
    coherent (field-level) average a phase-preserving aperture would read;
    sign-alternating fringes cancel, so it never exceeds the exposure-wise
    average.
    """
    E = np.asarray(E)
    size = _window_cells(pixel_m, patch_side_m)
    Ebar = np.stack([_uniform(E[..., c], size) for c in range(E.shape[-1])], axis=-1)
    return np.sum(np.abs(Ebar) ** 2, axis=-1) / (2 * Z_0)


def incoherent_power(weights: np.ndarray) -> float:
    """``sum_u |w_u|^2 / 2Z0``: the diffuse floor with no cross terms.

    ``weights`` are the collapsed per-direction plane-wave weights ``(U, 3)``
    from ``collapse_paths`` (the precoder already folded in). The spatial mean
    of the reconstructed ``|E|^2`` converges to this as the window grows.
    """
    w = np.asarray(weights)
    return float(np.sum(np.abs(w) ** 2) / (2 * Z_0))


def path_power(psi: np.ndarray, element_index: np.ndarray, x: np.ndarray) -> float:
    """``sum_n |x_{j(n)} psi_n|^2 / 2Z0``: the fully incoherent per-path power.

    Every path contributes independently, including the separate array
    elements that share an arrival direction, so this floor sits below
    ``incoherent_power`` by exactly the coherent array-combining gain folded
    into each direction.
    """
    psi = np.asarray(psi)
    x = np.asarray(x)
    element_index = np.asarray(element_index)
    p = np.sum(np.abs(psi * x[element_index][:, None]) ** 2)
    return float(p / (2 * Z_0))


def participation_ratio(weights: np.ndarray) -> float:
    """``(sum_u ||w_u||)^2 / sum_u ||w_u||^2``: the effective number of
    coherently combining directions, and the ceiling on the focusing gain.

    With per-direction magnitudes ``a_u = ||w_u||``, a perfectly phase-aligned
    focus reaches ``(sum a_u)^2`` while the same power decohered sits at
    ``sum a_u^2``, so their ratio is the largest peak-over-floor a coherent
    focus could achieve. Equals the number of directions when all carry equal
    power, and drops toward 1 when one direction dominates.
    """
    a = np.linalg.norm(np.asarray(weights), axis=1)
    s = float(np.sum(a**2))
    return float(np.sum(a) ** 2 / s) if s > 0 else 0.0


def decohere_weights(weights: np.ndarray, rng) -> np.ndarray:
    """Scramble the inter-direction phases, keep the per-direction power.

    Multiplies each direction's weight by an independent random phase. This
    leaves the angular power spectrum ``||w_u||`` (and therefore the total
    power delivered to the region, ``sum_u ||w_u||^2``) exactly unchanged
    while destroying the coherent focus. It is the matched-illumination
    baseline: the same multipath power illuminates the body, but the last-
    wavelength wavefront alignment that builds the hotspot is removed. The
    decohered field is flat at the incoherent floor in expectation.
    """
    w = np.asarray(weights)
    phase = np.exp(1j * rng.uniform(0, 2 * np.pi, w.shape[0]))
    return w * phase[:, None]


@dataclass
class PatchSweepPoint:
    patch_side_m: float
    patch_area_cm2: float
    peak_exposure: float  # max over the slice of <|E|^2>
    peak_propagation: float  # max over the slice of |<E>|^2
    window_cells: int


def patch_sweep(
    plane,
    E: np.ndarray,
    patch_sides_m,
) -> list[PatchSweepPoint]:
    """How the focal peak survives spatial averaging, both ways.

    For each patch side, average the field over a sliding square window and
    record the peak of the exposure-wise and propagation-wise maps. The first
    entry (smallest patch) is essentially the point peak; larger patches show
    the dilution. A patch side of sqrt(4) cm = 2 cm reproduces the 4 cm^2
    compliance footprint.
    """
    pixel_m = float(plane.u[1] - plane.u[0])
    out = []
    for side in patch_sides_m:
        size = _window_cells(pixel_m, side)
        Se = exposure_average(E, pixel_m, side)
        Sp = propagation_average(E, pixel_m, side)
        out.append(
            PatchSweepPoint(
                patch_side_m=float(side),
                patch_area_cm2=float((side * 100) ** 2),
                peak_exposure=float(Se.max()),
                peak_propagation=float(Sp.max()),
                window_cells=size,
            )
        )
    return out


@dataclass
class RadialProfile:
    r_cm: np.ndarray  # bin centres [cm]
    mean: np.ndarray  # <S> in the annulus [W/m^2]
    p95: np.ndarray  # 95th percentile of S in the annulus
    peak: float  # global peak S [W/m^2]
    floor: float  # incoherent power floor [W/m^2]


def radial_profile(plane, S: np.ndarray, n_bins: int = 60, *, floor: float = np.nan) -> RadialProfile:
    """Azimuthally averaged power density vs distance from the slice centre.

    Bins ``S`` by radius about the plane centre (the focus). The mean per
    annulus shows the focal lobe decaying outward toward the diffuse floor:
    the answer to "if I keep zooming out, does the hotspot wash out to
    something homogeneous?".
    """
    S = np.asarray(S, dtype=float)
    UU, VV = np.meshgrid(plane.u, plane.v, indexing="ij")
    R = np.sqrt(UU**2 + VV**2) * 100  # cm
    r_max = R.max() / np.sqrt(2)  # stay inside the inscribed circle
    edges = np.linspace(0, r_max, n_bins + 1)
    centres = 0.5 * (edges[:-1] + edges[1:])
    mean = np.full(n_bins, np.nan)
    p95 = np.full(n_bins, np.nan)
    for b in range(n_bins):
        m = (edges[b] <= R) & (edges[b + 1] > R)
        if m.any():
            mean[b] = S[m].mean()
            p95[b] = np.percentile(S[m], 95)
    return RadialProfile(r_cm=centres, mean=mean, p95=p95, peak=float(S.max()), floor=float(floor))
