"""Next-event connections from path vertices to explicit source sites."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from ..illumination.sources import SourceSet

#: Sites closer than this to a connecting point are dropped from that
#: connection. A site is a point standing for a real antenna of finite size, and
#: `1/r**2` at a few centimetres is meaningless.
MIN_CONNECT_M = 0.5


@dataclass
class NextEventGather:
    """Connects every path vertex to a sampled base station site.

    This plugs into :meth:`SbrTracer.trace` as its ``gather``, which already hands
    over everything a connection needs: where the vertex is, the normal already
    turned to face the incoming ray, the throughput after this interaction's
    reflectance, and the Rayleigh coherent share whose complement is the diffuse
    lobe.

    Only the diffuse lobe is connected. A connection to a point source has no
    chance of being a valid mirror path, so the coherent share is left to the ray
    continuation and to image sources. That is a statement about which term this
    estimator owns, not an approximation inside it.

    It draws from its own generator, so attaching it does not move the traced
    result by a single bit.

    The accumulated quantity is the bounced part of ``chi``, per source, averaged
    over the set. Divide by the ray count and multiply by ``4 pi`` to read it as
    an integral of arriving radiance over the sphere, which :meth:`chi_bounce`
    does. The line of sight part is not accumulated here: it is exact and
    :meth:`SourceSet.direct` computes it in one call.
    """

    geometry: Any
    sources: SourceSet
    rng: np.random.Generator
    samples: int = 1
    max_order: int = 8
    epsilon_m: float = 1.0e-3
    #: How far the connection start is lifted off its own surface. Set from the
    #: sensitivity measured in tests/test_next_event.py, not by taste.
    lift_m: float = 1.0e-2
    min_connect_m: float = MIN_CONNECT_M

    total: float = 0.0
    by_order: np.ndarray = field(init=False)
    connections: int = 0
    cleared: int = 0
    rays: int = 0

    def __post_init__(self) -> None:
        self.by_order = np.zeros(self.max_order + 1, dtype=np.float64)

    def begin(self, origin: np.ndarray, count: int) -> None:
        del origin
        self.rays += int(count)

    def vertex(
        self,
        index: np.ndarray,
        position: np.ndarray,
        incoming: np.ndarray,
        normal: np.ndarray,
        throughput: np.ndarray,
        share: np.ndarray,
        order: np.ndarray,
        path_length: np.ndarray,
        face: np.ndarray | None = None,
    ) -> None:
        del index, incoming, path_length, face
        sites = self.sources.positions
        if sites.shape[0] == 0 or position.shape[0] == 0:
            return

        # The diffuse lobe of a Lambertian reflector, whose albedo is already in
        # `throughput`. Splitting it out here is what keeps the coherent share
        # from being counted twice, once by this connection and once by the
        # mirror direction the tracer continues in.
        lobe = throughput * (1.0 - share) / np.pi
        bin_order = np.minimum(np.asarray(order, dtype=np.int64), self.max_order)

        for _ in range(self.samples):
            self._connect_once(sites, position, normal, lobe, bin_order)

    def _connect_once(
        self,
        sites: np.ndarray,
        position: np.ndarray,
        normal: np.ndarray,
        lobe: np.ndarray,
        bin_order: np.ndarray,
    ) -> None:
        """One drawn site per vertex, one shadow ray, one deposit."""
        draw = self.rng.integers(0, sites.shape[0], size=position.shape[0])
        target = sites[draw]
        to_site = target - position
        distance = np.linalg.norm(to_site, axis=1)
        direction = to_site / np.maximum(distance, 1.0e-12)[:, None]
        cos_out = np.einsum("ij,ij->i", direction, normal)

        # Only the front of the surface can be reached, and a site almost on top
        # of the vertex is not a physical connection.
        worth = (cos_out > 0.0) & (distance > self.min_connect_m)
        self.connections += int(worth.sum())
        if not np.any(worth):
            return

        # The tracer leaves each vertex a hair *behind* its surface, because it
        # advances by the hit distance plus an epsilon along the incoming ray. A
        # connection fired from there can cross back through the same face and
        # read as blocked by the very surface it is standing on. So the start is
        # lifted along the normal first, which is the side the site has to be on
        # anyway for `cos_out` to be positive.
        start = position[worth] + self.lift_m * normal[worth] + self.epsilon_m * direction[worth]
        hit, travel, _, _ = self.geometry.intersect(start, direction[worth])
        clear = (~hit) | (travel >= distance[worth] - 2.0 * self.epsilon_m)
        if not np.any(clear):
            return

        weight = lobe[worth][clear] * cos_out[worth][clear] / distance[worth][clear] ** 2
        self.cleared += int(clear.sum())
        self.total += float(weight.sum())
        np.add.at(self.by_order, bin_order[worth][clear], weight)

    def chi_bounce(self) -> float:
        """The bounced part, as an integral of arriving radiance over the sphere.

        Rays leave the head uniformly, so their density on the sphere is
        ``1/(4 pi)`` and the estimator of ``integral L dOmega`` is the sum times
        ``4 pi`` over the ray count. The extra division by ``samples`` averages
        the connections made at each vertex.
        """
        if self.rays == 0:
            return 0.0
        return 4.0 * np.pi * self.total / (self.rays * self.samples)

    def chi_by_order(self) -> np.ndarray:
        """The same, kept per bounce, so the surplus can be read term by term."""
        if self.rays == 0:
            return np.zeros_like(self.by_order)
        return 4.0 * np.pi * self.by_order / (self.rays * self.samples)

    def as_dict(self) -> dict[str, Any]:
        return {
            "chi_bounce": self.chi_bounce(),
            "chi_by_order": [float(v) for v in self.chi_by_order()],
            "connections": self.connections,
            "cleared": self.cleared,
            "clear_fraction": self.cleared / max(self.connections, 1),
            "rays": self.rays,
            "samples": self.samples,
        }
