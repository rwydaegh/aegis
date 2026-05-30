"""Figure generation for the v4 PoC empirical results.

Produces:
  fig1_pose_sweep.{png,pdf} — pose_sweep S2 + S3, multi-panel
  fig2_svd_spectrum.{png,pdf} — body-to-UE SVD spectra at multiple geometries
  fig3_calibration.{png,pdf} — Tier C / Tier B recovery vs SNR
  fig4_setup.{png,pdf} — geometry visualization
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "theory" / "scripts"))
from _plot_style import apply_monograph_style, fig_size_ieee, fig_size_textwidth


OUT_DIR = Path("/home/user/aegis/JSAC2/code/outputs")


def _save_pair(fig, stem: str):
    fig.savefig(OUT_DIR / f"{stem}.png", dpi=180)
    fig.savefig(OUT_DIR / f"{stem}.pdf")
    print(f"  saved {stem}.{{png,pdf}}")


def fig1_pose_sweep(suffix: str = ""):
    """Hero figure: pose-controllable cascaded channel.

    Compact 1x3 layout: SINR vs yaw across regimes, rate vs yaw across
    regimes, coherent-gain interpretation. The rest of the diagnostics
    (channel norms, visibility, cosine sim) move to fig1b for the appendix.

    `suffix` selects the input NPZ family: "" -> Thelonious legacy,
    "_smplx" -> SMPL-X parametric body. The output figures get the
    same suffix, e.g. fig1_pose_sweep_smplx.{pdf,png}.
    """
    s2 = np.load(OUT_DIR / f"pose_sweep{suffix}_S2.npz", allow_pickle=True)
    s3 = np.load(OUT_DIR / f"pose_sweep{suffix}_S3.npz", allow_pickle=True)
    s2b = np.load(OUT_DIR / f"pose_sweep{suffix}_S2bind.npz", allow_pickle=True)

    apply_monograph_style(mode="png")
    fig, axes = plt.subplots(
        1, 3, figsize=fig_size_textwidth(aspect=0.34, scale=1.0)
    )

    yaws = s2["yaws_deg"]

    # Panel (a): SINR sweep across regimes
    ax = axes[0]
    ax.plot(yaws, s2["sinr_cas_db"], "C0-o", label=f"LOS-attn 35 dB")
    ax.plot(yaws, s2b["sinr_cas_db"], "C3-s", label=f"LOS-attn 55 dB (binding)")
    ax.plot(yaws, s3["sinr_cas_db"], "C2-^", label="LOS extinguished (NLOS)")
    ax.set_xlabel(r"torso yaw $\theta$ [$^\circ$]")
    ax.set_ylabel("cascaded SINR [dB]")
    ax.set_title("(a) cascaded SINR vs pose")
    ax.legend(loc="lower center", fontsize=7)

    # Panel (b): Rate
    ax = axes[1]
    ax.plot(yaws, s2["rate_cas_mbps"], "C0-o", label="LOS-attn 35 dB")
    ax.plot(yaws, s2b["rate_cas_mbps"], "C3-s", label="LOS-attn 55 dB")
    ax.plot(yaws, s3["rate_cas_mbps"], "C2-^", label="LOS extinguished")
    ax.set_xlabel(r"torso yaw [$^\circ$]")
    ax.set_ylabel("achievable rate [Mbps]")
    ax.set_title("(b) Shannon rate vs pose")
    ax.legend(loc="lower center", fontsize=7)

    # Panel (c): channel norms (just the body and cas; LOS is constant)
    ax = axes[2]
    ax.semilogy(yaws, s2["h_body_norm"], "C0-o",
                label=r"$\Vert h_{\mathrm{body}}\Vert$ (pose-driven)")
    ax.axhline(s2["h_los_norm"][0], color="C3", linestyle="-",
               label=r"$\Vert h_{\mathrm{LOS}}\Vert$ (LOS-attn 35 dB)")
    ax.axhline(s3["h_los_norm"][0], color="C2", linestyle="--",
               label=r"$\Vert h_{\mathrm{LOS}}\Vert$ (LOS extinguished)")
    ax.set_xlabel(r"torso yaw [$^\circ$]")
    ax.set_ylabel(r"channel norm")
    ax.set_title(r"(c) body-mediated channel $\Vert h_{\mathrm{body}}\Vert$")
    ax.legend(loc="lower center", fontsize=7)

    fig.tight_layout()
    _save_pair(fig, f"fig1_pose_sweep{suffix}")
    plt.close(fig)


def fig1b_pose_sweep_diagnostics():
    """Diagnostic 2x2 of the pose sweep, for the appendix."""
    s2 = np.load(OUT_DIR / "pose_sweep_S2.npz", allow_pickle=True)
    s3 = np.load(OUT_DIR / "pose_sweep_S3.npz", allow_pickle=True)

    apply_monograph_style(mode="png")
    fig, axes = plt.subplots(2, 2, figsize=fig_size_textwidth(aspect=0.6, scale=1.0))
    yaws = s2["yaws_deg"]

    ax = axes[0, 0]
    ax.plot(yaws, s2["coherent_gain_db"], "C0-o", label="S2")
    ax.plot(yaws, s3["coherent_gain_db"], "C2-^", label="S3")
    ax.axhline(0, color="gray", linestyle=":", label="incoherent")
    ax.set_xlabel(r"torso yaw [$^\circ$]")
    ax.set_ylabel(r"$10\log_{10}\frac{|h_{\mathrm{cas}}|^2}{|h_{\mathrm{LOS}}|^2+|h_{\mathrm{body}}|^2}$ [dB]")
    ax.set_title("(a) coherent gain (LOS+body interference)")
    ax.legend(loc="best", fontsize=7)

    ax = axes[0, 1]
    ax.plot(yaws, s2["cosine_cas_to_los"], "k--",
            label=r"$\langle h_{\mathrm{cas}}, h_{\mathrm{LOS}}\rangle$")
    ax.plot(yaws, s2["cosine_cas_to_body"], "C0-",
            label=r"$\langle h_{\mathrm{cas}}, h_{\mathrm{body}}\rangle$")
    ax.set_xlabel(r"torso yaw [$^\circ$]")
    ax.set_ylabel("cosine similarity (S2)")
    ax.set_title("(b) cascaded direction composition")
    ax.legend(loc="best", fontsize=7)

    ax = axes[1, 0]
    ax.plot(yaws, s2["n_vis"], "C0-o", label="visible from phone")
    ax.set_xlabel(r"torso yaw [$^\circ$]")
    ax.set_ylabel("triangles")
    ax.set_title("(c) phone-visible triangles")
    ax.legend(loc="best", fontsize=7)

    ax = axes[1, 1]
    ax.plot(yaws, s2["cas_to_los_db"], "C3-o", label="S2 (LOS-attn 35 dB)")
    ax.plot(yaws, s3["cas_to_los_db"], "C2-^", label="S3 (LOS extinguished)")
    ax.axhline(0, color="gray", linestyle=":", label="LOS-only baseline")
    ax.set_xlabel(r"torso yaw [$^\circ$]")
    ax.set_ylabel(r"$|h_{\mathrm{cas}}|^2 / |h_{\mathrm{LOS}}|^2$ [dB]")
    ax.set_title("(d) cascaded vs LOS-only ratio")
    ax.legend(loc="best", fontsize=7)

    fig.tight_layout()
    _save_pair(fig, "fig1b_pose_sweep_diagnostics")
    plt.close(fig)


def fig2_svd_spectrum():
    data = np.load(OUT_DIR / "svd_spectrum.npz", allow_pickle=True)
    keys = list(data["geom_keys"])

    apply_monograph_style(mode="png")
    fig, axes = plt.subplots(1, 2, figsize=fig_size_textwidth(aspect=0.4, scale=1.0))

    # Panel (a): singular values, log-y
    ax = axes[0]
    colors = ["C0", "C2", "C3", "C4", "C5", "C6"]
    for ki, key in enumerate(keys):
        S = data[f"{key}__S"]
        ax.semilogy(np.arange(1, len(S) + 1), S / S[0],
                    label=key.replace("_", " "), alpha=0.85, color=colors[ki % len(colors)])
    ax.set_xlim(0, 32)
    ax.set_ylim(1e-9, 2)
    ax.set_xlabel("mode index $k$")
    ax.set_ylabel(r"$s_k / s_1$")
    ax.set_title("(a) Body-to-UE Kirchhoff singular spectrum")
    ax.legend(loc="best", fontsize=7)

    # Panel (b): cumulative spectral mass, with K_99 markers
    ax = axes[1]
    for ki, key in enumerate(keys):
        cum = data[f"{key}__cum_mass"]
        K99 = int(data[f"{key}__K_99"])
        ax.plot(np.arange(1, len(cum) + 1), cum,
                label=f"{key.replace('_', ' ')} ($K_{{99}}$={K99})",
                alpha=0.85, color=colors[ki % len(colors)])
    ax.axhline(0.99, color="gray", linestyle=":", linewidth=1.0)
    ax.set_xlim(0, 16)
    ax.set_ylim(0.7, 1.003)
    ax.set_xlabel("modes retained $K$")
    ax.set_ylabel("spectral mass fraction")
    ax.set_title("(b) Cumulative mass: rank-1 to rank-many transition")
    ax.legend(loc="lower right", fontsize=7)

    fig.tight_layout()
    _save_pair(fig, "fig2_svd_spectrum")
    plt.close(fig)


def fig3_calibration():
    """Calibration recovery: Tier D (1 DOF), Tier C (R=6), Tier B (K modes).

    Two side-by-side panels, one per geometry (far-BS rank-1 vs close-BS
    rank-many), showing how each tier's body-channel reconstruction error
    behaves vs UL pilot SNR.
    """
    apply_monograph_style(mode="png")
    fig, axes = plt.subplots(1, 2, figsize=fig_size_textwidth(aspect=0.42, scale=1.0))

    for col, (label, title_prefix) in enumerate([
        ("far30m", "(a) far-BS (30 m): rank-1"),
        ("close5m", "(b) close-BS (5 m): rank-many"),
    ]):
        path = OUT_DIR / f"calibration_recovery_{label}.npz"
        if not path.exists():
            print(f"  skip {label}: NPZ missing")
            continue
        data = np.load(path)
        snr = data["snr_grid_db"]
        K_grid = data["K_grid"]

        ax = axes[col]
        # Tier D
        med_d = np.median(data["err_d"], axis=1)
        ax.plot(snr, med_d, "k-D", label="Tier D (1 DOF)", lw=1.4, ms=4)
        # Tier C
        med_c = np.median(data["err_c"], axis=1)
        ax.plot(snr, med_c, "C0-o", label=f"Tier C ($R$=6)", lw=1.4, ms=4)
        # Tier B (K=1, K=8, K=32 selected for clarity)
        Ks_to_show = [1, 8, 32]
        for K in Ks_to_show:
            ki = list(K_grid).index(K)
            med_b = np.median(data["err_b"][ki], axis=1)
            ax.plot(snr, med_b, "--", label=f"Tier B ($K$={K})", alpha=0.8, lw=1.2)
        ax.set_xlabel("UL pilot SNR [dB]")
        if col == 0:
            ax.set_ylabel(r"$\Vert\hat h_{\mathrm{body}} - h_{\mathrm{body}}^{\mathrm{true}}\Vert / \Vert h_{\mathrm{body}}^{\mathrm{true}}\Vert$")
        K99 = int(data["K_99"])
        ax.set_title(f"{title_prefix} ($K_{{99}}$={K99})")
        ax.set_yscale("log")
        ax.set_ylim(1e-3, 2)
        ax.legend(loc="best", fontsize=6.5)

    fig.tight_layout()
    _save_pair(fig, "fig3_calibration")
    plt.close(fig)


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print("Generating figures...")
    if (OUT_DIR / "pose_sweep_S2.npz").exists():
        fig1_pose_sweep()
        fig1b_pose_sweep_diagnostics()
    else:
        print("  skipping fig1_pose_sweep (no NPZ)")
    if (OUT_DIR / "pose_sweep_smplx_S2.npz").exists():
        fig1_pose_sweep(suffix="_smplx")
    else:
        print("  skipping fig1_pose_sweep_smplx (no NPZ)")
    if (OUT_DIR / "svd_spectrum.npz").exists():
        fig2_svd_spectrum()
    else:
        print("  skipping fig2_svd_spectrum (no NPZ)")
    if (OUT_DIR / "calibration_recovery.npz").exists():
        fig3_calibration()
    else:
        print("  skipping fig3_calibration (no NPZ)")


if __name__ == "__main__":
    main()
