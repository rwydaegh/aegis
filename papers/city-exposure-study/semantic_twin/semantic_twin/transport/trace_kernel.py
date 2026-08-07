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


LAUNCH_SAMPLING_MODES = ("iid", "rotated_fibonacci")

# The golden angle represented as an exact uint32 Weyl increment. Keeping the
# phase in integer arithmetic avoids the loss of angular precision that a
# float32 device index would otherwise suffer after a few hundred thousand
# rays. The quantisation is below 1.5e-9 radians per increment.
_GOLDEN_ANGLE_UINT32 = np.uint64(0x61C88647)
_UINT32_TO_RADIANS = 2.0 * np.pi / float(1 << 32)


def launch_rotation(seed: int) -> np.ndarray:
    """Return one Haar-uniform SO(3) rotation determined only by ``seed``.

    Shoemake's three-uniform quaternion construction makes every rotation
    equally likely. The generator is separate from the transport generator, so
    selecting this launch rule does not consume or reorder diffuse-bounce draws.
    """
    seed_value = int(seed) & 0xFFFFFFFFFFFFFFFF
    u1, u2, u3 = np.random.Generator(np.random.PCG64(seed_value)).random(3)
    root_one = np.sqrt(1.0 - u1)
    root_u = np.sqrt(u1)
    x = root_one * np.sin(2.0 * np.pi * u2)
    y = root_one * np.cos(2.0 * np.pi * u2)
    z = root_u * np.sin(2.0 * np.pi * u3)
    w = root_u * np.cos(2.0 * np.pi * u3)
    return np.array(
        [
            [1.0 - 2.0 * (y * y + z * z), 2.0 * (x * y - z * w), 2.0 * (x * z + y * w)],
            [2.0 * (x * y + z * w), 1.0 - 2.0 * (x * x + z * z), 2.0 * (y * z - x * w)],
            [2.0 * (x * z - y * w), 2.0 * (y * z + x * w), 1.0 - 2.0 * (x * x + y * y)],
        ],
        dtype=np.float64,
    )


def rotated_fibonacci_sphere(indices: np.ndarray, total: int, seed: int) -> np.ndarray:
    """Return globally indexed Fibonacci launch directions for one replica.

    The fixed ``total``-point lattice is randomly rotated once per seed. For
    every lattice point, a Haar-uniform rotation makes its marginal direction
    uniform on the sphere. Therefore the mean over replicas is an unbiased
    sphere integral, while each replica is much more even than IID launching.
    """
    raw = np.asarray(indices)
    if raw.ndim != 1 or not np.issubdtype(raw.dtype, np.integer):
        raise ValueError("launch indices must be a one-dimensional integer array")
    if total < 1:
        raise ValueError("total launch rays must be positive")
    if raw.size and (np.any(raw < 0) or np.any(raw >= total)):
        raise ValueError("launch indices must lie inside the complete Fibonacci lattice")
    index = raw.astype(np.uint64, copy=False)
    z = 1.0 - (2.0 * index.astype(np.float64) + 1.0) / float(total)
    phase = (index * _GOLDEN_ANGLE_UINT32) & np.uint64(0xFFFFFFFF)
    theta = phase.astype(np.float64) * _UINT32_TO_RADIANS
    radius = np.sqrt(np.maximum(0.0, 1.0 - z * z))
    base = np.column_stack((radius * np.cos(theta), radius * np.sin(theta), z))
    return base @ launch_rotation(seed).T


def launch_directions(
    count: int,
    rng: np.random.Generator,
    *,
    mode: str,
    ray_start: int,
    total: int,
    seed: int,
) -> np.ndarray:
    """Generate one launch range without changing the established IID path."""
    if mode == "iid":
        return sample_sphere(count, rng)
    if mode == "rotated_fibonacci":
        stop = ray_start + count
        return rotated_fibonacci_sphere(np.arange(ray_start, stop, dtype=np.int64), total, seed)
    raise ValueError(f"launch_sampling must be one of {', '.join(LAUNCH_SAMPLING_MODES)}, got {mode!r}")


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
        *,
        launch_sampling: str,
        ray_start: int,
        total_rays: int,
        seed: int,
    ) -> BatchState:
        direction = launch_directions(
            count,
            rng,
            mode=launch_sampling,
            ray_start=ray_start,
            total=total_rays,
            seed=seed,
        )
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
    reflectance, share, nonblocking = tracer._surface_response(cos_i, klass, hit.face, position)
    if np.any(nonblocking):
        raise AssertionError("non-blocking hits must be removed before surface interaction")

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


