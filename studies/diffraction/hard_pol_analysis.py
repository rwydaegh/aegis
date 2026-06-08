# ruff: noqa: E731, B007, B023, B905, SIM108  (research script: lambdas in findroot, etc.)
"""Resolve the hard (p-pol / TE_z) deep-shadow decay contradiction.

This is a read-only analysis layer on top of cylinder_oracle.py and poles.py
(neither is modified). It adds:

  - complex_surface_field: the COMPLEX exterior surface field Psi(a, phi) for the
    exact lossy dielectric (the oracle returns only the real inward-Poynting
    Im(Psi conj Psi')); we need the complex field for pole extraction.
  - matrix_pencil: extract dominant complex orders nu directly from the exact
    shadow field by the matrix-pencil method (data-driven; no pole hunting).
  - dielectric poles via multi-seed findroot + classification (creeping vs
    interior-resonance vs surface-wave), with the PHYSICALLY CORRECT index.
  - residue reconstruction of the shadow field from the isolated pole(s).

Convention note (the crux): the oracle uses e^{-i w t} with outgoing H^(1), for
which a passive lossy medium MUST have Im(n) > 0. AEGIS's stored
SKIN_28GHZ.n_complex = 4.493 - 1.786j has Im(n) < 0 (engineering eps = eps' -
i sigma/w eps0). Feeding the stored value to the oracle models a GAIN cylinder
(Q_abs < 0, Q_sca > Q_sca_lossless). The physical index is the conjugate.
"""

from __future__ import annotations

import numpy as np
from scipy.special import h1vp, hankel1, jv, jvp

from studies.diffraction.cylinder_oracle import _log_deriv_J

try:
    import mpmath as mp
except ImportError:  # pragma: no cover
    mp = None


# ----------------------------------------------------------------------------
# Complex exterior surface field for the exact lossy dielectric cylinder.
# ----------------------------------------------------------------------------
def complex_surface_field(ka: float, n_complex: complex, phi: np.ndarray, pol: str):
    """Complex total field Psi(a, phi) = sum i^n (J_n + b_n H_n) e^{i n phi}.

    Same boundary admittance g as cylinder_oracle.dielectric_cylinder_surface_field,
    but returns the complex field (needed for matrix-pencil pole extraction).
    """
    k0a = ka
    k1a = n_complex * ka
    N = int(ka + 14 * max(ka, 1.0) ** (1.0 / 3.0) + 25)
    ns = np.arange(-N, N + 1)
    absn = np.abs(ns)
    Jn0 = jv(ns, k0a)
    Jp0 = jvp(ns, k0a)
    Hn0 = hankel1(ns, k0a)
    Hp0 = h1vp(ns, k0a)
    Dn = _log_deriv_J(k1a, N)[absn]
    g = (k1a * Dn) if pol == "TM" else ((k0a / n_complex) * Dn)
    b = (g * Jn0 - k0a * Jp0) / (k0a * Hp0 - g * Hn0)
    e = np.exp(1j * np.outer(phi, ns))
    psi_c = (1j**ns) * (Jn0 + b * Hn0)
    return (psi_c[None, :] * e).sum(axis=1)


# ----------------------------------------------------------------------------
# Matrix-pencil: extract complex orders nu from a uniformly sampled shadow field.
# Single-terminator window: Psi(phi) ~ sum_p A_p e^{i nu_p (pi/2 - phi)}, so as a
# function of phi the modes are z_p = e^{-i nu_p dphi}; nu_p = i log(z_p)/dphi.
# ----------------------------------------------------------------------------
def matrix_pencil(y: np.ndarray, dphi: float, L: int | None = None, n_modes: int = 6):
    """Return (nu_p, amp_p) sorted by |amp| descending. y uniform in phi."""
    y = np.asarray(y, complex)
    M = len(y)
    if L is None:
        L = M // 3
    # Hankel data matrix
    Y = np.array([y[i : i + L + 1] for i in range(M - L)])  # (M-L) x (L+1)
    Y0 = Y[:, :-1]
    Y1 = Y[:, 1:]
    # rank-reduced generalized eigenvalues via SVD pencil
    U, s, Vh = np.linalg.svd(Y0, full_matrices=False)
    r = min(n_modes, np.sum(s > s[0] * 1e-10))
    Ur, sr, Vr = U[:, :r], s[:r], Vh[:r, :]
    A = (Ur.conj().T @ Y1 @ Vr.conj().T) / sr  # r x r
    z = np.linalg.eigvals(A)
    nu = 1j * np.log(z) / dphi
    # amplitudes by least squares: y[m] = sum_p amp_p z_p^m
    m = np.arange(M)
    V = z[None, :] ** m[:, None]
    amp, *_ = np.linalg.lstsq(V, y, rcond=None)
    order = np.argsort(-np.abs(amp))
    return nu[order], amp[order]


