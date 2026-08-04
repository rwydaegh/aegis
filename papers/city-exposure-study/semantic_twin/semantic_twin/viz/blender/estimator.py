"""Drawing the estimator: the mesh, the paths, the spectrum, the sources, the body.

Everything in this module is measured. The mesh is the support mesh the rays were
cast against, the lobe is a stored angular power spectrum, and the colours on the
phantom are the absorbed power density AEGIS returned for that spectrum. A
standalone payload records paths from its exposure trace. A production payload
marks its smaller second trace as visible-path evidence only. The production walk,
spectrum, and body values still come from the three files named in its manifest.

The arithmetic each of these depends on is in
:mod:`~semantic_twin.viz.blender.payload` and the Blender calls are in
:mod:`~semantic_twin.viz.blender.scene`, so what is left here is the decisions:
which array becomes which layer, what range it is shaded over, and what the object
says about itself.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import bpy
import numpy as np

from .payload import (
    available_spectrum_models,
    octahedra,
    path_slice,
    place_body,
    ray_bundles,
    rim_polylines,
    rim_shading,
    rim_tube,
    shorten_sky_legs,
)
from .scene import (
    assign,
    attach_face_colour,
    attach_point_colour,
    attach_values,
    build_curves,
    build_mesh,
    emissive_material,
    layered,
    lit_material,
    show_layer,
)
from .style import (
    BOUNCE_STYLE,
    CLASS_TINT,
    MODEL_NAMES,
    NEE_BLOCKED_COLOUR,
    NEE_CLEAR_COLOUR,
    NEE_RAY_COLOUR,
    RAY_STYLE,
    RIM_BREAK_FRACTION,
    RIM_EMISSION_STRENGTH,
    RIM_RAMP_FLOOR,
    RIM_SITE_RADII,
    colour_ramp,
)


def _payload_text(payload: Any, key: str) -> str | None:
    keys = payload.files if hasattr(payload, "files") else payload
    return str(np.asarray(payload[key]).item()) if key in keys else None


def build_twin(payload: Any, class_names: Sequence[str], into: Any) -> Any:
    """The support mesh, tinted by the surface class that set each triangle's material."""
    face_class = payload["mesh_face_class"]
    tint = np.array([CLASS_TINT.get(name, (0.4, 0.4, 0.4)) for name in class_names])
    rgba = np.column_stack([tint[face_class], np.ones(face_class.size)])
    obj = build_mesh("support_mesh", payload["mesh_vertices"], payload["mesh_faces"], into)
    attach_face_colour(obj, "surface_class", rgba)
    assign(obj, lit_material("twin_surface", "surface_class"))
    return obj


def build_rays(payload: Any, terminations: Sequence[str], into: Any, *, base_radius: float) -> dict[str, int]:
    """One curves object per bundle, carrying throughput as thickness and as a layer.

    Throughput spans several decades along a multi bounce path, so the radius is the
    cube root of it. That keeps a fourth bounce visible instead of vanishing, and it
    is monotone, so thicker still means more power. The same number is on the points
    twice more, as an exact ``value_throughput`` and as a ``power_db`` colour over
    the decades it actually spans, so the fan can be shaded by power rather than
    only thickened by it. The default layer is ``fate``, the constant colour of the
    bundle, so nothing about the existing reading changes until it is asked to.
    """
    vertices = payload["path_vertices"]
    offsets = payload["path_offsets"].astype(np.int64)
    throughput = np.clip(payload["path_throughput"].astype(np.float64), 1.0e-9, None)
    decibels = 10.0 * np.log10(throughput)
    span = (float(np.quantile(decibels, 0.02)), float(decibels.max()))
    counts: dict[str, int] = {}
    for name, mask in ray_bundles(payload, terminations).items():
        indices = np.flatnonzero(mask)
        counts[name] = int(indices.size)
        keep = path_slice(offsets, indices)
        lengths = offsets[indices + 1] - offsets[indices]
        obj = build_curves(name, vertices[keep], lengths, base_radius * np.cbrt(throughput[keep]), into)
        colour, visible = RAY_STYLE[name]
        attach_point_colour(obj, "fate", np.tile((*colour, 1.0), (keep.size, 1)), byte=False)
        attach_point_colour(obj, "power_db", colour_ramp(decibels[keep], *span))
        attach_values(obj, "value_throughput", throughput[keep], "POINT")
        obj["colour_layers"] = ["fate", "power_db"]
        obj["power_db_range"] = list(span)
        obj["reading"] = "thickness is the cube root of throughput, and power_db is the same number as a colour"
        if role := _payload_text(payload, "visible_path_role"):
            obj["role"] = role
        assign(obj, emissive_material(f"ray_{name}", "fate"))
        show_layer(obj, "fate")
        obj.hide_render = not visible
    return counts


