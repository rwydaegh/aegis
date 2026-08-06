"""Three independent and increasingly realistic propagation checks."""

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


def _load(name: str) -> dict:
    return json.loads((DATA / name).read_text())


def _deterministic(axis: plt.Axes) -> None:
    reference = _load("deterministic_first_bounce_open_square_high.json")
    expected = np.asarray(reference["rows"][-1]["total"], dtype=np.float64)
    sampled = _load("forward_sionna_open_depth1_50k_open_square.json")
    x = np.arange(2, dtype=np.float64)
    for receiver in range(expected.size):
        residual = []
        for solver in ("adjoint", "sionna"):
            mean = np.asarray(sampled[solver]["total"]["mean"], dtype=np.float64)
            residual.append(10.0 * np.log10(mean[receiver] / expected[receiver]))
        axis.plot(x, residual, color="0.75", marker="o", ms=2.5, lw=0.6)
    medians = []
    for solver in ("adjoint", "sionna"):
        mean = np.asarray(sampled[solver]["total"]["mean"], dtype=np.float64)
        residual = 10.0 * np.log10(mean / expected)
        medians.append(float(np.median(residual)))
    axis.scatter(x, medians, color=("C0", "C3"), marker="D", s=25, zorder=3)
    axis.axhline(0.0, color="0.35", lw=0.7)
    axis.set_xticks(x)
    axis.set_xticklabels(("adjoint", "Sionna"))
    axis.set_ylabel("ray tracer minus integral (dB)")
    axis.set_ylim(-0.045, 0.045)
    axis.set_title("a  deterministic first bounce", loc="left")


def _city_depth(axis: plt.Axes) -> None:
    files = {
        1: "forward_sionna_korenmarkt_32s_4r_depth1_200k_gpu_korenmarkt_250m.json",
        2: "forward_sionna_korenmarkt_32s_4r_depth2_200k_gpu_korenmarkt_250m.json",
        3: "forward_sionna_korenmarkt_32s_4r_200k_fully_diffuse_gpu_korenmarkt_250m.json",
    }
    residuals = np.column_stack(
        [np.asarray(_load(name)["comparison"]["total"]["sionna_minus_adjoint_db"]) for name in files.values()]
    )
    x = np.asarray(tuple(files), dtype=np.float64)
    for row in residuals:
        axis.plot(x, row, color="0.7", marker="o", ms=2.5, lw=0.7)
    axis.plot(x, np.median(residuals, axis=0), color="C3", marker="D", ms=4, lw=1.4, label="median")
    axis.axhline(0.0, color="0.35", lw=0.7)
    axis.set_xticks(x)
    axis.set_xlabel("interactions")
    axis.set_ylabel("Sionna minus adjoint (dB)")
    axis.set_ylim(-0.02, 0.24)
    axis.legend(frameon=False, loc="upper left")
    axis.set_title("b  real mesh, neutral material", loc="left")


def _lift(axis: plt.Axes) -> None:
    files = {
        0.001: "forward_sionna_korenmarkt_lift_0.001_200k_gpu_korenmarkt_250m.json",
        0.01: "forward_sionna_korenmarkt_32s_4r_200k_fully_diffuse_gpu_korenmarkt_250m.json",
        0.03: "forward_sionna_korenmarkt_lift_0.03_200k_gpu_korenmarkt_250m.json",
        0.1: "forward_sionna_korenmarkt_lift_0.1_200k_gpu_korenmarkt_250m.json",
    }
    x = np.asarray(tuple(files), dtype=np.float64)
    residuals = np.column_stack(
        [np.asarray(_load(name)["comparison"]["total"]["sionna_minus_adjoint_db"]) for name in files.values()]
    )
    for row in residuals:
        axis.semilogx(x, row, color="0.7", marker="o", ms=2.5, lw=0.7)
    axis.semilogx(x, np.median(residuals, axis=0), color="C3", marker="D", ms=4, lw=1.4, label="median")
    axis.axhline(0.0, color="0.35", lw=0.7)
    axis.axvline(0.01, color="C0", lw=0.8, ls="--", label="production")
    axis.set_xlabel("connection lift (m)")
    axis.set_ylabel("Sionna minus adjoint (dB)")
    axis.set_ylim(-0.11, 0.24)
    axis.legend(frameon=False, loc="upper right")
    axis.set_title("c  photogrammetric surface offset", loc="left")


def main() -> None:
    apply_monograph_style()
    figure, axes = plt.subplots(
        1,
        3,
        figsize=fig_size_ieee(columns=2, aspect=0.34),
        constrained_layout=True,
    )
    _deterministic(axes[0])
    _city_depth(axes[1])
    _lift(axes[2])
    for suffix in (".pdf", ".png"):
        figure.savefig(OUT / f"28_sionna_validation_ladder{suffix}", dpi=300)
    print(f"wrote {OUT / '28_sionna_validation_ladder.pdf'}")


if __name__ == "__main__":
    main()
