"""Stage two of the propagation walkthrough: build the blend from the payload.

Everything in the scene is measured. The mesh is the support mesh the rays were
cast against, the ray polylines are the paths the estimator integrated, the lobe
is the angular power spectrum it accumulated, and the colours on the phantom are
the absorbed power density AEGIS returned for that spectrum. Nothing is drawn to
illustrate a number that was computed elsewhere.

The blend is deliberately austere. No textures, no packed images, no tile
imports, vertex colours only, and compression on. A textured 3D Tiles scene of
the same square is around ten times the size and says nothing about propagation,
so ``render_showcase.py`` remains the place to go for a photographic view.

Run it through headless Blender::

    ~/blender-4.5/blender --background --python propagation_blender.py -- \
        --payload outputs/propagation_viz/korenmarkt_payload.npz \
        --manifest outputs/propagation_viz/korenmarkt_manifest.json \
        --blend outputs/propagation_viz/korenmarkt_propagation.blend

Collections, and what each one answers:

``twin``     the geometry, tinted by the surface class that set its material
``rays``     five exclusive bundles of the recorded paths, thickness by throughput
``arrival``  the angular power spectrum at the hero standpoint, one lobe per model
``network``  where the illumination model's sources sit, at true range and height
``walk``     every traced standpoint, coloured by its susceptibility
``body``     the phantom at the hero standpoint, coloured by absorbed power density
"""

from __future__ import annotations

import argparse
import json
import math
import pathlib
import sys

import bpy
import numpy as np

MODEL_NAMES = ("isotropic", "rooftop", "street_small_cell")

#: Elevation support of each directional model, degrees. Only used to sort the
#: recorded rays into the bundle that carries that model's power, so a reader
#: can see which escapes matter and which merely escape.
MODEL_BANDS = {"rooftop": (3.1, 60.1), "street_small_cell": (0.95, 33.0)}

#: Surface class tints, matching the class order of
#: ``semantic_twin.propagation.scene.CLASS_NAMES``.
CLASS_TINT = {
    "ground": (0.28, 0.27, 0.26),
    "facade": (0.55, 0.42, 0.34),
    "roof": (0.34, 0.36, 0.42),
    "soffit": (0.22, 0.23, 0.25),
}

#: Ray bundle name -> (emission colour, whether it is on by default).
RAY_STYLE = {
    "direct_sky_in_rooftop_band": ((1.00, 0.42, 0.10), True),
    "direct_sky_elsewhere": ((0.16, 0.52, 0.95), True),
    "multipath_to_rooftop_band": ((1.00, 0.78, 0.30), True),
    "multipath_elsewhere": ((0.30, 0.75, 0.85), True),
    "stopped_in_the_scene": ((0.45, 0.10, 0.22), True),
}

#: Nine anchors of the matplotlib inferno map. Blender ships no matplotlib and
#: adding one to a headless render for a colour ramp would be absurd.
INFERNO = np.array(
    [
        [0.001462, 0.000466, 0.013866],
        [0.087411, 0.044556, 0.224813],
        [0.258234, 0.038571, 0.406485],
        [0.416331, 0.090203, 0.432943],
        [0.578304, 0.148039, 0.404411],
        [0.735683, 0.215906, 0.330245],
        [0.865006, 0.316822, 0.226055],
        [0.954506, 0.468744, 0.099874],
        [0.988260, 0.652325, 0.211364],
    ]
)


def colour_ramp(values: np.ndarray, low: float, high: float) -> np.ndarray:
    """Map values to inferno RGBA, clamped to ``[low, high]``."""
    span = max(high - low, 1.0e-30)
    t = np.clip((np.asarray(values, dtype=np.float64) - low) / span, 0.0, 1.0)
    position = t * (INFERNO.shape[0] - 1)
    lower = np.floor(position).astype(int)
    upper = np.minimum(lower + 1, INFERNO.shape[0] - 1)
    blend = (position - lower)[:, None]
    rgb = INFERNO[lower] * (1.0 - blend) + INFERNO[upper] * blend
    return np.column_stack([rgb, np.ones(rgb.shape[0])])


