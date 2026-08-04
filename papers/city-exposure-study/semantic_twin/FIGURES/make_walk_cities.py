"""Both candidate walks at every square whose panoramas chain.

One panel per square. Grey is the building plan, taken from the triangles that
stand more than six metres above the pavement. Green is the panorama link path,
which is where the survey car drove. Blue is the walking path from Google Routes
between the two cameras furthest apart. Red rings are the cameras and the two
squares are the walk's A and B. The standpoints drawn are the ones that were
kept, on whichever path stands nearer a camera.

Putting six squares side by side is what shows that neither path wins
everywhere, which one square could not.

The walking path wins at Brussels, the case it was built for: a pedestrianised
square the survey car had to drive around, so the link path spends 163 m walking
up side streets and back out. It loses badly at Mexico City. The Zocalo is 240 m
across with no way mapped inside it, so Routes walks the streets around the
outside and every camera lands 24 m or more from the walk. Look at that panel:
the cameras are a green lawnmower pattern inside the plaza and the blue line is
nowhere near them.

Run from the ``semantic_twin`` directory::

    PYTHONPATH=. ../../../.venv/bin/python FIGURES/make_walk_cities.py
"""

from __future__ import annotations

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

from semantic_twin.propagation.geometry import MitsubaGeometry  # noqa: E402
from semantic_twin.walk.route import build_panorama_route, load_admitted_stations, load_link_graph  # noqa: E402
from semantic_twin.walk.site import site_walk  # noqa: E402
from semantic_twin.walk.ground import measure_ground_datum  # noqa: E402

OUT = pathlib.Path(__file__).resolve().parent

#: Every square with enough admitted stations to chain into a route. Milan has
#: one, London and Times Square have none that pass the residual gate, and Krakow
#: and Toulouse have no panorama directory at all.
SITES = {
    "korenmarkt": "Ghent Korenmarkt",
    "brussels_grandplace": "Brussels Grand-Place",
    "madrid_plazamayor": "Madrid Plaza Mayor",
    "mexico_zocalo": "Mexico City Zocalo",
    "prague_staromestske": "Prague Old Town",
    "tokyo_hachiko": "Tokyo Hachiko",
}
REACH_M = 110.0


def site_mesh(site: str, crop_m: int = 250) -> pathlib.Path:
    root = ROOT / "data" / "geometry" / site
    precise = root / f"inhouse_leaf_{crop_m}m_f64.ply"
    return precise if precise.exists() else root / f"inhouse_leaf_{crop_m}m.ply"


def main() -> None:
    apply_monograph_style()
    figure, panels = plt.subplots(2, 3, figsize=fig_size_ieee(columns=2, aspect=0.72))
    rows = []

    for panel, (site, title) in zip(panels.ravel(), SITES.items(), strict=True):
        geometry = MitsubaGeometry(site_mesh(site), variant="llvm_ad_rgb")
        datum = measure_ground_datum(geometry, radius_m=90.0)
        route = build_panorama_route(geometry, load_admitted_stations(site), load_link_graph(site))
        walk, provenance = site_walk(geometry, site, stride_m=6.0, path="closest")
        _, street_only = site_walk(geometry, site, stride_m=6.0, path="street")
        street = np.asarray(street_only["street_route"]["polyline_enu"])

        centres = geometry.vertices[geometry.faces].mean(axis=1)
        plan = centres[centres[:, 2] > datum.z_m + 6.0]
        panel.scatter(plan[:, 0], plan[:, 1], s=0.04, color="0.86", edgecolors="none", zorder=0)

        first = True
        for leg in route.road_polyline:
            if leg is not None and len(leg) >= 2:
                panel.plot(
                    leg[:, 0],
                    leg[:, 1],
                    color="C1",
                    lw=1.3,
                    alpha=0.85,
                    zorder=2,
                    label="panorama links" if first else None,
                )
                first = False
        panel.plot(street[:, 0], street[:, 1], color="C0", lw=1.1, zorder=3, label="walking route")
        panel.scatter(walk.points[:, 0], walk.points[:, 1], s=4, color="C0", edgecolors="none", zorder=4)

        cameras = route.walk.points
        panel.scatter(
            cameras[:, 0], cameras[:, 1], s=20, facecolors="none", edgecolors="C3", lw=0.8, zorder=5, label="camera"
        )
        ends = cameras[street_only["street_route"]["endpoint_stations"]]
        panel.scatter(ends[:, 0], ends[:, 1], s=44, marker="s", facecolors="none", edgecolors="C3", lw=0.8, zorder=6)

        street_m = street_only["street_route"]["distance_m"]
        links_m = provenance["road_length_m"]
        tried = provenance["path_candidates_m"]
        panel.set_xlim(-REACH_M, REACH_M)
        panel.set_ylim(-REACH_M, REACH_M)
        panel.set_aspect("equal")
        panel.set_title(title, loc="left")
        panel.text(
            0.03,
            0.03,
            f"links {links_m:.0f} m, walk {street_m:.0f} m\n"
            f"from a camera: links {tried['links']:.1f} m, walk {tried['street']:.1f} m\n"
            f"kept {provenance['path']}, {len(walk)} standpoints",
            transform=panel.transAxes,
            fontsize=5.5,
            va="bottom",
        )
        rows.append((title, provenance["stations"], links_m, street_m, tried, provenance["path"], len(walk)))

    for panel in panels[-1]:
        panel.set_xlabel("east (m)")
    for panel in panels[:, 0]:
        panel.set_ylabel("north (m)")
    panels[0, 0].legend(loc="upper right", frameon=False, fontsize=5.5, markerscale=1.4)
    figure.tight_layout()
    for suffix in (".pdf", ".png"):
        figure.savefig(OUT / f"25_walk_cities{suffix}", dpi=300)

    head = f"{'square':22s} {'cams':>4s} {'links':>7s} {'walk':>7s} | {'gap links':>9s} {'gap walk':>9s} {'kept':>7s}"
    print(head)
    for title, cams, links_m, street_m, tried, kept, stands in rows:
        print(
            f"{title:22s} {cams:4d} {links_m:6.0f}m {street_m:6.0f}m | "
            f"{tried['links']:8.1f}m {tried['street']:8.1f}m {kept:>7s} ({stands} standpoints)"
        )
    print(f"wrote {OUT / '25_walk_cities.pdf'}")


if __name__ == "__main__":
    main()
