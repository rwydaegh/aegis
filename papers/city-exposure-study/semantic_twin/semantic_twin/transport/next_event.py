"""Next-event connections from path vertices to explicit source sites."""

from __future__ import annotations

import time
from collections import OrderedDict
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, ClassVar

import numpy as np

from ..illumination.model import AngularIllumination, PlacedIllumination
from ..illumination.sources import direct_from_sites, normalized_source_weights, visible
from ..illumination.sphere import nearest_cell
from .device_next_event import (
    BoundDeviceSpecularFaceProposal,
    DeviceNextEventGather,
    DeviceSpecularFaceProposal,
)
from .device_tracer import DeviceEscapeTracer
from .directional import DirectionalMeasure, _directions
from .model import Surplus, require_credit
from .persistent_cache import (
    CACHE_SCHEMA,
    DirectCacheValue,
    PersistentTransportCache,
    SpecularCacheValue,
    cache_key,
)
from .specular import (
    DEFAULT_SPECULAR_CANDIDATE_BUDGET,
    OneBounceSpecularTransport,
    ReceiverVisibleFaceCandidates,
    SpecularCandidateSet,
    SpecularDiagnostics,
    SpecularPaths,
    SpecularWorkEstimate,
    StratifiedSourceQuadrature,
)
from .specular_sampling import SampledOneBounceSpecularEstimator
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
    masses, _directions, _atom_mass, _direct, seen = _direct_field_data(
        geometry, origin, sources, local_grid, epsilon_m=epsilon_m
    )
    return masses, seen


def _direct_field_atoms(
    geometry: Any,
    origin: np.ndarray,
    sources: PlacedIllumination,
    *,
    epsilon_m: float = 1.0e-3,
) -> tuple[np.ndarray, np.ndarray]:
    """Return visible direct sources as exact physical-arrival atoms.

    The source-side direction is receiver-to-source. Reciprocity changes its
    sign for the body arrival direction, while the transfer mass itself stays
    in the raw placed-source scale used by :func:`_direct_field_masses`.
    """
    _masses, directions, atom_mass, _direct, _seen = _direct_field_data(
        geometry, origin, sources, None, epsilon_m=epsilon_m
    )
    return directions, atom_mass


def _direct_field_data(
    geometry: Any,
    origin: np.ndarray,
    sources: PlacedIllumination,
    local_grid: np.ndarray | None,
    *,
    epsilon_m: float = 1.0e-3,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, float, float]:
    """Collect direct bins, exact atoms, and scalar bookkeeping in one pass."""
    sites = np.asarray(sources.sites(), dtype=np.float64)
    masses = (
        np.zeros(local_grid.shape[0], dtype=np.float64) if local_grid is not None else np.empty(0, dtype=np.float64)
    )
    if sites.shape[0] == 0:
        empty_directions = np.empty((0, 3), dtype=np.float64)
        return masses, empty_directions, np.empty(0, dtype=np.float64), 0.0, 0.0

    receiver = np.asarray(origin, dtype=np.float64)
    probabilities = normalized_source_weights(sources)
    clear, distance = visible(
        geometry,
        np.broadcast_to(receiver, sites.shape),
        sites,
        epsilon_m=epsilon_m,
    )
    direction = (sites - receiver[None, :]) / np.maximum(distance, 1.0e-12)[:, None]
    unweighted = np.zeros_like(distance)
    unweighted[clear] = 1.0 / np.square(distance[clear])
    weighted = probabilities * unweighted
    if local_grid is not None:
        np.add.at(masses, nearest_cell(direction, local_grid), weighted)

    raw_weights = getattr(sources, "source_weights", None)
    equal_sources = raw_weights is None or np.all(np.asarray(raw_weights) == np.asarray(raw_weights)[0])
    direct_total = 0.0
    seen_total = 0.0
    for start in range(0, sites.shape[0], 400_000):
        stop = min(start + 400_000, sites.shape[0])
        clear_chunk = clear[start:stop]
        distance_chunk = distance[start:stop][clear_chunk]
        direct_total += float(np.sum(1.0 / np.square(distance_chunk), dtype=np.float64))
        seen_total += float(np.sum(clear_chunk, dtype=np.float64))
    if equal_sources:
        direct = direct_total / sites.shape[0]
        seen = seen_total / sites.shape[0]
    else:
        weighted_total = 0.0
        weighted_seen = 0.0
        for start in range(0, sites.shape[0], 400_000):
            stop = min(start + 400_000, sites.shape[0])
            clear_chunk = clear[start:stop]
            weighted_total += float(np.sum(weighted[start:stop][clear_chunk], dtype=np.float64))
            weighted_seen += float(np.sum(probabilities[start:stop][clear_chunk], dtype=np.float64))
        direct = weighted_total
        seen = weighted_seen
    return masses, -direction[clear], weighted[clear], direct, seen


