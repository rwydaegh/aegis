"""
Compute absorption directivity D(k̂) from a projected-area LUT and (optionally)
test spherical harmonic compression.

Task 02 (agent_tasks/02_compute_body_directivity_and_sh_compression.md)
"""

import scienceplots  # noqa: F401

import argparse
from dataclasses import dataclass
import math
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
import matplotlib
# Non-interactive backend (deliverable is the saved figure files).
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from _plot_style import apply_monograph_style, fig_size_textwidth
try:
    # SciPy traditionally provides sph_harm here, but some Windows/Python builds may omit it.
    from scipy.special import sph_harm as _scipy_sph_harm  # type: ignore

    def sph_harm(m: int, l: int, phi: np.ndarray, theta: np.ndarray) -> np.ndarray:
        return _scipy_sph_harm(m, l, phi, theta)

except Exception:  # pragma: no cover - platform/build dependent
    from scipy.special import lpmv

    def sph_harm(m: int, l: int, phi: np.ndarray, theta: np.ndarray) -> np.ndarray:
        """
        Complex spherical harmonics Y_l^m(θ,φ) with the same convention as SciPy's historical
        `scipy.special.sph_harm(m, l, phi, theta)`:

            Y_l^m(θ,φ) = N * P_l^m(cos θ) * exp(i m φ)

        where N = sqrt((2l+1)/(4π) * (l-m)!/(l+m)!) and P_l^m is the associated Legendre
        function (with Condon–Shortley phase, as in SciPy's lpmv).
        """
        m_int = int(m)
        l_int = int(l)
        if abs(m_int) > l_int:
            # By definition, Y_l^m = 0 for |m| > l.
            return np.zeros_like(np.asarray(theta, dtype=float), dtype=complex)

        phi = np.asarray(phi, dtype=float)
        theta = np.asarray(theta, dtype=float)
        x = np.cos(theta)

        if m_int < 0:
            mp = -m_int
            y_pos = sph_harm(mp, l_int, phi, theta)
            return ((-1) ** mp) * np.conj(y_pos)

        # Normalization factor (safe for small l; default maxL is small).
        num = math.factorial(l_int - m_int)
        den = math.factorial(l_int + m_int)
        N = math.sqrt((2 * l_int + 1) / (4 * math.pi) * (num / den))

        P = lpmv(m_int, l_int, x)  # includes Condon–Shortley phase
        return N * P * np.exp(1j * m_int * phi)


def _infer_phantom_name(lut_path: Path) -> str:
    """
    Heuristic: artifacts/body/<name>/A_perp_lut.npz -> <name>
    Otherwise fall back to parent directory name.
    """
    parts = [p.lower() for p in lut_path.parts]
    try:
        i = parts.index("body")
        if i + 1 < len(parts):
            return lut_path.parts[i + 1]
    except ValueError:
        pass
    return lut_path.parent.name or lut_path.stem


def _spherical_angles_from_k_hat(k_hat: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """
    Convert unit vectors to (theta, phi) angles.

    - theta: polar angle in [0, pi], measured from +z.
    - phi: azimuth in [-pi, pi], measured from +x toward +y.
    """
    k_hat = np.asarray(k_hat, dtype=float)
    if k_hat.ndim != 2 or k_hat.shape[1] != 3:
        raise ValueError(f"Expected k_hat shape (N,3); got {k_hat.shape}")

    norms = np.linalg.norm(k_hat, axis=1)
    if not np.all(norms > 0):
        raise ValueError("k_hat contains zero-length vectors")

    k = k_hat / norms[:, None]
    x, y, z = k[:, 0], k[:, 1], k[:, 2]

    z = np.clip(z, -1.0, 1.0)
    theta = np.arccos(z)
    phi = np.arctan2(y, x)
    return theta, phi


def _mollweide_scatter(phi: np.ndarray, theta: np.ndarray, values: np.ndarray, *,
                       title: str, out_path: Path) -> None:
    """
    Mollweide scatter plot on the sphere:
    - longitude = phi in [-pi, pi]
    - latitude = pi/2 - theta in [-pi/2, pi/2]
    """
    lon = np.asarray(phi)
    lat = np.pi / 2 - np.asarray(theta)
    v = np.asarray(values)

    fig = plt.figure(figsize=fig_size_textwidth(aspect=0.72))
    ax = fig.add_subplot(111, projection="mollweide")
    sc = ax.scatter(lon, lat, c=v, s=4.0, cmap="viridis", linewidths=0, alpha=0.95)
    ax.grid(True, alpha=0.25)
    # Prefer captions over in-plot titles in academic typesetting; keep a small title for PNG review.
    ax.set_title(title, pad=6, fontsize=11)
    cb = fig.colorbar(sc, ax=ax, orientation="horizontal", pad=0.10, fraction=0.065)
    cb.set_label(r"$D(\hat{k})$")
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.suffix.lower() == ".png":
        fig.savefig(out_path, dpi=250, bbox_inches="tight")
    else:
        fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)


