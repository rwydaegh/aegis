"""The tables the paper prints, generated from a cross city table rather than typed.

Two of these numbers carry the study's headline claim, so they are worth naming
precisely. The **between site range** is the ratio of the largest per site median
to the smallest, in decibels. The **within site spread** is one square's own 95th
percentile over its 5th, in decibels. The claim is that the second is larger than
the first, which is to say that where a person stands in one square matters more
than which city the square is in.

``paper/paper.tex`` prints that comparison as ``tab:result-summary`` and its
numbers were transcribed by hand. :func:`latex_spread_table` reproduces that table
from the published summary file to the last digit, which is the point: a number in
the paper that came out of a function can be re-derived when the sweep is rerun,
and a number that was typed cannot.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence

import numpy as np

from .crosscity import CrossCityTable

#: Column name to the label the paper uses. The paper writes the exposure ratio as
#: chi and never uses the word susceptibility, and these labels follow it.
MODEL_LABELS: dict[str, str] = {
    "chi_isotropic": "Isotropic",
    "chi_rooftop": "Rooftop",
    "chi_street_small_cell": "Street cell",
}


def between_site_range_db(table: CrossCityTable, key: str) -> float:
    """Largest per site median over the smallest, in decibels.

    Raises rather than returning a sentinel when a site's median is not positive,
    because a zero median means every second standpoint of that square scored
    exactly zero and a range computed against it would be an infinity dressed as a
    number.
    """
    sites = table.sites_with(key)
    if len(sites) < 2:
        raise ValueError(f"{key} is on {len(sites)} site(s), so there is no between site range")
    medians = [table.median(site, key) for site in sites]
    low, high = min(medians), max(medians)
    if low <= 0.0:
        raise ValueError(f"{key} has a non positive median at one site, so the range is undefined")
    return 10.0 * math.log10(high / low)


@dataclass(frozen=True)
class SpreadRow:
    """One illumination model's line of the within against between comparison."""

    key: str
    label: str
    between_db: float
    within_min_db: float
    within_median_db: float
    within_max_db: float
    #: Squares whose own spread exceeds the spread across all the squares. This is
    #: the count that makes the claim concrete rather than a comparison of two
    #: summary numbers.
    above_between: int
    sites: int

    @property
    def margin_db(self) -> float:
        """How much the median square's own spread beats the between site range by."""
        return self.within_median_db - self.between_db


def spread_rows(table: CrossCityTable, keys: Sequence[str] = tuple(MODEL_LABELS)) -> tuple[SpreadRow, ...]:
    """One :class:`SpreadRow` per illumination model that the table actually carries.

    A model missing from the summary is skipped rather than raised on. The cross
    city summary files hold four columns and street small cell is not one of them,
    so asking for all three models against a summary file gives two rows, and that
    is the honest answer rather than an error about a column nobody wrote.
    """
    rows: list[SpreadRow] = []
    for key in keys:
        sites = table.sites_with(key)
        if len(sites) < 2:
            continue
        spreads = [table.spread_db(site, key) for site in sites]
        finite = np.array([value for value in spreads if value is not None], dtype=np.float64)
        if finite.size == 0:
            continue
        between = between_site_range_db(table, key)
        rows.append(
            SpreadRow(
                key=key,
                label=MODEL_LABELS.get(key, key),
                between_db=between,
                within_min_db=float(finite.min()),
                within_median_db=float(np.median(finite)),
                within_max_db=float(finite.max()),
                above_between=int((finite > between).sum()),
                sites=len(sites),
            )
        )
    return tuple(rows)


def latex_spread_table(table: CrossCityTable, keys: Sequence[str] = tuple(MODEL_LABELS)) -> str:
    """``tab:result-summary`` of ``paper/paper.tex``, generated.

    The body of the table only. Caption, label and float placement stay in the
    ``.tex`` file, because those are typesetting decisions and this is arithmetic.
    """
    rows = spread_rows(table, keys)
    if not rows:
        raise ValueError("no illumination model in this table has enough sites for a spread row")
    lines = [
        r"\begin{tabular}{lccc}",
        r"  \toprule",
        r"  Illumination & Between & Within min./med./max. & Above \\",
        r"   & (dB) & (dB) & between \\",
        r"  \midrule",
    ]
    for row in rows:
        lines.append(
            f"  {row.label} & {row.between_db:.2f} & "
            f"{row.within_min_db:.2f} / {row.within_median_db:.2f} / {row.within_max_db:.2f} & "
            f"{row.above_between} of {row.sites} \\\\"
        )
    lines.extend([r"  \bottomrule", r"\end{tabular}"])
    return "\n".join(lines)


def markdown_site_table(
    table: CrossCityTable,
    key: str = "chi_rooftop",
    *,
    pretty: dict[str, str] | None = None,
) -> str:
    """Per site medians and spreads, sorted by median, for a note rather than the paper.

    Sorted rather than left in registry order, because the ordering of the squares
    is itself a result and reading it off an alphabetical list is how a reordering
    goes unnoticed. ``AGGREGATE_REBUILD.md`` had to measure a rank correlation
    against the published order to find that Toulouse had moved five places.
    """
    sites = sorted(table.sites_with(key), key=lambda site: table.median(site, key))
    if not sites:
        raise ValueError(f"no site in this table carries {key}")
    names = pretty or {}
    lines = [
        f"| site | standpoints | median {key} | spread p95/p05 dB |",
        "| --- | --- | --- | --- |",
    ]
    for site in sites:
        spread = table.spread_db(site, key)
        cell = "undefined" if spread is None else f"{spread:.2f}"
        lines.append(
            f"| {names.get(site, site)} | {table.coverage.locations.get(site, 0)} | "
            f"{table.median(site, key):.4f} | {cell} |"
        )
    return "\n".join(lines)