def reset_scene() -> None:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0
    scene.render.engine = "CYCLES"
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080
    scene.cycles.samples = 96
    scene.view_settings.view_transform = "Standard"


def collection(name: str) -> bpy.types.Collection:
    made = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(made)
    return made


def build_mesh(name: str, vertices: np.ndarray, faces: np.ndarray, into: bpy.types.Collection) -> bpy.types.Object:
    mesh = bpy.data.meshes.new(name)
    mesh.vertices.add(len(vertices))
    mesh.vertices.foreach_set("co", np.ascontiguousarray(vertices, dtype=np.float32).ravel())
    mesh.loops.add(faces.size)
    mesh.loops.foreach_set("vertex_index", np.ascontiguousarray(faces, dtype=np.int32).ravel())
    mesh.polygons.add(len(faces))
    mesh.polygons.foreach_set("loop_start", np.arange(len(faces), dtype=np.int32) * 3)
    mesh.polygons.foreach_set("loop_total", np.full(len(faces), 3, dtype=np.int32))
    mesh.update(calc_edges=True)
    mesh.validate(verbose=False)
    if len(mesh.polygons) != len(faces):
        raise RuntimeError(
            f"{name}: Blender kept {len(mesh.polygons)} of {len(faces)} triangles, so every "
            "per face colour after the first dropped one is shifted. Fix the payload."
        )
    obj = bpy.data.objects.new(name, mesh)
    into.objects.link(obj)
    return obj


def attach_face_colour(obj: bpy.types.Object, name: str, rgba: np.ndarray) -> None:
    """Store one colour per face on the corner domain, which shaders read directly."""
    attribute = obj.data.color_attributes.new(name=name, type="FLOAT_COLOR", domain="CORNER")
    corner = np.repeat(np.ascontiguousarray(rgba, dtype=np.float32), 3, axis=0)
    attribute.data.foreach_set("color", corner.ravel())


def emissive_material(name: str, channel: str | None, colour: tuple[float, float, float] = (1.0, 1.0, 1.0)):
    """A pure emitter, either at a fixed colour or at a colour attribute.

    Emission rather than a lit BSDF because these layers encode a measured
    number. A lit surface multiplies that number by whatever the lighting does,
    and two values that differ only in hue stop being distinguishable exactly
    where the reader is counting on them.
    """
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    tree = material.node_tree
    tree.nodes.clear()
    emission = tree.nodes.new("ShaderNodeEmission")
    emission.inputs["Strength"].default_value = 1.0
    output = tree.nodes.new("ShaderNodeOutputMaterial")
    if channel is None:
        emission.inputs["Color"].default_value = (*colour, 1.0)
    else:
        attribute = tree.nodes.new("ShaderNodeAttribute")
        attribute.attribute_name = channel
        attribute.location = (-300, 0)
        tree.links.new(attribute.outputs["Color"], emission.inputs["Color"])
    tree.links.new(emission.outputs["Emission"], output.inputs["Surface"])
    return material


def lit_material(name: str, channel: str):
    """A matte surface tinted by a colour attribute, for the geometry itself."""
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    tree = material.node_tree
    principled = tree.nodes["Principled BSDF"]
    principled.inputs["Roughness"].default_value = 0.85
    principled.inputs["Specular IOR Level"].default_value = 0.15
    attribute = tree.nodes.new("ShaderNodeAttribute")
    attribute.attribute_name = channel
    attribute.location = (-300, 300)
    tree.links.new(attribute.outputs["Color"], principled.inputs["Base Color"])
    return material


def assign(obj: bpy.types.Object, material) -> None:
    obj.data.materials.append(material)


def build_twin(payload, class_names: list[str], into: bpy.types.Collection) -> bpy.types.Object:
    vertices = payload["mesh_vertices"]
    faces = payload["mesh_faces"]
    face_class = payload["mesh_face_class"]
    tint = np.array([CLASS_TINT.get(name, (0.4, 0.4, 0.4)) for name in class_names])
    rgba = np.column_stack([tint[face_class], np.ones(face_class.size)])
    obj = build_mesh("support_mesh", vertices, faces, into)
    attach_face_colour(obj, "surface_class", rgba)
    assign(obj, lit_material("twin_surface", "surface_class"))
    return obj


