"""Coverage ladder calculations and Markdown rendering."""

from __future__ import annotations

import json
import pathlib
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np

from semantic_twin.viz.coverage import plot_coverage_ladder, plot_cross_site_ladder

__all__ = [
    "CoverageReportConfig",
    "CoverageReportEnvironment",
    "LadderReportConfig",
    "LadderReportEnvironment",
    "coverage_ladder_report",
    "coverage_report",
    "ladder_markdown",
    "plot_cross_site_ladder",
]


@dataclass(frozen=True)
class CoverageReportConfig:
    frequency_hz: float
    tag_suffix: str = ""
    site: str = "korenmarkt"
    crop_m: int = 130
    seed: int = 7


@dataclass(frozen=True)
class CoverageReportEnvironment:
    output: pathlib.Path
    rungs_for: Callable[[str, int, int], Sequence[tuple[str, str, str]]]
    key_for: Callable[[str, int, int], str]
    model_keys: Sequence[str]
    compare_to_baseline: Callable[[np.ndarray, np.ndarray], dict[str, float | int]]


@dataclass(frozen=True)
class LadderReportConfig:
    sites: list[str]
    crop_m: int
    seeds: tuple[int, ...]
    frequency_hz: float
    tag_suffix: str = ""
    refused: dict[str, str] | None = None
    failures: dict[str, str] | None = None


@dataclass(frozen=True)
class LadderReportEnvironment:
    output: pathlib.Path
    key_for: Callable[[str, int, int], str]
    model_keys: Sequence[str]
    one_value: Callable[[list[float]], float | list[float]]
    spread: Callable[[list[float]], dict[str, Any]]
    plotter: Callable[[list[dict[str, Any]], pathlib.Path, int, float], pathlib.Path | None]
    markdown: Callable[[list[dict[str, Any]]], str]


def _against_baseline(baseline: np.ndarray, values: np.ndarray) -> dict[str, float | int]:
    """How far one rung sits from the no evidence rung, paired standpoint by standpoint.

    Both rungs trace the same walk on the same per standpoint seeds, so the ray
    stream is common to the two and the difference carries no independent Monte
    Carlo noise from it. What the difference does carry is the standpoint draw,
    which is why the shift is replicated over seeds rather than quoted from one.
    """
    count = min(baseline.size, values.size)
    ratio = values[:count] / baseline[:count]
    return {
        # Median of the paired per location ratios: how far a typical location
        # moves.
        "median_ratio": float(np.median(ratio)),
        "median_shift_db": float(10.0 * np.log10(np.median(ratio))),
        # Ratio of the two distribution medians: how far the published
        # distribution moves. Larger than the paired figure at Korenmarkt, which
        # says the shift is concentrated in a minority of locations rather than
        # spread evenly.
        "distribution_median_shift_db": float(10.0 * np.log10(np.quantile(values, 0.5) / np.quantile(baseline, 0.5))),
        "spread_db_p95_over_p05": float(10.0 * np.log10(np.quantile(values, 0.95) / np.quantile(values, 0.05))),
        "p95_ratio": float(np.quantile(ratio, 0.95)),
        "max_absolute_change": float(np.max(np.abs(ratio - 1.0))),
        "locations_moved_more_than_1_db": int(np.count_nonzero(np.abs(10.0 * np.log10(ratio)) > 1.0)),
    }


def _one_value(values: list[float]) -> float | list[float]:
    """A bound fraction does not depend on the seed, so a spread in it is a fault."""
    unique = sorted(set(values))
    return unique[0] if len(unique) == 1 else unique


def _spread(values: list[float]) -> dict[str, Any]:
    array = np.array(values, dtype=float)
    if array.size == 0:
        return {"replicates": 0, "mean_db": None, "sd_db": None, "standard_error_db": None, "per_seed_db": []}
    sd = float(array.std(ddof=1)) if array.size > 1 else None
    return {
        "replicates": int(array.size),
        "mean_db": float(array.mean()),
        "sd_db": sd,
        "standard_error_db": None if sd is None else sd / float(np.sqrt(array.size)),
        "per_seed_db": [float(x) for x in array],
    }


