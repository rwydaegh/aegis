"""Publication result figures for paired roofline campaigns.

The campaign comparator is the only reader of replica shards.  This module
turns its validated report into a compact four-panel result figure and small,
machine-readable exports.  Exposure values are deliberately kept on the
``rho_A P_EIRP`` normalized scale used by the campaign contract.

Example::

    python -m semantic_twin.cli.roofline_result_figures \
        --city korenmarkt outputs/korenmarkt_iid outputs/korenmarkt_fibonacci \
        --city prague outputs/prague_iid outputs/prague_fibonacci \
        --output outputs/paper/roofline_results
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from .roofline_campaign_comparison import (
    CampaignComparisonError,
    REPORT_SCHEMA_VERSION,
    compare_campaigns,
)

RESULT_SCHEMA_VERSION = "roofline_publication_results_v1"
NORMALIZATION = "per unit rho_A P_EIRP"
UNIT_DIMENSIONLESS = "1"
UNIT_WBSAR = "m² kg⁻¹"
DEFAULT_LOOKS = (4, 8, 12, 16)
SAMPLERS = ("iid", "rotated_fibonacci")
SAMPLER_LABELS = {"iid": "IID", "rotated_fibonacci": "rotated Fibonacci"}
SAMPLER_STYLES = {"iid": "-", "rotated_fibonacci": "--"}

# Okabe-Ito colours, retained across every panel so city identity is readable
# in greyscale by the accompanying sampler line style.
CITY_COLORS = (
    "#0072B2",
    "#D55E00",
    "#009E73",
    "#CC79A7",
    "#E69F00",
    "#56B4E9",
)

_BODY_METRIC_KEYS = {
    "mean_sab_w_m2": "mean Sab",
    "absorbed_power_w": "absorbed power",
    "sar_wb_w_kg": "wbSAR",
}
_TABLE_METRIC_KEYS = {
    "peak_sab_w_m2": ("peak Sab", UNIT_DIMENSIONLESS),
    "mean_sab_w_m2": ("mean Sab", UNIT_DIMENSIONLESS),
    "absorbed_power_w": ("absorbed power", "m²"),
    "sar_wb_w_kg": ("wbSAR", UNIT_WBSAR),
}


@dataclass(frozen=True)
class CampaignPair:
    """One city's paired IID and rotated-Fibonacci campaign directories."""

    city: str
    iid_directory: Path
    rotated_fibonacci_directory: Path


@dataclass(frozen=True)
class FigureArtifacts:
    """Paths written by :func:`write_publication_results`."""

    pdf: Path
    png: Path
    json: Path
    csv: Path
    latex: Path


def _finite_array(values: Any) -> np.ndarray:
    """Coerce comparator values and discard explicit unavailable entries."""
    array = np.asarray(values, dtype=object).ravel()
    finite: list[float] = []
    for value in array:
        if value is None:
            continue
        try:
            number = float(value)
        except (TypeError, ValueError):
            continue
        if np.isfinite(number):
            finite.append(number)
    return np.asarray(finite, dtype=np.float64)