def build_ray_depth(payload: Any, into: Any, *, base_radius: float) -> dict[str, int]:
    """The same paths again, cut at the bounces, one object per leg index.

    The five bundles answer where a ray ended. They do not answer how deep it went,
    and depth is the question the bounce budget is about: the panoramas measure the
    material for the first two reflections and nothing measures it after that. A leg
    is one straight segment of a path, so leg zero is what left the standpoint and
    leg two is what carried on after the second surface. Switching the last object
    off shows exactly how much of the fan lives past what the evidence supports.
    """
    vertices = payload["path_vertices"]
    offsets = payload["path_offsets"].astype(np.int64)
    throughput = payload["path_throughput"]
    lengths = np.diff(offsets)
    counts: dict[str, int] = {}
    for depth, (colour, name) in enumerate(BOUNCE_STYLE):
        last = depth == len(BOUNCE_STYLE) - 1
        curve = bpy.data.curves.new(name, type="CURVE")
        curve.dimensions = "3D"
        curve.bevel_depth = base_radius
        curve.bevel_resolution = 1
        curve.use_fill_caps = True
        drawn = 0
        for index in np.flatnonzero(lengths > depth + 1):
            start, stop = int(offsets[index]), int(offsets[index + 1])
            first = start + depth
            points = vertices[first : stop if last else first + 2]
            if points.shape[0] < 2:
                continue
            spline = curve.splines.new("POLY")
            spline.points.add(points.shape[0] - 1)
            homogeneous = np.column_stack([points, np.ones(points.shape[0])]).astype(np.float32)
            spline.points.foreach_set("co", homogeneous.ravel())
            radius = np.cbrt(np.clip(throughput[first : first + points.shape[0]], 1.0e-6, None)).astype(np.float32)
            spline.points.foreach_set("radius", radius)
            drawn += 1
        counts[name] = drawn
        obj = bpy.data.objects.new(name, curve)
        into.objects.link(obj)
        assign(obj, emissive_material(f"bounce_{name}", None, colour))
        obj["legs_drawn"] = drawn
        obj["reading"] = f"path segments at leg index {depth}" + (" and past it" if last else "")
    return counts


def build_arrival(
    payload: Any,
    hero: np.ndarray,
    into: Any,
    *,
    scale_m: float,
    offset_m: float,
    floor: float,
) -> dict[str, float]:
    """One lobe per illumination model: the angular power spectrum as a surface.

    Radius is `rho(u)` normalised by the model's own maximum, so the three lobes are
    shape comparable rather than level comparable. Their levels differ by two orders
    of magnitude and drawing that faithfully would leave two of them invisible. The
    level is on the object as a custom property and in the manifest instead.

    The lobe belongs at the standpoint and is drawn ``offset_m`` above it, or it
    would enclose the phantom standing there and neither would be readable. Only the
    centre moves. Every direction and every radius is unchanged, and the offset is
    recorded on the object.
    """
    grid = payload["local_grid"].astype(np.float64)
    faces = payload["local_grid_faces"]
    centre = hero + np.array([0.0, 0.0, offset_m])
    peaks: dict[str, float] = {}
    for name in available_spectrum_models(payload, MODEL_NAMES):
        rho = payload[f"rho_{name}"].astype(np.float64)
        peak = float(rho.max())
        peaks[name] = peak
        # A directional model puts almost all of its measure in a narrow elevation
        # band, so the bare lobe is a pancake a few centimetres thick at this scale,
        # which is correct and unreadable. The floor keeps the surface closed and
        # turns the lobe into a bulge on a small sphere, the way an antenna pattern
        # is normally drawn. It compresses the low end and nothing else: the
        # ordering and the peak direction are untouched.
        shape = rho / peak if peak > 0.0 else rho
        radius = scale_m * (floor + (1.0 - floor) * shape)
        obj = build_mesh(f"arrival_{name}", centre + radius[:, None] * grid, faces, into)
        obj["drawn_metres_above_the_standpoint"] = offset_m
        obj["radius_floor_fraction"] = floor
        attach_face_colour(obj, "power", colour_ramp(rho[faces].mean(axis=1), 0.0, peak))
        assign(obj, emissive_material(f"arrival_{name}", "power"))
        obj["peak_rho_per_sr"] = peak
        obj["normalised_by"] = "its own peak, so shape is comparable across models and level is not"
        if arm := _payload_text(payload, "exposure_estimator_arm"):
            obj["estimator_arm"] = arm
        obj.hide_render = name != "rooftop"
    return peaks