def elevation_deg(directions: np.ndarray) -> np.ndarray:
    return np.degrees(np.arcsin(np.clip(directions[:, 2], -1.0, 1.0)))


def ray_bundles(payload, terminations: list[str]) -> dict[str, np.ndarray]:
    """Sort recorded paths into five exclusive bundles.

    The split is by what happened to the ray, not by how it looks. A ray either
    left the scene or died in it, and if it left, it either left into the
    elevation band the rooftop model illuminates from or it did not. That last
    distinction is the one worth drawing: an escape outside the band contributes
    nothing under that model no matter how far it travelled.
    """
    sky = terminations.index("sky")
    escaped = payload["path_termination"] == sky
    bounced = payload["path_bounces"] > 0
    low, high = MODEL_BANDS["rooftop"]
    band = (elevation_deg(payload["path_exit_direction"]) >= low) & (
        elevation_deg(payload["path_exit_direction"]) <= high
    )
    return {
        "direct_sky_in_rooftop_band": escaped & ~bounced & band,
        "direct_sky_elsewhere": escaped & ~bounced & ~band,
        "multipath_to_rooftop_band": escaped & bounced & band,
        "multipath_elsewhere": escaped & bounced & ~band,
        "stopped_in_the_scene": ~escaped,
    }


def build_rays(payload, terminations: list[str], into: bpy.types.Collection, *, base_radius: float) -> dict[str, int]:
    """One poly curve object per bundle, with point radius carrying throughput.

    Throughput spans several decades along a multi bounce path, so the radius is
    the cube root of it. That keeps a fourth bounce visible instead of
    vanishing, and it is monotone, so thicker still means more power.
    """
    vertices = payload["path_vertices"]
    offsets = payload["path_offsets"]
    throughput = payload["path_throughput"]
    counts: dict[str, int] = {}
    for name, mask in ray_bundles(payload, terminations).items():
        indices = np.flatnonzero(mask)
        counts[name] = int(indices.size)
        curve = bpy.data.curves.new(name, type="CURVE")
        curve.dimensions = "3D"
        curve.bevel_depth = base_radius
        curve.bevel_resolution = 1
        curve.use_fill_caps = True
        for i in indices:
            start, stop = int(offsets[i]), int(offsets[i + 1])
            points = vertices[start:stop]
            spline = curve.splines.new("POLY")
            spline.points.add(points.shape[0] - 1)
            homogeneous = np.column_stack([points, np.ones(points.shape[0])]).astype(np.float32)
            spline.points.foreach_set("co", homogeneous.ravel())
            radius = np.cbrt(np.clip(throughput[start:stop], 1.0e-6, None)).astype(np.float32)
            spline.points.foreach_set("radius", radius)
        obj = bpy.data.objects.new(name, curve)
        into.objects.link(obj)
        colour, visible = RAY_STYLE[name]
        assign(obj, emissive_material(f"ray_{name}", None, colour))
        obj.hide_render = not visible
    return counts


def octahedra(centres: np.ndarray, radius: np.ndarray | float) -> tuple[np.ndarray, np.ndarray]:
    """A marker mesh: one eight sided diamond per centre, in one triangle soup."""
    unit = np.array(
        [[1.0, 0.0, 0.0], [-1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, -1.0, 0.0], [0.0, 0.0, 1.0], [0.0, 0.0, -1.0]]
    )
    template = np.array(
        [[0, 2, 4], [2, 1, 4], [1, 3, 4], [3, 0, 4], [2, 0, 5], [1, 2, 5], [3, 1, 5], [0, 3, 5]], dtype=np.int64
    )
    count = centres.shape[0]
    scale = np.full(count, radius) if np.isscalar(radius) else np.asarray(radius, dtype=np.float64)
    vertices = (centres[:, None, :] + scale[:, None, None] * unit[None, :, :]).reshape(-1, 3)
    faces = (template[None, :, :] + 6 * np.arange(count)[:, None, None]).reshape(-1, 3)
    return vertices, faces