def _histogram(values: np.ndarray, *, title: str, out_path: Path) -> None:
    v = np.asarray(values)
    fig, ax = plt.subplots(1, 1, figsize=fig_size_textwidth(aspect=0.58))
    ax.hist(v, bins=60, color="#377eb8", alpha=0.75, edgecolor="black", linewidth=0.4)
    ax.set_xlabel(r"$D(\hat{k})$")
    ax.set_ylabel("Count")
    ax.set_title(title)
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.suffix.lower() == ".png":
        fig.savefig(out_path, dpi=250, bbox_inches="tight")
    else:
        fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)


@dataclass(frozen=True)
class ShFitSummary:
    L: int
    n_coeff: int
    rms: float
    max_abs: float
    p99_abs: float


def _fit_sh_complex_ls(D: np.ndarray, theta: np.ndarray, phi: np.ndarray, L: int) -> np.ndarray:
    """
    Fit complex SH coefficients c_{l,m} (stacked in increasing l, then m=-l..l)
    via least squares to sampled values D(theta, phi).

    Uses scipy.special.sph_harm(m, l, phi, theta).
    """
    if L < 0:
        raise ValueError("L must be >= 0")

    D = np.asarray(D, dtype=float)
    theta = np.asarray(theta, dtype=float)
    phi = np.asarray(phi, dtype=float)

    # scipy's sph_harm expects phi in [0, 2pi); enforce periodic representative.
    phi_02pi = np.mod(phi, 2 * np.pi)

    cols = []
    for l in range(L + 1):
        for m in range(-l, l + 1):
            cols.append(sph_harm(m, l, phi_02pi, theta))

    Y = np.stack(cols, axis=1)  # (N, (L+1)^2), complex
    c, *_ = np.linalg.lstsq(Y, D.astype(complex), rcond=None)
    return c


def _eval_sh_complex(c: np.ndarray, theta: np.ndarray, phi: np.ndarray, L: int) -> np.ndarray:
    phi_02pi = np.mod(phi, 2 * np.pi)
    cols = []
    idx = 0
    for l in range(L + 1):
        for m in range(-l, l + 1):
            cols.append(sph_harm(m, l, phi_02pi, theta) * c[idx])
            idx += 1
    y = np.sum(np.stack(cols, axis=1), axis=1)
    return np.real(y)


def _sh_error_sweep(D: np.ndarray, theta: np.ndarray, phi: np.ndarray, maxL: int) -> list[ShFitSummary]:
    summaries: list[ShFitSummary] = []
    for L in range(maxL + 1):
        c = _fit_sh_complex_ls(D, theta, phi, L)
        D_hat = _eval_sh_complex(c, theta, phi, L)
        err = D_hat - D
        abs_err = np.abs(err)
        summaries.append(
            ShFitSummary(
                L=L,
                n_coeff=(L + 1) ** 2,
                rms=float(np.sqrt(np.mean(err**2))),
                max_abs=float(np.max(abs_err)),
                p99_abs=float(np.percentile(abs_err, 99.0)),
            )
        )
    return summaries


