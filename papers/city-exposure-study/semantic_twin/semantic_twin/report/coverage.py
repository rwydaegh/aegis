"""Coverage ladder calculations and Markdown rendering."""

from __future__ import annotations

from typing import Any

import numpy as np


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