def build_arrival(
    payload,
    hero: np.ndarray,
    into: bpy.types.Collection,
    *,
    scale_m: float,
    offset_m: float,
    floor: float,
) -> dict[str, float]:
    """One lobe per illumination model: the angular power spectrum as a surface.

    Radius is `rho(u)` normalised by the model's own maximum, so the three lobes
    are shape comparable rather than level comparable. Their levels differ by
    two orders of magnitude and drawing that faithfully would leave two of them
    invisible. The level is on the object as a custom property and in the
    manifest instead.

    The lobe belongs at the standpoint and is drawn ``offset_m`` above it, or it
    would enclose the phantom standing there and neither would be readable.
    Only the centre moves. Every direction and every radius is unchanged, and
    the offset is recorded on the object.
    """
    grid = payload["local_grid"].astype(np.float64)
    faces = payload["local_grid_faces"]
    centre = hero + np.array([0.0, 0.0, offset_m])
    peaks: dict[str, float] = {}
    for name in MODEL_NAMES:
        rho = payload[f"rho_{name}"].astype(np.float64)
        peak = float(rho.max())
        peaks[name] = peak
        # A directional model puts almost all of its measure in a narrow
        # elevation band, so the bare lobe is a pancake a few centimetres thick
        # at this scale, which is correct and unreadable. The floor keeps the
        # surface closed and turns the lobe into a bulge on a small sphere, the
        # way an antenna pattern is normally drawn. It compresses the low end
        # and nothing else: the ordering and the peak direction are untouched.
        shape = rho / peak if peak > 0.0 else rho
        radius = scale_m * (floor + (1.0 - floor) * shape)
        obj = build_mesh(f"arrival_{name}", centre + radius[:, None] * grid, faces, into)
        obj["drawn_metres_above_the_standpoint"] = offset_m
        obj["radius_floor_fraction"] = floor
        attach_face_colour(obj, "power", colour_ramp(rho[faces].mean(axis=1), 0.0, peak))
        assign(obj, emissive_material(f"arrival_{name}", "power"))
        obj["peak_rho_per_sr"] = peak
        obj["normalised_by"] = "its own peak, so shape is comparable across models and level is not"
        obj.hide_render = name != "rooftop"
    return peaks


def build_network(payload, hero: np.ndarray, into: bpy.types.Collection) -> dict[str, int]:
    """Source markers at true horizontal range and true height above the head."""
    counts: dict[str, int] = {}
    for name in MODEL_NAMES:
        positions = payload[f"network_{name}"]
        counts[name] = int(positions.shape[0])
        if positions.shape[0] == 0:
            continue
        vertices, faces = octahedra(hero + positions, 1.6)
        obj = build_mesh(f"sources_{name}", vertices, faces, into)
        assign(obj, emissive_material(f"sources_{name}", None, (0.95, 0.85, 0.25)))
        obj["model"] = name
        obj.hide_render = name != "rooftop"
    return counts


def build_walk(payload, into: bpy.types.Collection, model: str) -> tuple[float, float]:
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
    return low, high


def build_body(payload, hero: np.ndarray, ground_z: float, into: bpy.types.Collection) -> tuple[float, float]:
    """The phantom at the hero standpoint, coloured by absorbed power density.

    The mesh arrives in metres with its own origin, so it is placed by its own
    feet on the local ground rather than by assuming where that origin sits.
    """
    vertices = payload["body_vertices"].astype(np.float64)
    faces = payload["body_faces"]
    sab = payload["body_sab_w_m2"].astype(np.float64)
    centre = vertices.mean(axis=0)
    placed = vertices - np.array([centre[0], centre[1], vertices[:, 2].min()]) + np.array([hero[0], hero[1], ground_z])
    obj = build_mesh("phantom_sab", placed, faces, into)
    low, high = float(sab.min()), float(sab.max())
    attach_face_colour(obj, "sab", colour_ramp(sab, low, high))
    assign(obj, emissive_material("phantom_sab", "sab"))
    obj["sab_w_m2_range"] = [low, high]
    obj["phantom"] = "duke, IT'IS adult male"
    return low, high