@dataclass(frozen=True)
class NextEventField:
    """Local angular masses from a facade-tip next-event trace.

    ``local_grid`` is the reciprocal ray's departure direction ``u0``. The
    physical body arrival direction is ``k_hat = -u0``. The two mass arrays carry
    the transfer contributions before division by solid angle. Their densities
    retain that transfer scale, so a caller must provide the desired reference
    transfer before using them as a normalized BodyCoupler spectrum.

    Directional atoms contain exact direct paths, deterministic one-reflection
    all-specular paths, and one-reflection source suffix estimates after a
    diffuse vertex. A sampled suffix atom is a Monte Carlo mass, not an exact
    path enumeration. Its reported standard error is conditional on the traced
    diffuse vertices. The diffuse grid owns only the zero-specular source suffix.
    Higher deterministic reflection orders remain absent and are explicitly
    marked below.
    """

    local_grid: np.ndarray
    solid_angle: float
    direct_mass: np.ndarray
    bounced_mass: np.ndarray
    diagnostic: bool = True
    includes_specular: bool = False
    missing_specular: bool = True
    specular_estimate_kind: str = "absent"
    finite_resolution_specular_estimate: bool = False
    specular_numerically_converged: bool = False
    specular_bounce_cap: int | None = None
    #: Exact visible direct source atoms in physical arrival convention.
    direct_k_hat: np.ndarray = field(default_factory=lambda: np.empty((0, 3), dtype=np.float64))
    direct_atom_mass: np.ndarray = field(default_factory=lambda: np.empty(0, dtype=np.float64))
    #: Deterministic all-specular paths and sampled diffuse/specular suffixes.
    specular_k_hat: np.ndarray = field(default_factory=lambda: np.empty((0, 3), dtype=np.float64))
    specular_atom_mass: np.ndarray = field(default_factory=lambda: np.empty(0, dtype=np.float64))
    #: Deterministic all-specular subset, retained separately for safe reuse.
    all_specular_k_hat: np.ndarray = field(default_factory=lambda: np.empty((0, 3), dtype=np.float64))
    all_specular_atom_mass: np.ndarray = field(default_factory=lambda: np.empty(0, dtype=np.float64))
    #: Diffuse-vertex/source-nearest specular subset, which may be sampled.
    mixed_specular_k_hat: np.ndarray = field(default_factory=lambda: np.empty((0, 3), dtype=np.float64))
    mixed_specular_atom_mass: np.ndarray = field(default_factory=lambda: np.empty(0, dtype=np.float64))
    all_specular_mass: float = 0.0
    mixed_specular_mass: float = 0.0
    specular_components_separable: bool = False
    sampled_specular_suffix_full_support: bool = False
    maximum_completed_all_specular_order: int = 0
    maximum_completed_specular_suffix_order: int = 0
    specular_work: dict[str, Any] = field(default_factory=dict)
    all_specular_diagnostics: dict[str, Any] = field(default_factory=dict)
    specular_source_refinement: tuple[dict[str, Any], ...] = ()

    def __post_init__(self) -> None:
        grid = np.asarray(self.local_grid, dtype=np.float64)
        direct = np.asarray(self.direct_mass, dtype=np.float64)
        bounced = np.asarray(self.bounced_mass, dtype=np.float64)
        grid = _directions(grid, "local_grid")
        if direct.shape != (grid.shape[0],) or bounced.shape != (grid.shape[0],):
            raise ValueError("direct_mass and bounced_mass must match local_grid")
        if not np.all(np.isfinite(direct)) or not np.all(np.isfinite(bounced)):
            raise ValueError("field arrays must be finite")
        if np.any(direct < 0.0) or np.any(bounced < 0.0):
            raise ValueError("field masses must be nonnegative")
        if not np.isfinite(self.solid_angle) or self.solid_angle <= 0.0:
            raise ValueError("solid_angle must be positive and finite")
        object.__setattr__(self, "local_grid", grid)
        object.__setattr__(self, "direct_mass", direct)
        object.__setattr__(self, "bounced_mass", bounced)
        atom_k_hat = np.asarray(self.direct_k_hat, dtype=np.float64)
        atom_mass = np.asarray(self.direct_atom_mass, dtype=np.float64)
        if atom_k_hat.ndim != 2 or atom_k_hat.shape[1] != 3:
            raise ValueError(f"direct_k_hat must have shape (atoms, 3), got {atom_k_hat.shape}")
        if atom_mass.shape != (atom_k_hat.shape[0],):
            raise ValueError("direct_atom_mass must match direct_k_hat")
        if not np.all(np.isfinite(atom_k_hat)) or not np.all(np.isfinite(atom_mass)):
            raise ValueError("direct atom arrays must be finite")
        if np.any(atom_mass < 0.0):
            raise ValueError("direct_atom_mass must be nonnegative")
        if not np.allclose(np.linalg.norm(atom_k_hat, axis=1), 1.0, rtol=1.0e-7, atol=1.0e-7):
            raise ValueError("direct_k_hat rows must be unit directions")
        object.__setattr__(self, "direct_k_hat", atom_k_hat)
        object.__setattr__(self, "direct_atom_mass", atom_mass)
        specular_k_hat = _directions(np.asarray(self.specular_k_hat, dtype=np.float64), "specular_k_hat")
        specular_atom_mass = np.asarray(self.specular_atom_mass, dtype=np.float64)
        if specular_atom_mass.shape != (specular_k_hat.shape[0],):
            raise ValueError("specular_atom_mass must match specular_k_hat")
        if np.any(~np.isfinite(specular_atom_mass)) or np.any(specular_atom_mass < 0.0):
            raise ValueError("specular_atom_mass must be finite and nonnegative")
        component_total = float(self.all_specular_mass) + float(self.mixed_specular_mass)
        if not np.isfinite(component_total) or self.all_specular_mass < 0.0 or self.mixed_specular_mass < 0.0:
            raise ValueError("specular component masses must be finite and nonnegative")
        if not np.isclose(component_total, np.sum(specular_atom_mass), rtol=2.0e-12, atol=1.0e-15):
            raise ValueError("specular component masses must sum to specular_atom_mass")
        if self.maximum_completed_all_specular_order not in (0, 1):
            raise ValueError("maximum completed all-specular order must be zero or one")
        if self.maximum_completed_specular_suffix_order not in (0, 1):
            raise ValueError("maximum completed specular suffix order must be zero or one")
        if self.specular_estimate_kind not in (
            "absent",
            "exact_order_1",
            "finite_resolution_order_1",
            "exact_all_sampled_mixed_order_1",
            "adaptive_all_sampled_mixed_order_1",
        ):
            raise ValueError("unknown specular estimate kind")
        finite_kinds = ("finite_resolution_order_1", "adaptive_all_sampled_mixed_order_1")
        if self.finite_resolution_specular_estimate != (self.specular_estimate_kind in finite_kinds):
            raise ValueError("finite-resolution specular flag must match specular_estimate_kind")
        if self.specular_bounce_cap is not None and (
            not isinstance(self.specular_bounce_cap, int)
            or isinstance(self.specular_bounce_cap, bool)
            or self.specular_bounce_cap < 0
        ):
            raise ValueError("specular_bounce_cap must be a nonnegative integer or None")
        object.__setattr__(self, "specular_k_hat", specular_k_hat)
        object.__setattr__(self, "specular_atom_mass", specular_atom_mass)
        for prefix in ("all_specular", "mixed_specular"):
            direction = _directions(np.asarray(getattr(self, f"{prefix}_k_hat"), dtype=np.float64), f"{prefix}_k_hat")
            mass = np.asarray(getattr(self, f"{prefix}_atom_mass"), dtype=np.float64)
            if mass.shape != (direction.shape[0],):
                raise ValueError(f"{prefix}_atom_mass must match {prefix}_k_hat")
            if np.any(~np.isfinite(mass)) or np.any(mass < 0.0):
                raise ValueError(f"{prefix}_atom_mass must be finite and nonnegative")
            object.__setattr__(self, f"{prefix}_k_hat", direction)
            object.__setattr__(self, f"{prefix}_atom_mass", mass)
        separated = self.all_specular_atom_mass.size + self.mixed_specular_atom_mass.size
        if separated and (
            not np.array_equal(
                np.concatenate((self.all_specular_k_hat, self.mixed_specular_k_hat), axis=0), specular_k_hat
            )
            or not np.array_equal(
                np.concatenate((self.all_specular_atom_mass, self.mixed_specular_atom_mass)), specular_atom_mass
            )
        ):
            raise ValueError("separated specular atoms must concatenate to specular atoms")
        if self.specular_components_separable and (
            not np.isclose(
                np.sum(self.all_specular_atom_mass, dtype=np.float64),
                self.all_specular_mass,
                rtol=2.0e-12,
                atol=1.0e-15,
            )
            or not np.isclose(
                np.sum(self.mixed_specular_atom_mass, dtype=np.float64),
                self.mixed_specular_mass,
                rtol=2.0e-12,
                atol=1.0e-15,
            )
        ):
            raise ValueError("separated atom masses must match their specular component totals")
        if self.sampled_specular_suffix_full_support and self.specular_estimate_kind not in (
            "exact_all_sampled_mixed_order_1",
            "adaptive_all_sampled_mixed_order_1",
        ):
            raise ValueError("sampled suffix full support requires a sampled specular estimate kind")

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
        return float(np.sum(self.bounced_mass, dtype=np.float64)) + self.specular

    @property
    def total(self) -> float:
        return self.direct + self.bounced

    @property
    def direct_atoms(self) -> float:
        """Total transfer mass in the exact direct atoms."""
        return float(np.sum(self.direct_atom_mass, dtype=np.float64))

    @property
    def specular(self) -> float:
        """Total one-reflection all-specular and mixed-suffix mass."""
        return float(np.sum(self.specular_atom_mass, dtype=np.float64))

    @property
    def specular_order_one_complete(self) -> bool:
        """Whether both declared order-one path classes were included."""
        return bool(
            self.maximum_completed_all_specular_order == 1 and self.maximum_completed_specular_suffix_order == 1
        )

    @property
    def specular_complete_through_bounce_cap(self) -> bool:
        """Whether exact specular support covers the configured transport cap."""
        return bool(self.specular_bounce_cap == 1 and self.specular_order_one_complete)

    @property
    def specular_result_complete(self) -> bool:
        """Backward-compatible alias for completeness through the bounce cap."""
        return self.specular_complete_through_bounce_cap

    def directional_measure(
        self,
        reference_transfer: float,
        reference_id: str | None = None,
    ) -> DirectionalMeasure:
        """Return normalized direct atoms plus bounced diffuse grid cells.

        The diagnostic ``direct_mass`` bins remain available for visualization,
        but are intentionally excluded here so a direct source cannot be counted
        once as an atom and again as a diffuse cell. ``reference_transfer`` is
        the caller-supplied positive free-space transfer scale for this field.
        """
        if not np.isfinite(reference_transfer) or reference_transfer <= 0.0:
            raise ValueError("reference_transfer must be positive and finite")
        if self.bounced_mass.size == 0:
            diffuse_k_hat = np.empty((0, 3), dtype=np.float64)
            diffuse_mass = np.empty(0, dtype=np.float64)
        else:
            diffuse_k_hat = -self.local_grid
            diffuse_mass = self.bounced_mass / float(reference_transfer)
        return DirectionalMeasure(
            atom_k_hat=np.concatenate((self.direct_k_hat, self.specular_k_hat), axis=0),
            atom_mass=np.concatenate((self.direct_atom_mass, self.specular_atom_mass)) / float(reference_transfer),
            diffuse_k_hat=diffuse_k_hat,
            diffuse_mass=diffuse_mass,
            reference_id=reference_id,
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "diagnostic": self.diagnostic,
            "includes_specular": self.includes_specular,
            "missing_specular": self.missing_specular,
            "specular_estimate_kind": self.specular_estimate_kind,
            "finite_resolution_specular_estimate": self.finite_resolution_specular_estimate,
            "specular_numerically_converged": self.specular_numerically_converged,
            "specular_bounce_cap": self.specular_bounce_cap,
            "specular_order_one_complete": self.specular_order_one_complete,
            "specular_complete_through_bounce_cap": self.specular_complete_through_bounce_cap,
            "specular_result_complete": self.specular_result_complete,
            "direction_convention": "local_grid=u0=-k_hat",
            "solid_angle": float(self.solid_angle),
            "direct_mass": self.direct_mass.tolist(),
            "bounced_mass": self.bounced_mass.tolist(),
            "direct": self.direct,
            "bounced": self.bounced,
            "total": self.total,
            "direct_atoms": self.direct_atoms,
            "specular_atoms": self.specular,
            "all_specular_mass": float(self.all_specular_mass),
            "mixed_specular_mass": float(self.mixed_specular_mass),
            "specular_components_separable": self.specular_components_separable,
            "sampled_specular_suffix_full_support": self.sampled_specular_suffix_full_support,
            "maximum_completed_all_specular_order": self.maximum_completed_all_specular_order,
            "maximum_completed_specular_suffix_order": self.maximum_completed_specular_suffix_order,
            "specular_work": dict(self.specular_work),
            "all_specular_diagnostics": dict(self.all_specular_diagnostics),
            "specular_source_refinement": [dict(level) for level in self.specular_source_refinement],
        }


