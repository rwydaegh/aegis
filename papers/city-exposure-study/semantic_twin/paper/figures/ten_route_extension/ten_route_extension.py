"""Plot the authenticated ten-route production-contract extension."""

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
REPORT_DIR = SEMANTIC_TWIN_ROOT / "outputs" / "experiments" / "ten_city_route_extension64_v1" / "report"
REPORT_PATH = REPORT_DIR / "ten_city_route_production64_v1.json"
MANIFEST_PATH = REPORT_DIR / "ten_city_route_production64_v1_manifest.json"
EXPECTED_MANIFEST_SHA256 = "595ffe0404517c824a231b565e7528ff799503f3beb74052168b11c7ea3e91b6"
OUTPUT_PDF = HERE / "ten_route_extension.pdf"
OUTPUT_PNG = HERE / "ten_route_extension.png"
AUDIT_PATH = HERE / "ten_route_extension.audit.json"

sys.path.insert(0, str(PAPER_ROOT / "figures"))
from _style.paper_style import paper_style, save_figure  # noqa: E402

SITE_ORDER = (
    "Ghent",
    "Prague",
    "Madrid",
    "Mexico City",
    "Tokyo Hachiko",
    "Brussels",
    "London",
    "Milan",
    "Krakow",
    "Toulouse",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_report() -> dict:
    if _sha256(MANIFEST_PATH) != EXPECTED_MANIFEST_SHA256:
        raise ValueError("ten-route artifact manifest hash mismatch")
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != "roofline_multicity_artifacts_v1" or len(manifest.get("sources", {})) != 10:
        raise ValueError("unexpected ten-route artifact manifest")
    for name, record in manifest["artifacts"].items():
        path = REPORT_DIR / name
        if path.stat().st_size != record["bytes"] or _sha256(path) != record["sha256"]:
            raise ValueError(f"ten-route artifact failed authentication: {path}")
    report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    if report.get("schema_version") != "roofline_multicity_results_v1" or set(report.get("cities", {})) != set(
        SITE_ORDER
    ):
        raise ValueError("unexpected ten-route report contract")
    return report


def _component_shares(city: dict) -> dict[str, float]:
    sums = {component: 0.0 for component in ("direct", "all_specular", "first_diffuse", "total")}
    for point in city["route"]:
        for component in sums:
            sums[component] += float(point["component_body"][component]["absorbed_power_w"])
    return {component: sums[component] / sums["total"] for component in sums if component != "total"}


def _plot(report: dict) -> None:
    cities = [report["cities"][name] for name in SITE_ORDER]
    y = np.arange(len(cities))
    quantiles = [city["route_quantile_uncertainty"]["quantiles"]["wbsar"] for city in cities]
    q10 = np.asarray([row["q10"]["estimate"] for row in quantiles])
    q50 = np.asarray([row["q50"]["estimate"] for row in quantiles])
    q90 = np.asarray([row["q90"]["estimate"] for row in quantiles])
    shares = [_component_shares(city) for city in cities]

    with paper_style("double", height_ratio=0.54, use_tex=True):
        figure, (distribution, components) = plt.subplots(1, 2, gridspec_kw={"width_ratios": (1.16, 0.84)})
        distribution.hlines(y, q10, q90, color="#6B7280", linewidth=2.0)
        distribution.plot(q50, y, "o", color="#000000", markerfacecolor="none", markeredgewidth=0.9)
        distribution.set_yticks(y, SITE_ORDER)
        distribution.invert_yaxis()
        distribution.set_xscale("log")
        distribution.set_xlabel(r"Normalized wbSAR per unit $\rho_A P_{\mathrm{EIRP}}$ (m$^2$ kg$^{-1}$)")
        distribution.set_title(r"(a) Route $q_{10}$, $q_{50}$, and $q_{90}$", loc="left")
        distribution.grid(axis="x", color="0.86", linewidth=0.45)
        distribution.grid(axis="y", visible=False)

        left = np.zeros(len(cities), dtype=np.float64)
        colors = {"direct": "#000000", "all_specular": "#FF0000", "first_diffuse": "#00C000"}
        labels = {"direct": "Direct", "all_specular": "Order-1 specular", "first_diffuse": "First diffuse"}
        for component in ("direct", "all_specular", "first_diffuse"):
            values = 100.0 * np.asarray([row[component] for row in shares])
            components.barh(y, values, left=100.0 * left, color=colors[component], label=labels[component])
            left += values / 100.0
        components.invert_yaxis()
        components.set_yticks([])
        components.set_xlim(0.0, 100.0)
        components.set_xlabel(r"Route-summed absorbed-power share (\%)")
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
    rows = [report["cities"][name] for name in SITE_ORDER]
    q50 = {
        name: report["cities"][name]["route_quantile_uncertainty"]["quantiles"]["wbsar"]["q50"]["estimate"]
        for name in SITE_ORDER
    }
    shares = {name: _component_shares(report["cities"][name]) for name in SITE_ORDER}
    audit = {
        "schema": "paper_ten_route_extension_figure_v1",
        "source": {
            "report": str(REPORT_PATH.relative_to(SEMANTIC_TWIN_ROOT)),
            "report_sha256": _sha256(REPORT_PATH),
            "manifest": str(MANIFEST_PATH.relative_to(SEMANTIC_TWIN_ROOT)),
            "manifest_sha256": _sha256(MANIFEST_PATH),
        },
        "contract": {
            "routes": len(rows),
            "standpoints": sum(int(row["standpoints"]) for row in rows),
            "replicas_per_route": sorted({int(row["replicas"]) for row in rows}),
        },
        "route_q50_wbsar": q50,
        "component_shares": shares,
        "outputs": {
            OUTPUT_PDF.name: {"bytes": OUTPUT_PDF.stat().st_size, "sha256": _sha256(OUTPUT_PDF)},
            OUTPUT_PNG.name: {"bytes": OUTPUT_PNG.stat().st_size, "sha256": _sha256(OUTPUT_PNG)},
        },
    }
    AUDIT_PATH.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
