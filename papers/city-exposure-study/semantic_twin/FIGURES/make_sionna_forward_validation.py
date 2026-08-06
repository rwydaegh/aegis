"""The controlled forward-versus-adjoint Sionna validation.

Run from the ``semantic_twin`` directory::

    ../../../.venv/bin/python FIGURES/make_sionna_forward_validation.py
"""

from __future__ import annotations

import json
import pathlib
import sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, "/home/user/aegis/theory/scripts")

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from mpl_toolkits.mplot3d.art3d import Poly3DCollection  # noqa: E402

from _plot_style import apply_monograph_style, fig_size_ieee  # noqa: E402
from semantic_twin.transport.sionna_forward import open_square_environment  # noqa: E402

OUT = pathlib.Path(__file__).resolve().parent
DATA = ROOT / "outputs" / "cross_validation"
FILES = {
    1: DATA / "forward_sionna_open_depth1_50k_open_square.json",
    2: DATA / "forward_sionna_open_depth2_50k_open_square.json",
    3: DATA / "forward_sionna_open_50k_open_square.json",
}
CONVERGED = DATA / "forward_sionna_open_100k_open_square.json"
RECEIVERS = ("centre", "north wall", "west side", "east side", "open side", "behind wall")


def _load(path: pathlib.Path) -> dict:
    return json.loads(path.read_text())


def _mean(payload: dict, solver: str, term: str) -> np.ndarray:
    return np.asarray(payload[solver][term]["mean"], dtype=np.float64)


def _residual(payload: dict, term: str = "total") -> np.ndarray:
    return np.asarray(payload["comparison"][term]["sionna_minus_adjoint_db"], dtype=np.float64)


def _scene(axis: plt.Axes) -> None:
    environment = open_square_environment()
    quads = [environment.vertices[start : start + 4] for start in range(0, environment.vertices.shape[0], 4)]
    axis.add_collection3d(Poly3DCollection([quads[0]], facecolor="0.8", edgecolor="0.65", alpha=0.18, linewidth=0.6))
    axis.add_collection3d(Poly3DCollection(quads[1:], facecolor="0.75", edgecolor="0.3", alpha=0.6, linewidth=0.8))
    axis.scatter(
        environment.sources[:, 0],
        environment.sources[:, 1],
        environment.sources[:, 2],
        s=8,
        color="C3",
        depthshade=False,
        label="27 facade-tip sources",
    )
    axis.scatter(
        environment.receivers[:, 0],
        environment.receivers[:, 1],
        environment.receivers[:, 2],
        s=18,
        color="C0",
        marker="o",
        depthshade=False,
        label="6 receivers",
    )
    for index, point in enumerate(environment.receivers, start=1):
        axis.text(point[0], point[1], point[2] + 1.2, f"R{index}", fontsize=6, ha="center")
    axis.set_xlim(-65.0, 65.0)
    axis.set_ylim(-65.0, 65.0)
    axis.set_zlim(0.0, 24.0)
    axis.set_box_aspect((2.0, 2.0, 0.55))
    axis.view_init(elev=24.0, azim=-56.0)
    axis.set_xticks((-40, 0, 40))
    axis.set_yticks((-40, 0, 40))
    axis.set_zticks((0, 20))
    axis.set_xlabel("x (m)", labelpad=-2)
    axis.set_ylabel("y (m)", labelpad=-2)
    axis.set_zlabel("z (m)", labelpad=-4)
    axis.legend(loc="upper left", frameon=False, fontsize=6, handletextpad=0.3)
    axis.set_title("a  imagined open square", loc="left")


