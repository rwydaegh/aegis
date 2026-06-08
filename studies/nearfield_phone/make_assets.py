"""Build the report assets: figures (IEEE style) and the partner Excel file.

Outputs (under ``studies/nearfield_phone/``):

* ``report/figures/fig_distance_metrics.pdf`` - the four ICNIRP metrics vs
  distance with the orientation envelope and the inverse-square-offset fit.
* ``report/figures/fig_distance_bands.pdf``   - psSAR10g distance law per band.
* ``report/figures/fig_uncertainty.pdf``       - orientation spread per placement.
* ``report/figures/fig_distance_factor.pdf``   - distance-adjustment factor and
  the worked example applied to the 2.62 W/kg/W brain reference.
* ``out/nearfield_dose_results.xlsx``          - the partner Excel file.
"""

from __future__ import annotations

import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from studies.nearfield_phone import analysis as A
from studies.nearfield_phone import config as C

sys.path.insert(0, str(C.REPO / "theory" / "scripts"))
from _plot_style import apply_monograph_style  # noqa: E402

# Single-column report: figures span the full text width (~6.5 in) and are wider
# than tall. aspect = height / width.
REPORT_W_IN = 6.5


def rsize(aspect: float) -> tuple[float, float]:
    return (REPORT_W_IN, REPORT_W_IN * float(aspect))


# The dose-model team's cited reference value.
BRAIN_REF = {
    "value_W_per_kg_per_W": 2.62,
    "tissue": "brain",
    "scenario": "front_of_eyes_center_vertical",
    "phantom": "Duke",
    "d_ref_mm": 200.0,
}
REPORT_BAND = 2450
METRIC_LABELS = {
    "sar_wb": r"whole-body SAR  [W/kg per W]",
    "pssar_10g": r"psSAR10g  [W/kg per W]",
    "peak_apd": r"peak APD  [W/m$^2$ per W]",
    "apd_4cm2": r"4 cm$^2$ APD  [W/m$^2$ per W]",
}


def fig_distance_metrics(df):
    apply_monograph_style(mode="png")
    metrics = ["pssar_10g", "sar_wb", "peak_apd", "apd_4cm2"]
    fig, axes = plt.subplots(2, 2, figsize=rsize(0.62))
    pl = "front_of_eyes"
    sub_all = df[(df.placement == pl) & (df.freq_mhz == REPORT_BAND) & (df.phantom == "duke")]
    for ax, met in zip(axes.ravel(), metrics, strict=False):
        # Orientation envelope.
        grp = sub_all.groupby("distance_mm")[met]
        d = np.array(sorted(sub_all.distance_mm.unique()))
        lo = grp.quantile(0.05).reindex(d).to_numpy()
        hi = grp.quantile(0.95).reindex(d).to_numpy()
        nominal = sub_all[sub_all.is_nominal].sort_values("distance_mm")
        ax.fill_between(d, lo, hi, alpha=0.2, color="C0", label="orientation P5-P95")
        ax.plot(nominal.distance_mm, nominal[met], "o", ms=3, color="C0", label="nominal pose")
        fit = A.fit_distance_law(df, pl, REPORT_BAND, met)
        dd = np.geomspace(d.min(), d.max(), 100)
        ax.plot(
            dd,
            A._inv_square_offset(dd, fit.A, fit.delta_mm),
            "-",
            color="C3",
            label=rf"fit $\delta$={fit.delta_mm:.0f} mm, $R^2$={fit.r2:.3f}",
        )
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlabel("source-to-body distance [mm]")
        ax.set_ylabel(METRIC_LABELS[met])
        ax.legend(frameon=False, fontsize=8)
    fig.suptitle(f"Duke, front of eyes, {REPORT_BAND} MHz", y=1.0)
    fig.tight_layout()
    _save(fig, "fig_distance_metrics")


def fig_distance_bands(df):
    apply_monograph_style(mode="png")
    fig, ax = plt.subplots(figsize=rsize(0.52))
    pl = "front_of_eyes"
    bands = sorted(df.freq_mhz.unique())
    cmap = plt.cm.viridis(np.linspace(0, 0.95, len(bands)))
    for c, mhz in zip(cmap, bands, strict=False):
        sub = df[(df.placement == pl) & (df.freq_mhz == mhz) & df.is_nominal & (df.phantom == "duke")].sort_values(
            "distance_mm"
        )
        ls = ":" if mhz in C.UNRELIABLE_EFFICIENCY_MHZ else "-"
        ax.plot(sub.distance_mm, sub.pssar_10g, ls, color=c, label=f"{mhz}")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("source-to-body distance [mm]")
    ax.set_ylabel(r"psSAR10g  [W/kg per W]")
    ax.set_title("Distance law across bands (front of eyes)")
    ax.legend(frameon=False, fontsize=8, ncol=2, title="MHz", title_fontsize=8)
    fig.tight_layout()
    _save(fig, "fig_distance_bands")