def build_rim(
    payload: Any,
    hero: np.ndarray,
    into: Any,
    *,
    drawn_radius_m: float,
    width_scale: float,
    site_step: int,
) -> dict[str, object]:
    """The skyline as a lit rim, and the sites sitting on it.

    Both are the same measured curve, so they cannot disagree. The rim is the
    continuum the law integrates, a mean over azimuth, and it shows where the
    silhouette breaks. The markers say the deployment is still a set of sites on
    that tip, and they stay readable from a long way off and under solid shading
    where a thin tube does not.

    Colour is `cos^2(alpha) / d`, the direct flux that azimuth carries, over the
    base ten logarithm because the near tips carry two orders of magnitude more than
    the far ones. Thickness is not that number. Thickness rises as the square root
    of the slant range, which is between constant world size and constant angular
    size, so the far rim neither swells nor vanishes and no reader can mistake it
    for a second reading of the flux.
    """
    offset = payload["rim_offset_m"].astype(np.float64)
    weight = payload["rim_weight"].astype(np.float64)
    alpha_deg = np.degrees(payload["rim_alpha_rad"].astype(np.float64))
    distance = payload["rim_distance_m"].astype(np.float64)
    found = payload["rim_found"].astype(bool)
    slant = np.linalg.norm(offset, axis=1)
    if not found.any():
        return {"azimuths": int(found.size), "polylines": 0, "sites": 0}

    live = weight[found]
    shade, low, high = rim_shading(weight, found)
    rgba = shade(weight)
    radius, lift = rim_tube(slant, width_scale)
    tip = hero + offset + np.column_stack([np.zeros_like(lift), np.zeros_like(lift), lift])

    # A tip beyond the drawn crop is a real measurement with no building under it in
    # this file, so on its own it reads as debris hanging in the air. It goes into a
    # second object that starts hidden rather than being dropped.
    inside = np.linalg.norm(tip[:, :2], axis=1) <= drawn_radius_m
    beyond = int(np.count_nonzero(found & ~inside))
    if not (found & inside).any():
        inside = np.ones_like(found)
    azimuth_deg = np.degrees(payload["rim_azimuth_rad"].astype(np.float64))

    def rim_object(name: str, keep: np.ndarray) -> tuple[Any, list[np.ndarray]]:
        runs = rim_polylines(found & keep, offset, break_fraction=RIM_BREAK_FRACTION)
        if not runs:
            return None, runs
        order = np.concatenate(runs)
        drawn = build_curves(name, tip[order], np.array([run.size for run in runs]), radius[order], into)
        attach_point_colour(drawn, "direct_flux", rgba[order])
        attach_point_colour(drawn, "distance_m", colour_ramp(distance[order], distance[found].min(), distance.max()))
        attach_point_colour(drawn, "alpha_deg", colour_ramp(alpha_deg[order], alpha_deg[found].min(), alpha_deg.max()))
        attach_values(drawn, "value_direct_flux", weight[order], "POINT")
        attach_values(drawn, "value_distance_m", distance[order], "POINT")
        attach_values(drawn, "value_alpha_deg", alpha_deg[order], "POINT")
        attach_values(drawn, "value_azimuth_deg", azimuth_deg[order], "POINT")
        assign(drawn, emissive_material("skyline_rim", "direct_flux", strength=RIM_EMISSION_STRENGTH))
        layered(drawn, ("direct_flux", "distance_m", "alpha_deg"), "direct_flux")
        return drawn, runs

    obj, runs = rim_object("skyline_rim", inside)
    far, far_runs = rim_object("skyline_rim_beyond_the_drawn_mesh", ~inside)
    if far is not None:
        far.hide_render = True
        far.hide_viewport = True
        far["why_it_is_hidden"] = (
            "these tips are further out than the mesh this file draws, so nothing holds them up "
            "here. They are measured the same way and they count the same in the law."
        )
        far["polylines"] = len(far_runs)
        far["azimuths"] = beyond

    # Uniform in azimuth rather than in arc length, because the law is a mean over
    # azimuth and one azimuth is one site. Spacing them along the rim instead would
    # crowd the far facades, which are the ones carrying least.
    pick = np.arange(0, found.size, max(site_step, 1))
    pick = pick[found[pick] & inside[pick]]
    vertices, faces = octahedra(tip[pick], RIM_SITE_RADII * radius[pick])
    sites = build_mesh("skyline_sites", vertices, faces, into)
    attach_face_colour(sites, "direct_flux", np.repeat(rgba[pick], 8, axis=0))
    attach_values(sites, "value_direct_flux", np.repeat(weight[pick], 8), "FACE")
    assign(sites, emissive_material("skyline_sites", "direct_flux", strength=RIM_EMISSION_STRENGTH))

    law = "a site stands on the facade tip, one per azimuth, at the elevation and range of the tip"
    for drawn in (obj, far, sites):
        if drawn is None:
            continue
        drawn["law"] = law
        drawn["direct_flux_is"] = "cos squared of the tip elevation over its horizontal distance, per azimuth"
        drawn["direct_flux_range"] = [float(live.min()), float(live.max())]
        drawn["shaded_over_log10"] = [low, high]
        drawn["ramp_entered_at"] = RIM_RAMP_FLOOR
        drawn["emission_strength"] = RIM_EMISSION_STRENGTH
        drawn["azimuths"] = int(found.size)
        drawn["azimuths_with_no_tip"] = int(np.count_nonzero(~found))
        drawn["tips_outside_the_drawn_mesh"] = beyond
        drawn["measured_from"] = "the hero standpoint, so it is the skyline that pedestrian sees"
    if obj is not None:
        obj["polylines"] = len(runs)
        obj["cut_where_the_tip_steps_by"] = RIM_BREAK_FRACTION
        obj["radius_m_is"] = f"{width_scale:g} times the square root of the slant range, not the flux"
        obj["drawn_metres_above_the_tip"] = [float(lift.min()), float(lift.max())]
        obj["why_it_is_lifted"] = (
            "a tip is often a roof ridge behind the facade, and a tube centred on it sits half "
            "inside the roof. Only the height moves, by two tube radii."
        )
    sites["azimuth_step_deg"] = 360.0 * site_step / found.size
    sites["radius_m_is"] = f"{RIM_SITE_RADII:g} times the rim radius, so size carries range and colour carries flux"
    return {
        "azimuths": int(found.size),
        "azimuths_with_no_tip": int(np.count_nonzero(~found)),
        "polylines": len(runs),
        "polylines_beyond_the_drawn_mesh": len(far_runs),
        "sites": int(pick.size),
        "tips_outside_the_drawn_mesh": beyond,
        "direct_flux_range": [float(live.min()), float(live.max())],
    }


