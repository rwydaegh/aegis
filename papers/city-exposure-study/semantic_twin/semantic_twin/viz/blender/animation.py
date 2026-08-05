"""Readable frame-by-frame explanations of the stored visual ray trace.

The dense ray fan remains in the file as an overview. This module adds two
small animations beside it. The first ranks the bounded visual-trace samples
under the rooftop angular law and shows one complete sample per frame. The
second shows one stored SBR chain and its roofline visibility connections per
frame.

These frames do not turn the visual trace into a transmitter-to-receiver MPC
decomposition. The production spectrum was computed from a separate, much
larger GPU trace. The stored next-event arrays are also geometry evidence. They
do not contain the factors needed to reconstruct a quantitative NEE deposit.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

import numpy as np

from ...illumination import nearest_cell
from ...illumination.catalogue import ROOFTOP
from .payload import (
    DrawableRayLegs,
    drawable_ray_legs,
    octahedra,
    supported_live_scattering_vertices,
)
from .style import (
    ANIMATION_BLOCKED_CONNECTION_COLOUR,
    ANIMATION_CLEAR_CONNECTION_COLOUR,
    ANIMATION_NEE_CHAIN_COLOUR,
    ANIMATION_PATH_COLOUR,
    ANIMATION_PROXY_COLOUR,
    ANIMATION_SCATTER_COLOUR,
    ANIMATION_SOURCE_COLOUR,
)


@dataclass(frozen=True)
class RankedVisualPaths:
    """Rooftop-law ranking of drawable paths in the bounded visual trace."""

    path_index: np.ndarray
    score: np.ndarray
    final_throughput: np.ndarray
    rooftop_density_per_sr: np.ndarray
    departure_cell: np.ndarray
    departure_cell_count: np.ndarray
    bounces: np.ndarray
    exit_elevation_deg: np.ndarray
    paths_recorded: int
    positive_sky_paths: int
    paths_left_out_beyond_drawn_support: np.ndarray
    score_sum_all_drawable_sky_paths: float


@dataclass(frozen=True)
class _NeeArrays:
    """The stored qualitative roofline-connection arrays."""

    path: np.ndarray
    vertex: np.ndarray
    origin: np.ndarray
    site: np.ndarray
    rim_weight: np.ndarray
    blocked: np.ndarray


def _payload_keys(payload: Any) -> Any:
    return payload.files if hasattr(payload, "files") else payload


def _launch_directions(payload: Any) -> np.ndarray:
    vertices = np.asarray(payload["path_vertices"], dtype=np.float64)
    offsets = np.asarray(payload["path_offsets"], dtype=np.int64)
    starts = vertices[offsets[:-1]]
    first = vertices[offsets[:-1] + 1]
    direction = first - starts
    norm = np.linalg.norm(direction, axis=1)
    if np.any(norm <= 1.0e-12):
        bad = np.flatnonzero(norm <= 1.0e-12)
        raise ValueError(f"recorded paths have no first-leg direction: {bad[:8].tolist()}")
    return direction / norm[:, None]


def rank_rooftop_visual_paths(
    payload: Any,
    terminations: Sequence[str],
    *,
    count: int,
    drawn_radius_m: float,
) -> RankedVisualPaths:
    """Rank drawable sky paths by their exact contribution to the visual retrace.

    For path ``i`` the score is

    ``solid_angle * final_throughput * rooftop_density(exit) / launch_cell_count``.

    This is the same non-range-weighted Monte Carlo deposit and departure-cell
    normalisation used by the escape tracer. It is exact for this bounded visual
    retrace because the payload records every ray cast by that retrace. It is not
    a per-path decomposition of the separate production GPU spectrum.
    """
    if count < 1:
        raise ValueError("animation path count must be positive")
    keys = _payload_keys(payload)
    required = {
        "path_vertices",
        "path_offsets",
        "path_throughput",
        "path_exit_direction",
        "path_termination",
        "path_bounces",
        "local_grid",
    }
    missing = sorted(required.difference(keys))
    if missing:
        raise KeyError(f"path animation payload is missing {', '.join(missing)}")

    offsets = np.asarray(payload["path_offsets"], dtype=np.int64)
    throughput = np.asarray(payload["path_throughput"], dtype=np.float64)
    exit_direction = np.asarray(payload["path_exit_direction"], dtype=np.float64)
    termination = np.asarray(payload["path_termination"], dtype=np.int64)
    bounces = np.asarray(payload["path_bounces"], dtype=np.int64)
    grid = np.asarray(payload["local_grid"], dtype=np.float64)
    paths = offsets.size - 1
    if offsets.shape != (paths + 1,) or exit_direction.shape != (paths, 3):
        raise ValueError("path animation arrays do not share one path count")
    if throughput.shape != (offsets[-1],) or termination.shape != (paths,) or bounces.shape != (paths,):
        raise ValueError("path animation arrays do not match the recorded offsets")

    launch_cell = nearest_cell(_launch_directions(payload), grid)
    cell_count = np.bincount(launch_cell, minlength=grid.shape[0])
    final = throughput[offsets[1:] - 1]
    density = ROOFTOP.density(exit_direction)
    solid_angle = 4.0 * np.pi / grid.shape[0]
    score = solid_angle * final * density / cell_count[launch_cell]

    sky = list(terminations).index("sky")
    positive_sky = (termination == sky) & (score > 0.0) & np.isfinite(score)
    candidates = np.flatnonzero(positive_sky)
    drawable = drawable_ray_legs(payload, candidates, terminations, drawn_radius_m=drawn_radius_m)
    outside = drawable.paths_left_out_beyond_drawn_support
    candidates = candidates[~np.isin(candidates, outside)]
    order = np.lexsort((candidates, -score[candidates]))
    ranked = candidates[order[:count]]
    elevation = np.degrees(np.arcsin(np.clip(exit_direction[ranked, 2], -1.0, 1.0)))
    return RankedVisualPaths(
        path_index=ranked,
        score=score[ranked],
        final_throughput=final[ranked],
        rooftop_density_per_sr=density[ranked],
        departure_cell=launch_cell[ranked],
        departure_cell_count=cell_count[launch_cell[ranked]],
        bounces=bounces[ranked],
        exit_elevation_deg=elevation,
        paths_recorded=paths,
        positive_sky_paths=int(np.count_nonzero(positive_sky)),
        paths_left_out_beyond_drawn_support=outside,
        score_sum_all_drawable_sky_paths=float(np.sum(score[candidates])),
    )


def _one_frame(obj: Any, frame: int, start: int, end: int) -> None:
    """Key visibility so ``obj`` is visible at one integer frame only."""
    keys = [(start, frame != start), (frame, False), (frame + 1, True)]
    for data_path in ("hide_viewport", "hide_render"):
        for at, hidden in keys:
            obj.__setattr__(data_path, hidden)
            obj.keyframe_insert(data_path=data_path, frame=at)
        action = obj.animation_data.action
        for curve in action.fcurves:
            if curve.data_path == data_path:
                for point in curve.keyframe_points:
                    point.interpolation = "CONSTANT"
    obj["visible_frame"] = frame
    obj["visibility_key_interpolation"] = "CONSTANT"
    obj["animation_frame_range"] = [start, end]


def _stamp_path_object(
    obj: Any,
    *,
    path_index: int,
    bounces: int,
    role: str,
    score: float | None,
) -> None:
    obj["visual_trace_path_index"] = path_index
    obj["bounce_count"] = bounces
    obj["chain_role"] = role
    obj["curve_type"] = "POLY"
    obj["is_classical_mpc"] = False
    obj["supplies_production_rho_or_body_dose"] = False
    if score is not None:
        obj["rooftop_visual_retrace_score"] = score


def _curve_from_legs(
    name: str,
    legs: DrawableRayLegs,
    keep: np.ndarray,
    into: Any,
    *,
    radius_m: float,
    material: Any,
    escaped_proxy_m: float | None = None,
) -> Any | None:
    from . import scene

    if not np.any(keep):
        return None
    pairs = legs.points.reshape(-1, 2, 3)[keep].copy()
    if escaped_proxy_m is not None:
        vector = pairs[:, 1] - pairs[:, 0]
        vector /= np.linalg.norm(vector, axis=1)[:, None]
        pairs[:, 1] = pairs[:, 0] + escaped_proxy_m * vector
    power = legs.leg_throughput[keep]
    point_power = np.repeat(power, 2)
    obj = scene.build_curves(
        name,
        pairs.reshape(-1, 3),
        np.full(power.size, 2, dtype=np.int32),
        radius_m * np.cbrt(np.maximum(point_power, 0.0)),
        into,
    )
    scene.attach_values(obj, "value_throughput", point_power, "POINT")
    scene.attach_values(obj, "value_leg_index", np.repeat(legs.leg_index[keep], 2), "POINT")
    scene.assign(obj, material)
    return obj


def _build_chain(
    payload: Any,
    terminations: Sequence[str],
    into: Any,
    *,
    path_index: int,
    name: str,
    drawn_radius_m: float,
    radius_m: float,
    escaped_proxy_m: float,
    chain_material: Any,
    proxy_material: Any,
    score: float | None,
) -> list[Any]:
    legs = drawable_ray_legs(
        payload,
        np.array([path_index], dtype=np.int64),
        terminations,
        drawn_radius_m=drawn_radius_m,
    )
    if legs.paths_drawn != 1:
        return []
    objects: list[Any] = []
    chain = _curve_from_legs(
        f"{name} | physical chain",
        legs,
        ~legs.escaped_final,
        into,
        radius_m=radius_m,
        material=chain_material,
    )
    if chain is not None:
        chain["reading"] = "straight physical legs from the pedestrian through every recorded reflection"
        objects.append(chain)
    proxy = _curve_from_legs(
        f"{name} | escaped direction proxy",
        legs,
        legs.escaped_final,
        into,
        radius_m=0.72 * radius_m,
        material=proxy_material,
        escaped_proxy_m=escaped_proxy_m,
    )
    if proxy is not None:
        proxy["reading"] = (
            "short display proxy for the final semi-infinite escaped ray; direction is physical and endpoint is not"
        )
        proxy["escaped_direction_proxy_length_m"] = escaped_proxy_m
        objects.append(proxy)
    bounces = int(np.asarray(payload["path_bounces"])[path_index])
    for obj in objects:
        _stamp_path_object(obj, path_index=path_index, bounces=bounces, role="stored SBR chain", score=score)
    return objects


def _marker_mesh(name: str, points: np.ndarray, into: Any, radius_m: float, material: Any) -> Any | None:
    from . import scene

    if points.size == 0:
        return None
    unique = np.unique(np.asarray(points, dtype=np.float64), axis=0)
    vertices, faces = octahedra(unique, radius_m)
    obj = scene.build_mesh(name, vertices, faces, into)
    scene.assign(obj, material)
    obj["markers"] = int(unique.shape[0])
    return obj


def _connection_curve(
    name: str,
    origin: np.ndarray,
    site: np.ndarray,
    rim_weight: np.ndarray,
    into: Any,
    *,
    radius_m: float,
    material: Any,
) -> Any | None:
    from . import scene

    if origin.size == 0:
        return None
    ends = np.empty((origin.shape[0] * 2, 3), dtype=np.float64)
    ends[0::2], ends[1::2] = origin, site
    obj = scene.build_curves(
        name,
        ends,
        np.full(origin.shape[0], 2, dtype=np.int32),
        np.full(ends.shape[0], radius_m),
        into,
    )
    scene.attach_values(obj, "value_roofline_rim_direct_flux", np.repeat(rim_weight, 2), "POINT")
    scene.assign(obj, material)
    obj["stored_weight_is"] = "roofline rim direct flux only"
    obj["stored_weight_is_not"] = "a quantitative NEE contribution"
    return obj


def _ordered_nee_paths(payload: Any, limit: int) -> np.ndarray:
    selected = np.asarray(payload["nee_paths"], dtype=np.int64)
    connection_path = np.asarray(payload["nee_path_index"], dtype=np.int64)
    vertex_index = np.asarray(payload["nee_vertex_index"], dtype=np.int64)
    blocked = np.asarray(payload["nee_blocked"], dtype=bool)
    records = []
    for order, path in enumerate(selected):
        values = blocked[(connection_path == path) & (vertex_index > 0)]
        has_clear = bool(np.any(~values))
        has_blocked = bool(np.any(values))
        records.append((not (has_clear and has_blocked), not has_blocked, order, int(path)))
    records.sort()
    return np.array([row[-1] for row in records[:limit]], dtype=np.int64)


def _animation_materials(scene_tools: Any) -> dict[str, Any]:
    return {
        "path": scene_tools.emissive_material(
            "animation ranked physical chain", None, ANIMATION_PATH_COLOUR, strength=2.2
        ),
        "proxy": scene_tools.emissive_material(
            "animation escaped direction proxy", None, ANIMATION_PROXY_COLOUR, strength=2.2
        ),
        "nee_chain": scene_tools.emissive_material(
            "animation NEE base SBR chain", None, ANIMATION_NEE_CHAIN_COLOUR, strength=2.2
        ),
        "clear": scene_tools.emissive_material(
            "animation NEE clear connection", None, ANIMATION_CLEAR_CONNECTION_COLOUR, strength=2.2
        ),
        "blocked": scene_tools.emissive_material(
            "animation NEE blocked connection", None, ANIMATION_BLOCKED_CONNECTION_COLOUR, strength=2.2
        ),
        "scatter": scene_tools.emissive_material(
            "animation NEE scattering origin", None, ANIMATION_SCATTER_COLOUR, strength=2.2
        ),
        "source": scene_tools.emissive_material(
            "animation NEE source endpoint", None, ANIMATION_SOURCE_COLOUR, strength=2.2
        ),
        "label": scene_tools.emissive_material("animation frame label", None, (1.0, 0.96, 0.82), strength=1.4),
        "label_panel": scene_tools.emissive_material(
            "animation frame label panel", None, (0.012, 0.016, 0.025), strength=1.0
        ),
    }


def _bounce_label(bounces: int) -> str:
    if bounces == 0:
        return "direct"
    suffix = "" if bounces == 1 else "s"
    return f"{bounces} bounce{suffix}"


def _frame_label(
    name: str,
    body: str,
    into: Any,
    materials: Mapping[str, Any],
    *,
    frame: int,
    frame_end: int,
) -> list[Any]:
    """A small camera-fixed plain-language label with a dark backing panel."""
    import bpy

    from . import scene

    camera = bpy.data.objects.get("cam_rays")
    if camera is None:
        raise RuntimeError("path animation needs cam_rays before it can place its frame label")
    text_data = bpy.data.curves.new(f"{name} text", type="FONT")
    text_data.body = body
    text_data.align_x = "LEFT"
    text_data.align_y = "TOP"
    text_data.size = 0.22
    text_data.space_line = 1.08
    text_obj = bpy.data.objects.new(f"{name} | readable frame label", text_data)
    into.objects.link(text_obj)
    text_obj.parent = camera
    text_obj.location = (-4.45, 2.34, -10.0)
    scene.assign(text_obj, materials["label"])

    vertices = np.array([[-4.72, -0.52, 0.0], [4.72, -0.52, 0.0], [4.72, 0.52, 0.0], [-4.72, 0.52, 0.0]])
    panel = scene.build_mesh(
        f"{name} | label backing panel",
        vertices,
        np.array([[0, 1, 2], [0, 2, 3]], dtype=np.int32),
        into,
    )
    panel.parent = camera
    panel.location = (0.0, 1.93, -10.05)
    scene.assign(panel, materials["label_panel"])
    for obj in (text_obj, panel):
        obj["label_text"] = body
        obj["label_role"] = "camera-fixed plain-language animation label"
        _one_frame(obj, frame, 1, frame_end)
    return [text_obj, panel]


def _build_ranked_frames(
    payload: Any,
    terminations: Sequence[str],
    ranked: RankedVisualPaths,
    path_collection: Any,
    materials: Mapping[str, Any],
    *,
    frame_end: int,
    drawn_radius_m: float,
    radius_m: float,
    escaped_proxy_m: float,
) -> list[dict[str, Any]]:
    import bpy

    rows: list[dict[str, Any]] = []
    for rank, path_index in enumerate(ranked.path_index, start=1):
        score = float(ranked.score[rank - 1])
        bounces = int(ranked.bounces[rank - 1])
        kind = _bounce_label(bounces)
        objects = _build_chain(
            payload,
            terminations,
            path_collection,
            path_index=int(path_index),
            name=f"rank {rank:02d} | path {int(path_index)} | {kind}",
            drawn_radius_m=drawn_radius_m,
            radius_m=radius_m,
            escaped_proxy_m=escaped_proxy_m,
            chain_material=materials["path"],
            proxy_material=materials["proxy"],
            score=score,
        )
        for obj in objects:
            obj["rank"] = rank
            obj["score_definition"] = (
                "solid angle times final throughput times rooftop density, divided by departure-cell ray count"
            )
            obj["final_throughput"] = float(ranked.final_throughput[rank - 1])
            obj["rooftop_density_per_sr"] = float(ranked.rooftop_density_per_sr[rank - 1])
            obj["departure_cell"] = int(ranked.departure_cell[rank - 1])
            obj["departure_cell_ray_count"] = int(ranked.departure_cell_count[rank - 1])
            obj["exit_elevation_deg"] = float(ranked.exit_elevation_deg[rank - 1])
            _one_frame(obj, rank, 1, frame_end)
        label = (
            f"RANK {rank:02d}  |  SAMPLE {int(path_index)}  |  {kind.upper()}\n"
            "ORANGE physical chain  |  BLUE escaped-direction proxy\n"
            f"visual-retrace score {score:.5g}  |  not a production MPC"
        )
        _frame_label(f"rank {rank:02d}", label, path_collection, materials, frame=rank, frame_end=frame_end)
        bpy.context.scene.timeline_markers.new(f"PATH {rank:02d} | {kind} | sample {int(path_index)}", frame=rank)
        rows.append(
            {
                "rank": rank,
                "frame": rank,
                "path_index": int(path_index),
                "bounces": bounces,
                "score": score,
                "exit_elevation_deg": float(ranked.exit_elevation_deg[rank - 1]),
            }
        )
    return rows


def _nee_arrays(payload: Any) -> _NeeArrays:
    return _NeeArrays(
        path=np.asarray(payload["nee_path_index"], dtype=np.int64),
        vertex=np.asarray(payload["nee_vertex_index"], dtype=np.int64),
        origin=np.asarray(payload["nee_origin_m"], dtype=np.float64),
        site=np.asarray(payload["nee_site_m"], dtype=np.float64),
        rim_weight=np.asarray(payload["nee_weight"], dtype=np.float64),
        blocked=np.asarray(payload["nee_blocked"], dtype=bool),
    )


def _nee_connections(
    arrays: _NeeArrays,
    keep: np.ndarray,
    nee_collection: Any,
    materials: Mapping[str, Any],
    nee_rank: int,
) -> tuple[list[Any], np.ndarray]:
    origin = arrays.origin[keep]
    site = arrays.site[keep]
    weight = arrays.rim_weight[keep]
    blocked = arrays.blocked[keep]
    objects = []
    for blocked_value, label, material, width in (
        (False, "clear NEE connection", materials["clear"], 0.065),
        (True, "blocked NEE connection", materials["blocked"], 0.055),
    ):
        subset = blocked == blocked_value
        obj = _connection_curve(
            f"NEE {nee_rank:02d} | {label}",
            origin[subset],
            site[subset],
            weight[subset],
            nee_collection,
            radius_m=width,
            material=material,
        )
        if obj is not None:
            obj["connection_state"] = "blocked" if blocked_value else "clear"
            objects.append(obj)
    scatter = _marker_mesh(
        f"NEE {nee_rank:02d} | scattering origins",
        origin,
        nee_collection,
        0.32,
        materials["scatter"],
    )
    source = _marker_mesh(
        f"NEE {nee_rank:02d} | sampled roofline source endpoints",
        site,
        nee_collection,
        0.48,
        materials["source"],
    )
    objects.extend(obj for obj in (scatter, source) if obj is not None)
    return objects, blocked


def _build_one_nee_frame(
    payload: Any,
    terminations: Sequence[str],
    arrays: _NeeArrays,
    live: np.ndarray,
    nee_collection: Any,
    materials: Mapping[str, Any],
    *,
    path_index: int,
    nee_rank: int,
    frame: int,
    frame_end: int,
    drawn_radius_m: float,
    radius_m: float,
    escaped_proxy_m: float,
) -> dict[str, Any]:
    import bpy

    objects = _build_chain(
        payload,
        terminations,
        nee_collection,
        path_index=path_index,
        name=f"NEE {nee_rank:02d} | sample {path_index} | base SBR chain",
        drawn_radius_m=drawn_radius_m,
        radius_m=radius_m,
        escaped_proxy_m=escaped_proxy_m,
        chain_material=materials["nee_chain"],
        proxy_material=materials["proxy"],
        score=None,
    )
    keep = (
        (arrays.path == path_index)
        & (arrays.vertex > 0)
        & live
        & (np.linalg.norm(arrays.site[:, :2], axis=1) <= drawn_radius_m)
    )
    connection_objects, blocked = _nee_connections(arrays, keep, nee_collection, materials, nee_rank)
    objects.extend(connection_objects)
    for obj in objects:
        obj["visual_trace_path_index"] = path_index
        obj["explanation_role"] = "qualitative roofline source visibility evidence"
        obj["connections_shown_from"] = "surface scattering vertices; the separate direct head-to-site term is left out"
        obj["supplies_production_rho_or_body_dose"] = False
        obj["quantitative_nee_contribution_available"] = False
        obj["why_no_quantitative_nee_value"] = (
            "the payload stores roofline rim weight and visibility, not the full NEE deposit factors"
        )
        _one_frame(obj, frame, 1, frame_end)
    clear_count = int(np.count_nonzero(~blocked))
    blocked_count = int(np.count_nonzero(blocked))
    label = (
        f"NEE VIEW {nee_rank:02d}  |  SAMPLE {path_index}  |  "
        f"CLEAR {clear_count}  BLOCKED {blocked_count}\n"
        "BROWN base chain  |  PINK post-bounce origin  |  LIME source\n"
        "WHITE clear  |  RED blocked  |  evidence only; no dose value"
    )
    _frame_label(f"NEE {nee_rank:02d}", label, nee_collection, materials, frame=frame, frame_end=frame_end)
    bpy.context.scene.timeline_markers.new(
        f"NEE {nee_rank:02d} | sample {path_index} | clear {clear_count} blocked {blocked_count}",
        frame=frame,
    )
    return {
        "frame": frame,
        "path_index": path_index,
        "clear_connections": clear_count,
        "blocked_connections": blocked_count,
    }


def _build_nee_frames(
    payload: Any,
    terminations: Sequence[str],
    nee_paths: np.ndarray,
    nee_collection: Any,
    materials: Mapping[str, Any],
    *,
    ranked_count: int,
    frame_end: int,
    drawn_radius_m: float,
    radius_m: float,
    escaped_proxy_m: float,
) -> list[dict[str, Any]]:
    arrays = _nee_arrays(payload)
    live = supported_live_scattering_vertices(
        payload,
        arrays.path,
        arrays.vertex,
        np.zeros(0, dtype=np.int64),
    )
    return [
        _build_one_nee_frame(
            payload,
            terminations,
            arrays,
            live,
            nee_collection,
            materials,
            path_index=int(path_index),
            nee_rank=nee_rank,
            frame=ranked_count + nee_rank,
            frame_end=frame_end,
            drawn_radius_m=drawn_radius_m,
            radius_m=radius_m,
            escaped_proxy_m=escaped_proxy_m,
        )
        for nee_rank, path_index in enumerate(nee_paths, start=1)
    ]


def _stamp_dense_overview(
    dense_ray_collection: Any,
    dense_bounce_collection: Any,
) -> None:
    for dense in (dense_ray_collection, dense_bounce_collection):
        dense["role"] = "static dense overview, kept in the raw data scene and excluded from animation views"
        dense["how_to_show"] = "open the raw data scene or include this collection in a prepared view layer"


def _stamp_animation_scene(
    ranked: RankedVisualPaths,
    ranking_rows: list[dict[str, Any]],
    nee_frames: list[dict[str, Any]],
    *,
    frame_end: int,
    escaped_proxy_m: float,
) -> None:
    import bpy

    scene = bpy.context.scene
    ranked_count = int(ranked.path_index.size)
    scene.render.fps = 1
    scene.render.fps_base = 1.0
    scene.frame_start = 1
    scene.frame_end = frame_end
    scene["animation_path_frames"] = [1, ranked_count]
    scene["animation_nee_frames"] = [ranked_count + 1, frame_end] if nee_frames else []
    scene["animation_ranked_paths"] = json.dumps(ranking_rows)
    scene["animation_nee_frames_detail"] = json.dumps(nee_frames)
    scene["animation_score_definition"] = (
        "visual retrace chi contribution: solid angle * final throughput * rooftop density / departure-cell count"
    )
    scene["animation_is_production_mpc_decomposition"] = False
    scene["animation_path_meaning"] = (
        "ranked reverse Monte Carlo samples from the bounded visual trace, not finite transmitter-to-receiver MPCs"
    )
    scene["animation_nee_meaning"] = (
        "qualitative source visibility evidence only; clear and blocked connections do not supply production exposure"
    )
    scene["animation_escape_proxy_length_m"] = escaped_proxy_m
    scene["animation_visual_trace_score_sum"] = ranked.score_sum_all_drawable_sky_paths
    scene["animation_paths_left_out_beyond_drawn_support"] = int(ranked.paths_left_out_beyond_drawn_support.size)
    scene.frame_set(1)


def build_path_animation(
    payload: Any,
    terminations: Sequence[str],
    *,
    path_collection: Any,
    nee_collection: Any,
    dense_ray_collection: Any,
    dense_bounce_collection: Any,
    drawn_radius_m: float,
    ranked_count: int = 12,
    nee_count: int = 12,
    radius_m: float = 0.16,
    escaped_proxy_m: float = 24.0,
) -> dict[str, Any]:
    """Build both animation ranges and make the dense ray fan an opt-in view."""
    from . import scene as scene_tools

    ranked = rank_rooftop_visual_paths(
        payload,
        terminations,
        count=ranked_count,
        drawn_radius_m=drawn_radius_m,
    )
    ranked_count = int(ranked.path_index.size)
    has_nee = all(
        key in _payload_keys(payload)
        for key in (
            "nee_paths",
            "nee_path_index",
            "nee_vertex_index",
            "nee_origin_m",
            "nee_site_m",
            "nee_weight",
            "nee_blocked",
        )
    )
    nee_paths = _ordered_nee_paths(payload, nee_count) if has_nee else np.zeros(0, dtype=np.int64)
    if nee_paths.size:
        nee_legs = drawable_ray_legs(payload, nee_paths, terminations, drawn_radius_m=drawn_radius_m)
        nee_paths = nee_paths[~np.isin(nee_paths, nee_legs.paths_left_out_beyond_drawn_support)]
    frame_end = max(ranked_count + int(nee_paths.size), 1)
    materials = _animation_materials(scene_tools)
    ranking_rows = _build_ranked_frames(
        payload,
        terminations,
        ranked,
        path_collection,
        materials,
        frame_end=frame_end,
        drawn_radius_m=drawn_radius_m,
        radius_m=radius_m,
        escaped_proxy_m=escaped_proxy_m,
    )
    nee_frames = (
        _build_nee_frames(
            payload,
            terminations,
            nee_paths,
            nee_collection,
            materials,
            ranked_count=ranked_count,
            frame_end=frame_end,
            drawn_radius_m=drawn_radius_m,
            radius_m=radius_m,
            escaped_proxy_m=escaped_proxy_m,
        )
        if has_nee
        else []
    )
    _stamp_dense_overview(dense_ray_collection, dense_bounce_collection)
    _stamp_animation_scene(
        ranked,
        ranking_rows,
        nee_frames,
        frame_end=frame_end,
        escaped_proxy_m=escaped_proxy_m,
    )
    return {
        "ranked_path_frames": ranked_count,
        "nee_frames": len(nee_frames),
        "frame_range": [1, frame_end],
        "strongest_path_index": int(ranked.path_index[0]) if ranked_count else None,
        "strongest_path_bounces": int(ranked.bounces[0]) if ranked_count else None,
        "strongest_score": float(ranked.score[0]) if ranked_count else None,
    }
