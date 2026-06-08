"""Unified spatial kernel with composable physics corrections.

Computes per-triangle S_ab from the general incoherent formula:

    S_ab = T(mu, q) * g(mu, sigma) @ power + T0 * (H/k) * g(mu, sigma)^2 @ power

where:
    T = T_avg + (q/2)*DeltaT  (with polarisation) or T_avg (without)
    g = the diffraction gate: ReLU(mu) ("none"), GELU(mu, sigma) ("gelu"),
        or the Fock smooth-convex-body gate ("fock")
    curvature term present or absent

See theory/composability_analysis.md for derivation and limiting cases.
"""

from __future__ import annotations

from typing import cast

import numpy as np
from numpy.typing import NDArray

from aegis._array_backend import JAX_AVAILABLE, jit, xp
from aegis.constants import C_0
from aegis.kernels._base import (
    fresnel_weights,
    incidence_geometry,
    physical_gelu,
    te_tm_power_weights,
)
from aegis.kernels.fock import fock_local

# Diffraction gate selector. ``"none"`` is exact ReLU, ``"gelu"`` is the legacy
# physical-GELU smoothing, ``"fock"`` is the smooth-convex-body (Fock) gate.
_DIFFRACTION_MODELS = ("none", "gelu", "fock")


def resolve_diffraction_model(
    diffraction: bool,
    diffraction_model: str | None,
) -> str:
    """Resolve the gate selector from the new string and the legacy bool.

    Precedence: an explicit ``diffraction_model`` always wins. When it is
    ``None`` the legacy ``diffraction`` bool is mapped to its historical
    meaning: ``True -> "gelu"`` (the physical-GELU smoothing this flag has always
    selected) and ``False -> "none"`` (exact ReLU).

    The Fock gate is reachable only by passing ``diffraction_model="fock"``
    explicitly, because it requires an in-plane radius (``fock_R``) that legacy
    bool callers do not supply. The engine selects Fock as its default and
    threads ``fock_R`` through (see the engine integration task); the kernel
    never guesses a radius.
    """
    if diffraction_model is not None:
        if diffraction_model not in _DIFFRACTION_MODELS:
            raise ValueError(f"diffraction_model must be one of {_DIFFRACTION_MODELS}, got {diffraction_model!r}")
        return diffraction_model
    return "gelu" if diffraction else "none"


# Maximum number of (M, N) elements before we split paths into chunks.
# The Fresnel path allocates multiple complex128 (M, N) intermediates
# inside ``fresnel_weights`` (``mu_complex``, ``xi``, ``r_s``, ``r_p``) plus
# a couple of transient complex arithmetic temporaries. Empirical peak is
# ~100 bytes per (M, N) element during the Fresnel step, so 10M elements
# corresponds to ~1 GB of resident memory — enough headroom for a 3 GB
# container running two Gunicorn workers without triggering the cgroup OOM
# killer (which surfaces as a 502 at the reverse proxy). Below this
# threshold the kernel runs unchunked (zero overhead).
_MAX_MN_ELEMENTS = 10_000_000


