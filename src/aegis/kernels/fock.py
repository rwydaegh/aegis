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

Impedance (lossy skin). The PEC eigenvalues shift to roots of the Leontovich
impedance-Fock equation ``Ai'(t) - q_F Ai(t) = 0``. The naive leading-Fock
parameter ``q_F = i m eta`` is NOT sufficient: against the exact dielectric
cylinder oracle it overshoots the hard pole by ~17% at body-scale ``kR`` (40 to
160), and the required correction is ``eta``-dependent (no clean rotation fixes
it, validated in studies/diffraction/HARD_POL_RESOLUTION.md). So
``fock_impedance_param`` solves the exact Leontovich pole (the validated truth in
studies/diffraction/poles.py) and returns the equivalent Airy-equation parameter
``q_F = Ai'(t*)/Ai(t*)`` evaluated at the exact pole's Airy argument ``t*``.
Feeding that ``q_F`` to the ``Ai'(t) - q_F Ai(t) = 0`` Newton solve in
``_impedance_roots`` recovers the exact dominant pole to three digits, while the
deeper poles (``n_terms > 1``) remain the documented leading-Fock approximation
(DECISIONS.md L6, dose-negligible deep shadow). The exact pole drifts with
``kR`` (the surface looks progressively softer to the hard creeping wave), so
``fock_q_hard_table`` tabulates ``q_eff(hard)`` over a log-``kR`` grid.

