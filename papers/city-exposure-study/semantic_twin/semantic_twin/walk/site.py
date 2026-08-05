"""The walk for one named square, and the choice of what runs between the cameras.

Two things happen here. A route gives one standpoint per camera, which is honest
and thin: five at Korenmarkt against 799 on the grid. So :func:`densify` lays
extra standpoints along the line between them at a fixed stride, and the line is
either the provider's own link chain or a walking path off the pedestrian
network. :func:`site_walk` is what a runner calls.

Which line to use was measured rather than argued. At six squares, mean metres
from a standpoint to the nearest camera at a 6 m stride and the 250 m crop:

    Ghent Korenmarkt        links 2.85   street 2.89
    Brussels Grand-Place    links 8.90   street 6.67
    Madrid Plaza Mayor      links 9.50   street 12.12
    Mexico City Zocalo      links 8.26   street 39.15
    Prague Old Town         links 6.45   street 7.35
    Tokyo Hachiko           links 13.47  street 20.30

The walking path wins once. It is the default nowhere, because BOUNCE_BUDGET.md
puts the first interaction on photographed surface with probability 0.987 to
0.999 anywhere inside ten metres of a camera, so both columns sit in the same
band at Brussels and the difference buys nothing the physics can feel. Run the
surplus both ways there and the two agree to 0.01 dB against a seed spread of
0.006 dB.
"""

from __future__ import annotations

import dataclasses
import pathlib
from collections.abc import Sequence
from typing import Any

import numpy as np

from .. import paths
from ..acquire.routes import cached_walking_route, polyline_enu, site_anchor
from ..scene.enu import EnuFrame
from .ground import ground_under_camera
from .model import CAMERA_REGISTERED, PANORAMA_LINKS, STREET_ROUTE, STRIDE_INTERPOLATED, Walk
from .route import HEAD_HEIGHT_M, PanoramaRoute, build_panorama_route, load_admitted_stations, load_link_graph

#: What ``path`` may be, and which walk kind each one produces. ``closest``
#: produces whichever of the other two stands nearer a camera, so its result
#: carries the winner's kind and the contest lands in the provenance.
PATH_KIND = {"links": PANORAMA_LINKS, "street": STREET_ROUTE}


def densify(polylines: Sequence[np.ndarray], stride_m: float) -> np.ndarray:
    """Points every ``stride_m`` along a chain of road legs, ends included.

    A route puts one standpoint at each camera, which is honest and thin. But a
    pedestrian is not only where the camera stopped, they are anywhere along the
    street the camera drove, and the leg polylines are that street. Walking them
    at a fixed stride keeps every standpoint on the captured road while giving
    the sample back its density.

    Returns an empty (0, 2) array when there is no road, which happens at a site
    with a single admitted station and is not an error.
    """
    chain = [p for p in polylines if p is not None and len(p) >= 2]
    if not chain:
        return np.zeros((0, 2))
    line = np.concatenate([np.asarray(p, dtype=float)[:, :2] for p in chain], axis=0)
    keep = np.concatenate([[True], np.linalg.norm(np.diff(line, axis=0), axis=1) > 1.0e-9])
    line = line[keep]
    if line.shape[0] < 2:
        return line
    step = np.linalg.norm(np.diff(line, axis=0), axis=1)
    travelled = np.concatenate([[0.0], np.cumsum(step)])
    wanted = np.arange(0.0, travelled[-1] + 0.5 * stride_m, stride_m)
    wanted = wanted[wanted <= travelled[-1]]
    return np.column_stack([np.interp(wanted, travelled, line[:, axis]) for axis in (0, 1)])


def span_endpoints(cameras: np.ndarray) -> tuple[int, int]:
    """The two cameras furthest apart in plan, which is the walk's A and B.

    The widest pair is the diameter of the capture, so the line between them is
    the longest walk the panoramas can speak for. At Brussels Grand-Place it is
    88 m straight, the town hall corner to the east side, and the walking path
    between them is the one a visitor actually takes across the square.
    """
    gap = np.linalg.norm(cameras[:, None, :2] - cameras[None, :, :2], axis=2)
    return tuple(int(v) for v in np.unravel_index(int(np.argmax(gap)), gap.shape))  # type: ignore[return-value]


def gap_to_path(points: np.ndarray, line: np.ndarray) -> np.ndarray:
    """Shortest plan distance from each point to a polyline."""
    start, end = line[:-1, :2], line[1:, :2]
    segment = end - start
    length2 = np.einsum("ij,ij->i", segment, segment)
    length2[length2 == 0.0] = 1.0
    along = np.clip(np.einsum("pij,ij->pi", points[:, None, :2] - start[None], segment) / length2, 0.0, 1.0)
    foot = start[None] + along[..., None] * segment[None]
    return np.linalg.norm(points[:, None, :2] - foot, axis=2).min(axis=1)


