"""Plot the authenticated material-label coverage report with paper terminology."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[3]
FIGURE_DIR = Path(__file__).resolve().parent
PAPER_ROOT = FIGURE_DIR.parents[1]
SOURCE_DIR = ROOT / "outputs" / "experiments" / "ray_reached_evidence_coverage_v1" / "report"
SOURCE_STEM = "ray_reached_evidence_coverage"
OUTPUT_STEM = "ray_reached_evidence"

sys.path.insert(0, str(PAPER_ROOT / "figures"))
from _style.paper_style import paper_style, save_figure  # noqa: E402


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_report() -> tuple[dict, Path, Path]:
    manifest_path = SOURCE_DIR / f"{SOURCE_STEM}_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema") != "ray_reached_evidence_coverage_artifacts_v1":
        raise ValueError("unexpected ray-reached report manifest schema")
    for record in manifest["files"]:
        source = SOURCE_DIR / record["path"]
        if source.stat().st_size != record["bytes"] or _sha256(source) != record["sha256"]:
            raise ValueError(f"ray-reached report artifact failed authentication: {source}")

    report_path = SOURCE_DIR / f"{SOURCE_STEM}.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if report.get("schema") != "ray_reached_evidence_coverage_v1" or not report.get("complete"):
        raise ValueError("ray-reached report is incomplete")
    return report, report_path, manifest_path


def _plot(report: dict) -> None:
    categories = report["pooled"]["non_direct"]["categories"]
    body_values = 100.0 * np.asarray(
        (
            report["headline"]["panorama_informed_sar_fraction"],
            report["headline"]["geometric_fallback_sar_fraction"],
        )
    )
    category_keys = (
        "atlas_interface",
        "geometric_no_panorama_evidence",
        "geometric_evidence_refused_host_compatibility",
        "geometric_evidence_refused_insufficient_structural_mass",
        "geometric_evidence_refused_atlas_state",
        "geometric_fallback_other",
        "nonblocking_woody_atlas",
    )
    category_labels = (
        "Image-mapped surface",
        "No image label",
        "Object-material mismatch",
        "Too little structure",
        "Image-label rejection",
        "Other geometry fallback",
        "Nonblocking woody",
    )
    counts_million = np.asarray([categories[key]["event_count"] for key in category_keys]) / 1.0e6

    with paper_style("double", height_ratio=0.38, use_tex=True):
        figure, (left, right) = plt.subplots(1, 2, gridspec_kw={"width_ratios": (0.72, 1.28)})
        left.bar((0, 1), body_values, color=("#0072B2", "#D55E00"), width=0.78)
        left.set_xticks((0, 1), ("Image-mapped", "Geometry-based"))
        left.set_ylabel(r"Non-direct body-coupled share (\%)")
        left.set_ylim(0.0, 100.0)
        left.set_title("(a) Body contribution", loc="left")
        left.grid(axis="y", color="0.86", linewidth=0.45)
        left.grid(axis="x", visible=False)

        positions = np.arange(len(category_labels))
        right.barh(positions, counts_million, color="#009E73", height=0.76)
        right.set_yticks(positions, category_labels)
        right.invert_yaxis()
        right.set_xlabel("Accepted interactions (million)")
        right.set_title("(b) Pooled event counts", loc="left")
        right.grid(axis="x", color="0.86", linewidth=0.45)
        right.grid(axis="y", visible=False)
        right.set_xlim(0.0, 1.05 * counts_million.max())

        save_figure(figure, FIGURE_DIR / f"{OUTPUT_STEM}.pdf")
        save_figure(figure, FIGURE_DIR / f"{OUTPUT_STEM}.png", dpi=300)
        plt.close(figure)


def main() -> None:
    report, report_path, manifest_path = _load_report()
    _plot(report)
    outputs = {}
    for suffix in ("pdf", "png"):
        output = FIGURE_DIR / f"{OUTPUT_STEM}.{suffix}"
        outputs[suffix] = {
            "path": output.name,
            "bytes": output.stat().st_size,
            "sha256": _sha256(output),
        }
    audit = {
        "schema": "paper_ray_reached_evidence_figure_v1",
        "source": {
            "report_path": str(report_path.relative_to(ROOT)),
            "report_sha256": _sha256(report_path),
            "manifest_path": str(manifest_path.relative_to(ROOT)),
            "manifest_sha256": _sha256(manifest_path),
        },
        "headline": report["headline"],
        "label_policy": "reader-facing image and material terms; report keys remain unchanged",
        "outputs": outputs,
    }
    (FIGURE_DIR / f"{OUTPUT_STEM}.audit.json").write_text(
        json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
