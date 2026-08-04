"""Rigorous coupled wave analysis for a periodic facade unit cell.

A masonry wall is a piecewise constant permittivity profile on a known lattice.
That is the case where a rigorous method is the cheap one: the scattered field
lives on a finite set of Floquet orders, so the unknown is a few hundred complex
numbers rather than a volumetric field. This module solves Maxwell's equations
for such a profile exactly, up to a stated Fourier truncation.

Conventions fixed here and used throughout the package.

- Time dependence ``exp(-i omega t)``, so a wave travelling towards ``+z`` carries
  ``exp(+i k_z z)``.
- The facade occupies ``z <= 0`` with outward normal ``+z``, matching
  :mod:`~.floquet`. Illumination arrives from ``z > 0``.
- Layers are listed from the illuminated side inwards. The first and last are
  semi-infinite. Every interior layer carries a thickness.
- Magnetic permeability is one everywhere, which is true of every building
  material in this study.

The formulation is the standard Fourier modal method written in normalised
coordinates ``z' = k0 z`` with the scaled magnetic field ``h = i Z0 H``, which
makes the two curl equations symmetric:

    curl E = h,  curl h = eps E.

The layer scattering matrices and the Redheffer product follow the usual
gap-medium construction, with the gap permittivity chosen as ``1 + Kx^2 + Ky^2``
so that the gap eigenvectors are the identity.

Two defects, and neither is a truncation you can outrun
--------------------------------------------------------
This solver is research code, it reaches no published number, and it carries
two independent failures recorded as findings 5 and 10 in ``docs/BUGS.md``.
Both are still here on purpose: the refactor moves them intact so that each fix
lands with its own before and after number.

:func:`_pq_matrices` factorises ``eps * E`` by Laurent's rule. The TM case needs
Li's inverse rule, because the field across a stripe boundary has a
discontinuous normal component and cannot be factorised term by term. The
consequence is not slow convergence in any useful sense. On a deep subwavelength
lamellar referee the across-stripe series does not usefully converge at all:
successive increments halve as the truncation doubles, a clean ``1/M`` tail, and
going from ``M = 16`` to ``M = 32`` still moves the answer by 4.4 percent of
itself. Under the inverse rule the same step moves it by 3 parts in a million.

Separately, a lossless passive grating on a semi-infinite substrate can return a
total reflectance far above one, with 54, 56.7 and 58 all measured. That is a
broken solve rather than a slow one, and it is not monotone in the truncation,
so a convergence sweep can step straight over it and a larger truncation is as
likely to land on a bad value as a good one.

Neither is visible to an energy identity. ``R`` and ``T`` blow up together, so
``R + T`` stays consistent to 1e-15 while both terms are nonsense. Test this
module against a known limit, never against its own conservation.

A residual that is physics and not either defect
------------------------------------------------
A subwavelength grating slab is not exactly a homogeneous slab, and the
difference does not vanish with the truncation. Its two faces carry evanescent
boundary layers, and for the across-stripe field those are worth a correction
measured here at +3.24, +0.78 and +0.39 percent for periods of one fiftieth,
one two hundredth and one four hundredth of a wavelength. It falls linearly with
the period, which is the signature of a boundary term. This is why a
subwavelength facade layer cannot simply be homogenised: the effective medium is
the limit, not the answer at any finite period.

Validity. The method is exact for the permittivity profile it is given, up to
the two defects above. Its remaining errors are the Fourier truncation, which is
reported by :func:`convergence_sweep`, and the assumption of a strictly
periodic, infinite, plane-wave-illuminated structure. Disorder and finite
illumination are handled in :mod:`~.kirchhoff`, not here.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import scipy.linalg as sla

from ..roughness import wavelength_m

TWO_PI = 2.0 * math.pi


@dataclass(frozen=True)
class Layer:
    """One stratum of the unit cell.

    ``permittivity`` is either a scalar for a homogeneous layer or a real space
    map sampled on a regular grid over the cell, indexed ``[y, x]``. A scalar
    layer is solved analytically and costs no eigenvalue decomposition, which is
    the difference between a two minute solve and a four minute one at 28 GHz.

    ``thickness_m`` is ``None`` for the two semi-infinite half spaces.
    """

    permittivity: complex | np.ndarray
    thickness_m: float | None = None
    name: str = "layer"

    @property
    def homogeneous(self) -> bool:
        return np.ndim(self.permittivity) == 0


@dataclass(frozen=True)
class RcwaSolution:
    """Reflected Floquet orders of one solve.

    ``efficiency`` is the fraction of incident power carried by each order, so
    it is zero for evanescent orders by construction. ``amplitude_x`` and
    ``amplitude_y`` are the complex tangential field amplitudes, kept because
    the coherent sum over a facade needs phase and the efficiency does not.
    """

    m: np.ndarray
    n: np.ndarray
    kx: np.ndarray
    ky: np.ndarray
    kz: np.ndarray
    propagating: np.ndarray
    efficiency: np.ndarray
    amplitude_x: np.ndarray
    amplitude_y: np.ndarray
    amplitude_z: np.ndarray
    transmission_efficiency: np.ndarray
    frequency_hz: float
    theta_deg: float
    phi_deg: float
    polarisation: str
    harmonics: tuple[int, int]

    @property
    def total_reflectance(self) -> float:
        return float(np.sum(self.efficiency))

    @property
    def total_transmittance(self) -> float:
        return float(np.sum(self.transmission_efficiency))

    @property
    def absorbed(self) -> float:
        return 1.0 - self.total_reflectance - self.total_transmittance

    @property
    def specular_efficiency(self) -> float:
        return float(self.efficiency[self.order_index(0, 0)])

    @property
    def diffuse_efficiency(self) -> float:
        """Reflected power in every order except the specular one."""
        return self.total_reflectance - self.specular_efficiency

    def order_index(self, m: int, n: int) -> int:
        hit = np.nonzero((self.m == m) & (self.n == n))[0]
        if hit.size == 0:
            raise KeyError(f"order ({m}, {n}) is outside the retained harmonics")
        return int(hit[0])

    def scattered_directions(self) -> np.ndarray:
        """Unit vectors of the propagating reflected orders, pointing away from the wall."""
        k0 = TWO_PI / float(wavelength_m(self.frequency_hz))
        stack = np.stack([self.kx, self.ky, np.real(self.kz)], axis=-1) / k0
        return stack[self.propagating]


def harmonic_indices(m_max: int, n_max: int, *, truncation: str = "elliptic") -> tuple[np.ndarray, np.ndarray]:
    """Retained Floquet order labels, as two flat integer arrays.

    ``elliptic`` keeps the orders inside the ellipse of semi-axes ``m_max`` and
    ``n_max``, ``rectangular`` keeps the whole box. The corners of the box are
    the most deeply evanescent orders in the set and contribute least, so
    dropping them removes 21 percent of the modes at equal reach, which is 38
    percent of the memory and 51 percent of the eigenvalue work. The two agree
    closely on every quantity this module reports, which is checked rather than
    assumed.
    """
    m_span = np.arange(-m_max, m_max + 1)
    n_span = np.arange(-n_max, n_max + 1)
    m_grid, n_grid = np.meshgrid(m_span, n_span, indexing="ij")
    m_flat, n_flat = m_grid.ravel(), n_grid.ravel()
    if truncation == "rectangular":
        return m_flat, n_flat
    if truncation != "elliptic":
        raise ValueError(f"unknown truncation '{truncation}', expected 'elliptic' or 'rectangular'")
    radius = (m_flat / max(m_max, 1)) ** 2 + (n_flat / max(n_max, 1)) ** 2
    keep = radius <= 1.0 + 1e-9
    return m_flat[keep], n_flat[keep]


def convolution_matrix(profile: np.ndarray, m_index: np.ndarray, n_index: np.ndarray) -> np.ndarray:
    """Toeplitz-like matrix of the Fourier coefficients of a sampled cell map.

    ``profile`` is indexed ``[y, x]`` over one period in each direction. The
    entry ``C[p, q]`` is the Fourier coefficient of order ``(m_p - m_q,
    n_p - n_q)``, which is what multiplication by ``profile`` becomes in the
    harmonic basis.
    """
    array = np.asarray(profile)
    if array.ndim != 2:
        raise ValueError("permittivity profile must be a two dimensional cell map")
    n_y, n_x = array.shape
    spectrum = np.fft.fftshift(np.fft.fft2(array)) / (n_x * n_y)
    centre_y, centre_x = n_y // 2, n_x // 2
    delta_m = m_index[:, None] - m_index[None, :]
    delta_n = n_index[:, None] - n_index[None, :]
    if np.abs(delta_m).max() > centre_x or np.abs(delta_n).max() > centre_y:
        raise ValueError(
            "the cell map is sampled too coarsely for the requested harmonics: "
            f"need at least {2 * np.abs(delta_m).max() + 1} by {2 * np.abs(delta_n).max() + 1} samples"
        )
    return spectrum[centre_y + delta_n, centre_x + delta_m]


def _branch(values: np.ndarray) -> np.ndarray:
    """Pick the root that decays or propagates towards ``+z'`` under ``exp(-lam z')``."""
    root = np.sqrt(np.asarray(values, dtype=np.complex128))
    flip = (root.real < 0.0) | ((np.abs(root.real) < 1e-12) & (root.imag > 0.0))
    root = np.where(flip, -root, root)
    return root


def _pq_matrices(
    eps: np.ndarray, eps_inverse: np.ndarray, kx: np.ndarray, ky: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    k_x = np.diag(kx)
    k_y = np.diag(ky)
    identity = np.eye(kx.size)
    p_matrix = np.block(
        [
            [k_x @ eps_inverse @ k_y, identity - k_x @ eps_inverse @ k_x],
            [k_y @ eps_inverse @ k_y - identity, -k_y @ eps_inverse @ k_x],
        ]
    )
    q_matrix = np.block(
        [
            [k_x @ k_y, eps - k_x @ k_x],
            [k_y @ k_y - eps, -k_y @ k_x],
        ]
    )
    return p_matrix, q_matrix


def _layer_modes(
    layer: Layer,
    kx: np.ndarray,
    ky: np.ndarray,
    m_index: np.ndarray,
    n_index: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Eigenmodes of one layer as ``(W, V, lam)``."""
    count = kx.size
    if layer.homogeneous:
        eps_value = complex(layer.permittivity)
        lam_half = _branch(kx**2 + ky**2 - eps_value)
        lam = np.concatenate([lam_half, lam_half])
        eps = eps_value * np.eye(count)
        _, q_matrix = _pq_matrices(eps, np.eye(count) / eps_value, kx, ky)
        w_matrix = np.eye(2 * count, dtype=np.complex128)
        v_matrix = q_matrix / lam[None, :]
        return w_matrix, v_matrix, lam
    eps = convolution_matrix(layer.permittivity, m_index, n_index)
    eps_inverse = np.linalg.inv(eps)
    p_matrix, q_matrix = _pq_matrices(eps, eps_inverse, kx, ky)
    del eps, eps_inverse
    # Peak memory lives here and is quadratic in the retained order count, so
    # every intermediate is released before the next one is formed.
    omega_squared = p_matrix @ q_matrix
    del p_matrix
    eigenvalues, w_matrix = sla.eig(omega_squared, overwrite_a=True)
    del omega_squared
    lam = _branch(eigenvalues)
    v_matrix = q_matrix @ w_matrix
    del q_matrix
    v_matrix /= lam[None, :]
    return w_matrix, v_matrix, lam