def _plot_sh_sweep(summaries: list[ShFitSummary], *, title: str, out_path: Path) -> None:
    Ls = np.array([s.L for s in summaries], dtype=int)
    # D is normalized to have mean ~ 1, so absolute error is numerically a relative error.
    # Plot as percent for interpretability.
    scale = 100.0
    rms = scale * np.array([s.rms for s in summaries], dtype=float)
    max_abs = scale * np.array([s.max_abs for s in summaries], dtype=float)
    p99_abs = scale * np.array([s.p99_abs for s in summaries], dtype=float)
    n_coeff = np.array([s.n_coeff for s in summaries], dtype=int)

    fig, ax = plt.subplots(1, 1, figsize=fig_size_textwidth(aspect=0.66))
    # Since D is normalized to mean ~1, these are relative errors; the y-axis is in %.
    ax.plot(Ls, rms, "o-", label="RMS", color="#4daf4a")
    ax.plot(Ls, p99_abs, "o-", label="99th percentile", color="#377eb8")
    ax.plot(Ls, max_abs, "o-", label="max", color="#e41a1c")
    ax.set_xlabel("Max SH degree L")
    if out_path.suffix.lower() == ".pdf":
        ax.set_ylabel(r"Relative error (\%)")
    else:
        ax.set_ylabel(r"Relative error (\%)")
    ax.set_title(title)
    ax.grid(True, alpha=0.3)

    ax2 = ax.twiny()
    ax2.set_xlim(ax.get_xlim())
    ax2.set_xticks(Ls)
    ax2.set_xticklabels([str(n) for n in n_coeff])
    ax2.set_xlabel(r"Number of coefficients $(L+1)^2$")

    ax.legend()
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.suffix.lower() == ".png":
        fig.savefig(out_path, dpi=250, bbox_inches="tight")
    else:
        fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Compute body absorption directivity D(k̂) from A_perp LUT.")
    parser.add_argument(
        "--mode",
        type=str,
        choices=["png", "pdf"],
        default="png",
        help="Output mode: png uses science+no-latex; pdf uses science+latex.",
    )
    parser.add_argument(
        "--figdir",
        type=str,
        default="figures",
        help="Directory to write output figures into.",
    )

    parser.add_argument(
        "--lut",
        type=str,
        default="artifacts/body/thelonious/A_perp_lut.npz",
        help="Path to projected-area LUT .npz containing arrays k_hat (N,3) and A_perp (N,).",
    )
    parser.add_argument(
        "--out",
        type=str,
        default=None,
        help="Output directory for any numeric outputs (default: same directory as LUT).",
    )
    parser.add_argument(
        "--maxL",
        type=int,
        default=6,
        help="Maximum SH degree for compression experiment (0 disables).",
    )
    args = parser.parse_args(argv)

    apply_monograph_style(mode=args.mode)

    lut_path = Path(args.lut)
    if not lut_path.exists():
        raise FileNotFoundError(f"LUT not found: {lut_path}")

    out_dir = Path(args.out) if args.out is not None else lut_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    phantom = _infer_phantom_name(lut_path)
    figures_dir = Path(args.figdir)
    figures_dir.mkdir(exist_ok=True)

    data = np.load(lut_path)
    if "k_hat" not in data or "A_perp" not in data:
        raise KeyError(f"{lut_path} must contain arrays 'k_hat' and 'A_perp'")
    k_hat = np.asarray(data["k_hat"], dtype=float)
    A_perp = np.asarray(data["A_perp"], dtype=float)

    if k_hat.ndim != 2 or k_hat.shape[1] != 3:
        raise ValueError(f"Expected k_hat shape (N,3); got {k_hat.shape}")
    if A_perp.ndim != 1 or A_perp.shape[0] != k_hat.shape[0]:
        raise ValueError(f"Expected A_perp shape (N,) matching k_hat; got {A_perp.shape}")

    if np.any(~np.isfinite(A_perp)):
        raise ValueError("A_perp contains non-finite values")
    if np.any(A_perp < 0):
        print("WARNING: A_perp contains negative values (unexpected). Proceeding anyway.")

    A_perp_mean = float(np.mean(A_perp))
    if A_perp_mean <= 0:
        raise ValueError(f"mean(A_perp) must be > 0; got {A_perp_mean}")

    D = A_perp / A_perp_mean

    # Scalar summaries
    idx_max = int(np.argmax(D))
    idx_min = int(np.argmin(D))
    D_max = float(D[idx_max])
    D_min = float(D[idx_min])
    p5, p50, p95 = np.percentile(D, [5, 50, 95]).astype(float)

    theta, phi = _spherical_angles_from_k_hat(k_hat)
    k_max = k_hat[idx_max] / np.linalg.norm(k_hat[idx_max])
    theta_max_deg = float(np.degrees(theta[idx_max]))
    phi_max_deg = float(np.degrees(phi[idx_max]))

    print("=== Body directivity from projected-area LUT ===")
    print(f"LUT: {lut_path}")
    print(f"Phantom: {phantom}")
    print(f"N directions: {len(D)}")
    print(f"mean(A_perp): {A_perp_mean:.6g}")
    print(f"mean(D): {float(np.mean(D)):.6f} (should be ~1.0)")
    print("")
    print(f"D_max: {D_max:.6f} at index {idx_max}")
    print(f"  k_hat_max (cartesian): [{k_max[0]: .6f}, {k_max[1]: .6f}, {k_max[2]: .6f}]")
    print(f"  (theta, phi) [deg]: ({theta_max_deg:.3f}, {phi_max_deg:.3f})")
    print(f"D_min: {D_min:.6f} at index {idx_min}")
    print(f"Percentiles: p5={p5:.6f}, p50={p50:.6f}, p95={p95:.6f}")

    # Plots
    ext = ".png" if args.mode == "png" else ".pdf"
    directivity_fig = figures_dir / f"body_directivity_{phantom}{ext}"
    if args.mode == "pdf":
        directivity_title = rf"Absorption directivity $D(\hat{{k}})$ ({phantom})"
    else:
        directivity_title = f"Absorption directivity D(k̂) — {phantom}"
    _mollweide_scatter(
        phi,
        theta,
        D,
        title=directivity_title,
        out_path=directivity_fig,
    )
    print(f"Saved: {directivity_fig}")

    hist_fig = figures_dir / f"body_directivity_hist_{phantom}{ext}"
    if args.mode == "pdf":
        hist_title = rf"Histogram of $D(\hat{{k}})$ ({phantom})"
    else:
        hist_title = f"Histogram of D(k̂) — {phantom}"
    _histogram(D, title=hist_title, out_path=hist_fig)
    print(f"Saved: {hist_fig}")

    # SH compression experiment
    if args.maxL and args.maxL > 0:
        maxL = int(args.maxL)
        summaries = _sh_error_sweep(D, theta, phi, maxL=maxL)

        # Report "how many coeffs for <5% RMS"
        target_rms = 0.05  # since mean(D)=1, this is 5% relative RMS
        L_hit = None
        for s in summaries:
            if s.rms <= target_rms:
                L_hit = s.L
                break

        print("")
        print("=== SH compression experiment ===")
        for s in summaries:
            print(
                f"L={s.L:2d}  coeffs={s.n_coeff:3d}  "
                f"RMS={s.rms:.5f}  p99_abs={s.p99_abs:.5f}  max_abs={s.max_abs:.5f}"
            )
        if L_hit is None:
            print(f"No L <= {maxL} achieved RMS <= {target_rms:.2%}.")
        else:
            n_coeff = (L_hit + 1) ** 2
            print(f"First L with RMS <= {target_rms:.2%}: L={L_hit} (coeffs={(L_hit+1)**2}).")
            print(f"Claim: need ~{n_coeff} SH coefficients for <5% RMS reconstruction error (on this sampler).")

        sh_fig = figures_dir / f"body_directivity_sh_fit_{phantom}{ext}"
        if args.mode == "pdf":
            sh_title = rf"SH fit error vs degree ({phantom})"
        else:
            sh_title = f"SH fit error vs degree — {phantom}"
        _plot_sh_sweep(summaries, title=sh_title, out_path=sh_fig)
        print(f"Saved: {sh_fig}")
    else:
        print("SH compression disabled (--maxL 0).")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

