"""Plot the authenticated fixed-grid diagnostic for the supplement."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent
SEMANTIC_TWIN_ROOT = HERE.parents[2]
PAPER_ROOT = HERE.parents[1]
REPORT_DIR = SEMANTIC_TWIN_ROOT / "outputs" / "experiments" / "ten_city_geometry_screen_64_v1" / "report"
REPORT_PATH = REPORT_DIR / "ten_city_geometry_screen_64_v1.json"
MANIFEST_PATH = REPORT_DIR / "ten_city_geometry_screen_64_v1_manifest.json"
EXPECTED_MANIFEST_SHA256 = "3e29d721e77de435da54a8881cf81ecf1a9ed6f8ee2b7df025caca2c9417dbb9"
OUTPUT_PDF = HERE / "geometric_screening.pdf"
OUTPUT_PNG = HERE / "geometric_screening.png"
AUDIT_PATH = HERE / "geometric_screening.audit.json"

sys.path.insert(0, str(PAPER_ROOT / "figures"))
from _style.paper_style import paper_style, save_figure  # noqa: E402

DISPLAY_NAMES = {
    "korenmarkt": "Ghent",
    "prague_staromestske": "Prague",
    "brussels_grandplace": "Brussels",
    "madrid_plazamayor": "Madrid",
    "mexico_zocalo": "Mexico City",
    "tokyo_hachiko": "Tokyo Hachiko",
    "london_trafalgar": "London",
    "milan_duomo": "Milan",
    "krakow_rynek": "Krakow",
    "toulouse_capitole": "Toulouse",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_report() -> dict:
    if _sha256(MANIFEST_PATH) != EXPECTED_MANIFEST_SHA256:
        raise ValueError("fixed-grid artifact manifest hash mismatch")
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    if (
        not manifest.get("authenticated")
        or manifest.get("schema_version") != "geometric_fixed_grid_screening_64_artifacts_v1"
    ):
        raise ValueError("fixed-grid artifact manifest is not authenticated")
    for name, record in manifest["artifacts"].items():
        path = REPORT_DIR / name
        if path.stat().st_size != record["bytes"] or _sha256(path) != record["sha256"]:
            raise ValueError(f"fixed-grid artifact failed authentication: {path}")
    report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    if report.get("schema_version") != "geometric_fixed_grid_screening_64_report_v1":
        raise ValueError("unexpected fixed-grid report schema")
    return report


def _plot(report: dict) -> None:
    site_order = report["screening_contract"]["sites"]
    y = np.arange(len(site_order))
    q10 = np.asarray([report["sites"][site]["normalized_wbsar_quantiles"]["q10"]["estimate"] for site in site_order])
    q50 = np.asarray([report["sites"][site]["normalized_wbsar_quantiles"]["q50"]["estimate"] for site in site_order])
    q90 = np.asarray([report["sites"][site]["normalized_wbsar_quantiles"]["q90"]["estimate"] for site in site_order])
    q50_se = np.asarray(
        [report["sites"][site]["normalized_wbsar_quantiles"]["q50"]["seed_standard_error"] for site in site_order]
    )

    with paper_style("double", height_ratio=0.54, use_tex=True):
        figure, (distribution, components) = plt.subplots(1, 2, gridspec_kw={"width_ratios": (1.18, 0.82)})
        distribution.hlines(y, q10, q90, color="#6B7280", linewidth=2.0)
        distribution.errorbar(q50, y, xerr=q50_se, fmt="o", color="#111827", ecolor="#D62728", capsize=2.0)
        distribution.set_yticks(y, [DISPLAY_NAMES[site] for site in site_order])
        distribution.invert_yaxis()
        distribution.set_xscale("log")
        distribution.set_xlabel(r"Normalized wbSAR per unit $\rho_A P_{\mathrm{EIRP}}$ (m$^2$ kg$^{-1}$)")
        distribution.set_title(r"(a) Fixed-point $q_{10}$, $q_{50}$, and $q_{90}$", loc="left")
        distribution.grid(axis="x", color="0.86", linewidth=0.45)
        distribution.grid(axis="y", visible=False)

        left = np.zeros(len(site_order), dtype=np.float64)
        colors = {"direct": "#0072B2", "all_specular": "#D55E00", "first_diffuse": "#009E73"}
        labels = {"direct": "Direct", "all_specular": "Order-1 specular", "first_diffuse": "First diffuse"}
        for component in ("direct", "all_specular", "first_diffuse"):
            shares = np.asarray(
                [report["sites"][site]["normalized_wbsar_component_shares"][component] for site in site_order]
            )
            components.barh(y, 100.0 * shares, left=100.0 * left, color=colors[component], label=labels[component])
            left += shares
        components.invert_yaxis()
        components.set_yticks([])
        components.set_xlim(0.0, 100.0)
        components.set_xlabel(r"Pooled normalized wbSAR share (\%)")
        components.set_title("(b) First-interaction components", loc="left")
        components.legend(loc="lower center", bbox_to_anchor=(0.5, -0.17), ncol=3)
        components.grid(axis="x", color="0.86", linewidth=0.45)
        components.grid(axis="y", visible=False)

        save_figure(figure, OUTPUT_PDF)
        save_figure(figure, OUTPUT_PNG, dpi=300)
        plt.close(figure)


def main() -> None:
    report = _load_report()
    _plot(report)
    sites = list(report["sites"].values())
    quantile_spans = {
        name: max(site["normalized_wbsar_quantiles"][name]["estimate"] for site in sites)
        / min(site["normalized_wbsar_quantiles"][name]["estimate"] for site in sites)
        for name in ("q10", "q50", "q90")
    }
    component_ranges = {
        component: [
            min(site["normalized_wbsar_component_shares"][component] for site in sites),
            max(site["normalized_wbsar_component_shares"][component] for site in sites),
        ]
        for component in ("direct", "all_specular", "first_diffuse")
    }
    audit = {
        "schema": "paper_geometric_fixed_grid_figure_v2",
        "source": {
            "report": str(REPORT_PATH.relative_to(SEMANTIC_TWIN_ROOT)),
            "report_sha256": _sha256(REPORT_PATH),
            "manifest": str(MANIFEST_PATH.relative_to(SEMANTIC_TWIN_ROOT)),
            "manifest_sha256": _sha256(MANIFEST_PATH),
        },
        "quantile_span_factors": quantile_spans,
        "component_share_ranges": component_ranges,
        "outputs": {
            OUTPUT_PDF.name: {"bytes": OUTPUT_PDF.stat().st_size, "sha256": _sha256(OUTPUT_PDF)},
            OUTPUT_PNG.name: {"bytes": OUTPUT_PNG.stat().st_size, "sha256": _sha256(OUTPUT_PNG)},
        },
    }
    AUDIT_PATH.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