def _star(left: tuple[np.ndarray, ...], right: tuple[np.ndarray, ...]) -> tuple[np.ndarray, ...]:
    """Redheffer star product of two scattering matrices."""
    a11, a12, a21, a22 = left
    b11, b12, b21, b22 = right
    identity = np.eye(a11.shape[0], dtype=np.complex128)
    d_term = a12 @ np.linalg.inv(identity - b11 @ a22)
    f_term = b21 @ np.linalg.inv(identity - a22 @ b11)
    return (
        a11 + d_term @ b11 @ a21,
        d_term @ b12,
        f_term @ a21,
        b22 + f_term @ a22 @ b12,
    )


def _polarisation_vector(polarisation: str, theta_deg: float, phi_deg: float) -> np.ndarray:
    theta = math.radians(theta_deg)
    phi = math.radians(phi_deg)
    s_hat = np.array([-math.sin(phi), math.cos(phi), 0.0])
    p_hat = np.array([math.cos(theta) * math.cos(phi), math.cos(theta) * math.sin(phi), math.sin(theta)])
    if polarisation.lower() in ("te", "s"):
        return s_hat
    if polarisation.lower() in ("tm", "p"):
        return p_hat
    raise ValueError(f"unknown polarisation '{polarisation}', expected 'te' or 'tm'")


