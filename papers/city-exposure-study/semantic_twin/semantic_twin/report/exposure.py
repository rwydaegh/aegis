"""Single-run exposure aggregation and CDF output."""

from __future__ import annotations

import json
import pathlib
from collections.abc import Sequence


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


def cross_city_report(
    sites: list[str],
    frequency_hz: float,
    *,
    crop_m: int = 130,
    tag_suffix: str = "",
    sites_expected: Sequence[str] | None = None,
    output: pathlib.Path,
    reference_s0_w_m2: float,
    crop_bound_note: str,
) -> None:
    """CDF with one curve per city, plus the numbers behind it.

    The suffix has to be threaded here as well as into the per site tags. It
    was not, and the result was quiet rather than loud: a suffixed run traced
    every site, then read the unsuffixed per site files and rewrote the
    unsuffixed aggregate from them, so the new runs were simply not in the
    figure and nothing said so.

    ``sites_expected`` names the squares the sweep meant to reach. It used to be
    a count, and a count is what let a ten of eleven aggregate call itself
    complete. Names go into :class:`~semantic_twin.report.Coverage`, which will
    not hand the figure a table it cannot vouch for.
    """
    if not sites:
        return
    from semantic_twin.report import CrossCityTable, IncompleteAggregate, read_rows
    from semantic_twin.viz.cdf import cross_city_cdf

    prefix = "city" if crop_m == 130 else f"city{crop_m}"
    stems = {site: f"{prefix}{tag_suffix}_{site}_{frequency_hz / 1e9:g}ghz" for site in sites}
    rows = {}
    for site, stem in stems.items():
        path = output / f"{stem}_locations.jsonl"
        if path.exists():
            rows[site] = read_rows(path, site=site)
    if not rows:
        return
    table = CrossCityTable.build(
        rows,
        expected=sites if sites_expected is None else sites_expected,
        frequency_hz=frequency_hz,
        reference_s0_w_m2=reference_s0_w_m2,
        crop_radius_m=float(crop_m),
        materials="geometric class prior, identical across sites",
        crop_bound_note=crop_bound_note,
    )
    path = output / f"cities{crop_m}{tag_suffix}_{frequency_hz / 1e9:g}ghz_summary.json"
    path.write_text(json.dumps(table.as_dict(), indent=2))
    try:
        published = table.publish()
    except IncompleteAggregate as refusal:
        # The table is still written, because a sweep that dies at hour two should
        # leave a readable aggregate behind. The figure is not, because the figure
        # is the thing that got copied into the paper.
        print(f"[partial] {refusal}", flush=True)
        print(f"wrote {path}, no figure", flush=True)
        return
    figure = cross_city_cdf(
        published,
        output / f"cities{crop_m}{tag_suffix}_{frequency_hz / 1e9:g}ghz_cdf.png",
        frequency_ghz=frequency_hz / 1e9,
        reference_s0_w_m2=reference_s0_w_m2,
        crop_radius_m=float(crop_m),
    )
    print(f"wrote {path} and {figure}", flush=True)