# ----------------------------------------------------------------------------
# Exact dielectric denominator D(nu) and its log-derivative, mpmath.
# Zeros of D are the scattering poles. g(nu) = (ka/n) J'/J (TE) or n ka J'/J (TM).
# ----------------------------------------------------------------------------
def _Hd(v, z):
    return mp.hankel1(v - 1, z) - (v / z) * mp.hankel1(v, z)


def _Jd(v, z):
    return mp.besselj(v - 1, z) - (v / z) * mp.besselj(v, z)


def denom(v, ka, pol, n):
    ka = mp.mpf(ka)
    D = _Jd(v, n * ka) / mp.besselj(v, n * ka)
    g = (n * ka * D) if pol == "TM" else ((ka / n) * D)
    return ka * _Hd(v, ka) - g * mp.hankel1(v, ka)


def find_poles_multiseed(ka, pol, n, seeds, tol=1e-20, dedup=0.05):
    """Find zeros of denom from many seeds; dedupe; keep Im(nu) in (-1, big)."""
    found = []
    for s in seeds:
        try:
            v = mp.findroot(lambda vv: denom(vv, ka, pol, n), mp.mpc(s), tol=tol)
        except Exception:
            continue
        vc = complex(v)
        # verify it is really a zero (not a spurious findroot stall)
        if abs(complex(denom(v, ka, pol, n))) > 1e-6 * max(1.0, abs(vc)):
            continue
        if any(abs(vc - f) < dedup for f in found):
            continue
        found.append(vc)
    return found


def classify_pole(nu, ka, n):
    """Distance to creeping ridge, nearest interior resonance J_nu(n ka)=0,
    and planar surface-wave order. Returns dict of diagnostics."""
    q1p = 1.019
    creep = ka + np.exp(1j * np.pi / 3) * (ka / 2) ** (1 / 3) * q1p
    sw = ka * complex(mp.sqrt(n**2 / (n**2 + 1)))
    # interior resonance: how close is J_nu(n ka) to zero, normalized
    Jval = complex(mp.besselj(mp.mpc(nu), n * ka))
    Jscale = complex(abs(mp.besselj(mp.mpf(round(nu.real)), abs(n) * ka))) + 1e-30
    return {
        "nu": nu,
        "pow_slope_2Imnu": 2 * nu.imag,
        "d_creep": abs(nu - creep),
        "d_surfwave": abs(nu - sw),
        "interior_resonance_proximity": abs(Jval) / Jscale,
    }


if __name__ == "__main__":
    from aegis.tissue.dielectric import SKIN_28GHZ as S

    n_phys = complex(np.conj(S.n_complex))  # PHYSICAL index, Im>0
    print(f"physical index n = {n_phys:.4f}  (conjugate of stored)")
    print("Matrix-pencil dominant nu extracted from the EXACT TE shadow field:")
    print(f"{'kR':>5} {'idx':>4} | {'dom nu (data)':>22} {'2Im(nu)=slope':>14} {'|amp|':>9}")
    for kR in (40.0, 80.0, 160.0):
        # near-upper-shadow window where one terminator dominates
        th = np.deg2rad(np.linspace(6, 50, 220))
        phi = np.pi / 2 - th
        dphi = phi[1] - phi[0]
        for tag, ncx in (("phys", n_phys), ("stored", complex(S.n_complex))):
            y = complex_surface_field(kR, ncx, phi, "TE")
            nu, amp = matrix_pencil(y, dphi, n_modes=6)
            # dominant physical (Im>0, near real axis ~ka) mode
            cand = [(v, a) for v, a in zip(nu, amp) if v.imag > -0.5 and 0.5 * kR < v.real < 1.3 * kR]
            v, a = (cand[0] if cand else (nu[0], amp[0]))
            print(f"{kR:>5.0f} {tag:>4} | {v.real:>10.3f}{v.imag:>+9.3f}j {2 * v.imag:>14.3f} {abs(a):>9.2e}")


