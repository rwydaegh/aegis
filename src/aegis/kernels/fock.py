"""Fock diffraction transition gate (PEC soft/hard).

Pure, backend-agnostic, differentiable math for the smooth-convex-body
(Fock) shadow-edge transition that replaces AEGIS's heuristic GeLU gate. The
physics is validated against the exact PEC cylinder oracle
(studies/diffraction/cylinder_oracle.py); see studies/diffraction/DECISIONS.md
and FINDINGS.md.

Conventions (single, used everywhere):

- ``mu = n_hat . (-k_hat)``. The terminator (grazing locus) is ``mu = 0``.
- ``theta = arcsin(mu)`` is the signed angle from the terminator: ``theta > 0``
  lit, ``theta < 0`` into the geometric shadow.
- ``m = (kR/2)^{1/3} = (pi f R / c)^{1/3}`` is the Fock large parameter.
- ``xi = m * theta`` is the detour parameter (``xi > 0`` lit, ``xi < 0``
  shadow), O(1) across the penumbra (width ``Delta theta ~ (kR)^{-1/3}``).
- Creeping exponent ``nu_p = q_p * exp(-i pi/3)`` so ``|exp(i nu_p xi)|`` decays
  for ``xi < 0`` (the validated ``|psi|^2 ~ exp(-sqrt3 q_p |xi|)`` shadow law).

The gate is a uniform additive composite ``g(xi) = phi_lit(xi) +
psi_shadow(xi)``: GO deep lit, the creeping-wave tail deep shadow.

Closed-form construction (a documented engineering choice). The bare
creeping residue series ``sum_p A_p exp(i nu_p xi)`` is an asymptotic
*shadow* expansion: it grows exponentially for ``xi > 0`` and is meaningless
there. To make ``psi_shadow`` a single bounded, smooth, differentiable
function of ``xi`` we (a) evaluate the creeping phase at the shadow-clamped
argument ``smin(xi) ~ min(xi, 0)`` (a smooth minimum, so the term stays
bounded in the lit) and (b) taper it by the shadow window ``1 - phi_lit(xi)``
(so it vanishes in the deep lit). In the deep shadow both reduce to the
identity, recovering the exact creeping series and its ``sqrt3 q_p`` decay law.

The residue amplitudes use the PEC magnitudes (soft ``|1/Ai'(a_p)^2|``, hard
``|1/[a_p Ai(a_p)^2]|``, ``a_p`` the signed Airy zeros); the constructive sign
matches the oracle, whose surface field at the terminator (~0.70 of GO,
``|g(0)|^2 ~ 0.49``) sits *above* the knife-edge half value. A single shared
Fock prefactor ``_SCALE`` is pinned so the hard terminator value
``|fock_g(0, "hard")|^2`` matches the exact PEC cylinder oracle (~0.488,
kR-independent); soft shares the prefactor (same Fock Green's-function
calculus). This is pinned to the oracle in tests/test_fock.py, not assumed.

Impedance (lossy skin) is a later task: the ``q_F`` parameters are accepted but
not yet implemented (PEC only here).
"""

from __future__ import annotations

import functools

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy import special

from aegis._array_backend import erf, xp
from aegis.constants import C_0
from aegis.defaults import NUMERICAL_FLOOR

_SQRT2 = np.sqrt(2.0)
# Shadow-clamp sharpness for smin(xi) ~ min(xi, 0). Large enough that the higher
# creeping poles stay bounded in the lit, small enough to keep smin C-infinity.
_SMIN_BETA = 8.0
# PEC hard surface-field gate value at the terminator, from the exact cylinder
# oracle at large kR (kR-independent). Pins the residue-amplitude scale.
_TERMINATOR_GATE_SQ_HARD = 0.488


def theta_from_mu(mu: ArrayLike) -> NDArray[np.floating]:
    """Signed terminator angle ``theta = arcsin(clip(mu, -1, 1))`` (radians)."""
    return xp.arcsin(xp.clip(mu, -1.0, 1.0))


def _impedance_roots(pol: str, q_F: complex, n_terms: int) -> np.ndarray:
    """Creeping eigenvalues from the impedance-Fock equation (LATER task)."""
    raise NotImplementedError(
        "Impedance-corrected Fock eigenvalues (q_F != None) are a later task; PEC only for now (pass q_F=None)."
    )


