"""Readable frame-by-frame explanations of the stored visual ray trace.

The dense ray fan remains in the file as an overview. This module adds two
small animations beside it. The first ranks the bounded visual-trace samples
under the rooftop angular law. It separates the finite reflection prefix from
the display proxy for the semi-infinite escape ray and arrows the incoming
travel direction. The second shows exactly one roofline visibility test per
frame. Its two coloured parts meet at one selected scattering vertex. No later
part of the stored reverse path is shown.

These frames do not turn the visual trace into a transmitter-to-receiver MPC
decomposition. The production spectrum was computed from a separate, much
larger GPU trace. The stored next-event arrays are also geometry evidence. They
do not contain the factors needed to reconstruct a quantitative NEE deposit.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

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

ANIMATION_CAMERA_NAME = "cam_path_animation"


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


@dataclass(frozen=True)
class NeeCandidate:
    """One stored roofline visibility test selected for one frame."""

    record_index: int
    path_index: int
    vertex_index: int
    blocked: bool


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
    if count < 0:
        raise ValueError("animation path count must be non-negative")
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
    display_power = np.maximum(point_power, 0.025)
    obj = scene.build_curves(
        name,
        pairs.reshape(-1, 3),
        np.full(power.size, 2, dtype=np.int32),
        radius_m * np.cbrt(display_power),
        into,
    )
    scene.attach_values(obj, "value_throughput", point_power, "POINT")
    scene.attach_values(obj, "value_leg_index", np.repeat(legs.leg_index[keep], 2), "POINT")
    scene.assign(obj, material)
    obj["display_radius_power_floor"] = 0.025
    obj["display_radius_floor_is_visual_only"] = True
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
        _stamp_path_object(
            obj,
            path_index=path_index,
            bounces=bounces,
            role="bounded visual-retrace escape sample",
            score=score,
        )
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
    obj["marker_radius_m"] = radius_m
    return obj


def _arrowhead_geometry(
    tip: np.ndarray,
    direction: np.ndarray,
    *,
    length_m: float,
    radius_m: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Return one four-sided arrowhead whose point follows ``direction``."""
    tip = np.asarray(tip, dtype=np.float64)
    direction = np.asarray(direction, dtype=np.float64)
    norm = float(np.linalg.norm(direction))
    if tip.shape != (3,) or direction.shape != (3,) or norm <= 1.0e-12:
        raise ValueError("an arrowhead needs one point and one non-zero direction")
    axis = direction / norm
    helper = np.array([0.0, 0.0, 1.0]) if abs(axis[2]) < 0.9 else np.array([0.0, 1.0, 0.0])
    side_a = np.cross(axis, helper)
    side_a /= np.linalg.norm(side_a)
    side_b = np.cross(axis, side_a)
    base = tip - length_m * axis
    vertices = np.vstack(
        [
            tip,
            base + radius_m * side_a,
            base + radius_m * side_b,
            base - radius_m * side_a,
            base - radius_m * side_b,
        ]
    )
    faces = np.array(
        [
            [0, 1, 2],
            [0, 2, 3],
            [0, 3, 4],
            [0, 4, 1],
            [1, 4, 3],
            [1, 3, 2],
        ],
        dtype=np.int32,
    )
    return vertices, faces


def _direction_arrow(
    name: str,
    escape_origin: np.ndarray,
    external: np.ndarray,
    into: Any,
    material: Any,
) -> Any:
    """Draw an inward arrow on a finite proxy for a semi-infinite arrival."""
    from . import scene

    outward = np.asarray(external, dtype=np.float64) - np.asarray(escape_origin, dtype=np.float64)
    length = float(np.linalg.norm(outward))
    outward /= max(length, 1.0e-12)
    tip = external - 0.62 * length * outward
    vertices, faces = _arrowhead_geometry(tip, -outward, length_m=0.95, radius_m=0.34)
    obj = scene.build_mesh(name, vertices, faces, into)
    scene.assign(obj, material)
    obj["candidate_part"] = "incoming travel direction arrow"
    obj["arrow_points_toward_receiver"] = True
    obj["arrow_is_on_finite_display_proxy"] = True
    return obj


