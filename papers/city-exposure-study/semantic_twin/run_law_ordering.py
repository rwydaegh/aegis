"""Does the corrected illumination law reorder the eleven cities, or only shift them?

`run_law_comparison.py` measured the law shift at Korenmarkt alone and found
+5.67 dB rooftop and +3.98 dB street at the 250 m crop. A level shift common to
all eleven squares reorders nothing, so the shift alone does not settle whether
the ordering moves. What settles it is the spread of the per site shift about
its own mean, and that is what this script measures.

It needs no tracing. `make_sensitivity_study.py` harvests, for every standpoint
at all eleven sites, the reduced angular vector

    W[b] = dOmega * sum over escaping rays in elevation bin b of
           throughput / n_cell(ray)

and both laws here are uniform in azimuth, so `chi` under either of them is the
dot product `W . Q`. The old fixed height law is `1/sin^3` over a hand written
support and the corrected one is the cubed slant range depth of the height band,
and both are functions of elevation alone. The two are therefore evaluated on
identical rays at every standpoint of every site, which means the difference
between them carries no Monte Carlo noise at all.

The one thing that is not exact is the elevation binning, 0.04 degrees. The old
law is discontinuous at its support edge and rises as `1/sin^3` just inside it,
which is a harder integrand for a histogram than the corrected law, whose weight
goes to zero at the edge. So the binning is measured rather than assumed: `Q` is
evaluated both at the bin centre and averaged across the bin, and the two are
reported against the effect.

    python run_law_ordering.py
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

import numpy as np
from scipy import stats

ROOT = pathlib.Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from make_sensitivity_study import OUTPUT as SENSITIVITY_OUTPUT  # noqa: E402
from make_sensitivity_study import Reweighter, elevation_centres, site_list  # noqa: E402
from semantic_twin.illumination import VARIANTS, IlluminationModel  # noqa: E402

OUTPUT = ROOT / "outputs" / "law_comparison"

#: A cross city run traced under the old law, at the same 250 m crop, at 80
#: standpoints rather than the harvest's 40 and on a different seed. It is the
#: only independent check available on the old law, because the old law is not
#: in ``MODELS`` and so was never traced at the harvested standpoints.
OLD_LAW_RUN = ROOT / "outputs" / "exposure_korenmarkt" / "cities250_15ghz_summary.json"

#: Sites whose ground datum was re-estimated after that run, so their level in it
#: is the roof of a building rather than the square. SPINE.md R1.
DATUM_MOVED = ("krakow_rynek", "toulouse_capitole")

#: Corrected model -> the model it replaces, as in `run_law_comparison.py`.
#: Only these pairs differ in the law and in nothing else.
PAIRS = {"rooftop": "rooftop_fixed_height", "street_small_cell": "street_small_cell_fixed_height"}

#: Quadrature for the normalising integral. Checked against 2000001 below rather
#: than trusted, because `1/sin^3` from 0.95 degrees is the worst integrand here.
QUADRATURE = 200_001

LABEL = {
    "brussels_grandplace": "Brussels",
    "korenmarkt": "Ghent",
    "krakow_rynek": "Krakow",
    "london_trafalgar": "London",
    "madrid_plazamayor": "Madrid",
    "mexico_zocalo": "Mexico City",
    "milan_duomo": "Milan",
    "newyork_timessquare": "New York",
    "prague_staromestske": "Prague",
    "tokyo_hachiko": "Tokyo",
    "toulouse_capitole": "Toulouse",
}


def density_at(model: IlluminationModel, elevation_deg: np.ndarray) -> np.ndarray:
    """`Q_S` in sr^-1 on an elevation axis, through the shipped model."""
    elevation = np.radians(elevation_deg)
    directions = np.column_stack([np.cos(elevation), np.zeros_like(elevation), np.sin(elevation)])
    return model.density(directions, model.normalisation(QUADRATURE))


def bin_averaged_density(model: IlluminationModel, bins: int, samples: int = 65) -> np.ndarray:
    """`Q_S` averaged across each elevation bin rather than read at its centre.

    The histogram knows only which bin a ray escaped into, so replacing the ray's
    own `Q` by the bin centre's is an approximation. Averaging uniformly across
    the bin is a different approximation with the same status. Neither is right,
    and the gap between them is the size of the question, which is why both are
    computed.
    """
    edges = np.linspace(-90.0, 90.0, bins + 1)
    offsets = np.linspace(0.0, 1.0, samples)
    width = edges[1] - edges[0]
    grid = edges[:-1][:, None] + width * offsets[None, :]
    values = density_at(model, grid.ravel()).reshape(bins, samples)
    return np.trapezoid(values, offsets, axis=1)


def quadrature_check() -> dict[str, float]:
    """Relative error of the normalising quadrature against a ten times finer one."""
    out = {}
    for name in [*PAIRS, *PAIRS.values()]:
        model = VARIANTS[name]
        reference = model.integrate(2_000_001)
        out[name] = float(abs(model.integrate(QUADRATURE) / reference - 1.0))
    return out


def against_old_law_run(reweighters: dict[str, Reweighter], old: str) -> dict[str, object]:
    """Harvested old law site medians against a production run under that law.

    The harvest reproduces the corrected law's own traced `chi` by construction,
    which `make_sensitivity_study.py` already checks. The old law has no such
    check available at the harvested standpoints, so it is checked against a
    different run at a different standpoint count on a different seed instead.
    Agreement there is the reason to believe the old law numbers at the sites
    that run does not cover.
    """
    if not OLD_LAW_RUN.exists() or old != "rooftop_fixed_height":
        return {"available": False}
    sites = json.loads(OLD_LAW_RUN.read_text())["sites"]
    axis = elevation_centres(int(next(iter(reweighters.values())).fine.shape[1]))
    weight = density_at(VARIANTS[old], axis)
    rows = {}
    for site, block in sites.items():
        if site not in reweighters or "chi_rooftop" not in block:
            continue
        run_db = 10.0 * np.log10(block["chi_rooftop"]["quantiles"]["0.5"])
        harvest_db = 10.0 * np.log10(np.median(reweighters[site].fine @ weight))
        rows[site] = {
            "run_median_db": float(run_db),
            "harvested_median_db": float(harvest_db),
            "difference_db": float(harvest_db - run_db),
            "ground_datum_moved_since": site in DATUM_MOVED,
        }
    clean = [abs(v["difference_db"]) for v in rows.values() if not v["ground_datum_moved_since"]]
    return {
        "available": True,
        "run": OLD_LAW_RUN.name,
        "per_site": rows,
        "sites_compared": len(rows),
        "sites_clean": len(clean),
        "max_abs_difference_db_clean": float(max(clean)) if clean else None,
        "median_abs_difference_db_clean": float(np.median(clean)) if clean else None,
    }


def low_elevation_diagnostic(
    reweighters: dict[str, Reweighter], new: str, old: str, cut_deg: float
) -> dict[str, object]:
    """Why the shift is not the same at every square.

    The old law is `1/sin^3` and puts its mass just above the support floor, so
    what it returns at a square is set by how much power that square lets in near
    the horizon. The corrected law samples the middle of the band instead. So the
    per site shift should track how much of the old law's own answer came from
    below a few degrees, and this measures whether it does.
    """
    sites = sorted(reweighters)
    axis = elevation_centres(int(next(iter(reweighters.values())).fine.shape[1]))
    weight_new = density_at(VARIANTS[new], axis)
    weight_old = density_at(VARIANTS[old], axis)
    below = axis < cut_deg
    share = []
    shift = []
    rows = {}
    for site in sites:
        fine = reweighters[site].fine
        chi_old = fine @ weight_old
        chi_new = fine @ weight_new
        fraction = float(np.median((fine @ (weight_old * below)) / chi_old))
        rows[site] = {
            "old_law_share_below_cut": fraction,
            "new_law_share_below_cut": float(np.median((fine @ (weight_new * below)) / chi_new)),
        }
        share.append(fraction)
        shift.append(10.0 * np.log10(np.median(chi_new) / np.median(chi_old)))
    residual = np.array(shift) - np.mean(shift)
    return {
        "cut_deg": cut_deg,
        "per_site": rows,
        "pearson_residual_against_share": float(stats.pearsonr(residual, np.array(share)).statistic),
        "spearman_residual_against_share": float(stats.spearmanr(residual, np.array(share)).statistic),
    }


def _rank(values: np.ndarray) -> np.ndarray:
    """Rank 1 = most exposed."""
    return stats.rankdata(-values, method="ordinal").astype(int)


def compare(reweighters: dict[str, Reweighter], new: str, old: str, *, centred: bool) -> dict[str, object]:
    sites = sorted(reweighters)
    bins = int(next(iter(reweighters.values())).fine.shape[1])
    axis = elevation_centres(bins)
    if centred:
        weight_new = density_at(VARIANTS[new], axis)
        weight_old = density_at(VARIANTS[old], axis)
    else:
        weight_new = bin_averaged_density(VARIANTS[new], bins)
        weight_old = bin_averaged_density(VARIANTS[old], bins)

    rows: dict[str, dict[str, float]] = {}
    for site in sites:
        fine = reweighters[site].fine
        chi_new = fine @ weight_new
        chi_old = fine @ weight_old
        rows[site] = {
            "standpoints": int(fine.shape[0]),
            "median_chi_new": float(np.median(chi_new)),
            "median_chi_old": float(np.median(chi_old)),
            "median_db_new": float(10.0 * np.log10(np.median(chi_new))),
            "median_db_old": float(10.0 * np.log10(np.median(chi_old))),
            "shift_of_medians_db": float(10.0 * np.log10(np.median(chi_new) / np.median(chi_old))),
            # Exactly paired: every standpoint's own two numbers come off the
            # same rays, so this one carries no Monte Carlo noise even in
            # principle. The shift of the medians can in principle pick a
            # different standpoint for each law, so both are reported.
            "median_of_paired_shifts_db": float(np.median(10.0 * np.log10(chi_new / chi_old))),
            "p05_of_paired_shifts_db": float(np.quantile(10.0 * np.log10(chi_new / chi_old), 0.05)),
            "p95_of_paired_shifts_db": float(np.quantile(10.0 * np.log10(chi_new / chi_old), 0.95)),
        }

    new_db = np.array([rows[s]["median_db_new"] for s in sites])
    old_db = np.array([rows[s]["median_db_old"] for s in sites])
    shift = new_db - old_db
    rank_new = _rank(new_db)
    rank_old = _rank(old_db)
    for i, site in enumerate(sites):
        rows[site]["rank_new"] = int(rank_new[i])
        rows[site]["rank_old"] = int(rank_old[i])
        rows[site]["rank_move"] = int(rank_old[i] - rank_new[i])

    spearman = stats.spearmanr(new_db, old_db)
    kendall = stats.kendalltau(new_db, old_db)
    residual = shift - shift.mean()
    return {
        "sites": sites,
        "per_site": rows,
        "mean_shift_db": float(shift.mean()),
        "median_shift_db": float(np.median(shift)),
        "min_shift_db": float(shift.min()),
        "max_shift_db": float(shift.max()),
        "shift_range_db": float(np.ptp(shift)),
        "residual_rms_db": float(np.sqrt(np.mean(residual**2))),
        "residual_max_abs_db": float(np.max(np.abs(residual))),
        "spearman": float(spearman.statistic),
        "spearman_p": float(spearman.pvalue),
        "kendall": float(kendall.statistic),
        "kendall_p": float(kendall.pvalue),
        "rank_changes": int(np.sum(rank_new != rank_old)),
        "max_rank_move": int(np.max(np.abs(rank_new - rank_old))),
        "spread_new_db": float(new_db.max() - new_db.min()),
        "spread_old_db": float(old_db.max() - old_db.min()),
        "ordering_new": [sites[i] for i in np.argsort(-new_db)],
        "ordering_old": [sites[i] for i in np.argsort(-old_db)],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=pathlib.Path, default=OUTPUT / "eleven_city_law_ordering.json")
    args = parser.parse_args(argv)

    reweighters: dict[str, Reweighter] = {}
    for site in site_list():
        path = SENSITIVITY_OUTPUT / f"harvest_{site}.npz"
        if path.exists():
            reweighters[site] = Reweighter(path)
        else:
            print(f"[skip] {site}: no harvest", flush=True)
    if len(reweighters) < 2:
        raise SystemExit("need at least two harvested sites")

    report: dict[str, object] = {
        "generator": "run_law_ordering.py",
        "harvest": str(SENSITIVITY_OUTPUT),
        "sites": sorted(reweighters),
        "standpoints_per_site": {s: rw.locations for s, rw in reweighters.items()},
        "normalisation_quadrature_rel_error": quadrature_check(),
        "note": (
            "Both laws are evaluated on the same harvested rays at every standpoint, "
            "so the difference between them carries no Monte Carlo noise."
        ),
    }

    for new, old in PAIRS.items():
        centred = compare(reweighters, new, old, centred=True)
        averaged = compare(reweighters, new, old, centred=False)
        centred["binning_check"] = {
            "mean_shift_db_bin_averaged": averaged["mean_shift_db"],
            "residual_rms_db_bin_averaged": averaged["residual_rms_db"],
            "spearman_bin_averaged": averaged["spearman"],
            "kendall_bin_averaged": averaged["kendall"],
            "rank_changes_bin_averaged": averaged["rank_changes"],
            "per_site_shift_difference_db": {
                s: float(centred["per_site"][s]["shift_of_medians_db"] - averaged["per_site"][s]["shift_of_medians_db"])
                for s in centred["sites"]
            },
            "max_abs_site_shift_difference_db": max(
                abs(centred["per_site"][s]["shift_of_medians_db"] - averaged["per_site"][s]["shift_of_medians_db"])
                for s in centred["sites"]
            ),
        }
        centred["against_old_law_run"] = against_old_law_run(reweighters, old)
        centred["low_elevation_diagnostic"] = low_elevation_diagnostic(
            reweighters, new, old, 5.0 if new == "rooftop" else 3.0
        )
        report[new] = centred

        print(f"\n== {new} against {old} ==")
        print(f"{'site':14s} {'old dB':>9s} {'new dB':>9s} {'shift':>8s} {'resid':>8s}  rank old -> new")
        mean_shift = centred["mean_shift_db"]
        for site in sorted(centred["sites"], key=lambda s: centred["per_site"][s]["rank_new"]):
            row = centred["per_site"][site]
            print(
                f"{LABEL.get(site, site):14s} {row['median_db_old']:9.2f} {row['median_db_new']:9.2f} "
                f"{row['shift_of_medians_db']:8.2f} {row['shift_of_medians_db'] - mean_shift:8.2f}"
                f"   {row['rank_old']:2d} -> {row['rank_new']:2d}"
            )
        print(
            f"mean shift {mean_shift:+.2f} dB, range {centred['min_shift_db']:+.2f} to "
            f"{centred['max_shift_db']:+.2f} dB, residual rms {centred['residual_rms_db']:.2f} dB, "
            f"worst {centred['residual_max_abs_db']:.2f} dB"
        )
        print(
            f"Spearman {centred['spearman']:.4f} (p={centred['spearman_p']:.2g}), "
            f"Kendall {centred['kendall']:.4f} (p={centred['kendall_p']:.2g}), "
            f"{centred['rank_changes']} of {len(centred['sites'])} sites change rank, "
            f"largest move {centred['max_rank_move']}"
        )
        print(
            f"cross city spread {centred['spread_old_db']:.2f} dB old, {centred['spread_new_db']:.2f} dB new. "
            f"binning: mean shift moves {abs(centred['binning_check']['mean_shift_db_bin_averaged'] - mean_shift):.3f} dB, "
            f"worst site {centred['binning_check']['max_abs_site_shift_difference_db']:.3f} dB"
        )
        diagnostic = centred["low_elevation_diagnostic"]
        print(
            f"share of the old law answer below {diagnostic['cut_deg']:g} deg against the residual: "
            f"Pearson {diagnostic['pearson_residual_against_share']:+.3f}, "
            f"Spearman {diagnostic['spearman_residual_against_share']:+.3f}"
        )
        check = centred["against_old_law_run"]
        if check["available"]:
            print(
                f"harvested old law against {check['run']}: {check['sites_clean']} sites free of the datum change "
                f"agree to {check['max_abs_difference_db_clean']:.2f} dB worst, "
                f"{check['median_abs_difference_db_clean']:.2f} dB median"
            )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=1) + "\n")
    print(f"\n[done] {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