@jit(
    static_argnames=(
        "fresnel",
        "polarisation",
        "curvature",
        "diffraction_model",
        "q_F_s",
        "q_F_h",
    )
)
def _spatial_kernel_unbatched(
    normals: NDArray[np.floating],
    k_hat: NDArray[np.floating],
    power: NDArray[np.floating],
    n_tilde: complex | NDArray[np.complexfloating],
    T0: float,
    freq_hz: float,
    *,
    fresnel: bool = True,
    polarisation: bool = False,
    q: float | NDArray[np.floating] = 0.0,
    psi: NDArray[np.complexfloating] | None = None,
    curvature: bool = False,
    diffraction_model: str = "none",
    curvature_H: NDArray[np.floating] | None = None,
    fock_R: NDArray[np.floating] | None = None,
    q_F_s: complex | None = None,
    q_F_h: complex | None = None,
) -> NDArray[np.floating]:
    """Core spatial kernel operating on all paths at once.

    This is the inner computation. For large M*N, use ``spatial_kernel``
    which automatically chunks over paths to bound memory usage.
    """
    mu, mu_plus = incidence_geometry(normals, k_hat)

    # Physical per-(triangle, path) TE/TM power weights from the incident field.
    # These are shared by the Fresnel factor and the Fock gate, so compute them
    # once here (it is one of the most expensive ops in the kernel). ``polarisation``
    # implies ``fresnel`` (guarded in ``spatial_kernel``), so this condition matches
    # exactly when either consumer below needs the weights.
    use_psi = polarisation and psi is not None
    w_s_pol: NDArray[np.floating] | None = None
    w_p_pol: NDArray[np.floating] | None = None
    if use_psi:
        assert psi is not None  # narrowed by use_psi; makes the guard visible to the type checker
        w_s_pol, w_p_pol = te_tm_power_weights(normals, k_hat, psi)

    # Fresnel factor
    t_factor: float | NDArray[np.floating]
    if fresnel:
        T_s, T_p, T_avg = fresnel_weights(mu, n_tilde)
        if use_psi:
            # Physical per-(triangle, path) polarisation from the incident field.
            assert w_s_pol is not None
            assert w_p_pol is not None
            t_factor = w_s_pol * T_s + w_p_pol * T_p
        elif polarisation:
            # Legacy scalar/array TM-excess knob (no real polarisation state).
            DeltaT = T_p - T_s
            t_factor = T_avg + 0.5 * q * DeltaT
        else:
            t_factor = T_avg
    else:
        t_factor = T0  # constant, broadcasts over (M, N)

    # Activation gate: ReLU ("none"), GELU smoothing ("gelu"), or Fock ("fock").
    if diffraction_model == "none":
        g = mu_plus
    elif diffraction_model == "gelu":
        wavelength = C_0 / freq_hz
        assert curvature_H is not None, "diffraction_model='gelu' requires curvature_H"
        H_safe = xp.maximum(curvature_H, 0.0)
        sigma = xp.sqrt(xp.maximum(wavelength * H_safe / (4.0 * xp.pi), 1e-20))
        g = physical_gelu(mu, sigma)
    else:  # "fock"
        assert fock_R is not None, "diffraction_model='fock' requires fock_R"
        w_s: NDArray[np.floating] | float
        w_p: NDArray[np.floating] | float
        if use_psi:
            assert w_s_pol is not None
            assert w_p_pol is not None
            w_s, w_p = w_s_pol, w_p_pol
        else:
            w_s, w_p = 0.5, 0.5
        # Far-field radius is per-triangle (M,); reshape so m*theta broadcasts
        # against theta of shape (M, N). A per-path radius (M, N) is used as is.
        R = fock_R[:, None] if fock_R.ndim == 1 else fock_R
        g = fock_local(mu, R, freq_hz, w_s, w_p, q_F_s, q_F_h)

    sab = cast("NDArray[np.floating]", (t_factor * g) @ power)

    # Curvature correction: additive perturbative term
    if curvature:
        k = xp.maximum(2.0 * xp.pi * freq_hz / C_0, 1e-6)
        assert curvature_H is not None, "curvature=True requires curvature_H"
        H_for_curv = xp.maximum(curvature_H, 0.0)
        # einsum avoids two (M, N) intermediates (g**2 and H-scaled g**2)
        g_sq_power = xp.einsum("mn,mn,n->m", g, g, power)
        sab_curvature = T0 * (H_for_curv / k) * g_sq_power
        sab = cast("NDArray[np.floating]", sab + sab_curvature)

    return sab


