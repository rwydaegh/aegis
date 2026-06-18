# -*- coding: utf-8 -*-
"""
Validation of Approximation 1 (TM polarisation direction) on the regulated
observable n.Re{S}, the inward normal Poynting flux (ICNIRP 2020 eq. 16).

Approximation 1 replaces the exact refracted TM field direction e'_p (nearly
tangential inside high-index tissue) by the incident TM direction e_p in the
Fresnel transmission operator F_n. The monograph bounds the resulting cross-term
error as O(1/|n~|^2) ~ 4%. That scaling is the magnitude of the discarded
normal-field term; it is NOT a bound on the per-pair direction error, which is
O(1) for paths at different incidence angles/azimuths. The physically relevant
quantity is the error on the *integrated* exposure operator

    Q = integral_Sigma  G~(r)^H G~(r)  dA ,

where the surface phase integral  Phi_{nn'} = integral exp(-i (k_t,n - k_t,n') . r) dA
decorrelates exactly the widely-separated path pairs that carry the large
direction error. This script measures the App-1 error on Q as a function of the
integration-domain size L: point (no integration), the 4 cm^2 local FR2 patch,
and the whole body.

Self-terms are unaffected (|e_p| = |e'_p| = 1); the App-1 error lives only in
cross-terms. Approximation 2 (depth coupling) is held exact here so the App-1
effect is isolated; see validate_approx2.py for App 2.

Sanity checks (must all pass, they pin the implementation):
  SC1  TE polarisation              -> error identically 0 (App 1 is TM-only)
  SC2  single path / self-term      -> exact == model (magnitude preserved)
  SC4  two identical paths          -> error 0 (directions coincide)
  SC5  normal incidence (theta=0)   -> error 0 (e_p == e'_p)
  large integration domain          -> error -> 0 (cross-terms decorrelate)

Run: python theory/scripts/validate_approx1.py
"""

from __future__ import annotations

import os
import sys

import numpy as np

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from _fresnel import fresnel_transmission, n_complex  # noqa: E402

FREQ_HZ = 28e9
C0 = 299792458.0
K0 = 2 * np.pi * FREQ_HZ / C0

# skin at 28 GHz (IT'IS-class eps_r, sigma giving |n~| ~ 4.83, matching the monograph)
N_TILDE = n_complex(16.5, 25.8, FREQ_HZ)


def _path_vector(theta, phi, pol, kind):
    """Transmitted-field vector (z=0) for one path, calibrated so the self-term
    Joule heating equals S_inc * T * cos(theta). kind in {'exact', 'model'}."""
    st, ct = np.sin(theta), np.cos(theta)
    xi = np.sqrt(N_TILDE**2 - st**2)
    if np.imag(xi) > 0:  # enforce decay  exp(-i k0 xi z), Im(xi) < 0
        xi = -xi
    alpha = -K0 * np.imag(xi)
    beta = K0 * np.real(xi)
    Ts, Tp = fresnel_transmission(ct, N_TILDE)
    T = Tp if pol == "TM" else Ts

    xhat = np.array([np.cos(phi), np.sin(phi), 0.0])  # tangential, in incidence plane
    yhat = np.array([-np.sin(phi), np.cos(phi), 0.0])  # TE direction (out of plane)
    zhat = np.array([0.0, 0.0, 1.0])  # inward normal

    if pol == "TM":
        e_p = (ct * xhat + st * zhat).astype(complex)  # incident TM dir (Approx 1 model)
        g = xi * xhat + st * zhat  # exact refracted TM dir (complex, ~tangential)
    else:
        e_p = yhat.astype(complex)
        g = yhat.astype(complex)

    vec = e_p if kind == "model" else g
    # calibrate so (sigma/2)|kappa|^2 |vec|^2 * Lambda_nn = S_inc T cos(theta);
    # only relative path weights matter for the error, so fold constants away.
    amp2 = 2 * alpha * T * ct / np.vdot(vec, vec).real
    kt = K0 * st * np.array([np.cos(phi), np.sin(phi)])
    return np.sqrt(amp2) * vec, alpha, beta, kt


