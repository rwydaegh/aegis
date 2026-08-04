"""The walking path between the cameras, from Google Routes.

``propagation/route.py`` builds a path out of the provider's own panorama links.
That path is dense, about ten metres between points, and it is free. It is also
the wrong path: those links are where the survey car drove, and the squares in
this study are pedestrianised, so the car went around what a person walks
across.

This asks Google Routes for one walking path instead, from A to B, where A and
B are the two cameras furthest apart. The answer comes off the pedestrian
network and it crosses the open square rather than skirting it.

What the two give at Brussels Grand-Place, eight cameras:

    panorama links   284 m, points about 10 m apart
    walking route    121 m, 8 points, segments 3.6 to 37.6 m

The link path is more than twice as long because it goes up three side streets
and comes back out of each. See ``route.street_path`` for why visiting every
camera makes the sample worse rather than better.

Two things to know before using it.

**The path is coarse.** Eight points over 121 m, and one segment is 37.6 m long.
That segment is a straight line across the open Grand-Place, which is a real
thing a pedestrian does, so the coarseness is the service telling you the square
is crossable rather than the service being lazy. Standpoints are laid along it at
a fixed stride afterwards, so what matters is that the line is walkable, not how
many points describe it.

**It costs money and it is cached.** One request per site per waypoint set,
named by the waypoints under the one cache rule in
:mod:`semantic_twin.acquire.cache`. The response lands in
``data/street_routes/`` and is reused, so a rerun is free. Delete the file to
buy it again.

The returned path is latitude and longitude in WGS84. The meshes come from
Google 3D Tiles, which is the same frame, so converting through the site anchor
puts the path in the mesh's own metres with nothing to reconcile. Height is not
returned and is not wanted: the ground under each point is probed off the mesh,
the same rule the rest of the walk uses.
"""

from __future__ import annotations

import json
import os
import pathlib
import urllib.request
from collections.abc import Sequence
from typing import Any

import numpy as np

from .. import paths
from ..scene.enu import EnuFrame
from .cache import route_key

URL = "https://routes.googleapis.com/directions/v2:computeRoutes"

#: What is asked for. ``optimizedIntermediateWaypointIndex`` is the service's own
#: answer to the ordering problem, solved on real walking distance rather than on
#: the panorama link graph, and it is kept so the two can be compared.
FIELDS = (
    "routes.distanceMeters,routes.duration,routes.polyline.encodedPolyline,routes.optimizedIntermediateWaypointIndex"
)


def decode_polyline(encoded: str) -> list[tuple[float, float]]:
    """Latitude and longitude pairs from Google's encoded polyline format."""
    points: list[tuple[float, float]] = []
    index = latitude = longitude = 0
    while index < len(encoded):
        for axis in (0, 1):
            shift = result = 0
            while True:
                byte = ord(encoded[index]) - 63
                index += 1
                result |= (byte & 0x1F) << shift
                shift += 5
                if byte < 0x20:
                    break
            delta = ~(result >> 1) if result & 1 else result >> 1
            if axis == 0:
                latitude += delta
            else:
                longitude += delta
        points.append((latitude / 1.0e5, longitude / 1.0e5))
    return points


def _waypoint(point: tuple[float, float]) -> dict[str, Any]:
    return {"location": {"latLng": {"latitude": point[0], "longitude": point[1]}}}


