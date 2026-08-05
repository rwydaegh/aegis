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

import numpy as np

from .payload import (
    available_spectrum_models,
    drawable_ray_legs,
    octahedra,
    place_body,
    ray_bundles,
    rim_polylines,
    rim_shading,
    rim_tube,
    shorten_sky_legs,
    supported_live_scattering_vertices,
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
    angular_law_sample_metadata,
    angular_law_sample_object_name,
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


def _stamp_ray_leg_record(
    obj: Any,
    legs: Any,
    drawn_radius_m: float,
    leg_mask: np.ndarray | None = None,
) -> None:
    """Record every display-only decision made while drawing ray legs."""
    keep = np.ones(legs.lengths.size, dtype=bool) if leg_mask is None else np.asarray(leg_mask, dtype=bool)
    obj["paths_requested"] = legs.paths_requested
    obj["paths_drawn"] = int(np.unique(legs.path_index[keep]).size)
    obj["physical_legs_drawn"] = int(np.count_nonzero(keep))
    obj["escaped_final_legs_drawn"] = int(np.count_nonzero(legs.escaped_final[keep]))
    obj["escaped_final_leg_representation"] = (
        "finite display proxy for a semi-infinite ray; direction is recorded and endpoint is not physical"
    )
    obj["paths_left_out_beyond_drawn_support"] = int(legs.paths_left_out_beyond_drawn_support.size)
    obj["drawn_support_radius_m"] = drawn_radius_m
    obj["why_paths_are_left_out"] = (
        "at least one recorded reflection lies outside the displayed support disc, so drawing it would turn in empty space"
    )
    obj["paths_trimmed_at_exact_zero_throughput"] = int(legs.paths_trimmed_at_zero_throughput.size)
    obj["outgoing_legs_after_zero_throughput_left_out"] = legs.outgoing_legs_after_zero_left_out
    obj["zero_length_terminal_markers_left_out"] = legs.degenerate_legs_left_out
    obj["why_zero_length_markers_are_left_out"] = (
        "roulette and truncated path records can end with a duplicate marker; it records termination and is not a leg"
    )


def build_rays(
    payload: Any,
    terminations: Sequence[str],
    into: Any,
    *,
    base_radius: float,
    drawn_radius_m: float,
) -> dict[str, int]:
    """One straight, constant-throughput curve per physical ray leg.

    A reflection duplicates its support point between two curves. The incoming
    leg keeps its old radius to the surface and the outgoing leg starts at its
    new radius, so no taper is invented between them. Escaped final legs keep
    their recorded direction and finite display endpoint, while the object says
    clearly that the physical ray continues to infinity.
    """
    raw_throughput = payload["path_throughput"].astype(np.float64)
    positive = raw_throughput[raw_throughput > 0.0]
    decibels = 10.0 * np.log10(positive)
    span = (float(np.quantile(decibels, 0.02)), float(decibels.max())) if positive.size else (-90.0, 0.0)
    counts: dict[str, int] = {}
    for name, mask in ray_bundles(payload, terminations).items():
        indices = np.flatnonzero(mask)
        legs = drawable_ray_legs(payload, indices, terminations, drawn_radius_m=drawn_radius_m)
        counts[name] = legs.paths_drawn
        point_throughput = np.repeat(legs.leg_throughput, 2)
        point_path = np.repeat(legs.path_index, 2)
        point_depth = np.repeat(legs.leg_index, 2)
        point_proxy = np.repeat(legs.escaped_final.astype(np.int32), 2)
        point_db = 10.0 * np.log10(np.maximum(point_throughput, np.finfo(np.float64).tiny))
        obj = build_curves(
            name,
            legs.points,
            legs.lengths,
            base_radius * np.cbrt(np.maximum(point_throughput, 0.0)),
            into,
        )
        colour, visible = RAY_STYLE[name]
        attach_point_colour(obj, "fate", np.tile((*colour, 1.0), (legs.points.shape[0], 1)), byte=False)
        attach_point_colour(obj, "power_db", colour_ramp(point_db, *span))
        attach_values(obj, "value_throughput", point_throughput, "POINT")
        attach_values(obj, "value_path_index", point_path, "POINT")
        attach_values(obj, "value_leg_index", point_depth, "POINT")
        attach_values(obj, "value_is_escaped_display_proxy", point_proxy, "POINT")
        obj["colour_layers"] = ["fate", "power_db"]
        obj["power_db_range"] = list(span)
        obj["reading"] = (
            "each straight leg has one constant throughput and radius; power changes discontinuously at a reflection"
        )
        _stamp_ray_leg_record(obj, legs, drawn_radius_m)
        if role := _payload_text(payload, "visible_path_role"):
            obj["role"] = role
        assign(obj, emissive_material(f"ray_{name}", "fate"))
        show_layer(obj, "fate")
        obj.hide_render = not visible
    return counts


def build_ray_depth(
    payload: Any,
    terminations: Sequence[str],
    into: Any,
    *,
    base_radius: float,
    drawn_radius_m: float,
) -> dict[str, int]:
    """The same paths again, cut at the bounces, one object per leg index.

    The five bundles answer where a ray ended. They do not answer how deep it went,
    and depth is the question the bounce budget is about: the panoramas measure the
    material for the first two reflections and nothing measures it after that. A leg
    is one straight segment of a path, so leg zero is what left the standpoint and
    leg two is what carried on after the second surface. Switching the last object
    off shows exactly how much of the fan lives past what the evidence supports.
    """
    legs = drawable_ray_legs(
        payload,
        np.arange(payload["path_bounces"].size),
        terminations,
        drawn_radius_m=drawn_radius_m,
    )
    paired = legs.points.reshape(-1, 2, 3)
    counts: dict[str, int] = {}
    for depth, (colour, name) in enumerate(BOUNCE_STYLE):
        last = depth == len(BOUNCE_STYLE) - 1
        keep = legs.leg_index >= depth if last else legs.leg_index == depth
        power = legs.leg_throughput[keep]
        points = paired[keep].reshape(-1, 3)
        point_power = np.repeat(power, 2)
        counts[name] = int(np.count_nonzero(keep))
        obj = build_curves(
            name,
            points,
            np.full(power.size, 2, dtype=np.int32),
            base_radius * np.cbrt(np.maximum(point_power, 0.0)),
            into,
        )
        attach_values(obj, "value_throughput", point_power, "POINT")
        attach_values(obj, "value_path_index", np.repeat(legs.path_index[keep], 2), "POINT")
        attach_values(obj, "value_leg_index", np.repeat(legs.leg_index[keep], 2), "POINT")
        attach_values(
            obj,
            "value_is_escaped_display_proxy",
            np.repeat(legs.escaped_final[keep].astype(np.int32), 2),
            "POINT",
        )
        assign(obj, emissive_material(f"bounce_{name}", None, colour))
        obj["legs_drawn"] = counts[name]
        obj["reading"] = f"path segments at leg index {depth}" + (" and past it" if last else "")
        _stamp_ray_leg_record(obj, legs, drawn_radius_m, keep)
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
    source_arm = _payload_text(payload, "source_estimator_arm")
    if far is not None:
        far.hide_render = True
        far.hide_viewport = True
        far["why_it_is_hidden"] = (
            "these tips are further out than the mesh this file draws, so nothing holds them up here"
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
    if source_arm:
        law = "roofline source evidence sampled by azimuth; separate from the stored exposure calculation"
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
        if source_arm:
            drawn["estimator_arm"] = source_arm
            drawn["supplies_exposure_values"] = False
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

    The band population is still built and starts hidden. Its points are Monte
    Carlo samples used only to picture the analytic law. The exact points are not
    counted sites and are not passed to the exposure calculation. The population
    they sample does define the analytic law, so each cloud records both facts.
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
        object_name = angular_law_sample_object_name(name)
        obj = build_mesh(object_name, vertices, faces, into)
        assign(obj, emissive_material(object_name, None, (0.95, 0.85, 0.25)))
        for key, value in angular_law_sample_metadata(name).items():
            obj[key] = value
        obj.hide_render = True
        obj.hide_viewport = True
    return counts


def build_next_event(
    payload: Any,
    terminations: Sequence[str],
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
    connection_path = payload["nee_path_index"].astype(np.int64)
    picked = payload["nee_paths"].astype(np.int64)

    legs = drawable_ray_legs(payload, picked, terminations, drawn_radius_m=drawn_radius_m)
    supported_live_origin = supported_live_scattering_vertices(
        payload,
        connection_path,
        depth,
        legs.paths_left_out_beyond_drawn_support,
    )

    # A connection is drawn only when the site it lands on is drawn. The tips beyond
    # the crop this file holds are hidden, and a line running out to one of them ends
    # in empty air, which is the one thing this picture must not show. The connection
    # was still cast and still counted. The crop is a disc about the scene origin
    # rather than about the head, which is the same test ``crop_for_drawing`` ran on
    # the mesh, so the two cannot disagree.
    on_the_drawn_mesh = np.linalg.norm(site[:, :2], axis=1) <= drawn_radius_m
    left_out = int(np.count_nonzero(~on_the_drawn_mesh))
    connection_without_supported_live_origin = int(np.count_nonzero(~supported_live_origin))
    keep_connection = on_the_drawn_mesh & supported_live_origin
    origin = origin[keep_connection]
    site = site[keep_connection]
    blocked = blocked[keep_connection]
    weight = weight[keep_connection]
    depth = depth[keep_connection]

    drawn = shorten_sky_legs(
        legs.points,
        legs.lengths,
        reach=sky_leg_m,
        escaped_final=legs.escaped_final,
    )
    rays = build_curves(
        f"{object_prefix}_rays",
        drawn,
        legs.lengths,
        np.full(drawn.shape[0], ray_radius),
        into,
    )
    attach_point_colour(rays, "ray", np.tile((*NEE_RAY_COLOUR, 1.0), (drawn.shape[0], 1)), byte=False)
    attach_values(rays, "value_path_index", np.repeat(legs.path_index, 2), "POINT")
    attach_values(rays, "value_leg_index", np.repeat(legs.leg_index, 2), "POINT")
    attach_values(
        rays,
        "value_is_escaped_display_proxy",
        np.repeat(legs.escaped_final.astype(np.int32), 2),
        "POINT",
    )
    assign(rays, emissive_material(f"{object_prefix}_rays", "ray"))
    _stamp_ray_leg_record(rays, legs, drawn_radius_m)
    rays["reading"] = "the same straight physical legs as 09, thinned to a readable few dozen"
    if role := _payload_text(payload, "visible_path_role"):
        rays["role"] = role
    rays["last_leg_shortened_to_m"] = sky_leg_m
    rays["what_that_changes"] = (
        "only the finite display proxy for a semi-infinite escaped leg. Its direction is untouched "
        "and no surface-to-surface leg moves."
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
    lines["connections_left_out_at_zero_throughput_or_beyond_support"] = connection_without_supported_live_origin
    lines["why_they_are_left_out"] = (
        "the roofline site lies beyond the displayed mesh, or the connection leaves a zero-throughput "
        "vertex or a path whose reflection lies beyond the displayed support. All were still cast and counted."
    )
    return {
        "paths": legs.paths_drawn,
        "connections": int(origin.shape[0]),
        "blocked": int(np.count_nonzero(blocked)),
        "blocked_from_the_head": int(np.count_nonzero(blocked & (depth == 0))),
        "left_out_beyond_the_drawn_mesh": left_out,
        "left_out_at_zero_throughput_or_beyond_support": connection_without_supported_live_origin,
    }


def _walk_point_kinds(count: int, provenance: dict[str, Any] | None) -> np.ndarray:
    raw = (provenance or {}).get("point_kind")
    if raw is None:
        return np.full(count, "unclassified", dtype=object)
    kinds = np.asarray(raw, dtype=object)
    if kinds.shape != (count,):
        raise ValueError("walk_provenance.point_kind must name every walk point")
    allowed = {"camera_registered", "stride_interpolated", "unclassified"}
    if unknown := sorted(set(kinds) - allowed):
        raise ValueError(f"unsupported walk point kinds: {unknown}")
    return kinds


def _walk_hero_index(payload: Any, supplied: int | None, count: int) -> int:
    hero = int(payload["hero_index"]) if supplied is None and "hero_index" in payload else supplied
    hero = int(hero) if hero is not None else 0
    if not 0 <= hero < count:
        raise IndexError("hero walk index is outside the walk")
    return hero


def build_walk(
    payload: Any,
    into: Any,
    model: str,
    walk_provenance: dict[str, Any] | None = None,
    *,
    hero_index: int | None = None,
) -> tuple[float, float]:
    """The ordered walk, its registered points, and exact susceptibility colours.

    ``walk_standpoints`` stays as the compact QA object it has always been. The
    other objects make the route readable without changing or replacing it: one
    straight polyline joins the points in payload order, small overlays identify
    the registered cameras and interpolated strides, and three larger markers
    identify the start, hero, and end.
    """
    points = payload["walk_points"].astype(np.float64)
    chi = payload[f"walk_chi_{model}"].astype(np.float64)
    if points.shape != (chi.size, 3):
        raise ValueError("walk points and susceptibility must have the same length")
    if chi.size == 0:
        raise ValueError("the Blender walk needs at least one standpoint")

    db = 10.0 * np.log10(np.maximum(chi, 1.0e-12))
    low, high = float(db.min()), float(db.max())
    vertices, faces = octahedra(points, 1.0)
    obj = build_mesh("walk_standpoints", vertices, faces, into)
    attach_face_colour(obj, "chi_db", np.repeat(colour_ramp(db, low, high), 8, axis=0))
    attach_values(obj, "value_chi", np.repeat(chi, 8), "FACE")
    attach_values(obj, "value_chi_db", np.repeat(db, 8), "FACE")
    assign(obj, emissive_material("walk_chi", "chi_db"))
    obj["illumination_model"] = model
    obj["chi_db_range"] = [low, high]
    obj["colour_quantity"] = f"10 log10(max(dimensionless {model} susceptibility chi, 1e-12)), in dB"
    obj["chi_db_floor"] = -120.0
    obj["colour_attribute"] = "chi_db"
    obj["exact_linear_attribute"] = "value_chi"
    obj["exact_db_attribute"] = "value_chi_db"
    obj["marker_order"] = "eight consecutive faces per walk point, in payload order"
    if arm := _payload_text(payload, "exposure_estimator_arm"):
        obj["estimator_arm"] = arm

    route = build_curves(
        "walk_route",
        points,
        np.array([points.shape[0]], dtype=np.int32),
        np.full(points.shape[0], 0.12),
        into,
    )
    attach_values(route, "value_walk_index", np.arange(points.shape[0]), "POINT")
    assign(route, emissive_material("walk_route", None, (0.82, 0.88, 0.94), strength=2.0))
    route["reading"] = "one connected POLY route through the standpoints in payload order"
    route["points"] = int(points.shape[0])
    route["segments"] = int(max(points.shape[0] - 1, 0))
    route["coordinates"] = "exact walk_points coordinates; no smoothing or display offset"

    point_kinds = _walk_point_kinds(points.shape[0], walk_provenance)
    point_styles = {
        "camera_registered": (0.48, (0.06, 0.78, 1.0)),
        "stride_interpolated": (0.30, (0.96, 0.98, 1.0)),
        "unclassified": (0.30, (0.55, 0.58, 0.62)),
    }
    for kind, (radius, colour) in point_styles.items():
        indices = np.flatnonzero(point_kinds == kind)
        if not indices.size:
            continue
        marker_vertices, marker_faces = octahedra(points[indices], radius)
        markers = build_mesh(f"walk_{kind}_points", marker_vertices, marker_faces, into)
        attach_values(markers, "value_walk_index", np.repeat(indices, 8), "FACE")
        assign(markers, emissive_material(f"walk_{kind}", None, colour, strength=2.0))
        markers["point_kind"] = kind
        markers["points"] = int(indices.size)
        markers["walk_indices"] = indices.tolist()
        markers["point_kind_source"] = "manifest.walk_provenance.point_kind"
        markers["reading"] = "small origin marker over the larger susceptibility-coloured standpoint"

    hero = _walk_hero_index(payload, hero_index, points.shape[0])
    role_styles = (
        ("start", 0, (0.18, 1.0, 0.28)),
        ("hero", hero, (1.0, 0.12, 0.82)),
        ("end", points.shape[0] - 1, (1.0, 0.12, 0.04)),
    )
    for role, index, colour in role_styles:
        marker_vertices, marker_faces = octahedra(points[[index]], 1.35)
        marker = build_mesh(f"walk_{role}_marker", marker_vertices, marker_faces, into)
        assign(marker, emissive_material(f"walk_{role}", None, colour, strength=2.4))
        marker["role"] = role
        marker["walk_index"] = index
        marker["point_kind"] = str(point_kinds[index])
        marker["coordinates"] = "exact walk point; no display offset"
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
