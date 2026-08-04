"""Single-run exposure aggregation and CDF output."""

from __future__ import annotations

import json
import pathlib


def report(stem: str, output: pathlib.Path) -> pathlib.Path:
    """Regenerate the CDF figure and the numbers behind it from the JSONL."""
    from semantic_twin.report import read_rows, split_half_stability, summarise
    from semantic_twin.viz.cdf import walk_cdf

    rows_path = output / f"{stem}_locations.jsonl"
    manifest = json.loads((output / f"{stem}_manifest.json").read_text())
    # ``read_rows`` returns the file plus what it cost to read. Only the rows go
    # on from here, because the summary this writes is pinned by a golden fixture
    # and has no field for a torn line count.
    rows = list(read_rows(rows_path, site=stem).rows)
    keys = [
        "chi_isotropic",
        "chi_rooftop",
        "chi_street_small_cell",
        "chi_isotropic_direct",
        "chi_rooftop_direct",
        "chi_street_small_cell_direct",
        "multipath_gain_isotropic",
        "multipath_gain_rooftop",
        "sky_fraction",
        "mean_bounces",
        "mean_excess_delay_ns",
        "truncated_throughput_share",
        "rooftop_peak_sab_w_m2",
        "rooftop_mean_sab_w_m2",
        "rooftop_absorbed_power_w",
        "rooftop_sar_wb_w_kg",
        "isotropic_peak_sab_w_m2",
        "street_small_cell_peak_sab_w_m2",
    ]
    summary = summarise(rows, keys)
    stability_keys = ["chi_rooftop", "chi_isotropic", "sky_fraction", "rooftop_peak_sab_w_m2"]
    summary["split_half_stability"] = {
        split: split_half_stability(rows, stability_keys, split=split) for split in ("interleaved", "contiguous")
    }
    summary["reference_s0_w_m2"] = manifest["reference_s0_w_m2"]
    summary["frequency_hz"] = manifest["trace_config"]["frequency_hz"]
    summary["rays_per_location"] = manifest["trace_config"]["rays"]
    summary_path = output / f"{stem}_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2))
    figure = walk_cdf(
        rows,
        output / f"{stem}_cdf.png",
        reference_s0_w_m2=manifest["reference_s0_w_m2"],
        frequency_ghz=manifest["trace_config"]["frequency_hz"] / 1e9,
    )
    print(f"wrote {summary_path} and {figure}")
    return summary_path
