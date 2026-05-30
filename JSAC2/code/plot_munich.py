"""Plot existence + reachability bars from munich_existence.npz."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "theory" / "scripts"))
try:
    from _plot_style import apply_monograph_style, fig_size_ieee as _fig_size
    apply_monograph_style()
    def fig_size_ieee(cols=1, ar=0.62):
        return _fig_size(columns=cols, aspect=ar)
except Exception:
    def fig_size_ieee(cols=1, ar=0.62):
        return (3.5 * cols, 3.5 * cols * ar)


NPZ = Path("/home/user/aegis/JSAC2/code/outputs/munich_existence.npz")
OUT_DIR = Path("/home/user/aegis/JSAC2/code/outputs")


def main():
    d = np.load(NPZ, allow_pickle=False)
    los_flag = np.array([s.decode() if isinstance(s, bytes) else str(s)
                         for s in d["los_flag"]])
    sinr_baseline = d["sinr_baseline"]
    sinr_existence_max = d["sinr_existence_max"]
    sinr_traj = d["sinr_traj"]
    K_grid = d["K_grid"]
    target_gains_db = d["target_gains_db"]
    success_tol_db = float(d["success_tol_db"])
    rho_z = float(d["rho_z"])
    n_existence = int(d["n_existence_samples"])

    flags = ["LOS", "NLOS"]
    colors = {"LOS": "#1F4E79", "NLOS": "#B26A00"}

    # ---- Existence ----
    fig, ax = plt.subplots(figsize=fig_size_ieee(cols=1, ar=0.62))
    width = 0.36
    x = np.arange(len(target_gains_db))
    for j, flag in enumerate(flags):
        m = los_flag == flag
        if not m.any():
            continue
        gains = sinr_existence_max[m] - sinr_baseline[m]
        fracs = np.array([(gains >= g).mean() for g in target_gains_db])
        offset = (j - 0.5) * width
        ax.bar(x + offset, fracs * 100, width, color=colors[flag],
               label=f"{flag} (n={m.sum()})", alpha=0.9)
    ax.set_xticks(x)
    ax.set_xticklabels([f"{g:.0f}" for g in target_gains_db])
    ax.set_xlabel(r"target SINR gain $\Delta_\mathrm{tgt}$ (dB)")
    ax.set_ylabel(r"existence fraction (\%)")
    ax.set_ylim(0, 105)
    ax.legend(loc="upper right", fontsize=7)
    ax.grid(True, alpha=0.3, axis="y")
    fig.tight_layout()
    for ext in ("pdf", "png"):
        p = OUT_DIR / f"fig_munich_existence.{ext}"
        fig.savefig(p, dpi=200, bbox_inches="tight")
        print(f"  wrote {p}")
    plt.close(fig)

    # ---- Reachability ----
    fig, axes = plt.subplots(1, 2, figsize=fig_size_ieee(cols=2, ar=0.34),
                             sharey=True)
    for j, (flag, ax) in enumerate(zip(flags, axes)):
        m = los_flag == flag
        if not m.any():
            ax.set_visible(False)
            continue
        traj_m = sinr_traj[m]
        existence_m = sinr_existence_max[m]
        success_at_K = np.zeros(len(K_grid))
        for ki, K in enumerate(K_grid):
            terminal = traj_m[:, K]
            success_at_K[ki] = (terminal >= existence_m - success_tol_db).mean()
        ax.plot(K_grid, success_at_K * 100, "o-", color=colors[flag],
                linewidth=1.2, markersize=4)
        ax.set_xlabel("iterations $K$")
        ax.set_xticks(K_grid)
        ax.set_xticklabels([str(int(K)) for K in K_grid])
        ax.set_ylim(0, 105)
        ax.set_title(flag, fontsize=8)
        ax.grid(True, alpha=0.3)
        ax.text(0.97, 0.05, f"$n={int(m.sum())}$", transform=ax.transAxes,
                ha="right", va="bottom", fontsize=6)
    axes[0].set_ylabel(r"reachability (\%)")
    fig.suptitle(rf"Munich reachability: terminal within {success_tol_db:.0f} dB "
                 rf"of brute-force optimum ($\rho_z={rho_z}$, "
                 rf"{n_existence} samples/scene)",
                 fontsize=8)
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    for ext in ("pdf", "png"):
        p = OUT_DIR / f"fig_munich_reachability.{ext}"
        fig.savefig(p, dpi=200, bbox_inches="tight")
        print(f"  wrote {p}")
    plt.close(fig)

    # ---- Per-scene SINR bar (informational) ----
    fig, ax = plt.subplots(figsize=fig_size_ieee(cols=1, ar=0.55))
    n_scenes = len(sinr_baseline)
    idx = np.arange(n_scenes)
    bar_colors = [colors[f] for f in los_flag]
    ax.bar(idx - 0.18, sinr_baseline, 0.36, color=bar_colors, alpha=0.5,
           label="baseline ($\\boldsymbol{z}_0$)")
    ax.bar(idx + 0.18, sinr_existence_max, 0.36, color=bar_colors, alpha=1.0,
           label=f"best of N={n_existence}", edgecolor="black", linewidth=0.4)
    ax.set_xticks(idx)
    ax.set_xticklabels([str(i) for i in idx], fontsize=6)
    ax.set_xlabel("Munich scene index")
    ax.set_ylabel("cascaded SINR (dB)")
    ax.legend(loc="lower right", fontsize=7)
    ax.grid(True, alpha=0.3, axis="y")
    # Mark LOS / NLOS regions on x-axis
    los_count = int((los_flag == "LOS").sum())
    ax.axvspan(-0.5, los_count - 0.5, color=colors["LOS"], alpha=0.05)
    ax.axvspan(los_count - 0.5, n_scenes - 0.5, color=colors["NLOS"], alpha=0.08)
    ax.text(los_count / 2 - 0.5, ax.get_ylim()[1] * 0.95, "LOS",
            ha="center", fontsize=7, color=colors["LOS"])
    ax.text((los_count + n_scenes) / 2 - 0.5, ax.get_ylim()[1] * 0.95,
            "NLOS", ha="center", fontsize=7, color=colors["NLOS"])
    fig.tight_layout()
    for ext in ("pdf", "png"):
        p = OUT_DIR / f"fig_munich_perscene.{ext}"
        fig.savefig(p, dpi=200, bbox_inches="tight")
        print(f"  wrote {p}")
    plt.close(fig)


if __name__ == "__main__":
    main()