def solve(
    layers: list[Layer],
    *,
    period_x_m: float,
    period_y_m: float,
    frequency_hz: float,
    theta_deg: float,
    phi_deg: float = 0.0,
    polarisation: str = "te",
    harmonics: tuple[int, int] = (8, 8),
    truncation: str = "elliptic",
) -> RcwaSolution:
    """Solve one periodic cell at one frequency, incidence and polarisation.

    ``layers[0]`` is the semi-infinite illuminated half space and must be
    homogeneous. ``layers[-1]`` is the semi-infinite substrate and may be
    laterally patterned. Everything between carries a thickness.
    """
    if len(layers) < 2:
        raise ValueError("need at least an incidence half space and a substrate")
    if not layers[0].homogeneous:
        raise ValueError("the illuminated half space must be homogeneous")
    if any(layer.thickness_m is None for layer in layers[1:-1]):
        raise ValueError("interior layers must carry a thickness")
    if layers[0].thickness_m is not None or layers[-1].thickness_m is not None:
        raise ValueError("the two half spaces must not carry a thickness")

    m_max, n_max = harmonics
    m_index, n_index = harmonic_indices(m_max, n_max, truncation=truncation)
    count = m_index.size

    lam0 = float(wavelength_m(frequency_hz))
    k0 = TWO_PI / lam0
    eps_ref = complex(layers[0].permittivity)
    index_ref = np.sqrt(eps_ref).real
    theta = math.radians(theta_deg)
    phi = math.radians(phi_deg)
    kx_inc = index_ref * math.sin(theta) * math.cos(phi)
    ky_inc = index_ref * math.sin(theta) * math.sin(phi)
    kz_inc = index_ref * math.cos(theta)

    kx = kx_inc + m_index * lam0 / period_x_m
    ky = ky_inc + n_index * lam0 / period_y_m

    kz_ref = np.sqrt(np.asarray(eps_ref - kx**2 - ky**2, dtype=np.complex128))
    kz_ref = np.where(kz_ref.real < 0, -kz_ref, kz_ref)

    # Gap medium chosen so that its eigenvectors are the identity.
    eps_gap = 1.0 + kx**2 + ky**2
    lam_gap_half = _branch(kx**2 + ky**2 - eps_gap)
    lam_gap = np.concatenate([lam_gap_half, lam_gap_half])
    k_x = np.diag(kx)
    k_y = np.diag(ky)
    eps_gap_matrix = np.diag(eps_gap)
    q_gap = np.block(
        [
            [k_x @ k_y, eps_gap_matrix - k_x @ k_x],
            [k_y @ k_y - eps_gap_matrix, -k_y @ k_x],
        ]
    )
    w_gap = np.eye(2 * count, dtype=np.complex128)
    v_gap = q_gap / lam_gap[None, :]
    w_gap_inv = w_gap
    v_gap_inv = np.linalg.inv(v_gap)

    zero = np.zeros((2 * count, 2 * count), dtype=np.complex128)
    identity = np.eye(2 * count, dtype=np.complex128)

    # Reflection side half space.
    w_ref, v_ref, _ = _layer_modes(layers[0], kx, ky, m_index, n_index)
    a_ref = w_gap_inv @ w_ref + v_gap_inv @ v_ref
    b_ref = w_gap_inv @ w_ref - v_gap_inv @ v_ref
    a_ref_inv = np.linalg.inv(a_ref)
    global_s = (
        -a_ref_inv @ b_ref,
        2.0 * a_ref_inv,
        0.5 * (a_ref - b_ref @ a_ref_inv @ b_ref),
        b_ref @ a_ref_inv,
    )

    for layer in layers[1:-1]:
        w_i, v_i, lam_i = _layer_modes(layer, kx, ky, m_index, n_index)
        w_inv = np.linalg.inv(w_i)
        del w_i
        v_inv = np.linalg.inv(v_i)
        del v_i
        a_i = w_inv @ w_gap + v_inv @ v_gap
        b_i = w_inv @ w_gap - v_inv @ v_gap
        del w_inv, v_inv
        x_i = np.diag(np.exp(-lam_i * k0 * float(layer.thickness_m)))
        a_inv = np.linalg.inv(a_i)
        xb = x_i @ b_i
        xba = xb @ a_inv
        common = np.linalg.inv(a_i - xba @ xb)
        s11 = common @ (xba @ x_i @ a_i - b_i)
        s12 = common @ x_i @ (a_i - b_i @ a_inv @ b_i)
        del a_i, b_i, x_i, a_inv, xb, xba, common
        global_s = _star(global_s, (s11, s12, s12, s11))
        del s11, s12

    # Transmission side half space.
    w_trn, v_trn, _ = _layer_modes(layers[-1], kx, ky, m_index, n_index)
    a_trn = w_gap_inv @ w_trn + v_gap_inv @ v_trn
    b_trn = w_gap_inv @ w_trn - v_gap_inv @ v_trn
    a_trn_inv = np.linalg.inv(a_trn)
    s_trn = (
        b_trn @ a_trn_inv,
        0.5 * (a_trn - b_trn @ a_trn_inv @ b_trn),
        2.0 * a_trn_inv,
        -a_trn_inv @ b_trn,
    )
    global_s = _star(global_s, s_trn)
    del zero, identity

    polarisation_vector = _polarisation_vector(polarisation, theta_deg, phi_deg)
    delta = np.zeros(count, dtype=np.complex128)
    delta[np.nonzero((m_index == 0) & (n_index == 0))[0][0]] = 1.0
    source = np.concatenate([polarisation_vector[0] * delta, polarisation_vector[1] * delta])
    source = np.linalg.solve(w_ref, source)

    reflected = w_ref @ (global_s[0] @ source)
    transmitted = w_trn @ (global_s[2] @ source)

    ex_r = reflected[:count]
    ey_r = reflected[count:]
    with np.errstate(divide="ignore", invalid="ignore"):
        ez_r = np.where(np.abs(kz_ref) > 1e-12, (kx * ex_r + ky * ey_r) / kz_ref, 0.0)
    power_r = np.abs(ex_r) ** 2 + np.abs(ey_r) ** 2 + np.abs(ez_r) ** 2
    efficiency = power_r * np.real(kz_ref) / kz_inc

    if layers[-1].homogeneous:
        eps_trn = complex(layers[-1].permittivity)
        kz_trn = np.sqrt(np.asarray(eps_trn - kx**2 - ky**2, dtype=np.complex128))
        kz_trn = np.where(kz_trn.real < 0, -kz_trn, kz_trn)
        ex_t = transmitted[:count]
        ey_t = transmitted[count:]
        with np.errstate(divide="ignore", invalid="ignore"):
            ez_t = np.where(np.abs(kz_trn) > 1e-12, -(kx * ex_t + ky * ey_t) / kz_trn, 0.0)
        power_t = np.abs(ex_t) ** 2 + np.abs(ey_t) ** 2 + np.abs(ez_t) ** 2
        transmission = power_t * np.real(kz_trn) / kz_inc
    else:
        transmission = np.full(count, np.nan)

    propagating = np.real(kz_ref) > 1e-9
    return RcwaSolution(
        m=m_index,
        n=n_index,
        kx=kx * k0,
        ky=ky * k0,
        kz=kz_ref * k0,
        propagating=propagating,
        efficiency=np.where(propagating, efficiency, 0.0),
        amplitude_x=ex_r,
        amplitude_y=ey_r,
        amplitude_z=ez_r,
        transmission_efficiency=transmission,
        frequency_hz=float(frequency_hz),
        theta_deg=float(theta_deg),
        phi_deg=float(phi_deg),
        polarisation=polarisation,
        harmonics=(int(m_max), int(n_max)),
    )


