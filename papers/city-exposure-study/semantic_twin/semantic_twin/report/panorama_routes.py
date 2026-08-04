"""Census and report generation for connected panorama routes.

The exposure method puts the transmitter and receiver at the same point, with
the photograph taken there as its evidence. ``BOUNCE_BUDGET.md`` measures how
far that evidence reaches. The first surface interaction lands on photographed
geometry with probability 0.999 at a panorama position and about 0.1 past forty
metres. A route made of panorama positions is therefore the only walk with
evidence along its whole length. This report establishes whether such a route
exists.

For each site, the census records how many panoramas are on disk, registered,
and admitted. It checks whether the admitted cameras form one chain in the
provider's link graph or several fragments. It also measures route length and
the spacing between standpoints in both the admitted set and the full graph.

The detour ratio divides road length by the straight hops between registered
camera positions. These are two measurements of the same walk. The road follows
the provider's published positions, while the hops use skyline-registered
positions that differ by 1 to 6 m. A ratio slightly below one therefore means
the route is straight. It does not mean the road is shorter than the line.
"""

from __future__ import annotations

import json
import pathlib
from typing import Any

import numpy as np

from semantic_twin.sites import Site
from semantic_twin.walk.links import fragments
from semantic_twin.walk.ordering import order_along_links
from semantic_twin.walk.route import load_admitted_stations, load_link_graph


def _panorama_sets(site: str) -> tuple[tuple[str, tuple[str, ...]], ...]:
    """Return station and walk imagery sets, with a fallback for fixture sites."""
    try:
        imagery = Site.get(site).imagery
    except KeyError:
        return ((site, ("pano_", "walk_")),)
    return tuple(
        (entry.directory, (entry.station_prefix,) if entry.station_prefix else ())
        for entry in imagery
        if entry.role in {"stations", "walk"}
    )


def on_disk(site: str, root: pathlib.Path) -> tuple[int, int]:
    """Return panorama directories held by a site and how many are registered."""
    folders: list[pathlib.Path] = []
    for name, prefixes in _panorama_sets(site):
        base = root / "data" / "panoramas" / name
        if not base.exists():
            continue
        numbered = sorted(folder for prefix in prefixes for folder in base.glob(f"{prefix}*") if folder.is_dir())
        if not numbered and (base / "alignment" / "pose_aligned.json").exists():
            numbered = [base]
        folders.extend(numbered)
    registered = sum(1 for folder in folders if (folder / "alignment" / "pose_aligned.json").exists())
    return len(folders), registered


def link_spacing_m(graph: Any) -> float | None:
    """Return the median graph-link length in the provider's coordinate frame."""
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

    nodes = [station["node"] for station in stations]
    row["admitted_in_link_graph"] = sum(1 for node in nodes if node in graph.position)
    groups = fragments(nodes, graph)
    row["fragments"] = [len(group) for group in groups]
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
    place = {station["node"]: np.asarray(station["camera_enu_m"], dtype=float)[:2] for station in stations}
    walked = np.array([place[chain[index]] for index in ordering["order"]])
    straight = float(np.sum(np.linalg.norm(np.diff(walked, axis=0), axis=1))) if len(walked) > 1 else 0.0
    row["straight_length_m"] = round(straight, 1)
    row["detour_ratio"] = round(ordering["road_length_m"] / straight, 3) if straight > 0.0 else 1.0
    row["end_to_end_m"] = round(float(np.linalg.norm(walked[-1] - walked[0])), 1) if len(walked) > 1 else 0.0
    row["order"] = [
        next(station["name"] for station in stations if station["node"] == chain[index]) for index in ordering["order"]
    ]
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


def build_report(sites: tuple[str, ...] | list[str], root: pathlib.Path) -> tuple[list[dict[str, Any]], str]:
    """Build the structured route rows and their Markdown rendering."""
    rows = [site_row(site, root) for site in sites]
    return rows, table(rows)


def write_report(rows: list[dict[str, Any]], rendered: str, output_dir: pathlib.Path) -> None:
    """Write the route census in its JSON and Markdown forms."""
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "panorama_routes.json").write_text(json.dumps(rows, indent=2, default=str))
    (output_dir / "panorama_routes.md").write_text(rendered + "\n")
