"""Quantiles, spreads and empirical distributions, over one column at a time.

Every published number in this study is a quantile of a column or a ratio of two
of them, so this is a short module that decides a lot. Two conventions are fixed
here and both are load bearing.

The plotting position is ``(i + 0.5) / n``. It puts the smallest of n samples at
``0.5/n`` rather than at 0 and the largest at ``1 - 0.5/n`` rather than at 1, which
is the honest statement that a sample of 80 has not measured the 100th percentile.

The quantile rule is NumPy's default linear interpolation between order
statistics, and it is stated rather than assumed because the alternatives disagree
by a visible amount on the sample sizes this study uses. At n = 80 the 5th
percentile sits between the fourth and fifth smallest values, and the three common
rules put it in three different places.

Spread is reported in decibels as ``10 log10(p95 / p05)``, which is a ratio of
power densities and not of amplitudes. The whole study is in power, so the factor
is ten.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

import numpy as np

#: The quantiles every column reports. The set has to include 0.05 and 0.95
#: because the study's within site spread is the ratio of those two, and 0.5
#: because the between site range is the ratio of the extremes of that.
QUANTILES: tuple[float, ...] = (0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95, 0.99)


def _finite(values: Sequence[float] | np.ndarray) -> np.ndarray:
    array = np.asarray(values, dtype=np.float64).ravel()
    return array[np.isfinite(array)]


def empirical_cdf(values: Sequence[float] | np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Sorted values and their plotting positions ``(i + 0.5) / n``."""
    ordered = np.sort(np.asarray(values, dtype=np.float64))
    return ordered, (np.arange(ordered.size) + 0.5) / ordered.size


def quantile(values: Sequence[float] | np.ndarray, q: float) -> float:
    """One quantile, by linear interpolation between order statistics.

    Wrapped rather than called inline so that the rule is named in one place. A
    study that quotes a 5th percentile of 80 samples is quoting an interpolation
    between the fourth and fifth smallest, and which interpolation is a choice.
    """
    return float(np.quantile(np.asarray(values, dtype=np.float64), q))


def spread_db(values: Sequence[float] | np.ndarray, *, low: float = 0.05, high: float = 0.95) -> float | None:
    """``10 log10(q_high / q_low)``, or None when the lower quantile is not positive.

    None rather than negative infinity, because the caller writes this into JSON
    and an infinity there is a value that most readers silently turn into a string.
    A non positive lower quantile means the column has a standpoint at zero, which
    happens under the street small cell model when a standpoint's entire elevation
    support is occluded.
    """
    array = np.asarray(values, dtype=np.float64)
    lower = float(np.quantile(array, low))
    if lower <= 0.0:
        return None
    return float(10.0 * np.log10(float(np.quantile(array, high)) / lower))


def describe(values: Sequence[float] | np.ndarray) -> dict[str, Any] | None:
    """One column reduced to the record the summary files carry.

    Returns None for a column with no finite values, so the caller can leave the
    key out entirely rather than write a record full of NaN. A key that is absent
    says the run did not produce that column. A key present and full of NaN says
    something worse and less clearly.

    The standard deviation is the sample one, ``ddof=1``, and is defined as zero
    for a single value rather than as NaN. That is a display convention and not a
    statistic, and nothing in the study reads it.
    """
    finite = _finite(values)
    if finite.size == 0:
        return None
    return {
        "n": int(finite.size),
        "min": float(finite.min()),
        "max": float(finite.max()),
        "mean": float(finite.mean()),
        "std": float(finite.std(ddof=1)) if finite.size > 1 else 0.0,
        "quantiles": {str(q): quantile(finite, q) for q in QUANTILES},
        "spread_db_p95_over_p05": spread_db(finite),
    }


def summarise(rows: Sequence[Mapping[str, Any]], keys: Sequence[str]) -> dict[str, Any]:
    """Per column statistics over one site's standpoints.

    ``locations`` is the number of rows, which is not the same as any column's
    ``n``. A row written by an older code version can be missing a column, so a
    site can hold 80 standpoints and 78 values of one of them, and the difference
    between those two numbers is the only signal that a file is a mixture.
    """
    out: dict[str, Any] = {"locations": len(rows)}
    for key in keys:
        record = describe([row[key] for row in rows if key in row])
        if record is not None:
            out[key] = record
    return out


def split_half_stability(
    rows: Sequence[Mapping[str, Any]],
    keys: Sequence[str],
    *,
    split: str = "interleaved",
) -> dict[str, Any]:
    """Are there enough locations for the CDF to have settled?

    Split the walk in half and compare the two empirical distributions. This
    answers the "how many locations is enough" question by measurement rather than
    by picking a number, and the Kolmogorov statistic between the halves is the
    single number to quote.

    The two splits answer different questions and neither alone is the honest one.
    ``interleaved`` takes the even and odd indexed locations, which are about a
    walk spacing apart and therefore highly correlated, so it measures whether the
    route is sampled densely enough and it understates the true sampling error.
    ``contiguous`` takes the first and second halves of the route, which are
    different parts of the square, so its disagreement mixes sampling error with
    genuine spatial heterogeneity and it overstates. The true uncertainty sits
    between them, and both are reported.
    """
    out: dict[str, Any] = {"locations": len(rows), "split": split}
    if len(rows) < 8:
        out["note"] = "too few locations to split"
        return out
    if split == "interleaved":
        first, second = list(rows[0::2]), list(rows[1::2])
    elif split == "contiguous":
        half = len(rows) // 2
        first, second = list(rows[:half]), list(rows[half:])
    else:
        raise ValueError(f"unknown split {split!r}")
    for key in keys:
        a = _finite([row[key] for row in first if key in row])
        b = _finite([row[key] for row in second if key in row])
        if a.size < 4 or b.size < 4:
            continue
        grid = np.unique(np.concatenate([a, b]))
        cdf_a = np.searchsorted(np.sort(a), grid, side="right") / a.size
        cdf_b = np.searchsorted(np.sort(b), grid, side="right") / b.size
        quantiles = (0.1, 0.5, 0.9)
        ratios = [quantile(a, q) / quantile(b, q) if quantile(b, q) > 0 else None for q in quantiles]
        out[key] = {
            "kolmogorov_distance": float(np.max(np.abs(cdf_a - cdf_b))),
            "median_ratio": ratios[1],
            "quantile_ratios": {str(q): r for q, r in zip(quantiles, ratios, strict=True)},
            "n_half": [int(a.size), int(b.size)],
        }
    return out