def _animation_camera() -> Any:
    """Return a private camera copied from the static ray overview camera.

    Prepared still scenes also use ``cam_rays``. Animation keyframes therefore
    belong on a separate object and camera datablock, so saving an animation
    cannot change the framing of any still scene.
    """
    import bpy

    camera = bpy.data.objects.get(ANIMATION_CAMERA_NAME)
    if camera is not None:
        return camera
    source = bpy.data.objects.get("cam_rays")
    if source is None:
        raise RuntimeError("path animation needs cam_rays before it can copy its private camera")
    camera = source.copy()
    camera.data = source.data.copy()
    camera.animation_data_clear()
    camera.data.animation_data_clear()
    camera.name = ANIMATION_CAMERA_NAME
    camera.data.name = ANIMATION_CAMERA_NAME
    for collection in source.users_collection:
        collection.objects.link(camera)
    camera["animation_camera_source"] = source.name
    camera["animation_camera_is_private"] = True
    return camera


def _key_camera_for_frame(points: np.ndarray, frame: int) -> None:
    """Fit the private animation camera to one frame."""
    import bpy

    from .payload import camera_rotation

    if points.size == 0:
        return
    camera = _animation_camera()
    points = np.asarray(points, dtype=np.float64).reshape(-1, 3)
    low, high = np.min(points, axis=0), np.max(points, axis=0)
    centre = 0.5 * (low + high)
    radius = max(0.5 * float(np.linalg.norm(high - low)), 2.0)
    if "animation_view_direction" in camera:
        view = np.asarray(camera["animation_view_direction"], dtype=np.float64)
    else:
        view = np.asarray(camera.location, dtype=np.float64) - centre
        if np.linalg.norm(view) <= 1.0e-9:
            view = np.array([0.6, -1.0, 0.55])
        view /= np.linalg.norm(view)
        camera["animation_view_direction"] = view.tolist()

    render = bpy.context.scene.render
    aspect = max(float(render.resolution_x) / max(float(render.resolution_y), 1.0), 1.0e-6)
    half_horizontal = np.arctan(float(camera.data.sensor_width) / (2.0 * float(camera.data.lens)))
    half_vertical = np.arctan(np.tan(half_horizontal) / aspect)
    distance = 1.35 * radius / max(np.tan(min(half_horizontal, half_vertical)), 1.0e-3)
    location = centre + distance * view
    camera.location = tuple(location)
    camera.rotation_euler = camera_rotation(location, centre)
    camera.data.clip_end = max(float(camera.data.clip_end), distance + 4.0 * radius)
    for data_path in ("location", "rotation_euler"):
        camera.keyframe_insert(data_path=data_path, frame=frame)
    action = camera.animation_data.action
    for curve in action.fcurves:
        if curve.data_path in {"location", "rotation_euler"}:
            for point in curve.keyframe_points:
                point.interpolation = "CONSTANT"
    camera["animation_camera_fit"] = "per-frame bounds with 35 percent margin"


