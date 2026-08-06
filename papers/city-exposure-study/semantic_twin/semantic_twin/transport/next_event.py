"""Next-event connections from path vertices to explicit source sites."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, ClassVar

import numpy as np

from ..illumination.model import AngularIllumination, PlacedIllumination
from ..illumination.sources import direct_from_sites, normalized_source_weights, visible
from ..illumination.sphere import nearest_cell
from .model import Surplus, require_credit
from .tracer import SbrTracer

#: Sites closer than this to a connecting point are dropped from that
#: connection. A site is a point standing for a real antenna of finite size, and
#: `1/r**2` at a few centimetres is meaningless.
MIN_CONNECT_M = 0.5


def _direct_field_masses(
    geometry: Any,
    origin: np.ndarray,
    sources: PlacedIllumination,
    local_grid: np.ndarray,
    *,
    epsilon_m: float = 1.0e-3,
) -> tuple[np.ndarray, float]:
    """Exact direct source masses binned by receiver-local direction.

    A mass is the weighted ``1/r**2`` contribution of one visible source. The
    source set is finite, so there is no sampling or angular-density estimate in
    this branch. ``u0`` points from the receiver to the source and is binned
    directly because it is the reciprocal direction consumed by BodyCoupler.
    """
    sites = np.asarray(sources.sites(), dtype=np.float64)
    masses = np.zeros(local_grid.shape[0], dtype=np.float64)
    if sites.shape[0] == 0:
        return masses, 0.0
    probabilities = normalized_source_weights(sources)
    receiver = np.asarray(origin, dtype=np.float64)
    clear, distance = visible(
        geometry,
        np.broadcast_to(receiver, sites.shape),
        sites,
        epsilon_m=epsilon_m,
    )
    direction = (sites - receiver[None, :]) / np.maximum(distance, 1.0e-12)[:, None]
    bins = nearest_cell(direction, local_grid)
    contribution = probabilities * np.where(clear, 1.0 / np.square(distance), 0.0)
    np.add.at(masses, bins, contribution)
    return masses, float(np.sum(probabilities[clear], dtype=np.float64))


@dataclass(frozen=True)
class NextEventField:
    """Diagnostic local angular masses from a facade-tip next-event trace.

    ``local_grid`` is the reciprocal ray's departure direction ``u0``. The
    physical body arrival direction is ``k_hat = -u0``. The two mass arrays carry
    the transfer contributions before division by solid angle. Their densities
    retain that transfer scale, so a caller must provide the desired reference
    transfer before using them as a normalized BodyCoupler spectrum.

    This field is deliberately diagnostic. The next-event gather owns only the
    diffuse lobe, so purely specular connections, including specular suffixes of
    a mixed path, are absent and explicitly marked below.
    """

    local_grid: np.ndarray
    solid_angle: float
    direct_mass: np.ndarray
    bounced_mass: np.ndarray
    diagnostic: bool = True
    includes_specular: bool = False
    missing_specular: bool = True

    def __post_init__(self) -> None:
        grid = np.asarray(self.local_grid, dtype=np.float64)
        direct = np.asarray(self.direct_mass, dtype=np.float64)
        bounced = np.asarray(self.bounced_mass, dtype=np.float64)
        if grid.ndim != 2 or grid.shape[1] != 3:
            raise ValueError(f"local_grid must have shape (cells, 3), got {grid.shape}")
        if direct.shape != (grid.shape[0],) or bounced.shape != (grid.shape[0],):
            raise ValueError("direct_mass and bounced_mass must match local_grid")
        if not np.all(np.isfinite(grid)) or not np.all(np.isfinite(direct)) or not np.all(np.isfinite(bounced)):
            raise ValueError("field arrays must be finite")
        if np.any(direct < 0.0) or np.any(bounced < 0.0):
            raise ValueError("field masses must be nonnegative")
        if not np.isfinite(self.solid_angle) or self.solid_angle <= 0.0:
            raise ValueError("solid_angle must be positive and finite")
        object.__setattr__(self, "local_grid", grid)
        object.__setattr__(self, "direct_mass", direct)
        object.__setattr__(self, "bounced_mass", bounced)

    @property
    def arrival_directions(self) -> np.ndarray:
        """Physical local arrival directions ``k_hat`` for each bin."""
        return -self.local_grid

    @property
    def k_hat(self) -> np.ndarray:
        """Alias for :attr:`arrival_directions` used in the reciprocity table."""
        return self.arrival_directions

    @property
    def direct_density(self) -> np.ndarray:
        """Direct transfer density in the reciprocal local-direction bins."""
        return self.direct_mass / self.solid_angle

    @property
    def bounced_density(self) -> np.ndarray:
        """Diffuse bounced transfer density in the reciprocal local bins."""
        return self.bounced_mass / self.solid_angle

    def normalized_density(self, component: str, reference_transfer: float) -> np.ndarray:
        """Convert one component to a BodyCoupler-style density.

        ``reference_transfer`` is the caller's positive free-space transfer
        factor. It is intentionally not inferred from this diagnostic field.
        """
        if not np.isfinite(reference_transfer) or reference_transfer <= 0.0:
            raise ValueError("reference_transfer must be positive and finite")
        if component == "direct":
            density = self.direct_density
        elif component == "bounced":
            density = self.bounced_density
        elif component == "total":
            density = self.direct_density + self.bounced_density
        else:
            raise ValueError("component must be 'direct', 'bounced', or 'total'")
        return density / float(reference_transfer)

    @property
    def direct(self) -> float:
        return float(np.sum(self.direct_mass, dtype=np.float64))

    @property
    def bounced(self) -> float:
        return float(np.sum(self.bounced_mass, dtype=np.float64))

    @property
    def total(self) -> float:
        return self.direct + self.bounced

    def as_dict(self) -> dict[str, Any]:
        return {
            "diagnostic": self.diagnostic,
            "includes_specular": self.includes_specular,
            "missing_specular": self.missing_specular,
            "direction_convention": "local_grid=u0=-k_hat",
            "solid_angle": float(self.solid_angle),
            "direct_mass": self.direct_mass.tolist(),
            "bounced_mass": self.bounced_mass.tolist(),
            "direct": self.direct,
            "bounced": self.bounced,
            "total": self.total,
        }


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
    does. The line of sight part is not accumulated here. The estimator computes
    it exactly from :meth:`PlacedIllumination.sites` in one call.
    """

    geometry: Any
    sources: PlacedIllumination
    rng: np.random.Generator
    samples: int = 1
    max_order: int = 8
    epsilon_m: float = 1.0e-3
    #: How far the connection start is lifted off its own surface. Set from the
    #: sensitivity measured in tests/test_next_event.py, not by taste.
    lift_m: float = 1.0e-2
    min_connect_m: float = MIN_CONNECT_M
    #: Optional reciprocal launch grid. Supplying it enables the diagnostic
    #: bounced angular field while leaving the scalar gather path untouched.
    field_grid: np.ndarray | None = None

    total: float = 0.0
    by_order: np.ndarray = field(init=False)
    bounced_mass: np.ndarray | None = field(init=False, default=None)
    connections: int = 0
    cleared: int = 0
    rays: int = 0
    _launch_cells: np.ndarray | None = field(init=False, default=None, repr=False)
    _source_probabilities: np.ndarray = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self.by_order = np.zeros(self.max_order + 1, dtype=np.float64)
        self._source_probabilities = normalized_source_weights(self.sources)
        if self.field_grid is not None:
            grid = np.asarray(self.field_grid, dtype=np.float64)
            if grid.ndim != 2 or grid.shape[1] != 3 or grid.shape[0] == 0:
                raise ValueError("field_grid must have shape (positive cells, 3)")
            if not np.all(np.isfinite(grid)):
                raise ValueError("field_grid must be finite")
            self.field_grid = grid
            self.bounced_mass = np.zeros(grid.shape[0], dtype=np.float64)

    def begin(self, origin: np.ndarray, count: int) -> None:
        del origin
        self.rays += int(count)

    def set_launch_cells(self, cells: np.ndarray) -> None:
        """Receive the original local launch cell for this trace batch.

        The tracer keeps rays in their original batch-index order, so these
        cells remain valid after any number of surface interactions. This
        optional hook avoids widening the long-standing gather vertex contract.
        """
        self._launch_cells = np.asarray(cells, dtype=np.int64)

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
        del incoming, path_length, face
        sites = self.sources.sites()
        if sites.shape[0] == 0 or position.shape[0] == 0:
            return

        # The diffuse lobe of a Lambertian reflector, whose albedo is already in
        # `throughput`. Splitting it out here is what keeps the coherent share
        # from being counted twice, once by this connection and once by the
        # mirror direction the tracer continues in.
        lobe = throughput * (1.0 - share) / np.pi
        bin_order = np.minimum(np.asarray(order, dtype=np.int64), self.max_order)

        for _ in range(self.samples):
            self._connect_once(sites, index, position, normal, lobe, bin_order)

    def _connect_once(
        self,
        sites: np.ndarray,
        index: np.ndarray,
        position: np.ndarray,
        normal: np.ndarray,
        lobe: np.ndarray,
        bin_order: np.ndarray,
    ) -> None:
        """One drawn site per vertex, one shadow ray, one deposit."""
        if np.all(self._source_probabilities == self._source_probabilities[0]):
            # Keep the historical equal-source random stream exactly unchanged.
            draw = self.rng.integers(0, sites.shape[0], size=position.shape[0])
        else:
            draw = self.rng.choice(sites.shape[0], size=position.shape[0], p=self._source_probabilities)
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
        if self.bounced_mass is not None:
            if self._launch_cells is None:
                raise RuntimeError("field-enabled next-event gather did not receive launch cells")
            np.add.at(self.bounced_mass, self._launch_cells[index[worth][clear]], weight)

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

    def field(self, direct_mass: np.ndarray | None = None) -> NextEventField:
        """Reduce this gather to a diagnostic field.

        ``direct_mass`` is supplied by the estimator's exact source-side
        visibility pass. The bounced deposits are averaged with the same
        ``4 pi / (rays * samples)`` factor as :meth:`chi_bounce`.
        """
        if self.field_grid is None or self.bounced_mass is None:
            raise RuntimeError("field output was not enabled for this gather")
        if self.rays == 0:
            bounced = np.zeros_like(self.bounced_mass)
        else:
            bounced = 4.0 * np.pi * self.bounced_mass / (self.rays * self.samples)
        direct = np.zeros_like(bounced) if direct_mass is None else np.asarray(direct_mass, dtype=np.float64)
        if direct.shape != bounced.shape:
            raise ValueError("direct_mass must match the field grid")
        return NextEventField(
            local_grid=self.field_grid,
            solid_angle=4.0 * np.pi / self.field_grid.shape[0],
            direct_mass=direct,
            bounced_mass=bounced,
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "chi_bounce": self.chi_bounce(),
            "chi_by_order": [float(v) for v in self.chi_by_order()],
            "connections": self.connections,
            "cleared": self.cleared,
            "clear_fraction": self.cleared / max(self.connections, 1),
            "rays": self.rays,
            "samples": self.samples,
            "field_enabled": self.bounced_mass is not None,
        }


