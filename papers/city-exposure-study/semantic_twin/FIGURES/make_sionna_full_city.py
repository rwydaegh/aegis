"""Full-source neutral-material Korenmarkt comparison with Sionna RT."""

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
INPUT = DATA / "forward_sionna_korenmarkt_full_3000_gpu_korenmarkt_250m.json"
REFERENCE = DATA / "forward_sionna_korenmarkt_full_6000_gpu_korenmarkt_250m.json"
COLOURS = {"adjoint": "C0", "sionna": "C3"}


def _load() -> dict:
    return json.loads(INPUT.read_text())


def _transfer(axis: plt.Axes, payload: dict) -> None:
    adjoint = np.asarray(payload["adjoint"]["total"]["mean"], dtype=np.float64)
    sionna = np.asarray(payload["sionna"]["total"]["mean"], dtype=np.float64)
    limits = (float(min(adjoint.min(), sionna.min())), float(max(adjoint.max(), sionna.max())))
    axis.loglog(limits, limits, color="0.45", lw=0.8, ls="--")
    axis.scatter(adjoint, sionna, color="C3", edgecolor="white", linewidth=0.4, s=25, zorder=3)
    axis.set_xlabel("adjoint transfer ($\\mathrm{m}^{-2}$)")
    axis.set_ylabel("Sionna transfer ($\\mathrm{m}^{-2}$)")
    axis.set_title("a  full-source transfer", loc="left")


def _residual(axis: plt.Axes, payload: dict) -> None:
    labels = ("direct", "bounced", "total")
    for index, name in enumerate(labels):
        residual = np.asarray(payload["comparison"][name]["sionna_minus_adjoint_db"], dtype=np.float64)
        standard_error = []
        for solver in ("adjoint", "sionna"):
            mean = np.asarray(payload[solver][name]["mean"], dtype=np.float64)
            linear_error = np.asarray(payload[solver][name]["standard_error"], dtype=np.float64)
            standard_error.append(10.0 / np.log(10.0) * linear_error / np.maximum(np.abs(mean), 1.0e-300))
        combined_error = np.hypot(*standard_error)
        outside = np.abs(residual) > 0.1 + 3.0 * combined_error
        offset = np.linspace(-0.12, 0.12, residual.size)
        axis.scatter(index + offset[~outside], residual[~outside], color="0.68", s=11, zorder=2)
        axis.scatter(index + offset[outside], residual[outside], color="C3", s=16, zorder=3)
        axis.scatter(index, np.median(residual), color="C0", marker="D", s=28, zorder=4)
    axis.axhline(0.0, color="0.35", lw=0.8)
    axis.scatter([], [], color="0.68", s=11, label="inside error rule")
    axis.scatter([], [], color="C3", s=16, label="outside error rule")
    axis.scatter([], [], color="C0", marker="D", s=28, label="median")
    axis.set_xticks(range(len(labels)))
    axis.set_xticklabels(labels)
    axis.set_ylabel("Sionna minus adjoint (dB)")
    axis.legend(frameon=False, loc="upper left")
    if REFERENCE.exists():
        reference = json.loads(REFERENCE.read_text())
        coarse = np.asarray(payload["sionna"]["total"]["mean"], dtype=np.float64)
        fine = np.asarray(reference["sionna"]["total"]["mean"], dtype=np.float64)
        shift = np.abs(10.0 * np.log10(fine / coarse))
        axis.text(
            0.98,
            0.96,
            f"3k to 6k: {np.median(shift):.3f} dB median, {np.max(shift):.3f} dB max",
            transform=axis.transAxes,
            ha="right",
            va="top",
            fontsize=6.5,
            bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.85, "pad": 1.5},
        )
    axis.set_title("b  numerical agreement", loc="left")


def _runtime(axis: plt.Axes, payload: dict) -> None:
    labels = ("adjoint\nCPU", "Sionna\nA6000")
    timing = {}
    spread = {}
    for solver in ("adjoint", "sionna"):
        seconds = np.asarray(payload[solver]["seconds"], dtype=np.float64)[1:]
        timing[solver] = float(np.mean(seconds))
        spread[solver] = float(np.std(seconds, ddof=1))
    bars = axis.bar(
        np.arange(2),
        [timing["adjoint"], timing["sionna"]],
        yerr=[spread["adjoint"], spread["sionna"]],
        capsize=2,
        color=(COLOURS["adjoint"], COLOURS["sionna"]),
        alpha=0.85,
    )
    speedup = timing["sionna"] / timing["adjoint"]
    axis.text(
        bars[1].get_x() + bars[1].get_width() / 2,
        bars[1].get_height() + spread["sionna"],
        f"{speedup:.1f}$\\times$",
        ha="center",
        va="bottom",
        fontsize=7,
    )
    axis.set_xticks(np.arange(2))
    axis.set_xticklabels(labels)
    axis.set_ylabel("warmed seconds per seed")
    axis.set_title("c  measured-budget wall time", loc="left")


def main() -> None:
    payload = _load()
    apply_monograph_style()
    figure, axes = plt.subplots(
        1,
        3,
        figsize=fig_size_ieee(columns=2, aspect=0.34),
        constrained_layout=True,
    )
    _transfer(axes[0], payload)
    _residual(axes[1], payload)
    _runtime(axes[2], payload)
    for suffix in (".pdf", ".png"):
        figure.savefig(OUT / f"30_sionna_full_city{suffix}", dpi=300)
    print(f"wrote {OUT / '30_sionna_full_city.pdf'}")


if __name__ == "__main__":
    main()
