"""Verification, benchmark, and figures for the self-shadowing visibility gate.

Run with the project venv:
  .venv-nf/bin/python studies/self_shadowing/make_figures.py

Produces studies/self_shadowing/report/figs/*.pdf and a results.json summary.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import scipy.special as sp

import jax

jax.config.update("jax_enable_x64", True)
import jax.numpy as jnp  # noqa: E402

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "theory" / "scripts"))
sys.path.insert(0, str(HERE))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from faddeeva_jax import (  # noqa: E402
    weideman_coeffs,
    faddeeva,
    knife_edge_gate,
    gate_erf,
    gate_erf_squared,
)

try:
    from _plot_style import apply_monograph_style, fig_size_ieee

    apply_monograph_style()
    _SIZE = lambda aspect: fig_size_ieee(columns=1, aspect=aspect)  # noqa: E731
except Exception:  # pragma: no cover
    _SIZE = lambda aspect: (3.5, 3.5 * aspect)  # noqa: E731

FIGS = HERE / "report" / "figs"
FIGS.mkdir(parents=True, exist_ok=True)
C0 = 299_792_458.0
results: dict = {}

ELL, A = weideman_coeffs(48)
_fad = jax.jit(lambda z: faddeeva(z, ELL, A))
_gate_exact = jax.jit(lambda nu: knife_edge_gate(nu, ELL, A))


def save(fig, name):
    fig.tight_layout(pad=0.4)
    fig.savefig(FIGS / f"{name}.pdf")
    fig.savefig(FIGS / f"{name}.png", dpi=160)
    plt.close(fig)


# 1. Verify Faddeeva vs scipy.special.wofz over the complex plane.
def verify_faddeeva():
    re = np.linspace(-6, 6, 240)
    im = np.linspace(-6, 6, 240)
    R, I = np.meshgrid(re, im)
    Z = R + 1j * I
    w_ref = sp.wofz(Z)
    w_jax = np.asarray(_fad(jnp.asarray(Z)))
    err = np.abs(w_jax - w_ref)
    rel = err / (np.abs(w_ref) + 1e-300)
    results["faddeeva_max_abs_err"] = float(err.max())
    results["faddeeva_max_rel_err"] = float(rel.max())

    fig, ax = plt.subplots(figsize=_SIZE(0.85))
    pcm = ax.pcolormesh(R, I, np.log10(rel + 1e-18), shading="auto", cmap="viridis", vmin=-16, vmax=-10)
    ax.set_xlabel(r"$\mathrm{Re}\,z$")
    ax.set_ylabel(r"$\mathrm{Im}\,z$")
    ax.set_title(r"$\log_{10}$ relative error $|w_{\mathrm{JAX}}-w_{\mathrm{SciPy}}|/|w_{\mathrm{SciPy}}|$")
    fig.colorbar(pcm, ax=ax)
    save(fig, "faddeeva_error")


# 2. Verify the knife-edge gate vs scipy.special.fresnel.
def verify_gate():
    nu = np.linspace(-6, 6, 2000)
    s_sp, c_sp = sp.fresnel(nu)
    F = (1 + 1j) / 2.0 * ((0.5 - c_sp) - 1j * (0.5 - s_sp))
    gate_ref = np.abs(F) ** 2
    gate_jax = np.asarray(_gate_exact(jnp.asarray(nu)))
    results["gate_max_abs_err"] = float(np.abs(gate_jax - gate_ref).max())
    results["gate_at_zero"] = float(np.asarray(_gate_exact(jnp.asarray(0.0))))


# 3. The gate family in the dimensionless clearance s = c/sigma (s>0 lit).
def fig_gate_family():
    s = np.linspace(-4, 4, 1600)
    # exact power |F(nu)|^2 with nu = -sqrt(2) s (field-slope matched, s>0 -> lit).
    nu = -np.sqrt(2.0) * s
    g_exact = np.asarray(_gate_exact(jnp.asarray(nu)))
    g_erf = np.asarray(gate_erf(s))
    g_sq = np.asarray(gate_erf_squared(s))

    fig, ax = plt.subplots(figsize=_SIZE(0.72))
    ax.plot(s, g_exact, "k-", lw=1.4, label=r"exact $|F|^2$ (knife-edge)")
    ax.plot(s, g_sq, "C0--", lw=1.3, label=r"$[\frac{1}{2}(1+\mathrm{erf}\,s)]^2$ (-6 dB)")
    ax.plot(s, g_erf, "C3-.", lw=1.3, label=r"$\frac{1}{2}(1+\mathrm{erf}\,s)$ (default, -3 dB)")
    ax.axvline(0, color="0.6", lw=0.6)
    ax.axhline(0.25, color="0.8", lw=0.6, ls=":")
    ax.axhline(0.5, color="0.8", lw=0.6, ls=":")
    ax.set_xlabel(r"signed clearance $s=c/\sigma$  (lit $\to$)")
    ax.set_ylabel(r"power gate $V$")
    ax.set_ylim(-0.02, 1.25)
    ax.legend(loc="upper left")
    save(fig, "gate_family")


# 4. Shadow-side tail (deep-shadow leakage), log scale.
def fig_shadow_tail():
    s = np.linspace(-6, -0.2, 1200)  # shadow side
    nu = -np.sqrt(2.0) * s  # nu > 0
    g_exact = np.asarray(_gate_exact(jnp.asarray(nu)))
    g_erf = np.asarray(gate_erf(s))
    g_sq = np.asarray(gate_erf_squared(s))

    fig, ax = plt.subplots(figsize=_SIZE(0.72))
    ax.semilogy(-s, g_exact, "k-", lw=1.4, label=r"exact $|F|^2\sim \nu^{-2}$")
    ax.semilogy(-s, g_sq, "C0--", lw=1.3, label=r"erf$^2$ $\sim e^{-2s^2}$")
    ax.semilogy(-s, g_erf, "C3-.", lw=1.3, label=r"erf $\sim e^{-s^2}$")
    ax.set_xlabel(r"depth into shadow $|s|=|c|/\sigma$")
    ax.set_ylabel(r"power gate $V$ (leakage)")
    ax.set_ylim(1e-12, 1)
    ax.legend(loc="upper right")
    save(fig, "shadow_tail")
    # quantify under-prediction at |s|=4
    i = np.argmin(np.abs(-s - 4.0))
    results["leak_ratio_exact_over_erf_at_s4"] = float(g_exact[i] / max(g_erf[i], 1e-300))


# 5. Penumbra width vs frequency (sigma = K sqrt(lambda / d_occ)).
def fig_penumbra():
    K = 1.0 / np.sqrt(2.0 * np.pi)
    d_occ = 0.2  # m, typical body-part separation
    freqs = np.array([0.7e9, 2.45e9, 28e9])
    c_deg = np.linspace(-60, 60, 1200)
    c = np.deg2rad(c_deg)

    fig, ax = plt.subplots(figsize=_SIZE(0.72))
    for f, ls in zip(freqs, ["C0-", "C1--", "C2-."]):
        lam = C0 / f
        sigma = K * np.sqrt(lam / d_occ)
        V = 0.5 * (1 + sp.erf(c / sigma))
        ax.plot(c_deg, V, ls, lw=1.3, label=f"{f/1e9:.2f} GHz ($\\sigma$={np.rad2deg(sigma):.0f}$^\\circ$)")
    ax.axvline(0, color="0.6", lw=0.6)
    ax.set_xlabel(r"angular clearance $c$ [deg] (lit $\to$)")
    ax.set_ylabel(r"distal gate $V$")
    ax.set_title(r"penumbra width $\sigma=K\sqrt{\lambda/d_{\mathrm{occ}}}$, $d_{\mathrm{occ}}=0.2$ m")
    ax.legend(loc="upper left")
    save(fig, "penumbra_width")


# 6. sin(c) vs c: the small-angle question.
def fig_sinc():
    c_deg = np.linspace(0.1, 45, 1000)
    c = np.deg2rad(c_deg)
    rel = np.abs(c - np.sin(c)) / np.sin(c)
    fig, ax = plt.subplots(figsize=_SIZE(0.72))
    ax.plot(c_deg, 100 * rel, "k-", lw=1.4)
    ax.axvline(np.rad2deg(0.5), color="C3", ls="--", lw=1.0, label=r"int8 cap $0.5$ rad")
    for f, lab in [(2.45e9, "2.45 GHz"), (28e9, "28 GHz")]:
        sigma = (1 / np.sqrt(2 * np.pi)) * np.sqrt((C0 / f) / 0.2)
        ax.axvline(np.rad2deg(sigma), color="0.5", ls=":", lw=0.9)
        ax.text(np.rad2deg(sigma), 0.2, f"$\\sigma$({lab})", rotation=90, fontsize=6, va="bottom")
    ax.set_xlabel(r"clearance angle $c$ [deg]")
    ax.set_ylabel(r"relative error of $\sin c\approx c$ [%]")
    ax.legend(loc="upper left")
    save(fig, "sinc_error")
    results["sinc_rel_err_at_0p5rad_pct"] = float(100 * (0.5 - np.sin(0.5)) / np.sin(0.5))


# 7. Benchmark: scaling and per-element cost.
def benchmark():
    sizes = [10**k for k in range(3, 8)]
    reps = 7

    def timeit(fn, x):
        fn(x).block_until_ready() if hasattr(fn(x), "block_until_ready") else None
        ts = []
        for _ in range(reps):
            t0 = time.perf_counter()
            r = fn(x)
            if hasattr(r, "block_until_ready"):
                r.block_until_ready()
            ts.append(time.perf_counter() - t0)
        return float(np.median(ts))

    real_erf = jax.jit(lambda x: jax.scipy.special.erf(x))
    rng = np.random.default_rng(0)
    t_fad, t_erf, t_scipy = [], [], []
    for n in sizes:
        zc = jnp.asarray(rng.standard_normal(n) + 1j * rng.standard_normal(n))
        xr = jnp.asarray(rng.standard_normal(n))
        zc_np = np.asarray(zc)
        _fad(zc).block_until_ready()
        real_erf(xr).block_until_ready()
        t_fad.append(timeit(_fad, zc))
        t_erf.append(timeit(real_erf, xr))
        # scipy wofz (numpy, single-threaded reference)
        ts = []
        for _ in range(reps):
            t0 = time.perf_counter()
            sp.wofz(zc_np)
            ts.append(time.perf_counter() - t0)
        t_scipy.append(float(np.median(ts)))

    results["bench_sizes"] = sizes
    results["bench_t_faddeeva_jax"] = t_fad
    results["bench_t_real_erf_jax"] = t_erf
    results["bench_t_wofz_scipy"] = t_scipy
    big = -1
    results["faddeeva_over_real_erf_ratio"] = float(t_fad[big] / t_erf[big])
    results["ns_per_elem_faddeeva"] = float(t_fad[big] / sizes[big] * 1e9)
    results["ns_per_elem_real_erf"] = float(t_erf[big] / sizes[big] * 1e9)
    # slope of log-log (scaling exponent)
    lx = np.log10(sizes)
    for key, t in [("faddeeva", t_fad), ("real_erf", t_erf), ("wofz", t_scipy)]:
        slope = np.polyfit(lx, np.log10(t), 1)[0]
        results[f"scaling_exponent_{key}"] = float(slope)

    fig, ax = plt.subplots(figsize=_SIZE(0.72))
    ax.loglog(sizes, t_fad, "ko-", lw=1.2, ms=3, label="Faddeeva (JAX, jit)")
    ax.loglog(sizes, t_erf, "C0s--", lw=1.2, ms=3, label="real erf (JAX, jit)")
    ax.loglog(sizes, t_scipy, "C3^-.", lw=1.2, ms=3, label="wofz (SciPy)")
    ax.set_xlabel("array length $N$")
    ax.set_ylabel("median wall time [s]")
    ax.set_title("per-element cost and $O(N)$ scaling")
    ax.legend(loc="upper left")
    save(fig, "timing")


def main():
    verify_faddeeva()
    verify_gate()
    fig_gate_family()
    fig_shadow_tail()
    fig_penumbra()
    fig_sinc()
    benchmark()
    (HERE / "report").mkdir(exist_ok=True)
    (HERE / "results.json").write_text(json.dumps(results, indent=2))
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
