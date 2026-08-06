"""Summaries of skyline registration quality across panorama sites.

Every panorama fetched by ``fetch_site_panoramas.py`` is registered on its own,
so the useful quantity is the distribution over a site rather than any single
residual. This module reads the aligned poses and writes one JSON summary plus a
Markdown table per site.

The two numbers to read first are the median skyline residual, which says how
well the modelled silhouette matches the segmented one, and the count of poses
whose recovered altitude landed on its search bound. A pose at its bound is the
bound rather than a measurement. Every pose shipped before this check was added
had that defect.
"""

from __future__ import annotations

import json
import pathlib
import statistics
from typing import Any


def read_pose(path: pathlib.Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text())


def panorama_rows(site_dir: pathlib.Path) -> list[dict[str, Any]]:
    """Return one row per panorama directory, including unregistered panoramas."""
    rows: list[dict[str, Any]] = []
    for pano_dir in sorted(site_dir.glob("pano_*")):
        aligned = read_pose(pano_dir / "alignment" / "pose_aligned.json")
        initial = read_pose(pano_dir / "pose_initial.json")
        metadata = read_pose(pano_dir / "metadata.json")
        if aligned is None or initial is None:
            rows.append({"name": pano_dir.name, "registered": False})
            continue
        provenance = aligned.get("provenance", {})
        rows.append(
            {
                "name": pano_dir.name,
                "registered": True,
                "pano_id": None if metadata is None else metadata.get("panoId"),
                "date": None if metadata is None else metadata.get("date"),
                "position_enu_m": aligned.get("position_enu_m"),
                "initial_enu_m": initial.get("position_enu_m"),
                "residual_deg": aligned.get("skyline_score_mean_deg"),
                "signed_residual_deg": aligned.get("skyline_signed_residual_median_deg"),
                "dz_at_bound": aligned.get("skyline_dz_at_bound"),
                "skyline_samples": aligned.get("n_observed_structural_skyline_samples"),
                "orientation_source": aligned.get("orientation_source"),
                "ground_minus_scene_constant_m": provenance.get("ground_minus_scene_constant_m"),
                "ground_spread_m": provenance.get("ground_spread_m"),
            }
        )
    return rows


def summarise(site_dir: pathlib.Path) -> dict[str, Any]:
    rows = panorama_rows(site_dir)
    done = [row for row in rows if row["registered"]]
    residuals = [row["residual_deg"] for row in done if row["residual_deg"] is not None]
    offsets = [
        row["ground_minus_scene_constant_m"] for row in done if row.get("ground_minus_scene_constant_m") is not None
    ]
    moved = []
    for row in done:
        if row["position_enu_m"] and row["initial_enu_m"]:
            moved.append(
                sum(
                    (aligned - initial) ** 2
                    for aligned, initial in zip(row["position_enu_m"], row["initial_enu_m"], strict=True)
                )
                ** 0.5
            )
    return {
        "site": site_dir.name,
        "panoramas": len(rows),
        "registered": len(done),
        "dates": sorted({row["date"] for row in done if row.get("date")}),
        "residual_deg": {
            "median": round(statistics.median(residuals), 3) if residuals else None,
            "min": round(min(residuals), 3) if residuals else None,
            "max": round(max(residuals), 3) if residuals else None,
        },
        "poses_at_altitude_bound": sum(1 for row in done if row.get("dz_at_bound")),
        "poses_without_measured_orientation": sum(
            1 for row in done if row.get("orientation_source", "").startswith(("absent", "degenerate"))
        ),
        "ground_minus_scene_constant_m": {
            "min": round(min(offsets), 3) if offsets else None,
            "max": round(max(offsets), 3) if offsets else None,
        },
        "pose_correction_m": {
            "median": round(statistics.median(moved), 3) if moved else None,
            "max": round(max(moved), 3) if moved else None,
        },
        "panoramas_detail": rows,
    }


def markdown(summaries: list[dict[str, Any]]) -> str:
    header = (
        "| Site | Panoramas | Registered | Capture | Median residual | Best | Worst | At altitude bound |\n"
        "| --- | --- | --- | --- | --- | --- | --- | --- |\n"
    )
    lines = []
    for summary in summaries:
        residual = summary["residual_deg"]

        def format_degrees(value: float | None) -> str:
            return "n/a" if value is None else f"{value:.2f} deg"

        lines.append(
            f"| {summary['site']} | {summary['panoramas']} | {summary['registered']} | "
            f"{', '.join(summary['dates']) or 'n/a'} | {format_degrees(residual['median'])} | "
            f"{format_degrees(residual['min'])} | {format_degrees(residual['max'])} | "
            f"{summary['poses_at_altitude_bound']} |"
        )
    return header + "\n".join(lines) + "\n"


def write_summary(site_dirs: list[pathlib.Path], output_dir: pathlib.Path) -> str:
    """Write the JSON and Markdown registration reports and return the table."""
    summaries = [summarise(site) for site in site_dirs]
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "panorama_registration.json").write_text(
        json.dumps(summaries, indent=2) + "\n",
        encoding="utf-8",
    )
    rendered = markdown(summaries)
    (output_dir / "panorama_registration.md").write_text(rendered, encoding="utf-8")
    return rendered