def _ordered_nee_paths(payload: Any, limit: int) -> np.ndarray:
    """Put paths with both clear and blocked tests first for explanation."""
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
        "receiver": scene_tools.emissive_material("animation receiver marker", None, (0.15, 0.95, 1.0), strength=2.8),
        "boundary": scene_tools.emissive_material(
            "animation external arrival boundary", None, ANIMATION_PROXY_COLOUR, strength=2.8
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

    camera = _animation_camera()
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
    vertices = np.asarray(payload["path_vertices"], dtype=np.float64)
    offsets = np.asarray(payload["path_offsets"], dtype=np.int64)
    exit_direction = np.asarray(payload["path_exit_direction"], dtype=np.float64)
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
        start = int(offsets[path_index])
        receiver = vertices[start]
        bounce_points = vertices[start + 1 : start + bounces + 1]
        escape_origin = vertices[start + bounces]
        escaped_direction = exit_direction[path_index].copy()
        escaped_direction /= max(float(np.linalg.norm(escaped_direction)), 1.0e-12)
        external = escape_origin + escaped_proxy_m * escaped_direction
        receiver_marker = _marker_mesh(
            f"rank {rank:02d} | receiver",
            receiver[None, :],
            path_collection,
            0.52,
            materials["receiver"],
        )
        bounce_marker = _marker_mesh(
            f"rank {rank:02d} | finite reflection vertices",
            bounce_points,
            path_collection,
            0.36,
            materials["scatter"],
        )
        boundary_marker = _marker_mesh(
            f"rank {rank:02d} | external arrival direction boundary",
            external[None, :],
            path_collection,
            0.46,
            materials["boundary"],
        )
        direction_arrow = _direction_arrow(
            f"rank {rank:02d} | incoming travel direction arrow",
            escape_origin,
            external,
            path_collection,
            materials["boundary"],
        )
        for marker, marker_role in (
            (receiver_marker, "receiver endpoint"),
            (bounce_marker, "finite reflection vertices"),
            (boundary_marker, "display boundary on a semi-infinite arrival direction"),
            (direction_arrow, "incoming travel direction arrow"),
        ):
            if marker is None:
                continue
            _stamp_path_object(
                marker,
                path_index=int(path_index),
                bounces=bounces,
                role="bounded visual-retrace escape sample",
                score=score,
            )
            marker["candidate_part"] = marker_role
            objects.append(marker)
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
            f"VISUAL-RETRACE RANK {rank:02d}  |  SAMPLE {int(path_index)}  |  {kind.upper()}\n"
            "ORANGE finite bounce prefix  |  BLUE semi-infinite direction  |  CYAN arrow points inward\n"
            f"finite boundary is display only  |  score {score:.5g}  |  visual retrace, not a production MPC"
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
        frame_points = np.vstack([receiver, bounce_points, external])
        _key_camera_for_frame(frame_points, rank)
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


def nee_candidate_chain_points(
    payload: Any,
    *,
    path_index: int,
    vertex_index: int,
    site: np.ndarray,
    recorded_origin: np.ndarray,
) -> np.ndarray:
    """Return ``source -> selected vertex -> reverse prefix -> receiver``.

    No vertex after ``vertex_index`` is admitted. Those vertices form the unused
    suffix of the sampled reverse SBR path and do not belong to this NEE candidate.
    """
    vertices = np.asarray(payload["path_vertices"], dtype=np.float64)
    offsets = np.asarray(payload["path_offsets"], dtype=np.int64)
    if path_index < 0 or path_index >= offsets.size - 1:
        raise IndexError("NEE candidate path is outside the recorded path table")
    start, stop = int(offsets[path_index]), int(offsets[path_index + 1])
    if vertex_index <= 0 or start + vertex_index >= stop - 1:
        raise ValueError("NEE candidate must use a non-receiver scattering vertex")
    origin = vertices[start + vertex_index]
    recorded_origin = np.asarray(recorded_origin, dtype=np.float64)
    if not np.allclose(origin, recorded_origin, rtol=0.0, atol=2.0e-5):
        raise ValueError("stored NEE origin does not match its indexed SBR vertex")
    prefix_to_receiver = vertices[start : start + vertex_index + 1][::-1]
    return np.vstack([np.asarray(site, dtype=np.float64), prefix_to_receiver])


def _candidate_records(
    payload: Any,
    arrays: _NeeArrays,
    selected_paths: np.ndarray,
    live: np.ndarray,
    *,
    drawn_radius_m: float,
    limit: int,
) -> list[NeeCandidate]:
    """Choose one clear and blocked row per path whose shown prefix has support."""
    if limit == 0:
        return []
    on_mesh = np.linalg.norm(arrays.site[:, :2], axis=1) <= drawn_radius_m
    eligible = (arrays.vertex > 0) & live & on_mesh & np.isfinite(arrays.rim_weight)
    candidates: list[NeeCandidate] = []
    for path_index in selected_paths:
        rows = np.flatnonzero(eligible & (arrays.path == path_index))
        for blocked in (False, True):
            state_rows = rows[arrays.blocked[rows] == blocked]
            if not state_rows.size:
                continue
            order = np.lexsort((state_rows, arrays.vertex[state_rows], -arrays.rim_weight[state_rows]))
            for ordered_record in state_rows[order]:
                record = int(ordered_record)
                candidate = NeeCandidate(
                    record_index=record,
                    path_index=int(path_index),
                    vertex_index=int(arrays.vertex[record]),
                    blocked=bool(blocked),
                )
                chain = nee_candidate_chain_points(
                    payload,
                    path_index=candidate.path_index,
                    vertex_index=candidate.vertex_index,
                    site=arrays.site[record],
                    recorded_origin=arrays.origin[record],
                )
                if np.any(np.linalg.norm(chain[1:-1, :2], axis=1) > drawn_radius_m):
                    continue
                candidates.append(candidate)
                break
            if len(candidates) >= limit:
                return candidates
    return candidates


def _single_polyline(
    name: str,
    points: np.ndarray,
    into: Any,
    *,
    radius_m: float,
    material: Any,
) -> Any:
    from . import scene

    obj = scene.build_curves(
        name,
        points,
        np.array([points.shape[0]], dtype=np.int32),
        np.full(points.shape[0], radius_m, dtype=np.float64),
        into,
    )
    scene.attach_values(obj, "value_candidate_point_order", np.arange(points.shape[0]), "POINT")
    scene.assign(obj, material)
    obj["candidate_start_m"] = np.asarray(points[0], dtype=float).tolist()
    obj["candidate_end_m"] = np.asarray(points[-1], dtype=float).tolist()
    return obj


def _build_one_nee_frame(
    payload: Any,
    arrays: _NeeArrays,
    candidate: NeeCandidate,
    nee_collection: Any,
    materials: Mapping[str, Any],
    *,
    nee_rank: int,
    frame: int,
    frame_end: int,
    radius_m: float,
) -> dict[str, Any]:
    import bpy

    record = candidate.record_index
    chain = nee_candidate_chain_points(
        payload,
        path_index=candidate.path_index,
        vertex_index=candidate.vertex_index,
        site=arrays.site[record],
        recorded_origin=arrays.origin[record],
    )
    source_link = _single_polyline(
        f"NEE {nee_rank:02d} | {'blocked' if candidate.blocked else 'clear'} source link",
        chain[:2],
        nee_collection,
        radius_m=0.075 if not candidate.blocked else 0.062,
        material=materials["blocked" if candidate.blocked else "clear"],
    )
    receiver_prefix = _single_polyline(
        f"NEE {nee_rank:02d} | selected reverse prefix to receiver",
        chain[1:],
        nee_collection,
        radius_m=max(radius_m, 0.09),
        material=materials["nee_chain"],
    )
    scatter = _marker_mesh(
        f"NEE {nee_rank:02d} | selected scattering vertex",
        chain[1:2],
        nee_collection,
        0.42,
        materials["scatter"],
    )
    source = _marker_mesh(
        f"NEE {nee_rank:02d} | sampled roofline source",
        chain[0:1],
        nee_collection,
        0.56,
        materials["source"],
    )
    receiver = _marker_mesh(
        f"NEE {nee_rank:02d} | receiver",
        chain[-1:],
        nee_collection,
        0.52,
        materials["receiver"],
    )
    objects = [source_link, receiver_prefix]
    objects.extend(obj for obj in (scatter, source, receiver) if obj is not None)
    for obj in objects:
        obj["visual_trace_path_index"] = candidate.path_index
        obj["nee_record_index"] = record
        obj["nee_vertex_index"] = candidate.vertex_index
        obj["connection_state"] = "blocked" if candidate.blocked else "clear"
        obj["explanation_role"] = "one qualitative roofline source visibility candidate"
        obj["candidate_topology"] = "source -> selected SBR vertex -> reversed earlier prefix -> receiver"
        obj["unused_sbr_suffix_drawn"] = False
        obj["other_nee_alternatives_drawn"] = False
        obj["supplies_production_rho_or_body_dose"] = False
        obj["quantitative_nee_contribution_available"] = False
        obj["why_no_quantitative_nee_value"] = (
            "the payload stores roofline rim weight and visibility, not the full NEE deposit factors"
        )
        _one_frame(obj, frame, 1, frame_end)
    source_link["candidate_part"] = "sampled source to selected scattering vertex"
    source_link["stored_roofline_rim_direct_flux"] = float(arrays.rim_weight[record])
    source_link["stored_weight_is_not"] = "a quantitative NEE contribution"
    receiver_prefix["candidate_part"] = "selected scattering vertex to receiver through earlier reverse prefix"
    receiver_prefix["prefix_vertex_count"] = candidate.vertex_index + 1
    receiver_prefix["path_record_vertex_count"] = int(
        np.asarray(payload["path_offsets"])[candidate.path_index + 1]
        - np.asarray(payload["path_offsets"])[candidate.path_index]
    )
    state = "BLOCKED, REJECTED" if candidate.blocked else "CLEAR, ADMITTED"
    label = (
        f"ROOFLINE CANDIDATE {nee_rank:02d}  |  SAMPLE {candidate.path_index}  |  "
        f"VERTEX {candidate.vertex_index}  |  {state}\n"
        "LIME source -> WHITE/RED tested link -> PINK scatter -> BROWN prefix -> CYAN receiver\n"
        "one connected candidate  |  unused SBR suffix omitted  |  evidence only; no dose value"
    )
    _frame_label(f"NEE {nee_rank:02d}", label, nee_collection, materials, frame=frame, frame_end=frame_end)
    bpy.context.scene.timeline_markers.new(
        f"NEE {nee_rank:02d} | sample {candidate.path_index} vertex {candidate.vertex_index} | "
        f"{'blocked' if candidate.blocked else 'clear'}",
        frame=frame,
    )
    _key_camera_for_frame(chain, frame)
    return {
        "frame": frame,
        "path_index": candidate.path_index,
        "record_index": record,
        "vertex_index": candidate.vertex_index,
        "connection_state": "blocked" if candidate.blocked else "clear",
        "clear_connections": int(not candidate.blocked),
        "blocked_connections": int(candidate.blocked),
    }


def _build_nee_frames(
    payload: Any,
    candidates: Sequence[NeeCandidate],
    nee_collection: Any,
    materials: Mapping[str, Any],
    *,
    ranked_count: int,
    frame_end: int,
    radius_m: float,
) -> list[dict[str, Any]]:
    arrays = _nee_arrays(payload)
    return [
        _build_one_nee_frame(
            payload,
            arrays,
            candidate,
            nee_collection,
            materials,
            nee_rank=nee_rank,
            frame=ranked_count + nee_rank,
            frame_end=frame_end,
            radius_m=radius_m,
        )
        for nee_rank, candidate in enumerate(candidates, start=1)
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
    if ranked_count:
        scene["animation_path_frames"] = [1, ranked_count]
    elif "animation_path_frames" in scene:
        del scene["animation_path_frames"]
    if nee_frames:
        scene["animation_nee_frames"] = [ranked_count + 1, frame_end]
    elif "animation_nee_frames" in scene:
        del scene["animation_nee_frames"]
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
        "one connected qualitative source candidate per frame; clear and blocked tests do not supply production exposure"
    )
    scene["animation_nee_topology"] = (
        "sampled roofline source -> selected SBR vertex -> reversed earlier path prefix -> receiver"
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
    """Build the escape-sample and one-candidate-per-frame NEE ranges."""
    from . import scene as scene_tools

    if ranked_count < 0:
        raise ValueError("ranked animation count must be non-negative")
    if nee_count < 0:
        raise ValueError("NEE animation count must be non-negative")

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
    nee_paths = (
        _ordered_nee_paths(payload, int(np.asarray(payload["nee_paths"]).size))
        if has_nee
        else np.zeros(0, dtype=np.int64)
    )
    candidates: list[NeeCandidate] = []
    if nee_paths.size:
        arrays = _nee_arrays(payload)
        live = supported_live_scattering_vertices(
            payload,
            arrays.path,
            arrays.vertex,
            np.zeros(0, dtype=np.int64),
        )
        candidates = _candidate_records(
            payload,
            arrays,
            nee_paths,
            live,
            drawn_radius_m=drawn_radius_m,
            limit=nee_count,
        )
    frame_end = max(ranked_count + len(candidates), 1)
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
            candidates,
            nee_collection,
            materials,
            ranked_count=ranked_count,
            frame_end=frame_end,
            radius_m=radius_m,
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
