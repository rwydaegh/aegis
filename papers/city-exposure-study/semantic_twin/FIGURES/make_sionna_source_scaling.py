"""Source-count scaling and equal-accuracy checks against Sionna RT."""

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


def _scaling_rows() -> list[dict]:
    rows = list(_load("sionna_source_scaling_tuned_gpu.json")["rows"])
    high = DATA / "sionna_source_scaling_tuned_25782_clean_gpu.json"
    if not high.exists():
        high = DATA / "sionna_source_scaling_tuned_25782_gpu.json"
    if high.exists():
        rows.extend(json.loads(high.read_text())["rows"])
    return sorted({int(row["sources"]): row for row in rows}.values(), key=lambda row: row["sources"])


def _source_scaling(axis: plt.Axes) -> None:
    rows = _scaling_rows()
    sources = np.asarray([row["sources"] for row in rows], dtype=np.float64)
    source_ratio = np.asarray([row["sources"] / row["receivers"] for row in rows], dtype=np.float64)
    adjoint = np.asarray([row["adjoint"]["metrics"]["seconds_warmed_mean"] for row in rows])
    sionna = np.asarray([row["sionna"]["per_source_3000"]["metrics"]["seconds_warmed_mean"] for row in rows])

    study = json.loads((ROOT / "outputs" / "next_event" / "eleven_250m.json").read_text())
    study_ratio = np.asarray(
        [row["sources"]["sites"] / row["held_out"] for row in study["rows"]],
        dtype=np.float64,
    )
    axis.axvspan(study_ratio.min(), study_ratio.max(), color="0.92", lw=0, label="study ratio range")
    axis.loglog(source_ratio, adjoint, color="C0", marker="o", ms=3.5, label="study, CPU")
    axis.loglog(source_ratio, sionna, color="C3", marker="o", ms=3.5, label="Sionna, A6000")
    for source_count in (5_002, 9_668, 25_782):
        if source_count not in sources:
            continue
        index = int(np.flatnonzero(sources == source_count)[0])
        ratio = sionna[index] / adjoint[index]
        axis.annotate(
            f"{ratio:.1f}$\\times$",
            (source_ratio[index], sionna[index]),
            xytext=(0, 7),
            textcoords="offset points",
            ha="center",
            fontsize=7,
        )
    axis.set_xlabel("sources per receiver")
    axis.set_ylabel("warmed seconds per seed")
    axis.legend(frameon=False, loc="upper left")
    axis.set_title("a  source scaling", loc="left")


def _sionna_convergence(axis: plt.Axes) -> None:
    budget_rows = _load("sionna_source_budget_gpu.json")["rows"]
    coarse = next(row["sionna"] for row in budget_rows if row["sources"] == 2_187)
    tuned = _load("sionna_accuracy_threshold_gpu.json")["rows"][0]["sionna"]
    reference = np.asarray(tuned["per_source_10000"]["total"]["mean"], dtype=np.float64)
    entries = {}
    for payload in (coarse, tuned):
        for value in payload.values():
            budget = int(value["samples_per_source"])
            if budget >= 10_000:
                continue
            if payload is coarse and budget >= 2_500:
                continue
            mean = np.asarray(value["total"]["mean"], dtype=np.float64)
            residual = np.abs(10.0 * np.log10(mean / reference))
            entries[budget] = (float(np.median(residual)), float(np.max(residual)))
    budgets = np.asarray(sorted(entries), dtype=np.float64)
    median = np.asarray([entries[int(budget)][0] for budget in budgets])
    maximum = np.asarray([entries[int(budget)][1] for budget in budgets])

    axis.loglog(budgets, median, color="C3", marker="o", ms=3.5, label="median receiver")
    axis.loglog(budgets, maximum, color="C3", marker="^", ms=3.5, ls="--", label="worst receiver")
    axis.axhline(0.1, color="0.35", lw=0.8, ls=":", label="0.1 dB rule")
    axis.axvline(3_000, color="C0", lw=0.8, ls="--")
    axis.set_xlabel("Sionna samples per source")
    axis.set_ylabel("shift from 10k reference (dB)")
    axis.legend(frameon=False, loc="upper right")
    axis.set_title("b  Sionna convergence", loc="left")


def _variance_cost(axis: plt.Axes) -> None:
    adjoint_rows = _load("adjoint_ray_budget_gpu_host.json")["rows"]
    tuned = _load("sionna_accuracy_threshold_gpu.json")["rows"][0]["sionna"]

    adjoint_time = np.asarray([row["metrics"]["seconds_warmed_mean"] for row in adjoint_rows])
    adjoint_sd = np.asarray([row["metrics"]["median_single_seed_sd_db"] for row in adjoint_rows])
    adjoint_rays = np.asarray([row["rays"] for row in adjoint_rows])
    sionna_values = sorted(tuned.values(), key=lambda value: value["samples_per_source"])
    sionna_time = np.asarray([value["metrics"]["seconds_warmed_mean"] for value in sionna_values])
    sionna_sd = np.asarray([value["metrics"]["median_single_seed_sd_db"] for value in sionna_values])
    sionna_budget = np.asarray([value["samples_per_source"] for value in sionna_values])

    axis.scatter(adjoint_time, adjoint_sd, color="C0", marker="o", s=22, label="study, CPU")
    axis.scatter(sionna_time, sionna_sd, color="C3", marker="o", s=22, label="Sionna, A6000")
    axis.set_xscale("log")
    axis.set_yscale("log")
    for time_s, spread, rays in zip(adjoint_time, adjoint_sd, adjoint_rays, strict=True):
        if rays in (50_000, 100_000):
            offset = (-26, 12) if rays == 100_000 else (4, 1)
            axis.annotate(f"{rays // 1000}k", (time_s, spread), xytext=offset, textcoords="offset points", fontsize=6.5)
    for time_s, spread, budget in zip(sionna_time, sionna_sd, sionna_budget, strict=True):
        if budget in (2_500, 3_000):
            offset = (8, 9) if budget == 2_500 else (5, -8)
            label = "2500, biased" if budget == 2_500 else "3000"
            axis.annotate(label, (time_s, spread), xytext=offset, textcoords="offset points", fontsize=6.5)
    axis.set_xlabel("warmed seconds per seed")
    axis.set_ylabel("median single-run spread (dB)")
    axis.legend(frameon=False, loc="upper right")
    axis.set_title("c  variance misses search bias", loc="left")


def main() -> None:
    apply_monograph_style()
    figure, axes = plt.subplots(
        1,
        3,
        figsize=fig_size_ieee(columns=2, aspect=0.34),
        constrained_layout=True,
    )
    _source_scaling(axes[0])
    _sionna_convergence(axes[1])
    _variance_cost(axes[2])
    for suffix in (".pdf", ".png"):
        figure.savefig(OUT / f"29_sionna_source_scaling{suffix}", dpi=300)
    print(f"wrote {OUT / '29_sionna_source_scaling.pdf'}")


if __name__ == "__main__":
    main()
