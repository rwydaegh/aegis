"""
SH Compression of Polarisation Response — Task 5
=================================================

Compare spherical harmonic compressibility of three body-response functions
on Thelonious at 28 GHz:

  D(k̂)     — normalised projected area (existing quantity)
  Ã_⊥(k̂)  — Fresnel-weighted projected area (unpolarised absorption)
  |B̃(k̂)|  — polarisation correction magnitude

All three are computed from scratch on the Thelonious mesh using brute-force
per-triangle Fresnel computation via _fresnel.py and _geom.py.  SH fitting
reuses the complex-LS approach from compute_body_directivity.py.

Figure name: sh_compression_polarization
Produces:    Figure for §10.5 of the monograph
Wave:        1 (independent)
"""

import scienceplots  # noqa: F401

import argparse
import math
import sqlite3
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from _plot_style import apply_monograph_style, fig_size_textwidth
from _fresnel import fresnel_transmission, n_complex as _n_complex_helper
from _geom import load_stl_binary, triangle_areas

# ---------------------------------------------------------------------------
# SH infrastructure (from compute_body_directivity.py)
# ---------------------------------------------------------------------------
try:
    from scipy.special import sph_harm as _scipy_sph_harm  # type: ignore

    def sph_harm(m: int, l: int, phi: np.ndarray, theta: np.ndarray) -> np.ndarray:
        return _scipy_sph_harm(m, l, phi, theta)

except Exception:
    from scipy.special import lpmv

    def sph_harm(m: int, l: int, phi: np.ndarray, theta: np.ndarray) -> np.ndarray:
        m_int = int(m)
        l_int = int(l)
        if abs(m_int) > l_int:
            return np.zeros_like(np.asarray(theta, dtype=float), dtype=complex)
        phi = np.asarray(phi, dtype=float)
        theta = np.asarray(theta, dtype=float)
        x = np.cos(theta)
        if m_int < 0:
            mp = -m_int
            y_pos = sph_harm(mp, l_int, phi, theta)
            return ((-1) ** mp) * np.conj(y_pos)
        num = math.factorial(l_int - m_int)
        den = math.factorial(l_int + m_int)
        N = math.sqrt((2 * l_int + 1) / (4 * math.pi) * (num / den))
        P = lpmv(m_int, l_int, x)
        return N * P * np.exp(1j * m_int * phi)


# ---------------------------------------------------------------------------
# IT'IS database — Gabriel 4-Cole-Cole (from mie_theory_corrected.py)
# ---------------------------------------------------------------------------
EPS_0 = 8.854187817e-12

DB_PATHS = [
    Path(__file__).parent.parent / "data" / "itis_v5.db",
    Path(__file__).parent / "itis_v5.db",
    Path(__file__).parent.parent / "EMT" / "itis_v5.db",
    Path(__file__).parent.parent / "PRL_brainstorm" / "itis_v5.db",
]


def _find_database() -> Path:
    for p in DB_PATHS:
        if p.exists():
            return p
    raise FileNotFoundError("Could not find itis_v5.db database")


def _get_gabriel_params(tissue_name: str = "Skin") -> dict:
    db_path = _find_database()
    conn = sqlite3.connect(str(db_path))
    c = conn.cursor()
    c.execute("SELECT prop_id FROM properties WHERE name = ?", ("Gabriel Parameters",))
    prop_result = c.fetchone()
    if not prop_result:
        conn.close()
        raise ValueError("No Gabriel Parameters found in database")
    prop_id = prop_result[0]
    c.execute(
        """SELECT m.mat_id, v.vals
           FROM materials m
           JOIN vectors v ON m.mat_id = v.mat_id
           WHERE m.name = ? AND v.prop_id = ?
           LIMIT 1""",
        (tissue_name, prop_id),
    )
    result = c.fetchone()
    conn.close()
    if not result:
        raise ValueError(f"No Gabriel params for tissue '{tissue_name}'")
    blob = result[1]
    if len(blob) < 14 * 8:
        raise ValueError("Unexpected blob length for Gabriel params")
    values = struct.unpack("d" * 14, blob[: 14 * 8])
    return {
        "ef": values[0],
        "del1": values[1], "tau1": values[2], "alf1": values[3],
        "del2": values[4], "tau2": values[5], "alf2": values[6],
        "del3": values[7], "tau3": values[8], "alf3": values[9],
        "del4": values[10], "tau4": values[11], "alf4": values[12],
        "sig": values[13],
    }


