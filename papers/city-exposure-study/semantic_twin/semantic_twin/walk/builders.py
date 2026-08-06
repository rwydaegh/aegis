"""The three rules for where a pedestrian stands, and the one that picks between two.

They are in one file on purpose. The study has three answers to a single
question and they disagree, and until now the only way to see that was to notice
that two modules with unrelated names both produced something called a walk.

What the disagreement costs, measured. Mean metres from a standpoint to the
nearest camera at Korenmarkt: 44.3 on the grid, 2.8 on the panorama link route.
Material coverage by area at Korenmarkt: 0.032 by the fishnet route, 0.106 by
the fused walk, and the second of those is the number that circulates. Coverage
across squares under one rule spans 0.032 at Korenmarkt to 0.330 at Prague, so
neither the site nor the rule can be dropped from a quoted number.

What the disagreement does not cost. Run the multipath surplus at Brussels along
both capture paths and the two land 0.01 dB apart, against a seed spread of
0.006 dB, on walks that carry 56 and 26 standpoints and disagree about sky
fraction by a quarter. The surplus is a property of the square. Coverage is a
property of the walk. Quote the walk with the coverage and not with the surplus.

Every builder here is a thin wrapper over the function underneath it. That is
deliberate while the golden lock is in force: the classes add the identity and
the common interface, and they add nothing a traced number can feel.
"""

from __future__ import annotations

import dataclasses
import pathlib
from dataclasses import dataclass, field
from typing import Any

from .ground import SKY_PROBE, measure_ground_datum
from .grid import build_walk
from .model import GRID, NEAREST_OF, PANORAMA_LINKS, STREET_ROUTE, Walk
from .route import HEAD_HEIGHT_M
from .site import site_walk


@dataclass(frozen=True)
class GridWalk:
    """A three metre lattice over the walkable ground of a disc.

    Site-independent, which is why ``site`` is a label rather than a lookup key:
    this builder reads nothing off disk and will run against any geometry handed
    to it. Naming the square is still worth doing, because the resulting walk
    then says where it stood.

    ``ground_datum_m`` left as ``None`` measures the datum off the geometry at
    the same radius the walk uses, which is what both drivers do by hand today.
    Pass a number to reproduce a run whose datum was measured under an older
    rule.
    """

    site: str | None = None
    ground_datum_m: float | None = None
    radius_m: float = 90.0
    spacing_m: float = 3.0
    head_height_m: float = 1.5
    seed: int = 0
    probe_z_m: float = SKY_PROBE
    options: dict[str, Any] = field(default_factory=dict)

    kind = GRID

    def build(self, geometry: Any) -> Walk:
        datum = (
            measure_ground_datum(geometry, radius_m=self.radius_m).z_m
            if self.ground_datum_m is None
            else float(self.ground_datum_m)
        )
        walk = build_walk(
            geometry,
            ground_datum_m=datum,
            radius_m=self.radius_m,
            spacing_m=self.spacing_m,
            head_height_m=self.head_height_m,
            seed=self.seed,
            probe_z_m=self.probe_z_m,
            **self.options,
        )
        return walk if self.site is None else dataclasses.replace(walk, site=self.site)


@dataclass(frozen=True)
class _CaptureWalk:
    """Shared shape of the two walks that stand where the cameras stood.

    Both read the site's admitted stations and its link graph off disk, both put
    a head above the ground measured under a camera, and both lay extra
    standpoints at ``stride_m`` along a line. All that separates them is which
    line, so the subclasses differ by one string.
    """

    site: str
    stride_m: float = 0.0
    head_height_m: float = HEAD_HEIGHT_M
    root: pathlib.Path | None = None
    bridge_m: float = 0.0
    crop_m: int = 250
    options: dict[str, Any] = field(default_factory=dict)

    #: What ``site_walk`` calls this line.
    path = ""

    def build(self, geometry: Any) -> Walk:
        walk, _ = site_walk(
            geometry,
            self.site,
            stride_m=self.stride_m,
            head_height_m=self.head_height_m,
            root=self.root,
            bridge_m=self.bridge_m,
            path=self.path,
            crop_m=self.crop_m,
            **self.options,
        )
        return walk


@dataclass(frozen=True)
class PanoramaLinkWalk(_CaptureWalk):
    """Standpoints along the chain the imagery provider itself published.

    Free, dense at about ten metres between links, and available at six of the
    eleven squares. The other five have no chainable panorama set and can only
    be walked on the grid: Krakow and Toulouse have no panorama directory,
    London has one unregistered capture, and all fourteen Times Square poses
    fail the residual gate.

    Its weakness is that the links are where the survey vehicle drove. These
    squares are pedestrianised, so the vehicle went around what a person walks
    across, and at Brussels the chain spends 163 of its 284 m in side streets
    where there is one camera at the dead end and nothing either side of it.
    """

    kind = PANORAMA_LINKS
    path = "links"


@dataclass(frozen=True)
class StreetRouteWalk(_CaptureWalk):
    """Standpoints along one walking path from A to B across the square.

    A and B are the two admitted cameras furthest apart. The path comes off the
    pedestrian network through Google Routes, so it can cross an open square the
    vehicle had to skirt: 121 m at Brussels against the chain's 284 m.

    It fails where the pedestrian network does not enter the square. Mexico
    City's Zocalo is 240 m across with no way mapped inside it, so the service
    walks the streets around the outside and every one of the eleven cameras
    ends up 24 m or more off the walk. Choosing different endpoints cannot help,
    because it is the network that has no path there.

    Cameras further from the path than the stride are dropped as standpoints and
    counted in the provenance. Their panoramas still label geometry.
    """

    kind = STREET_ROUTE
    path = "street"


@dataclass(frozen=True)
class NearestCameraWalk(_CaptureWalk):
    """Build both capture walks and keep the one that stands nearer a camera.

    The score is the mean distance from a standpoint to the nearest admitted
    camera, which is the quantity the method rests on. The result carries the
    winner's :attr:`~semantic_twin.walk.model.Walk.kind`, not a kind of its own,
    because what produced the number is one of the other two.

    It is not the default anywhere. Measured at six squares the link chain wins
    five times, and where the walking path wins it gains 2.2 m inside a band
    BOUNCE_BUDGET.md shows is flat. One sampling rule for all eleven squares is
    easier to defend than a rule that changes site by site to buy metres that
    change no answer.
    """

    kind = NEAREST_OF
    path = "closest"