def _solver_scatter(axis: plt.Axes, depths: dict[int, dict]) -> None:
    markers = {1: "o", 2: "s", 3: "^"}
    values = []
    for depth, payload in depths.items():
        adjoint = 10.0 * np.log10(_mean(payload, "adjoint", "total"))
        sionna = 10.0 * np.log10(_mean(payload, "sionna", "total"))
        values.extend(adjoint)
        values.extend(sionna)
        axis.scatter(
            adjoint, sionna, s=22, marker=markers[depth], label=f"{depth} interaction{'s' if depth > 1 else ''}"
        )
    low = min(values) - 0.15
    high = max(values) + 0.15
    axis.plot([low, high], [low, high], color="0.35", lw=0.8, zorder=0)
    axis.set_xlim(low, high)
    axis.set_ylim(low, high)
    axis.set_aspect("equal", adjustable="box")
    axis.set_xlabel("adjoint total (dB m$^{-2}$)")
    axis.set_ylabel("Sionna total (dB m$^{-2}$)")
    axis.legend(loc="upper left", frameon=False)
    axis.set_title("b  same transfer in both directions", loc="left")


def _receiver_residuals(axis: plt.Axes, depths: dict[int, dict], converged: dict) -> None:
    x = np.arange(len(RECEIVERS))
    for depth, payload in depths.items():
        axis.plot(x, _residual(payload), marker=("o", "s", "^")[depth - 1], ms=3.5, lw=1.0, label=f"depth {depth}, 50k")
    axis.plot(x, _residual(converged), marker="D", ms=3.2, lw=1.1, color="0.15", label="depth 3, 100k")
    axis.axhspan(-0.1, 0.1, color="0.92", zorder=-2)
    axis.axhline(0.0, color="0.45", lw=0.7, zorder=-1)
    axis.set_xticks(x)
    axis.set_xticklabels(RECEIVERS, rotation=28, ha="right")
    axis.set_ylabel("Sionna minus adjoint (dB)")
    axis.set_ylim(-0.105, 0.105)
    axis.legend(loc="lower left", frameon=False, ncol=2, fontsize=6)
    axis.set_title("c  residual at each receiver", loc="left")


def _convergence(axis: plt.Axes, baseline: dict, converged: dict) -> None:
    x = np.arange(len(RECEIVERS))
    for solver, marker, colour in (("adjoint", "o", "C0"), ("sionna", "s", "C3")):
        low = _mean(baseline, solver, "total")
        high = _mean(converged, solver, "total")
        change = 10.0 * np.log10(high / low)
        median = np.median(np.abs(change))
        axis.plot(x, change, marker=marker, ms=3.5, lw=1.0, color=colour, label=f"{solver}, median {median:.3f} dB")
    axis.axhspan(-0.1, 0.1, color="0.92", zorder=-2)
    axis.axhline(0.0, color="0.45", lw=0.7, zorder=-1)
    axis.set_xticks(x)
    axis.set_xticklabels(RECEIVERS, rotation=28, ha="right")
    axis.set_ylabel("100k minus 50k (dB)")
    axis.set_ylim(-0.105, 0.105)
    axis.legend(loc="lower left", frameon=False, fontsize=6)
    axis.set_title("d  doubling the sample count", loc="left")


def main() -> None:
    depths = {depth: _load(path) for depth, path in FILES.items()}
    converged = _load(CONVERGED)

    apply_monograph_style()
    figure = plt.figure(figsize=fig_size_ieee(columns=2, aspect=0.78), constrained_layout=True)
    grid = figure.add_gridspec(2, 2)
    scene = figure.add_subplot(grid[0, 0], projection="3d")
    scatter = figure.add_subplot(grid[0, 1])
    residuals = figure.add_subplot(grid[1, 0])
    convergence = figure.add_subplot(grid[1, 1])

    _scene(scene)
    _solver_scatter(scatter, depths)
    _receiver_residuals(residuals, depths, converged)
    _convergence(convergence, depths[3], converged)

    for suffix in (".pdf", ".png"):
        figure.savefig(OUT / f"26_sionna_forward_validation{suffix}", dpi=300)
    print(f"wrote {OUT / '26_sionna_forward_validation.pdf'}")


if __name__ == "__main__":
    main()