@functools.cache
def _fock_eigenvalues_cached(pol: str, q_F_key, n_terms: int) -> tuple:
    if pol not in {"soft", "hard"}:
        raise ValueError(f"pol must be 'soft' or 'hard', got {pol!r}")
    if q_F_key is not None:
        re, im = q_F_key
        return tuple(_impedance_roots(pol, complex(re, im), n_terms))
    # PEC: magnitudes of the Airy / Airy' zeros.
    a_soft, ap_hard, _, _ = special.ai_zeros(n_terms)
    zeros = a_soft if pol == "soft" else ap_hard
    return tuple(np.abs(zeros).astype(complex))


def fock_eigenvalues(pol: str, q_F: complex | None = None, n_terms: int = 3) -> NDArray[np.complexfloating]:
    """Creeping eigenvalues ``q_p`` for the given polarization.

    PEC (``q_F is None``): ``|zeros of Ai|`` for ``"soft"``, ``|zeros of Ai'|``
    for ``"hard"`` (the Dirichlet / Neumann Fock constants). Returns a complex
    array of length ``n_terms``.
    """
    # Quantize the real and imag parts separately; never round() a complex.
    q_F_key = None if q_F is None else (round(q_F.real, 4), round(q_F.imag, 4))
    return np.asarray(_fock_eigenvalues_cached(pol, q_F_key, n_terms))


@functools.cache
def _residue_amplitudes(pol: str, q_F_key, n_terms: int) -> tuple:
    """PEC creeping residue magnitudes ``A_p`` (constructive, real, positive).

    soft: ``|1/Ai'(a_p)^2|``; hard: ``|1/[a_p Ai(a_p)^2]|``, ``a_p`` the signed
    Airy / Airy' zeros. Magnitudes give the constructive terminator the oracle
    shows (field above the knife-edge half value).

    ``q_F_key`` is ``None`` for PEC or a ``(round(re,4), round(im,4))`` tuple for
    impedance surface (not yet implemented).
    """
    # PEC only; impedance residues are a later task.
    if q_F_key is not None:
        raise NotImplementedError(
            "Impedance-corrected Fock residues (q_F != None) are a later task; PEC only for now (pass q_F=None)."
        )
    a_soft, ap_hard, _, _ = special.ai_zeros(n_terms)
    if pol == "soft":
        _, aip, _, _ = special.airy(a_soft)
        amp = 1.0 / (aip**2)
    else:
        ai, _, _, _ = special.airy(ap_hard)
        amp = 1.0 / (ap_hard * ai**2)
    return tuple(np.abs(amp))


def _smin(xi):
    """Smooth ``min(xi, 0)``: identity deep shadow, saturates to 0 deep lit."""
    return -xp.logaddexp(0.0, -_SMIN_BETA * xi) / _SMIN_BETA


def phi_lit(xi: ArrayLike) -> NDArray[np.floating]:
    """Lit transition ``0.5 (1 + erf(xi / sqrt2))``: 1 deep lit, 0 deep shadow.

    Uses the backend-aware ``erf`` (xi is real on every path, so a real erf
    suffices and JAX tracing is preserved).
    """
    return 0.5 * (1.0 + erf(xi / _SQRT2))


def _creep_series(xi, pol: str, q_F, n_terms: int):
    """Bounded creeping sum ``sum_p A_p exp(i nu_p smin(xi))`` (un-scaled, un-windowed)."""
    q = fock_eigenvalues(pol, q_F, n_terms)
    q_F_key = None if q_F is None else (round(q_F.real, 4), round(q_F.imag, 4))
    amp = np.asarray(_residue_amplitudes(pol, q_F_key, n_terms))
    nu = q * np.exp(-1j * np.pi / 3.0)
    xn = _smin(xi)
    total = 0.0
    for p in range(n_terms):
        total = total + amp[p] * xp.exp(1j * nu[p] * xn)
    return total


