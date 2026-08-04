"""Standpoints at the cameras, ordered along the street they were driven.

The guarantee behind the method is that a photograph taken at a point sees the
surfaces that scatter energy into that point, and BOUNCE_BUDGET.md measures how
far that guarantee travels: the first interaction lands on photographed surface
with probability 0.999 at a panorama position, 0.99 within ten metres of one,
and about 0.1 past forty. So a standpoint with no panorama near it is a
standpoint with no evidence behind it, and the fix is to stand where the cameras
stood.

Nothing here replaces the grid in :mod:`~semantic_twin.walk.grid`. Every
published run rests on that and it is left alone. :func:`panorama_walk` returns
the same :class:`~semantic_twin.walk.model.Walk` a caller already knows how to
consume, so a script can choose between the two by which builder it asks for.
"""

from __future__ import annotations

import json
import pathlib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from .. import paths
from .ground import SKY_PROBE, clearance, ground_height, ground_under_camera, sky_visibility
from .links import (
    LinkGraph,
    bridge_components,
    fragments,
    link_graph_from_screening,
    link_graph_from_sequences,
)
from .model import PANORAMA_LINKS, Walk
from .ordering import order_along_links

#: Pedestrian head height above the ground under the camera. The camera itself
#: rides at ``camera_height_m`` in the scene config, 2.5 m at every site, which
#: is a car roof and not a head.
HEAD_HEIGHT_M = 1.5


@dataclass(frozen=True)
class RouteStation:
    """One standpoint of the route, and the camera it inherits its evidence from."""

    name: str
    node: str
    camera_enu_m: np.ndarray
    ground_z_m: float
    head_enu_m: np.ndarray
    road_from_previous_m: float
    straight_from_previous_m: float
    clearance_m: float | None
    sky_fraction: float | None
    detail: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PanoramaRoute:
    """An ordered walk from A to B along the street the cameras were driven."""

    walk: Walk
    stations: tuple[RouteStation, ...]
    road_m: np.ndarray
    road_polyline: tuple[np.ndarray, ...]
    dropped: tuple[dict[str, Any], ...]
    provenance: dict[str, Any]

    def __len__(self) -> int:
        return len(self.stations)

    @property
    def road_length_m(self) -> float:
        return float(np.sum(self.road_m))

    @property
    def straight_length_m(self) -> float:
        points = self.walk.points[:, :2]
        return float(np.sum(np.linalg.norm(np.diff(points, axis=0), axis=1))) if len(points) > 1 else 0.0

    @property
    def detour_ratio(self) -> float:
        """How much longer the road is than the straight hops between stations.

        Near one where the route runs down one straight street. Well above one
        where it turns a corner, which is exactly where the straight hop would
        have cut through a building.
        """
        straight = self.straight_length_m
        return float(self.road_length_m / straight) if straight > 0.0 else 1.0

    @property
    def end_to_end_m(self) -> float:
        if len(self.walk.points) < 2:
            return 0.0
        return float(np.linalg.norm(self.walk.points[-1, :2] - self.walk.points[0, :2]))


