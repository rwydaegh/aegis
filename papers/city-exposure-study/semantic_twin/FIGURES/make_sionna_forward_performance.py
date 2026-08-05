"""Runtime and accuracy cost for the controlled Sionna validation.

Run from the ``semantic_twin`` directory::

    ../../../.venv/bin/python FIGURES/make_sionna_forward_performance.py
"""

from __future__ import annotations

import json
import pathlib
import sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, "/home/user/aegis/theory/scripts")

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from _plot_style import apply_monograph_style, fig_size_ieee  # noqa: E402

OUT = pathlib.Path(__file__).resolve().parent
DATA = ROOT / "outputs" / "cross_validation"
FILES = {
    50_000: DATA / "forward_sionna_open_50k_open_square.json",
    100_000: DATA / "forward_sionna_open_100k_open_square.json",
}
SOLVERS = ("adjoint", "sionna")
COLOURS = {"adjoint": "C0", "sionna": "C3"}


def _load(path: pathlib.Path) -> dict:
    return json.loads(path.read_text())


def _single_run_db_sd(payload: dict, solver: str) -> np.ndarray:
    values = payload[solver]["total"]
    mean = np.asarray(values["mean"], dtype=np.float64)
    standard_error = np.asarray(values["standard_error"], dtype=np.float64)
    seeds = len(payload[solver]["seconds"])
    return 10.0 / np.log(10.0) * standard_error / mean * np.sqrt(seeds)


def _runtime(axis: plt.Axes, payloads: dict[int, dict]) -> None:
    x = np.arange(len(payloads), dtype=np.float64)
    width = 0.32
    means: dict[str, list[float]] = {solver: [] for solver in SOLVERS}
    spreads: dict[str, list[float]] = {solver: [] for solver in SOLVERS}
    for payload in payloads.values():
        for solver in SOLVERS:
            seconds = np.asarray(payload[solver]["seconds"], dtype=np.float64)[1:]
            means[solver].append(float(np.mean(seconds)))
            spreads[solver].append(float(np.std(seconds, ddof=1)))

    for offset, solver in zip((-width / 2, width / 2), SOLVERS, strict=True):
        axis.bar(
            x + offset,
            means[solver],
            width,
            yerr=spreads[solver],
            capsize=2,
            color=COLOURS[solver],
            alpha=0.85,
            label=solver,
        )

    for index in range(len(payloads)):
        speedup = means["sionna"][index] / means["adjoint"][index]
        top = max(
            means["sionna"][index] + spreads["sionna"][index],
            means["adjoint"][index],
        )
        axis.text(
            x[index],
            top + 0.35,
            f"{speedup:.1f}$\\times$",
            ha="center",
            va="bottom",
            fontsize=7,
        )

    axis.set_xticks(x)
    axis.set_xticklabels(("50k", "100k"))
    axis.set_xlabel("samples")
    axis.set_ylabel("seconds per seed")
    axis.set_ylim(0.0, 9.2)
    axis.legend(frameon=False, loc="upper left")
    axis.set_title("a  warmed, equal sample budget", loc="left")


def _accuracy_cost(axis: plt.Axes, payloads: dict[int, dict]) -> None:
    x = np.arange(len(payloads), dtype=np.float64)
    ratios = []
    for payload in payloads.values():
        time = {solver: float(np.mean(payload[solver]["seconds"][1:])) for solver in SOLVERS}
        median_variance = {solver: float(np.median(_single_run_db_sd(payload, solver) ** 2)) for solver in SOLVERS}
        ratios.append(time["sionna"] * median_variance["sionna"] / (time["adjoint"] * median_variance["adjoint"]))

    axis.bar(
        x,
        np.ones(len(x)),
        width=0.32,
        color=COLOURS["adjoint"],
        alpha=0.85,
        label="adjoint",
    )
    bars = axis.bar(
        x + 0.32,
        ratios,
        width=0.32,
        color=COLOURS["sionna"],
        alpha=0.85,
        label="Sionna",
    )
    for bar, ratio in zip(bars, ratios, strict=True):
        axis.text(
            bar.get_x() + bar.get_width() / 2,
            ratio + 0.05,
            f"{ratio:.1f}$\\times$",
            ha="center",
            va="bottom",
            fontsize=7,
        )
    axis.set_xticks(x + 0.16)
    axis.set_xticklabels(("50k", "100k"))
    axis.set_xlabel("samples")
    axis.set_ylabel("relative compute cost")
    axis.set_ylim(0.0, 2.35)
    axis.legend(frameon=False, loc="upper right")
    axis.set_title("b  same Monte Carlo variance", loc="left")


def main() -> None:
    payloads = {budget: _load(path) for budget, path in FILES.items()}

    apply_monograph_style()
    figure, axes = plt.subplots(
        1,
        2,
        figsize=fig_size_ieee(columns=2, aspect=0.42),
        constrained_layout=True,
    )
    _runtime(axes[0], payloads)
    _accuracy_cost(axes[1], payloads)

    for suffix in (".pdf", ".png"):
        figure.savefig(OUT / f"27_sionna_forward_performance{suffix}", dpi=300)
    print(f"wrote {OUT / '27_sionna_forward_performance.pdf'}")


if __name__ == "__main__":
    main()