def camera_rotation(location: np.ndarray, target: np.ndarray) -> tuple[float, float, float]:
    """XYZ Euler angles aiming a Blender camera from ``location`` at ``target``.

    A Blender camera looks down its own -Z with +Y up, so this solves
    ``Rz(rz) Rx(rx) (0, 0, -1) = d``. That gives ``rx`` from ``-dz`` and ``rz``
    from ``(-dx, dy)``. Every other arrangement of those signs aims somewhere
    plausible looking and wrong, and the failure is a black frame or a view of
    the inside of a roof rather than an error.
    """
    direction = np.asarray(target, dtype=np.float64) - np.asarray(location, dtype=np.float64)
    direction = direction / max(float(np.linalg.norm(direction)), 1.0e-12)
    return (
        math.acos(float(np.clip(-direction[2], -1.0, 1.0))),
        0.0,
        math.atan2(-direction[0], direction[1]),
    )


def add_camera(name: str, location, target, into: bpy.types.Collection, *, lens: float = 35.0):
    data = bpy.data.cameras.new(name)
    data.lens = lens
    data.clip_end = 8000.0
    obj = bpy.data.objects.new(name, data)
    into.objects.link(obj)
    obj.location = tuple(float(v) for v in location)
    obj.rotation_euler = camera_rotation(location, target)
    return obj


def free_distance(
    twin: bpy.types.Object, subject: np.ndarray, direction: np.ndarray, reach: float
) -> tuple[float, bool]:
    """How far a ray from ``subject`` gets, and whether anything stopped it.

    The two are not the same question. A ray that runs out of ``reach`` and a
    ray that hits a wall at ``reach`` return the same distance, and only the
    second one needs a standoff.
    """
    hit, location, _, _ = twin.ray_cast(subject, direction, distance=reach)
    if not hit:
        return reach, False
    return float(np.linalg.norm(np.asarray(location, dtype=np.float64) - subject)), True


def clear_view(
    twin: bpy.types.Object,
    subject: np.ndarray,
    reach: float,
    elevations_deg: tuple[float, ...],
    *,
    azimuths: int = 24,
    margin: float = 0.82,
) -> np.ndarray:
    """Find a camera position at roughly ``reach`` metres that can see the subject.

    A fixed offset frames a square with fifteen metre eaves and fails anywhere
    else. At Times Square it puts the camera inside a tower. The obvious repair,
    casting along the wanted direction and stopping short of the first hit, is
    worse than it looks: on a blocked bearing it does not find a view, it just
    parks the camera twelve metres away inside the ray fan it was meant to
    photograph.

    So search instead. A canyon has clear bearings, up the street and upward,
    and this finds the best one available rather than insisting on a bearing
    chosen for a different city. Ties break towards the lower elevation, which
    keeps a three quarter view wherever a three quarter view exists and only
    climbs overhead when nothing else is open.
    """
    best_offset = np.array([0.0, 0.0, reach])
    best_free = -1.0
    for elevation in elevations_deg:
        vertical = math.sin(math.radians(elevation))
        horizontal = math.cos(math.radians(elevation))
        for step in range(azimuths):
            azimuth = 2.0 * math.pi * step / azimuths
            direction = np.array([horizontal * math.cos(azimuth), horizontal * math.sin(azimuth), vertical])
            free, blocked = free_distance(twin, subject, direction, reach)
            if free > best_free + 1.0e-6:
                best_free = free
                # Stand off only from something that is actually there. A
                # bearing that ran out of reach is open, and shortening it
                # would frame every site more tightly than asked for.
                usable = max(margin * free, 3.0) if blocked else free
                best_offset = direction * min(reach, usable)
    return subject + best_offset