def build_network(
    payload: Any, hero: np.ndarray, manifest: dict, into: Any, *, width_scale: float, site_step: int
) -> dict[str, object]:
    """Where the sources are, on the facade tips they stand on.

    A site sits on the tip of a facade, the top edge where the wall meets the sky,
    and there is no mast under it. One azimuth therefore carries one source, at the
    elevation and the range of the tip visible along it, and what that draws is a
    rim of light along the rooflines.

    The band population is still built and starts hidden. A height band and a range
    band draw a shell of points floating in the air, which is not where a base
    station is, and it is the geometry the trace in this same payload integrated, so
    dropping it would leave the picture and the numbers with nothing connecting them.
    Each cloud says on itself which of the two it is.
    """
    counts: dict[str, object] = {}
    if "rim_offset_m" in payload.files:
        counts["facade_tip_rim"] = build_rim(
            payload,
            hero,
            into,
            drawn_radius_m=float(manifest["drawn_radius_m"]),
            width_scale=width_scale,
            site_step=site_step,
        )
    for name in MODEL_NAMES:
        positions = payload[f"network_{name}"]
        counts[name] = int(positions.shape[0])
        if positions.shape[0] == 0:
            continue
        vertices, faces = octahedra(hero + positions, 1.6)
        obj = build_mesh(f"sources_{name}", vertices, faces, into)
        assign(obj, emissive_material(f"sources_{name}", None, (0.95, 0.85, 0.25)))
        obj["model"] = name
        obj["drawn_from"] = "a height band and a range band, uniform in azimuth"
        obj["superseded_by"] = "skyline_rim, which puts the sources on the facade tips instead"
        obj.hide_render = True
        obj.hide_viewport = True
    return counts


