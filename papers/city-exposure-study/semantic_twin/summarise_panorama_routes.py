"""How much of a connected panorama chain each site can actually supply.

The exposure method puts the transmitter and the receiver at the same point and
its evidence is the photograph taken at that point. BOUNCE_BUDGET.md measures how
far that reaches: the first surface interaction lands on photographed geometry
with probability 0.999 at a panorama position and about 0.1 past forty metres. So
a route made of panorama positions is the only walk the method has evidence for
along its whole length, and the question this script answers is whether such a
route exists.

It reports, per site, how many panoramas are on disk, how many registered, how
many the admission gate admitted, whether those admitted cameras form one chain
in the provider's link graph or several fragments, how long the chain is along
the road, and what the spacing between standpoints is. It also reports the
spacing of the underlying link graph, which is the spacing a route would have if
every panorama of the drive were on disk rather than the spread out subset the
acquisition selected.

The detour ratio divides the road length by the straight hops between the
registered camera positions, and those are two different measurements of the same
walk: the road runs through the provider's published positions and the hops run
through the skyline registered ones, which differ by 1 to 6 m. So a ratio a
fraction below one means the route is straight, not that the road is shorter than
the line.

Run from the ``semantic_twin`` directory::

    ../../../.venv/bin/python summarise_panorama_routes.py \
      --out outputs/panorama_routes
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any

import numpy as np

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from semantic_twin.walk.links import fragments  # noqa: E402
from semantic_twin.walk.ordering import order_along_links  # noqa: E402
from semantic_twin.walk.route import load_admitted_stations, load_link_graph  # noqa: E402

#: The eleven crops the study ships a support mesh for.
SITES: tuple[str, ...] = (
    "brussels_grandplace",
    "korenmarkt",
    "krakow_rynek",
    "london_trafalgar",
    "madrid_plazamayor",
    "mexico_zocalo",
    "milan_duomo",
    "newyork_timessquare",
    "prague_staromestske",
    "tokyo_hachiko",
    "toulouse_capitole",
)

#: Directories whose panoramas belong to a site under another name.
COMPANIONS: dict[str, tuple[str, ...]] = {"korenmarkt": ("korenmarkt_walk",)}


def on_disk(site: str, root: pathlib.Path) -> tuple[int, int]:
    """Panorama directories a site holds, and how many carry a registered pose."""
    folders: list[pathlib.Path] = []
    for name in (site, *COMPANIONS.get(site, ())):
        base = root / "data" / "panoramas" / name
        if not base.exists():
            continue
        numbered = sorted(f for prefix in ("pano_", "walk_") for f in base.glob(f"{prefix}*") if f.is_dir())
        if not numbered and (base / "alignment" / "pose_aligned.json").exists():
            numbered = [base]
        folders.extend(numbered)
    registered = sum(1 for f in folders if (f / "alignment" / "pose_aligned.json").exists())
    return len(folders), registered


def link_spacing_m(graph: Any) -> float | None:
    """Median length of a link in the graph, which is the drive's own frame spacing."""
    lengths = [
        float(np.linalg.norm(graph.position[a] - graph.position[b]))
        for a, links in graph.neighbours.items()
        for b in links
        if a < b
    ]
    return float(np.median(lengths)) if lengths else None


def site_row(site: str, root: pathlib.Path) -> dict[str, Any]:
    row: dict[str, Any] = {"site": site}
    row["panoramas_on_disk"], row["registered"] = on_disk(site, root)
    try:
        stations = load_admitted_stations(site, root=root)
    except FileNotFoundError as error:
        row["admitted"] = 0
        row["note"] = str(error)
        return row
    row["admitted"] = len(stations)
    try:
        graph = load_link_graph(site, root=root)
    except FileNotFoundError as error:
        row["note"] = str(error)
        return row
    row["link_graph_nodes"] = len(graph)
    row["link_graph_edges"] = graph.edge_count
    row["link_graph_median_spacing_m"] = link_spacing_m(graph)
    row["link_graph_source"] = graph.provenance.get("source") or graph.provenance.get("merged_from")

    nodes = [s["node"] for s in stations]
    row["admitted_in_link_graph"] = sum(1 for n in nodes if n in graph.position)
    groups = fragments(nodes, graph)
    row["fragments"] = [len(g) for g in groups]
    if not groups:
        row["note"] = "no admitted camera is in the link graph"
        return row

    chain = groups[0]
    row["chain_stations"] = len(chain)
    ordering = order_along_links(chain, graph)
    row["chain_road_length_m"] = round(ordering["road_length_m"], 1)
    legs = ordering["road_m"][1:]
    if legs:
        row["road_leg_median_m"] = round(float(np.median(legs)), 1)
        row["road_leg_min_m"] = round(float(np.min(legs)), 1)
        row["road_leg_max_m"] = round(float(np.max(legs)), 1)
    place = {s["node"]: np.asarray(s["camera_enu_m"], dtype=float)[:2] for s in stations}
    walked = np.array([place[chain[i]] for i in ordering["order"]])
    straight = float(np.sum(np.linalg.norm(np.diff(walked, axis=0), axis=1))) if len(walked) > 1 else 0.0
    row["straight_length_m"] = round(straight, 1)
    row["detour_ratio"] = round(ordering["road_length_m"] / straight, 3) if straight > 0.0 else 1.0
    row["end_to_end_m"] = round(float(np.linalg.norm(walked[-1] - walked[0])), 1) if len(walked) > 1 else 0.0
    row["order"] = [next(s["name"] for s in stations if s["node"] == chain[i]) for i in ordering["order"]]
    return row


def table(rows: list[dict[str, Any]]) -> str:
    header = (
        "| site | on disk | registered | admitted | fragments | chain | road m | "
        "leg median m | end to end m | detour | link spacing m |"
    )
    lines = [header, "| --- " * 11 + "|"]
    for row in rows:
        lines.append(
            "| {site} | {on_disk} | {registered} | {admitted} | {fragments} | {chain} | {road} | "
            "{leg} | {span} | {detour} | {spacing} |".format(
                site=row["site"],
                on_disk=row.get("panoramas_on_disk", 0),
                registered=row.get("registered", 0),
                admitted=row.get("admitted", 0),
                fragments=row.get("fragments", "none"),
                chain=row.get("chain_stations", 0),
                road=row.get("chain_road_length_m", "n/a"),
                leg=row.get("road_leg_median_m", "n/a"),
                span=row.get("end_to_end_m", "n/a"),
                detour=row.get("detour_ratio", "n/a"),
                spacing=(
                    round(row["link_graph_median_spacing_m"], 2)
                    if row.get("link_graph_median_spacing_m") is not None
                    else "n/a"
                ),
            )
        )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=pathlib.Path, default=SCRIPT_DIR)
    parser.add_argument("--out", type=pathlib.Path, default=None)
    parser.add_argument("--site", action="append", default=None)
    args = parser.parse_args()

    rows = [site_row(site, args.root) for site in (args.site or SITES)]
    rendered = table(rows)
    print(rendered)
    if args.out is not None:
        args.out.mkdir(parents=True, exist_ok=True)
        (args.out / "panorama_routes.json").write_text(json.dumps(rows, indent=2, default=str))
        (args.out / "panorama_routes.md").write_text(rendered + "\n")


if __name__ == "__main__":
    main()