def build_cameras(twin: bpy.types.Object, hero: np.ndarray, ground_z: float, into: bpy.types.Collection) -> None:
    """Five cameras, four of them clearance checked and one deliberately not.

    A camera whose subject is at the standpoint has to see it, so it is cast
    towards and stopped short of whatever blocks it. The overview camera is the
    opposite case: it is meant to be outside the scene looking in, and casting
    from the standpoint towards it just finds the nearest facade, which at
    Korenmarkt put a bird's eye view 3.7 m from the observer. It is placed above
    the tallest drawn geometry instead, which is the constraint that actually
    applies to it.
    """
    eye = np.array([hero[0], hero[1], ground_z + 1.6])
    lobe = hero + np.array([0.0, 0.0, 13.0])
    plan = (
        ("cam_rays", hero, 85.0, (28.0, 40.0, 55.0, 72.0), hero, 35.0),
        ("cam_lobe", lobe, 30.0, (8.0, 18.0, 32.0, 55.0), lobe, 35.0),
        ("cam_body", eye, 4.4, (4.0, 12.0, 26.0), eye, 50.0),
    )
    for name, subject, reach, elevations, target, lens in plan:
        location = clear_view(twin, subject, reach, elevations)
        add_camera(name, location, target, into, lens=lens)
        got = location - subject
        print(
            f"[camera] {name} at {np.linalg.norm(got):.1f} m of {reach:.1f} m wanted, "
            f"elevation {math.degrees(math.asin(got[2] / max(np.linalg.norm(got), 1e-9))):.0f} deg",
            flush=True,
        )
    # The pedestrian view is at the standpoint by definition, so it has nothing
    # to clear. It looks along the most open bearing the standpoint has.
    look = clear_view(twin, eye, 60.0, (4.0, 10.0))
    add_camera("cam_pedestrian", eye, eye + 4.0 * (look - eye), into, lens=24.0)

    # The 99th percentile rather than the maximum, so one spurious spike of
    # photogrammetry does not push the whole view into orbit. Times Square has
    # 200 m of exactly that.
    heights = np.empty(len(twin.data.vertices) * 3)
    twin.data.vertices.foreach_get("co", heights)
    ceiling = float(np.quantile(heights.reshape(-1, 3)[:, 2], 0.99))
    above = max(ceiling - hero[2] + 55.0, 90.0)
    add_camera("cam_overview", hero + np.array([0.0, -1.3 * above, above]), hero, into, lens=28.0)
    print(f"[camera] cam_overview {above:.1f} m above the standpoint, ceiling {ceiling:.1f} m", flush=True)
    bpy.context.scene.camera = bpy.data.objects["cam_rays"]


def build_lighting(hero: np.ndarray) -> None:
    world = bpy.data.worlds.new("world")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.02, 0.025, 0.035, 1.0)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 1.0
    bpy.context.scene.world = world
    data = bpy.data.lights.new("sun", type="SUN")
    data.energy = 3.0
    data.angle = math.radians(3.0)
    sun = bpy.data.objects.new("sun", data)
    bpy.context.scene.collection.objects.link(sun)
    sun.location = tuple(hero + np.array([0.0, 0.0, 200.0]))
    sun.rotation_euler = (math.radians(48.0), 0.0, math.radians(-35.0))


#: (figure name, camera, collections to show). One camera is not one figure:
#: the ray fan leaves the standpoint in every direction, so there is no vantage
#: from which it does not cover a close subject, and the arrival lobe and the
#: phantom both sit at the standpoint underneath it. Each figure therefore names
#: what it is about, and the saved blend keeps everything switched on.
FIGURE_VIEWS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("01_the_square", "cam_overview", ("twin",)),
    ("02_where_the_sources_are", "cam_overview", ("twin", "network")),
    ("03_exposure_along_the_walk", "cam_overview", ("twin", "walk")),
    ("04_the_rays_from_one_standpoint", "cam_rays", ("twin", "rays")),
    ("05_standing_in_the_ray_fan", "cam_pedestrian", ("twin", "rays")),
    ("06_what_arrives", "cam_lobe", ("twin", "arrival")),
    ("07_the_body", "cam_body", ("twin", "body")),
)