def analytic_pole_inventory():
    """Find and classify exact-dielectric TE poles near the creeping ridge with
    the PHYSICAL index, and confirm the matrix-pencil pole is a true zero."""
    from aegis.tissue.dielectric import SKIN_28GHZ as S

    mp.mp.dps = 30
    n = mp.mpc(float(np.conj(S.n_complex).real), float(np.conj(S.n_complex).imag))
    print(f"\nAnalytic exact-dielectric TE poles, PHYSICAL index n={complex(n):.4f}")
    for ka in (40.0, 80.0, 160.0):
        q1p = 1.019
        creep = ka + np.exp(1j * np.pi / 3) * (ka / 2) ** (1 / 3) * q1p
        # seed a grid around the creeping ridge AND the second/third creeping modes
        seeds = []
        for j, q in enumerate([1.019, 3.248, 4.820]):  # Ai' zeros (hard ladder)
            seeds.append(ka + np.exp(1j * np.pi / 3) * (ka / 2) ** (1 / 3) * q)
        # plus a coarse complex grid to catch anything dominant we did not guess
        for dr in (-3, 0, 3, 6, 9):
            for di in (0.5, 2, 4, 7, 11):
                seeds.append(ka + dr + 1j * di)
        poles = find_poles_multiseed(ka, "TE", n, seeds)
        poles = [p for p in poles if -0.5 < p.imag < 25 and 0.8 * ka < p.real < 1.4 * ka]
        poles.sort(key=lambda v: v.imag)  # smallest Im = dominant in deep shadow
        print(f"\n kR={ka:.0f}  creeping-ridge guess nu1={creep:.3f}")
        print(f"   {'nu (zero of D)':>22} {'2Im=slope':>10} {'d_creep':>8} {'d_surfw':>8} {'J_nu(nka)/scale':>15}")
        for p in poles[:6]:
            c = classify_pole(p, ka, n)
            print(f"   {p.real:>10.3f}{p.imag:>+9.3f}j {c['pow_slope_2Imnu']:>10.3f}"
                  f" {c['d_creep']:>8.2f} {c['d_surfwave']:>8.2f} {c['interior_resonance_proximity']:>15.2e}")


if __name__ == "__main__" and "--inventory" in __import__("sys").argv:
    analytic_pole_inventory()


def residue_reconstruction():
    """Prove the isolated analytic poles reproduce the exact direct-sum field.

    Fit complex amplitudes (= residues) of the analytic poles to the exact
    complex field over a shadow window by least squares, using BOTH terminators
    (basis e^{i nu (pi/2 -+ phi)} by phi->-phi symmetry). Report reconstruction
    error with 1, 2, 3 poles.
    """
    from aegis.tissue.dielectric import SKIN_28GHZ as S

    mp.mp.dps = 30
    n = mp.mpc(float(np.conj(S.n_complex).real), float(np.conj(S.n_complex).imag))
    print("\nResidue (pole-sum) vs exact direct-sum field, EXACT dielectric TE, physical index:")
    print(f"{'kR':>5} | {'1-pole err':>11} {'2-pole err':>11} {'3-pole err':>11}")
    for ka in (40.0, 80.0, 160.0):
        # analytic poles (the creeping ladder), sorted by Im
        seeds = [ka + np.exp(1j * np.pi / 3) * (ka / 2) ** (1 / 3) * q for q in (1.019, 3.248, 4.820)]
        poles = find_poles_multiseed(ka, "TE", n, seeds)
        poles = sorted([p for p in poles if 0 < p.imag < 25], key=lambda v: v.imag)[:3]
        # shadow window (upper shadow), exact complex field
        th = np.deg2rad(np.linspace(8, 70, 400))
        phi = np.pi / 2 - th
        y = complex_surface_field(ka, complex(n), phi, "TE")
        errs = []
        for npol in (1, 2, 3):
            cols = []
            for p in poles[:npol]:
                cols.append(np.exp(1j * p * (np.pi / 2 - phi)))  # upper terminator
                cols.append(np.exp(1j * p * (np.pi / 2 + phi)))  # lower terminator
            B = np.array(cols).T
            coef, *_ = np.linalg.lstsq(B, y, rcond=None)
            yhat = B @ coef
            errs.append(np.linalg.norm(y - yhat) / np.linalg.norm(y))
        print(f"{ka:>5.0f} | {errs[0]:>11.2e} {errs[1]:>11.2e} {errs[2]:>11.2e}")


