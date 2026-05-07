"""Re-render Paper C figures at IEEE two-column sizes from cached npz.

Single-column width = 3.5 in (~89 mm). Full-width (figure*) = 7.16 in.

ecbf_pareto: single column, 3.5 in wide, two stacked panels.
hotspot_pair: figure*, 7.16 in wide, four panels (2 cases x 2 views).
spectrum:    single column, 3.5 in wide.

Uses SciencePlots + LaTeX rendering via the shared theory style helper.
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LogNorm

# Add aegis to path. parents[4] resolves to /home/user/aegis (this file is
# at .../papers/drafts/figures/paperC/rerender_ieee.py).
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).parent))

# IEEE/SciencePlots styling. The helper sets text.usetex when mode='pdf' and
# matches the monograph's Latin Modern font stack.
sys.path.insert(0, str(ROOT / "theory" / "scripts"))
from _plot_style import apply_monograph_style, fig_size_ieee  # noqa: E402

apply_monograph_style(mode="pdf")

# Reuse paperC_simulate helpers (paths, ECBF, GEP, etc.)
import paperC_simulate as sim  # noqa: E402

OUT = Path(__file__).parent

DATA = np.load(OUT / "paperC_results.npz", allow_pickle=True)
Q_a = DATA["Q_a"]
Q_b = DATA["Q_b"]
h_a = DATA["h_a"]
h_b = DATA["h_b"]
M_ANT = h_a.shape[0]


def render_pareto():
    print("Rendering ECBF Pareto (3.5 in single column)...")
    rng = np.random.default_rng(31415)
    P = 1.0

    fig, axes = plt.subplots(
        2, 1, figsize=fig_size_ieee(columns=1, aspect=1.30), dpi=200, sharex=True,
    )
    for ax, Q, h, label in [
        (axes[0], Q_a, h_a, r"(a) UE in front"),
        (axes[1], Q_b, h_b, r"(b) UE behind phantom"),
    ]:
        pabs_curve, psig_curve, _ = sim.ecbf_pareto_curve(h, Q, P, n_lambdas=50)
        x_mrt = sim.mrt_precoder(h, P)
        x_gep = sim.gep_precoder(h, Q, P)
        x_rand = sim.random_unit_precoders(200, M_ANT, P, rng)
        pabs_rand = np.array([sim.absorbed_power(x, Q) for x in x_rand]) / P
        psig_rand = np.array([sim.signal_power(x, h) for x in x_rand]) / P
        x_inc = sim.random_phase_precoder(h, P, rng, 200)
        pabs_inc = np.array([sim.absorbed_power(x, Q) for x in x_inc]) / P
        psig_inc = np.array([sim.signal_power(x, h) for x in x_inc]) / P

        ax.scatter(pabs_rand, psig_rand, s=4, alpha=0.25, color="0.65", label="Random")
        ax.scatter(pabs_inc, psig_inc, s=4, alpha=0.45, color="C2", label="Incoherent")
        ax.plot(pabs_curve, psig_curve, "-", color="C0", lw=1.4, label="ECBF")
        ax.scatter(
            [sim.absorbed_power(x_mrt, Q) / P], [sim.signal_power(x_mrt, h) / P],
            s=70, marker="*", color="C3", zorder=5, label="MRT",
        )
        ax.scatter(
            [sim.absorbed_power(x_gep, Q) / P], [sim.signal_power(x_gep, h) / P],
            s=50, marker="D", color="C1", zorder=5, label="GEP",
        )

        ax.set_xscale("log")
        ax.set_yscale("log")
        if ax is axes[1]:
            ax.set_xlabel(r"Absorbed body power $\mathbf{x}^H Q \mathbf{x}/P$")
        ax.set_ylabel(r"Received $|\mathbf{h}^T \mathbf{x}|^2/P$")
        ax.set_title(label)
        ax.grid(True, which="both", ls=":", lw=0.4)
        ax.legend(fontsize=6.5, loc="lower right", framealpha=0.85, ncol=2, handlelength=1.2)

    fig.tight_layout(pad=0.3)
    fig.savefig(OUT / "ecbf_pareto.pdf")
    fig.savefig(OUT / "ecbf_pareto.png", dpi=300)
    plt.close(fig)


def render_spectrum():
    print("Rendering spectrum (3.5 in)...")
    body = sim.load_thelonious(max_triangles=2000)
    bs_positions = DATA["bs_positions"]
    ue_pos = DATA["ue_a"]
    p_per_elem = sim.P_TX_W / sim.M_ANT

    fig, ax = plt.subplots(figsize=fig_size_ieee(columns=1, aspect=0.75), dpi=200)
    Ns = [10, 30, 60, 100]
    for n_per in Ns:
        rng = np.random.default_rng(7 * n_per + 13)
        k_hat, psi, elem_idx, _ = sim.synthetic_paths_for_target(
            bs_positions, ue_pos, n_per, sim.CONE_HALF_ANGLE_DEG, p_per_elem, rng,
        )
        from aegis.coherent.body_channel import compute_body_channel
        from aegis.coherent.exposure_operator import compute_exposure_operator
        G_tilde = compute_body_channel(
            body.normals, body.centroids, k_hat, psi, elem_idx,
            sim.N_TILDE, sim.SKIN_SIGMA, sim.FREQ_HZ, sim.M_ANT,
        )
        Q_n = np.asarray(compute_exposure_operator(G_tilde, body.areas))
        eigvals = np.linalg.eigvalsh(Q_n)[::-1]
        eigvals = np.maximum(eigvals, 0.0)
        cumfrac = np.cumsum(eigvals) / max(np.sum(eigvals), 1e-30)
        ax.plot(np.arange(1, sim.M_ANT + 1), cumfrac, lw=1.4, label=f"$N/M={n_per}$")

    ax.axhline(0.99, ls="--", color="0.5", lw=0.7, label=r"$99\%$")
    ax.set_xlabel(r"Eigenvalue rank $k$")
    ax.set_ylabel(r"$\sum_{i\leq k}\lambda_i\,/\,\mathrm{tr}(Q)$")
    ax.set_xlim(0, sim.M_ANT)
    ax.set_ylim(0, 1.02)
    ax.grid(True, ls=":", lw=0.4)
    ax.legend(fontsize=7.5, loc="lower right", framealpha=0.9)
    fig.tight_layout(pad=0.3)
    fig.savefig(OUT / "spectrum.pdf")
    fig.savefig(OUT / "spectrum.png", dpi=300)
    plt.close(fig)


def render_hotspot():
    print("Rendering hotspot pair (7.16 in)...")
    from aegis.coherent.body_channel import compute_body_channel
    from aegis.coherent.ecbf import solve_ecbf

    body = sim.load_thelonious(max_triangles=12000)
    k_hat = DATA["k_hat_a"]
    psi = DATA["psi_a"]
    elem_idx = DATA["elem_idx_a"]
    Q = Q_a
    h = h_a
    P = 1.0

    G_tilde = compute_body_channel(
        body.normals, body.centroids, k_hat, psi, elem_idx,
        sim.N_TILDE, sim.SKIN_SIGMA, sim.FREQ_HZ, sim.M_ANT,
    )

    x_mrt = sim.mrt_precoder(h, P)
    p_abs_mrt = sim.absorbed_power(x_mrt, Q)
    psig_mrt = sim.signal_power(x_mrt, h)
    target_psig = 0.5 * psig_mrt
    pabs_curve, psig_curve, _ = sim.ecbf_pareto_curve(h, Q, P, n_lambdas=80)
    idx0 = int(np.argmin(np.abs(psig_curve - target_psig)))
    p_abs_target = pabs_curve[idx0] * P
    x_ecbf = np.asarray(solve_ecbf(h, Q, p_abs_target, P))
    p_abs_ecbf = sim.absorbed_power(x_ecbf, Q)
    psig_ecbf = sim.signal_power(x_ecbf, h)

    field_mrt = np.einsum("mia,a->mi", G_tilde, x_mrt)
    sab_mrt = np.real(np.sum(np.conj(field_mrt) * field_mrt, axis=1))
    field_ecbf = np.einsum("mia,a->mi", G_tilde, x_ecbf)
    sab_ecbf = np.real(np.sum(np.conj(field_ecbf) * field_ecbf, axis=1))

    centroids = body.centroids
    vmax = float(max(sab_mrt.max(), sab_ecbf.max()))
    vmin = max(vmax * 1e-3, 1e-12)

    def _scinot(value: float) -> str:
        """Return a TeX-rendered string like '1.69 \\times 10^{-5}' for a positive value."""
        if value <= 0:
            return f"{value:g}"
        exp = int(np.floor(np.log10(value)))
        mant = value / 10.0 ** exp
        return rf"{mant:.2f}\times 10^{{{exp}}}"

    # Layout: 4 panels in a single row at full `figure*` width.
    # Columns: MRT-front, MRT-side, gap, ECBF-front, ECBF-side.
    # A single shared colorbar on the right.
    fig = plt.figure(figsize=fig_size_ieee(columns=2, aspect=0.50), dpi=200)
    gs = fig.add_gridspec(
        1, 5,
        width_ratios=[1.0, 1.0, 0.20, 1.0, 1.0],
        wspace=0.10,
    )

    def _draw(ax, sab, x_axis_idx: int, x_label: str, show_y: bool):
        xs = centroids[:, x_axis_idx]
        sc_local = ax.scatter(
            xs, centroids[:, 2], c=sab, cmap="inferno", s=1.0,
            norm=LogNorm(vmin=vmin, vmax=vmax),
        )
        ax.set_aspect("equal")
        ax.set_xlabel(x_label, labelpad=1)
        ax.set_xticks([-0.2, 0.2])
        if show_y:
            ax.set_ylabel(r"$z$ (m)")
        else:
            ax.set_yticklabels([])
        return sc_local

    axM_front = fig.add_subplot(gs[0, 0])
    axM_side = fig.add_subplot(gs[0, 1])
    axE_front = fig.add_subplot(gs[0, 3])
    axE_side = fig.add_subplot(gs[0, 4])

    _draw(axM_front, sab_mrt, 0, r"$x$ (m)", show_y=True)
    _draw(axM_side, sab_mrt, 1, r"$y$ (m)", show_y=False)
    _draw(axE_front, sab_ecbf, 0, r"$x$ (m)", show_y=True)
    sc = _draw(axE_side, sab_ecbf, 1, r"$y$ (m)", show_y=False)

    axM_front.set_title(r"Front ($xz$)")
    axM_side.set_title(r"Side ($yz$)")
    axE_front.set_title(r"Front ($xz$)")
    axE_side.set_title(r"Side ($yz$)")

    # Group titles centred above each pair of panels.
    fig.text(
        0.225, 1.02,
        rf"(a) MRT: $P_{{\mathrm{{abs}}}}={_scinot(p_abs_mrt)}\,$W",
        ha="center", va="bottom",
    )
    fig.text(
        0.69, 1.02,
        rf"(b) ECBF (50\% sig.): $P_{{\mathrm{{abs}}}}={_scinot(p_abs_ecbf)}\,$W "
        rf"($\times {p_abs_mrt / max(p_abs_ecbf, 1e-30):.1f}$ reduction)",
        ha="center", va="bottom",
    )

    # Single shared colorbar to the right of the figure.
    cax = fig.add_axes([0.93, 0.20, 0.012, 0.60])
    cb = fig.colorbar(sc, cax=cax)
    cb.set_label(r"$S_{\mathrm{ab}}$ (W/m$^2$)")

    fig.savefig(OUT / "hotspot_pair.pdf", bbox_inches="tight", pad_inches=0.10)
    fig.savefig(OUT / "hotspot_pair.png", dpi=300, bbox_inches="tight", pad_inches=0.10)
    plt.close(fig)


if __name__ == "__main__":
    render_pareto()
    render_spectrum()
    render_hotspot()
    print("Done.")