def street_path(
    site: str,
    route: PanoramaRoute,
    *,
    root: pathlib.Path | None = None,
    crop_m: int = 250,
    endpoints: str = "span",
) -> tuple[tuple[np.ndarray, ...], dict[str, Any]]:
    """The walking path across the square, from the routing service.

    ``endpoints="span"`` asks for one walk from A to B, where A and B are the two
    cameras furthest apart. Nothing in between is a waypoint. This is what a
    person walking across the square does, and it is the default.

    ``endpoints="all"`` makes every camera a waypoint and lets the service
    reorder them. That sounds better and is worse. Three of the eight Brussels
    cameras sit up side streets, so a path that visits all of them walks in and
    walks back out three times: 267 m against 121 m, and the extra 146 m is spent
    in alleys where there is one camera at the dead end and nothing either side
    of it. Measured over the standpoints laid at a 6 m stride, the mean distance
    from a standpoint to the nearest camera is 8.3 m for the A to B walk and
    10.2 m for the full tour. Visiting every camera makes the sample worse by the
    one measure that matters.

    The three cameras the A to B walk passes 20 to 38 m from are not discarded.
    Their panoramas still label the geometry through the fishnet. They just no
    longer bend the walk into a shape no pedestrian would take.

    Returned as a one element tuple so it drops straight into :func:`densify`,
    which takes a chain of legs. The walking path is one continuous line and has
    no legs to speak of.
    """
    base = root or paths.root()
    anchor = site_anchor(site, base, crop_m=crop_m)
    frame = EnuFrame(anchor[0], anchor[1])
    cameras = np.array([station.camera_enu_m for station in route.stations], dtype=float)
    if endpoints == "span":
        chosen = list(span_endpoints(cameras))
    elif endpoints == "all":
        chosen = list(range(len(cameras)))
    else:
        raise ValueError(f"endpoints is 'span' or 'all', not {endpoints!r}")

    waypoints = [tuple(frame.to_llh(cameras[k])[:2]) for k in chosen]
    answer = cached_walking_route(site, waypoints, root=base, optimise=len(waypoints) > 2)
    line = polyline_enu(answer, anchor)
    step = np.linalg.norm(np.diff(line, axis=0), axis=1) if line.shape[0] > 1 else np.zeros(0)
    off = gap_to_path(cameras, line) if line.shape[0] > 1 else np.full(len(cameras), np.inf)
    record = {
        "source": answer["source"],
        "endpoints": endpoints,
        "waypoints": len(waypoints),
        "endpoint_stations": chosen if endpoints == "span" else None,
        "endpoint_separation_m": float(np.linalg.norm(cameras[chosen[0], :2] - cameras[chosen[-1], :2])),
        "distance_m": answer["distance_m"],
        "points": int(line.shape[0]),
        "waypoint_order": answer.get("waypoint_order"),
        "longest_segment_m": float(step.max()) if step.size else 0.0,
        "measured_length_m": float(step.sum()),
        "link_graph_length_m": float(np.sum(route.road_length_m)),
        # How far the cameras sit from the line that was walked. A camera well
        # off the path still labels geometry, but it no longer says where a head
        # stood, and this is where that shows up.
        "cameras_off_path_median_m": float(np.median(off)),
        "cameras_off_path_max_m": float(off.max()),
        "cameras_within_10m": int((off < 10.0).sum()),
        "anchor_lat_lon": list(anchor),
        # The path itself, in scene metres. It is small, it is what the walk
        # actually used, and keeping it means a figure or a reviewer can see the
        # line without another request.
        "polyline_enu": [[round(float(x), 3), round(float(y), 3)] for x, y in line],
    }
    return (line,), record


def _nearest_of(
    geometry: Any,
    site: str,
    candidates: Sequence[str],
    root: pathlib.Path | None,
    kwargs: dict[str, Any],
) -> tuple[Walk, dict[str, Any]]:
    """Build each candidate path and keep the one that stands nearer a camera.

    The score is the mean distance from a standpoint to the nearest admitted
    camera, because that is the quantity the whole method rests on. The loser is
    written into the record rather than thrown away, so a run says what it did
    not pick as well as what it did.
    """
    best: tuple[Walk, dict[str, Any]] | None = None
    best_gap = np.inf
    tried: dict[str, float] = {}
    for candidate in candidates:
        walk, record = site_walk(geometry, site, root=root, path=candidate, **kwargs)
        cameras = np.array([s["camera_enu_m"] for s in load_admitted_stations(site, root=root)], dtype=float)
        gap = float(np.linalg.norm(walk.points[:, None, :2] - cameras[None, :, :2], axis=2).min(axis=1).mean())
        tried[candidate] = round(gap, 2)
        if gap < best_gap:
            best, best_gap = (walk, record), gap
    walk, record = best  # type: ignore[misc]
    record["path_chosen_by"] = "mean metres from a standpoint to the nearest camera"
    record["path_candidates_m"] = tried
    return walk, record