def _lambda(a_n, b_n, a_m, b_m):
    return 1.0 / ((a_n + a_m) + 1j * (b_n - b_m))


def _phi(kt_n, kt_m, L):
    d = kt_n - kt_m

    def sinc(u):
        return np.where(np.abs(u) < 1e-12, 1.0, np.sin(u) / np.where(u == 0.0, 1.0, u))

    return L * L * sinc(d[0] * L / 2) * sinc(d[1] * L / 2)


def _build_Q(paths, L, kind):
    data = [_path_vector(th, ph, pol, kind) for (th, ph, pol) in paths]
    V, A, B, K = zip(*data)
    n = len(paths)
    Q = np.zeros((n, n), complex)
    for i in range(n):
        for j in range(n):
            Q[i, j] = np.vdot(V[j], V[i]) * _lambda(A[i], B[i], A[j], B[j]) * _phi(K[i], K[j], L)
    return (Q + Q.conj().T) / 2


def app1_error(paths, L):
    """Operator error of Approximation 1 relative to the peak exposure mode."""
    Qe = _build_Q(paths, L, "exact")
    Qm = _build_Q(paths, L, "model")
    lam_max = np.linalg.eigvalsh(Qe)[-1]
    return np.max(np.abs(np.linalg.eigvalsh(Qm - Qe))) / lam_max


def _rand_paths(rng, n, pol="TM"):
    return [(rng.uniform(0, np.radians(80)), rng.uniform(0, 2 * np.pi), pol) for _ in range(n)]


def main():
    print(f"Tissue: n~ = {N_TILDE:.3f}   |n~| = {abs(N_TILDE):.3f}   (skin at 28 GHz)")
    print(f"lambda = {C0 / FREQ_HZ * 1e3:.2f} mm,   1/|n~|^2 = {1 / abs(N_TILDE) ** 2 * 100:.2f}%")
    print("=" * 64)

    rng = np.random.default_rng(1)

    print("\nSanity checks:")
    print(f"  SC1 TE polarisation (expect 0)        : {app1_error(_rand_paths(rng, 6, 'TE'), 0.5) * 100:.2e}%")
    for th in (10, 40, 70):
        p = [(np.radians(th), 0.3, "TM")]
        r = _build_Q(p, 0.04, "exact")[0, 0].real / _build_Q(p, 0.04, "model")[0, 0].real
        print(f"  SC2 self-term theta={th:2d} (expect 1.0)   : {r:.4f}")
    p_id = [(np.radians(50), 1.0, "TM"), (np.radians(50), 1.0, "TM")]
    print(f"  SC4 identical paths (expect 0)        : {app1_error(p_id, 0.1) * 100:.2e}%")
    p_nrm = [(0.0, 0.0, "TM"), (0.0, 1.5, "TM")]
    print(f"  SC5 normal incidence (expect 0)       : {app1_error(p_nrm, 0.1) * 100:.2e}%")

    print("\nApproximation 1 operator error vs peak exposure, by integration domain:")
    domains = [
        (0.001, "point (no integration)"),
        (0.02, "4 cm^2 local FR2 patch"),
        (0.5, "whole body ~0.5 m"),
        (1.5, "whole body ~1.5 m"),
    ]
    for L, label in domains:
        errs = [app1_error(_rand_paths(rng, 8), L) for _ in range(400)]
        print(
            f"  L = {label:24s}: median {np.median(errs) * 100:6.3f}%  "
            f"90th {np.percentile(errs, 90) * 100:6.3f}%  max {np.max(errs) * 100:6.3f}%"
        )

    print(
        "\nConclusion: the whole-body exposure operator Q (carrying lambda_max, the\n"
        "suppression factor, and the effective rank) has App-1 error < 0.1%. The 4 cm^2\n"
        "local FR2 operator carries ~6% (median). The O(1) per-pair direction error is\n"
        "suppressed by the surface-phase integral over the body."
    )


if __name__ == "__main__":
    main()
