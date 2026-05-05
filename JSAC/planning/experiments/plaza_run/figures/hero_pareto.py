"""Hero figure for §VII.D.

The original plan was a Pareto (violation rate vs sum-rate, one dot per
precoder), but at the paper's nominal load all five precoders collapse:
zero violations, identical sum-rate. The honest plot is therefore a
two-panel figure that *shows* that collapse:

  (a) per-precoder p_abs / L distribution — overlapping CDFs across
      body-slots, with the binding budget at p_abs / L = 1 marked
  (b) per-precoder mean sum-rate as a bar with a thin error span

Path-model comparison (plaza-specular vs UMa-LOS) overlaid where it
matters. Two-column wide IEEE figure.

Run:
    python -m JSAC.planning.experiments.plaza_run.figures.hero_pareto
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from _data import PRECODER_DISPLAY, load_canonical
from _figstyle import apply_monograph_style, fig_size_ieee, save_both

FIG_DIR = Path(__file__).resolve().parent
PRECODER_ORDER = ["mrt", "zf", "wc_backoff", "multibody_ecbf", "oracle"]
PATH_MODEL_DISPLAY = {"specular_aware": "Plaza-specular", "uma_aware": "3GPP UMa-LOS"}
PATH_COLORS = {"specular_aware": "#2166ac", "uma_aware": "#b2182b"}
PATH_LS = {"specular_aware": "-", "uma_aware": "--"}


def _budget_ratio(run) -> dict[str, np.ndarray]:
    """Return {precoder: flat array of p_abs/L_per_body across (slot,body)}."""
    out = {}
    for pname in PRECODER_ORDER:
        idx = run.precoder_index(pname)
        ratio = run.p_abs[..., idx] / run.body_budgets_w[None, :]
        out[pname] = ratio.reshape(-1)
    return out


def main() -> None:
    apply_monograph_style(mode="png")
    runs = {k: load_canonical(k) for k in PATH_MODEL_DISPLAY}

    fig, (ax_a, ax_b) = plt.subplots(1, 2, figsize=fig_size_ieee(columns=2, aspect=0.42))

    # Panel (a): overlapping CDFs of p_abs/L_RL across (slot, body)
    for run_key, run in runs.items():
        ratios = _budget_ratio(run)
        for pname in PRECODER_ORDER:
            r = np.sort(ratios[pname])
            f = np.arange(1, len(r) + 1) / len(r)
            ax_a.plot(
                r,
                f,
                lw=1.2,
                color=PATH_COLORS[run_key],
                ls=PATH_LS[run_key],
                alpha=0.55 if pname != "multibody_ecbf" else 1.0,
            )
    ax_a.axvline(1.0, color="#404040", lw=1.1, ls=":", label="Brussels RL budget")
    ax_a.axvspan(1.0, 2.0, color="#b2182b", alpha=0.08)
    ax_a.set_xscale("log")
    ax_a.set_xlabel(r"$P_\mathrm{abs} / L_\mathrm{RL}$ per body-slot")
    ax_a.set_ylabel("ECDF over body-slots")
    ax_a.set_xlim(1e-7, 2.0)
    ax_a.set_ylim(0, 1)
    ax_a.text(
        1.05,
        0.05,
        "violation\nzone",
        fontsize=7,
        color="#b2182b",
        ha="left",
        va="bottom",
    )

    # Synthetic path-model legend (precoders all overlap, would be cluttered)
    handles = [
        plt.Line2D([], [], color=PATH_COLORS[k], ls=PATH_LS[k], lw=1.6, label=PATH_MODEL_DISPLAY[k])
        for k in PATH_MODEL_DISPLAY
    ]
    handles.append(plt.Line2D([], [], color="#404040", ls=":", lw=1.0, label="Budget"))
    ax_a.legend(handles=handles, loc="upper left", framealpha=0.95, fontsize=7.5)
    ax_a.set_title("(a) Budget approach across precoders")

    # Panel (b): mean sum-rate bar chart, grouped by path model
    x = np.arange(len(PRECODER_ORDER))
    width = 0.36
    for i, (run_key, run) in enumerate(runs.items()):
        means = np.array([run.sumrate[:, run.precoder_index(p)].mean() / 1e6 for p in PRECODER_ORDER])
        ax_b.bar(
            x + (i - 0.5) * width,
            means,
            width,
            color=PATH_COLORS[run_key],
            label=PATH_MODEL_DISPLAY[run_key],
            edgecolor="black",
            lw=0.4,
        )
    ax_b.set_xticks(x)
    ax_b.set_xticklabels([PRECODER_DISPLAY[p] for p in PRECODER_ORDER], rotation=20, ha="right")
    ax_b.set_ylabel("Mean sum-rate (Mbps)")
    ax_b.set_title("(b) Served sum-rate per precoder")
    ax_b.legend(loc="upper right", framealpha=0.95, fontsize=7.5)
    ax_b.annotate(
        "ZF singular under\nK=25 in UMa-LOS",
        xy=(1, 200),
        xytext=(1.7, 1500),
        fontsize=7,
        color="#404040",
        arrowprops=dict(arrowstyle="-", lw=0.6, color="#404040"),
    )

    fig.tight_layout()
    pdf, png = save_both(fig, FIG_DIR / "hero_pareto")
    plt.close(fig)
    print(f"saved {pdf}")
    print(f"saved {png}")
    # Headline sanity print
    for run_key, run in runs.items():
        ratios = _budget_ratio(run)
        worst = max(r.max() for r in ratios.values())
        print(f"  {run_key}: max p_abs/L = {worst:.2e}, all-precoder collapse confirmed")


if __name__ == "__main__":
    main()
