"""What a walk is, and how a walk says which one it is.

A walk is the set of points a pedestrian is assumed to stand at. Every exposure
number in this study is a distribution over those points, so the walk is not a
detail of the sampling. It is half the question being asked.

The study has three rules for choosing them and they disagree. The disagreement
is a real result, recorded in ``docs/2026-08-04_103942_WALK.md``, and the reason
:attr:`Walk.kind` exists is that a number alone cannot say which rule produced
it. Korenmarkt's material coverage is 0.032 by the fishnet route and 0.106 by
the fused walk. Both are true. A reader who meets one of them without the rule
beside it has no way to tell which square, let alone which walk, is being
described, and that has already caused one published figure to be misread.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

import numpy as np

#: A three metre lattice over walkable ground, filtered by ray cast gates and
#: ordered nearest neighbour. Every published number in the study used this one.
GRID = "grid"

#: One standpoint per admitted panorama, ordered by the shortest route through
#: the imagery provider's own link graph, plus points at a fixed stride along the
#: road between them.
PANORAMA_LINKS = "panorama_links"

#: One walking path from A to B off the pedestrian network, where A and B are the
#: two admitted cameras furthest apart, with standpoints at a fixed stride along
#: it.
STREET_ROUTE = "street_route"

#: Not a way of choosing standpoints but a way of choosing between two of them.
#: A builder wears it. A walk never does: a contest hands back the winner's
#: points, so the winner's kind is what produced the number.
NEAREST_OF = "nearest_of"

#: A walk built before the identity existed, or assembled by hand in a test.
UNRECORDED = "unrecorded"

#: One sentence per kind, so a report can print the rule rather than the label.
KIND_RULE = {
    GRID: "a three metre grid over walkable ground, chained nearest neighbour",
    PANORAMA_LINKS: "the panorama link chain, standpoints at the cameras and along the road between them",
    STREET_ROUTE: "a walking path from A to B across the square, standpoints at a fixed stride",
    NEAREST_OF: "whichever capture path stood nearer a camera",
    UNRECORDED: "unrecorded",
}


@dataclass(frozen=True)
class Walk:
    """Ordered observation points, with their ground and their provenance.

    ``kind`` and ``site`` are the answer to "which walk wrote this number". They
    sit on the record rather than inside ``provenance`` because ``provenance``
    is the builder's own parameter dump, it differs field by field between the
    three builders, and a consumer that wants the identity should not have to
    know which builder's dialect it is reading.

    ``step_m`` is the distance from the previous point, so its first entry is
    always zero. It is a plan distance, not a road distance: where the two differ
    the road length is in ``provenance``.
    """

    points: np.ndarray  # (P, 3) head height positions
    ground_z_m: np.ndarray  # (P,)
    step_m: np.ndarray  # (P,) plan distance from the previous point
    provenance: dict[str, Any]
    kind: str = UNRECORDED
    site: str | None = None

    def __len__(self) -> int:
        return int(self.points.shape[0])

    def identity(self) -> dict[str, Any]:
        """The walk's own name, shaped to drop into an output manifest.

        Three fields and no arrays. A manifest that carries this can be told
        apart from one built by another rule without opening the payload, which
        is the failure ``docs/2026-08-04_103942_WALK.md`` records.
        """
        return {
            "walk_kind": self.kind,
            "walk_site": self.site,
            "walk_rule": KIND_RULE.get(self.kind, self.kind),
            "standpoints": len(self),
        }

    def describe(self) -> str:
        """One line, for a log or a figure caption."""
        where = self.site or "an unnamed site"
        return f"{len(self)} standpoints at {where}: {KIND_RULE.get(self.kind, self.kind)}"


@runtime_checkable
class WalkBuilder(Protocol):
    """One rule for deciding where a pedestrian stands.

    Deliberately narrow. Everything that separates the three rules is a field on
    the implementation, and the only thing they have in common at call time is
    the geometry they stand on, so that is the only argument.

    That asymmetry is real and worth keeping visible. The grid needs no site: it
    is a sampling design and it runs against any mesh you hand it. The two
    capture routes cannot run without one, because they read that site's
    admitted stations and its link graph off disk. A protocol that took a site
    argument would force the grid to ignore it and would make the two look more
    alike than they are.
    """

    #: The rule this builder applies. The walk it returns carries the kind of
    #: whatever actually chose its points, which is the same value except for a
    #: contest like :data:`NEAREST_OF`, where the winner's kind is the honest
    #: answer to "which walk produced this number".
    kind: str

    #: The square this builder is bound to, or ``None`` where the rule is
    #: site-independent.
    site: str | None

    def build(self, geometry: Any) -> Walk:
        """Standpoints on this geometry, stamped with this builder's identity."""
        ...


def stratified_subset(walk: Walk, count: int) -> np.ndarray:
    """Evenly spaced indices along the walk, for a pilot run.

    Zero means every standpoint, matching :class:`semantic_twin.runconfig.RunConfig`.
    Evenly spaced along the ordering rather than randomly drawn, so a pilot
    covers the whole walk instead of clustering wherever the draw fell. The
    ordering is what makes that work, which is the one thing the grid's nearest
    neighbour chain is genuinely for.
    """
    if count <= 0 or count >= len(walk):
        return np.arange(len(walk))
    return np.unique(np.linspace(0, len(walk) - 1, count).round().astype(int))