def _solve_scale() -> float:
    """Pin the shared Fock prefactor to the hard terminator oracle value.

    Solve ``|phi_lit(0) + (1 - phi_lit(0)) * scale * S0|^2 = target`` for the
    real positive ``scale``, with ``S0`` the hard creeping sum at the
    terminator. NumPy-only (a constant computed once at import).
    """
    s0 = complex(_creep_series(np.array(0.0), "hard", None, 3))
    w0 = 0.5  # 1 - phi_lit(0)
    phi0 = 0.5
    a = (w0 * abs(s0)) ** 2
    b = 2.0 * phi0 * w0 * s0.real
    c = phi0**2 - _TERMINATOR_GATE_SQ_HARD
    disc = b * b - 4.0 * a * c
    return float((-b + np.sqrt(disc)) / (2.0 * a))


_SCALE = _solve_scale()


def psi_shadow(
    xi: ArrayLike,
    pol: str,
    q_F: complex | None = None,
    n_terms: int = 3,
) -> NDArray[np.complexfloating]:
    """Shadow creeping contribution: 0 deep lit, ``sum_p A_p exp(i nu_p xi)`` deep shadow.

    ``= (1 - phi_lit(xi)) * scale * sum_p A_p exp(i nu_p smin(xi))``. In the deep
    shadow (``xi << 0``) the window and clamp are the identity, so this reduces
    to the exact creeping residue series with the ``sqrt3 q_p`` decay law.
    """
    window = 1.0 - phi_lit(xi)
    return window * _SCALE * _creep_series(xi, pol, q_F, n_terms)


def fock_g(
    xi: ArrayLike,
    pol: str,
    q_F: complex | None = None,
    n_terms: int = 3,
) -> NDArray[np.complexfloating]:
    """Uniform complex field gate ``g(xi) = phi_lit(xi) + psi_shadow(xi)``."""
    return phi_lit(xi) + psi_shadow(xi, pol, q_F, n_terms)


def fock_gate(
    xi: ArrayLike,
    w_s: ArrayLike,
    w_p: ArrayLike,
    q_F_s: complex | None = None,
    q_F_h: complex | None = None,
) -> NDArray[np.complexfloating]:
    """Combined complex field gate ``w_s g_soft + w_p g_hard`` (the coherent gate)."""
    return w_s * fock_g(xi, "soft", q_F_s) + w_p * fock_g(xi, "hard", q_F_h)


def w_nf(
    d1: ArrayLike | None,
    d2: ArrayLike | None,
    R: float,
    theta: ArrayLike,
) -> NDArray[np.floating] | float:
    """Near-field width taper ``sqrt(d1 / (d1 + d2))``.

    ``d2 = R * |theta|`` (geodesic arc from the terminator) when ``None``.
    Returns ``1.0`` in the far field (``d1 is None``).

    A floor is applied to the denominator to avoid 0/0 at the degenerate
    ``d1 == 0, theta == 0`` point.
    """
    if d1 is None:
        return 1.0
    if d2 is None:
        d2 = R * xp.abs(theta)
    return xp.sqrt(d1 / xp.maximum(d1 + d2, NUMERICAL_FLOOR))


def fock_local(
    mu: ArrayLike,
    R: float,
    freq_hz: float,
    w_s: ArrayLike,
    w_p: ArrayLike,
    q_F_s: complex | None = None,
    q_F_h: complex | None = None,
    d1: ArrayLike | None = None,
    d2: ArrayLike | None = None,
) -> NDArray[np.floating]:
    """Incoherent Fock gate (drop-in replacement for ``physical_gelu``).

    ``= max(mu, 0) |phi_lit(xi)|^2 + |w_s psi_soft + w_p psi_hard|^2``: the GO
    obliquity modulated by the lit penumbra, plus the polarization-combined
    creeping leakage (nonzero past the terminator). Real and ``>= 0``.
    """
    theta = theta_from_mu(mu)
    m = (xp.pi * freq_hz * R / C_0) ** (1.0 / 3.0)
    xi = m * theta * w_nf(d1, d2, R, theta)
    creep = w_s * psi_shadow(xi, "soft", q_F_s) + w_p * psi_shadow(xi, "hard", q_F_h)
    return xp.maximum(mu, 0.0) * xp.abs(phi_lit(xi)) ** 2 + xp.abs(creep) ** 2