def spatial_kernel(
    normals: NDArray[np.floating],
    k_hat: NDArray[np.floating],
    power: NDArray[np.floating],
    n_tilde: complex | NDArray[np.complexfloating],
    T0: float,
    freq_hz: float,
    *,
    fresnel: bool = True,
    polarisation: bool = False,
    q: float | NDArray[np.floating] = 0.0,
    psi: NDArray[np.complexfloating] | None = None,
    curvature: bool = False,
    diffraction: bool = False,
    diffraction_model: str | None = None,
    curvature_H: NDArray[np.floating] | None = None,
    fock_R: NDArray[np.floating] | None = None,
    q_F_s: complex | None = None,
    q_F_h: complex | None = None,
) -> NDArray[np.floating]:
    """Compute per-triangle S_ab with composable physics corrections.

    Automatically chunks over paths (N dimension) when M*N exceeds
    ``_MAX_MN_ELEMENTS`` to prevent out-of-memory on large scenes.
    The result is mathematically identical to the unchunked version
    because both the main term ``(T * g) @ power`` and the curvature
    einsum decompose as sums over independent path subsets.

    Parameters
    ----------
    normals : (M, 3) unit outward normals
    k_hat : (N, 3) incident directions
    power : (N,) per-path power density [W/m^2]
    n_tilde : complex refractive index
    T0 : normal-incidence transmission coefficient
    freq_hz : frequency [Hz]
    fresnel : use angle-dependent T_avg(mu) instead of constant T0
    polarisation : enable polarisation correction (requires fresnel=True)
    q : TM excess parameter (scalar or (N,) array), used if polarisation=True
        and ``psi`` is None (legacy knob)
    psi : (N, 3) complex incident polarisation. When given with
        polarisation=True, the physical per-(triangle, path) TE/TM split is
        used instead of the scalar ``q``.
    curvature : enable curvature correction (requires curvature_H)
    diffraction : legacy bool. Mapped to ``diffraction_model`` when the latter is
        None: True -> "gelu", False -> "none". An explicit ``diffraction_model``
        always wins.
    diffraction_model : gate selector "none" | "gelu" | "fock". "none" is exact
        ReLU, "gelu" is the legacy physical-GELU smoothing (requires curvature_H),
        "fock" is the smooth-convex-body gate (requires fock_R).
    curvature_H : (M,) twice mean curvature per triangle [1/m]
    fock_R : (M,) or (M, N) in-incidence-plane radius of curvature [m], required
        when diffraction_model="fock" (from geometry.curvature.fock_radius)
    q_F_s, q_F_h : Leontovich impedance-Fock parameters for the soft/hard
        creeping waves. None (default) selects the PEC eigenvalues.

    Returns
    -------
    sab : (M,) absorbed power density per triangle [W/m^2]
    """
    if polarisation and not fresnel:
        raise ValueError("polarisation correction requires fresnel=True")

    model = resolve_diffraction_model(diffraction, diffraction_model)

    if (curvature or model == "gelu") and curvature_H is None:
        raise ValueError("curvature_H is required when curvature=True or diffraction_model='gelu'")
    if model == "fock" and fock_R is None:
        raise ValueError("fock_R is required when diffraction_model='fock'")

    use_psi = polarisation and psi is not None

    M = normals.shape[0]
    N = k_hat.shape[0]

    # The psi polarisation path allocates the (M, N, 3) TE/TM bases, so it needs
    # roughly twice the transient memory of the scalar Fresnel path; halve the
    # chunking threshold accordingly.
    max_mn = _MAX_MN_ELEMENTS // 2 if use_psi else _MAX_MN_ELEMENTS

    # Fast path: small enough to run in one shot
    if max_mn >= M * N or JAX_AVAILABLE:
        sab = _spatial_kernel_unbatched(
            normals,
            k_hat,
            power,
            n_tilde,
            T0,
            freq_hz,
            fresnel=fresnel,
            polarisation=polarisation,
            q=q,
            psi=psi,
            curvature=curvature,
            diffraction_model=model,
            curvature_H=curvature_H,
            fock_R=fock_R,
            q_F_s=q_F_s,
            q_F_h=q_F_h,
        )
    else:
        # Chunked path: split along N to bound peak memory
        chunk_size = max(max_mn // M, 1)
        sab = np.zeros(M, dtype=np.float64)

        for start in range(0, N, chunk_size):
            end = min(start + chunk_size, N)
            k_chunk = k_hat[start:end]
            p_chunk = power[start:end]
            q_chunk: float | NDArray[np.floating] = q[start:end] if isinstance(q, np.ndarray) and q.ndim > 0 else q
            psi_chunk = psi[start:end] if psi is not None else None
            # fock_R only carries an N axis when per-path (M, N); a per-triangle
            # (M,) radius broadcasts across all paths and needs no slicing. The
            # explicit ``is not None`` keeps the subscript visible as safe.
            fock_R_chunk = fock_R[:, start:end] if fock_R is not None and fock_R.ndim == 2 else fock_R

            chunk_sab = _spatial_kernel_unbatched(
                normals,
                k_chunk,
                p_chunk,
                n_tilde,
                T0,
                freq_hz,
                fresnel=fresnel,
                polarisation=polarisation,
                q=q_chunk,
                psi=psi_chunk,
                curvature=curvature,
                diffraction_model=model,
                curvature_H=curvature_H,
                fock_R=fock_R_chunk,
                q_F_s=q_F_s,
                q_F_h=q_F_h,
            )
            sab = sab + chunk_sab

    # Clamp the final summed result. Clamping per-chunk would produce
    # chunk-size-dependent answers because partial sums can be negative while
    # the full sum is positive (or vice versa).
    if curvature or model != "none":
        sab = xp.maximum(sab, 0.0)

    return sab