def _admit(
    records: list[dict[str, Any]],
    graph: LinkGraph,
    *,
    centre_xy: tuple[float, float],
    radius_m: float | None,
    dropped: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Stations the link graph can place inside the crop, with a reason for each refusal."""
    kept = []
    for record in records:
        camera = np.asarray(record["camera_enu_m"], dtype=float)
        if not record.get("node"):
            dropped.append({"station": record["name"], "because": "this station carries no provider identifier"})
            continue
        if record["node"] not in graph.position:
            dropped.append({"station": record["name"], "because": "the camera is not in the link graph"})
            continue
        if radius_m is not None and float(np.linalg.norm(camera[:2] - np.asarray(centre_xy))) > radius_m:
            dropped.append({"station": record["name"], "because": f"the camera is beyond the {radius_m:.0f} m crop"})
            continue
        record["camera_enu_m"] = camera
        kept.append(record)
    if not kept:
        raise RuntimeError("no station survived, so this site cannot supply a panorama route")
    return kept


def _one_fragment(
    kept: list[dict[str, Any]],
    graph: LinkGraph,
    *,
    fragment: int,
    dropped: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[list[str]]]:
    """The stations of one connected part of the graph, and the part sizes.

    A route can only be walked along one connected part. Which part is a choice
    rather than an accident, so it is an argument, and the stations left behind
    are counted with the sizes that explain them.
    """
    groups = fragments([r["node"] for r in kept], graph)
    if fragment >= len(groups):
        raise IndexError(f"this site has {len(groups)} connected fragments, so fragment {fragment} does not exist")
    chosen = set(groups[fragment])
    for record in kept:
        if record["node"] not in chosen:
            dropped.append(
                {
                    "station": record["name"],
                    "because": (
                        f"the camera sits on a separate fragment of the link graph, "
                        f"{len(groups)} fragments of sizes {[len(g) for g in groups]}"
                    ),
                }
            )
    return [r for r in kept if r["node"] in chosen], groups


def build_panorama_route(
    geometry: Any,
    stations: Sequence[Mapping[str, Any]],
    graph: LinkGraph,
    *,
    head_height_m: float = HEAD_HEIGHT_M,
    fragment: int = 0,
    centre_xy: tuple[float, float] = (0.0, 0.0),
    radius_m: float | None = None,
    ground_datum_m: float | None = None,
    datum_tolerance_m: float = 2.5,
    probe_from: str = "camera",
    min_clearance_m: float | None = None,
    min_sky_fraction: float | None = None,
    clearance_samples: int = 96,
    seed: int = 0,
    probe_z_m: float = SKY_PROBE,
) -> PanoramaRoute:
    """Order registered cameras into a route and put a head at each of them.

    ``stations`` is a sequence of records carrying at least ``name``, ``node``
    and ``camera_enu_m``. :func:`load_admitted_stations` builds them from the
    site semantics report, which is where the admission decision lives.

    The height of a standpoint is measured, not inherited. The head goes
    ``head_height_m`` above the ground under the camera, cast for on the geometry
    in hand by :func:`~semantic_twin.walk.ground.ground_under_camera`. It is
    deliberately not derived from the registered camera altitude minus the
    scene's 2.5 m camera height, because that altitude is a fitted nuisance
    parameter and it does not hold: across the 51 admitted stations the
    registered camera sits between 0.35 m and 5.72 m above the ground under it,
    so a head placed one metre below the camera would land anywhere from 0.65 m
    underground to 4.2 m in the air. Both quantities are reported per station, so
    the disagreement is visible rather than absorbed.

    ``ground_datum_m`` is optional and changes nothing. Pass it and every
    standpoint whose ground sits further than ``datum_tolerance_m`` from the
    crop's walkable level is counted in the provenance, which is how a camera
    standing on a raised terrace announces itself.

    ``min_clearance_m`` and ``min_sky_fraction`` default to no refusal at all,
    which is the opposite of the grid builder. That is deliberate. A grid point
    has nothing behind it, so the walk has to test whether it is a place a person
    could stand. A station is a place a camera physically stood and already
    passed the skyline residual and sky conflict gates of
    ``build_site_semantics.py``, and dropping one here would silently break the
    one property this route exists to hold, that every standpoint has a
    photograph taken at it. Both numbers are measured and reported either way.
    """
    rng = np.random.default_rng(seed)
    dropped: list[dict[str, Any]] = []
    kept = _admit([dict(s) for s in stations], graph, centre_xy=centre_xy, radius_m=radius_m, dropped=dropped)
    kept, groups = _one_fragment(kept, graph, fragment=fragment, dropped=dropped)

    ordering = order_along_links([r["node"] for r in kept], graph)
    kept = [kept[i] for i in ordering["order"]]

    if probe_from not in ("camera", "sky"):
        raise ValueError("probe_from is 'camera' or 'sky'")
    xy = np.array([r["camera_enu_m"][:2] for r in kept])
    camera_z = np.array([r["camera_enu_m"][2] for r in kept])
    if probe_from == "camera":
        ground, up = ground_under_camera(geometry, xy, camera_z)
    else:
        ground, up = ground_height(geometry, xy, probe_z_m)
    if not np.isfinite(ground).all():
        missing = [kept[i]["name"] for i in np.flatnonzero(~np.isfinite(ground))]
        raise RuntimeError(f"no ground under {missing}, so the camera stands outside this crop")

    heads = np.column_stack([xy, ground + head_height_m])
    free = clearance(geometry, heads, clearance_samples, rng)
    sky = sky_visibility(geometry, heads, clearance_samples, rng)
    if min_clearance_m is not None or min_sky_fraction is not None:
        keep = np.ones(len(kept), dtype=bool)
        if min_clearance_m is not None:
            keep &= free >= min_clearance_m
        if min_sky_fraction is not None:
            keep &= sky >= min_sky_fraction
        for i in np.flatnonzero(~keep):
            dropped.append(
                {
                    "station": kept[i]["name"],
                    "because": f"clearance {free[i]:.2f} m and sky {sky[i]:.3f} failed the caller's gate",
                }
            )
        if not keep.any():
            raise RuntimeError("every station failed the clearance or sky gate")
        kept = [r for r, k in zip(kept, keep, strict=True) if k]
        xy, ground, up, camera_z = xy[keep], ground[keep], up[keep], camera_z[keep]
        heads, free, sky = heads[keep], free[keep], sky[keep]
        ordering = order_along_links([r["node"] for r in kept], graph)
        remap = ordering["order"]
        kept = [kept[i] for i in remap]
        xy, ground, up, camera_z = xy[remap], ground[remap], up[remap], camera_z[remap]
        heads, free, sky = heads[remap], free[remap], sky[remap]

    straight = np.zeros(len(kept))
    if len(kept) > 1:
        straight[1:] = np.linalg.norm(np.diff(xy, axis=0), axis=1)
    road = np.asarray(ordering["road_m"], dtype=float)
    off_datum = (
        [kept[i]["name"] for i in np.flatnonzero(np.abs(ground - ground_datum_m) > datum_tolerance_m)]
        if ground_datum_m is not None
        else []
    )

    route_stations = tuple(
        RouteStation(
            name=record["name"],
            node=record["node"],
            camera_enu_m=record["camera_enu_m"],
            ground_z_m=float(ground[i]),
            head_enu_m=heads[i],
            road_from_previous_m=float(road[i]),
            straight_from_previous_m=float(straight[i]),
            clearance_m=float(free[i]),
            sky_fraction=float(sky[i]),
            detail={
                **{k: v for k, v in record.items() if k not in ("name", "node", "camera_enu_m")},
                "camera_z_m": float(record["camera_enu_m"][2]),
                "camera_above_measured_ground_m": float(record["camera_enu_m"][2] - ground[i]),
                "ground_up_cosine": float(up[i]),
            },
        )
        for i, record in enumerate(kept)
    )

    polyline = tuple(
        np.array([graph.position[n] for n in road_nodes]) for road_nodes in ordering["roads"] if len(road_nodes) > 1
    )
    walk = Walk(
        points=heads,
        ground_z_m=ground,
        step_m=straight,
        provenance={
            "rule": (
                "one standpoint per admitted panorama, ordered by the shortest route through the "
                "provider's own link graph, head placed above the ground measured under the camera"
            ),
            "head_height_m": head_height_m,
            "stations": [r.name for r in route_stations],
            "ordering": ordering["method"],
            "road_length_m": float(np.sum(road)),
            "straight_length_m": float(np.sum(straight)),
            "road_step_m": [float(v) for v in road],
            "fragment": fragment,
            "fragment_sizes": [len(g) for g in groups],
            "dropped": dropped,
            "probe_from": probe_from,
            "ground_datum_m": ground_datum_m,
            "datum_tolerance_m": datum_tolerance_m,
            "standpoints_off_the_ground_datum": off_datum,
            "camera_above_measured_ground_m": [float(v) for v in camera_z - ground],
            "clearance_samples": clearance_samples,
            "min_clearance_m": min_clearance_m,
            "min_sky_fraction": min_sky_fraction,
            "clearance_m": [float(v) for v in free],
            "sky_fraction": [float(v) for v in sky],
            "link_graph": graph.provenance,
            "seed": seed,
        },
        kind=PANORAMA_LINKS,
    )
    return PanoramaRoute(
        walk=walk,
        stations=route_stations,
        road_m=road,
        road_polyline=polyline,
        dropped=tuple(dropped),
        provenance=dict(walk.provenance),
    )


def panorama_walk(geometry: Any, stations: Sequence[Mapping[str, Any]], graph: LinkGraph, **kwargs: Any) -> Walk:
    """The route as a plain :class:`~semantic_twin.walk.model.Walk`, for a drop-in caller."""
    return build_panorama_route(geometry, stations, graph, **kwargs).walk


# --- reading the study's own files -------------------------------------------


def load_admitted_stations(site: str, *, root: pathlib.Path | None = None, report: str | None = None) -> list[dict]:
    """The stations one site admitted, with their registered position and pano id.

    Read from ``outputs/site_semantics/<site>/walk_semantic_250m.json`` rather
    than re-derived, because that file is where the admission rule lives and a
    second copy of the rule here would be a second rule. The pano id is not in
    that report and is read from each station's own ``metadata.json``, which is
    ``panoId`` on a Street View capture and ``id`` on a Mapillary one.
    """
    base = root if root is not None else paths.root()
    name = report or "walk_semantic_250m.json"
    path = base / "outputs" / "site_semantics" / site / name
    if not path.exists():
        raise FileNotFoundError(
            f"{path} does not exist, so {site} has no admitted station set. Build it with build_site_semantics.py."
        )
    document = json.loads(path.read_text())
    out = []
    for entry in document.get("stations_admitted", ()):
        folder = pathlib.Path(entry["folder"])
        if not folder.is_absolute():
            folder = base / folder
        record: dict[str, Any] = {
            "name": entry["station"],
            "node": None,
            "camera_enu_m": np.asarray(entry["position_enu_m"], dtype=float),
            "residual_deg": entry.get("residual_deg"),
            "position_sigma_m": entry.get("position_sigma_m"),
            "folder": str(folder),
        }
        metadata = folder / "metadata.json"
        if metadata.exists():
            document_meta = json.loads(metadata.read_text())
            record["node"] = str(document_meta.get("panoId") or document_meta.get("id") or "")
            record["sequence_id"] = document_meta.get("sequence")
            record["date"] = document_meta.get("date")
        out.append(record)
    return out


def load_link_graph(
    site: str,
    *,
    root: pathlib.Path | None = None,
    bridge_m: float = 0.0,
) -> LinkGraph:
    """Whatever link structure the study holds for one site, merged.

    Street View sites come from ``outputs/city_screening/screening.json``.
    Korenmarkt's cameras are mostly Mapillary and come from the sequence
    traversal in ``outputs/walk_korenmarkt_saturation/walk_selection.json``. A
    site with both gets both, which is what lets a single Street View capture
    sit on the same route as a Mapillary walk when the two graphs touch.

    ``bridge_m`` is handed to :func:`~semantic_twin.walk.links.bridge_components`
    and applies to the merged graph, so it joins two providers as readily as two
    sequences. It is off by default because the join is this study's inference
    rather than the provider's record, and any run that turns it on says so in
    the provenance.
    """
    base = root if root is not None else paths.root()
    parts: list[LinkGraph] = []
    screening = base / "outputs" / "city_screening" / "screening.json"
    if screening.exists():
        for row in json.loads(screening.read_text())["rows"]:
            if row["key"] == site:
                parts.append(link_graph_from_screening(row))
                break
    traversal = base / "outputs" / "walk_korenmarkt_saturation" / "walk_selection.json"
    if site == "korenmarkt" and traversal.exists():
        parts.append(link_graph_from_sequences(json.loads(traversal.read_text())["candidates"]))
    if not parts:
        raise FileNotFoundError(f"no link graph on disk for {site}")
    graph = parts[0]
    for other in parts[1:]:
        graph = graph.merge(other)
    return bridge_components(graph, bridge_m)