def fetch_walking_route(
    waypoints: Sequence[tuple[float, float]],
    *,
    api_key: str | None = None,
    optimise: bool = True,
    timeout_s: float = 30.0,
) -> dict[str, Any]:
    """One walking route through every waypoint, first to last.

    Raises rather than returning something empty. A caller that cannot reach the
    service should say so and fall back on purpose, not discover later that its
    walk quietly became a straight line.
    """
    if len(waypoints) < 2:
        raise ValueError("a route needs at least two waypoints")
    key = api_key or os.environ.get("GOOGLE_API_KEY")
    if not key:
        raise RuntimeError("GOOGLE_API_KEY is not set, so no walking route can be asked for")

    body: dict[str, Any] = {
        "origin": _waypoint(waypoints[0]),
        "destination": _waypoint(waypoints[-1]),
        "travelMode": "WALK",
        "polylineQuality": "HIGH_QUALITY",
    }
    if len(waypoints) > 2:
        body["intermediates"] = [_waypoint(p) for p in waypoints[1:-1]]
        body["optimizeWaypointOrder"] = bool(optimise)

    request = urllib.request.Request(
        URL,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "X-Goog-Api-Key": key, "X-Goog-FieldMask": FIELDS},
    )
    with urllib.request.urlopen(request, timeout=timeout_s) as response:
        answer = json.load(response)
    routes = answer.get("routes")
    if not routes:
        raise RuntimeError(f"the routing service returned no route: {json.dumps(answer)[:400]}")
    route = routes[0]
    return {
        "distance_m": float(route.get("distanceMeters", 0.0)),
        "duration": route.get("duration"),
        "waypoint_order": route.get("optimizedIntermediateWaypointIndex"),
        # Lists, not tuples, so a fresh answer and one read back out of the cache
        # compare equal. JSON has no tuple to round trip through.
        "polyline_llh": [list(p) for p in decode_polyline(route["polyline"]["encodedPolyline"])],
        "waypoints_llh": [list(p) for p in waypoints],
        "optimised": bool(optimise) and len(waypoints) > 2,
        "source": "Google Routes API, computeRoutes, WALK, HIGH_QUALITY",
    }


def cached_walking_route(
    site: str,
    waypoints: Sequence[tuple[float, float]],
    *,
    root: pathlib.Path | None = None,
    optimise: bool = True,
    refresh: bool = False,
    api_key: str | None = None,
) -> dict[str, Any]:
    """The walking route for one site, bought once and read from disk after.

    Named by the waypoints, so adding a camera buys a new route and rerunning
    the same set does not. The old answer is left in place beside the new one,
    because a route is evidence for the run that used it.
    """
    directory = (root / "data" / "street_routes") if root is not None else paths.street_routes_dir()
    path = directory / f"{site}_{route_key(waypoints, optimise)}.json"
    if path.exists() and not refresh:
        return json.loads(path.read_text())
    answer = fetch_walking_route(waypoints, api_key=api_key, optimise=optimise)
    directory.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"site": site, **answer}, indent=2) + "\n")
    return answer


def polyline_enu(route: dict[str, Any], anchor: tuple[float, float]) -> np.ndarray:
    """The route's path in the scene's own metres, east and north.

    The meshes are built from Google 3D Tiles and the path comes from Google
    Routes, so both are WGS84 and the anchor is the only thing needed to line
    them up. No fitting, no offset, nothing to tune.
    """
    frame = EnuFrame(anchor[0], anchor[1])
    return np.array([frame.to_enu(latitude, longitude)[:2] for latitude, longitude in route["polyline_llh"]])


def site_anchor(site: str, root: pathlib.Path | None = None, crop_m: int = 250) -> tuple[float, float]:
    """Where the site's local metres are measured from, read off the mesh manifest.

    Resolved through :func:`semantic_twin.paths.site_mesh`, which is the study's
    one mesh resolver. This function used to rebuild the file name here and
    reimplement the prefer-``_f64``-then-plain fallback without the version gate,
    so the study carried two resolvers that disagree: at Korenmarkt's 130 m build
    the gate refuses the version 2 file and takes the ``_f64`` rebuild, and a
    name-only rule that ever loses the suffix takes the file with a metre of
    seaming in it. An anchor read off a mesh the study will not trace is an anchor
    for nothing, and the walk built on it lands in the wrong metres.
    """
    mesh = paths.site_mesh(site, crop_m, root_dir=root)
    anchor = json.loads(paths.mesh_manifest(mesh).read_text())["anchor"]
    return float(anchor["lat_deg"]), float(anchor["lon_deg"])