def _slice_intersection(hit: Intersection, keep: np.ndarray) -> Intersection:
    """Select hit rows without changing their original ray order."""
    return Intersection(
        hit.index[keep],
        hit.position[keep],
        hit.direction[keep],
        hit.throughput[keep],
        hit.bounces[keep],
        hit.hit[keep],
        hit.distance[keep],
        hit.normal[keep],
        hit.face[keep] if hit.face is not None else None,
    )


def partition_nonblocking_hits(
    tracer: Any,
    state: BatchState,
    hit: Intersection,
) -> tuple[Intersection, np.ndarray]:
    """Advance false canopy surfaces and return the blocking hit subset.

    A non-blocking cell is image evidence for a woody volume on geometry that
    is not a registered canopy boundary. The ray crosses it in the same
    direction with the same power and bounce count. The travelled distance is
    still physical path length. Repeated intersections are resolved inside the
    same bounce slot by :func:`run_batch`.
    """
    if hit.index.size == 0:
        return hit, np.zeros(0, dtype=np.int64)
    position = hit.position + (hit.distance + tracer.config.ray_epsilon_m)[:, None] * hit.direction
    nonblocking = tracer._surface_nonblocking(hit.face, position)
    if nonblocking.shape != (hit.index.size,):
        raise ValueError("surface non-blocking state must have one value per hit")
    pass_index = hit.index[nonblocking]
    if pass_index.size:
        state.position[pass_index] = position[nonblocking]
        state.path_length[pass_index] += hit.distance[nonblocking]
        state.last_vertex[pass_index] = position[nonblocking]
    return _slice_intersection(hit, ~nonblocking), pass_index


def _nonblocking_crossing_limit(tracer: Any) -> int:
    """Bound straight-line canopy crossings by the support-mesh face count.

    A ray that only advances cannot cross one triangle more than once. The
    support mesh therefore gives a conservative hard limit even when every
    face carries a non-blocking atlas cell. Atlas transport already requires
    indexed mesh geometry, but the face-class length remains a useful fallback
    for small test geometries that expose the same contract.
    """
    face_count = getattr(tracer.geometry, "face_count", None)
    if face_count is None and tracer.face_class is not None:
        face_count = tracer.face_class.size
    if face_count is None or int(face_count) < 1:
        raise RuntimeError(
            "non-blocking canopy transport needs a positive support-mesh face count to bound pass-through intersections"
        )
    return int(face_count)


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
    *,
    ray_start: int = 0,
    seed: int | None = None,
) -> None:
    """Run one batch through the ordered trace phases."""
    state = BatchState.begin(
        origin,
        count,
        rng,
        tracer.local_grid,
        accumulators.cell_counts,
        launch_sampling=tracer.config.launch_sampling,
        ray_start=ray_start,
        total_rays=tracer.config.rays,
        seed=tracer.config.seed if seed is None else seed,
    )
    if observers.recorder is not None:
        observers.recorder.begin(origin, count)
    if observers.gather is not None:
        observers.gather.begin(origin, count)
        set_launch_cells = getattr(observers.gather, "set_launch_cells", None)
        if set_launch_cells is not None:
            set_launch_cells(state.cell)

    for depth in range(tracer.config.max_bounces + 1):
        if state.alive.size == 0:
            break
        searching = state.alive
        reflected: list[np.ndarray] = []
        canopy_crossings = 0
        crossing_limit: int | None = None
        while searching.size:
            state.alive = searching
            intersection = intersect_live(state, tracer.geometry, tracer.config.ray_epsilon_m)
            deposit_escapes(tracer, origin, state, intersection, models, accumulators, observers.recorder)
            hit = select_surface_hits(state, intersection)
            if state.alive.size == 0:
                break
            blocking, searching = partition_nonblocking_hits(tracer, state, hit)
            if searching.size:
                canopy_crossings += 1
                if crossing_limit is None:
                    crossing_limit = _nonblocking_crossing_limit(tracer)
                if canopy_crossings > crossing_limit:
                    raise RuntimeError(
                        f"{searching.size} rays exceeded the support-mesh face count "
                        f"({crossing_limit}) while crossing non-blocking canopy cells at bounce {depth}; "
                        "the mesh likely contains a repeated self-intersection"
                    )
            if blocking.index.size == 0:
                continue
            state.alive = blocking.index
            if depth == tracer.config.max_bounces:
                truncate_hits(state, blocking, accumulators.totals, observers.recorder)
                continue
            interaction = interact_with_surface(tracer, depth, state, blocking, rng, observers)
            if depth + 1 >= tracer.config.roulette_start:
                apply_roulette(state, interaction, rng, tracer.config.roulette_floor, observers.recorder)
            reflected.append(state.alive.copy())
        state.alive = np.sort(np.concatenate(reflected), kind="stable") if reflected else np.zeros(0, dtype=np.int64)


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