def fig_uncertainty(df):
    apply_monograph_style(mode="png")
    fig, ax = plt.subplots(figsize=rsize(0.5))
    data, labels = [], []
    for pl in C.PLACEMENTS:
        d_ref = A.NOMINAL_D[pl]
        sub = df[(df.placement == pl) & (df.freq_mhz == REPORT_BAND) & (df.phantom == "duke")]
        nearest = sub.distance_mm.iloc[(sub.distance_mm - d_ref).abs().argmin()]
        v = sub[np.isclose(sub.distance_mm, nearest)].pssar_10g.to_numpy()
        # normalise each to its own nominal so the spread is comparable.
        nom = sub[np.isclose(sub.distance_mm, nearest) & sub.is_nominal].pssar_10g.to_numpy()[0]
        data.append(v / nom)
        labels.append(pl.replace("_", "\n"))
    parts = ax.violinplot(data, showmedians=True, showextrema=True)
    for pc in parts["bodies"]:
        pc.set_alpha(0.4)
    ax.set_xticks(range(1, len(labels) + 1))
    ax.set_xticklabels(labels, fontsize=8)
    ax.axhline(1.0, ls=":", color="0.4", lw=1)
    ax.set_ylabel("psSAR10g / nominal-pose value")
    ax.set_title(f"Orientation variability at nominal distance ({REPORT_BAND} MHz)")
    fig.tight_layout()
    _save(fig, "fig_uncertainty")


def applied_to_reference(df) -> pd.DataFrame:
    """Adjust the 2.62 W/kg/W brain reference to other distances with a band."""
    pl = "front_of_eyes"
    # Distance law shape from the head-region metric (psSAR10g) at the report band.
    fit = A.fit_distance_law(df, pl, REPORT_BAND, "pssar_10g")
    # Organ-scale uncertainty: brain SAR is a volume average, closest to the
    # whole-body metric; use its device-orientation CV (the variability of the
    # fixed-phantom Duke value). Inter-individual spread is reported separately.
    unc = A.uncertainty_at_distance(df, pl, REPORT_BAND, "sar_wb", over="orientation")
    cv = unc["cv_pct"] / 100.0
    rel_min = unc["min"] / unc["mean"]
    rel_max = unc["max"] / unc["mean"]

    d_ref = BRAIN_REF["d_ref_mm"]
    ref = BRAIN_REF["value_W_per_kg_per_W"]
    distances = np.array([10, 20, 50, 100, 150, 200, 250, 300, 400.0])
    factor = A._inv_square_offset(distances, fit.A, fit.delta_mm) / A._inv_square_offset(d_ref, fit.A, fit.delta_mm)
    adj = ref * factor
    return (
        pd.DataFrame(
            {
                "distance_mm": distances,
                "distance_factor": factor,
                "brain_SAR_adjusted_W_per_kg_per_W": adj,
                "minus_1sigma": adj * (1 - cv),
                "plus_1sigma": adj * (1 + cv),
                "ensemble_min": adj * rel_min,
                "ensemble_max": adj * rel_max,
            }
        ),
        fit,
        unc,
    )


def fig_distance_factor(df):
    apply_monograph_style(mode="png")
    tbl, fit, unc = applied_to_reference(df)
    fig, ax = plt.subplots(figsize=rsize(0.5))
    d = tbl.distance_mm.to_numpy()
    ax.plot(d, tbl.brain_SAR_adjusted_W_per_kg_per_W, "o-", color="C0", label="adjusted value")
    ax.fill_between(d, tbl.minus_1sigma, tbl.plus_1sigma, alpha=0.25, color="C0", label=r"$\pm 1\sigma$ (orientation)")
    ax.fill_between(d, tbl.ensemble_min, tbl.ensemble_max, alpha=0.12, color="C0", label="orientation min-max")
    ax.axvline(BRAIN_REF["d_ref_mm"], ls=":", color="0.4")
    ax.scatter(
        [BRAIN_REF["d_ref_mm"]],
        [BRAIN_REF["value_W_per_kg_per_W"]],
        color="C3",
        zorder=5,
        label="2.62 W/kg/W reference",
    )
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("phone-to-face distance [mm]")
    ax.set_ylabel("brain normalized SAR  [W/kg per W]")
    ax.set_title("Distance-adjusted brain SAR with uncertainty")
    ax.legend(frameon=False, fontsize=8, loc="upper right")
    fig.tight_layout()
    _save(fig, "fig_distance_factor")
    return tbl, fit, unc


