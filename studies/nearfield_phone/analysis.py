"""Analysis layer: distance-adjustment law and uncertainty from the sweep.

Turns the raw sweep parquet into the two deliverables the dose-model team asked
for:

* a **distance-adjustment formula** for normalized SAR, fitted per placement and
  band as an inverse-square law with a near-field offset
  ``S(d) = S_ref * ((d_ref + delta) / (d + delta))**2``;
* **uncertainty statistics** (mean, std, min, max, percentiles, coefficient of
  variation) for each normalized value, taken over the device-orientation and
  phantom ensemble.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.optimize import curve_fit

from studies.nearfield_phone import config as C

METRICS = ["sar_wb", "pssar_10g", "peak_apd", "apd_4cm2", "apd_1cm2"]
NOMINAL_D = {"front_of_eyes": 200.0, "by_cheek": 8.0, "by_belly": 200.0}


def load_sweeps() -> pd.DataFrame:
    frames = []
    for tag in ("duke", "others"):
        p = C.OUT_DIR / f"sweep_{tag}.parquet"
        if p.exists():
            frames.append(pd.read_parquet(p))
    if not frames:
        raise FileNotFoundError("no sweep parquet found; run run_sweep first")
    return pd.concat(frames, ignore_index=True)


# -- distance law -----------------------------------------------------------


def _inv_square_offset(d, A, delta):
    return A / (d + delta) ** 2


@dataclass
class DistanceFit:
    placement: str
    freq_mhz: int
    metric: str
    A: float
    delta_mm: float
    r2: float
    s_ref: float  # model value at the placement's nominal distance
    d_ref_mm: float

    def factor(self, d_mm):
        """Multiplicative adjustment relative to the nominal distance."""
        return _inv_square_offset(np.asarray(d_mm, float), self.A, self.delta_mm) / self.s_ref


def fit_distance_law(df: pd.DataFrame, placement: str, freq_mhz: int, metric: str) -> DistanceFit:
    """Fit S(d) = A / (d + delta)^2 to the nominal-orientation distance curve."""
    sub = df[
        (df.placement == placement) & (df.freq_mhz == freq_mhz) & (df.is_nominal) & (df.phantom == "duke")
    ].sort_values("distance_mm")
    d = sub.distance_mm.to_numpy()
    y = sub[metric].to_numpy()
    p0 = [y[0] * (d[0] + 10) ** 2, 10.0]
    popt, _ = curve_fit(_inv_square_offset, d, y, p0=p0, maxfev=40000, bounds=([0, 0], [np.inf, 500]))
    yhat = _inv_square_offset(d, *popt)
    r2 = 1.0 - np.sum((y - yhat) ** 2) / np.sum((y - y.mean()) ** 2)
    d_ref = NOMINAL_D[placement]
    s_ref = float(_inv_square_offset(d_ref, *popt))
    return DistanceFit(placement, freq_mhz, metric, float(popt[0]), float(popt[1]), float(r2), s_ref, d_ref)


def distance_fit_table(df: pd.DataFrame, metric: str = "pssar_10g") -> pd.DataFrame:
    rows = []
    for placement in C.PLACEMENTS:
        for mhz in sorted(df.freq_mhz.unique()):
            fit = fit_distance_law(df, placement, mhz, metric)
            rows.append(
                {
                    "placement": placement,
                    "freq_mhz": mhz,
                    "metric": metric,
                    "A": fit.A,
                    "delta_mm": fit.delta_mm,
                    "R2": fit.r2,
                    "d_ref_mm": fit.d_ref_mm,
                    "S_ref_per_W": fit.s_ref,
                }
            )
    return pd.DataFrame(rows)


# -- uncertainty ------------------------------------------------------------


def _stats(v: np.ndarray) -> dict:
    v = np.asarray(v, float)
    mean = float(v.mean())
    return {
        "mean": mean,
        "std": float(v.std(ddof=1)) if v.size > 1 else 0.0,
        "min": float(v.min()),
        "max": float(v.max()),
        "p5": float(np.percentile(v, 5)),
        "p50": float(np.percentile(v, 50)),
        "p95": float(np.percentile(v, 95)),
        "cv_pct": float(100 * v.std(ddof=1) / mean) if mean > 0 and v.size > 1 else 0.0,
        "n": int(v.size),
    }


def uncertainty_at_distance(
    df: pd.DataFrame,
    placement: str,
    freq_mhz: int,
    metric: str,
    distance_mm: float | None = None,
    over: str = "orientation",
) -> dict:
    """Stats of a normalized metric over an ensemble.

    ``over`` selects the source of variability:
    ``orientation`` (device rotations, single phantom Duke), ``phantom``
    (the nominal pose across all phantoms), or ``all`` (both combined).
    """
    d_ref = NOMINAL_D[placement] if distance_mm is None else distance_mm
    sub = df[(df.placement == placement) & (df.freq_mhz == freq_mhz)]
    # Snap to the nearest distance present in the grid.
    nearest = sub.distance_mm.iloc[(sub.distance_mm - d_ref).abs().argmin()]
    sub = sub[np.isclose(sub.distance_mm, nearest)]
    if over == "orientation":
        sub = sub[sub.phantom == "duke"]
    elif over == "phantom":
        sub = sub[sub.is_nominal]
    out = _stats(sub[metric].to_numpy())
    out.update({"distance_mm": float(nearest), "over": over})
    return out


def uncertainty_table(df: pd.DataFrame, metric: str = "pssar_10g", over: str = "orientation") -> pd.DataFrame:
    rows = []
    for placement in C.PLACEMENTS:
        for mhz in sorted(df.freq_mhz.unique()):
            s = uncertainty_at_distance(df, placement, mhz, metric, over=over)
            s.update({"placement": placement, "freq_mhz": mhz, "metric": metric})
            rows.append(s)
    cols = [
        "placement",
        "freq_mhz",
        "metric",
        "distance_mm",
        "over",
        "mean",
        "std",
        "cv_pct",
        "min",
        "p5",
        "p50",
        "p95",
        "max",
        "n",
    ]
    return pd.DataFrame(rows)[cols]