@dataclass
class NextEventGather:
    """Connects every path vertex to a sampled base station site.

    This plugs into :meth:`SbrTracer.trace` as its ``gather``, which already hands
    over everything a connection needs: where the vertex is, the normal already
    turned to face the incoming ray, the throughput after this interaction's
    reflectance, and the Rayleigh coherent share whose complement is the diffuse
    lobe.

    The zero-specular connection owns the diffuse lobe. When a finite-face image
    solver is attached, a second mutually exclusive connection reaches the same
    drawn source through exactly one coherent reflection before the source-nearest
    diffuse vertex. All-specular paths are solved once by the estimator rather
    than through this stochastic gather.

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
    specular_transport: OneBounceSpecularTransport | None = None
    specular_work: SpecularWorkEstimate | None = None
    sampled_specular_estimator: SampledOneBounceSpecularEstimator | None = None
    sampled_specular_samples: int = 1
    sampled_specular_seed: int = 0
    #: Restrict the reciprocal next-event gather to its first material vertex.
    #: This is deliberately a transport-topology choice, not a roulette or
    #: ray-budget optimisation: direct and deterministic one-reflection atoms
    #: are added by :class:`NextEventEstimator` outside this gather.
    first_material_interaction_only: bool = False

    total: float = 0.0
    by_order: np.ndarray = field(init=False)
    specular_suffix_total: float = 0.0
    specular_suffix_by_order: np.ndarray = field(init=False)
    bounced_mass: np.ndarray | None = field(init=False, default=None)
    connections: int = 0
    cleared: int = 0
    rays: int = 0
    _launch_cells: np.ndarray | None = field(init=False, default=None, repr=False)
    _source_probabilities: np.ndarray = field(init=False, repr=False)
    _arrival_k_hat: np.ndarray | None = field(init=False, default=None, repr=False)
    _specular_k_hat: list[np.ndarray] = field(init=False, default_factory=list, repr=False)
    _specular_mass: list[np.ndarray] = field(init=False, default_factory=list, repr=False)
    specular_candidates: int = 0
    specular_accepted: int = 0
    specular_seconds: float = 0.0
    sampled_specular_trials: int = 0
    sampled_specular_solver_calls: int = 0
    sampled_specular_conditional_variance: float = 0.0
    _sampled_specular_counter: int = field(init=False, default=0, repr=False)
    _sampled_contribution_sum: float = field(init=False, default=0.0, repr=False)
    _sampled_contribution_sq_sum: float = field(init=False, default=0.0, repr=False)

    def __post_init__(self) -> None:
        self.by_order = np.zeros(self.max_order + 1, dtype=np.float64)
        self.specular_suffix_by_order = np.zeros(self.max_order + 1, dtype=np.float64)
        self._source_probabilities = normalized_source_weights(self.sources)
        if self.specular_transport is not None and self.sampled_specular_estimator is not None:
            raise ValueError("exact and sampled specular suffix estimators are mutually exclusive")
        if self.sampled_specular_samples < 1:
            raise ValueError("sampled_specular_samples must be positive")
        if not isinstance(self.first_material_interaction_only, bool):
            raise TypeError("first_material_interaction_only must be boolean")
        if self.field_grid is not None:
            grid = np.asarray(self.field_grid, dtype=np.float64)
            if grid.ndim != 2 or grid.shape[1] != 3 or grid.shape[0] == 0:
                raise ValueError("field_grid must have shape (positive cells, 3)")
            grid = _directions(grid, "field_grid")
            self.field_grid = grid
            self.bounced_mass = np.zeros(grid.shape[0], dtype=np.float64)

    def begin(self, origin: np.ndarray, count: int) -> None:
        del origin
        self.rays += int(count)
        self._arrival_k_hat = np.zeros((int(count), 3), dtype=np.float64)

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
        del path_length, face
        if self.first_material_interaction_only and not np.all(np.asarray(order) == 1):
            keep = np.asarray(order) == 1
            index = index[keep]
            position = position[keep]
            incoming = incoming[keep]
            normal = normal[keep]
            throughput = throughput[keep]
            share = share[keep]
            order = np.asarray(order)[keep]
            if position.shape[0] == 0:
                return
        sites = self.sources.sites()
        if sites.shape[0] == 0 or position.shape[0] == 0:
            return

        first = np.asarray(order) == 1
        if self._arrival_k_hat is not None and np.any(first):
            self._arrival_k_hat[index[first]] = -incoming[first]

        # The diffuse lobe of a Lambertian reflector, whose albedo is already in
        # `throughput`. Splitting it out here is what keeps the coherent share
        # from being counted twice, once by this connection and once by the
        # mirror direction the tracer continues in.
        lobe = throughput * (1.0 - share) / np.pi
        bin_order = np.minimum(np.asarray(order, dtype=np.int64), self.max_order)

        if self.sampled_specular_estimator is not None:
            self._connect_sampled_specular_suffix(index, position, normal, lobe, bin_order)

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
        self._connect_one_specular_suffix(target, index, position, normal, lobe, bin_order)
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

    def _connect_one_specular_suffix(
        self,
        target: np.ndarray,
        index: np.ndarray,
        position: np.ndarray,
        normal: np.ndarray,
        lobe: np.ndarray,
        bin_order: np.ndarray,
    ) -> None:
        """Connect the source through one mirror patch to this diffuse vertex."""
        if self.specular_transport is None or self.max_order < 2:
            return
        eligible = np.flatnonzero((bin_order < self.max_order) & (lobe > 0.0))
        if eligible.size == 0:
            return
        paths = self.specular_transport.solve_paired(target[eligible], position[eligible])
        diagnostics = paths.diagnostics
        self.specular_candidates += diagnostics.candidates
        self.specular_accepted += diagnostics.accepted
        self.specular_seconds += diagnostics.seconds
        if paths.transfer.size == 0:
            return
        pair = eligible[paths.endpoint_index]
        total_order = bin_order[pair] + 1
        toward_reflection = -paths.k_hat
        cosine = np.einsum("ij,ij->i", toward_reflection, normal[pair])
        keep = (cosine > 0.0) & (total_order <= self.max_order)
        if not np.any(keep):
            return
        pair = pair[keep]
        total_order = total_order[keep]
        weight = lobe[pair] * cosine[keep] * paths.transfer[keep]
        positive = weight > 0.0
        if not np.any(positive):
            return
        pair = pair[positive]
        total_order = total_order[positive]
        weight = weight[positive]
        self.specular_suffix_total += float(np.sum(weight, dtype=np.float64))
        np.add.at(self.specular_suffix_by_order, total_order, weight)
        if self.field_grid is not None:
            if self._arrival_k_hat is None:
                raise RuntimeError("field-enabled next-event gather did not receive launch directions")
            self._specular_k_hat.append(self._arrival_k_hat[index[pair]].copy())
            self._specular_mass.append(weight.copy())

    def _connect_sampled_specular_suffix(
        self,
        index: np.ndarray,
        position: np.ndarray,
        normal: np.ndarray,
        lobe: np.ndarray,
        bin_order: np.ndarray,
    ) -> None:
        """Sample one full-support mirror suffix in its own counter namespace."""
        if self.max_order < 2:
            return
        eligible = np.flatnonzero((bin_order < self.max_order) & (lobe > 0.0))
        if eligible.size == 0:
            return
        if self._arrival_k_hat is None:
            raise RuntimeError("sampled specular suffix did not receive launch directions")
        result = self.sampled_specular_estimator.estimate_suffix(
            position[eligible],
            normal[eligible],
            lobe[eligible],
            self._arrival_k_hat[index[eligible]],
            bin_order[eligible],
            samples_per_vertex=self.sampled_specular_samples,
            seed=self.sampled_specular_seed,
            counter_start=self._sampled_specular_counter,
        )
        diagnostics = result.diagnostics
        self._sampled_specular_counter = diagnostics.counter_stop
        self.specular_candidates += diagnostics.candidates
        self.specular_accepted += diagnostics.accepted
        self.specular_seconds += diagnostics.seconds
        self.sampled_specular_trials += diagnostics.trials
        self.sampled_specular_solver_calls += diagnostics.solver_calls
        self.sampled_specular_conditional_variance += diagnostics.estimated_variance
        self._sampled_contribution_sum += float(np.sum(result.trial_transfer, dtype=np.float64))
        self._sampled_contribution_sq_sum += float(np.dot(result.trial_transfer, result.trial_transfer))
        self.specular_suffix_total += result.transfer
        self.specular_suffix_by_order[: result.by_order.size] += result.by_order
        if self.field_grid is not None and result.mass.size:
            self._specular_k_hat.append(result.k_hat.copy())
            self._specular_mass.append(result.mass.copy())

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

    def chi_specular_suffix(self) -> float:
        """One-reflection source suffixes after source-nearest diffuse vertices."""
        if self.rays == 0:
            return 0.0
        sample_divisor = 1 if self.sampled_specular_estimator is not None else self.samples
        return 4.0 * np.pi * self.specular_suffix_total / (self.rays * sample_divisor)

    def chi_specular_suffix_by_order(self) -> np.ndarray:
        if self.rays == 0:
            return np.zeros_like(self.specular_suffix_by_order)
        sample_divisor = 1 if self.sampled_specular_estimator is not None else self.samples
        return 4.0 * np.pi * self.specular_suffix_by_order / (self.rays * sample_divisor)

    def specular_atoms(self) -> tuple[np.ndarray, np.ndarray]:
        """Exact receiver arrival directions and normalized raw transfer masses."""
        if not self._specular_mass:
            return np.empty((0, 3), dtype=np.float64), np.empty(0, dtype=np.float64)
        sample_divisor = 1 if self.sampled_specular_estimator is not None else self.samples
        scale = 4.0 * np.pi / (self.rays * sample_divisor)
        return np.concatenate(self._specular_k_hat), scale * np.concatenate(self._specular_mass)

    def sampled_specular_diagnostics(self) -> dict[str, Any]:
        """Conditional proposal diagnostics, excluding primary-ray uncertainty."""
        estimator = self.sampled_specular_estimator
        if estimator is None:
            return {"enabled": False}
        ess = (
            self._sampled_contribution_sum**2 / self._sampled_contribution_sq_sum
            if self._sampled_contribution_sq_sum > 0.0
            else 0.0
        )
        scale = 0.0 if self.rays == 0 else 4.0 * np.pi / self.rays
        return {
            "enabled": True,
            "samples_per_vertex": self.sampled_specular_samples,
            "seed": self.sampled_specular_seed,
            "counter_start": 0,
            "counter_stop": self._sampled_specular_counter,
            "trials": self.sampled_specular_trials,
            "candidates": self.specular_candidates,
            "accepted": self.specular_accepted,
            "acceptance": self.specular_accepted / max(self.sampled_specular_trials, 1),
            "solver_calls": self.sampled_specular_solver_calls,
            "conditional_estimated_variance_raw": self.sampled_specular_conditional_variance,
            "conditional_standard_error_chi": scale * np.sqrt(self.sampled_specular_conditional_variance),
            "conditional_contribution_ess": ess,
            "uncertainty_scope": (
                "conditional_on_traced_diffuse_vertices_and_not_a_total_estimator_standard_error; "
                "campaign_seed_replicas_control_primary_ray_body_and_cdf_uncertainty"
            ),
            "sampling_identity": estimator.sampling_identity(),
        }

    def field(
        self,
        direct_mass: np.ndarray | None = None,
        *,
        direct_k_hat: np.ndarray | None = None,
        direct_atom_mass: np.ndarray | None = None,
        all_specular: SpecularPaths | None = None,
        source_refinement: list[dict[str, Any]] | None = None,
        specular_bounce_cap: int | None = None,
    ) -> NextEventField:
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
        atom_k_hat = (
            np.empty((0, 3), dtype=np.float64) if direct_k_hat is None else np.asarray(direct_k_hat, dtype=np.float64)
        )
        atom_mass = (
            np.empty(0, dtype=np.float64)
            if direct_atom_mass is None
            else np.asarray(direct_atom_mass, dtype=np.float64)
        )
        mixed_k_hat, mixed_mass = self.specular_atoms()
        if all_specular is None:
            all_k_hat = np.empty((0, 3), dtype=np.float64)
            all_mass = np.empty(0, dtype=np.float64)
        else:
            all_k_hat = all_specular.k_hat
            all_mass = all_specular.transfer
        specular_k_hat = np.concatenate((all_k_hat, mixed_k_hat), axis=0)
        specular_mass = np.concatenate((all_mass, mixed_mass))
        sampled_suffix = bool(
            self.max_order >= 2
            and self.sampled_specular_estimator is not None
            and self.sampled_specular_estimator.ready
        )
        suffix_included = self.specular_transport is not None or sampled_suffix
        suffix_completed = int(
            self.specular_transport is not None and self.specular_transport.surfaces.support_complete
        )
        sampled_full_support = bool(
            sampled_suffix
            and self.sampled_specular_estimator is not None
            and self.sampled_specular_estimator.sampling_identity()["surface_support_complete"]
            and self.sampled_specular_estimator.sampling_identity()["source_support"]
            == self.sampled_specular_estimator.sampling_identity()["source_count"]
        )
        all_included = all_specular is not None
        all_completed = int(all_included and all_specular.diagnostics.candidate_support_complete)
        if source_refinement:
            all_completed &= int(bool(source_refinement[-1]["source_support_complete"]))
        finite_resolution = bool(
            all_specular is not None
            and (
                not all_specular.diagnostics.candidate_support_complete
                or bool(source_refinement and not source_refinement[-1]["source_support_complete"])
            )
        )
        if sampled_suffix and finite_resolution:
            estimate_kind = "adaptive_all_sampled_mixed_order_1"
        elif sampled_suffix:
            estimate_kind = "exact_all_sampled_mixed_order_1"
        elif finite_resolution:
            estimate_kind = "finite_resolution_order_1"
        elif all_included or suffix_included:
            estimate_kind = "exact_order_1"
        else:
            estimate_kind = "absent"
        numerically_converged = bool(
            all_completed or (source_refinement and source_refinement[-1].get("numerically_converged", False))
        )
        return NextEventField(
            local_grid=self.field_grid,
            solid_angle=4.0 * np.pi / self.field_grid.shape[0],
            direct_mass=direct,
            bounced_mass=bounced,
            direct_k_hat=atom_k_hat,
            direct_atom_mass=atom_mass,
            specular_k_hat=specular_k_hat,
            specular_atom_mass=specular_mass,
            all_specular_k_hat=all_k_hat,
            all_specular_atom_mass=all_mass,
            mixed_specular_k_hat=mixed_k_hat,
            mixed_specular_atom_mass=mixed_mass,
            all_specular_mass=float(np.sum(all_mass, dtype=np.float64)),
            mixed_specular_mass=float(np.sum(mixed_mass, dtype=np.float64)),
            specular_components_separable=True,
            sampled_specular_suffix_full_support=sampled_full_support,
            includes_specular=all_included or suffix_included,
            missing_specular=True,
            specular_estimate_kind=estimate_kind,
            finite_resolution_specular_estimate=finite_resolution,
            specular_numerically_converged=numerically_converged,
            specular_bounce_cap=specular_bounce_cap,
            maximum_completed_all_specular_order=all_completed,
            maximum_completed_specular_suffix_order=suffix_completed,
            specular_work={} if self.specular_work is None else self.specular_work.as_dict(),
            all_specular_diagnostics={} if all_specular is None else all_specular.diagnostics.as_dict(),
            specular_source_refinement=tuple(source_refinement or ()),
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
            "chi_specular_suffix": self.chi_specular_suffix(),
            "specular_candidates": self.specular_candidates,
            "specular_accepted": self.specular_accepted,
            "specular_seconds": self.specular_seconds,
            "sampled_specular_suffix": self.sampled_specular_diagnostics(),
            "maximum_completed_specular_suffix_order": int(
                self.specular_transport is not None and self.specular_transport.surfaces.support_complete
            ),
            "specular_work": None if self.specular_work is None else self.specular_work.as_dict(),
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

    tracer: SbrTracer | DeviceEscapeTracer
    geometry: Any
    sources: PlacedIllumination
    samples: int = 1
    max_order: int | None = None
    connection_lift_m: float = 1.0e-2
    specular_order: int = 1
    specular_candidate_budget: int = DEFAULT_SPECULAR_CANDIDATE_BUDGET
    specular_transport: OneBounceSpecularTransport | None = None
    specular_suffix_mode: str = "exact"
    sampled_specular_samples: int = 1
    sampled_specular_seed_offset: int = 2000
    visible_face_candidates: ReceiverVisibleFaceCandidates = field(default_factory=ReceiverVisibleFaceCandidates)
    source_quadrature: StratifiedSourceQuadrature = field(default_factory=StratifiedSourceQuadrature)
    specular_refinement_relative_tolerance: float = 0.02
    diagnostic_models: Mapping[str, AngularIllumination] = field(default_factory=dict)
    deterministic_cache_size: int = 8
    persistent_cache_dir: Path | None = None
    #: ``hybrid_max_bounces_v1`` preserves the historical bounded hybrid
    #: transport. ``first_material_interaction_v1`` is the closed first-surface
    #: contract: exact direct and order-one all-specular atoms plus diffuse NEE
    #: at the first material vertex only.
    transport_topology: str = "hybrid_max_bounces_v1"
    _deterministic_cache: OrderedDict[tuple[Any, ...], Any] = field(
        default_factory=OrderedDict,
        init=False,
        repr=False,
        compare=False,
    )
    _device_specular_face_proposal: BoundDeviceSpecularFaceProposal | None = field(
        default=None,
        init=False,
        repr=False,
        compare=False,
    )
    _persistent_cache: PersistentTransportCache | None = field(
        default=None,
        init=False,
        repr=False,
        compare=False,
    )

    name: ClassVar[str] = "next_event"
    gather_seed_offset: ClassVar[int] = 1000

    def __post_init__(self) -> None:
        require_credit(self.name, self.sources)
        if self.specular_order not in (0, 1):
            raise ValueError("maximum completed specular order is one")
        if self.specular_candidate_budget < 1:
            raise ValueError("specular_candidate_budget must be positive")
        if self.specular_suffix_mode not in ("exact", "sampled", "disabled"):
            raise ValueError("specular_suffix_mode must be 'exact', 'sampled', or 'disabled'")
        if self.transport_topology not in ("hybrid_max_bounces_v1", "first_material_interaction_v1"):
            raise ValueError("transport_topology must be hybrid_max_bounces_v1 or first_material_interaction_v1")
        if (
            not isinstance(self.sampled_specular_samples, int)
            or isinstance(self.sampled_specular_samples, bool)
            or self.sampled_specular_samples < 1
        ):
            raise ValueError("sampled_specular_samples must be a positive integer")
        if (
            not isinstance(self.sampled_specular_seed_offset, int)
            or isinstance(self.sampled_specular_seed_offset, bool)
            or self.sampled_specular_seed_offset < 0
        ):
            raise ValueError("sampled_specular_seed_offset must be a nonnegative integer")
        if self.specular_suffix_mode == "sampled" and self.specular_order != 1:
            raise ValueError("sampled specular suffixes require specular_order=1")
        if self.transport_topology == "first_material_interaction_v1":
            maximum_order = self.tracer.config.max_bounces if self.max_order is None else self.max_order
            if maximum_order != 1:
                raise ValueError("first-material-interaction transport requires max_order=1")
            if self.specular_order != 1:
                raise ValueError("first-material-interaction transport requires exact order-one all-specular support")
            if self.specular_suffix_mode != "disabled":
                raise ValueError("first-material-interaction transport requires specular_suffix_mode='disabled'")
        if self.deterministic_cache_size < 1:
            raise ValueError("deterministic_cache_size must be positive")
        if self.persistent_cache_dir is not None:
            cache_dir = Path(self.persistent_cache_dir)
            object.__setattr__(self, "persistent_cache_dir", cache_dir)
            object.__setattr__(self, "_persistent_cache", PersistentTransportCache(cache_dir))
        if not np.isfinite(self.specular_refinement_relative_tolerance) or not (
            0.0 < self.specular_refinement_relative_tolerance < 1.0
        ):
            raise ValueError("specular_refinement_relative_tolerance must lie strictly between zero and one")
        device_sampled = self.specular_order == 1 and self.specular_suffix_mode == "sampled"
        device_first_interaction = self.transport_topology == "first_material_interaction_v1"
        if (
            isinstance(self.tracer, DeviceEscapeTracer)
            and self.specular_order != 0
            and not (device_sampled or device_first_interaction)
        ):
            raise NotImplementedError(
                "resident device next-event estimation supports omitted specular transport or the "
                "full-support sampled order-one suffix; select specular_suffix_mode='sampled' or use SbrTracer"
            )
        if isinstance(self.tracer, DeviceEscapeTracer) and device_sampled:
            proposal = DeviceSpecularFaceProposal.from_geometry(self.tracer.geometry)
            object.__setattr__(
                self,
                "_device_specular_face_proposal",
                BoundDeviceSpecularFaceProposal.bind(proposal, self.tracer.kernel),
            )

    def _deterministic_key(
        self,
        kind: str,
        origin: np.ndarray,
        maximum_order: int,
        *variant: Any,
    ) -> tuple[Any, ...]:
        point = np.asarray(origin, dtype=np.float64)
        if point.shape != (3,) or np.any(~np.isfinite(point)):
            raise ValueError("origin must be one finite three-vector")
        return (
            kind,
            id(self.tracer),
            id(self.geometry),
            id(self.sources),
            id(self.specular_transport),
            tuple(float(value) for value in point),
            len(self.sources),
            maximum_order,
            self.specular_order,
            self.specular_suffix_mode,
            self.transport_topology,
            self.sampled_specular_samples,
            self.sampled_specular_seed_offset,
            self.specular_candidate_budget,
            self.visible_face_candidates.sample_levels,
            self.visible_face_candidates.growth_factor,
            self.source_quadrature.strata_levels,
            self.source_quadrature.growth_factor,
            self.specular_refinement_relative_tolerance,
            *variant,
        )

    def _cache_get(self, key: tuple[Any, ...]) -> Any | None:
        cached = self._deterministic_cache.get(key)
        if cached is not None:
            self._deterministic_cache.move_to_end(key)
        return cached

    def _cache_put(self, key: tuple[Any, ...], value: Any) -> None:
        self._deterministic_cache[key] = value
        self._deterministic_cache.move_to_end(key)
        while len(self._deterministic_cache) > self.deterministic_cache_size:
            self._deterministic_cache.popitem(last=False)

    def illumination(self) -> PlacedIllumination:
        return self.sources

    def transfer_scales(self, result: Surplus) -> dict[str, float]:
        """Report source-scale factors without changing legacy ``Surplus`` values.

        ``result.total`` is the historical unit-source, relative-population
        transfer.  The first field multiplies it by crop area and divides by
        the free-space ``4 pi`` convention, so it is per unit active antenna
        density and EIRP.  The optional physical field additionally applies the
        declared expected count and common EIRP, and therefore equals the first
        field times ``density_per_m2 * eirp_w``.
        """
        if not hasattr(self.sources, "per_density_eirp_transfer"):
            raise ValueError("source population does not declare a crop area")
        per_density = self.sources.per_density_eirp_transfer(result.total)
        scales = {"per_density_eirp_transfer": float(per_density)}
        count = getattr(self.sources, "physical_expected_count", None)
        eirp = getattr(self.sources, "eirp_w", None)
        if count is not None and eirp is not None:
            scales["physical_transfer_w_m2"] = float(self.sources.physical_transfer(result.total))
        return scales

    def estimate_scaled(
        self,
        origin: np.ndarray,
        *,
        ground_z_m: float = 0.0,
        seed: int | None = None,
    ) -> tuple[Surplus, dict[str, float]]:
        """Return the unchanged diagnostic result plus explicit source scales."""
        result = self.estimate(origin, ground_z_m=ground_z_m, seed=seed)
        return result, self.transfer_scales(result)

    def estimate(
        self,
        origin: np.ndarray,
        *,
        ground_z_m: float = 0.0,
        seed: int | None = None,
    ) -> Surplus:
        """Return the historical scalar next-event result."""
        surplus, _gather, _field_data, _all_specular, _source_refinement = self._estimate_and_gather(
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
        surplus, gather, field_data, all_specular, source_refinement = self._estimate_and_gather(
            origin,
            ground_z_m=ground_z_m,
            seed=seed,
            field_grid=self.tracer.local_grid,
        )
        if field_data is None:
            raise RuntimeError("field estimate did not collect direct field data")
        direct_mass, direct_k_hat, direct_atom_mass, _direct, _seen = field_data
        maximum_order = self.tracer.config.max_bounces if self.max_order is None else self.max_order
        if isinstance(gather, DeviceNextEventGather):
            mixed_grid = gather.specular_bounced_mass()
            mixed_positive = mixed_grid > 0.0
            mixed_k_hat = -np.asarray(self.tracer.local_grid[mixed_positive], dtype=np.float64)
            mixed_mass = np.asarray(mixed_grid[mixed_positive], dtype=np.float64)
            if all_specular is None:
                all_k_hat = np.empty((0, 3), dtype=np.float64)
                all_mass = np.empty(0, dtype=np.float64)
                all_diagnostics: dict[str, Any] = {}
            else:
                all_k_hat = all_specular.k_hat
                all_mass = all_specular.transfer
                all_diagnostics = all_specular.diagnostics.as_dict()
            sampled_diagnostics = gather.sampled_specular_diagnostics()
            sampled_identity = sampled_diagnostics.get("sampling_identity", {})
            sampled_active = bool(maximum_order >= 2 and sampled_diagnostics.get("enabled", False))
            sampled_full_support = bool(
                sampled_active
                and sampled_identity.get("surface_support_complete", False)
                and sampled_identity.get("source_support", 0) == sampled_identity.get("source_count", -1)
            )
            all_complete = bool(all_specular is not None and all_specular.diagnostics.candidate_support_complete)
            if source_refinement:
                all_complete &= bool(source_refinement[-1]["source_support_complete"])
            specular_k_hat = np.concatenate((all_k_hat, mixed_k_hat), axis=0)
            specular_mass = np.concatenate((all_mass, mixed_mass))
            detail = surplus.detail
            return surplus, NextEventField(
                local_grid=self.tracer.local_grid,
                solid_angle=4.0 * np.pi / self.tracer.local_grid.shape[0],
                direct_mass=direct_mass,
                bounced_mass=gather.bounced_mass(),
                direct_k_hat=direct_k_hat,
                direct_atom_mass=direct_atom_mass,
                specular_k_hat=specular_k_hat,
                specular_atom_mass=specular_mass,
                all_specular_k_hat=all_k_hat,
                all_specular_atom_mass=all_mass,
                mixed_specular_k_hat=mixed_k_hat,
                mixed_specular_atom_mass=mixed_mass,
                all_specular_mass=float(np.sum(all_mass, dtype=np.float64)),
                mixed_specular_mass=float(np.sum(mixed_mass, dtype=np.float64)),
                specular_components_separable=True,
                sampled_specular_suffix_full_support=sampled_full_support,
                includes_specular=bool(all_specular is not None or sampled_active),
                missing_specular=True,
                specular_estimate_kind=str(detail["specular_estimate_kind"]),
                finite_resolution_specular_estimate=bool(detail["finite_resolution_specular_estimate"]),
                specular_numerically_converged=bool(detail["specular_numerically_converged"]),
                specular_bounce_cap=maximum_order,
                maximum_completed_all_specular_order=int(all_complete),
                maximum_completed_specular_suffix_order=0,
                specular_work=dict(detail["specular_work"]),
                all_specular_diagnostics=all_diagnostics,
                specular_source_refinement=tuple(source_refinement),
            )
        return surplus, gather.field(
            direct_mass,
            direct_k_hat=direct_k_hat,
            direct_atom_mass=direct_atom_mass,
            all_specular=all_specular,
            source_refinement=source_refinement,
            specular_bounce_cap=maximum_order,
        )

    def _automatic_specular_transport(self) -> OneBounceSpecularTransport:
        key = ("automatic_specular_transport", id(self.tracer), self.specular_candidate_budget)
        cached = self._cache_get(key)
        if cached is None:
            cached = OneBounceSpecularTransport(
                self.tracer,
                candidate_budget=self.specular_candidate_budget,
            )
            self._cache_put(key, cached)
        return cached

    @staticmethod
    def _refinement_change(current: float, previous: float) -> tuple[float, float]:
        absolute = abs(current - previous)
        scale = max(abs(current), abs(previous))
        return absolute, 0.0 if scale == 0.0 else absolute / scale

    def _adaptive_all_specular(
        self,
        transport: OneBounceSpecularTransport,
        origin: np.ndarray,
    ) -> tuple[SpecularPaths | None, list[dict[str, Any]], dict[str, Any]]:
        """Refine receiver support and source quadrature until tolerance or budget."""
        sites = np.asarray(self.sources.sites(), dtype=np.float64)
        probabilities = normalized_source_weights(self.sources)
        receiver = np.asarray(origin, dtype=np.float64)
        tolerance = self.specular_refinement_relative_tolerance
        budget = self.specular_candidate_budget
        face_samples = self.visible_face_candidates.sample_levels[0]
        source_strata = self.source_quadrature.strata_levels[0]
        if face_samples > budget:
            return (
                None,
                [],
                {
                    "method": "adaptive_receiver_faces_and_probability_strata",
                    "candidate_budget": budget,
                    "candidate_work_used": 0,
                    "executed_candidate_work_used": 0,
                    "avoided_candidate_work": 0,
                    "executed_candidate_seconds": 0.0,
                    "visibility_rays_used": 0,
                    "refinement_work_used": 0,
                    "relative_tolerance": tolerance,
                    "numerically_converged": False,
                    "support_complete": False,
                    "mixed_specular_suffix_enabled": False,
                    "stop_reason": "initial_visibility_screen_exceeds_candidate_budget",
                    "enabled": False,
                    "estimate_count": 0,
                },
            )
        candidates = self.visible_face_candidates.refine_level(transport, receiver, face_samples)
        visibility_rays = face_samples
        candidate_work = 0
        executed_candidate_work = 0
        executed_candidate_seconds = 0.0
        refinement: list[dict[str, Any]] = []
        face_level = 0
        source_level = 0
        stop_reason = "candidate_budget_exhausted"
        blocked_next_cycle: dict[str, int] | None = None

        def selection(strata: int):
            return self.source_quadrature.select(sites, probabilities, strata)

        surface_face_index = np.asarray(transport.surfaces.face_index, dtype=np.int64)
        reusable_face_identity = np.unique(surface_face_index).size == surface_face_index.size

        def execute(candidate_set: SpecularCandidateSet, selected: Any) -> SpecularPaths:
            nonlocal executed_candidate_seconds, executed_candidate_work
            paired_receiver = np.broadcast_to(receiver, selected.positions.shape)
            paths = transport.solve_paired(
                selected.positions,
                paired_receiver,
                endpoint_weight=selected.probabilities,
                source_index=selected.source_index,
                candidate_set=candidate_set,
            )
            executed_candidate_work += paths.diagnostics.candidates
            executed_candidate_seconds += paths.diagnostics.seconds
            return paths

        def merge_face_blocks(
            parts: tuple[SpecularPaths, ...],
            candidate_set: SpecularCandidateSet,
            selected: Any,
        ) -> SpecularPaths:
            candidate_faces = candidate_set.sequences[:, 0]
            actual_faces = surface_face_index[candidate_faces]
            rank_by_actual = {int(actual): rank for rank, actual in enumerate(actual_faces)}
            accepted = sum(part.diagnostics.accepted for part in parts)
            logical_candidates = int(candidate_faces.size * selected.positions.shape[0])
            diagnostics = SpecularDiagnostics(
                endpoint_pairs=int(selected.positions.shape[0]),
                plane_sequences=int(candidate_faces.size),
                candidates=logical_candidates,
                geometric=sum(part.diagnostics.geometric for part in parts),
                visible=sum(part.diagnostics.visible for part in parts),
                accepted=accepted,
                chunks=(logical_candidates + transport.candidate_chunk - 1) // transport.candidate_chunk,
                seconds=sum(part.diagnostics.seconds for part in parts),
                candidate_method=candidate_set.method,
                candidate_support_complete=candidate_set.support_complete,
                selected_faces=int(np.unique(candidate_faces).size),
                support_faces=int(transport.surfaces.scene_face_count or transport.surfaces.triangles.shape[0]),
                missed_support_faces=candidate_set.missed_support_faces,
                candidate_diagnostics=dict(candidate_set.diagnostics),
            )
            if accepted == 0:
                return SpecularPaths.empty(diagnostics)
            k_hat = np.concatenate([part.k_hat for part in parts])
            transfer = np.concatenate([part.transfer for part in parts])
            reflection = np.concatenate([part.reflection_point for part in parts])
            source = np.concatenate([part.source_index for part in parts])
            endpoint = np.concatenate([part.endpoint_index for part in parts])
            sequence = np.concatenate([part.surface_sequence for part in parts])
            length = np.concatenate([part.unfolded_length_m for part in parts])
            face_rank = np.fromiter(
                (rank_by_actual[int(face)] for face in sequence[:, 0]),
                dtype=np.int64,
                count=accepted,
            )
            order = np.lexsort((face_rank, endpoint))
            return SpecularPaths(
                k_hat[order],
                transfer[order],
                reflection[order],
                source[order],
                endpoint[order],
                sequence[order],
                length[order],
                diagnostics,
            )

        def record(
            paths: SpecularPaths,
            selected: Any,
            candidate_set: SpecularCandidateSet,
            *,
            axis: str,
            face_index: int,
            source_index: int,
            previous_face: tuple[SpecularPaths, float] | None,
            previous_source: tuple[SpecularPaths, float] | None,
            executed_candidates: int,
            executed_seconds: float,
        ) -> tuple[SpecularPaths, float]:
            nonlocal candidate_work
            candidate_work += paths.diagnostics.candidates
            transfer = paths.total
            if previous_face is None:
                absolute_face = relative_face = None
            else:
                absolute_face, relative_face = self._refinement_change(transfer, previous_face[1])
            if previous_source is None:
                absolute_source = relative_source = None
            else:
                absolute_source, relative_source = self._refinement_change(transfer, previous_source[1])
            face_converged = relative_face is not None and relative_face <= tolerance
            source_converged = selected.support_complete or (
                relative_source is not None and relative_source <= tolerance
            )
            numerical = bool(transfer > 0.0 and face_converged and source_converged)
            refinement.append(
                {
                    "step": len(refinement),
                    "axis_refined": axis,
                    "face_level": face_index,
                    "source_level": source_index,
                    "angular_samples": int(candidate_set.diagnostics["angular_samples"]),
                    "cumulative_visibility_rays": int(candidate_set.diagnostics["total_visibility_rays"]),
                    "selected_faces": int(candidate_set.sequences.shape[0]),
                    "requested_strata": selected.requested_strata,
                    "selected_sources": int(selected.positions.shape[0]),
                    "candidate_support_complete": False,
                    "source_support_complete": selected.support_complete,
                    "finite_resolution_support_incomplete": True,
                    "candidates": paths.diagnostics.candidates,
                    "cumulative_candidates": candidate_work,
                    "executed_candidates": executed_candidates,
                    "avoided_candidates": paths.diagnostics.candidates - executed_candidates,
                    "cumulative_executed_candidates": executed_candidate_work,
                    "cumulative_avoided_candidates": candidate_work - executed_candidate_work,
                    "accepted": paths.diagnostics.accepted,
                    "seconds": executed_seconds,
                    "executed_seconds": executed_seconds,
                    "cumulative_executed_seconds": executed_candidate_seconds,
                    "logical_solution_seconds": paths.diagnostics.seconds,
                    "reused_block_seconds": max(paths.diagnostics.seconds - executed_seconds, 0.0),
                    "transfer": transfer,
                    "absolute_change_from_previous_face_level": absolute_face,
                    "relative_change_from_previous_face_level": relative_face,
                    "absolute_change_from_previous_source_level": absolute_source,
                    "relative_change_from_previous_source_level": relative_source,
                    "face_axis_converged": face_converged,
                    "source_axis_converged": source_converged,
                    "numerically_converged": numerical,
                    "relative_tolerance": tolerance,
                }
            )
            value = (paths, transfer)
            return value

        selected = selection(source_strata)
        initial_cost = candidates.sequences.shape[0] * selected.positions.shape[0]
        if visibility_rays + initial_cost > budget:
            work = {
                "method": "adaptive_receiver_faces_and_probability_strata",
                "candidate_budget": budget,
                "candidate_work_used": 0,
                "executed_candidate_work_used": 0,
                "avoided_candidate_work": 0,
                "executed_candidate_seconds": 0.0,
                "visibility_rays_used": visibility_rays,
                "refinement_work_used": visibility_rays,
                "relative_tolerance": tolerance,
                "numerically_converged": False,
                "support_complete": False,
                "mixed_specular_suffix_enabled": False,
                "stop_reason": "initial_estimate_exceeds_candidate_budget",
                "enabled": False,
            }
            return None, refinement, work
        initial_paths = execute(candidates, selected)
        current = record(
            initial_paths,
            selected,
            candidates,
            axis="initial",
            face_index=face_level,
            source_index=source_level,
            previous_face=None,
            previous_source=None,
            executed_candidates=initial_paths.diagnostics.candidates,
            executed_seconds=initial_paths.diagnostics.seconds,
        )

        while True:
            next_source_strata = min(source_strata * self.source_quadrature.growth_factor, len(sites))
            source_is_exact = selected.support_complete or next_source_strata == source_strata
            if source_is_exact:
                next_source_strata = source_strata
                next_selected = selected
                next_source_level = source_level
            else:
                next_selected = selection(next_source_strata)
                next_source_level = source_level + 1
            next_face_samples = face_samples * self.visible_face_candidates.growth_factor
            if candidate_work + visibility_rays + next_face_samples > budget:
                stop_reason = "candidate_budget_exhausted"
                blocked_next_cycle = {
                    "angular_samples": next_face_samples,
                    "projected_refinement_work": candidate_work + visibility_rays + next_face_samples,
                }
                break
            next_candidates = self.visible_face_candidates.refine_level(
                transport,
                receiver,
                next_face_samples,
                previous=candidates,
            )
            visibility_rays += next_face_samples
            next_face_level = face_level + 1
            source_only_cost = (
                0 if source_is_exact else candidates.sequences.shape[0] * next_selected.positions.shape[0]
            )
            face_only_cost = next_candidates.sequences.shape[0] * selected.positions.shape[0]
            corner_cost = (
                0 if source_is_exact else next_candidates.sequences.shape[0] * next_selected.positions.shape[0]
            )
            cycle_cost = source_only_cost + face_only_cost + corner_cost
            if candidate_work + visibility_rays + cycle_cost > budget:
                stop_reason = "candidate_budget_exhausted"
                blocked_next_cycle = {
                    "angular_samples": next_face_samples,
                    "selected_faces": int(next_candidates.sequences.shape[0]),
                    "requested_strata": int(next_source_strata),
                    "projected_image_candidates": candidate_work + cycle_cost,
                    "projected_refinement_work": candidate_work + visibility_rays + cycle_cost,
                }
                break

            if source_is_exact:
                old_faces = candidates.sequences[:, 0]
                next_faces = next_candidates.sequences[:, 0]
                nested_faces = (
                    np.unique(old_faces).size == old_faces.size
                    and np.unique(next_faces).size == next_faces.size
                    and np.all(np.isin(old_faces, next_faces))
                )
                reuse_faces = reusable_face_identity and nested_faces
                if reuse_faces:
                    delta_mask = ~np.isin(next_faces, old_faces)
                    delta_candidates = SpecularCandidateSet(
                        next_candidates.sequences[delta_mask],
                        method=next_candidates.method,
                        support_complete=False,
                        missed_support_faces=next_candidates.missed_support_faces,
                        diagnostics=next_candidates.diagnostics,
                    )
                    delta = execute(delta_candidates, selected)
                    corner_paths = merge_face_blocks((current[0], delta), next_candidates, selected)
                    executed = delta.diagnostics.candidates
                else:
                    corner_paths = execute(next_candidates, selected)
                    executed = corner_paths.diagnostics.candidates
                corner = record(
                    corner_paths,
                    selected,
                    next_candidates,
                    axis="receiver_faces",
                    face_index=next_face_level,
                    source_index=source_level,
                    previous_face=current,
                    previous_source=None,
                    executed_candidates=executed,
                    executed_seconds=(delta.diagnostics.seconds if reuse_faces else corner_paths.diagnostics.seconds),
                )
                row = refinement[-1]
                row["source_axis_converged"] = True
                row["numerically_converged"] = bool(corner[1] > 0.0 and row["face_axis_converged"])
            else:
                source_paths = execute(candidates, next_selected)
                source_only = record(
                    source_paths,
                    next_selected,
                    candidates,
                    axis="source_quadrature",
                    face_index=face_level,
                    source_index=next_source_level,
                    previous_face=None,
                    previous_source=current,
                    executed_candidates=source_paths.diagnostics.candidates,
                    executed_seconds=source_paths.diagnostics.seconds,
                )
                old_faces = candidates.sequences[:, 0]
                next_faces = next_candidates.sequences[:, 0]
                nested_faces = (
                    np.unique(old_faces).size == old_faces.size
                    and np.unique(next_faces).size == next_faces.size
                    and np.all(np.isin(old_faces, next_faces))
                )
                reuse_faces = reusable_face_identity and nested_faces
                if reuse_faces:
                    delta_mask = ~np.isin(next_faces, old_faces)
                    delta_candidates = SpecularCandidateSet(
                        next_candidates.sequences[delta_mask],
                        method=next_candidates.method,
                        support_complete=False,
                        missed_support_faces=next_candidates.missed_support_faces,
                        diagnostics=next_candidates.diagnostics,
                    )
                    old_source_delta = execute(delta_candidates, selected)
                    face_paths = merge_face_blocks((current[0], old_source_delta), next_candidates, selected)
                    face_executed = old_source_delta.diagnostics.candidates
                else:
                    face_paths = execute(next_candidates, selected)
                    face_executed = face_paths.diagnostics.candidates
                face_only = record(
                    face_paths,
                    selected,
                    next_candidates,
                    axis="receiver_faces",
                    face_index=next_face_level,
                    source_index=source_level,
                    previous_face=current,
                    previous_source=None,
                    executed_candidates=face_executed,
                    executed_seconds=(
                        old_source_delta.diagnostics.seconds if reuse_faces else face_paths.diagnostics.seconds
                    ),
                )
                if reuse_faces:
                    new_source_delta = execute(delta_candidates, next_selected)
                    corner_paths = merge_face_blocks((source_only[0], new_source_delta), next_candidates, next_selected)
                    corner_executed = new_source_delta.diagnostics.candidates
                else:
                    corner_paths = execute(next_candidates, next_selected)
                    corner_executed = corner_paths.diagnostics.candidates
                corner = record(
                    corner_paths,
                    next_selected,
                    next_candidates,
                    axis="crossed_corner",
                    face_index=next_face_level,
                    source_index=next_source_level,
                    previous_face=source_only,
                    previous_source=face_only,
                    executed_candidates=corner_executed,
                    executed_seconds=(
                        new_source_delta.diagnostics.seconds if reuse_faces else corner_paths.diagnostics.seconds
                    ),
                )
            current = corner
            candidates = next_candidates
            selected = next_selected
            face_samples = next_face_samples
            source_strata = next_source_strata
            face_level = next_face_level
            source_level = next_source_level
            if refinement[-1]["numerically_converged"]:
                stop_reason = "relative_tolerance_reached"
                break

        numerically_converged = bool(refinement and refinement[-1]["numerically_converged"])
        work = {
            "method": "adaptive_receiver_faces_and_probability_strata",
            "candidate_budget": budget,
            "candidate_work_used": candidate_work,
            "executed_candidate_work_used": executed_candidate_work,
            "avoided_candidate_work": candidate_work - executed_candidate_work,
            "executed_candidate_seconds": executed_candidate_seconds,
            "total_candidates_upper_bound": candidate_work,
            "visibility_rays_used": visibility_rays,
            "refinement_work_used": candidate_work + visibility_rays,
            "relative_tolerance": tolerance,
            "numerically_converged": numerically_converged,
            "support_complete": False,
            "mixed_specular_suffix_enabled": False,
            "stop_reason": stop_reason,
            "enabled": bool(refinement),
            "estimate_count": len(refinement),
            "budget_remaining": budget - candidate_work - visibility_rays,
            "blocked_next_cycle": blocked_next_cycle,
            "face_level_counts": sorted({int(row["selected_faces"]) for row in refinement}),
            "source_strata_levels": sorted({int(row["requested_strata"]) for row in refinement}),
        }
        return current[0], refinement, work

    def _deterministic_specular(
        self,
        origin: np.ndarray,
        maximum_order: int,
    ) -> tuple[
        OneBounceSpecularTransport | None,
        SpecularWorkEstimate | None,
        SpecularPaths | None,
        list[dict[str, Any]],
        dict[str, Any] | None,
        float,
        bool,
        bool,
        str | None,
    ]:
        """Prepare deterministic reflection work once for a standpoint."""
        key = self._deterministic_key("specular", origin, maximum_order)
        cached = self._cache_get(key)
        if cached is not None:
            suffix_transport, specular_work, all_specular, refinement, finite_work, persistent_key = cached
            return (
                suffix_transport,
                specular_work,
                all_specular,
                refinement,
                finite_work,
                0.0,
                True,
                False,
                persistent_key,
            )

        started = time.perf_counter()
        all_specular_transport = self.specular_transport if self.specular_order == 1 else None
        supports_specular = hasattr(self.tracer, "geometry") and hasattr(self.tracer, "_surface_response")
        specular_work = None
        if all_specular_transport is None and self.specular_order == 1 and supports_specular:
            face_count = int(getattr(self.tracer.geometry, "face_count", 0))
            specular_work = SpecularWorkEstimate.exact_order_one(
                faces=face_count,
                sources=len(self.sources),
                rays=self.tracer.config.rays,
                samples=self.samples,
                max_bounces=maximum_order,
                candidate_budget=self.specular_candidate_budget,
                support_complete=True,
            )
            if face_count > 0 and maximum_order >= 1:
                all_specular_transport = self._automatic_specular_transport()
        elif all_specular_transport is not None:
            specular_work = all_specular_transport.work_estimate(
                sources=len(self.sources),
                rays=self.tracer.config.rays,
                samples=self.samples,
                max_bounces=maximum_order,
            )

        def compute() -> SpecularCacheValue:
            all_specular = None
            refinement: list[dict[str, Any]] = []
            finite_work: dict[str, Any] | None = None
            suffix_transport_enabled = False
            if all_specular_transport is not None and maximum_order >= 1:
                sites = np.asarray(self.sources.sites(), dtype=np.float64)
                probabilities = normalized_source_weights(self.sources)
                all_specular_cost = all_specular_transport.surfaces.triangles.shape[0] * sites.shape[0]
                if all_specular_cost <= self.specular_candidate_budget:
                    all_specular = all_specular_transport.solve_all_sources(
                        sites,
                        np.asarray(origin, dtype=np.float64),
                        probabilities,
                    )
                    support_complete = bool(all_specular.diagnostics.candidate_support_complete)
                    finite_work = {
                        "method": "exact_all_specular_order_1",
                        "candidate_budget": self.specular_candidate_budget,
                        "candidate_work_used": all_specular.diagnostics.candidates,
                        "total_candidates_upper_bound": all_specular.diagnostics.candidates,
                        "relative_tolerance": self.specular_refinement_relative_tolerance,
                        "numerically_converged": support_complete,
                        "support_complete": support_complete,
                        "mixed_specular_suffix_enabled": bool(
                            self.specular_suffix_mode == "sampled" or (specular_work and specular_work.enabled)
                        ),
                        "stop_reason": "full_reflection_and_source_support_enumerated",
                        "enabled": True,
                        "estimate_count": 1,
                    }
                    suffix_transport_enabled = bool(
                        self.specular_suffix_mode == "exact"
                        and specular_work is not None
                        and specular_work.enabled
                        and support_complete
                    )
                elif getattr(self.sources, "curve", None) is not None:
                    all_specular, refinement, finite_work = self._adaptive_all_specular(
                        all_specular_transport,
                        np.asarray(origin, dtype=np.float64),
                    )
                else:
                    finite_work = {
                        "method": "adaptive_receiver_faces_and_probability_strata",
                        "candidate_budget": self.specular_candidate_budget,
                        "candidate_work_used": 0,
                        "relative_tolerance": self.specular_refinement_relative_tolerance,
                        "numerically_converged": False,
                        "support_complete": False,
                        "mixed_specular_suffix_enabled": False,
                        "stop_reason": "source_curve_required_for_bounded_source_refinement",
                        "enabled": False,
                        "estimate_count": 0,
                    }
            if finite_work is not None and self.specular_suffix_mode == "sampled":
                finite_work = {
                    **finite_work,
                    "mixed_specular_suffix_enabled": bool(
                        all_specular_transport is not None
                        and all_specular_transport.surfaces.triangles.shape[0] > 0
                        and len(self.sources) > 0
                    ),
                    "mixed_specular_suffix_method": "full_support_sampled_one_reflection",
                }
            return SpecularCacheValue(
                specular_work,
                all_specular,
                refinement,
                finite_work,
                suffix_transport_enabled,
            )

        persistent_hit = False
        persistent_key = None
        if self._persistent_cache is None:
            persistent_value = compute()
        else:
            identity = self._persistent_cache.identity(
                self,
                kind="deterministic_one_reflection",
                origin=origin,
                maximum_order=maximum_order,
                transport=all_specular_transport,
            )
            persistent_key = None if identity is None else cache_key(identity)
            persistent_value, persistent_hit = self._persistent_cache.specular(identity, compute)
        suffix_transport = all_specular_transport if persistent_value.suffix_transport_enabled else None
        value = (
            suffix_transport,
            persistent_value.specular_work,
            persistent_value.paths,
            persistent_value.refinement,
            persistent_value.finite_work,
        )
        self._cache_put(key, (*value, persistent_key))
        seconds = 0.0 if persistent_hit else time.perf_counter() - started
        return *value, seconds, persistent_hit, persistent_hit, persistent_key

    def _deterministic_direct(
        self,
        origin: np.ndarray,
        maximum_order: int,
        field_grid: np.ndarray | None,
    ) -> tuple[
        np.ndarray,
        np.ndarray,
        tuple[np.ndarray, np.ndarray, np.ndarray, float, float] | None,
        float,
        bool,
        bool,
        str | None,
    ]:
        """Resolve exact direct work through memory and optional disk caches."""
        key = self._deterministic_key("direct", origin, maximum_order, field_grid is not None)
        cached = self._cache_get(key)
        if cached is not None:
            direct, seen, field_data, persistent_key = cached
            return direct, seen, field_data, 0.0, True, False, persistent_key

        direct_seconds = 0.0

        def compute() -> DirectCacheValue:
            nonlocal direct_seconds
            started = time.perf_counter()
            if field_grid is None:
                direct, seen = direct_from_sites(
                    self.geometry,
                    np.atleast_2d(origin),
                    self.sources.sites(),
                    weights=getattr(self.sources, "source_weights", None),
                )
                field_data = None
            else:
                direct_mass, direct_k_hat, direct_atom_mass, direct_value, seen_value = _direct_field_data(
                    self.geometry,
                    np.asarray(origin, dtype=np.float64),
                    self.sources,
                    field_grid,
                )
                direct = np.array([direct_value], dtype=np.float64)
                seen = np.array([seen_value], dtype=np.float64)
                field_data = (direct_mass, direct_k_hat, direct_atom_mass, direct_value, seen_value)
            direct_seconds = time.perf_counter() - started
            return DirectCacheValue(direct, seen, field_data)

        persistent_hit = False
        persistent_key = None
        if self._persistent_cache is None:
            value = compute()
        else:
            identity = self._persistent_cache.identity(
                self,
                kind="exact_direct",
                origin=origin,
                maximum_order=maximum_order,
                field_grid=field_grid,
            )
            persistent_key = None if identity is None else cache_key(identity)
            value, persistent_hit = self._persistent_cache.direct(
                identity,
                compute,
                field_cells=None if field_grid is None else field_grid.shape[0],
            )
        cached_value = (value.direct, value.seen, value.field_data, persistent_key)
        self._cache_put(key, cached_value)
        return (
            value.direct,
            value.seen,
            value.field_data,
            direct_seconds,
            persistent_hit,
            persistent_hit,
            persistent_key,
        )

    def _estimate_device(
        self,
        origin: np.ndarray,
        *,
        ground_z_m: float,
        seed: int | None,
        field_grid: np.ndarray | None,
    ) -> tuple[
        Surplus,
        DeviceNextEventGather,
        tuple[np.ndarray, np.ndarray, np.ndarray, float, float] | None,
        SpecularPaths | None,
        list[dict[str, Any]],
    ]:
        """Run resident diffuse and sampled mixed connections with exact direct paths."""
        sampled_mode = self.specular_order == 1 and self.specular_suffix_mode == "sampled"
        first_interaction = self.transport_topology == "first_material_interaction_v1"
        if self.specular_order != 0 and not (sampled_mode or first_interaction):
            raise NotImplementedError(
                "resident device next-event estimation supports specular_order=0 or the "
                "full-support sampled order-one suffix"
            )
        estimator_started = time.perf_counter()
        maximum_order = self.tracer.config.max_bounces if self.max_order is None else self.max_order
        (
            _suffix_transport,
            specular_work,
            all_specular,
            source_refinement,
            finite_resolution_work,
            deterministic_specular_seconds,
            deterministic_specular_cache_hit,
            deterministic_specular_persistent_cache_hit,
            deterministic_specular_persistent_cache_key,
        ) = self._deterministic_specular(origin, maximum_order)

        direct, seen, field_data, direct_seconds, direct_cache_hit, direct_persistent_cache_hit, direct_cache_key = (
            self._deterministic_direct(origin, maximum_order, field_grid)
        )

        gather = DeviceNextEventGather(
            sources=self.sources,
            samples=self.samples,
            max_order=maximum_order,
            seed_offset=self.gather_seed_offset,
            lift_m=self.connection_lift_m,
            min_connect_m=MIN_CONNECT_M,
            specular_suffix_order=int(sampled_mode),
            sampled_specular_samples=self.sampled_specular_samples,
            sampled_specular_seed_offset=self.sampled_specular_seed_offset,
            collect_field=field_grid is not None,
            specular_face_proposal=self._device_specular_face_proposal,
            first_material_interaction_only=first_interaction,
        )
        trace_started = time.perf_counter()
        point = self.tracer.trace(
            origin,
            dict(self.diagnostic_models),
            ground_z_m=ground_z_m,
            seed=seed,
            next_event=gather,
        )
        stochastic_trace_seconds = time.perf_counter() - trace_started
        diffuse_zero_suffix = gather.chi_bounce()
        mixed_specular = gather.chi_specular_suffix() if sampled_mode else 0.0
        all_specular_total = 0.0 if all_specular is None else all_specular.total
        bounced = diffuse_zero_suffix + mixed_specular + all_specular_total
        by_order = gather.chi_by_order() + gather.chi_specular_suffix_by_order()
        if all_specular is not None and by_order.size > 1:
            by_order[1] += all_specular_total
        all_diagnostics = None if all_specular is None else all_specular.diagnostics.as_dict()
        all_specular_complete = bool(all_specular is not None and all_specular.diagnostics.candidate_support_complete)
        if source_refinement:
            all_specular_complete &= bool(source_refinement[-1]["source_support_complete"])
        sampled_diagnostics = gather.sampled_specular_diagnostics()
        sampled_identity = sampled_diagnostics.get("sampling_identity", {})
        sampled_active = bool(sampled_mode and maximum_order >= 2 and sampled_diagnostics.get("enabled", False))
        sampled_full_support = bool(
            sampled_active
            and sampled_identity.get("surface_support_complete", False)
            and sampled_identity.get("source_support", 0) == sampled_identity.get("source_count", -1)
        )
        finite_resolution = bool(source_refinement)
        if sampled_active and finite_resolution:
            estimate_kind = "adaptive_all_sampled_mixed_order_1"
        elif sampled_active:
            estimate_kind = "exact_all_sampled_mixed_order_1"
        elif all_specular is not None:
            estimate_kind = "finite_resolution_order_1" if finite_resolution else "exact_order_1"
        else:
            estimate_kind = "absent"
        specular_reason = "resident device diffuse run explicitly selected specular_order=0"
        specular_work_detail = (
            {"enabled": False, "reason": specular_reason} if specular_work is None else specular_work.as_dict()
        )
        detail = {
            "bounced": bounced,
            "by_order": [float(value) for value in by_order],
            "visible_fraction": float(seen[0]),
            "sky_fraction": point.sky_fraction,
            "mean_bounces": point.mean_bounces,
            "escape_chi": {name: point.susceptibility[name] for name in self.diagnostic_models},
            "escape_chi_direct": {name: point.susceptibility_direct[name] for name in self.diagnostic_models},
            "connections": gather.connections,
            "clear_fraction": gather.cleared / max(gather.connections, 1),
            "deterministic_specular_seconds": deterministic_specular_seconds,
            "direct_seconds": direct_seconds,
            "stochastic_trace_seconds": stochastic_trace_seconds,
            "deterministic_specular_cache_hit": deterministic_specular_cache_hit,
            "direct_cache_hit": direct_cache_hit,
            "specular_suffix_seconds_in_stochastic_trace": 0.0,
            "specular_diagnostic_seconds_reused": False,
            "diffuse_zero_specular_suffix": diffuse_zero_suffix,
            "all_specular_order_1": all_specular_total,
            "mixed_specular_suffix_order_1": mixed_specular,
            "maximum_completed_all_specular_order": int(all_specular_complete),
            "maximum_completed_specular_suffix_order": 0,
            "all_specular_order_1_included": all_specular is not None,
            "mixed_specular_suffix_order_1_included": sampled_active,
            "all_specular_order_1_missing": not all_specular_complete,
            "mixed_specular_suffix_order_1_missing": not sampled_full_support,
            "higher_specular_orders_missing": True,
            "specular_work": specular_work_detail,
            "finite_resolution_specular_work": finite_resolution_work,
            "specular_estimate_kind": estimate_kind,
            "finite_resolution_specular_estimate": finite_resolution,
            "specular_numerically_converged": bool(
                finite_resolution_work and finite_resolution_work.get("numerically_converged", False)
            ),
            "specular_bounce_cap": maximum_order,
            "specular_order_one_complete": False,
            "specular_complete_through_bounce_cap": False,
            "specular_result_complete": False,
            "specular_source_refinement": source_refinement,
            "all_specular_diagnostics": all_diagnostics,
            "specular_suffix_candidates": gather.specular_candidates,
            "specular_suffix_accepted": gather.specular_accepted,
            "specular_suffix_seconds": 0.0,
            "sampled_specular_suffix_full_support": sampled_full_support,
            "sampled_specular_suffix": sampled_diagnostics,
            "transport_kernel": "drjit_resident_next_event",
            "device_next_event": gather.as_dict(),
            "direct_evaluation": "exact_host_source_visibility_and_atoms",
            "timing_note": (
                "top-level timing components are disjoint; direct source visibility runs on the host-facing "
                "geometry API while diffuse and sampled mixed source connections stay resident in the device trace"
            ),
            "timing_components_non_overlapping": [
                "deterministic_specular_seconds",
                "direct_seconds",
                "stochastic_trace_seconds",
                "estimator_overhead_seconds",
            ],
        }
        if first_interaction:
            detail["transport_topology"] = self.transport_topology
            detail["first_material_interaction_nee_only"] = True
        if self._persistent_cache is not None:
            detail["deterministic_specular_persistent_cache_hit"] = deterministic_specular_persistent_cache_hit
            detail["direct_persistent_cache_hit"] = direct_persistent_cache_hit
            detail["persistent_transport_cache"] = {
                "schema": CACHE_SCHEMA,
                "deterministic_specular_key_sha256": deterministic_specular_persistent_cache_key,
                "direct_key_sha256": direct_cache_key,
            }
        surplus = Surplus(
            estimator=self.name,
            law=self.sources.law,
            direct=float(direct[0]),
            total=float(direct[0]) + bounced,
            detail=detail,
        )
        if getattr(self.sources, "curve", None) is not None and getattr(self.sources, "crop_area_m2", None) is not None:
            surplus.detail["per_density_eirp_transfer"] = float(self.sources.per_density_eirp_transfer(surplus.total))
            if (
                getattr(self.sources, "physical_expected_count", None) is not None
                and getattr(self.sources, "eirp_w", None) is not None
            ):
                surplus.detail["physical_transfer_w_m2"] = float(self.sources.physical_transfer(surplus.total))
        estimator_wall_seconds = time.perf_counter() - estimator_started
        measured_components = deterministic_specular_seconds + direct_seconds + stochastic_trace_seconds
        surplus.detail["estimator_wall_seconds"] = estimator_wall_seconds
        surplus.detail["estimator_overhead_seconds"] = max(estimator_wall_seconds - measured_components, 0.0)
        return surplus, gather, field_data, all_specular, source_refinement

    def _estimate_and_gather(
        self,
        origin: np.ndarray,
        *,
        ground_z_m: float,
        seed: int | None,
        field_grid: np.ndarray | None,
    ) -> tuple[
        Surplus,
        NextEventGather | DeviceNextEventGather,
        tuple[np.ndarray, np.ndarray, np.ndarray, float, float] | None,
        SpecularPaths | None,
        list[dict[str, Any]],
    ]:
        if isinstance(self.tracer, DeviceEscapeTracer):
            return self._estimate_device(
                origin,
                ground_z_m=ground_z_m,
                seed=seed,
                field_grid=field_grid,
            )
        estimator_started = time.perf_counter()
        trace_seed = self.tracer.config.seed if seed is None else seed
        maximum_order = self.tracer.config.max_bounces if self.max_order is None else self.max_order
        (
            suffix_transport,
            specular_work,
            all_specular,
            source_refinement,
            finite_resolution_work,
            deterministic_specular_seconds,
            deterministic_specular_cache_hit,
            deterministic_specular_persistent_cache_hit,
            deterministic_specular_persistent_cache_key,
        ) = self._deterministic_specular(origin, maximum_order)

        sampled_suffix = None
        if self.specular_suffix_mode == "sampled" and self.specular_order == 1:
            sampled_transport = self.specular_transport
            if sampled_transport is None and hasattr(self.tracer, "_surface_response"):
                sampled_transport = self._automatic_specular_transport()
            if sampled_transport is not None:
                sampled_suffix = SampledOneBounceSpecularEstimator(sampled_transport, self.sources)

        direct, seen, field_data, direct_seconds, direct_cache_hit, direct_persistent_cache_hit, direct_cache_key = (
            self._deterministic_direct(origin, maximum_order, field_grid)
        )
        gather = NextEventGather(
            geometry=self.geometry,
            sources=self.sources,
            rng=np.random.default_rng(trace_seed + self.gather_seed_offset),
            samples=self.samples,
            max_order=maximum_order,
            lift_m=self.connection_lift_m,
            field_grid=field_grid,
            specular_transport=suffix_transport if self.specular_suffix_mode == "exact" else None,
            specular_work=specular_work,
            sampled_specular_estimator=sampled_suffix,
            sampled_specular_samples=self.sampled_specular_samples,
            sampled_specular_seed=(trace_seed + self.sampled_specular_seed_offset) & ((1 << 64) - 1),
            first_material_interaction_only=self.transport_topology == "first_material_interaction_v1",
        )
        trace_started = time.perf_counter()
        point = self.tracer.trace(
            origin,
            dict(self.diagnostic_models),
            ground_z_m=ground_z_m,
            seed=seed,
            gather=gather,
        )
        stochastic_trace_seconds = time.perf_counter() - trace_started
        diffuse_zero_suffix = gather.chi_bounce()
        mixed_specular = gather.chi_specular_suffix()
        all_specular_total = 0.0 if all_specular is None else all_specular.total
        bounced = diffuse_zero_suffix + mixed_specular + all_specular_total
        by_order = gather.chi_by_order() + gather.chi_specular_suffix_by_order()
        if all_specular is not None and by_order.size > 1:
            by_order[1] += all_specular_total
        all_diagnostics = None if all_specular is None else all_specular.diagnostics.as_dict()
        detail = {
            "bounced": bounced,
            "by_order": [float(value) for value in by_order],
            "visible_fraction": float(seen[0]),
            "sky_fraction": point.sky_fraction,
            "mean_bounces": point.mean_bounces,
            "escape_chi": {name: point.susceptibility[name] for name in self.diagnostic_models},
            "escape_chi_direct": {name: point.susceptibility_direct[name] for name in self.diagnostic_models},
            "connections": gather.connections,
            "clear_fraction": gather.cleared / max(gather.connections, 1),
            "deterministic_specular_seconds": deterministic_specular_seconds,
            "direct_seconds": direct_seconds,
            "stochastic_trace_seconds": stochastic_trace_seconds,
            "deterministic_specular_cache_hit": deterministic_specular_cache_hit,
            "direct_cache_hit": direct_cache_hit,
            "specular_suffix_seconds_in_stochastic_trace": gather.specular_seconds,
            "specular_diagnostic_seconds_reused": bool(
                deterministic_specular_cache_hit and not deterministic_specular_persistent_cache_hit
            ),
            "timing_note": (
                "top-level timing components are disjoint; suffix timing is contained in stochastic trace, "
                "and cached candidate/path diagnostics describe their original computation"
            ),
            "timing_components_non_overlapping": [
                "deterministic_specular_seconds",
                "direct_seconds",
                "stochastic_trace_seconds",
                "estimator_overhead_seconds",
            ],
            "specular_bounce_cap": maximum_order,
            "specular_order_one_complete": False,
            "specular_complete_through_bounce_cap": False,
            "specular_result_complete": False,
        }
        if self.transport_topology == "first_material_interaction_v1":
            detail["transport_topology"] = self.transport_topology
            detail["first_material_interaction_nee_only"] = True
        if self._persistent_cache is not None:
            detail["deterministic_specular_persistent_cache_hit"] = deterministic_specular_persistent_cache_hit
            detail["direct_persistent_cache_hit"] = direct_persistent_cache_hit
            detail["persistent_transport_cache"] = {
                "schema": CACHE_SCHEMA,
                "deterministic_specular_key_sha256": deterministic_specular_persistent_cache_key,
                "direct_key_sha256": direct_cache_key,
            }
        if specular_work is not None:
            sampled_suffix_active = bool(sampled_suffix is not None and sampled_suffix.ready and maximum_order >= 2)
            all_specular_complete = bool(
                all_specular is not None and all_specular.diagnostics.candidate_support_complete
            )
            if source_refinement:
                all_specular_complete &= bool(source_refinement[-1]["source_support_complete"])
            suffix_complete = bool(suffix_transport is not None and suffix_transport.surfaces.support_complete)
            sampled_suffix_diagnostics = gather.sampled_specular_diagnostics()
            sampled_suffix_full_support = bool(
                sampled_suffix_active
                and sampled_suffix_diagnostics.get("enabled", False)
                and sampled_suffix_diagnostics.get("sampling_identity", {}).get("surface_support_complete", False)
                and sampled_suffix_diagnostics.get("sampling_identity", {}).get("source_support", 0)
                == sampled_suffix_diagnostics.get("sampling_identity", {}).get("source_count", -1)
            )
            order_one_complete = bool(all_specular_complete and suffix_complete and not source_refinement)
            through_bounce_cap = bool(order_one_complete and maximum_order == 1)
            detail.update(
                {
                    "diffuse_zero_specular_suffix": diffuse_zero_suffix,
                    "all_specular_order_1": all_specular_total,
                    "mixed_specular_suffix_order_1": mixed_specular,
                    "maximum_completed_all_specular_order": int(all_specular_complete),
                    "maximum_completed_specular_suffix_order": int(suffix_complete),
                    "all_specular_order_1_included": all_specular is not None,
                    "mixed_specular_suffix_order_1_included": suffix_transport is not None or sampled_suffix_active,
                    "all_specular_order_1_missing": not all_specular_complete,
                    "mixed_specular_suffix_order_1_missing": not (suffix_complete or sampled_suffix_full_support),
                    "higher_specular_orders_missing": True,
                    "specular_work": specular_work.as_dict(),
                    "finite_resolution_specular_work": finite_resolution_work,
                    "specular_estimate_kind": (
                        "adaptive_all_sampled_mixed_order_1"
                        if sampled_suffix_active and source_refinement
                        else (
                            "exact_all_sampled_mixed_order_1"
                            if sampled_suffix_active
                            else (
                                "finite_resolution_order_1"
                                if source_refinement
                                else (
                                    "exact_order_1"
                                    if all_specular is not None or suffix_transport is not None
                                    else "absent"
                                )
                            )
                        )
                    ),
                    "finite_resolution_specular_estimate": bool(source_refinement),
                    "specular_numerically_converged": bool(
                        finite_resolution_work and finite_resolution_work.get("numerically_converged", False)
                    ),
                    "specular_order_one_complete": order_one_complete,
                    "specular_complete_through_bounce_cap": through_bounce_cap,
                    "specular_result_complete": through_bounce_cap,
                    "specular_source_refinement": source_refinement,
                    "all_specular_diagnostics": all_diagnostics,
                    "specular_suffix_candidates": gather.specular_candidates,
                    "specular_suffix_accepted": gather.specular_accepted,
                    "specular_suffix_seconds": gather.specular_seconds,
                    "sampled_specular_suffix_full_support": sampled_suffix_full_support,
                    "sampled_specular_suffix": sampled_suffix_diagnostics,
                }
            )
        surplus = Surplus(
            estimator=self.name,
            law=self.sources.law,
            direct=float(direct[0]),
            total=float(direct[0]) + bounced,
            detail=detail,
        )
        if getattr(self.sources, "curve", None) is not None and getattr(self.sources, "crop_area_m2", None) is not None:
            surplus.detail["per_density_eirp_transfer"] = float(self.sources.per_density_eirp_transfer(surplus.total))
            if (
                getattr(self.sources, "physical_expected_count", None) is not None
                and getattr(self.sources, "eirp_w", None) is not None
            ):
                surplus.detail["physical_transfer_w_m2"] = float(self.sources.physical_transfer(surplus.total))
        estimator_wall_seconds = time.perf_counter() - estimator_started
        measured_components = deterministic_specular_seconds + direct_seconds + stochastic_trace_seconds
        surplus.detail["estimator_wall_seconds"] = estimator_wall_seconds
        surplus.detail["estimator_overhead_seconds"] = max(estimator_wall_seconds - measured_components, 0.0)
        return surplus, gather, field_data, all_specular, source_refinement
