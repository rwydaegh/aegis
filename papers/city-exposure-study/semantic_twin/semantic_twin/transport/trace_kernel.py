"""State and small phases for one adjoint ray-tracing batch.

The public tracer owns configuration and result construction. This module owns
the inner loop. Its phases follow the estimator in order: intersect, deposit
escapes, update a surface interaction, then apply roulette.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from ..illumination import IlluminationModel, nearest_cell, sample_sphere
from .observers import BounceEvidenceTally, PathRecorder


def _cross(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Evaluate ``np.cross`` for rows in the same arithmetic order."""
    out = np.empty(a.shape, dtype=np.float64)
    a0, a1, a2 = a[:, 0], a[:, 1], a[:, 2]
    b0, b1, b2 = b[:, 0], b[:, 1], b[:, 2]
    np.multiply(a1, b2, out=out[:, 0])
    out[:, 0] -= a2 * b1
    np.multiply(a2, b0, out=out[:, 1])
    out[:, 1] -= a0 * b2
    np.multiply(a0, b1, out=out[:, 2])
    out[:, 2] -= a1 * b0
    return out


def _row_norms(a: np.ndarray) -> np.ndarray:
    """Evaluate row norms in the same summation order as the original kernel."""
    total = a[:, 0] * a[:, 0]
    total = total + a[:, 1] * a[:, 1]
    total = total + a[:, 2] * a[:, 2]
    return np.sqrt(total)[:, None]


_UP = np.array([[0.0, 0.0, 1.0]])
_ACROSS = np.array([[1.0, 0.0, 0.0]])
_ROW_DOT = "ij,ij->i"


