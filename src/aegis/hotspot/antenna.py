"""UE receive antenna patterns for the end-to-end channel vector.

The monograph (signal branch, eq. h-def) writes the UE channel as

    h_j = sum_{n: j(n)=j} C_R(k_n)^H psi_n  exp(-i k0 k_n . r_UE),

where C_R(k) in C^2 is the UE receive antenna pattern in the (theta, phi)
basis and the scalar a_n = C_R(k_n)^H psi_n projects each path's 3D
polarisation-amplitude vector onto the antenna response. The base-station
transmit pattern C_T is already folded into psi by the ray tracer; the only
antenna missing from the paper's scalar channel is this UE one, which the
default ``channel_at`` had degenerated to a unit-gain vertical reference.

This module supplies C_R as a 3D Cartesian vector field over arrival
directions, so ``channel_at`` can compute the antenna-aware h exactly as AEGIS
MIMO mode does (``aegis.mimo.channel.compute_channel_vector`` projects onto a
half-wave dipole effective length the same way). Three sources:

- ``dipole_response``: the analytic half-wave dipole effective length (the
  pattern AEGIS MIMO uses). Self-contained and reproducible, the default.
- ``AntennaPattern.synthetic``: analytic isotropic / dipole / cos^n patch
  directivity grids, given a vertical polarisation.
- ``AntennaPattern.from_npz``: a measured free-space pattern with full complex
  (E_theta, E_phi) polarisation, e.g. the GOLIAT Sim4Life near-to-far handset
  grids. This is the actual smartphone free-space pattern.

All return C_R(k) as ``(N, 3)`` complex vectors perpendicular to each k, so the
per-path scalar is ``a_n = sum(conj(C_R) * psi, axis=1)``.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from aegis.constants import C_0


def _spherical_basis(k_hat: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Polar angle, azimuth and local (theta_hat, phi_hat) frame for each k.

    Convention matches Sionna / the measured grids: theta is measured from +z,
    phi is the azimuth from +x in the xy-plane.

        theta_hat = ( cos th cos ph, cos th sin ph, -sin th )
        phi_hat   = ( -sin ph,        cos ph,        0       )

    At the poles (sin th -> 0) phi is undefined; phi_hat falls back to +x and
    theta_hat to a consistent perpendicular, which is harmless because the
    fields there are sampled, not differentiated.
    """
    k = np.asarray(k_hat, float)
    kz = np.clip(k[:, 2], -1.0, 1.0)
    theta = np.arccos(kz)
    phi = np.arctan2(k[:, 1], k[:, 0])
    ct, st = np.cos(theta), np.sin(theta)
    cp, sp = np.cos(phi), np.sin(phi)
    theta_hat = np.stack([ct * cp, ct * sp, -st], axis=1)
    phi_hat = np.stack([-sp, cp, np.zeros_like(sp)], axis=1)
    return theta, phi, theta_hat, phi_hat


def dipole_response(k_hat: np.ndarray, axis: np.ndarray, freq_hz: float) -> np.ndarray:
    """Half-wave dipole effective length C_R(k), as (N, 3) real vectors.

    C_R(k) = (lambda/pi) * [cos(pi/2 cos a) / sin a] * a_hat, with ``a`` the
    angle between k and the dipole axis and a_hat the E-plane unit vector
    (component of the axis perpendicular to k). This is the exact pattern AEGIS
    MIMO uses (``aegis.mimo.channel.dipole_effective_length``); ``|C_R|^2`` is
    the dipole directivity up to the constant.
    """
    k = np.asarray(k_hat, float)
    d = np.asarray(axis, float)
    d = d / np.linalg.norm(d)
    lam = C_0 / freq_hz
    cos_a = k @ d
    sin_a = np.sqrt(np.maximum(1.0 - cos_a**2, 0.0))
    d_perp = d[None, :] - cos_a[:, None] * k
    d_perp_n = np.linalg.norm(d_perp, axis=1, keepdims=True)
    a_hat = d_perp / np.where(d_perp_n > 1e-15, d_perp_n, 1.0)
    num = np.cos(0.5 * np.pi * cos_a)
    scalar = np.where(sin_a > 1e-9, num / np.where(sin_a > 1e-9, sin_a, 1.0), 0.0)
    return (lam / np.pi) * scalar[:, None] * a_hat


