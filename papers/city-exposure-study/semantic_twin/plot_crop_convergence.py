"""Plot the crop radius sweep, with the convergence criterion drawn on it.

The useful reading is not the curve but where it stops moving, so the lower panel
is the step change per radius against the criterion the study uses elsewhere,
half a decibel. A model whose steps have fallen under that line is converged. A
model whose steps have not is reporting a bound, not a value.
"""

from __future__ import annotations

import argparse
import json
import pathlib

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
CRITERION_DB = 0.5
ACQUIRED_M = 130.0
SERIES = [
    ("chi_isotropic_mean", "isotropic, full sphere", "#1f77b4"),
    ("chi_rooftop_mean", "macro rooftop sites, 3.1 to 60 deg", "#d62728"),
    ("chi_street_small_cell_mean", "street small cells, 0.95 to 33 deg", "#9467bd"),
    ("sky_fraction_mean", "sky fraction", "#7f7f7f"),
]


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", default="korenmarkt")
    parser.add_argument("--out", type=pathlib.Path, default=SCRIPT_DIR / "outputs/crop_convergence")
    return parser.parse_args()


def main() -> None:
    args = arguments()
    payload = json.loads((args.out / f"{args.site}_crop_convergence.json").read_text())
    rows = payload["rows"]
    radius = np.array([r["crop_radius_m"] for r in rows], dtype=float)

    figure, (upper, lower) = plt.subplots(
        2, 1, figsize=(7.2, 6.4), sharex=True, gridspec_kw={"height_ratios": [1.35, 1.0]}
    )

    for key, label, colour in SERIES:
        values = np.array([r[key] for r in rows], dtype=float)
        upper.plot(radius, values / values[-1], "o-", color=colour, label=label, lw=1.6, ms=5)
        upper.set_yscale("log")
        # Floor the step so an exactly converged pair does not send a log axis
        # to minus infinity and draw a spike where the answer stopped moving.
        step = np.maximum(np.abs(10.0 * np.log10(values[1:] / values[:-1])), 1e-4)
        lower.plot(radius[1:], step, "o-", color=colour, lw=1.6, ms=5)

    upper.set_ylabel("relative to the widest crop")
    upper.axhline(1.0, color="0.75", lw=0.8, zorder=0)
    upper.legend(frameon=False, loc="upper right")
    upper.set_title(f"{args.site}, {rows[0]['observers']} fixed observers, only the surroundings change")

    lower.axhline(CRITERION_DB, color="0.4", ls="--", lw=1.0)
    lower.text(radius[1], CRITERION_DB * 1.12, f"{CRITERION_DB} dB convergence criterion", color="0.35", fontsize=9)
    lower.set_yscale("log")
    lower.set_ylabel("step change from the previous crop, dB")
    lower.set_xlabel("crop radius, m")

    # The curves order by how close to the horizon each model puts its weight,
    # not by how far its sources reach, so what a reader needs marked is the
    # radius the study was actually acquired at.
    for axis in (upper, lower):
        axis.axvline(ACQUIRED_M, color="0.3", ls=":", lw=1.3)
    upper.text(ACQUIRED_M + 5, upper.get_ylim()[1] * 0.55, "acquired radius", color="0.25", fontsize=8.5)

    # The precision change is a real discontinuity in the series and saying so on
    # the figure is cheaper than a reader rediscovering it as a physical effect.
    boundary = 125.0
    for axis in (upper, lower):
        axis.axvline(boundary, color="0.8", lw=0.8, zorder=0)
    upper.text(boundary + 3, upper.get_ylim()[0] + 0.02, "float64 builds", color="0.5", fontsize=8)

    figure.tight_layout()
    for suffix in ("png", "pdf"):
        figure.savefig(args.out / f"{args.site}_crop_convergence.{suffix}", dpi=170)
    print(f"wrote {args.out / f'{args.site}_crop_convergence.png'}")


if __name__ == "__main__":
    main()