def _keep_near_the_street(
    walk: Walk,
    provenance: dict[str, Any],
    street: dict[str, Any],
    *,
    site: str,
    stride_m: float,
) -> Walk:
    """Drop the cameras the routed walking path does not pass.

    A camera further from the path than the stride is not on the walk, so it is
    not a standpoint. It still labels geometry through its panorama.
    """
    provenance["street_route"] = street
    line = np.asarray(street["polyline_enu"], dtype=float)
    within = max(stride_m, 5.0)
    on = gap_to_path(walk.points, line) <= within
    provenance["stations_on_path"] = int(on.sum())
    provenance["stations_off_path"] = int((~on).sum())
    if not on.any():
        # Every camera is off the routed path. This is the pedestrian network
        # not entering the square: Mexico City's Zocalo is 240 m across with no
        # way mapped inside it, so Routes walks the streets around it and the
        # nearest camera to that walk is 24 m away. The walk is still real, it
        # just carries no station, and the caller should hear it.
        provenance["note"] = (
            f"no camera lies within {within:.0f} m of the walking path, "
            f"nearest is {gap_to_path(walk.points, line).min():.0f} m off"
        )
    point_kind = walk.provenance.get("point_kind")
    kept_kind = [kind for kind, keep in zip(point_kind, on, strict=True) if keep] if point_kind is not None else None
    walk_provenance = {**walk.provenance, "kept_within_m": within}
    if kept_kind is not None:
        walk_provenance["point_kind"] = kept_kind
    return Walk(
        points=walk.points[on],
        ground_z_m=walk.ground_z_m[on],
        step_m=walk.step_m[on],
        provenance=walk_provenance,
        kind=STREET_ROUTE,
        site=site,
    )


def _stride_along(
    geometry: Any,
    walk: Walk,
    heights: np.ndarray,
    legs: Sequence[np.ndarray],
    *,
    stride_m: float,
    head_height_m: float,
) -> tuple[np.ndarray, np.ndarray, list[str]] | None:
    """Extra standpoints along the road, or ``None`` when there is no road.

    The camera height is interpolated along the road so the downward probe
    starts under a camera exactly as it does at a station, which is what keeps a
    head off the arcade roofs a probe from the sky lands on.
    """
    extra = densify(legs, stride_m)
    if extra.shape[0] == 0:
        return None
    at = heights[:, :2]
    order = np.argsort(np.linalg.norm(at - at[0], axis=1))
    camera_z = np.interp(
        np.linalg.norm(extra - at[0], axis=1),
        np.linalg.norm(at[order] - at[0], axis=1),
        heights[order, 2],
    )
    z, _ = ground_under_camera(geometry, extra, camera_z)
    good = np.isfinite(z)
    points = np.concatenate([walk.points, np.column_stack([extra[good], z[good] + head_height_m])], axis=0)
    ground = np.concatenate([walk.ground_z_m, z[good]])
    point_kind = [CAMERA_REGISTERED] * len(walk) + [STRIDE_INTERPOLATED] * int(good.sum())
    seen = np.round(points[:, :2], 2)
    _, unique = np.unique(seen, axis=0, return_index=True)
    unique = np.sort(unique)
    points, ground = points[unique], ground[unique]
    point_kind = [point_kind[i] for i in unique]
    order = _order_along_path(points, legs)
    return points[order], ground[order], [point_kind[i] for i in order]


def _order_along_path(points: np.ndarray, polylines: Sequence[np.ndarray]) -> np.ndarray:
    """Order an existing point set by distance travelled along its road."""
    chain = [np.asarray(polyline, dtype=float)[:, :2] for polyline in polylines if len(polyline) >= 2]
    if not chain or len(points) < 2:
        return np.arange(len(points))
    line = np.concatenate(chain, axis=0)
    keep = np.concatenate([[True], np.linalg.norm(np.diff(line, axis=0), axis=1) > 1.0e-9])
    line = line[keep]
    if line.shape[0] < 2:
        return np.arange(len(points))

    start = line[:-1]
    segment = line[1:] - start
    length = np.linalg.norm(segment, axis=1)
    along_segment = np.clip(
        np.einsum("pij,ij->pi", points[:, None, :2] - start[None], segment) / np.square(length),
        0.0,
        1.0,
    )
    foot = start[None] + along_segment[..., None] * segment[None]
    nearest = np.argmin(np.linalg.norm(points[:, None, :2] - foot, axis=2), axis=1)
    travelled = np.concatenate([[0.0], np.cumsum(length)])
    coordinate = travelled[nearest] + along_segment[np.arange(len(points)), nearest] * length[nearest]
    return np.argsort(coordinate, kind="stable")