def build_next_event(
    payload: Any,
    into: Any,
    *,
    drawn_radius_m: float,
    ray_radius: float,
    line_radius: float,
    sky_leg_m: float,
) -> dict[str, object]:
    """A few dozen rays, and the connection every scattering vertex of them makes.

    In a standalone next-event payload this is the estimator in one picture. In a
    production escape payload the same geometry is labeled source evidence. It
    supplies no angular spectrum or body result there. A ray leaves the head,
    bounces off the buildings, and each vertex is connected to a sampled facade tip.

    A few dozen paths rather than the nine hundred in ``09 ray paths by fate``,
    because the answer here is how the method works and a dense fan hides it.

    A clear connection is bright and a blocked one is dark red and thinner.
    Blender's curve strands have no dash pattern, so the difference is carried by
    colour and thickness, and it is also on the points as ``value_blocked`` to be
    read exactly. Switching to the ``contribution`` layer shades each clear
    connection by the flux of the site it reached instead, which is the same number
    the rim is shaded by.
    """
    source_arm = _payload_text(payload, "source_estimator_arm")
    object_prefix = "source_evidence" if source_arm else "estimator"
    origin = payload["nee_origin_m"].astype(np.float64)
    site = payload["nee_site_m"].astype(np.float64)
    blocked = payload["nee_blocked"].astype(bool)
    weight = payload["nee_weight"].astype(np.float64)
    depth = payload["nee_vertex_index"].astype(np.int64)
    picked = payload["nee_paths"].astype(np.int64)

    # A connection is drawn only when the site it lands on is drawn. The tips beyond
    # the crop this file holds are hidden, and a line running out to one of them ends
    # in empty air, which is the one thing this picture must not show. The connection
    # was still cast and still counted. The crop is a disc about the scene origin
    # rather than about the head, which is the same test ``crop_for_drawing`` ran on
    # the mesh, so the two cannot disagree.
    on_the_drawn_mesh = np.linalg.norm(site[:, :2], axis=1) <= drawn_radius_m
    left_out = int(np.count_nonzero(~on_the_drawn_mesh))
    if on_the_drawn_mesh.any():
        origin = origin[on_the_drawn_mesh]
        site = site[on_the_drawn_mesh]
        blocked = blocked[on_the_drawn_mesh]
        weight = weight[on_the_drawn_mesh]
        depth = depth[on_the_drawn_mesh]

    vertices = payload["path_vertices"].astype(np.float64)
    offsets = payload["path_offsets"].astype(np.int64)
    keep = path_slice(offsets, picked)
    lengths = offsets[picked + 1] - offsets[picked]
    drawn = shorten_sky_legs(vertices[keep], lengths, reach=sky_leg_m)
    rays = build_curves(f"{object_prefix}_rays", drawn, lengths, np.full(keep.size, ray_radius), into)
    attach_point_colour(rays, "ray", np.tile((*NEE_RAY_COLOUR, 1.0), (keep.size, 1)), byte=False)
    assign(rays, emissive_material(f"{object_prefix}_rays", "ray"))
    rays["paths_drawn"] = int(picked.size)
    rays["reading"] = "the same recorded paths as 09, thinned to a readable few dozen"
    if role := _payload_text(payload, "visible_path_role"):
        rays["role"] = role
    rays["last_leg_shortened_to_m"] = sky_leg_m
    rays["what_that_changes"] = (
        "only the drawn length of the leg that left the scene. In 09 it runs to the sky sphere "
        "176 m out, which here would push every ray past the frame and hide the connections. "
        "Its direction is untouched and no other vertex moves."
    )

    # Two points per connection, so one curves object holds them all and each end
    # can carry its own colour.
    ends = np.empty((origin.shape[0] * 2, 3))
    ends[0::2], ends[1::2] = origin, site
    shade, _, _ = rim_shading(payload["rim_weight"], payload["rim_found"])
    contribution = np.repeat(shade(weight), 2, axis=0)
    dark = np.repeat(blocked, 2)
    contribution[dark] = (*NEE_BLOCKED_COLOUR, 1.0)
    visibility = np.where(dark[:, None], np.array([*NEE_BLOCKED_COLOUR, 1.0]), np.array([*NEE_CLEAR_COLOUR, 1.0]))
    lines = build_curves(
        f"{object_prefix}_connections",
        ends,
        np.full(origin.shape[0], 2),
        np.repeat(np.where(blocked, 0.75 * line_radius, line_radius), 2),
        into,
    )
    attach_point_colour(lines, "visibility", visibility, byte=False)
    attach_point_colour(lines, "contribution", contribution, byte=False)
    attach_values(lines, "value_direct_flux", np.repeat(weight, 2), "POINT")
    attach_values(lines, "value_blocked", np.repeat(blocked.astype(np.int32), 2), "POINT")
    attach_values(lines, "value_bounce_index", np.repeat(depth, 2), "POINT")
    assign(lines, emissive_material(f"{object_prefix}_connections", "visibility", strength=RIM_EMISSION_STRENGTH))
    layered(lines, ("visibility", "contribution"), "visibility")
    lines["connections"] = int(origin.shape[0])
    lines["blocked"] = int(np.count_nonzero(blocked))
    lines["from_the_head"] = int(np.count_nonzero(depth == 0))
    lines["blocked_from_the_head"] = int(np.count_nonzero(blocked & (depth == 0)))
    lines["sites_sampled"] = "uniformly in azimuth on the facade tip, one per scattering vertex"
    lines["reading"] = (
        "one straight visibility line per sampled roofline site. This is source evidence and supplies no exposure value"
        if source_arm
        else "one straight line per contribution. Dark red carries nothing, something is in the way"
    )
    if source_arm:
        lines["evidence_arm"] = source_arm
    lines["connections_left_out"] = left_out
    lines["why_they_are_left_out"] = (
        "the site they reached is further out than the mesh this file draws, so the line would "
        "end in empty air. They were cast and counted the same as the rest."
    )
    return {
        "paths": int(picked.size),
        "connections": int(origin.shape[0]),
        "blocked": int(np.count_nonzero(blocked)),
        "blocked_from_the_head": int(np.count_nonzero(blocked & (depth == 0))),
        "left_out_beyond_the_drawn_mesh": left_out,
    }