Sign convention: AEGIS stores ``n - i k`` (``e^{+i w t}``), so ``eta = 1/n`` has
``Im(eta) > 0`` (a passive inductive skin, ``eta = 0.192 + 0.076j`` at 28 GHz).
``Im(eta) < 0`` is a gain medium and is rejected.
"""

from __future__ import annotations

import functools
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, cast

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy import special as _special  # pyright: ignore[reportMissingTypeStubs]

if TYPE_CHECKING:
    from aegis.tissue.dielectric import TissueModel

from aegis._array_backend import erf, xp
from aegis.constants import C_0
from aegis.defaults import NUMERICAL_FLOOR

# scipy ships no py.typed marker, so basedpyright treats its members as untyped
# (the project config disables reportMissingTypeStubs globally; the strict kernels
# override re-escalates it, hence the import-line ignore above). Bind the module
# through Any so member access stays clean at this numerical boundary; concrete
# return types are recovered with explicit casts at each call site below.
special: Any = _special

_SQRT2 = np.sqrt(2.0)
_SQRT3 = np.sqrt(3.0)
# Newton iteration controls for the impedance-Fock root solve.
_NEWTON_MAXITER = 100
_NEWTON_TOL = 1e-13
# Log-spaced kR grid for the tabulated drifting hard eigenvalue (4 ... 2048).
_Q_HARD_GRID = 2.0 ** np.arange(2, 12)
# Shadow-clamp sharpness for smin(xi) ~ min(xi, 0). Large enough that the higher
# creeping poles stay bounded in the lit, small enough to keep smin C-infinity.
_SMIN_BETA = 8.0
# PEC hard surface-field gate value at the terminator, from the exact cylinder
# oracle at large kR (kR-independent). Pins the residue-amplitude scale.
_TERMINATOR_GATE_SQ_HARD = 0.488


def theta_from_mu(mu: ArrayLike) -> NDArray[np.floating]:
    """Signed terminator angle ``theta = arcsin(clip(mu, -1, 1))`` (radians)."""
    return xp.arcsin(xp.clip(mu, -1.0, 1.0))


def _impedance_roots(pol: str, q_F: complex, n_terms: int) -> NDArray[np.complexfloating]:
    """Creeping eigenvalues ``q_p`` from the Leontovich impedance-Fock equation.

    Newton-iterates the roots of ``Ai'(t) - q_F Ai(t) = 0`` from the PEC seeds
    (the signed ``Ai`` zeros for ``"soft"``, ``Ai'`` zeros for ``"hard"``) and
    returns ``q_p = -t``. The hard PEC limit is ``q_F = 0`` (Neumann: ``Ai'(t) = 0``);
    the soft PEC limit is ``q_F -> inf`` (Dirichlet: ``Ai(t) = 0``). The
    Newton derivative is ``d/dt[Ai'(t) - q_F Ai(t)] = t Ai(t) - q_F Ai'(t)``
    using ``Ai''(t) = t Ai(t)``.

    The dominant root (seeded from the first PEC zero) reproduces the exact
    Leontovich pole when ``q_F`` comes from :func:`fock_impedance_param`. The
    deeper roots are the leading-Fock approximation (DECISIONS.md L6).
    """
    a_soft, ap_hard, _, _ = special.ai_zeros(n_terms)
    seeds = a_soft if pol == "soft" else ap_hard  # signed (negative) zeros = PEC roots
    roots = np.empty(n_terms, dtype=complex)
    for p, t0 in enumerate(seeds):
        t = complex(t0)
        for _ in range(_NEWTON_MAXITER):
            ai, aip, _, _ = special.airy(t)
            df = t * ai - q_F * aip
            if df == 0:
                break
            step = (aip - q_F * ai) / df
            t = t - step
            if abs(step) < _NEWTON_TOL:
                break
        ai_c, aip_c, _, _ = special.airy(t)
        residual = abs(aip_c - q_F * ai_c)
        if residual > _NEWTON_TOL:
            raise RuntimeError(f"impedance-Fock Newton did not converge for pol={pol!r}, q_F={q_F}")
        roots[p] = -t  # q_p = -t
    return roots


def _leontovich_pole(eta: complex, ka: float, pol: str) -> complex:
    """Exact Leontovich creeping pole ``nu`` of the impedance cylinder (mpmath).

    Solves ``ka H_nu'(ka) - g H_nu(ka) = 0`` for the dominant complex order,
    seeded from the PEC pole, with the boundary admittance ``g = -i ka n``
    (soft / TM) or ``g = -i ka/n`` (hard / TE), ``n = 1/eta``. This is the
    validated truth (studies/diffraction/poles.py); the shadow power-decay slope
    is ``2 Im(nu)``. mpmath is imported lazily so the PEC path stays dependency
    free.
    """
    import mpmath as _mpmath  # pyright: ignore[reportMissingTypeStubs]

    # mpmath ships no type stubs; bind it through Any so its arbitrary-precision
    # members stay clean under the strict kernels ruleset.
    mp: Any = _mpmath

    with mp.workdps(30):
        n = mp.mpc(1.0 / complex(eta))
        if n.imag < 0:  # e^{-i w t}/outgoing-H^(1) convention needs Im(n) > 0
            n = mp.conj(n)
        ka_m = mp.mpf(float(ka))
        g = (-1j * ka_m * n) if pol == "soft" else (-1j * ka_m / n)

        def hankel_d(v: Any, z: Any) -> Any:  # H_nu'(z) via H_{v-1} - (v/z) H_v
            return mp.hankel1(v - 1, z) - (v / z) * mp.hankel1(v, z)

        m = (ka_m / 2) ** mp.mpf("0.3333333333333333")
        q1 = mp.mpf("2.338") if pol == "soft" else mp.mpf("1.019")
        guess = ka_m + mp.exp(1j * mp.pi / 3) * m * q1

        def residual(v: Any) -> Any:
            return ka_m * hankel_d(v, ka_m) - g * mp.hankel1(v, ka_m)

        nu = mp.findroot(residual, guess, tol=mp.mpf(10) ** -13)
        return complex(nu)


@functools.cache
def fock_impedance_param(eta: complex, kR: float, pol: str) -> complex:
    """Airy-equation parameter ``q_F`` for the lossy-skin (impedance) Fock pole.

    Calibrated to the exact Leontovich pole, not the leading-Fock estimate. The
    schematic ``q_F = i m eta`` (hard) / ``-i m/eta`` (soft), ``m = (kR/2)**(1/3)``,
    overshoots the hard pole by ~17% at body-scale ``kR`` and the correction is
    ``eta``-dependent (HARD_POL_RESOLUTION.md). So this solves the exact
    Leontovich pole ``nu`` (:func:`_leontovich_pole`), maps it to its Airy
    argument ``t* = -(nu - ka) / (m e^{i pi/3})``, and returns
    ``q_F = Ai'(t*)/Ai(t*)``. Fed to :func:`_impedance_roots`, this recovers the
    exact dominant eigenvalue ``q_p = -t*`` (pole reproduced to three digits).

    Sign convention: AEGIS stores ``n - i k``, so a physical skin has
    ``Im(eta) > 0``. ``Im(eta) < 0`` is a gain medium (corrupts the hard
    creeping wave) and raises ``ValueError``.
    """
    if pol not in {"soft", "hard"}:
        raise ValueError(f"pol must be 'soft' or 'hard', got {pol!r}")
    if eta == 0:
        raise ValueError(
            "eta = 0 is the exact PEC limit; the Leontovich impedance is undefined. Use q_F=None for the PEC Fock gate."
        )
    if eta.imag < -1e-12:
        raise ValueError(
            f"Im(eta) = {eta.imag:.4g} < 0 is a gain medium; pass eta = 1/n with the "
            "AEGIS n - i k convention (Im(eta) > 0, a passive inductive skin)."
        )
    m = (kR / 2.0) ** (1.0 / 3.0)
    nu = _leontovich_pole(eta, kR, pol)
    t_star = -(nu - kR) / (m * np.exp(1j * np.pi / 3.0))
    ai, aip, _, _ = special.airy(t_star)
    return complex(aip / ai)


@functools.cache
def _q_hard_table_cached(eta: complex) -> Callable[[ArrayLike], NDArray[np.floating]]:
    """Cached log-``kR`` interpolator of ``q_eff(hard)`` for surface admittance ``eta``."""
    q_eff = np.empty(_Q_HARD_GRID.shape, dtype=float)
    for i, kR in enumerate(_Q_HARD_GRID):
        q_F = fock_impedance_param(eta, float(kR), "hard")
        q_p = fock_eigenvalues("hard", q_F)[0]
        # q_eff = Im(nu)/[(kR/2)^{1/3} sin60] = Re(q_p) + Im(q_p)/sqrt3.
        q_eff[i] = q_p.real + q_p.imag / _SQRT3
    log_grid = np.log(_Q_HARD_GRID)

    def interp(kR: ArrayLike) -> NDArray[np.floating]:
        return cast(
            "NDArray[np.floating]",
            np.interp(np.log(np.asarray(kR, dtype=float)), log_grid, q_eff),
        )

    return interp


def fock_q_hard_table(band: TissueModel) -> Callable[[ArrayLike], NDArray[np.floating]]:
    """Cached interpolator ``q_hard(kR)`` for a tissue band's drifting hard eigenvalue.

    ``band`` is a :class:`~aegis.tissue.dielectric.TissueModel` instance exposing
    ``.n_complex`` (e.g. ``aegis.tissue.dielectric.SKIN_28GHZ``). Returns
    ``callable(kR) -> q_eff``, the effective hard creeping eigenvalue obtained by
    solving the impedance-Fock pole on a log-spaced ``kR`` grid (4 ... 2048) and
    linearly interpolating in ``log(kR)``. The eigenvalue drifts from the PEC-hard
    1.019 toward the PEC-soft 2.338 as ``kR`` grows. Cached per band (keyed on
    ``eta = 1/n``).

    Outside the grid (``kR < 4`` or ``kR > 2048``) the returned callable clamps
    to the nearest endpoint value (``np.interp`` hold-constant extrapolation).
    Body-scale ``kR`` (~6-90 at 28 GHz) sits well inside the grid.
    """
    n = band.n_complex
    if n == 0:
        raise ValueError(
            "band.n_complex = 0 is unphysical; the surface impedance is undefined. Use q_F=None for the PEC Fock gate."
        )
    return _q_hard_table_cached(complex(1.0 / n))


@functools.cache
def _fock_eigenvalues_cached(pol: str, q_F_key: tuple[float, float] | None, n_terms: int) -> tuple[complex, ...]:
    if pol not in {"soft", "hard"}:
        raise ValueError(f"pol must be 'soft' or 'hard', got {pol!r}")
    if q_F_key is not None:
        re, im = q_F_key
        return cast("tuple[complex, ...]", tuple(_impedance_roots(pol, complex(re, im), n_terms)))
    # PEC: magnitudes of the Airy / Airy' zeros.
    a_soft, ap_hard, _, _ = special.ai_zeros(n_terms)
    zeros = a_soft if pol == "soft" else ap_hard
    return cast("tuple[complex, ...]", tuple(np.abs(zeros).astype(complex)))


def fock_eigenvalues(pol: str, q_F: complex | None = None, n_terms: int = 3) -> NDArray[np.complexfloating]:
    """Creeping eigenvalues ``q_p`` for the given polarization.

    PEC (``q_F is None``): ``|zeros of Ai|`` for ``"soft"``, ``|zeros of Ai'|``
    for ``"hard"`` (the Dirichlet / Neumann Fock constants). Returns a complex
    array of length ``n_terms``.
    """
    # Quantize the real and imag parts separately; never round() a complex.
    q_F_key = None if q_F is None else (round(q_F.real, 4), round(q_F.imag, 4))
    return cast("NDArray[np.complexfloating]", np.asarray(_fock_eigenvalues_cached(pol, q_F_key, n_terms)))


@functools.cache
def _residue_amplitudes(pol: str, q_F_key: tuple[float, float] | None, n_terms: int) -> tuple[float, ...]:
    """PEC creeping residue magnitudes ``A_p`` (constructive, real, positive).

    soft: ``|1/Ai'(a_p)^2|``; hard: ``|1/[a_p Ai(a_p)^2]|``, ``a_p`` the signed
    Airy / Airy' zeros. Magnitudes give the constructive terminator the oracle
    shows (field above the knife-edge half value).

    ``q_F_key`` is ``None`` for PEC or a ``(round(re,4), round(im,4))`` tuple for
    an impedance surface. For the impedance case the same pol-appropriate
    residue magnitude is evaluated at the shifted (complex) roots ``t_p = -q_p``;
    this is the documented amplitude approximation (DECISIONS.md L6), exact in
    the PEC limit and continuous away from it. The dose-relevant quantity, the
    dominant-pole decay, is set by the eigenvalues (exact), not these amplitudes.
    """
    if q_F_key is not None:
        # Impedance roots t_p = -q_p; pol-appropriate residue magnitude at t_p.
        q_p = np.asarray(_fock_eigenvalues_cached(pol, q_F_key, n_terms))
        t = -q_p
        ai, aip, _, _ = special.airy(t)
        amp = 1.0 / (aip**2) if pol == "soft" else 1.0 / (t * ai**2)
        return cast("tuple[float, ...]", tuple(np.abs(amp)))
    a_soft, ap_hard, _, _ = special.ai_zeros(n_terms)
    if pol == "soft":
        _, aip, _, _ = special.airy(a_soft)
        amp = 1.0 / (aip**2)
    else:
        ai, _, _, _ = special.airy(ap_hard)
        amp = 1.0 / (ap_hard * ai**2)
    return cast("tuple[float, ...]", tuple(np.abs(amp)))


def _smin(xi: NDArray[np.floating] | float) -> NDArray[np.floating]:
    """Smooth ``min(xi, 0)``: identity deep shadow, saturates to 0 deep lit."""
    return cast("NDArray[np.floating]", -xp.logaddexp(0.0, -_SMIN_BETA * xi) / _SMIN_BETA)


def phi_lit(xi: ArrayLike) -> NDArray[np.floating]:
    """Lit transition ``0.5 (1 + erf(xi / sqrt2))``: 1 deep lit, 0 deep shadow.

    Uses the backend-aware ``erf`` (xi is real on every path, so a real erf
    suffices and JAX tracing is preserved).
    """
    return 0.5 * (1.0 + erf(xi / _SQRT2))


def _creep_series(
    xi: NDArray[np.floating] | float,
    pol: str,
    q_F: complex | None,
    n_terms: int,
) -> NDArray[np.complexfloating]:
    """Bounded creeping sum ``sum_p A_p exp(i nu_p smin(xi))`` (un-scaled, un-windowed)."""
    q = fock_eigenvalues(pol, q_F, n_terms)
    q_F_key = None if q_F is None else (round(q_F.real, 4), round(q_F.imag, 4))
    amp = np.asarray(_residue_amplitudes(pol, q_F_key, n_terms))
    nu = q * np.exp(-1j * np.pi / 3.0)
    xn = _smin(xi)
    total = 0.0
    for p in range(n_terms):
        total = total + amp[p] * xp.exp(1j * nu[p] * xn)
    return cast("NDArray[np.complexfloating]", total)


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
    xi: NDArray[np.floating] | float,
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
    return cast("NDArray[np.complexfloating]", window * _SCALE * _creep_series(xi, pol, q_F, n_terms))


def fock_g(
    xi: NDArray[np.floating] | float,
    pol: str,
    q_F: complex | None = None,
    n_terms: int = 3,
) -> NDArray[np.complexfloating]:
    """Uniform complex field gate ``g(xi) = phi_lit(xi) + psi_shadow(xi)``."""
    return cast("NDArray[np.complexfloating]", phi_lit(xi) + psi_shadow(xi, pol, q_F, n_terms))


def fock_gate(
    xi: NDArray[np.floating] | float,
    w_s: NDArray[np.floating] | float,
    w_p: NDArray[np.floating] | float,
    q_F_s: complex | None = None,
    q_F_h: complex | None = None,
) -> NDArray[np.complexfloating]:
    """Combined complex field gate ``w_s g_soft + w_p g_hard`` (the coherent gate)."""
    return cast(
        "NDArray[np.complexfloating]",
        w_s * fock_g(xi, "soft", q_F_s) + w_p * fock_g(xi, "hard", q_F_h),
    )


def w_nf(
    d1: NDArray[np.floating] | float | None,
    d2: NDArray[np.floating] | float | None,
    R: NDArray[np.floating] | float,
    theta: ArrayLike,
) -> NDArray[np.floating] | float:
    """Near-field width taper ``sqrt(d1 / (d1 + d2)) in (0, 1]``.

    The penumbra width scales with this factor (``sigma -> w_nf sigma``), so a
    finite source distance ``d1`` *narrows* the shadow transition relative to the
    plane wave; the gate divides the detour by it (``xi = m theta / w_nf``, see
    :func:`fock_local` and theory/unified/sec_08_distal_cmetric.tex eq:xi-distal).

    ``d2 = R * |theta|`` (geodesic arc from the terminator) when ``None``.
    Returns ``1.0`` in the far field (``d1 is None``).

    ``d1`` is clamped to ``>= 0`` (a source at or behind the surface gives
    ``w_nf = 0``, an infinitely sharp transition) and the denominator is floored,
    so the result is finite and NaN-free at the degenerate ``d1 == 0, theta == 0``
    point.
    """
    if d1 is None:
        return 1.0
    if d2 is None:
        d2 = R * xp.abs(theta)
    d1c = cast("NDArray[np.floating]", xp.maximum(d1, 0.0))
    return cast("NDArray[np.floating]", xp.sqrt(d1c / xp.maximum(d1c + d2, NUMERICAL_FLOOR)))


def fock_local(
    mu: ArrayLike,
    R: NDArray[np.floating] | float,
    freq_hz: float,
    w_s: NDArray[np.floating] | float,
    w_p: NDArray[np.floating] | float,
    q_F_s: complex | None = None,
    q_F_h: complex | None = None,
    d1: NDArray[np.floating] | float | None = None,
    d2: NDArray[np.floating] | float | None = None,
) -> NDArray[np.floating]:
    """Incoherent Fock gate (drop-in replacement for ``physical_gelu``).

    ``= max(mu, 0) |phi_lit(xi)|^2 + |w_s psi_soft + w_p psi_hard|^2``: the GO
    obliquity modulated by the lit penumbra, plus the polarization-combined
    creeping leakage (nonzero past the terminator). Real and ``>= 0``.
    """
    theta = theta_from_mu(mu)
    m = (xp.pi * freq_hz * R / C_0) ** (1.0 / 3.0)
    # The near-field factor is the penumbra WIDTH (sigma -> w_nf sigma), so it
    # DIVIDES the detour: a finite source distance narrows the transition (L13,
    # sec_08_distal_cmetric.tex eq:xi-distal). Floor it so a source on the
    # surface (w_nf -> 0) gives a sharp, finite, NaN-free gate.
    width = w_nf(d1, d2, R, theta)
    xi = m * theta / xp.maximum(width, NUMERICAL_FLOOR)
    creep = cast(
        "NDArray[np.complexfloating]",
        w_s * psi_shadow(xi, "soft", q_F_s) + w_p * psi_shadow(xi, "hard", q_F_h),
    )
    return cast(
        "NDArray[np.floating]",
        xp.maximum(mu, 0.0) * xp.abs(phi_lit(xi)) ** 2 + xp.abs(creep) ** 2,
    )


# ---------------------------------------------------------------------------
# Distal (self-shadowing) gate: one body part shadowing another
# ---------------------------------------------------------------------------

# Knife-edge Fresnel width constant. 1/sqrt(2 pi) gives C1 continuity with the
# local GeLU form; 1/sqrt(2) is the knife-exact option.
_K_DEFAULT = 1.0 / np.sqrt(2.0 * np.pi)


def fock_xi_distal(
    clearance: ArrayLike,
    R_occ: ArrayLike,
    freq_hz: float,
    w_nf: NDArray[np.floating] | float = 1.0,
) -> NDArray[np.floating]:
    """Distal Fock detour parameter (DECISIONS L13 / sec_08 eq:xi-distal).

    ``xi_d = m_occ c / w_nf`` with ``m_occ = (pi f R_occ / C_0)**(1/3)``. The
    signed angular clearance ``c > 0`` (clear) maps to the lit branch (NO minus
    sign), ``c < 0`` (shadowed) to the shadow branch. The near-field factor
    ``w_nf <= 1`` DIVIDES the detour, narrowing the penumbra at finite source
    distance.
    """
    m_occ = (xp.pi * freq_hz * xp.asarray(R_occ) / C_0) ** (1.0 / 3.0)
    return cast(
        "NDArray[np.floating]",
        m_occ * xp.asarray(clearance) / xp.maximum(w_nf, NUMERICAL_FLOOR),
    )


def distal_gate(
    clearance: ArrayLike,
    R_occ: ArrayLike,
    freq_hz: float,
    w_s: NDArray[np.floating] | float,
    w_p: NDArray[np.floating] | float,
    *,
    d1: NDArray[np.floating] | float,
    d2: NDArray[np.floating] | float,
    q_F_s: complex | None = None,
    q_F_h: complex | None = None,
    diffraction_model: str = "fock",
    K: float = _K_DEFAULT,
    n_terms: int = 5,
    boundary: str = "erf",
) -> NDArray[np.floating]:
    """Distal self-shadowing power gate (dual width: Fock curvature + knife Fresnel).

    The gate carries BOTH the Fock curvature width ``sigma_F ~ (k R_occ)^{-1/3}``
    and the knife-edge Fresnel width ``sigma_ke ~ (k L)^{-1/2}`` (sec_08
    prop:knife); the broader mechanism wins. The sharp-edge limit
    (``R_occ -> inf``) recovers the erf knife gate exactly, and ``lambda -> 0``
    recovers binary occlusion ``1[c > 0]``.

    For ``diffraction_model != "fock"`` (flat occluder, no creeping wave) the gate
    is the pure knife erf ``0.5 (1 + erf(c / sigma_ke))``, which is the old
    self-shadowing behaviour.

    ``n_terms`` defaults to 5 (not 3) for the distal creeping series: the distal
    deep shadow (a hand over the cheek) can carry real dose, where the 3-pole
    composite under-predicts by 3-4x (DECISIONS L6, sec_08 rem:distal-validity).
    The Fock branch is documented as a LOWER BOUND on deep cross-body shadow dose.
    A smooth-quadrature blend ``sigma_eff = sqrt(sigma_F^2 + sigma_ke^2)`` is a
    documented refinement; v1 uses a hard switch on the baked ``R_occ`` (constant
    in the pose gradient).
    """
    c = xp.asarray(clearance)
    R = xp.asarray(R_occ)
    lam = C_0 / freq_hz
    k = 2.0 * xp.pi / lam
    d2a = xp.asarray(d2)
    # near-field wavefront factor (double-where guard for d1 finite vs inf)
    d1a = xp.asarray(d1)
    d1_finite = xp.isfinite(d1a)
    d1s = xp.where(d1_finite, d1a, 1.0)
    width_nf = xp.where(d1_finite, xp.sqrt(d1s / xp.maximum(d1s + d2a, NUMERICAL_FLOOR)), 1.0)
    # knife Fresnel width (far field: K sqrt(lam / d2))
    sigma_ke_far = K * xp.sqrt(lam / xp.maximum(d2a, NUMERICAL_FLOOR))
    sigma_ke = xp.where(
        d1_finite,
        K * xp.sqrt(lam * d1s / xp.maximum(d2a * (d1s + d2a), NUMERICAL_FLOOR)),
        sigma_ke_far,
    )
    v_ke = 0.5 * (1.0 + erf(c / xp.maximum(sigma_ke, NUMERICAL_FLOOR)))
    if boundary == "knife_edge":
        v_ke = v_ke**2
    if diffraction_model != "fock":
        return cast("NDArray[np.floating]", v_ke)
    # Fock curvature branch
    sigma_f = 2.0 ** (5.0 / 6.0) * (k * R) ** (-1.0 / 3.0)
    xi_d = fock_xi_distal(c, R, freq_hz, width_nf)
    g_soft = fock_g(xi_d, "soft", q_F_s, n_terms)
    g_hard = fock_g(xi_d, "hard", q_F_h, n_terms)
    g_fock = w_s * xp.abs(g_soft) ** 2 + w_p * xp.abs(g_hard) ** 2
    # broader mechanism wins; R_occ is baked so the switch is constant in pose-grad
    return cast("NDArray[np.floating]", xp.where(sigma_f >= sigma_ke, g_fock, v_ke))