def _cole_cole_permittivity(freq_hz: float, params: dict) -> complex:
    omega = 2 * np.pi * freq_hz
    eps = complex(params["ef"], 0)
    tau_units = [1e-12, 1e-9, 1e-6, 1e-3]
    for i in range(4):
        delta = params[f"del{i+1}"]
        tau = params[f"tau{i+1}"] * tau_units[i]
        alpha = params[f"alf{i+1}"]
        if delta != 0 and tau != 0:
            denom = 1 + (1j * omega * tau) ** (1 - alpha)
            eps += delta / denom
    if params["sig"] != 0 and omega != 0:
        eps -= 1j * params["sig"] / (omega * EPS_0)
    return eps


def _get_n_complex_from_db(tissue_name: str, freq_hz: float) -> complex:
    """Complex refractive index from IT'IS 4-Cole-Cole model."""
    params = _get_gabriel_params(tissue_name)
    eps_c = _cole_cole_permittivity(freq_hz, params)
    import cmath
    n = cmath.sqrt(eps_c)
    if n.real < 0:
        n = -n
    return n


# ---------------------------------------------------------------------------
# Direction sampling (from compute_polarization_response_tables.py)
# ---------------------------------------------------------------------------
def fibonacci_sphere(n: int) -> np.ndarray:
    """Deterministic, approximately-uniform directions on S^2 (unit vectors)."""
    if n <= 0:
        raise ValueError("n must be positive")
    golden_ratio = (1 + np.sqrt(5.0)) / 2.0
    dirs = np.zeros((n, 3), dtype=float)
    for i in range(n):
        z = 1.0 - 2.0 * (i + 0.5) / n
        r = np.sqrt(max(0.0, 1.0 - z * z))
        phi = 2.0 * np.pi * i / golden_ratio
        dirs[i] = np.array([r * np.cos(phi), r * np.sin(phi), z], dtype=float)
    return dirs