def build_walk(payload: Any, into: Any, model: str) -> tuple[float, float]:
    """Every traced standpoint, coloured by susceptibility in decibels."""
    points = payload["walk_points"].astype(np.float64)
    chi = payload[f"walk_chi_{model}"].astype(np.float64)
    db = 10.0 * np.log10(np.maximum(chi, 1.0e-12))
    low, high = float(db.min()), float(db.max())
    vertices, faces = octahedra(points, 1.0)
    obj = build_mesh("walk_standpoints", vertices, faces, into)
    attach_face_colour(obj, "chi_db", np.repeat(colour_ramp(db, low, high), 8, axis=0))
    assign(obj, emissive_material("walk_chi", "chi_db"))
    obj["illumination_model"] = model
    obj["chi_db_range"] = [low, high]
    if arm := _payload_text(payload, "exposure_estimator_arm"):
        obj["estimator_arm"] = arm
    return low, high


def build_body(payload: Any, hero: np.ndarray, ground_z: float, into: Any) -> tuple[float, float]:
    """The phantom at the hero standpoint, coloured by absorbed power density."""
    sab = payload["body_sab_w_m2"].astype(np.float64)
    placed = place_body(payload["body_vertices"], hero, ground_z)
    obj = build_mesh("phantom_sab", placed, payload["body_faces"], into)
    low, high = float(sab.min()), float(sab.max())
    attach_face_colour(obj, "sab", colour_ramp(sab, low, high))
    assign(obj, emissive_material("phantom_sab", "sab"))
    obj["sab_w_m2_range"] = [low, high]
    obj["phantom"] = "duke, IT'IS adult male"
    if arm := _payload_text(payload, "exposure_estimator_arm"):
        obj["estimator_arm"] = arm
    return low, high