@dataclass
class AntennaPattern:
    """A UE receive antenna pattern on a regular (theta, phi) grid.

    ``e_theta`` and ``e_phi`` are the complex field components in the
    (theta_hat, phi_hat) basis (``C_R`` in C^2). For a synthetic pattern given
    only by scalar directivity, ``e_phi = 0`` and ``e_theta = sqrt(D)`` puts all
    response on the theta (vertical-ish) polarisation, matching the paper's
    existing vertical reference but now tapered by the directivity.
    """

    theta_rad: np.ndarray  # (n_theta,) increasing in [0, pi]
    phi_rad: np.ndarray  # (n_phi,) increasing in [-pi, pi]
    e_theta: np.ndarray  # (n_phi, n_theta) complex
    e_phi: np.ndarray  # (n_phi, n_theta) complex
    freq_hz: float
    name: str = "pattern"

    # -- constructors -------------------------------------------------------

    @classmethod
    def from_npz(cls, npz_path: str | Path, freq_hz: float | None = None, name: str | None = None) -> AntennaPattern:
        """Load a measured ``far_field_1deg_pattern.npz`` (GOLIAT/Sim4Life).

        Uses the rigorous complex (E_theta, E_phi) grids, so the full
        polarisation of the handset free-space pattern enters the channel. The
        grid is normalised to unit sphere-average power so the antenna neither
        adds nor removes total received energy relative to an isotropic
        reference (gain only redistributes it over direction).
        """
        npz_path = Path(npz_path)
        d = np.load(npz_path)
        theta = np.asarray(d["theta_rad"], float)
        phi = np.asarray(d["phi_rad"], float)
        et = np.asarray(d["e_theta" if "e_theta" in d else "Etheta"]).astype(complex)
        ep = np.asarray(d["e_phi" if "e_phi" in d else "Ephi"]).astype(complex)
        obj = cls(theta, phi, et, ep, float(freq_hz or 0.0), name or npz_path.parent.name)
        return obj._normalised()

    @classmethod
    def synthetic(cls, kind: str, freq_hz: float, n: float = 4.0) -> AntennaPattern:
        """Analytic ``isotropic`` / ``dipole`` / ``patch`` directivity, vertical pol."""
        theta = np.linspace(0.0, np.pi, 181)
        phi = np.linspace(-np.pi, np.pi, 361)
        st = np.sin(theta)
        if kind == "isotropic":
            d_theta = np.ones_like(theta)
        elif kind == "dipole":
            with np.errstate(divide="ignore", invalid="ignore"):
                d_theta = np.where(st > 1e-9, np.cos(0.5 * np.pi * np.cos(theta)) / st, 0.0) ** 2
        elif kind == "patch":
            front = np.cos(theta)
            d_theta = np.where(front > 0.0, front**n, 0.0)
        else:
            raise ValueError(f"unknown synthetic pattern {kind!r}")
        et = np.sqrt(np.repeat(d_theta[None, :], phi.size, axis=0)).astype(complex)
        ep = np.zeros_like(et)
        return cls(theta, phi, et, ep, float(freq_hz), kind)._normalised()

    def _normalised(self) -> AntennaPattern:
        """Scale so the sphere-average of |C_R|^2 is 1 (unit-gain reference)."""
        power = np.abs(self.e_theta) ** 2 + np.abs(self.e_phi) ** 2  # (n_phi, n_theta)
        st = np.sin(self.theta_rad)[None, :]
        # average over the sphere: (1/4pi) int |C|^2 sin th dth dph
        num = np.trapezoid(np.trapezoid(power * st, self.theta_rad, axis=1), self.phi_rad)
        avg = num / (4 * np.pi)
        if avg > 0:
            s = 1.0 / np.sqrt(avg)
            self.e_theta = self.e_theta * s
            self.e_phi = self.e_phi * s
        return self

    # -- sampling -----------------------------------------------------------

    def response(self, k_hat: np.ndarray, rotation: np.ndarray | None = None) -> np.ndarray:
        """C_R(k) as (N, 3) complex Cartesian vectors perpendicular to each k.

        ``rotation`` is the antenna-frame -> world matrix (default identity).
        Each direction is sampled in the antenna frame, then E_theta and E_phi
        are lifted onto the local (theta_hat, phi_hat) frame in world
        coordinates so the result dots directly against the world-frame psi.
        """
        k = np.asarray(k_hat, float)
        # world -> antenna (R^T k); rotation columns are antenna axes in world
        k_ant = k @ np.asarray(rotation, float) if rotation is not None else k
        theta, phi, _, _ = _spherical_basis(k_ant)
        et = _bilinear(self.e_theta, self.theta_rad, self.phi_rad, theta, phi)
        ep = _bilinear(self.e_phi, self.theta_rad, self.phi_rad, theta, phi)
        # lift onto the world-frame local spherical basis at the true k
        _, _, th_hat, ph_hat = _spherical_basis(k)
        return et[:, None] * th_hat + ep[:, None] * ph_hat


