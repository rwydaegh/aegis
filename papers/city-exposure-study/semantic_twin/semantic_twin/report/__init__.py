"""Aggregation. Per standpoint rows in, per site statistics and cross city tables out.

This is the arithmetic between a trace and a published number, and it is the part
of the study that has already been wrong in a way nobody noticed. The eleven city
figure was once drawn from a sweep that held one square at 3 standpoints and ten
at 80, and the reason it survived review is that the reduction reported a shape
rather than a coverage. ``docs/2026-08-03_160550_AGGREGATE_REBUILD.md`` is the
audit.

So the shape of this package follows from that failure. Rows are read with the
lines that did not parse counted rather than skipped, a cross city table carries
its own :class:`~.crosscity.Coverage` as a required field, and the only way to
get an object a figure will accept is :meth:`~.crosscity.CrossCityTable.publish`,
which refuses an incomplete or ragged set. A partial aggregate is still buildable,
because a sweep that dies at hour two should leave something readable behind, but
it can no longer be mistaken for a finished one by looking at it.

Nothing here draws. Everything that draws is in :mod:`semantic_twin.viz`.
"""

from __future__ import annotations

from .crosscity import (
    Coverage,
    CrossCityTable,
    IncompleteAggregate,
    PublishedAggregate,
)
from .rows import RowSet, drop_enclosed, read_rows
from .stats import (
    QUANTILES,
    describe,
    empirical_cdf,
    quantile,
    spread_db,
    split_half_stability,
    summarise,
)
from .tables import (
    SpreadRow,
    between_site_range_db,
    latex_spread_table,
    markdown_site_table,
    spread_rows,
)

__all__ = [
    "QUANTILES",
    "Coverage",
    "CrossCityTable",
    "IncompleteAggregate",
    "PublishedAggregate",
    "RowSet",
    "SpreadRow",
    "between_site_range_db",
    "describe",
    "drop_enclosed",
    "empirical_cdf",
    "latex_spread_table",
    "markdown_site_table",
    "quantile",
    "read_rows",
    "spread_db",
    "spread_rows",
    "split_half_stability",
    "summarise",
]
