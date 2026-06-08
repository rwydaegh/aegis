# ruff: noqa: E731, B007, B023, B905  (research script: lambdas in findroot, etc.)
"""Creeping/surface-wave poles of the cylinder, via complex-order roots.

The Watson-transform poles are the complex orders nu where the scattering
denominator vanishes. The dominant pole's Im(nu) is the exact shadow decay
rate (field ~ e^{i nu phi}, so |field| ~ e^{-Im(nu) phi}, power ~ e^{-2 Im(nu) phi}).

Three boundary models:
  - PEC soft  : H_nu(ka) = 0          (zeros of Ai -> q1=2.338)
  - PEC hard  : H_nu'(ka) = 0         (zeros of Ai' -> q1=1.019)
  - Leontovich: ka H_nu'(ka) - g H_nu(ka) = 0, g = -i ka n (TM) or -i ka/n (TE)
  - dielectric: same with g(nu) = n ka J_nu'(n ka)/J_nu(n ka)  (TM)
                            or (ka/n) J_nu'(n ka)/J_nu(n ka)   (TE)

The dielectric pole set is contaminated by interior resonances J_nu(n ka)=0,
so the physical creeping pole must be tracked by fine continuation in kR from
a well-separated start, with branch-jump rejection. Open question (see
FINDINGS): the exact-dielectric hard (p-pol) shadow decay appears far slower
than the Leontovich pole predicts; reconcile by isolating the true physical
dielectric pole.

Requires mpmath (complex-order Hankel/Bessel).
"""

from __future__ import annotations

import numpy as np

try:
    import mpmath as mp
except ImportError:  # pragma: no cover
    mp = None


def _setup(dps=30):
    from aegis.tissue.dielectric import SKIN_28GHZ as S

    mp.mp.dps = dps
    # e^{-iwt}/H^(1) convention needs Im(n) > 0; AEGIS stores n - ik, so take |Im|.
    n = mp.mpc(S.n_complex.real, abs(S.n_complex.imag))
    return n


def _Hd(v, z):
    return mp.hankel1(v - 1, z) - (v / z) * mp.hankel1(v, z)


def _Jd(v, z):
    return mp.besselj(v - 1, z) - (v / z) * mp.besselj(v, z)


def denom(v, ka, pol, model, n):
    ka = mp.mpf(ka)
    if model == "PEC":
        return mp.hankel1(v, ka) if pol == "TM" else _Hd(v, ka)
    if model == "leontovich":
        g = (-1j * ka * n) if pol == "TM" else (-1j * ka / n)
    elif model == "dielectric":
        D = _Jd(v, n * ka) / mp.besselj(v, n * ka)
        g = (n * ka * D) if pol == "TM" else ((ka / n) * D)
    else:
        raise ValueError(model)
    return ka * _Hd(v, ka) - g * mp.hankel1(v, ka)


def track_pole(pol, model, kR_grid, n=None, q1=None):
    """Track the dominant pole by fine continuation in kR. Returns list of (kR, nu)."""
    if n is None:
        n = _setup()
    if q1 is None:
        q1 = 2.338 if pol == "TM" else 1.019
    ka0 = mp.mpf(float(kR_grid[0]))
    guess = ka0 + mp.exp(1j * mp.pi / 3) * (ka0 / 2) ** mp.mpf("0.3333333") * q1
    tol = mp.mpf(10) ** -12
    v = mp.findroot(lambda vv: denom(vv, ka0, pol, model, n), guess, tol=tol)
    out = []
    for kt in kR_grid:
        vnew = mp.findroot(lambda vv: denom(vv, kt, pol, model, n), v, tol=tol)
        if out and abs(complex(vnew - v)) > 5:  # reject branch jump
            break
        v = vnew
        out.append((float(kt), complex(v)))
    return out


def main():
    if mp is None:
        print("mpmath not installed")
        return
    n = _setup()
    grid = np.arange(15, 326, 2.5)
    print(f"skin n={complex(n):.3f}, eta=1/n={complex(1/n):.4f}")
    for model in ("PEC", "leontovich", "dielectric"):
        print(f"\n== {model} ==")
        for pol in ("TM", "TE"):
            t = track_pole(pol, model, grid, n=n)
            kk = np.array([x[0] for x in t])
            sl = np.array([2 * x[1].imag for x in t])
            ok = sl > 0
            p = np.polyfit(np.log(kk[ok]), np.log(sl[ok]), 1)[0] if ok.sum() > 2 else float("nan")
            tag = "soft/s-pol" if pol == "TM" else "hard/p-pol"
            print(f"  {pol} ({tag}): {len(t)} pts kR={kk[0]:.0f}..{kk[-1]:.0f}, "
                  f"pow-slope {sl[0]:.1f}..{sl[-1]:.1f}, scaling p={p:.3f}")


if __name__ == "__main__":
    main()
