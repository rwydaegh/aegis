"""Authenticate and stage the compact roofline-budget sensitivity figure.

The numerical reporter owns the figure. This wrapper verifies the report and
its artifact manifest before copying the PDF and PNG into the paper tree. It
then writes a small paper-facing audit. Run with ``--check`` to validate the
source without writing figure assets.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np


SEMANTIC_TWIN_ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
PAPER_ROOT = HERE.parents[1]
REPORT_DIR = SEMANTIC_TWIN_ROOT / "outputs" / "experiments" / "roofline_budget_sensitivity_v1"
REPORT = REPORT_DIR / "roofline_budget_sensitivity_v1.json"
MANIFEST = REPORT_DIR / "roofline_budget_sensitivity_v1_manifest.json"
SOURCE_PDF = REPORT_DIR / "roofline_budget_sensitivity_v1.pdf"
SOURCE_PNG = REPORT_DIR / "roofline_budget_sensitivity_v1.png"
OUTPUT_PDF = HERE / "budget_sensitivity.pdf"
OUTPUT_PNG = HERE / "budget_sensitivity.png"
AUDIT = HERE / "budget_sensitivity.audit.json"

REPORT_SCHEMA = "aegis.roofline-budget-sensitivity-report.v1"
MANIFEST_SCHEMA = "aegis.roofline-budget-sensitivity-artifacts.v1"
EXPECTED_ARMS = ((25_000, 4096), (50_000, 4096), (100_000, 4096), (200_000, 1024), (200_000, 2048))
EXPECTED_DIRECTIONAL_Q90 = {
    (25_000, 4096): 0.8774980143368515,
    (50_000, 4096): 0.6789419645795945,
    (100_000, 4096): 0.40021795550889805,
    (200_000, 1024): 0.49126480809041534,
    (200_000, 2048): 0.45543106112995413,
}

sys.path.insert(0, str(PAPER_ROOT / "figures"))
from _style.paper_style import paper_style, save_figure  # noqa: E402


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def _artifact(manifest: dict[str, Any], path: Path) -> dict[str, Any]:
    record = manifest.get("artifacts", {}).get(path.name)
    if not isinstance(record, dict):
        raise ValueError(f"manifest has no record for {path.name}")
    if not path.is_file():
        raise ValueError(f"missing report artifact: {path}")
    if path.stat().st_size != int(record["bytes"]):
        raise ValueError(f"byte count mismatch: {path}")
    if _sha256(path) != record["sha256"]:
        raise ValueError(f"SHA-256 mismatch: {path}")
    return record


def authenticate() -> dict[str, Any]:
    """Return a compact, authenticated report summary for the manuscript."""
    report = _read_json(REPORT)
    manifest = _read_json(MANIFEST)
    if report.get("schema") != REPORT_SCHEMA:
        raise ValueError("unexpected budget-sensitivity report schema")
    if manifest.get("schema") != MANIFEST_SCHEMA or manifest.get("report_schema") != REPORT_SCHEMA:
        raise ValueError("unexpected budget-sensitivity manifest schema")
    if report.get("baseline") != {"rays": 200_000, "cells": 4096}:
        raise ValueError("report does not retain the declared production baseline")
    artifacts = {path.name: _artifact(manifest, path) for path in (REPORT, SOURCE_PDF, SOURCE_PNG)}
    arms = {(int(row["rays"]), int(row["cells"])): row for row in report.get("budgets", [])}
    if not set(EXPECTED_ARMS).issubset(arms):
        raise ValueError("report lacks a required cheaper budget arm")

    directional_q90: dict[str, float] = {}
    for arm, expected in EXPECTED_DIRECTIONAL_Q90.items():
        row = arms[arm]
        values = [
            float(site["directional_first_diffuse"]["normalized_l1_quantiles"]["q90"]) for site in row["sites"].values()
        ]
        maximum = max(values)
        if abs(maximum - expected) > 1.0e-12 or maximum <= 0.1:
            raise ValueError(f"directional gate evidence drifted for {arm}")
        if row["recommendation"]["migration_recommended"] is not False:
            raise ValueError(f"report unexpectedly recommends migrating {arm}")
        if not all(site["deterministic_invariance"]["status"] == "pass" for site in row["sites"].values()):
            raise ValueError(f"deterministic invariance failed for {arm}")
        directional_q90[f"rays_{arm[0]}_cells_{arm[1]}"] = maximum

    parity = report.get("sealed_baseline_replay_parity", {})
    if not parity or not all(row.get("status") == "pass" for row in parity.values()):
        raise ValueError("sealed baseline replay parity failed")
    return {
        "source_report_sha256": artifacts[REPORT.name]["sha256"],
        "source_manifest_sha256": _sha256(MANIFEST),
        "schedule_identity_sha256": manifest["schedule_identity_sha256"],
        "directional_q90_normalized_l1_max": directional_q90,
        "baseline_replay_parity": "pass",
        "source_artifacts": artifacts,
    }


def _plot_report(report: dict[str, Any]) -> None:
    sites = (
        ("madrid_plazamayor", "Madrid", "#0072B2"),
        ("mexico_zocalo", "Mexico City", "#D55E00"),
        ("prague_staromestske", "Prague", "#009E73"),
    )
    rows = report["budgets"]
    labels = [f"{row['rays'] // 1000}k\n{row['cells']:,}" for row in rows]
    x = np.arange(len(rows))

    def db_change_to_percent(value: float) -> float:
        """Convert a power-ratio change in decibels to a relative percentage."""
        return 100.0 * (10.0 ** (float(value) / 10.0) - 1.0)

    # The manuscript uses this as a full-width thesis figure.  Explicit inches
    # preserve readable type when LaTeX places it at the thesis text width.
    with paper_style("double", height_ratio=0.72, use_tex=True):
        plt.rcParams["figure.constrained_layout.use"] = False
        figure, axes = plt.subplots(2, 2, figsize=(4.55, 3.65), sharex=True)
        city_lines = []
        for site, label, color in sites:
            q50 = [
                db_change_to_percent(row["sites"][site]["normalized_wbSAR"]["route_quantile_difference_db"]["q50"])
                for row in rows
            ]
            directional = [
                row["sites"][site]["directional_first_diffuse"]["normalized_l1_quantiles"]["q90"] for row in rows
            ]
            timing = [row["sites"][site]["timing"]["estimator_wall_seconds"]["ratio"] for row in rows]
            (line,) = axes[0, 0].plot(x, q50, marker="o", markersize=3.4, color=color, label=label)
            city_lines.append(line)
            axes[1, 0].plot(x, directional, marker="o", markersize=3.4, color=color)
            axes[1, 1].plot(x, timing, marker="o", markersize=3.4, color=color)

        # The route-wide maximum is dominated by Mexico City's three fully
        # shadowed points. Showing that controlling case alone avoids an
        # unreadable axis with the other two curves compressed against zero.
        mexico = "mexico_zocalo"
        shadow = [db_change_to_percent(row["sites"][mexico]["normalized_wbSAR"]["maximum_absolute_db"]) for row in rows]
        axes[0, 1].plot(x, shadow, marker="s", markersize=3.4, color="#D55E00", linestyle="--")

        axes[0, 0].set_title("(a) Route-median SAR", loc="left")
        axes[0, 0].set_ylabel(r"Median deviation (\%)")
        axes[0, 1].set_title("(b) Mexico City shadow points", loc="left")
        axes[0, 1].set_ylabel(r"Largest deviation (\%)")
        axes[1, 0].set_title("(c) Diffuse directionality", loc="left")
        axes[1, 0].set_ylabel("90th-percentile\nnormalized L1")
        axes[1, 1].set_title("(d) Estimator time", loc="left")
        axes[1, 1].set_ylabel("Relative time\n(baseline = 1)")
        axes[0, 0].axhline(0.0, color="0.25", linewidth=0.7, zorder=0)
        axes[0, 1].set_ylim(bottom=0.0)
        axes[1, 0].set_ylim(bottom=0.0)
        axes[1, 1].axhline(1.0, color="0.25", linewidth=0.7, zorder=0)
        for axis in axes.flat:
            axis.set_xlim(-0.25, len(rows) - 0.75)
            axis.set_xticks(x, labels)
            axis.grid(axis="y", color="0.86", linewidth=0.45)
            axis.axvline(2.5, color="0.72", linewidth=0.65, linestyle=":", zorder=0)
            axis.tick_params(axis="x", pad=2.0)
        figure.supxlabel("Primary rays / angular cells", y=0.165)
        legend = figure.legend(
            city_lines,
            [line.get_label() for line in city_lines],
            loc="lower center",
            bbox_to_anchor=(0.5, 0.018),
            ncol=3,
            frameon=True,
            fancybox=False,
            framealpha=1.0,
            edgecolor="black",
            facecolor="white",
            borderpad=0.45,
            handlelength=2.2,
            columnspacing=1.5,
        )
        legend.get_frame().set_linewidth(0.8)
        figure.subplots_adjust(left=0.145, right=0.985, bottom=0.31, top=0.95, wspace=0.38, hspace=0.40)
        save_figure(figure, OUTPUT_PDF)
        save_figure(figure, OUTPUT_PNG, dpi=300)
        plt.close(figure)


def stage() -> dict[str, Any]:
    """Plot authenticated report values and write their paper-facing audit."""
    audit = authenticate()
    HERE.mkdir(parents=True, exist_ok=True)
    _plot_report(_read_json(REPORT))
    audit["schema_version"] = "roofline_budget_sensitivity_figure_audit_v1"
    audit["outputs"] = {
        "pdf": {"path": OUTPUT_PDF.name, "bytes": OUTPUT_PDF.stat().st_size, "sha256": _sha256(OUTPUT_PDF)},
        "png": {"path": OUTPUT_PNG.name, "bytes": OUTPUT_PNG.stat().st_size, "sha256": _sha256(OUTPUT_PNG)},
    }
    AUDIT.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return audit


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="authenticate source files without staging assets")
    args = parser.parse_args(argv)
    audit = authenticate() if args.check else stage()
    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
