"""Where the pedestrian stands.

Every exposure number in this study is a distribution over standpoints, so the
rule that chooses them is half the question. There are three such rules and they
disagree:

* :class:`~semantic_twin.walk.builders.GridWalk` lays a three metre lattice over
  the walkable ground of a disc. Every published number used it.
* :class:`~semantic_twin.walk.builders.PanoramaLinkWalk` stands at the cameras,
  ordered along the link chain the imagery provider published.
* :class:`~semantic_twin.walk.builders.StreetRouteWalk` stands along one walking
  path across the square, from the routing service.

:class:`~semantic_twin.walk.builders.NearestCameraWalk` is not a fourth rule. It
builds the two capture walks and keeps whichever stands nearer a camera.

Every walk carries :attr:`~semantic_twin.walk.model.Walk.kind` and
:attr:`~semantic_twin.walk.model.Walk.site`, because a coverage number means
nothing without both. Korenmarkt reads 0.032 by one route and 0.106 by another,
and Prague reads 0.330 under the rule that gives Korenmarkt 0.032.
:mod:`semantic_twin.walk.builders` carries the measurements behind that.

The package is laid out by what a reader is looking for rather than by which
module a function used to live in:

    model       the record, the protocol, the kind vocabulary
    ground      the ground datum, the two downward probes, the two gates
    grid        the lattice
    links       the provider's link graph
    ordering    the shortest route through that graph
    route       standpoints at the cameras, and the files that name them
    site        the runner entry point, the stride, the walking path
    builders    the three rules side by side
"""

from __future__ import annotations

from .builders import GridWalk, NearestCameraWalk, PanoramaLinkWalk, StreetRouteWalk
from .grid import build_walk
from .ground import (
    SKY_PROBE,
    GroundDatum,
    clearance,
    ground_datum,
    ground_height,
    ground_under_camera,
    measure_ground_datum,
    sky_visibility,
)
from .links import LinkGraph
from .model import (
    GRID,
    KIND_RULE,
    NEAREST_OF,
    PANORAMA_LINKS,
    STREET_ROUTE,
    UNRECORDED,
    Walk,
    WalkBuilder,
    stratified_subset,
)
from .orientation import (
    BODY_YAW_CONVENTION,
    BODY_YAW_FALLBACK,
    body_yaw_array_hash,
    body_yaw_hash,
    orient_route_walk,
    route_body_yaw_deg,
    route_order_hash,
    validate_body_yaw_alignment,
)
from .route import PanoramaRoute, RouteStation, build_panorama_route, panorama_walk
from .site import site_walk

__all__ = [
    "GRID",
    "KIND_RULE",
    "NEAREST_OF",
    "PANORAMA_LINKS",
    "SKY_PROBE",
    "STREET_ROUTE",
    "UNRECORDED",
    "GridWalk",
    "GroundDatum",
    "LinkGraph",
    "NearestCameraWalk",
    "PanoramaLinkWalk",
    "PanoramaRoute",
    "RouteStation",
    "StreetRouteWalk",
    "Walk",
    "WalkBuilder",
    "BODY_YAW_CONVENTION",
    "BODY_YAW_FALLBACK",
    "body_yaw_array_hash",
    "body_yaw_hash",
    "build_panorama_route",
    "build_walk",
    "clearance",
    "ground_datum",
    "ground_height",
    "ground_under_camera",
    "measure_ground_datum",
    "panorama_walk",
    "orient_route_walk",
    "route_body_yaw_deg",
    "route_order_hash",
    "site_walk",
    "sky_visibility",
    "stratified_subset",
    "validate_body_yaw_alignment",
]