def final_table():
    """The deliverable numbers: exact-dielectric shadow decay with the PHYSICAL
    index, both pols, slope vs kR, ratio vs kR, scaling exponent. Cross-check
    measured slope against dominant-pole 2 Im(nu)."""
    from aegis.tissue.dielectric import SKIN_28GHZ as S
    from studies.diffraction.cylinder_oracle import dielectric_cylinder_surface_field

    nphys = complex(np.conj(S.n_complex))
    kRs = [20, 40, 80, 160, 320]
    th = np.deg2rad(np.linspace(8, 45, 400))
    phi = np.pi / 2 - th

    def meas_slope(kR, pol):
        P = np.abs(dielectric_cylinder_surface_field(kR, nphys, phi, pol))
        y = np.log(np.maximum(P, 1e-300))
        lo, hi = len(th) // 4, 3 * len(th) // 4
        return -np.polyfit(th[lo:hi], y[lo:hi], 1)[0]

    def pole_slope(kR, pol):
        mp.mp.dps = 30
        n = mp.mpc(nphys.real, nphys.imag)
        q1 = 2.338 if pol == "TM" else 1.019
        seeds = [kR + np.exp(1j * np.pi / 3) * (kR / 2) ** (1 / 3) * q for q in (q1, q1 + 2, q1 + 4)]
        poles = find_poles_multiseed(kR, pol, n, seeds)
        poles = [p for p in poles if 0 < p.imag < 30 and 0.8 * kR < p.real < 1.3 * kR]
        return 2 * min(p.imag for p in poles) if poles else float("nan")

    print("\n=== FINAL: exact lossy-skin cylinder, physical index, shadow power-decay slope ===")
    print(f"{'kR':>5} | {'TM meas':>8} {'TM pole':>8} | {'TE meas':>8} {'TE pole':>8} | {'TM/TE meas':>10}")
    tm_m, te_m = [], []
    for kR in kRs:
        a, b = meas_slope(kR, "TM"), pole_slope(kR, "TM")
        c, d = meas_slope(kR, "TE"), pole_slope(kR, "TE")
        tm_m.append(a)
        te_m.append(c)
        print(f"{kR:>5} | {a:>8.3f} {b:>8.3f} | {c:>8.3f} {d:>8.3f} | {a / c:>10.3f}")
    kk = np.log(np.array(kRs, float))
    print(f"\n  TM scaling exponent p (Fock=1/3): {np.polyfit(kk, np.log(tm_m), 1)[0]:.3f}")
    print(f"  TE scaling exponent p (Fock=1/3): {np.polyfit(kk, np.log(te_m), 1)[0]:.3f}")