def site_walk(
    geometry: Any,
    site: str,
    *,
    stride_m: float = 0.0,
    head_height_m: float = HEAD_HEIGHT_M,
    root: pathlib.Path | None = None,
    bridge_m: float = 0.0,
    path: str = "links",
    endpoints: str = "span",
    crop_m: int = 250,
    **kwargs: Any,
) -> tuple[Walk, dict[str, Any]]:
    """The walk for one site, taken from its capture rather than from a grid.

    This is the entry point a runner should call. The grid builder scatters heads
    over a disc on a three metre lattice and joins them nearest neighbour first,
    which is a flood fill of the open ground and not a route anyone took. This
    stands where the cameras stood, in the order the street connects them.

    ``stride_m`` above zero adds standpoints along the road between cameras, so
    the sample is dense without leaving the captured street.

    ``path`` chooses what "between the cameras" means.

    ``links`` walks the provider's own panorama links. Dense, about ten metres
    between points, and free, but those links are where the survey car drove and
    these squares are pedestrianised, so the car went around what a person walks
    across.

    ``street`` asks Google Routes for one walking path from A to B across the
    square. It comes off the pedestrian network, so it may cross an open square
    the car had to go round. At Brussels it is 121 m against the links' 284 m. It
    costs one request per site and the answer is cached on disk.

    ``closest`` builds both and keeps whichever stands nearer a camera. The table
    in this module's own docstring is why it is not the default: neither path
    wins everywhere and the metres it gains change no answer.

    Returns the walk and a provenance record. It raises rather than quietly
    falling back to the grid: a run that silently changed what a standpoint means
    is how a stale walk survives, and the caller should decide.
    """
    if path == "closest":
        return _nearest_of(
            geometry,
            site,
            ("links", "street"),
            root,
            {
                "stride_m": stride_m,
                "head_height_m": head_height_m,
                "bridge_m": bridge_m,
                "endpoints": endpoints,
                "crop_m": crop_m,
                **kwargs,
            },
        )
    stations = load_admitted_stations(site, root=root)
    graph = load_link_graph(site, root=root, bridge_m=bridge_m)
    route = build_panorama_route(geometry, stations, graph, head_height_m=head_height_m, **kwargs)
    walk = dataclasses.replace(route.walk, site=site)
    provenance: dict[str, Any] = {
        **route.provenance,
        "builder": "panorama route",
        "path": path,
        "stations": len(route),
        "road_length_m": float(np.sum(route.road_length_m)),
        "stride_m": stride_m,
    }
    # Camera heights, kept before any filtering. The stride probes the ground
    # from just under an interpolated camera, and dropping a station off the walk
    # must not also drop the height it measured.
    heights = walk.points.copy()

    if path == "street":
        legs, street = street_path(site, route, root=root, crop_m=crop_m, endpoints=endpoints)
        walk = _keep_near_the_street(walk, provenance, street, site=site, stride_m=stride_m)
    else:
        legs = route.road_polyline
    provenance["point_kind"] = list(walk.provenance.get("point_kind", [CAMERA_REGISTERED] * len(walk)))
    walk = dataclasses.replace(walk, provenance=provenance)
    if stride_m <= 0.0:
        provenance["standpoints"] = len(walk)
        return walk, provenance

    strode = _stride_along(geometry, walk, heights, legs, stride_m=stride_m, head_height_m=head_height_m)
    if strode is None:
        provenance["standpoints"] = len(walk)
        provenance["note"] = "no road between stations, so the stride added nothing"
        return walk, provenance

    points, ground, point_kind = strode
    step = np.concatenate([[0.0], np.linalg.norm(np.diff(points[:, :2], axis=0), axis=1)])
    provenance["standpoints"] = int(points.shape[0])
    provenance["added_along_the_road"] = int(points.shape[0] - len(walk))
    provenance["standpoint_ordering"] = "increasing distance travelled along the selected path"
    provenance["point_kind"] = point_kind
    return (
        Walk(
            points=points,
            ground_z_m=ground,
            step_m=step,
            provenance=provenance,
            kind=PATH_KIND[path],
            site=site,
        ),
        provenance,
    )
