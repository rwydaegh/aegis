"""Reading the streamed per standpoint rows back off disk, with the damage counted.

A run appends one JSON object per standpoint to a ``*_locations.jsonl`` file. That
is a good format for a sweep that may die, and it has one failure mode that has
already cost this study a published figure: two writers on one tag interleave
their appends and tear a record in half. The tail of a torn record is a line that
does not parse, and the head of it is a standpoint that no longer exists.

The old reader called :func:`json.loads` on every line and let the exception out,
so a torn file killed a sweep at the reduction step. The figure generator grew its
own tolerant loader that counted the torn lines, and the two readers then
disagreed about what the same file contained. There is one reader here, it is
tolerant, and it counts. A count of zero is the normal answer and it is worth
carrying anyway, because :class:`~.crosscity.Coverage` refuses to publish a table
whose rows came from a file with torn lines.
"""

from __future__ import annotations

import json
import pathlib
from dataclasses import dataclass
from typing import Any

#: One standpoint. Forty odd scalars, written by the driver, read by everything
#: downstream. Left as a plain mapping on purpose: the column set differs between
#: estimators and between code versions, and a dataclass here would either have to
#: track every one of them or drop the ones it did not know about.
Row = dict[str, Any]

#: Below this sky fraction a standpoint is inside geometry rather than in the open.
#: See :func:`drop_enclosed`.
MIN_SKY_FRACTION = 1.0e-4


@dataclass(frozen=True)
class RowSet:
    """The rows of one file, and what the file cost to read.

    ``torn`` is the number of lines that did not parse. It is not a curiosity and
    it is not zero on every file in ``outputs/``: New York lost two whole
    standpoints to interleaved writes and Prague kept a 46 character fragment, and
    both files looked the right length.
    """

    site: str
    path: pathlib.Path
    rows: tuple[Row, ...]
    torn: int = 0

    def __len__(self) -> int:
        return len(self.rows)

    def column(self, key: str) -> list[float]:
        """One column, over the rows that carry it.

        Rows written by two code versions into one file differ by which keys they
        have, which is a mixture that has actually happened at Brussels, Madrid and
        Prague. A missing key is therefore skipped rather than raised on, and the
        length of what comes back is the honest count of what was there.
        """
        return [float(row[key]) for row in self.rows if key in row]


def read_rows(path: str | pathlib.Path, *, site: str = "") -> RowSet:
    """Every parseable line of one location file, with the rest counted.

    ``site`` defaults to empty rather than being guessed from the file name. The
    stem carries a tag, a site and a frequency in one string and parsing it here
    would put a fourth copy of that convention in the tree.
    """
    path = pathlib.Path(path)
    rows: list[Row] = []
    torn = 0
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            torn += 1
    return RowSet(site=site, path=path, rows=tuple(rows), torn=torn)


def drop_enclosed(rows: tuple[Row, ...] | list[Row], *, min_sky_fraction: float = MIN_SKY_FRACTION) -> tuple[Row, ...]:
    """Remove standpoints from which no ray escapes at all.

    A point with a sky fraction of exactly zero is inside geometry. It traces to a
    susceptibility orders of magnitude below its neighbours, which is not an
    exposure result but a walkability filter that let a bad standpoint through.
    :func:`semantic_twin.walk.build_walk` rejects these at construction
    now, so this is a guard for runs made before that fix and it should normally
    remove nothing.

    Applied to the figure and not to the table, which is how it has always been and
    is worth stating out loud because it means the two can in principle disagree.
    On every published sweep the count removed is zero, so they do not.
    """
    return tuple(row for row in rows if row.get("sky_fraction", 1.0) >= min_sky_fraction)