def reference_frame_from_k(k_hat: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    k_hat = np.asarray(k_hat, dtype=float)
    k_hat = k_hat / np.linalg.norm(k_hat)
    up = np.array([0.0, 0.0, 1.0], dtype=float)
    if abs(np.dot(up, k_hat)) > 0.9:
        up = np.array([0.0, 1.0, 0.0], dtype=float)
    e1 = np.cross(up, k_hat)
    n1 = np.linalg.norm(e1)
    if n1 < 1e-12:
        up = np.array([1.0, 0.0, 0.0], dtype=float)
        e1 = np.cross(up, k_hat)
        n1 = np.linalg.norm(e1)
    e1 = e1 / n1
    e2 = np.cross(k_hat, e1)
    e2 = e2 / np.linalg.norm(e2)
    return e1, e2


# ---------------------------------------------------------------------------
# Compute A_perp, A_tilde, Bc, Bs per direction
# ---------------------------------------------------------------------------
def compute_all_tables(
    normals: np.ndarray,
    areas: np.ndarray,
    directions: np.ndarray,
    n_tilde: complex,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    For each direction, compute:
        A_perp(k̂) — geometric projected area  (sum of mu*A for illuminated triangles)
        A_tilde(k̂) — Fresnel-weighted projected area
        Bc(k̂), Bs(k̂) — polarisation correction components
    Returns (A_perp, A_tilde, Bc, Bs), each shape (n_dir,).
    """
    n_dir = directions.shape[0]
    A_perp = np.zeros(n_dir, dtype=float)
    A_tilde = np.zeros(n_dir, dtype=float)
    Bc = np.zeros(n_dir, dtype=float)
    Bs = np.zeros(n_dir, dtype=float)

    for i in range(n_dir):
        k_hat = directions[i]
        k_hat = k_hat / np.linalg.norm(k_hat)

        mu = np.sum(normals * (-k_hat), axis=1)
        mu_pos = np.clip(mu, 0.0, 1.0)
        illuminated = mu > 0

        # Geometric projected area
        A_perp[i] = float(np.sum(areas * mu_pos * illuminated.astype(float)))

        # Fresnel
        T_s, T_p = fresnel_transmission(mu_pos, n_tilde)
        T_avg = 0.5 * (T_s + T_p)
        dT = T_p - T_s

        w = areas * mu_pos * illuminated.astype(float)
        A_tilde[i] = float(np.sum(w * T_avg))

        e1, e2 = reference_frame_from_k(k_hat)

        # Local TE direction for each triangle
        kxn = np.cross(k_hat[None, :], normals)
        kxn_norm = np.linalg.norm(kxn, axis=1, keepdims=True)
        small = kxn_norm[:, 0] < 1e-12

        e_s = np.zeros_like(kxn)
        e_s[~small] = kxn[~small] / kxn_norm[~small]
        e_s[small] = e1[None, :]

        ca = e_s @ e1
        sa = e_s @ e2
        cos2a = ca * ca - sa * sa
        sin2a = 2.0 * ca * sa

        Bc[i] = float(np.sum(w * dT * cos2a))
        Bs[i] = float(np.sum(w * dT * sin2a))

        if (i + 1) % 500 == 0 or i == n_dir - 1:
            print(f"  direction {i+1}/{n_dir}")

    return A_perp, A_tilde, Bc, Bs


# ---------------------------------------------------------------------------
# SH fitting
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ShFitSummary:
    L: int
    n_coeff: int
    rms: float         # absolute RMS error
    max_abs: float
    p99_abs: float
    rms_rel: float     # RMS / mean(|data|)  → relative error


def _spherical_angles(k_hat: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    k = k_hat / np.linalg.norm(k_hat, axis=1, keepdims=True)
    z = np.clip(k[:, 2], -1.0, 1.0)
    theta = np.arccos(z)
    phi = np.arctan2(k[:, 1], k[:, 0])
    return theta, phi


def _fit_sh(D: np.ndarray, theta: np.ndarray, phi: np.ndarray, L: int) -> np.ndarray:
    phi_02pi = np.mod(phi, 2 * np.pi)
    cols = []
    for l in range(L + 1):
        for m in range(-l, l + 1):
            cols.append(sph_harm(m, l, phi_02pi, theta))
    Y = np.stack(cols, axis=1)
    c, *_ = np.linalg.lstsq(Y, D.astype(complex), rcond=None)
    return c


def _eval_sh(c: np.ndarray, theta: np.ndarray, phi: np.ndarray, L: int) -> np.ndarray:
    phi_02pi = np.mod(phi, 2 * np.pi)
    cols = []
    idx = 0
    for l in range(L + 1):
        for m in range(-l, l + 1):
            cols.append(sph_harm(m, l, phi_02pi, theta) * c[idx])
            idx += 1
    y = np.sum(np.stack(cols, axis=1), axis=1)
    return np.real(y)


def sh_error_sweep(
    data: np.ndarray, theta: np.ndarray, phi: np.ndarray, maxL: int
) -> List[ShFitSummary]:
    data_mean = float(np.mean(np.abs(data)))
    summaries = []
    for L in range(maxL + 1):
        c = _fit_sh(data, theta, phi, L)
        D_hat = _eval_sh(c, theta, phi, L)
        err = D_hat - data
        abs_err = np.abs(err)
        rms = float(np.sqrt(np.mean(err ** 2)))
        summaries.append(
            ShFitSummary(
                L=L,
                n_coeff=(L + 1) ** 2,
                rms=rms,
                max_abs=float(np.max(abs_err)),
                p99_abs=float(np.percentile(abs_err, 99.0)),
                rms_rel=rms / data_mean if data_mean > 0 else 0.0,
            )
        )
    return summaries


# ---------------------------------------------------------------------------
# Plotting
# ---------------------------------------------------------------------------
def plot_sh_compression(
    summaries_D: List[ShFitSummary],
    summaries_Atilde: List[ShFitSummary],
    summaries_Bmag: List[ShFitSummary],
    *,
    out_path: Path,
    mode: str = "png",
) -> None:
    """Single-panel figure: relative error vs SH degree for D, Ã_⊥, |B̃|."""
    pct = r"\%" if mode == "pdf" else "%"
    scale = 100.0  # convert fraction → percent

    Ls = np.array([s.L for s in summaries_D], dtype=int)

    # Use RMS relative error for each quantity
    rms_D = scale * np.array([s.rms_rel for s in summaries_D])
    rms_At = scale * np.array([s.rms_rel for s in summaries_Atilde])
    rms_Bm = scale * np.array([s.rms_rel for s in summaries_Bmag])

    fig, ax = plt.subplots(1, 1, figsize=fig_size_textwidth(aspect=0.65, scale=1.0))

    c_D = "#377eb8"    # blue
    c_At = "#4daf4a"   # green
    c_Bm = "#e41a1c"   # red

    if mode == "pdf":
        lab_D = r"$D(\hat{k})$ (directivity)"
        lab_At = r"$\tilde{A}_\perp(\hat{k})$ (unpolarised)"
        lab_Bm = r"$|\tilde{B}(\hat{k})|$ (pol.\ correction)"
    else:
        lab_D = "D(k̂) (directivity)"
        lab_At = "Ã_⊥(k̂) (unpolarised)"
        lab_Bm = "|B̃(k̂)| (pol. correction)"

    ax.semilogy(Ls, rms_D, "o-", color=c_D, label=lab_D, markersize=5)
    ax.semilogy(Ls, rms_At, "s-", color=c_At, label=lab_At, markersize=5)
    ax.semilogy(Ls, rms_Bm, "^-", color=c_Bm, label=lab_Bm, markersize=5)

    # 5% threshold line
    ax.axhline(y=5.0, color="gray", linestyle="--", linewidth=1.0, alpha=0.6)
    ax.text(0.3, 5.3, f"5{pct} threshold", fontsize=8, color="gray", alpha=0.7)

    # Mark where each crosses 5%
    crossings = {}  # L_cross -> [(name_display, color, rms_val)]
    if mode == "pdf":
        annot_names = [r"$D$", r"$\tilde{A}_\perp$", r"$|\tilde{B}|$"]
    else:
        annot_names = ["D", "Ã_⊥", "|B̃|"]
    for aname, summaries, color in zip(
        annot_names,
        [summaries_D, summaries_Atilde, summaries_Bmag],
        [c_D, c_At, c_Bm],
    ):
        rms_vals = [s.rms_rel * 100 for s in summaries]
        for s, rv in zip(summaries, rms_vals):
            if rv <= 5.0:
                crossings.setdefault(s.L, []).append((aname, color, rv))
                break

    for L_cross, items in crossings.items():
        if len(items) == 1:
            name, color, rv_at = items[0]
            ax.annotate(
                f"L = {L_cross}",
                xy=(L_cross, rv_at),
                xytext=(L_cross + 1.2, rv_at * 1.6),
                fontsize=8, color=color, fontweight="bold",
                arrowprops=dict(arrowstyle="->", color=color, lw=0.8),
            )
        else:
            # Multiple quantities cross at same L — combine label
            names = ", ".join(it[0] for it in items)
            avg_rv = np.mean([it[2] for it in items])
            ax.annotate(
                f"L = {L_cross}\n({names})",
                xy=(L_cross, avg_rv),
                xytext=(L_cross + 1.5, avg_rv * 2.5),
                fontsize=8, color="black", fontweight="bold",
                arrowprops=dict(arrowstyle="->", color="gray", lw=0.8),
            )

    ax.set_xlabel("Maximum SH degree $L$" if mode == "pdf" else "Maximum SH degree L")
    ax.set_ylabel(f"RMS relative error ({pct})")
    ax.set_xlim(-0.3, Ls[-1] + 0.3)
    ax.set_xticks(range(0, Ls[-1] + 1, 2))
    ax.grid(True, alpha=0.25)
    ax.legend(loc="upper right", frameon=True, fontsize=9)

    # Secondary x-axis: number of coefficients
    ax2 = ax.twiny()
    ax2.set_xlim(ax.get_xlim())
    tick_Ls = list(range(0, Ls[-1] + 1, 2))
    ax2.set_xticks(tick_Ls)
    ax2.set_xticklabels([str((L + 1) ** 2) for L in tick_Ls])
    if mode == "pdf":
        ax2.set_xlabel(r"Number of SH coefficients $(L+1)^2$")
    else:
        ax2.set_xlabel("Number of SH coefficients (L+1)²")

    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.suffix.lower() == ".png":
        fig.savefig(out_path, dpi=250, bbox_inches="tight")
    else:
        fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {out_path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Task 5: SH compression of polarisation response on Thelonious."
    )
    parser.add_argument(
        "--mode", choices=["png", "pdf"], default="png",
        help="Output mode (png for iteration, pdf for final).",
    )
    parser.add_argument(
        "--outdir", type=str, default=str(Path(__file__).parent.parent / "monograph" / "figures"),
        help="Directory for output figures.",
    )
    parser.add_argument(
        "--stl", type=str,
        default=str(Path(__file__).parent.parent / "data" / "thelonious.stl"),
        help="Path to STL mesh.",
    )
    parser.add_argument(
        "--n-dirs", type=int, default=2000,
        help="Number of fibonacci-sphere directions.",
    )
    parser.add_argument(
        "--maxL", type=int, default=15,
        help="Maximum SH degree to sweep.",
    )
    parser.add_argument(
        "--freq-ghz", type=float, default=28.0,
        help="Frequency in GHz.",
    )
    args = parser.parse_args(argv)

    apply_monograph_style(mode=args.mode)

    # 1. Load mesh
    stl_path = Path(args.stl)
    print(f"Loading mesh: {stl_path}")
    vertices, normals, centroids = load_stl_binary(str(stl_path))
    areas = triangle_areas(vertices)
    print(f"  {len(areas)} triangles, total area = {np.sum(areas):.6g} m²")

    # 2. Get tissue properties from IT'IS database
    freq_hz = args.freq_ghz * 1e9
    n_tilde = _get_n_complex_from_db("Skin", freq_hz)
    print(f"Skin at {args.freq_ghz} GHz: ñ = {n_tilde.real:.3f} - {-n_tilde.imag:.3f}j, |ñ| = {abs(n_tilde):.3f}")

    # 3. Sample directions
    n_dirs = args.n_dirs
    print(f"Sampling {n_dirs} fibonacci-sphere directions...")
    directions = fibonacci_sphere(n_dirs)

    # 4. Compute all response functions
    print("Computing A_perp, Ã_⊥, Bc, Bs for each direction...")
    A_perp, A_tilde, Bc, Bs = compute_all_tables(normals, areas, directions, n_tilde)

    # Derived quantities
    B_mag = np.sqrt(Bc ** 2 + Bs ** 2)  # |B̃|
    D = A_perp / np.mean(A_perp)         # normalised directivity

    # Print summaries
    print("\n=== Response function summaries ===")
    print(f"D(k̂):     mean={np.mean(D):.4f}  std={np.std(D):.4f}  min={np.min(D):.4f}  max={np.max(D):.4f}")
    print(f"Ã_⊥(k̂):  mean={np.mean(A_tilde):.6g}  std={np.std(A_tilde):.6g}")
    print(f"|B̃(k̂)|:  mean={np.mean(B_mag):.6g}  std={np.std(B_mag):.6g}  max={np.max(B_mag):.6g}")

    D_B = B_mag / (2 * A_tilde)
    print(f"D_B = |B̃|/(2Ã_⊥):  mean={np.mean(D_B)*100:.2f}%  max={np.max(D_B)*100:.2f}%")
    print(f"  (cylinder bound at 28 GHz: 27.9%)")

    # 5. SH error sweep for each quantity
    theta, phi = _spherical_angles(directions)

    print("\nSH sweep for D(k̂)...")
    sum_D = sh_error_sweep(D, theta, phi, args.maxL)

    print("SH sweep for Ã_⊥(k̂)...")
    sum_At = sh_error_sweep(A_tilde, theta, phi, args.maxL)

    print("SH sweep for |B̃(k̂)|...")
    sum_Bm = sh_error_sweep(B_mag, theta, phi, args.maxL)

    # Print table
    print("\n=== SH Compression Results ===")
    print(f"{'L':>3}  {'(L+1)²':>7}  {'D rms%':>9}  {'Ã_⊥ rms%':>9}  {'|B̃| rms%':>9}")
    print("-" * 50)
    for sd, sa, sb in zip(sum_D, sum_At, sum_Bm):
        print(
            f"{sd.L:3d}  {sd.n_coeff:7d}  {sd.rms_rel*100:9.3f}  "
            f"{sa.rms_rel*100:9.3f}  {sb.rms_rel*100:9.3f}"
        )

    # Report threshold crossings
    for name, summaries in [("D", sum_D), ("Ã_⊥", sum_At), ("|B̃|", sum_Bm)]:
        L_hit = None
        for s in summaries:
            if s.rms_rel * 100 <= 5.0:
                L_hit = s.L
                break
        if L_hit is not None:
            print(f"  {name}: first L with RMS ≤ 5% → L={L_hit} ({(L_hit+1)**2} coefficients)")
        else:
            print(f"  {name}: did NOT reach 5% by L={args.maxL}")

    # 6. Plot
    ext = ".png" if args.mode == "png" else ".pdf"
    out_dir = Path(args.outdir)
    out_dir.mkdir(parents=True, exist_ok=True)
    fig_path = out_dir / f"sh_compression_polarization{ext}"

    plot_sh_compression(sum_D, sum_At, sum_Bm, out_path=fig_path, mode=args.mode)

    print("\nDone.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