def render_every_figure(args: argparse.Namespace) -> None:
    """One PNG per entry in :data:`FIGURE_VIEWS`.

    Renders happen after the blend is saved, so the shipped file is the one the
    figures came from and no render setting or visibility toggle leaks into it.
    """
    scene = bpy.context.scene
    scene.cycles.samples = args.samples
    scene.render.resolution_x = int(1920 * args.resolution_scale)
    scene.render.resolution_y = int(1080 * args.resolution_scale)
    scene.render.image_settings.file_format = "PNG"
    args.render_dir.mkdir(parents=True, exist_ok=True)
    for name, camera, shown in FIGURE_VIEWS:
        if camera not in bpy.data.objects:
            raise RuntimeError(f"figure {name} wants camera {camera}, which the scene does not have")
        scene.camera = bpy.data.objects[camera]
        for group in bpy.data.collections:
            for obj in group.objects:
                obj.hide_render = group.name not in shown
        scene.render.filepath = str((args.render_dir / f"{args.blend.stem}_{name}.png").resolve())
        bpy.ops.render.render(write_still=True)
        print(f"[render] {name} from {camera}", flush=True)


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--payload", type=pathlib.Path, required=True)
    parser.add_argument("--manifest", type=pathlib.Path)
    parser.add_argument("--blend", type=pathlib.Path, required=True)
    parser.add_argument("--walk-model", default="rooftop", choices=list(MODEL_NAMES))
    parser.add_argument("--lobe-scale-m", type=float, default=7.0)
    parser.add_argument("--lobe-offset-m", type=float, default=13.0)
    parser.add_argument("--lobe-floor", type=float, default=0.14)
    parser.add_argument("--ray-radius-m", type=float, default=0.11)
    parser.add_argument("--render-dir", type=pathlib.Path, help="Also render one PNG per camera")
    parser.add_argument("--samples", type=int, default=64)
    parser.add_argument("--resolution-scale", type=float, default=1.0)
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    return parser.parse_args(argv)


def main() -> int:
    args = arguments()
    payload = np.load(args.payload)
    manifest_path = args.manifest or args.payload.with_name(args.payload.name.replace("_payload.npz", "_manifest.json"))
    manifest = json.loads(manifest_path.read_text())

    reset_scene()
    hero = payload["hero_point"].astype(np.float64)
    ground_z = float(payload["walk_ground_z_m"][int(payload["hero_index"])])

    twin = build_twin(payload, manifest["class_names"], collection("twin"))
    rays = build_rays(payload, manifest["terminations"], collection("rays"), base_radius=args.ray_radius_m)
    peaks = build_arrival(
        payload,
        hero,
        collection("arrival"),
        scale_m=args.lobe_scale_m,
        offset_m=args.lobe_offset_m,
        floor=args.lobe_floor,
    )
    sources = build_network(payload, hero, collection("network"))
    walk_range = build_walk(payload, collection("walk"), args.walk_model)
    sab_range = build_body(payload, hero, ground_z, collection("body"))
    build_cameras(twin, hero, ground_z, collection("cameras"))
    build_lighting(hero)

    scene = bpy.context.scene
    scene["site"] = manifest["site"]
    scene["frequency_ghz"] = manifest["frequency_hz"] / 1.0e9
    scene["traced_crop_radius_m"] = manifest["traced_crop_radius_m"]
    scene["drawn_radius_m"] = manifest["drawn_radius_m"]
    scene["hero_sky_fraction"] = manifest["hero"]["sky_fraction"]
    scene["hero_susceptibility"] = json.dumps(manifest["hero"]["susceptibility"])
    scene["ray_bundle_counts"] = json.dumps(rays)
    scene["reading_note"] = (
        "Every object here is measured. Ray thickness is the cube root of throughput. "
        "The lobes are normalised by their own peak so their shapes compare and their "
        "levels do not. The drawn mesh is smaller than the traced mesh, see "
        "drawn_radius_m against traced_crop_radius_m."
    )

    args.blend.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(args.blend.resolve()), compress=True)

    if args.render_dir is not None:
        render_every_figure(args)

    print(f"[twin] {len(twin.data.polygons)} triangles inside {manifest['drawn_radius_m']:g} m", flush=True)
    print(f"[rays] {rays}", flush=True)
    print(f"[arrival] peak rho per sr { {k: round(v, 5) for k, v in peaks.items()} }", flush=True)
    print(f"[network] {sources} source markers", flush=True)
    print(f"[walk] chi range {walk_range[0]:.2f} to {walk_range[1]:.2f} dB", flush=True)
    print(f"[body] Sab {sab_range[0]:.4g} to {sab_range[1]:.4g} W/m2", flush=True)
    print(f"[done] {args.blend} ({args.blend.stat().st_size / 1e6:.1f} MB)", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