def _json_number(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if np.isfinite(number) else None


def _city_label(city: str) -> str:
    return " ".join(part.capitalize() for part in city.replace("_", " ").split())


def _cdf(values: Any) -> dict[str, list[float]]:
    array = np.sort(_finite_array(values))
    if array.size == 0:
        return {"x": [], "cdf": []}
    return {
        "x": [float(value) for value in array],
        "cdf": [float(value) for value in (np.arange(array.size) + 0.5) / array.size],
    }


def _campaign_metric(report: Mapping[str, Any], look: int, sampler: str, metric: str) -> list[float]:
    values = report["looks"][str(look)]["linear_db_differences"]["body_metrics"]["total"][metric][f"{sampler}_linear"]
    return [float(value) for value in _finite_array(values)]


def _campaign_transfer(report: Mapping[str, Any], look: int, sampler: str, component: str) -> np.ndarray:
    values = report["looks"][str(look)]["linear_db_differences"]["raw_transfer"][component][f"{sampler}_linear"]
    return _finite_array(values)


def _normalised_surplus(report: Mapping[str, Any], look: int, sampler: str) -> list[float]:
    total = _campaign_transfer(report, look, sampler, "total")
    direct = _campaign_transfer(report, look, sampler, "direct")
    if total.shape != direct.shape:
        raise CampaignComparisonError("validated comparator report has unpaired total and direct route arrays")
    valid = (total > 0.0) & (direct > 0.0)
    return [float(value) for value in (10.0 * np.log10(total[valid] / direct[valid]))]


def _require_report(report: Mapping[str, Any], looks: tuple[int, ...]) -> None:
    if report.get("schema_version") != REPORT_SCHEMA_VERSION:
        raise CampaignComparisonError("publication result requires a roofline campaign comparison report")
    report_looks = report.get("looks")
    if not isinstance(report_looks, Mapping):
        raise CampaignComparisonError("comparison report does not contain look reports")
    for look in looks:
        if str(look) not in report_looks:
            raise CampaignComparisonError(f"comparison report does not contain requested look {look}")


def _reference_mode(path: Path) -> str:
    """Read only the sealed mode after comparator validation.

    The comparator has already authenticated all campaign artifacts.  Reading
    this tiny identity document prevents a physical-scale campaign from being
    silently presented with normalized units.  Historical fixtures omitted the
    field and are the documented per-density default.
    """
    identity_path = path / "campaign_identity.json"
    if not identity_path.is_file():
        return "per_density_eirp"
    try:
        identity = json.loads(identity_path.read_text(encoding="utf-8"))
        mode = identity.get("data", {}).get("configuration", {}).get("reference_mode", "per_density_eirp")
    except (OSError, json.JSONDecodeError, AttributeError):
        raise CampaignComparisonError(f"campaign identity cannot be read for normalized-unit validation: {path}")
    if mode not in ("per_density_eirp", "physical"):
        raise CampaignComparisonError(f"unknown campaign reference mode: {mode!r}")
    return str(mode)


def _validate_normalized_pair(pair: CampaignPair) -> None:
    modes = {_reference_mode(pair.iid_directory), _reference_mode(pair.rotated_fibonacci_directory)}
    if modes != {"per_density_eirp"}:
        raise CampaignComparisonError(
            f"{pair.city}: publication exposure panels require reference_mode='per_density_eirp', got {sorted(modes)}"
        )


def _convergence_rows(report: Mapping[str, Any], sampler: str, looks: tuple[int, ...]) -> list[dict[str, Any]]:
    evidence = report["within_mode_convergence"][sampler]["standard_error"]
    rows: list[dict[str, Any]] = []
    for look in looks:
        transfer = evidence[str(look)]["total_transfer"]
        rows.append(
            {
                "look": look,
                "p90_db": _json_number(transfer.get("p90_db_delta_approximation")),
                "maximum_db": _json_number(transfer.get("maximum_db_delta_approximation")),
                "replicas": int(transfer.get("replicas", look)),
            }
        )
    return rows


def _variance_rows(report: Mapping[str, Any], look: int) -> dict[str, dict[str, Any]]:
    variance = report["looks"][str(look)]["across_seed_variance_ratios"]
    rows: dict[str, dict[str, Any]] = {}
    total = variance["total_raw_transfer"]["total"]
    rows["total_transfer"] = {"label": "total transfer", **dict(total.get("summary", {}))}
    body = variance["body_metrics"]["total"]
    for key, label in _BODY_METRIC_KEYS.items():
        rows[key] = {"label": label, **dict(body[key].get("summary", {}))}
    return rows


def _variance_data(report: Mapping[str, Any], look: int) -> dict[str, dict[str, Any]]:
    data: dict[str, dict[str, Any]] = {}
    for metric, summary in _variance_rows(report, look).items():
        data[metric] = {
            "label": summary["label"],
            **{
                key: (
                    int(summary[key])
                    if key == "count" and summary.get(key) is not None
                    else _json_number(summary.get(key))
                )
                for key in ("count", "minimum", "q10", "q50", "q90", "maximum")
            },
        }
    return data


def _table_data(report: Mapping[str, Any], sampler: str, look: int) -> dict[str, dict[str, Any]]:
    table: dict[str, dict[str, Any]] = {}
    for metric, (label, unit) in _TABLE_METRIC_KEYS.items():
        values = _campaign_metric(report, look, sampler, metric)
        table[metric] = {
            "label": label,
            "unit": unit,
            "normalization": NORMALIZATION,
            "look": look,
            "route_median": None if not values else float(np.median(values)),
        }
    return table


def _city_data(report: Mapping[str, Any], requested: tuple[int, ...], chosen: int) -> dict[str, Any]:
    _require_report(report, requested)
    data: dict[str, Any] = {
        "provenance": {
            "iid_directory": report.get("iid_directory"),
            "rotated_fibonacci_directory": report.get("rotated_fibonacci_directory"),
            "comparison_schema_version": report.get("schema_version"),
        },
        "surplus_cdf": {},
        "total_wbsar_cdf": {},
        "convergence": {},
        "variance_ratios": _variance_data(report, chosen),
        "table": {},
    }
    for sampler in SAMPLERS:
        data["surplus_cdf"][sampler] = _cdf(_normalised_surplus(report, chosen, sampler))
        data["total_wbsar_cdf"][sampler] = _cdf(_campaign_metric(report, chosen, sampler, "sar_wb_w_kg"))
        data["convergence"][sampler] = _convergence_rows(report, sampler, requested)
        data["table"][sampler] = _table_data(report, sampler, chosen)
    return data


def build_plot_data(
    reports: Mapping[str, Mapping[str, Any]],
    *,
    looks: Sequence[int] = DEFAULT_LOOKS,
    final_look: int | None = None,
) -> dict[str, Any]:
    """Build all plot and table data from validated comparator reports.

    ``reports`` is keyed by city and contains the return value of
    :func:`compare_campaigns`.  This split makes figure rendering testable with
    a small mock report and keeps artifact loading in the comparator.
    """
    requested = tuple(int(value) for value in looks)
    if not requested or tuple(sorted(set(requested))) != requested or requested[0] < 1:
        raise ValueError("looks must be unique, increasing, and positive")
    chosen = requested[-1] if final_look is None else int(final_look)
    if chosen not in requested:
        raise ValueError("final_look must be one of looks")

    cities = {str(city): _city_data(report, requested, chosen) for city, report in reports.items()}

    return {
        "schema_version": RESULT_SCHEMA_VERSION,
        "metadata": {
            "caption": (
                "Paired IID and rotated-Fibonacci roofline campaigns with a one-reflection transport limit. "
                "Body outputs are on the normalized per-unit rho_A P_EIRP scale and are not deployment values."
            ),
            "physics_scope": "direct plus diffuse and specular paths with at most one surface reflection",
            "normalization": NORMALIZATION,
            "normalization_units": {
                "total_wbsar": UNIT_WBSAR,
                "peak_sab": UNIT_DIMENSIONLESS,
                "mean_sab": UNIT_DIMENSIONLESS,
                "absorbed_power": "m²",
            },
            "sampler_line_styles": dict(SAMPLER_STYLES),
            "sampler_labels": dict(SAMPLER_LABELS),
        },
        "looks": list(requested),
        "final_look": chosen,
        "cities": cities,
    }


def collect_reports(
    campaigns: Sequence[CampaignPair], *, looks: Sequence[int] = DEFAULT_LOOKS
) -> dict[str, Mapping[str, Any]]:
    """Compare each paired campaign, rejecting non-normalized exposure runs."""
    reports: dict[str, Mapping[str, Any]] = {}
    requested = tuple(int(value) for value in looks)
    for pair in campaigns:
        if not pair.city or pair.city in reports:
            raise ValueError(f"city names must be non-empty and unique: {pair.city!r}")
        report = compare_campaigns(pair.iid_directory, pair.rotated_fibonacci_directory, looks=requested)
        _validate_normalized_pair(pair)
        reports[pair.city] = report
    if not reports:
        raise ValueError("at least one city campaign pair is required")
    return reports


def _cdf_csv_rows(city: str, city_data: Mapping[str, Any], sampler: str, look: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for panel in ("surplus_cdf", "total_wbsar_cdf"):
        curve = city_data[panel][sampler]
        unit = "dB" if panel == "surplus_cdf" else UNIT_WBSAR
        metric = "multipath_surplus" if panel == "surplus_cdf" else "total_wbsar"
        for x, cdf in zip(curve["x"], curve["cdf"], strict=True):
            rows.append(
                {
                    "city": city,
                    "panel": panel,
                    "sampler": sampler,
                    "metric": metric,
                    "look": look,
                    "x": x,
                    "cdf": cdf,
                    "value": "",
                    "unit": unit,
                    "normalization": NORMALIZATION,
                }
            )
    return rows


def _convergence_csv_rows(city: str, city_data: Mapping[str, Any], sampler: str) -> list[dict[str, Any]]:
    return [
        {
            "city": city,
            "panel": "convergence",
            "sampler": sampler,
            "metric": "total_transfer_p90_uncertainty",
            "look": point["look"],
            "x": "",
            "cdf": "",
            "value": point["p90_db"],
            "unit": "dB",
            "normalization": NORMALIZATION,
        }
        for point in city_data["convergence"][sampler]
    ]


def _table_csv_rows(city: str, city_data: Mapping[str, Any], sampler: str) -> list[dict[str, Any]]:
    return [
        {
            "city": city,
            "panel": "table",
            "sampler": sampler,
            "metric": metric,
            "look": summary["look"],
            "x": "",
            "cdf": "",
            "value": summary["route_median"],
            "unit": summary["unit"],
            "normalization": summary["normalization"],
        }
        for metric, summary in city_data["table"][sampler].items()
    ]


def _variance_csv_rows(city: str, city_data: Mapping[str, Any], look: int) -> list[dict[str, Any]]:
    return [
        {
            "city": city,
            "panel": "variance_ratio",
            "sampler": "rotated_fibonacci/iid",
            "metric": metric,
            "look": look,
            "x": "",
            "cdf": "",
            "value": summary.get("q50"),
            "unit": "Fibonacci/IID",
            "normalization": "variance ratio, no exposure scale",
        }
        for metric, summary in city_data["variance_ratios"].items()
    ]


def _sampler_csv_rows(city: str, city_data: Mapping[str, Any], sampler: str, look: int) -> list[dict[str, Any]]:
    return [
        *_cdf_csv_rows(city, city_data, sampler, look),
        *_convergence_csv_rows(city, city_data, sampler),
        *_table_csv_rows(city, city_data, sampler),
    ]


def _csv_rows(data: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for city, city_data in data["cities"].items():
        for sampler in SAMPLERS:
            rows.extend(_sampler_csv_rows(city, city_data, sampler, data["final_look"]))
        rows.extend(_variance_csv_rows(city, city_data, data["final_look"]))
    return rows


def _write_json(data: Mapping[str, Any], path: Path) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def _write_csv(data: Mapping[str, Any], path: Path) -> None:
    fields = ("city", "panel", "sampler", "metric", "look", "x", "cdf", "value", "unit", "normalization")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in _csv_rows(data):
            writer.writerow(row)


def _latex_number(value: Any) -> str:
    number = _json_number(value)
    return "--" if number is None else f"{number:.4g}"


def _latex_fragment(data: Mapping[str, Any]) -> str:
    lines = [
        "% Normalized roofline results: values are per unit rho_A P_EIRP, not deployment values.",
        "% Peak and mean Sab are dimensionless after division by rho_A P_EIRP; absorbed power and wbSAR retain the units below.",
        r"\begin{tabular}{llrrrr}",
        r"City & Sampler & peak $S_{ab}$ [1] & mean $S_{ab}$ [1] & absorbed [m$^2$] & wbSAR [m$^2$ kg$^{-1}$] \\",
        r"\hline",
    ]
    for city, city_data in data["cities"].items():
        for sampler in SAMPLERS:
            table = city_data["table"][sampler]
            lines.append(
                f"{_city_label(city)} & {SAMPLER_LABELS[sampler]} & "
                f"{_latex_number(table['peak_sab_w_m2']['route_median'])} & "
                f"{_latex_number(table['mean_sab_w_m2']['route_median'])} & "
                f"{_latex_number(table['absorbed_power_w']['route_median'])} & "
                f"{_latex_number(table['sar_wb_w_kg']['route_median'])} " + r"\\"
            )
    lines.extend([r"\end{tabular}", ""])
    return "\n".join(lines)


def _draw(data: Mapping[str, Any], pdf_path: Path, png_path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.ticker import FormatStrFormatter, MaxNLocator

    plt.rcParams.update(
        {
            "font.size": 8.0,
            "axes.labelsize": 8.0,
            "xtick.labelsize": 7.0,
            "ytick.labelsize": 7.0,
            "legend.fontsize": 6.5,
            "axes.spines.top": False,
            "axes.spines.right": False,
        }
    )
    cities = list(data["cities"])
    colors = {city: CITY_COLORS[index % len(CITY_COLORS)] for index, city in enumerate(cities)}
    figure, axes = plt.subplots(2, 2, figsize=(7.1, 5.0), constrained_layout=True)
    ax_surplus, ax_sar, ax_conv, ax_var = axes.flat

    for city in cities:
        city_data = data["cities"][city]
        city_label = _city_label(city)
        for sampler in SAMPLERS:
            label = f"{city_label}, {SAMPLER_LABELS[sampler]}"
            style = SAMPLER_STYLES[sampler]
            ax_surplus.step(
                city_data["surplus_cdf"][sampler]["x"],
                city_data["surplus_cdf"][sampler]["cdf"],
                where="post",
                color=colors[city],
                linestyle=style,
                linewidth=1.15,
                label=label,
            )
            ax_sar.step(
                city_data["total_wbsar_cdf"][sampler]["x"],
                city_data["total_wbsar_cdf"][sampler]["cdf"],
                where="post",
                color=colors[city],
                linestyle=style,
                linewidth=1.15,
            )
            convergence = city_data["convergence"][sampler]
            ax_conv.plot(
                [point["look"] for point in convergence if point["p90_db"] is not None],
                [point["p90_db"] for point in convergence if point["p90_db"] is not None],
                color=colors[city],
                linestyle=style,
                marker="o",
                markersize=3.0,
                linewidth=1.1,
            )

        ratios = city_data["variance_ratios"]
        metric_keys = ("total_transfer", "mean_sab_w_m2", "absorbed_power_w", "sar_wb_w_kg")
        x = np.arange(len(metric_keys), dtype=np.float64)
        medians = [ratios[metric].get("q50") for metric in metric_keys]
        low = [ratios[metric].get("q10") for metric in metric_keys]
        high = [ratios[metric].get("q90") for metric in metric_keys]
        valid = [
            (xx, float(median), float(q10), float(q90))
            for xx, median, q10, q90 in zip(x, medians, low, high, strict=True)
            if median is not None and q10 is not None and q90 is not None and q10 > 0.0
        ]
        if valid:
            ax_var.errorbar(
                [item[0] for item in valid],
                [item[1] for item in valid],
                yerr=[
                    [item[1] - item[2] for item in valid],
                    [item[3] - item[1] for item in valid],
                ],
                color=colors[city],
                marker="o",
                markersize=3.5,
                linewidth=1.1,
                capsize=2.0,
                label=city_label,
            )

    ax_surplus.set_xlabel("multipath surplus over direct [dB]")
    ax_surplus.set_ylabel("route fraction")
    ax_surplus.set_ylim(0.0, 1.0)
    ax_surplus.text(0.02, 0.96, "(a)", transform=ax_surplus.transAxes, va="top")
    ax_surplus.legend(loc="lower right", frameon=True, framealpha=0.9)

    ax_sar.set_xlabel(r"total wbSAR / $(\rho_A P_{\mathrm{EIRP}})$ [m$^2$ kg$^{-1}$]")
    ax_sar.set_ylabel("route fraction")
    ax_sar.set_ylim(0.0, 1.0)
    ax_sar.xaxis.set_major_locator(MaxNLocator(4))
    ax_sar.xaxis.set_major_formatter(FormatStrFormatter("%.3g"))
    ax_sar.text(0.02, 0.96, "(b)", transform=ax_sar.transAxes, va="top")

    ax_conv.set_xlabel("replica count")
    ax_conv.set_ylabel("total-transfer p90 uncertainty [dB]")
    ax_conv.set_xticks(data["looks"])
    ax_conv.text(0.02, 0.96, "(c)", transform=ax_conv.transAxes, va="top")
    ax_conv.grid(axis="y", alpha=0.25)

    metrics = ["total_transfer", "mean_sab_w_m2", "absorbed_power_w", "sar_wb_w_kg"]
    ax_var.set_xticks(np.arange(len(metrics)))
    ax_var.set_xticklabels(["total\ntransfer", "mean\nSab", "absorbed", "wbSAR"])
    ax_var.set_ylabel("variance ratio, Fibonacci / IID")
    ax_var.set_yscale("log")
    ax_var.axhline(1.0, color="0.45", linewidth=0.75, linestyle=":")
    ax_var.text(0.02, 0.96, "(d)", transform=ax_var.transAxes, va="top")
    if ax_var.get_legend_handles_labels()[0]:
        ax_var.legend(loc="best", frameon=True, framealpha=0.9)
    for axis in axes.flat:
        axis.grid(axis="x", alpha=0.15)

    metadata = data["metadata"]
    save_metadata = {
        "Title": "Paired roofline campaign results",
        "Subject": metadata["caption"],
        "Keywords": "one-reflection; normalized rho_A P_EIRP; IID; rotated Fibonacci",
    }
    figure.savefig(pdf_path, metadata=save_metadata)
    figure.savefig(png_path, dpi=300, metadata=save_metadata)
    plt.close(figure)


def write_publication_results(
    campaigns: Sequence[CampaignPair],
    output: str | Path,
    *,
    looks: Sequence[int] = DEFAULT_LOOKS,
    final_look: int | None = None,
) -> FigureArtifacts:
    """Compare campaigns and write figure, plot data, CSV, and LaTeX outputs."""
    reports = collect_reports(campaigns, looks=looks)
    data = build_plot_data(reports, looks=looks, final_look=final_look)
    stem = Path(output)
    stem.parent.mkdir(parents=True, exist_ok=True)
    pdf_path = stem.with_suffix(".pdf")
    png_path = stem.with_suffix(".png")
    json_path = stem.with_suffix(".json")
    csv_path = stem.with_suffix(".csv")
    latex_path = stem.with_suffix(".tex")
    _draw(data, pdf_path, png_path)
    _write_json(data, json_path)
    _write_csv(data, csv_path)
    latex_path.write_text(_latex_fragment(data), encoding="utf-8")
    return FigureArtifacts(pdf_path, png_path, json_path, csv_path, latex_path)


__all__ = [
    "CampaignPair",
    "FigureArtifacts",
    "RESULT_SCHEMA_VERSION",
    "build_plot_data",
    "collect_reports",
    "write_publication_results",
]