def leontovich_check():
    """Confirm Leontovich (method A) tracks the exact creeping pole when BOTH use
    the physical index, and is ~sign-robust (reactance dominates)."""
    from aegis.tissue.dielectric import SKIN_28GHZ as S

    mp.mp.dps = 30
    nphys = mp.mpc(float(np.conj(S.n_complex).real), float(np.conj(S.n_complex).imag))
    nstor = mp.mpc(float(S.n_complex.real), float(S.n_complex.imag))

    def leont_denom(v, ka, n):
        ka = mp.mpf(ka)
        g = -1j * ka / n  # TE
        return ka * _Hd(v, ka) - g * mp.hankel1(v, ka)

    print("\nLeontovich TE pole 2Im(nu) (method A) vs exact-dielectric, physical vs stored index:")
    print(f"{'kR':>5} | {'Leont phys':>11} {'Leont stored':>13} | {'exact phys':>11}")
    for ka in (40.0, 80.0, 160.0):
        out = {}
        for tag, n in (("lp", nphys), ("ls", nstor)):
            g = ka + np.exp(1j * np.pi / 3) * (ka / 2) ** (1 / 3) * 1.019
            v = mp.findroot(lambda vv: leont_denom(vv, ka, n), mp.mpc(g), tol=1e-18)
            out[tag] = 2 * complex(v).imag
        seeds = [ka + np.exp(1j * np.pi / 3) * (ka / 2) ** (1 / 3) * 1.019]
        ex = find_poles_multiseed(ka, "TE", nphys, seeds)
        ex_s = 2 * min(p.imag for p in ex) if ex else float("nan")
        print(f"{ka:>5.0f} | {out['lp']:>11.3f} {out['ls']:>13.3f} | {ex_s:>11.3f}")


if __name__ == "__main__" and "--final" in __import__("sys").argv:
    residue_reconstruction()
    final_table()
    leontovich_check()


def asymptotic_scaling():
    """Local log-log exponent of the creeping-pole slope at large kR, to test
    whether TE tends to the Fock 1/3 (pre-asymptotic impedance drift) or stays
    steeper. Also compares to the PEC pole (clean 1/3) as a control."""
    from aegis.tissue.dielectric import SKIN_28GHZ as S

    mp.mp.dps = 30
    nphys = mp.mpc(float(np.conj(S.n_complex).real), float(np.conj(S.n_complex).imag))

    def pec_denom(v, ka, pol):
        ka = mp.mpf(ka)
        return mp.hankel1(v, ka) if pol == "TM" else _Hd(v, ka)

    def pole_slope(ka, pol, model):
        q1 = 2.338 if pol == "TM" else 1.019
        g = ka + np.exp(1j * np.pi / 3) * (ka / 2) ** (1 / 3) * q1
        if model == "PEC":
            f = lambda vv: pec_denom(vv, ka, pol)
        else:
            f = lambda vv: denom(vv, ka, pol, nphys)
        v = mp.findroot(f, mp.mpc(g), tol=1e-18)
        return 2 * complex(v).imag

    kRs = [80, 160, 320, 640, 1280, 2560]
    print("\nAsymptotic scaling: local exponent between consecutive kR (Fock=0.333):")
    print(f"{'kR range':>12} | {'TM skin':>8} {'TE skin':>8} | {'TM PEC':>8} {'TE PEC':>8}")
    sl = {(pol, m): [pole_slope(k, pol, m) for k in kRs]
          for pol in ("TM", "TE") for m in ("skin", "PEC")}
    for i in range(len(kRs) - 1):
        r = np.log(kRs[i + 1] / kRs[i])
        e = {key: np.log(sl[key][i + 1] / sl[key][i]) / r for key in sl}
        print(f"{kRs[i]:>5}->{kRs[i + 1]:>5} | {e[('TM','skin')]:>8.3f} {e[('TE','skin')]:>8.3f}"
              f" | {e[('TM','PEC')]:>8.3f} {e[('TE','PEC')]:>8.3f}")
    te = sl[("TE", "skin")]
    ratio = [sl[("TM", "skin")][i] / sl[("TE", "skin")][i] for i in range(len(kRs))]
    print("\n  slope values TE skin: " + ", ".join(f"{x:.2f}" for x in te))
    print("  ratio TM/TE skin: " + ", ".join(f"{x:.3f}" for x in ratio))


if __name__ == "__main__" and "--asym" in __import__("sys").argv:
    asymptotic_scaling()