def write_excel(df):
    path = C.OUT_DIR / "nearfield_dose_results.xlsx"
    applied_tbl, fit, unc = applied_to_reference(df)
    with pd.ExcelWriter(path, engine="xlsxwriter") as xw:
        # README sheet.
        readme = pd.DataFrame(
            {
                "field": [
                    "method",
                    "quantity",
                    "normalization",
                    "phantoms",
                    "bands_MHz",
                    "placements",
                    "distance_law",
                    "uncertainty",
                    "note_on_2.62",
                ],
                "description": [
                    "Fast near-field surface dose method (in-house, patent pending). Runs thousands of"
                    " phone positions and orientations in minutes. Does not replace full-wave: the"
                    " distance law and the uncertainty are ratios applied to a full-wave reference value.",
                    "ICNIRP 2020 metrics: whole-body SAR, psSAR10g, peak/4cm2/1cm2 APD.",
                    "Per 1 W radiated power (W/kg per W, or W/m^2 per W) - the same normalized-SAR convention.",
                    "Duke, Ella, Eartha, Thelonious.",
                    "700, 835, 1450, 2140, 2450, 3500, 5200, 5800.",
                    "front_of_eyes (200 mm), by_cheek (8 mm), by_belly (200 mm).",
                    "S(d) = A / (d + delta)^2 ; equivalently S(d)=S_ref*((d_ref+delta)/(d+delta))^2.",
                    "mean/std/min/max/percentiles over device orientation and phantom ensemble.",
                    "The 2.62 W/kg/W brain value is your reference figure; sheet 'brain_2.62_adjusted'"
                    " applies the distance law and uncertainty band to it.",
                ],
            }
        )
        readme.to_excel(xw, sheet_name="README", index=False)

        for met in ["pssar_10g", "peak_apd", "apd_4cm2", "sar_wb"]:
            A.distance_fit_table(df, met).to_excel(xw, sheet_name=f"distlaw_{met}"[:31], index=False)
        for met in ["pssar_10g", "sar_wb", "peak_apd"]:
            A.uncertainty_table(df, met, over="orientation").to_excel(
                xw, sheet_name=f"unc_orient_{met}"[:31], index=False
            )
        A.uncertainty_table(df, "pssar_10g", over="all").to_excel(xw, sheet_name="unc_all_pssar10g", index=False)

        # front_of_eyes Duke detail: per-distance stats over orientation.
        detail = _detail_table(df, "front_of_eyes", REPORT_BAND)
        detail.to_excel(xw, sheet_name="duke_fronteyes_detail", index=False)

        applied_tbl.to_excel(xw, sheet_name="brain_2.62_adjusted", index=False)
    print(f"wrote {path}")
    return path


def _detail_table(df, placement, freq_mhz) -> pd.DataFrame:
    sub = df[(df.placement == placement) & (df.freq_mhz == freq_mhz) & (df.phantom == "duke")]
    rows = []
    for d in sorted(sub.distance_mm.unique()):
        g = sub[np.isclose(sub.distance_mm, d)]
        row = {"distance_mm": d}
        for met in A.METRICS:
            v = g[met].to_numpy()
            row[f"{met}_mean"] = v.mean()
            row[f"{met}_std"] = v.std(ddof=1)
            row[f"{met}_min"] = v.min()
            row[f"{met}_max"] = v.max()
        rows.append(row)
    return pd.DataFrame(rows)


def _save(fig, name):
    fig.savefig(C.FIG_DIR / f"{name}.pdf")
    fig.savefig(C.FIG_DIR / f"{name}.png", dpi=200)
    plt.close(fig)
    print(f"wrote {C.FIG_DIR / name}.pdf")


def main():
    df = A.load_sweeps()
    fig_distance_metrics(df)
    fig_distance_bands(df)
    fig_uncertainty(df)
    tbl, fit, unc = fig_distance_factor(df)
    write_excel(df)
    print("\n--- headline numbers ---")
    print(f"psSAR10g distance law (front_of_eyes, {REPORT_BAND} MHz): delta={fit.delta_mm:.1f} mm, R2={fit.r2:.4f}")
    lo, hi = unc["min"] / unc["mean"], unc["max"] / unc["mean"]
    print(f"orientation uncertainty (sar_wb): CV={unc['cv_pct']:.0f}%, range [{lo:.2f}, {hi:.2f}] x nominal")
    print("brain 2.62 W/kg/W adjusted:")
    print(tbl.to_string(index=False))


if __name__ == "__main__":
    main()