def _cosine_hemisphere(normals: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Draw cosine-weighted directions about every normal."""
    count = normals.shape[0]
    u1 = rng.random(count)
    u2 = rng.random(count)
    radius = np.sqrt(u1)
    phi = 2.0 * np.pi * u2
    x = radius * np.cos(phi)
    y = radius * np.sin(phi)
    z = np.sqrt(np.maximum(0.0, 1.0 - u1))
    helper = np.where(np.abs(normals[:, 2:3]) < 0.9, _UP, _ACROSS)
    tangent = _cross(helper, normals)
    tangent /= _row_norms(tangent)
    bitangent = _cross(normals, tangent)
    return x[:, None] * tangent + y[:, None] * bitangent + z[:, None] * normals


@dataclass
class TraceAccumulators:
    """Arrays and scalar totals shared by every batch of one trace."""

    normalisations: dict[str, float]
    rho: dict[str, np.ndarray]
    rho_direct: dict[str, np.ndarray]
    cell_counts: np.ndarray
    exit_power: np.ndarray
    totals: dict[str, float]

    @classmethod
    def create(
        cls,
        models: dict[str, IlluminationModel],
        local_cells: int,
        exit_bands: int,
    ) -> TraceAccumulators:
        return cls(
            normalisations={name: model.normalisation() for name, model in models.items()},
            rho={name: np.zeros(local_cells) for name in models},
            rho_direct={name: np.zeros(local_cells) for name in models},
            cell_counts=np.zeros(local_cells),
            exit_power=np.zeros(exit_bands),
            totals={
                "escaped": 0,
                "bounce_sum": 0.0,
                "delay_sum": 0.0,
                "delay_weight": 0.0,
                "zero_bounce": 0,
                "truncated": 0,
                "truncated_throughput": 0.0,
            },
        )


@dataclass(frozen=True)
class BatchObservers:
    """Passive callbacks attached to a batch."""

    recorder: PathRecorder | None = None
    tally: BounceEvidenceTally | None = None
    gather: Any = None


@dataclass
class BatchState:
    """Full per-ray state, kept in original ray-index order."""

    direction: np.ndarray
    cell: np.ndarray
    position: np.ndarray
    throughput: np.ndarray
    path_length: np.ndarray
    last_vertex: np.ndarray
    bounces: np.ndarray
    alive: np.ndarray

    @classmethod
    def begin(
        cls,
        origin: np.ndarray,
        count: int,
        rng: np.random.Generator,
        local_grid: np.ndarray,
        cell_counts: np.ndarray,
    ) -> BatchState:
        direction = sample_sphere(count, rng)
        cell = nearest_cell(direction, local_grid)
        np.add.at(cell_counts, cell, 1.0)
        position = np.tile(np.asarray(origin, dtype=np.float64), (count, 1))
        return cls(
            direction=direction,
            cell=cell,
            position=position,
            throughput=np.ones(count),
            path_length=np.zeros(count),
            last_vertex=position.copy(),
            bounces=np.zeros(count, dtype=np.int32),
            alive=np.arange(count),
        )


@dataclass(frozen=True)
class Intersection:
    """One gathered live slice and its geometry query."""

    index: np.ndarray
    position: np.ndarray
    direction: np.ndarray
    throughput: np.ndarray
    bounces: np.ndarray
    hit: np.ndarray
    distance: np.ndarray
    normal: np.ndarray
    face: np.ndarray | None


@dataclass(frozen=True)
class SurfaceInteraction:
    """The hit-only slice after its material response was applied."""

    index: np.ndarray
    position: np.ndarray
    incoming: np.ndarray
    normal: np.ndarray
    throughput: np.ndarray
    bounces: np.ndarray
    face: np.ndarray | None
    share: np.ndarray
    new_direction: np.ndarray


@dataclass(frozen=True)
class EscapeDeposit:
    """One escaped slice and the state needed to reduce it."""

    index: np.ndarray
    direction: np.ndarray
    throughput: np.ndarray
    cell: np.ndarray
    path_length: np.ndarray
    last_vertex: np.ndarray
    origin: np.ndarray
    bounces: np.ndarray


def intersect_live(state: BatchState, geometry: Any, ray_epsilon_m: float) -> Intersection:
    """Gather live rays once and intersect them in their current order."""
    index = state.alive
    position = state.position[index]
    direction = state.direction[index]
    throughput = state.throughput[index]
    bounces = state.bounces[index]
    hit, distance, normal, face = geometry.intersect(position + ray_epsilon_m * direction, direction)
    return Intersection(index, position, direction, throughput, bounces, hit, distance, normal, face)


def deposit_escapes(
    tracer: Any,
    origin: np.ndarray,
    state: BatchState,
    intersection: Intersection,
    models: dict[str, IlluminationModel],
    accumulators: TraceAccumulators,
    recorder: PathRecorder | None,
) -> None:
    """Deposit every miss before narrowing the live slice to hits."""
    escaped = ~intersection.hit
    if not np.any(escaped):
        return
    index = intersection.index[escaped]
    tracer._deposit(
        index,
        intersection.direction[escaped],
        intersection.throughput[escaped],
        state.cell[index],
        state.path_length[index],
        state.last_vertex[index],
        np.asarray(origin, dtype=np.float64),
        intersection.bounces[escaped],
        models,
        accumulators.normalisations,
        accumulators.rho,
        accumulators.rho_direct,
        accumulators.exit_power,
        accumulators.totals,
    )
    if recorder is not None:
        recorder.close(
            index,
            intersection.position[escaped],
            intersection.direction[escaped],
            intersection.bounces[escaped],
            "sky",
        )


def select_surface_hits(state: BatchState, intersection: Intersection) -> Intersection:
    """Keep hit rays in their prior live order."""
    hit = intersection.hit
    state.alive = intersection.index[hit]
    return Intersection(
        state.alive,
        intersection.position[hit],
        intersection.direction[hit],
        intersection.throughput[hit],
        intersection.bounces[hit],
        np.ones(state.alive.size, dtype=bool),
        intersection.distance[hit],
        intersection.normal[hit],
        intersection.face[hit] if intersection.face is not None else None,
    )


def truncate_hits(
    state: BatchState,
    intersection: Intersection,
    totals: dict[str, float],
    recorder: PathRecorder | None,
) -> None:
    """Drop rays still travelling at the hard bounce cap."""
    totals["truncated"] += int(state.alive.size)
    totals["truncated_throughput"] += float(intersection.throughput.sum())
    if recorder is not None:
        recorder.close(
            state.alive,
            intersection.position,
            intersection.direction,
            intersection.bounces,
            "truncated",
        )


def interact_with_surface(
    tracer: Any,
    depth: int,
    state: BatchState,
    hit: Intersection,
    rng: np.random.Generator,
    observers: BatchObservers,
) -> SurfaceInteraction:
    """Advance hit points, apply material response, and choose reflection directions."""
    cfg = tracer.config
    position = hit.position + (hit.distance + cfg.ray_epsilon_m)[:, None] * hit.direction
    state.position[state.alive] = position
    state.path_length[state.alive] += hit.distance
    state.last_vertex[state.alive] = position
    bounces = hit.bounces
    bounces += 1
    state.bounces[state.alive] = bounces

    incoming = hit.direction
    facing = np.sign(-np.einsum(_ROW_DOT, incoming, hit.normal))
    facing[np.equal(facing, 0.0)] = 1.0
    normal = hit.normal * facing[:, None]
    cos_i = np.clip(-np.einsum(_ROW_DOT, incoming, normal), 0.0, 1.0)
    if tracer.face_class is not None and hit.face is not None:
        klass = tracer.face_class[hit.face]
    else:
        klass = np.zeros(state.alive.size, dtype=np.int64)
    reflectance = tracer._fresnel_power_reflectance(cos_i, tracer.permittivity[klass])
    share = tracer._specular_share(tracer.rms_height_m[klass], cos_i)

    if observers.tally is not None and hit.face is not None:
        observers.tally.record(depth, hit.face, hit.throughput)
    throughput = hit.throughput * reflectance
    state.throughput[state.alive] = throughput
    if observers.recorder is not None:
        observers.recorder.advance(state.alive, position, throughput, klass)
    if observers.gather is not None:
        observers.gather.vertex(
            state.alive,
            position,
            incoming,
            normal,
            throughput,
            share,
            bounces,
            state.path_length[state.alive],
            hit.face,
        )

    take_specular = rng.random(state.alive.size) < share
    mirror = incoming - 2.0 * np.einsum(_ROW_DOT, incoming, normal)[:, None] * normal
    diffuse = _cosine_hemisphere(normal, rng)
    new_direction = np.where(take_specular[:, None], mirror, diffuse)
    new_direction /= _row_norms(new_direction)
    state.direction[state.alive] = new_direction
    return SurfaceInteraction(
        state.alive, position, incoming, normal, throughput, bounces, hit.face, share, new_direction
    )


def apply_roulette(
    state: BatchState,
    interaction: SurfaceInteraction,
    rng: np.random.Generator,
    roulette_floor: float,
    recorder: PathRecorder | None,
) -> None:
    """Apply roulette without changing the order of surviving ray indices."""
    survive_probability = np.clip(interaction.throughput, roulette_floor, 1.0)
    survive = rng.random(state.alive.size) < survive_probability
    state.throughput[state.alive] = interaction.throughput / survive_probability
    if recorder is not None:
        killed = state.alive[~survive]
        recorder.close(
            killed,
            state.position[killed],
            interaction.new_direction[~survive],
            interaction.bounces[~survive],
            "roulette",
        )
    state.alive = state.alive[survive]


def run_batch(
    tracer: Any,
    origin: np.ndarray,
    count: int,
    rng: np.random.Generator,
    models: dict[str, IlluminationModel],
    accumulators: TraceAccumulators,
    observers: BatchObservers,
) -> None:
    """Run one batch through the ordered trace phases."""
    state = BatchState.begin(origin, count, rng, tracer.local_grid, accumulators.cell_counts)
    if observers.recorder is not None:
        observers.recorder.begin(origin, count)
    if observers.gather is not None:
        observers.gather.begin(origin, count)

    for depth in range(tracer.config.max_bounces + 1):
        if state.alive.size == 0:
            break
        intersection = intersect_live(state, tracer.geometry, tracer.config.ray_epsilon_m)
        deposit_escapes(tracer, origin, state, intersection, models, accumulators, observers.recorder)
        hit = select_surface_hits(state, intersection)
        if state.alive.size == 0:
            break
        if depth == tracer.config.max_bounces:
            truncate_hits(state, hit, accumulators.totals, observers.recorder)
            break
        interaction = interact_with_surface(tracer, depth, state, hit, rng, observers)
        if depth + 1 >= tracer.config.roulette_start:
            apply_roulette(state, interaction, rng, tracer.config.roulette_floor, observers.recorder)


def range_to_source_shell(
    last_vertex: np.ndarray,
    exit_direction: np.ndarray,
    path_length: np.ndarray,
    source_shell_radius_m: float,
    ray_epsilon_m: float,
) -> np.ndarray:
    """Return each escaping ray's end-to-end distance to the source shell."""
    along = np.einsum(_ROW_DOT, last_vertex, exit_direction)
    square = np.einsum(_ROW_DOT, last_vertex, last_vertex)
    inside = np.maximum(along**2 - square + source_shell_radius_m**2, 0.0)
    out = np.maximum(-along + np.sqrt(inside), 0.0)
    return np.maximum(path_length + out, ray_epsilon_m)


def deposit(
    tracer: Any,
    escaped: EscapeDeposit,
    models: dict[str, IlluminationModel],
    accumulators: TraceAccumulators,
) -> None:
    """Deposit escaped power into model, elevation, and scalar accumulators."""
    zero_bounce = escaped.bounces == 0
    weight = escaped.throughput
    if tracer.config.range_weighted_escape:
        distance = tracer._range_to_the_source_shell(
            escaped.last_vertex,
            escaped.direction,
            escaped.path_length,
        )
        weight = escaped.throughput / distance**2
    for name, model in models.items():
        contribution = weight * model.density(escaped.direction, accumulators.normalisations[name])
        np.add.at(accumulators.rho[name], escaped.cell, contribution)
        if np.any(zero_bounce):
            np.add.at(
                accumulators.rho_direct[name],
                escaped.cell[zero_bounce],
                contribution[zero_bounce],
            )
    band = np.clip(
        np.searchsorted(tracer.exit_sin_edges, escaped.direction[:, 2], side="right") - 1,
        0,
        accumulators.exit_power.size - 1,
    )
    np.add.at(accumulators.exit_power, band, escaped.throughput)

    excess = escaped.path_length - np.einsum(
        _ROW_DOT,
        escaped.direction,
        escaped.last_vertex - escaped.origin,
    )
    accumulators.totals["escaped"] += int(escaped.index.size)
    accumulators.totals["bounce_sum"] += float(escaped.bounces.sum())
    accumulators.totals["delay_sum"] += float(np.sum(escaped.throughput * excess))
    accumulators.totals["delay_weight"] += float(np.sum(escaped.throughput))
    accumulators.totals["zero_bounce"] += int(np.count_nonzero(zero_bounce))
