"""Where the walk stands now, against where it used to stand.

The grid builder lays a three metre lattice over a disc, keeps the squares whose
ground is walkable, and joins the survivors nearest neighbour first. That is a
flood fill of the open ground. It is not a route, and most of its standpoints
are nowhere near a camera, which matters because the guarantee behind the whole
method is that a photograph taken at a point sees the surfaces that scatter
energy into that point. Past forty metres from a camera that guarantee is worth
about a tenth.

So this draws both. Grey is the grid. Blue is the capture route: the cameras
themselves as large dots, the street between them as a line, and the standpoints
the stride added along that street as small dots. The number under each panel is
how far the average standpoint is from the nearest camera, which is the quantity
the evidence argument turns on.

Run from the ``semantic_twin`` directory::

    ../../../.venv/bin/python FIGURES/make_walk_route.py
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
from semantic_twin.propagation.route import (  # noqa: E402
    build_panorama_route,
    load_admitted_stations,
    load_link_graph,
    site_walk,
)
from semantic_twin.propagation.walk import build_walk, measure_ground_datum  # noqa: E402

OUT = pathlib.Path(__file__).resolve().parent
SITES = ("korenmarkt", "brussels_grandplace")
TITLE = {"korenmarkt": "Korenmarkt", "brussels_grandplace": "Brussels Grand-Place"}


def site_mesh(site: str, crop_m: int = 250) -> pathlib.Path:
    root = ROOT / "data" / "geometry" / site
    precise = root / f"inhouse_leaf_{crop_m}m_f64.ply"
    return precise if precise.exists() else root / f"inhouse_leaf_{crop_m}m.ply"


def footprint(geometry: MitsubaGeometry, datum_z: float) -> np.ndarray:
    """Triangle centres of everything standing well above the pavement.

    A cheap plan of the buildings. Drawing the mesh itself would be six hundred
    thousand triangles for a panel three centimetres wide.
    """
    centres = geometry.vertices[geometry.faces].mean(axis=1)
    return centres[centres[:, 2] > datum_z + 6.0]


def nearest_camera_m(points: np.ndarray, cameras: np.ndarray) -> np.ndarray:
    gap = points[:, None, :2] - cameras[None, :, :2]
    return np.linalg.norm(gap, axis=2).min(axis=1)


def main() -> None:
    apply_monograph_style()
    figure, panels = plt.subplots(1, len(SITES), figsize=fig_size_ieee(columns=2, aspect=0.5))

    for panel, site in zip(np.atleast_1d(panels), SITES, strict=True):
        geometry = MitsubaGeometry(site_mesh(site), variant="llvm_ad_rgb")
        datum = measure_ground_datum(geometry, radius_m=90.0)

        stations = load_admitted_stations(site)
        graph = load_link_graph(site)
        route = build_panorama_route(geometry, stations, graph)
        walk, provenance = site_walk(geometry, site, stride_m=6.0)
        grid = build_walk(geometry, ground_datum_m=datum.z_m, radius_m=90.0, spacing_m=3.0, seed=0)

        plan = footprint(geometry, datum.z_m)
        panel.scatter(plan[:, 0], plan[:, 1], s=0.05, color="0.86", edgecolors="none", zorder=0)
        panel.scatter(grid.points[:, 0], grid.points[:, 1], s=3, color="0.55", edgecolors="none", label="grid walk")

        for leg in route.road_polyline:
            if leg is not None and len(leg) >= 2:
                panel.plot(leg[:, 0], leg[:, 1], color="C0", lw=1.0, zorder=3)
        panel.scatter(walk.points[:, 0], walk.points[:, 1], s=6, color="C0", edgecolors="none", zorder=4)
        cameras = route.walk.points
        panel.scatter(
            cameras[:, 0],
            cameras[:, 1],
            s=26,
            facecolors="none",
            edgecolors="C3",
            lw=0.9,
            zorder=5,
            label="camera",
        )

        reach = 1.15 * np.abs(np.concatenate([grid.points[:, :2].ravel(), walk.points[:, :2].ravel()])).max()
        panel.set_xlim(-reach, reach)
        panel.set_ylim(-reach, reach)
        panel.set_aspect("equal")
        panel.set_xlabel("east (m)")
        panel.set_title(TITLE[site], loc="left")

        near_route = nearest_camera_m(walk.points, cameras).mean()
        near_grid = nearest_camera_m(grid.points, cameras).mean()
        panel.text(
            0.02,
            0.02,
            f"route {len(walk)} standpoints, {near_route:.0f} m from a camera\n"
            f"grid {len(grid)} standpoints, {near_grid:.0f} m\n"
            f"{provenance['stations']} cameras over {provenance['road_length_m']:.0f} m of street",
            transform=panel.transAxes,
            fontsize=6,
            va="bottom",
        )
        print(
            f"{site:24s} route {len(walk):4d} standpoints at {near_route:5.1f} m mean, "
            f"grid {len(grid):4d} at {near_grid:5.1f} m"
        )

    np.atleast_1d(panels)[0].set_ylabel("north (m)")
    np.atleast_1d(panels)[0].legend(loc="upper right", frameon=False, fontsize=6, markerscale=1.5)
    figure.tight_layout()
    for suffix in (".pdf", ".png"):
        figure.savefig(OUT / f"24_walk_route{suffix}", dpi=300)
    print(f"wrote {OUT / '24_walk_route.pdf'}")


if __name__ == "__main__":
    main()