def convergence_sweep(
    layers: list[Layer],
    *,
    period_x_m: float,
    period_y_m: float,
    frequency_hz: float,
    theta_deg: float,
    phi_deg: float = 0.0,
    polarisation: str = "te",
    harmonic_counts: tuple[tuple[int, int], ...] = ((4, 0), (8, 0), (12, 0), (16, 0)),
    truncation: str = "elliptic",
) -> list[dict[str, float]]:
    """Total and specular reflectance against Fourier truncation.

    Truncation is the only free parameter of a rigorous solve, so it is the one
    number that has to be reported rather than chosen. The returned records are
    written verbatim into the sweep output.
    """
    records: list[dict[str, float]] = []
    for harmonics in harmonic_counts:
        solution = solve(
            layers,
            period_x_m=period_x_m,
            period_y_m=period_y_m,
            frequency_hz=frequency_hz,
            theta_deg=theta_deg,
            phi_deg=phi_deg,
            polarisation=polarisation,
            harmonics=harmonics,
            truncation=truncation,
        )
        records.append(
            {
                "m_max": float(harmonics[0]),
                "n_max": float(harmonics[1]),
                "truncation": truncation,
                "modes": float(solution.m.size),
                "matrix_dimension": float(2 * solution.m.size),
                "dense_matrix_gibibytes": float(2 * solution.m.size) ** 2 * 16.0 / 2**30,
                "total_reflectance": solution.total_reflectance,
                "specular_efficiency": solution.specular_efficiency,
                "diffuse_efficiency": solution.diffuse_efficiency,
                "propagating_orders": float(np.count_nonzero(solution.propagating)),
            }
        )
    return records
