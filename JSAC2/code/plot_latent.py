"""Plot existence + reachability figures from latent_sweep.npz output."""
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


NPZ = Path("/home/user/aegis/JSAC2/code/outputs/latent_existence.npz")
OUT_DIR = Path("/home/user/aegis/JSAC2/code/outputs")


def main():
    d = np.load(NPZ, allow_pickle=False)
    regime_idx = d["regime_idx"]
    regimes = [s.decode() if isinstance(s, bytes) else str(s) for s in d["regimes"]]
    sinr_baseline = d["sinr_baseline"]
    sinr_existence_max = d["sinr_existence_max"]
    sinr_traj = d["sinr_traj"]
    K_grid = d["K_grid"]
    target_gains_db = d["target_gains_db"]
    success_tol_db = float(d["success_tol_db"])
    rho_z = float(d["rho_z"])
    n_existence_samples = int(d["n_existence_samples"])

    # ---- Existence ----
    fig, ax = plt.subplots(figsize=fig_size_ieee(cols=1, ar=0.62))
    n_regimes = len(regimes)
    width = 0.22
    x = np.arange(len(target_gains_db))
    colors = ["#1F4E79", "#B26A00", "#2E7D32"]
    for r in range(n_regimes):
        rmask = regime_idx == r
        if not rmask.any():
            continue
        gains = sinr_existence_max[rmask] - sinr_baseline[rmask]
        fracs = np.array([(gains >= g).mean() for g in target_gains_db])
        offset = (r - (n_regimes - 1) / 2) * width
        ax.bar(x + offset, fracs * 100, width, color=colors[r % len(colors)],
               label=regimes[r], alpha=0.9)
    ax.set_xticks(x)
    ax.set_xticklabels([f"{g:.0f}" for g in target_gains_db])
    ax.set_xlabel(r"target rate gain $\Delta R_\mathrm{tgt}$ (dB)")
    ax.set_ylabel(r"existence fraction (\%)")
    ax.set_ylim(0, 105)
    ax.legend(loc="upper right", fontsize=7)
    ax.grid(True, alpha=0.3, axis="y")
    fig.tight_layout()
    for ext in ("pdf", "png"):
        p = OUT_DIR / f"fig_latent_existence.{ext}"
        fig.savefig(p, dpi=200, bbox_inches="tight")
        print(f"  wrote {p}")
    plt.close(fig)

    # ---- Reachability ----
    # Take terminal SINR at each K_grid iteration; success = within
    # success_tol_db of the existence_max.
    fig, axes = plt.subplots(1, n_regimes, figsize=fig_size_ieee(cols=2, ar=0.34),
                             sharey=True)
    if n_regimes == 1:
        axes = [axes]
    for r, ax in enumerate(axes):
        rmask = regime_idx == r
        if not rmask.any():
            ax.set_visible(False)
            continue
        traj_r = sinr_traj[rmask]  # (n_scenes_r, K_MAX+1)
        existence_r = sinr_existence_max[rmask]
        success_at_K = np.zeros(len(K_grid))
        for ki, K in enumerate(K_grid):
            terminal = traj_r[:, K]
            success_at_K[ki] = (terminal >= existence_r - success_tol_db).mean()
        ax.plot(K_grid, success_at_K * 100, "o-", color=colors[r % len(colors)],
                linewidth=1.2, markersize=4)
        ax.set_xlabel("iterations $K$")
        ax.set_xticks(K_grid)
        ax.set_xticklabels([str(int(K)) for K in K_grid])
        ax.set_ylim(0, 105)
        ax.set_title(regimes[r], fontsize=8)
        ax.grid(True, alpha=0.3)
        n_cell = int(rmask.sum())
        ax.text(0.97, 0.05, f"$n={n_cell}$", transform=ax.transAxes,
                ha="right", va="bottom", fontsize=6)
    axes[0].set_ylabel(r"reachability (\%)")
    fig.suptitle(
        rf"Reachability: terminal within {success_tol_db:.0f} dB of "
        rf"brute-force optimum ($\rho_z={rho_z}$, "
        rf"{n_existence_samples} samples/scene)",
        fontsize=8,
    )
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    for ext in ("pdf", "png"):
        p = OUT_DIR / f"fig_latent_reachability.{ext}"
        fig.savefig(p, dpi=200, bbox_inches="tight")
        print(f"  wrote {p}")
    plt.close(fig)


if __name__ == "__main__":
    main()