def _bilinear(
    grid: np.ndarray, theta_ax: np.ndarray, phi_ax: np.ndarray, theta: np.ndarray, phi: np.ndarray
) -> np.ndarray:
    """Bilinear sample of a (n_phi, n_theta) grid at query (theta, phi)."""
    th0, dth, nth = theta_ax[0], theta_ax[1] - theta_ax[0], theta_ax.size
    ph0, dph, nph = phi_ax[0], phi_ax[1] - phi_ax[0], phi_ax.size
    ft = np.clip((theta - th0) / dth, 0, nth - 1)
    fp = (phi - ph0) / dph
    it0 = np.clip(np.floor(ft).astype(int), 0, nth - 2)
    it1 = it0 + 1
    wt = ft - it0
    ip0 = np.mod(np.floor(fp).astype(int), nph)
    ip1 = np.mod(ip0 + 1, nph)
    wp = fp - np.floor(fp)
    g00, g01 = grid[ip0, it0], grid[ip0, it1]
    g10, g11 = grid[ip1, it0], grid[ip1, it1]
    g0 = g00 * (1 - wt) + g01 * wt
    g1 = g10 * (1 - wt) + g11 * wt
    return g0 * (1 - wp) + g1 * wp


def make_rx_response(kind: str, freq_hz: float, *, axis=(0.0, 0.0, 1.0), npz_path=None, rotation=None):
    """Return a callable ``k_hat -> C_R (N, 3) complex`` for a named UE antenna.

    ``kind`` is one of ``vertical`` (the legacy unit-gain reference),
    ``dipole`` (analytic, as AEGIS MIMO), ``patch``, ``isotropic``, or
    ``measured`` (load ``npz_path``, the GOLIAT handset free-space pattern).
    """
    if kind == "vertical":
        ref = np.array([0.0, 0.0, 1.0])

        def resp(k_hat):
            k = np.asarray(k_hat, float)
            proj = ref[None, :] - (k @ ref)[:, None] * k
            n = np.linalg.norm(proj, axis=1, keepdims=True)
            fb = np.array([1.0, 0.0, 0.0])
            return np.where(n > 1e-12, proj / np.where(n > 0, n, 1.0), fb).astype(complex)

        return resp
    if kind == "dipole":
        return lambda k_hat: dipole_response(k_hat, axis, freq_hz).astype(complex)
    if kind in ("patch", "isotropic"):
        pat = AntennaPattern.synthetic(kind, freq_hz)
        return lambda k_hat: pat.response(k_hat, rotation)
    if kind == "measured":
        if npz_path is None:
            raise ValueError("measured pattern needs npz_path")
        pat = AntennaPattern.from_npz(npz_path, freq_hz)
        return lambda k_hat: pat.response(k_hat, rotation)
    raise ValueError(f"unknown UE antenna kind {kind!r}")
