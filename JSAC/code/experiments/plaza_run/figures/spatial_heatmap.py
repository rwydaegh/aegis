"""§VII spatial heatmap — mean P_abs(x, y) over a 5-min OD-walk run.

Bodies traverse the plaza via random origin-destination pairs through the
seven Brussels Grand Place street nodes. Each (body, slot) tuple
contributes one (x, y, p_abs) sample. Binning by (x, y) and taking the
mean p_abs per cell reveals where the BS forward sector + served-user
clustering deposits power vs the cooler street-mouth and shadow zones.

Two panels:
  (a) plaza-specular, multi-body ECBF — physically meaningful map
  (b) plaza-specular, MRT — naive baseline that does not respect
      compliance, useful as visual contrast

Run:
    python -m JSAC.code.experiments.plaza_run.figures.spatial_heatmap
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from _data import OUTPUTS_DIR, load_canonical, load_run
from _figstyle import apply_monograph_style, fig_size_ieee, save_both

FIG_DIR = Path(__file__).resolve().parent

GRID_HALF_M = 35.0
GRID_STEP_M = 1.5  # 47x47 cells over the plaza interior
MIN_SAMPLES_PER_CELL = 8  # below this, leave the cell blank (low confidence)


def _spatial_mean(run, precoder_name: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Bin (body, slot) p_abs samples onto a fixed (x, y) grid.

    Returns ``(mean_grid, count_grid, edges)`` where ``mean_grid`` is W per
    cell and ``count_grid`` is the number of contributing body-slots.
    Cells with < ``MIN_SAMPLES_PER_CELL`` samples are NaN.
    """
    pidx = run.precoder_index(precoder_name)
    pos = run.body_positions  # (T, B, 3)
    p_abs = run.p_abs[..., pidx]  # (T, B)
    # Flatten to (T*B,) samples; drop off-camera samples (parked off-screen)
    xs = pos[..., 0].reshape(-1)
    ys = pos[..., 1].reshape(-1)
    ps = p_abs.reshape(-1)
    in_plaza = (xs >= -GRID_HALF_M) & (xs <= GRID_HALF_M) & (ys >= -GRID_HALF_M) & (ys <= GRID_HALF_M)
    xs, ys, ps = xs[in_plaza], ys[in_plaza], ps[in_plaza]

    edges = np.arange(-GRID_HALF_M, GRID_HALF_M + GRID_STEP_M, GRID_STEP_M)
    sum_grid, _, _ = np.histogram2d(xs, ys, bins=[edges, edges], weights=ps)
    count_grid, _, _ = np.histogram2d(xs, ys, bins=[edges, edges])
    with np.errstate(invalid="ignore", divide="ignore"):
        mean = np.where(count_grid >= MIN_SAMPLES_PER_CELL, sum_grid / count_grid, np.nan)
    return mean, count_grid, edges


def _try_load(label_5min: str, label_legacy: str):
    """Prefer the 9000-slot run if it exists; else fall back to the 600-slot."""
    npz_5min = OUTPUTS_DIR / f"plaza_run_seed42_physhannon_poseaware_pathsdict_{label_5min}.npz"
    if npz_5min.exists():
        return load_run(npz_5min, label=label_5min), label_5min
    return load_canonical(label_legacy), label_legacy


def main() -> None:
    apply_monograph_style(mode="png")
    run_specular, lbl_spec = _try_load("viz5min", "specular_aware")
    run_bind, lbl_bind = _try_load("bind5min", "specular_bind")

    fig, axes = plt.subplots(1, 2, figsize=fig_size_ieee(columns=2, aspect=0.50))
    panels = [
        (axes[0], run_specular, "multibody_ecbf", f"(a) Slack regime ({lbl_spec}) — multi-body ECBF"),
        (axes[1], run_bind, "zf", f"(b) Binding regime ({lbl_bind}) — ZF"),
    ]

    for ax, run, precoder, title in panels:
        mean_grid, count_grid, edges = _spatial_mean(run, precoder)
        budget = float(np.median(run.body_budgets_w))
        with np.errstate(invalid="ignore", divide="ignore"):
            ratio = mean_grid / budget
        # Symmetric log color norm so empty cells (NaN) and dynamic range read.
        vmax = float(np.nanpercentile(ratio, 99))
        vmin = max(float(np.nanpercentile(ratio, 5)), vmax * 1e-5)
        from matplotlib.colors import LogNorm

        norm = LogNorm(vmin=vmin, vmax=vmax)
        cmap = plt.cm.viridis.copy()
        cmap.set_bad(color="#1c1c24")
        im = ax.imshow(
            ratio.T,
            origin="lower",
            extent=[edges[0], edges[-1], edges[0], edges[-1]],
            aspect="equal",
            cmap=cmap,
            norm=norm,
            interpolation="nearest",
        )
        # Plaza outline (the polygon enclosing the plaza ground).
        ax.scatter([0], [-40], marker="s", s=60, c="#cc4422", edgecolors="black", lw=0.8, zorder=3, label="BS")
        ax.set_xlim(-GRID_HALF_M, GRID_HALF_M)
        ax.set_ylim(-GRID_HALF_M, GRID_HALF_M)
        ax.set_xlabel("x [m]")
        ax.set_ylabel("y [m]")
        ax.set_title(title, fontsize=8.5)
        cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
        cbar.set_label(r"$\langle P_\mathrm{abs}\rangle / L_\mathrm{RL}$", fontsize=8)
        cbar.ax.tick_params(labelsize=7)

    fig.tight_layout()
    pdf, png = save_both(fig, FIG_DIR / "spatial_heatmap")
    plt.close(fig)
    print(f"saved {pdf}")
    print(f"saved {png}")
    # Sanity print
    for _ax, run, precoder, _ in panels:
        mean_grid, count_grid, _ = _spatial_mean(run, precoder)
        budget = float(np.median(run.body_budgets_w))
        with np.errstate(invalid="ignore"):
            ratio = mean_grid / budget
            valid = ratio[count_grid >= MIN_SAMPLES_PER_CELL]
        if valid.size:
            print(
                f"  {run.label} / {precoder}: cells={valid.size} "
                f"median ratio={np.nanmedian(valid):.2e} "
                f"p95={np.nanpercentile(valid, 95):.2e} max={np.nanmax(valid):.2e}"
            )


if __name__ == "__main__":
    main()