def ladder_markdown(rows: list[dict[str, Any]]) -> str:
    """The per square table, bound fraction first and never on its own."""
    header = (
        "| Site | Rung | Bound area | Stations or views | Standpoints | "
        "Rooftop shift | Isotropic shift | Street shift |"
    )
    lines = [header, "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    for row in rows:
        bound = row["covered_fraction_by_area"]
        bound_cell = f"{100 * bound:.1f} %" if isinstance(bound, float) else "inconsistent across seeds"
        evidence = row["stations"] if row["stations"] is not None else row["views"]
        kind = "stations" if row["stations"] is not None else "views"
        cells = [
            row["site"],
            row["rung"],
            bound_cell,
            "not recorded" if evidence is None else f"{evidence} {kind}",
            f"{sum(row['locations'])} over {len(row['seeds'])} seeds",
        ]
        for key in ("chi_rooftop", "chi_isotropic", "chi_street_small_cell"):
            spread = row["shift_db"][key]
            if spread["mean_db"] is None:
                cells.append("n/a")
            elif spread["standard_error_db"] is None:
                cells.append(f"{spread['mean_db']:+.3f} dB, one seed")
            else:
                cells.append(f"{spread['mean_db']:+.3f} +/- {spread['standard_error_db']:.3f} dB")
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def coverage_report(config: CoverageReportConfig, environment: CoverageReportEnvironment) -> pathlib.Path:
    """How far does the exposure distribution move as image evidence grows?

    This is the experiment that says whether the material assignment matters at
    all. Everything except the material binding is held fixed, so the only
    thing varying between the three runs is the fraction of scene area whose
    material came from an image rather than from which way the triangle points.

    ``tag_suffix`` reads a rerun of the same rungs written under suffixed
    tags, so a rerun at a different bounce budget does not overwrite the
    published ladder and can be compared against it.
    """
    from semantic_twin.report import read_rows

    entries: list[dict[str, Any]] = []
    baseline: dict[str, np.ndarray] | None = None
    for stem, _materials, description in environment.rungs_for(config.site, config.crop_m, config.seed):
        full = f"{stem}{config.tag_suffix}_{config.frequency_hz / 1e9:g}ghz"
        rows_path = environment.output / f"{full}_locations.jsonl"
        manifest_path = environment.output / f"{full}_manifest.json"
        if not rows_path.exists() or not manifest_path.exists():
            continue
        rows = read_rows(rows_path, site=config.site).rows
        manifest = json.loads(manifest_path.read_text())
        binding = manifest["semantic_binding"]
        columns = {key: np.array([row[key] for row in rows]) for key in environment.model_keys}
        values = columns["chi_rooftop"]
        entry: dict[str, Any] = {
            "run": stem,
            # The suffixed stem, because the figure below reloads these rows and
            # rebuilding the name from ``run`` would silently read the published
            # ladder while the table above described the rerun.
            "stem": full,
            "site": config.site,
            "crop_radius_m": config.crop_m,
            "seed": config.seed,
            "evidence": description,
            # A bound run is a run in which this fraction of the triangle area
            # carries image evidence and the rest still falls back to the
            # orientation rule. It travels beside every shift below because a
            # shift without it is not interpretable.
            "covered_fraction_by_area": binding.get("covered_fraction_by_area", 0.0),
            "covered_fraction_by_face": binding.get("covered_fraction_by_face", 0.0),
            "stations": binding.get("stations"),
            "views": len(binding["views"]) if isinstance(binding.get("views"), list) else None,
            # Every fishnet in this study was cut against a smaller mesh than the
            # 250 m run uses, so the join from the cut mesh's triangle numbering
            # to the run's is done by centroid and normal and can drop triangles.
            # How many it kept is part of the result, not an implementation
            # detail, so it is carried rather than left inside the manifest.
            "mesh_match": binding.get("mesh_match"),
            "binding_source": binding.get("walk_npz") or binding.get("fishnet_dir"),
            "locations": len(rows),
            "chi_rooftop": {
                "p05": float(np.quantile(values, 0.05)),
                "p50": float(np.quantile(values, 0.50)),
                "p95": float(np.quantile(values, 0.95)),
                "mean": float(values.mean()),
            },
        }
        if baseline is None:
            baseline = columns
        else:
            entry["against_no_evidence"] = environment.compare_to_baseline(baseline["chi_rooftop"], values)
            entry["by_model"] = {
                key: environment.compare_to_baseline(baseline[key], columns[key])
                for key in environment.model_keys
                if key in baseline
            }
        entries.append(entry)

    summary = {
        "question": (
            "how far does the exposure distribution move as the fraction of scene area carrying image evidence grows"
        ),
        "site": config.site,
        "crop_radius_m": config.crop_m,
        "seed": config.seed,
        "frequency_hz": config.frequency_hz,
        "ladder": entries,
    }
    key = environment.key_for(config.site, config.crop_m, config.seed)
    path = environment.output / f"coverage_ladder{key}{config.tag_suffix}_{config.frequency_hz / 1e9:g}ghz.json"
    path.write_text(json.dumps(summary, indent=2))

    if len(entries) >= 2:
        figure_path = environment.output / (
            f"coverage_ladder{key}{config.tag_suffix}_{config.frequency_hz / 1e9:g}ghz.png"
        )
        plot_coverage_ladder(
            entries,
            figure_path,
            site=config.site,
            crop_m=config.crop_m,
            frequency_hz=config.frequency_hz,
        )
    print(f"wrote {path}")
    return path


def coverage_ladder_report(
    config: LadderReportConfig,
    environment: LadderReportEnvironment,
) -> pathlib.Path | None:
    """Does the single square material negative travel? One row per square.

    The shift is a mean over the seeds and its error bar is their standard
    error. The bound area fraction sits beside it in the same row and is not
    optional: a 4.6 percent bound run is a run in which 95.4 percent of the area
    still came from the orientation rule, and quoting the shift without it
    invites the reader to read it as the effect of knowing the materials.

    The bound fraction is a property of where a camera could stand rather than
    of how good the segmentation is, so the rows are ordered by site name and
    not by it.
    """
    rows = _ladder_rows(config, environment)
    if not rows:
        print("no ladder to report", flush=True)
        return None
    summary = {
        "question": "does the single square material negative travel to the other squares",
        "crop_radius_m": config.crop_m,
        "frequency_hz": config.frequency_hz,
        "seeds": list(config.seeds),
        "shift_definition": (
            "ratio of the two distribution medians in dB, the walk or fishnet rung against the "
            "geometric rung on the same standpoints, averaged over the seeds"
        ),
        "standard_error": "standard deviation over the seeds divided by the square root of their count",
        "bound_fraction_note": (
            "covered_fraction_by_area is the fraction of the crop's triangle area carrying image "
            "evidence. The rest falls back to the orientation rule. It is set by where a camera "
            "could stand against how far the crop reaches, not by segmentation quality, so it does "
            "not rank the squares by evidence quality."
        ),
        "rows": rows,
        "sites_refused": config.refused or {},
        "rungs_failed": config.failures or {},
    }
    path = environment.output / (
        f"coverage_ladder_cross_site_{config.crop_m}m{config.tag_suffix}_{config.frequency_hz / 1e9:g}ghz.json"
    )
    path.write_text(json.dumps(summary, indent=2))
    environment.plotter(rows, path.with_suffix(".png"), config.crop_m, config.frequency_hz)
    print(environment.markdown(rows), flush=True)
    print(f"wrote {path}", flush=True)
    return path


def _ladder_rows(config: LadderReportConfig, environment: LadderReportEnvironment) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for site in config.sites:
        per_rung = _site_rungs(site, config, environment)
        for rung in per_rung.values():
            rung["covered_fraction_by_area"] = environment.one_value(rung["covered_fraction_by_area"])
            rung["shift_db"] = {key: environment.spread(values) for key, values in rung["shift_db"].items()}
            rung["paired_median_shift_db"] = {
                key: environment.spread(values) for key, values in rung["paired_median_shift_db"].items()
            }
            rows.append({"site": site, **rung})
    return rows


def _site_rungs(
    site: str,
    config: LadderReportConfig,
    environment: LadderReportEnvironment,
) -> dict[str, dict[str, Any]]:
    per_rung: dict[str, dict[str, Any]] = {}
    for seed in config.seeds:
        path = environment.output / (
            f"coverage_ladder{environment.key_for(site, config.crop_m, seed)}{config.tag_suffix}_"
            f"{config.frequency_hz / 1e9:g}ghz.json"
        )
        if not path.exists():
            continue
        for entry in json.loads(path.read_text())["ladder"]:
            _add_ladder_entry(per_rung, entry, seed, environment.model_keys)
    return per_rung


def _add_ladder_entry(
    per_rung: dict[str, dict[str, Any]],
    entry: dict[str, Any],
    seed: int,
    model_keys: Sequence[str],
) -> None:
    if "against_no_evidence" not in entry:
        return
    rung = entry["run"].rsplit("_", 1)[-1]
    record = per_rung.setdefault(rung, _empty_rung(rung, entry, model_keys))
    record["covered_fraction_by_area"].append(entry["covered_fraction_by_area"])
    record["locations"].append(entry["locations"])
    record["seeds"].append(seed)
    record["locations_moved_more_than_1_db"].append(entry["against_no_evidence"]["locations_moved_more_than_1_db"])
    for key in model_keys:
        against = entry.get("by_model", {}).get(key)
        if against is not None:
            record["shift_db"][key].append(against["distribution_median_shift_db"])
            record["paired_median_shift_db"][key].append(against["median_shift_db"])


def _empty_rung(rung: str, entry: dict[str, Any], model_keys: Sequence[str]) -> dict[str, Any]:
    return {
        "rung": rung,
        "evidence": entry["evidence"],
        "covered_fraction_by_area": [],
        "stations": entry["stations"],
        "views": entry["views"],
        "locations": [],
        "seeds": [],
        "shift_db": {key: [] for key in model_keys},
        "paired_median_shift_db": {key: [] for key in model_keys},
        "locations_moved_more_than_1_db": [],
    }