@dataclass(frozen=True)
class NextEventEstimator:
    """Score one explicit source set from one standpoint.

    The gather draws from ``seed + 1000`` while the trace draws from ``seed``.
    That split is the convention used by every published next-event run. The
    direct term still accepts sources closer than :data:`MIN_CONNECT_M`, while
    the bounced term refuses them. That known mismatch is preserved here until
    it can be changed and measured in its own physics commit.

    ``diagnostic_models`` are angular laws traced alongside the connection.
    They do not feed the next-event answer. They preserve the live escape
    comparison written by the next-event study.
    """

    tracer: SbrTracer
    geometry: Any
    sources: PlacedIllumination
    samples: int = 1
    max_order: int | None = None
    connection_lift_m: float = 1.0e-2
    diagnostic_models: Mapping[str, AngularIllumination] = field(default_factory=dict)

    name: ClassVar[str] = "next_event"
    gather_seed_offset: ClassVar[int] = 1000

    def __post_init__(self) -> None:
        require_credit(self.name, self.sources)

    def illumination(self) -> PlacedIllumination:
        return self.sources

    def estimate(
        self,
        origin: np.ndarray,
        *,
        ground_z_m: float = 0.0,
        seed: int | None = None,
    ) -> Surplus:
        """Return the historical scalar next-event result."""
        surplus, _gather = self._estimate_and_gather(
            origin,
            ground_z_m=ground_z_m,
            seed=seed,
            field_grid=None,
        )
        return surplus

    def estimate_field(
        self,
        origin: np.ndarray,
        *,
        ground_z_m: float = 0.0,
        seed: int | None = None,
    ) -> tuple[Surplus, NextEventField]:
        """Return the scalar result and a diagnostic local angular field."""
        surplus, gather = self._estimate_and_gather(
            origin,
            ground_z_m=ground_z_m,
            seed=seed,
            field_grid=self.tracer.local_grid,
        )
        direct_mass, _seen = _direct_field_masses(
            self.geometry,
            np.asarray(origin, dtype=np.float64),
            self.sources,
            self.tracer.local_grid,
        )
        return surplus, gather.field(direct_mass)

    def _estimate_and_gather(
        self,
        origin: np.ndarray,
        *,
        ground_z_m: float,
        seed: int | None,
        field_grid: np.ndarray | None,
    ) -> tuple[Surplus, NextEventGather]:
        trace_seed = self.tracer.config.seed if seed is None else seed
        direct, seen = direct_from_sites(
            self.geometry,
            np.atleast_2d(origin),
            self.sources.sites(),
            weights=getattr(self.sources, "source_weights", None),
        )
        gather = NextEventGather(
            geometry=self.geometry,
            sources=self.sources,
            rng=np.random.default_rng(trace_seed + self.gather_seed_offset),
            samples=self.samples,
            max_order=self.tracer.config.max_bounces if self.max_order is None else self.max_order,
            lift_m=self.connection_lift_m,
            field_grid=field_grid,
        )
        point = self.tracer.trace(
            origin,
            dict(self.diagnostic_models),
            ground_z_m=ground_z_m,
            seed=seed,
            gather=gather,
        )
        bounced = gather.chi_bounce()
        surplus = Surplus(
            estimator=self.name,
            law=self.sources.law,
            direct=float(direct[0]),
            total=float(direct[0]) + bounced,
            detail={
                "bounced": bounced,
                "by_order": [float(value) for value in gather.chi_by_order()],
                "visible_fraction": float(seen[0]),
                "sky_fraction": point.sky_fraction,
                "mean_bounces": point.mean_bounces,
                "escape_chi": {name: point.susceptibility[name] for name in self.diagnostic_models},
                "escape_chi_direct": {name: point.susceptibility_direct[name] for name in self.diagnostic_models},
                "connections": gather.connections,
                "clear_fraction": gather.cleared / max(gather.connections, 1),
            },
        )
        return surplus, gather
