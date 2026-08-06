"""What the bounces add, and why the older estimator said something else.

Two panels, one question. A pedestrian sees some rooftops directly. How much
more do they get once the walls and the ground are allowed to bounce?

Left: the answer from next event estimation, which connects each path vertex to
explicit rooftop points and divides by range. The direct term is 1 by
construction, so the bar is the whole story and no transmit power or antenna
count appears anywhere. Beside it, the same ratio from the escape estimator the
study used before, which credits a ray for reaching the source population the
moment it leaves the scene.

Right: why they differ. Each held out standpoint is one dot, its own site mean
removed from both axes, so what is left is how each estimator responds to how
much sky is overhead. The escape answer is dominated by it. The next event
answer is nearly flat. That is the evidence that the older number was largely
restating openness rather than measuring multipath.

The reason is what the two estimators take the sources to be, and it is not the
missing range term. ``archive/scripts/measure_escape_range_term.py`` charges every escaping ray
for the distance it travelled and the escape answer moves 0.13 dB at Korenmarkt
and 0.35 dB at Brussels, against a gap of about 1.3 dB, so range is a quarter of
it at most. What is left is the source population. The escape estimator assumes
sites of uniform density filling a band 13.5 to 43.5 m above the head out to
250 m, which fills whatever sky is visible; next event uses the square's own
measured roofline, which is a thin rim. A bounce point up a wall sees more sky
than the head does, so the assumed population rewards it and the measured rim
barely does. That is exactly the slope in this panel.

Run from the ``semantic_twin`` directory::

    ../../../.venv/bin/python FIGURES/make_multipath_surplus.py
"""

from __future__ import annotations

import json
import pathlib
import sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, "/home/user/aegis/theory/scripts")

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from _plot_style import apply_monograph_style, fig_size_ieee  # noqa: E402

OUT = pathlib.Path(__file__).resolve().parent
SOURCE = ROOT / "outputs" / "next_event" / "eleven_250m.json"

SHORT = {
    "brussels_grandplace": "Grand-Place",
    "korenmarkt": "Korenmarkt",
    "krakow_rynek": "Rynek",
    "london_trafalgar": "Trafalgar",
    "madrid_plazamayor": "Plaza Mayor",
    "mexico_zocalo": "Zocalo",
    "milan_duomo": "Duomo",
    "newyork_timessquare": "Times Sq",
    "prague_staromestske": "Staromestske",
    "tokyo_hachiko": "Hachiko",
    "toulouse_capitole": "Capitole",
}


def escape_surplus_db(point: dict) -> float:
    """The escape estimator's own (direct + bounced) / direct, in decibels."""
    whole = point["escape_chi"]["rooftop"]
    line = point["escape_chi_direct"]["rooftop"]
    return 10.0 * np.log10(whole / line) if line > 0.0 else float("nan")


def main() -> None:
    rows = json.loads(SOURCE.read_text())["rows"]
    rows.sort(key=lambda r: r["surplus_db_median"])

    apply_monograph_style()
    figure, (bars, scatter) = plt.subplots(1, 2, figsize=fig_size_ieee(columns=2, aspect=0.42))

    names = [SHORT.get(r["site"], r["site"]) for r in rows]
    y = np.arange(len(rows))
    surplus = np.array([r["surplus_db_median"] for r in rows])
    escape = np.array([r["escape_surplus_db_median"] for r in rows])
    low = surplus - np.array([r["surplus_db_p5"] for r in rows])
    high = np.array([r["surplus_db_p95"] for r in rows]) - surplus

    bars.barh(y + 0.19, escape, height=0.36, color="0.75", label="escape weighted")
    bars.barh(y - 0.19, surplus, height=0.36, xerr=[low, high], color="C0", error_kw={"lw": 0.7}, label="next event")
    bars.set_yticks(y)
    bars.set_yticklabels(names)
    bars.set_xlabel("surplus over line of sight (dB)")
    bars.legend(loc="lower right", frameon=False)
    bars.set_title("what the bounces add", loc="left")

    # Site means removed from both axes, so the panel shows the response to sky
    # within a square rather than the differences between squares.
    sky, near, far = [], [], []
    for row in rows:
        points = row["per_point"]
        s = np.array([p["sky_fraction"] for p in points])
        n = np.array([p["surplus_db"] for p in points])
        f = np.array([escape_surplus_db(p) for p in points])
        sky.append(s - s.mean())
        near.append(n - n.mean())
        far.append(f - f.mean())
    sky, near, far = (np.concatenate(v) for v in (sky, near, far))

    grid = np.linspace(sky.min(), sky.max(), 2)
    for values, colour, label in ((far, "0.55", "escape weighted"), (near, "C0", "next event")):
        scatter.scatter(sky, values, s=4, color=colour, alpha=0.55, edgecolors="none")
        slope, intercept = np.polyfit(sky, values, 1)
        scatter.plot(
            grid,
            slope * grid + intercept,
            color=colour,
            lw=1.4,
            label=f"{label}, {slope:+.2f} dB per unit sky",
        )
    scatter.axhline(0.0, color="0.8", lw=0.6, zorder=0)
    scatter.set_xlabel("sky fraction, site mean removed")
    scatter.set_ylabel("surplus, site mean removed (dB)")
    scatter.legend(loc="upper right", frameon=False)
    scatter.set_title("why they disagree", loc="left")

    figure.tight_layout()
    for suffix in (".pdf", ".png"):
        figure.savefig(OUT / f"23_multipath_surplus{suffix}", dpi=300)
    print(f"wrote {OUT / '23_multipath_surplus.pdf'}")

    # The slopes are the claim, so print them rather than leaving them to be
    # read off a picture.
    for values, label in ((near, "next event"), (far, "escape weighted")):
        slope = np.polyfit(sky, values, 1)[0]
        print(f"  {label:16s} {slope:+.2f} dB per unit sky fraction, r = {np.corrcoef(sky, values)[0, 1]:+.3f}")


if __name__ == "__main__":
    main()
