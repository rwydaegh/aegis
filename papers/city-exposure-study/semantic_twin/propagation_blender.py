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

``twin``       the geometry, tinted by the surface class that set its material
``rays``       five exclusive bundles of the recorded paths, thickness by throughput
``arrival``    the angular power spectrum at the hero standpoint, one lobe per model
``network``    the sources, on the facade tips, brightest where the flux comes from
``nee``        a few dozen rays with the connection each of them makes to a site
``walk``       every traced standpoint, coloured by its susceptibility
``body``       the phantom at the hero standpoint, coloured by absorbed power density
``semantics``  the fishnet surface sets, one per taxonomy, with their evidence
``evidence``   every support triangle a view considered, clean against withheld
``refused``    what the cutter threw away, one object per reason it was thrown
``depth``      the mesh first hit, and the monocular depth the gate refused
``panoramas``  the registered poses, their covariance and their sky conflict verdict
``bodies``     the SMPL-X bystanders the dynamic layer reconstructed and placed

The last six are only built when the payload carries them, and all of them start
hidden, so a site with no panorama opens exactly as it did before and a site with
one opens just as fast.

A layer is a named attribute, not an object. Every object in those collections
carries its measured quantities twice: once as a float or integer attribute
holding the exact value, which the spreadsheet editor will show, and once as a
colour attribute holding the shaded version. Switching what a surface shows is
therefore a click in the colour attribute list rather than a rebuild, and the
exact number survives next to the picture of it.
"""

from __future__ import annotations

import argparse
import json
import math
import hashlib
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

#: Leg index -> emission colour. The first leg is the one that left the
#: standpoint, the second is the one after the first reflection, and so on. The
#: budget stops at three reflections because the panoramas measure the material
#: for the first two, so the fourth entry is everything past what the evidence
#: covers and is deliberately the dimmest.
BOUNCE_STYLE = (
    ((1.00, 0.55, 0.12), "leg_0_before_any_bounce"),
    ((0.98, 0.85, 0.30), "leg_1_after_one_bounce"),
    ((0.45, 0.85, 0.95), "leg_2_after_two_bounces"),
    ((1.00, 0.20, 0.85), "leg_3_and_beyond"),
)

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


def use_gpu() -> str:
    """Point Cycles at whatever accelerator this machine has, or say so and stop.

    Half a million depth points and a quarter of a million ray legs is a minute
    a frame on four contended cores and seconds on the A6000, so the figures are
    worth moving. This is opt in rather than automatic, because a silent
    fallback to the CPU is the failure mode where you wait an hour and never
    learn why.
    """
    preferences = bpy.context.preferences.addons["cycles"].preferences
    for backend in ("OPTIX", "CUDA", "HIP", "METAL", "ONEAPI"):
        preferences.compute_device_type = backend
        preferences.get_devices()
        usable = [device for device in preferences.devices if device.type == backend]
        if not usable:
            continue
        for device in preferences.devices:
            device.use = device.type == backend
        bpy.context.scene.cycles.device = "GPU"
        return f"{backend} on {', '.join(device.name for device in usable)}"
    raise RuntimeError("--gpu asked for, and Cycles found no OPTIX, CUDA, HIP, METAL or ONEAPI device")


#: Internal key -> the name a person reads in the outliner. The keys stay short
#: because the figure table and the build code index on them. The names are
#: written for someone who opens the file having never read this script, which
#: is the only audience the outliner has. Order is the order they are created
#: in, and that is the order they appear in.
COLLECTION_NAMES: dict[str, str] = {
    "twin": "01 city mesh",
    "semantics": "02 semantic surface",
    "evidence": "03 image coverage",
    "refused": "04 refused faces",
    "depth": "05 depth clouds",
    "panoramas": "06 panorama captures",
    "bodies": "07 bystander bodies",
    "walk": "08 walk standpoints",
    "rays": "09 ray paths by fate",
    "bounces": "10 ray paths by bounce",
    "network": "11 sources on the facade tips",
    "nee": "12 next event estimation",
    "arrival": "13 arrival spectrum",
    "body": "14 body exposure",
    "cameras": "15 cameras",
}

#: key -> the collection, so the rest of the build and the figure table can keep
#: using short keys while the file shows sentences.
BUILT: dict[str, bpy.types.Collection] = {}


def collection(key: str) -> bpy.types.Collection:
    """The collection for a key, created on first use and numbered for reading.

    Every key gets a collection whether or not anything goes in it. An empty one
    is the honest answer to a site that has no panorama: the structure is the
    same everywhere, and a layer that is missing is missing visibly rather than
    by not being there to notice.
    """
    if key in BUILT:
        return BUILT[key]
    made = bpy.data.collections.new(COLLECTION_NAMES.get(key, key))
    bpy.context.scene.collection.children.link(made)
    BUILT[key] = made
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


def attach_point_colour(obj: bpy.types.Object, name: str, rgba: np.ndarray, *, byte: bool = True) -> None:
    """One colour per vertex, byte encoded unless asked otherwise.

    Byte rather than float because a cloud is a quarter of a million points and
    four bytes against sixteen decides whether the file is worth downloading.
    Eight bits per channel is more than a shaded scalar carries anyway, and the
    exact value is on the float attribute next to it.

    Byte colours are stored non linearly, so a constant tint written this way
    comes back out of the shader at a visibly different colour. That does not
    matter for a ramp, where the reader is comparing one point against another
    and both moved the same way, and it does matter for a fixed key colour, so
    those pass ``byte=False``.
    """
    kind = "BYTE_COLOR" if byte else "FLOAT_COLOR"
    attribute = obj.data.color_attributes.new(name=name, type=kind, domain="POINT")
    attribute.data.foreach_set("color", np.ascontiguousarray(rgba, dtype=np.float32).ravel())


def attach_values(obj: bpy.types.Object, name: str, values: np.ndarray, domain: str) -> None:
    """The measured number itself, unshaded, so the blend is data and not only a picture.

    A colour attribute is lossy by construction: it is clamped to the range the
    ramp was given and it cannot be read back as the quantity it came from. This
    keeps the quantity, which is what the spreadsheet editor shows and what a
    geometry node or a script can query.
    """
    values = np.asarray(values)
    kind = "INT" if np.issubdtype(values.dtype, np.integer) else "FLOAT"
    attribute = obj.data.attributes.new(name=name, type=kind, domain=domain)
    attribute.data.foreach_set("value", values.astype(np.int32 if kind == "INT" else np.float32).ravel())


def emissive_material(
    name: str,
    channel: str | None,
    colour: tuple[float, float, float] = (1.0, 1.0, 1.0),
    *,
    strength: float = 1.0,
):
    """A pure emitter, either at a fixed colour or at a colour attribute.

    Emission rather than a lit BSDF because these layers encode a measured
    number. A lit surface multiplies that number by whatever the lighting does,
    and two values that differ only in hue stop being distinguishable exactly
    where the reader is counting on them.

    Strength above one is a display gain and nothing else. It multiplies every
    value on the layer by the same factor, so it moves no ordering and no
    ratio, and it exists because the sunlit mesh is brighter than an emitter at
    one and a thin line drawn over it stops looking like light. The layers that
    use it say so on the object.
    """
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    tree = material.node_tree
    tree.nodes.clear()
    emission = tree.nodes.new("ShaderNodeEmission")
    emission.inputs["Strength"].default_value = float(strength)
    output = tree.nodes.new("ShaderNodeOutputMaterial")
    if channel is None:
        emission.inputs["Color"].default_value = (*colour, 1.0)
    else:
        attribute = tree.nodes.new("ShaderNodeAttribute")
        attribute.name = LAYER_NODE
        attribute.attribute_name = channel
        attribute.location = (-300, 0)
        tree.links.new(attribute.outputs["Color"], emission.inputs["Color"])
    tree.links.new(emission.outputs["Emission"], output.inputs["Surface"])
    return material


#: Name of the attribute node every layered material carries. Renaming the
#: attribute it reads is the whole of switching a layer, so it is found by name
#: rather than by position in a node tree a reader may have rearranged.
LAYER_NODE = "layer"


def show_layer(obj: bpy.types.Object, channel: str) -> None:
    """Point an object's material and its viewport at one of its colour layers.

    Both are set, because they are read in different places: the shader path uses
    the attribute node, and solid shading with the colour source set to attribute
    uses whichever colour attribute is active. Setting one and not the other
    gives a viewport and a render that disagree, which is worse than either.

    A curves datablock holds colour attributes and has no active one to set, so
    only the shader half applies there.
    """
    for material in obj.data.materials:
        node = material.node_tree.nodes.get(LAYER_NODE) if material.use_nodes else None
        if node is not None:
            node.attribute_name = channel
    colours = obj.data.color_attributes
    if channel in colours.keys() and hasattr(colours, "active_color_index"):
        colours.active_color_index = colours.keys().index(channel)


def layered(obj: bpy.types.Object, channels: tuple[str, ...], default: str) -> None:
    """Record the layer list on the object and select the one it opens on."""
    obj["colour_layers"] = list(channels)
    obj["reading"] = "switch layer in Object Data Properties, Colour Attributes, or rename the 'layer' node"
    show_layer(obj, default)


def point_cloud(
    name: str, points: np.ndarray, into: bpy.types.Collection, *, radius: float, material
) -> bpy.types.Object:
    """A vertex only mesh turned into renderable points by one geometry node.

    A quarter of a million points as triangles would be a quarter of a million
    triangles and three times the vertices. As loose vertices it is one position
    each, and ``Mesh to Points`` gives Cycles something to shade without any of
    that reaching the file. The material has to be set inside the node group:
    the point component is new geometry and does not inherit the mesh's slots,
    and the symptom of forgetting is a cloud that renders pure black.
    """
    mesh = bpy.data.meshes.new(name)
    mesh.vertices.add(points.shape[0])
    mesh.vertices.foreach_set("co", np.ascontiguousarray(points, dtype=np.float32).ravel())
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    into.objects.link(obj)

    group = bpy.data.node_groups.new(f"{name}_points", "GeometryNodeTree")
    group.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    group.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    inputs = group.nodes.new("NodeGroupInput")
    inputs.location = (-400, 0)
    outputs = group.nodes.new("NodeGroupOutput")
    outputs.location = (400, 0)
    to_points = group.nodes.new("GeometryNodeMeshToPoints")
    to_points.inputs["Radius"].default_value = radius
    set_material = group.nodes.new("GeometryNodeSetMaterial")
    set_material.location = (200, 0)
    set_material.inputs["Material"].default_value = material
    group.links.new(inputs.outputs[0], to_points.inputs["Mesh"])
    group.links.new(to_points.outputs["Points"], set_material.inputs["Geometry"])
    group.links.new(set_material.outputs["Geometry"], outputs.inputs[0])
    modifier = obj.modifiers.new("points", "NODES")
    modifier.node_group = group
    obj.data.materials.append(material)
    obj["point_radius_m"] = radius
    return obj


def categorical_colours(codes: np.ndarray, palette: np.ndarray) -> np.ndarray:
    """RGBA for integer codes, with anything outside the palette drawn as grey."""
    codes = np.asarray(codes, dtype=np.int64)
    inside = (codes >= 0) & (codes < palette.shape[0])
    rgb = np.full((codes.size, 3), 0.35)
    rgb[inside] = palette[codes[inside]]
    return np.column_stack([rgb, np.ones(codes.size)])


def log_ramp(values: np.ndarray, floor: float = 1.0) -> tuple[np.ndarray, float, float]:
    """Inferno over the base ten logarithm, for counts that span decades."""
    scaled = np.log10(np.maximum(np.asarray(values, dtype=np.float64), floor))
    low, high = float(scaled.min()), float(scaled.max())
    return colour_ramp(scaled, low, max(high, low + 1.0e-6)), low, high


def scalar_layers(
    obj: bpy.types.Object, columns: dict[str, np.ndarray], domain: str, *, ranges: dict[str, tuple[float, float]]
) -> None:
    """Attach every column twice, as its exact value and as a shaded colour."""
    attach = attach_face_colour if domain == "FACE" else attach_point_colour
    for name, values in columns.items():
        attach_values(obj, f"value_{name}", values, domain)
        low, high = ranges.get(name, (float(np.nanmin(values)), float(np.nanmax(values))))
        attach(obj, name, colour_ramp(np.nan_to_num(values, nan=low), low, max(high, low + 1.0e-9)))
        obj[f"{name}_range"] = [low, high]


def lit_material(name: str, channel: str):
    """A matte surface tinted by a colour attribute, for the geometry itself."""
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    tree = material.node_tree
    principled = tree.nodes["Principled BSDF"]
    principled.inputs["Roughness"].default_value = 0.85
    principled.inputs["Specular IOR Level"].default_value = 0.15
    attribute = tree.nodes.new("ShaderNodeAttribute")
    attribute.name = LAYER_NODE
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


def build_curves(
    name: str,
    points: np.ndarray,
    lengths: np.ndarray,
    radius: np.ndarray,
    into: bpy.types.Collection,
) -> bpy.types.Object:
    """A hair curves object, which is the only curve type that carries attributes.

    A legacy Blender curve has a per point radius and nothing else, so the power
    a ray carries could be drawn and could not be read. A ``Curves`` datablock
    takes named attributes on its points, so the same number is both the
    thickness and a column in the spreadsheet, which is the convention the rest
    of this file uses everywhere else.
    """
    curves = bpy.data.hair_curves.new(name)
    curves.add_curves([int(value) for value in lengths])
    curves.attributes["position"].data.foreach_set("vector", points.astype(np.float32).ravel())
    if "radius" not in curves.attributes:
        curves.attributes.new("radius", "FLOAT", "POINT")
    curves.attributes["radius"].data.foreach_set("value", radius.astype(np.float32))
    obj = bpy.data.objects.new(name, curves)
    into.objects.link(obj)
    return obj


def build_rays(payload, terminations: list[str], into: bpy.types.Collection, *, base_radius: float) -> dict[str, int]:
    """One curves object per bundle, carrying throughput as thickness and as a layer.

    Throughput spans several decades along a multi bounce path, so the radius is
    the cube root of it. That keeps a fourth bounce visible instead of
    vanishing, and it is monotone, so thicker still means more power. The same
    number is on the points twice more, as an exact ``value_throughput`` and as
    a ``power_db`` colour over the decades it actually spans, so the fan can be
    shaded by power rather than only thickened by it. The default layer is
    ``fate``, the constant colour of the bundle, so nothing about the existing
    reading changes until it is asked to.
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
        keep = (
            np.concatenate([np.arange(offsets[i], offsets[i + 1]) for i in indices])
            if indices.size
            else np.zeros(0, dtype=np.int64)
        )
        lengths = offsets[indices + 1] - offsets[indices]
        obj = build_curves(
            name,
            vertices[keep],
            lengths,
            base_radius * np.cbrt(throughput[keep]),
            into,
        )
        colour, visible = RAY_STYLE[name]
        attach_point_colour(obj, "fate", np.tile((*colour, 1.0), (keep.size, 1)), byte=False)
        attach_point_colour(obj, "power_db", colour_ramp(decibels[keep], *span))
        attach_values(obj, "value_throughput", throughput[keep], "POINT")
        obj["colour_layers"] = ["fate", "power_db"]
        obj["power_db_range"] = list(span)
        obj["reading"] = "thickness is the cube root of throughput, and power_db is the same number as a colour"
        assign(obj, emissive_material(f"ray_{name}", "fate"))
        show_layer(obj, "fate")
        obj.hide_render = not visible
    return counts


def build_ray_depth(payload, into: bpy.types.Collection, *, base_radius: float) -> dict[str, int]:
    """The same paths again, cut at the bounces, one object per leg index.

    The five bundles answer where a ray ended. They do not answer how deep it
    went, and depth is the question the bounce budget is about: the panoramas
    measure the material for the first two reflections and nothing measures it
    after that. A leg is one straight segment of a path, so leg zero is what
    left the standpoint and leg two is what carried on after the second surface.
    Switching the last object off shows exactly how much of the fan lives past
    what the evidence supports.
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


#: Where the rim polyline is cut. Two azimuths half a degree apart whose tips
#: are further apart than this fraction of their own range are not one roofline:
#: the silhouette has stepped across a street opening onto a facade behind it,
#: and joining them draws a wire across the square. A flat wall seen at 85
#: degrees of grazing moves 0.10 of its range per half degree, so 0.15 cuts at
#: the openings and never along a facade.
RIM_BREAK_FRACTION = 0.15

#: Inferno starts at black. A rim shaded from its black end loses the rooflines
#: that carry least power rather than merely dimming them, so the ramp is
#: entered at this fraction of its length and the dimmest azimuth is still a
#: visible line.
RIM_RAMP_FLOOR = 0.18

#: Display gain on the rim, its sites and the connections that land on it. The
#: mesh is sunlit and an emitter at one is dimmer than the roof it is drawn
#: over, which stops a rim of light looking like light. It multiplies every
#: value on the layer alike, so no ordering and no ratio moves.
RIM_EMISSION_STRENGTH = 2.0

#: The rim is drawn this many tube radii above the tip. A tip is the top of the
#: silhouette and on a photogrammetric roof it is often a ridge behind the
#: facade, so a tube centred on it sits half inside the roof and disappears.
#: Lifting it puts the whole tube in the sky the tip borders on. Nothing else
#: moves: the height is the only coordinate touched and it is recorded.
RIM_LIFT_RADII = 2.0

#: Marker radius, in tube radii. Five is about two metres at a roofline thirty
#: metres off, which is what it takes to read a site from an overview of a
#: square rather than only from the pavement.
RIM_SITE_RADII = 5.0


def rim_tube(slant: np.ndarray, width_scale: float) -> tuple[np.ndarray, np.ndarray]:
    """Drawn radius of the rim at a slant range, and how far above the tip it goes.

    The radius rises as the square root of the range, which is between constant
    world size and constant angular size, so the far rim neither swells nor
    vanishes. It carries no flux, so there is no second reading of that number
    to reconcile with the colour.
    """
    radius = width_scale * np.sqrt(np.maximum(np.asarray(slant, dtype=np.float64), 1.0e-6))
    return radius, RIM_LIFT_RADII * radius


def rim_shading(weight: np.ndarray, found: np.ndarray):
    """The flux ramp, and the two logarithms it spans. Shared, so nothing drifts.

    The rim and the connections that land on it are shaded by the same call, or
    a bright line could arrive at a dark roofline and the reader would have no
    way to know which of the two was lying.

    The ramp spans the middle eight tenths of the azimuths rather than the whole
    range, so a tenth of the rim saturates at each end. A single tip a metre and
    a half away carries eighty times the median at Korenmarkt, and shading to it
    leaves every other roofline in one dark colour. Most rooflines deliver
    within a factor of three of each other, so what is left after the tails are
    cut is 1.07 decades at Korenmarkt rather than 1.58. The true range and the
    span shaded are both on the object.
    """
    live = np.asarray(weight)[np.asarray(found, dtype=bool)]
    low, high = (float(np.log10(value)) for value in np.percentile(live, [10, 90]))

    def shade(values: np.ndarray) -> np.ndarray:
        scaled = np.log10(np.maximum(np.asarray(values, dtype=np.float64), 1.0e-12))
        step = np.clip((scaled - low) / max(high - low, 1.0e-9), 0.0, 1.0)
        return colour_ramp(RIM_RAMP_FLOOR + (1.0 - RIM_RAMP_FLOOR) * step, 0.0, 1.0)

    return shade, low, high


def contiguous_runs(mask: np.ndarray) -> list[np.ndarray]:
    """Runs of consecutive true indices, joined across the wrap at azimuth zero.

    The rim closes on itself, so a run ending at the last azimuth and one
    starting at the first are one run through the seam rather than two.
    """
    index = np.flatnonzero(mask)
    if index.size == 0:
        return []
    runs = np.split(index, np.flatnonzero(np.diff(index) > 1) + 1)
    if len(runs) > 1 and runs[0][0] == 0 and runs[-1][-1] == mask.size - 1:
        runs = [np.concatenate([runs[-1], runs[0]])] + runs[1:-1]
    return runs


def rim_polylines(found: np.ndarray, offset: np.ndarray, *, break_fraction: float) -> list[np.ndarray]:
    """The rim as drawable polylines: index runs with a tip, cut where it steps.

    Two cuts, and they are different questions. An azimuth with no tip is open
    to the horizon and carries no source, so the rim has a hole there. An
    azimuth whose tip jumps is a corner: the silhouette has moved onto a facade
    behind the one it was on, and the two tips are both real and are not joined
    by a roofline.
    """
    pieces: list[np.ndarray] = []
    for run in contiguous_runs(found):
        if run.size == found.size:
            run = np.append(run, run[0])
        reach = np.linalg.norm(offset[run], axis=1)
        step = np.linalg.norm(np.diff(offset[run], axis=0), axis=1)
        cut = np.flatnonzero(step > break_fraction * np.minimum(reach[:-1], reach[1:])) + 1
        pieces += [piece for piece in np.split(run, cut) if piece.size >= 2]
    return pieces


def build_rim(
    payload,
    hero: np.ndarray,
    into: bpy.types.Collection,
    *,
    drawn_radius_m: float,
    width_scale: float,
    site_step: int,
) -> dict[str, object]:
    """The skyline as a lit rim, and the sites sitting on it.

    Both are the same measured curve, so they cannot disagree. The rim is the
    continuum the law integrates, a mean over azimuth, and it shows where the
    silhouette breaks. The markers say the deployment is still a set of sites
    on that tip, and they stay readable from a long way off and under solid
    shading where a thin tube does not.

    Colour is `cos^2(alpha) / d`, the direct flux that azimuth carries, over the
    base ten logarithm because the near tips carry two orders of magnitude more
    than the far ones. Thickness is not that number. Thickness rises as the
    square root of the slant range, which is between constant world size and
    constant angular size, so the far rim neither swells nor vanishes and no
    reader can mistake it for a second reading of the flux.
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

    # A tip beyond the drawn crop is a real measurement with no building under
    # it in this file, so on its own it reads as debris hanging in the air. It
    # goes into a second object that starts hidden rather than being dropped.
    inside = np.linalg.norm(tip[:, :2], axis=1) <= drawn_radius_m
    beyond = int(np.count_nonzero(found & ~inside))
    if not (found & inside).any():
        inside = np.ones_like(found)
    azimuth_deg = np.degrees(payload["rim_azimuth_rad"].astype(np.float64))

    def rim_object(name: str, keep: np.ndarray) -> tuple[object, list[np.ndarray]]:
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

    # Uniform in azimuth rather than in arc length, because the law is a mean
    # over azimuth and one azimuth is one site. Spacing them along the rim
    # instead would crowd the far facades, which are the ones carrying least.
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
    payload, hero: np.ndarray, manifest: dict, into: bpy.types.Collection, *, width_scale: float, site_step: int
) -> dict[str, object]:
    """Where the sources are, on the facade tips they stand on.

    A site sits on the tip of a facade, the top edge where the wall meets the
    sky, and there is no mast under it. One azimuth therefore carries one
    source, at the elevation and the range of the tip visible along it, and what
    that draws is a rim of light along the rooflines.

    The band population is still built and starts hidden. A height band and a
    range band draw a shell of points floating in the air, which is not where a
    base station is, and it is the geometry the trace in this same payload
    integrated, so dropping it would leave the picture and the numbers with
    nothing connecting them. Each cloud says on itself which of the two it is.
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


#: The connection colours. Clear is bright and blocked is dark, and that is the
#: whole of the default reading, because the visibility term is the one thing a
#: connection carries that the rim it lands on does not. How much the site
#: delivers is on the rim, and is a colour layer away on the connection too.
NEE_CLEAR_COLOUR = (1.0, 0.96, 0.86)
NEE_BLOCKED_COLOUR = (0.24, 0.05, 0.09)
NEE_RAY_COLOUR = (0.62, 0.44, 0.22)


def shorten_sky_legs(points: np.ndarray, lengths: np.ndarray, *, reach: float) -> np.ndarray:
    """Pull the last vertex of each polyline back to ``reach`` metres.

    Only the last one, and only along its own direction. A recorded path that
    escaped ends on a sky sphere 176 m out, which in a close view runs off the
    frame and takes the connections with it. A path that stopped in the scene
    has its last vertex sitting on the previous one and is left alone.
    """
    moved = np.array(points, dtype=np.float64, copy=True)
    end = np.cumsum(lengths) - 1
    span = moved[end] - moved[end - 1]
    distance = np.linalg.norm(span, axis=1)
    live = distance > 1.0e-9
    moved[end[live]] = moved[end[live] - 1] + reach * span[live] / distance[live, None]
    return moved


def build_next_event(
    payload,
    into: bpy.types.Collection,
    *,
    drawn_radius_m: float,
    ray_radius: float,
    line_radius: float,
    sky_leg_m: float,
) -> dict[str, object]:
    """A few dozen rays, and the connection every scattering vertex of them makes.

    This is the estimator in one picture. A ray leaves the head, bounces off the
    buildings up to three times, and at the head and at every bounce it is
    connected by one straight line to a site sampled on the facade tip. The
    connection is the contribution, so the fan of thin lines is the estimator
    and the spray of thick ones is only how it got there.

    A few dozen paths rather than the nine hundred in ``09 ray paths by fate``,
    because the answer here is how the method works and a dense fan hides it.

    A clear connection is bright and a blocked one is dark red and thinner.
    Blender's curve strands have no dash pattern, so the difference is carried
    by colour and thickness, and it is also on the points as ``value_blocked``
    to be read exactly. Switching to the ``contribution`` layer shades each
    clear connection by the flux of the site it reached instead, which is the
    same number the rim is shaded by.
    """
    origin = payload["nee_origin_m"].astype(np.float64)
    site = payload["nee_site_m"].astype(np.float64)
    blocked = payload["nee_blocked"].astype(bool)
    weight = payload["nee_weight"].astype(np.float64)
    depth = payload["nee_vertex_index"].astype(np.int64)
    picked = payload["nee_paths"].astype(np.int64)

    # A connection is drawn only when the site it lands on is drawn. The tips
    # beyond the crop this file holds are hidden, and a line running out to one
    # of them ends in empty air, which is the one thing this picture must not
    # show. The connection was still cast and still counted. The crop is a disc
    # about the scene origin rather than about the head, which is the same test
    # ``crop_for_drawing`` ran on the mesh, so the two cannot disagree.
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
    keep = np.concatenate([np.arange(offsets[i], offsets[i + 1]) for i in picked])
    drawn = shorten_sky_legs(vertices[keep], offsets[picked + 1] - offsets[picked], reach=sky_leg_m)
    rays = build_curves(
        "estimator_rays",
        drawn,
        offsets[picked + 1] - offsets[picked],
        np.full(keep.size, ray_radius),
        into,
    )
    attach_point_colour(rays, "ray", np.tile((*NEE_RAY_COLOUR, 1.0), (keep.size, 1)), byte=False)
    assign(rays, emissive_material("estimator_rays", "ray"))
    rays["paths_drawn"] = int(picked.size)
    rays["reading"] = "the same recorded paths as 09, thinned to a readable few dozen"
    rays["last_leg_shortened_to_m"] = sky_leg_m
    rays["what_that_changes"] = (
        "only the drawn length of the leg that left the scene. In 09 it runs to the sky sphere "
        "176 m out, which here would push every ray past the frame and hide the connections. "
        "Its direction is untouched and no other vertex moves."
    )

    # Two points per connection, so one curves object holds them all and each
    # end can carry its own colour.
    ends = np.empty((origin.shape[0] * 2, 3))
    ends[0::2], ends[1::2] = origin, site
    shade, _, _ = rim_shading(payload["rim_weight"], payload["rim_found"])
    contribution = np.repeat(shade(weight), 2, axis=0)
    dark = np.repeat(blocked, 2)
    contribution[dark] = (*NEE_BLOCKED_COLOUR, 1.0)
    visibility = np.where(dark[:, None], np.array([*NEE_BLOCKED_COLOUR, 1.0]), np.array([*NEE_CLEAR_COLOUR, 1.0]))
    lines = build_curves(
        "estimator_connections",
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
    assign(lines, emissive_material("estimator_connections", "visibility", strength=RIM_EMISSION_STRENGTH))
    layered(lines, ("visibility", "contribution"), "visibility")
    lines["connections"] = int(origin.shape[0])
    lines["blocked"] = int(np.count_nonzero(blocked))
    lines["from_the_head"] = int(np.count_nonzero(depth == 0))
    lines["blocked_from_the_head"] = int(np.count_nonzero(blocked & (depth == 0)))
    lines["sites_sampled"] = "uniformly in azimuth on the facade tip, one per scattering vertex"
    lines["reading"] = "one straight line per contribution. Dark red carries nothing, something is in the way"
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


# ---------------------------------------------------------------------------
# Evidence layers. Every one of these is skipped when the payload lacks it.
# ---------------------------------------------------------------------------

#: Which fishnet columns become colour layers, and the range each is shaded on.
#: A fixed range where the quantity has one, so two taxonomies and two sites are
#: comparable, and a measured range where it does not.
FISHNET_LAYERS: dict[str, tuple[float, float] | None] = {
    "confidence": (0.0, 1.0),
    "top_probability": (0.0, 1.0),
    # Clipped at half a bit rather than at the maximum. Five sixths of the faces
    # sit at exactly zero, so a range set by the tail leaves the whole surface
    # in the dark end of the ramp and the mixed faces, which are the point of
    # the layer, invisible. The exact value is on the same object.
    "entropy_bits": (0.0, 0.5),
    "visible_fraction": (0.0, 1.0),
    "range_m": None,
}

#: Colours for the mesh against monocular depth verdict, matching the order in
#: ``compare_mesh_depth.DECISIONS``. Kept in that order rather than looked up so
#: the blend does not need the module.
DECISION_TINT = np.array(
    [
        [0.35, 0.35, 0.35],  # no mesh
        [0.08, 0.75, 0.35],  # agree
        [0.96, 0.75, 0.12],  # uncertain
        [0.92, 0.20, 0.16],  # something stands in front of the mesh
        [0.51, 0.22, 0.75],  # the mesh is implausibly in front
        [0.14, 0.59, 0.96],  # person or vehicle, handled by the body layer
        [0.55, 0.55, 0.55],  # depth evidence withheld, the mesh decides alone
    ]
)

#: Colour per rejection reason code, indexed from one as the reasons are.
REFUSAL_TINT = {
    "occluded_by_support_mesh": (0.30, 0.34, 0.55),
    "transient_object": (0.14, 0.59, 0.96),
    "clutter_in_front": (0.92, 0.20, 0.16),
    "mesh_or_pose_conflict": (0.51, 0.22, 0.75),
    "not_support_surface": (0.62, 0.58, 0.30),
    "below_minimum_area": (0.40, 0.40, 0.40),
}

#: Verdict colours for a registered pose, in the order of the exporter's codes.
VERDICT_TINT = np.array([[0.10, 0.80, 0.40], [0.98, 0.72, 0.15], [0.95, 0.18, 0.18]])


def has(payload, prefix: str) -> bool:
    return any(key.startswith(prefix) for key in payload.files)


def build_fishnet(payload, manifest, taxonomy: str, into: bpy.types.Collection) -> dict[str, int] | None:
    """One surface set per taxonomy, carrying what the segmenter said about each face.

    The class layer is a lookup and is drawn from a palette, not a ramp. Every
    other layer is a measured scalar and is drawn on inferno over a stated range,
    which is on the object. The face count is the cutter's own, so this is the
    surface the propagation stage would bind materials to, not a redrawing of it.
    """
    key = f"fishnet_{taxonomy}"
    if not has(payload, f"{key}_vertices"):
        return None
    record = manifest.get("evidence", {}).get(key, {})
    obj = build_mesh(f"fishnet_{taxonomy}", payload[f"{key}_vertices"], payload[f"{key}_faces"], into)
    classes = payload[f"{key}_class"]
    attach_face_colour(obj, "class", categorical_colours(classes, payload[f"{key}_class_rgb"]))
    attach_values(obj, "value_class", classes, "FACE")
    columns = {name: payload[f"{key}_{name}"] for name in FISHNET_LAYERS if f"{key}_{name}" in payload.files}
    ranges = {
        name: span for name, span in FISHNET_LAYERS.items() if span is not None and f"{key}_{name}" in payload.files
    }
    scalar_layers(obj, columns, "FACE", ranges=ranges)
    for extra in ("area_m2", "solid_angle_sr", "pixel_support", "view"):
        if f"{key}_{extra}" in payload.files:
            attach_values(obj, f"value_{extra}", payload[f"{key}_{extra}"], "FACE")
    assign(obj, emissive_material(f"fishnet_{taxonomy}", "class"))
    obj["taxonomy"] = taxonomy
    obj["class_names"] = record.get("class_names", [])
    obj["views"] = record.get("views", [])
    obj["cut_by"] = "semantic_twin/fishnet.py, projected support triangles cut at semantic island boundaries"
    layered(obj, ("class", *columns), "class")
    return {"faces": int(payload[f"{key}_faces"].shape[0])}


def build_support_evidence(payload, manifest, into: bpy.types.Collection) -> dict[str, float] | None:
    """Every support triangle a view considered, clean pixels against withheld ones.

    Four withholding channels rather than one total, because they do not mean the
    same thing. A transient pixel is deferred to the body layer and will come
    back as a person. A clutter pixel is geometry the tiles never captured and is
    simply gone. Reading them as one number is what this layer exists to stop.
    """
    if not has(payload, "support_evidence_vertices"):
        return None
    record = manifest.get("evidence", {}).get("support_evidence", {})
    obj = build_mesh("support_evidence", payload["support_evidence_vertices"], payload["support_evidence_faces"], into)
    attach_face_colour(
        obj, "class", categorical_colours(payload["support_evidence_class"], payload["support_evidence_class_rgb"])
    )
    attach_values(obj, "value_class", payload["support_evidence_class"], "FACE")
    scalar_layers(
        obj, {"confidence": payload["support_evidence_confidence"]}, "FACE", ranges={"confidence": (0.0, 1.0)}
    )
    withheld = np.zeros(payload["support_evidence_class"].size)
    counted = ("clean", "transient", "clutter", "occluded", "other")
    for name in counted:
        values = payload[f"support_evidence_{name}_px"]
        attach_values(obj, f"value_{name}_px", values, "FACE")
        rgba, low, high = log_ramp(values)
        attach_face_colour(obj, f"{name}_px", rgba)
        obj[f"{name}_px_log10_range"] = [low, high]
        if name != "clean":
            withheld += values
    total = withheld + payload["support_evidence_clean_px"]
    fraction = np.divide(withheld, total, out=np.zeros(total.size), where=total > 0.0)
    scalar_layers(obj, {"withheld_fraction": fraction}, "FACE", ranges={"withheld_fraction": (0.0, 1.0)})
    assign(obj, emissive_material("support_evidence", "class"))
    obj["grouping"] = json.dumps(record.get("grouping", {}))
    obj["reading"] = "clean_px is what was painted, the other four are what was refused and why"
    layered(obj, ("class", "confidence", *(f"{name}_px" for name in counted), "withheld_fraction"), "class")
    return {"triangles": int(payload["support_evidence_faces"].shape[0])}


def build_refused(payload, manifest, into: bpy.types.Collection) -> dict[str, int] | None:
    """The candidate surface the cutter refused, one object per reason.

    Separate objects rather than one object with a reason layer, because the
    question a reader has is what a single reason removed, and that is answered
    by switching an object off. The transient set and the clutter set are the two
    that matter: one comes back as a body and the other never comes back.
    """
    if not has(payload, "rejected_vertices"):
        return None
    record = manifest.get("evidence", {}).get("rejected", {})
    names = record.get("reason_names", [])
    reasons = payload["rejected_reason"]
    faces = payload["rejected_faces"]
    vertices = payload["rejected_vertices"]
    areas = payload["rejected_image_area_px"]
    counts: dict[str, int] = {}
    for code in np.unique(reasons):
        label = names[int(code) - 1] if 0 < int(code) <= len(names) else f"reason_{int(code)}"
        keep = np.flatnonzero(reasons == code)
        kept = faces[keep]
        used, remapped = np.unique(kept, return_inverse=True)
        obj = build_mesh(f"refused_{label}", vertices[used], remapped.reshape(kept.shape), into)
        rgba, low, high = log_ramp(areas[keep])
        attach_face_colour(obj, "image_area_px", rgba)
        attach_values(obj, "value_image_area_px", areas[keep], "FACE")
        tint = REFUSAL_TINT.get(label, (0.5, 0.5, 0.5))
        attach_face_colour(obj, "reason", np.tile((*tint, 1.0), (kept.shape[0], 1)))
        assign(obj, emissive_material(f"refused_{label}", "reason"))
        obj["reason"] = label
        obj["image_area_px_total"] = float(areas[keep].sum())
        obj["image_area_px_log10_range"] = [low, high]
        layered(obj, ("reason", "image_area_px"), "reason")
        counts[label] = int(kept.shape[0])
    return counts


def build_depth(payload, manifest, into: bpy.types.Collection, *, radius: float) -> dict[str, int] | None:
    """Two clouds: the first hit the twin uses, and the depth the gate refused.

    They are deliberately in the same collection and the same units. The point of
    drawing the refused one is that the refusal stops being a line in a manifest:
    at a fitted scale of 0.41 the whole square sits at four tenths of its range,
    inside the mesh, and no reader needs the plausibility band explained after
    seeing it.
    """
    made: dict[str, int] = {}
    camera = payload["evidence_camera"].astype(np.float64) if "evidence_camera" in payload.files else None
    for kind, tint_channel in (("mesh", "decision"), ("monocular", "decision")):
        key = f"depth_{kind}"
        if not has(payload, f"{key}_points"):
            continue
        points = payload[f"{key}_points"].astype(np.float64)
        material = emissive_material(f"{key}_cloud", "decision")
        obj = point_cloud(f"depth_{kind}", points, into, radius=radius, material=material)
        attach_point_colour(obj, "decision", categorical_colours(payload[f"{key}_decision"], DECISION_TINT))
        attach_values(obj, "value_decision", payload[f"{key}_decision"].astype(np.int32), "POINT")
        columns: dict[str, np.ndarray] = {}
        if camera is not None:
            columns["range_m"] = np.linalg.norm(points - camera, axis=1)
        if f"{key}_z_score" in payload.files:
            columns["z_score"] = np.clip(payload[f"{key}_z_score"], -6.0, 6.0)
        if f"{key}_mesh_range_m" in payload.files and camera is not None:
            columns["mesh_minus_this_m"] = payload[f"{key}_mesh_range_m"] - columns["range_m"]
        scalar_layers(obj, columns, "POINT", ranges={"z_score": (-6.0, 6.0)})
        attach_values(obj, "value_view", payload[f"{key}_view"].astype(np.int32), "POINT")
        record = manifest.get("evidence", {}).get(key, {})
        obj["meaning"] = record.get("meaning", "")
        obj["decisions"] = json.dumps(
            record.get("decisions") or manifest.get("evidence", {}).get("depth_mesh", {}).get("decisions")
        )
        obj["stride_px"] = record.get("stride_px")
        if record.get("scale_plausibility") is not None:
            obj["scale_plausibility"] = json.dumps(record["scale_plausibility"].get("problems", []))
        layered(obj, (tint_channel, *columns), tint_channel)
        made[kind] = int(points.shape[0])
    return made or None


def unit_sphere(subdivisions: int = 2) -> tuple[np.ndarray, np.ndarray]:
    """A sphere by subdividing an octahedron, so no external primitive is needed."""
    vertices = np.array(
        [[1.0, 0, 0], [-1.0, 0, 0], [0, 1.0, 0], [0, -1.0, 0], [0, 0, 1.0], [0, 0, -1.0]], dtype=np.float64
    )
    faces = np.array(
        [[0, 2, 4], [2, 1, 4], [1, 3, 4], [3, 0, 4], [2, 0, 5], [1, 2, 5], [3, 1, 5], [0, 3, 5]], dtype=np.int64
    )
    for _ in range(subdivisions):
        a, b, c = vertices[faces[:, 0]], vertices[faces[:, 1]], vertices[faces[:, 2]]
        base = vertices.shape[0]
        count = faces.shape[0]
        midpoints = np.concatenate([(a + b) / 2.0, (b + c) / 2.0, (c + a) / 2.0])
        vertices = np.concatenate([vertices, midpoints])
        ab = base + np.arange(count)
        bc = ab + count
        ca = bc + count
        faces = np.concatenate(
            [
                np.column_stack([faces[:, 0], ab, ca]),
                np.column_stack([ab, faces[:, 1], bc]),
                np.column_stack([ca, bc, faces[:, 2]]),
                np.column_stack([ab, bc, ca]),
            ]
        )
    return vertices / np.linalg.norm(vertices, axis=1, keepdims=True), faces


def build_panoramas(payload, manifest, into: bpy.types.Collection, *, sigma_scale: float) -> int | None:
    """Every registered pose, as a camera you can look through, a marker and an ellipsoid.

    The camera is a real Blender camera at the solved rotation, so the view it
    saw is reproducible from inside the blend. The marker carries the verdict the
    sky conflict audit reached, which at Korenmarkt is three cameras standing
    inside the geometry out of thirteen, and no residual would have said so. The
    ellipsoid is the position block of the seed study covariance at one sigma,
    scaled by ``sigma_scale`` because one sigma here is a few centimetres and a
    few centimetres in a two hundred metre scene is nothing. The scale is on
    every ellipsoid as a property, so nobody reads it as a metre.
    """
    # Imported here rather than at module level: mathutils ships inside Blender
    # and is absent from the venv, and the pure geometry in this file is tested
    # outside Blender with only ``bpy`` stubbed.
    import mathutils

    if "pano_position" not in payload.files:
        return None
    positions = payload["pano_position"].astype(np.float64)
    rotations = payload["pano_rotation"].astype(np.float64)
    sigmas = payload["pano_sigma_vectors"].astype(np.float64)
    verdict = payload["pano_verdict"]
    records = manifest.get("evidence", {}).get("registration", {}).get("poses", [])
    markers, faces = octahedra(positions, 0.9)
    marker = build_mesh("pano_markers", markers, faces, into)
    attach_face_colour(marker, "verdict", np.repeat(categorical_colours(verdict, VERDICT_TINT), 8, axis=0))
    attach_face_colour(
        marker,
        "sky_conflict",
        np.repeat(colour_ramp(payload["pano_sky_conflict"], 0.0, 1.0), 8, axis=0),
    )
    attach_face_colour(
        marker,
        "skyline_residual_deg",
        np.repeat(colour_ramp(payload["pano_residual_deg"], 0.0, 8.0), 8, axis=0),
    )
    assign(marker, emissive_material("pano_markers", "verdict"))
    marker["reading"] = manifest.get("evidence", {}).get("registration", {}).get("reading", "")
    marker["captures"] = [record.get("capture", "") for record in records]
    layered(marker, ("verdict", "sky_conflict", "skyline_residual_deg"), "verdict")

    sphere, sphere_faces = unit_sphere()
    blobs = []
    for index, position in enumerate(positions):
        blobs.append(position + sigma_scale * (sphere @ sigmas[index].T))
    ellipsoid = build_mesh(
        "pano_uncertainty",
        np.concatenate(blobs),
        np.concatenate([sphere_faces + index * sphere.shape[0] for index in range(len(blobs))]),
        into,
    )
    attach_face_colour(
        ellipsoid,
        "verdict",
        np.repeat(categorical_colours(verdict, VERDICT_TINT), sphere_faces.shape[0], axis=0),
    )
    assign(ellipsoid, emissive_material("pano_uncertainty", "verdict"))
    ellipsoid["sigma_multiple_drawn"] = sigma_scale
    ellipsoid["reading"] = f"one sigma of the pose position, drawn {sigma_scale:g} times life size"
    layered(ellipsoid, ("verdict",), "verdict")

    for index, record in enumerate(records):
        rotation = rotations[index]
        # The pose rotation takes panorama-local right, forward and up to world.
        # A Blender camera looks down its own -Z with +Y up, so its columns are
        # right, up and backwards, which is the pose's columns with the last two
        # swapped and the new last one negated.
        basis = np.column_stack([rotation[:, 0], rotation[:, 2], -rotation[:, 1]])
        data = bpy.data.cameras.new(f"pano_{index:02d}")
        data.lens = 18.0
        data.clip_end = 400.0
        obj = bpy.data.objects.new(f"pano_{index:02d}", data)
        into.objects.link(obj)
        placed = np.eye(4)
        placed[:3, :3] = basis
        placed[:3, 3] = positions[index]
        obj.matrix_world = mathutils.Matrix([[float(value) for value in row] for row in placed])
        for field in ("capture", "skyline_residual_deg", "sky_with_mesh_hit_fraction", "position_sigma_m", "verdict"):
            if record.get(field) is not None:
                obj[field] = record[field]
    return int(positions.shape[0])


def build_bodies(payload, manifest, into: bpy.types.Collection) -> int | None:
    """The SMPL-X bystanders, already in scene ENU, one object each.

    These are the people the transient mask cut out of the static surface. The
    fishnet leaves a hole where they stood and this layer is what fills it, which
    is the whole reason the occlusion budget separates deferred from absent. They
    have never been in a blend before and they carry no exposure, so the tint is
    flat and the numbers are properties.
    """
    if "body_layer_vertices" not in payload.files:
        return None
    vertices = payload["body_layer_vertices"].astype(np.float64)
    faces = payload["body_layer_faces"]
    records = manifest.get("evidence", {}).get("bodies", {}).get("records", [])
    material = emissive_material("bystander", None, (0.20, 0.62, 0.95))
    for index in range(vertices.shape[0]):
        record = records[index] if index < len(records) else {}
        obj = build_mesh(record.get("body_id", f"bystander_{index:02d}"), vertices[index], faces, into)
        assign(obj, material)
        for field in ("view", "stature_m", "placed_range_m", "range_source", "placement_provenance"):
            if record.get(field) is not None:
                obj[field] = record[field]
        if record.get("uncertainty"):
            obj["uncertainty"] = json.dumps(record["uncertainty"])
        obj["layer"] = "transient, never baked into the static semantic atlas"
    return int(vertices.shape[0])


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


def build_evidence_cameras(
    twin: bpy.types.Object, payload, hero: np.ndarray, ground_z: float, into: bpy.types.Collection
) -> None:
    """Three more vantages, aimed at the capture point rather than the standpoint.

    The evidence layers are not centred where the rays are. They radiate from the
    panorama the segmenter ran on, which is metres away from the median walk
    location and looking at a different part of the square, so pointing the
    existing cameras at them frames the wrong wall. These are placed against the
    capture point with the same clearance search.
    """
    capture = payload["evidence_camera"].astype(np.float64) if "evidence_camera" in payload.files else hero
    # This one is not placed outside looking in, and every attempt to do that
    # failed for the same reason. The cut surface is by construction the set of
    # surfaces visible from the capture point, most of it facade, 2296 of the
    # 3306 faces of the first crop being Building. Any vantage outside the square
    # is therefore behind a wall that owns part of the layer it is trying to
    # photograph, and raising the camera until the wall clears turns the facades
    # edge on and frames roofs. So it stands where the panorama stood, five
    # metres up to clear the bystanders, and looks along the most open bearing.
    # Nothing it can see is occluded, because seeing it is what put it there.
    eye = capture + np.array([0.0, 0.0, 5.0])
    look = clear_view(twin, eye, 60.0, (5.0, 12.0, 22.0))
    add_camera("cam_evidence", eye, eye + 4.0 * (look - eye), into, lens=24.0)
    print(f"[camera] cam_evidence at the capture point, {eye[2] - capture[2]:.1f} m up", flush=True)

    if "pano_position" in payload.files:
        poses = payload["pano_position"].astype(np.float64)
        centre = poses.mean(axis=0)
        reach = max(float(np.linalg.norm(poses[:, :2] - centre[:2], axis=1).max()) * 2.2, 45.0)
        add_camera("cam_registration", centre + np.array([0.0, -0.35 * reach, reach]), centre, into, lens=30.0)
        print(f"[camera] cam_registration {reach:.1f} m above {poses.shape[0]} poses", flush=True)

    if "body_layer_vertices" in payload.files:
        # The bodies stand all round the capture point, four crops of one
        # panorama, so their centroid is the camera. Standing there and looking
        # at the centroid frames nothing. The crowd is framed from outside its
        # own bounding sphere instead.
        crowd = payload["body_layer_vertices"].astype(np.float64).reshape(-1, 3)
        centre = crowd.mean(axis=0)
        spread = float(np.linalg.norm(crowd - centre, axis=1).max())
        reach = max(2.4 * spread, 14.0)
        add_camera("cam_bystanders", clear_view(twin, centre, reach, (12.0, 22.0, 38.0, 58.0)), centre, into, lens=34.0)
        print(f"[camera] cam_bystanders {reach:.1f} m out, crowd spread {spread:.1f} m", flush=True)


def frame_the_viewport(twin: bpy.types.Object, hero: np.ndarray) -> None:
    """Save a view that opens on the square, in every workspace the file ships with.

    A blend built headlessly keeps the factory viewport, which looks at the
    origin from two metres away with a one hundred metre clip. The square is
    220 m across and its origin is the standpoint, so opening the file shows a
    grey wall of one facade seen from inside it, and the first thing anyone does
    is fight the navigation. Setting the pivot, the distance, the rotation and
    the far clip once here is the difference between a file that opens on the
    subject and a file that opens on nothing.

    Every workspace is set rather than only the layout one, because whichever
    tab the reader lands on is the one that has to be right.
    """
    # Imported here rather than at module level, for the reason given in
    # ``build_panoramas``.
    import mathutils

    heights = np.empty(len(twin.data.vertices) * 3)
    twin.data.vertices.foreach_get("co", heights)
    points = heights.reshape(-1, 3)
    span = float(np.linalg.norm(points[:, :2] - hero[:2], axis=1).max())
    pivot = np.array([hero[0], hero[1], float(np.quantile(points[:, 2], 0.5))])
    # Looking down the negative Y axis from thirty degrees up, which is the
    # three quarter view the figures use and the one a square reads best from.
    rotation = mathutils.Euler((math.radians(60.0), 0.0, 0.0), "XYZ").to_quaternion()
    saved = 0
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type != "VIEW_3D":
                continue
            space = area.spaces.active
            space.clip_start = 0.5
            space.clip_end = max(4.0 * span, 2000.0)
            space.shading.type = "MATERIAL"
            space.overlay.show_relationship_lines = False
            view = space.region_3d
            view.view_perspective = "PERSP"
            view.view_location = tuple(float(value) for value in pivot)
            view.view_distance = 1.7 * span
            view.view_rotation = rotation
            saved += 1
    print(f"[viewport] {saved} views saved at {1.7 * span:.0f} m over the standpoint", flush=True)


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


#: One figure names what it is about, not which camera took it. The ray fan
#: leaves the standpoint in every direction, so there is no vantage from which it
#: does not cover a close subject, and the arrival lobe and the phantom both sit
#: at the standpoint underneath it. ``show`` names the collections, ``objects``
#: narrows to particular objects inside them when two layers share a collection,
#: and ``layers`` selects which colour attribute each object is shaded by. The
#: saved blend keeps every collection it built, so this list drives the renders
#: and nothing else.
FIGURE_VIEWS: tuple[dict[str, object], ...] = (
    {"name": "01_the_square", "camera": "cam_overview", "show": ("twin",)},
    {
        # The band clouds are in this collection and are left out of every
        # figure that shows it. They are a shell of points in the air, they are
        # not where a base station is, and a picture captioned where the sources
        # are would be saying that they are.
        "name": "02_where_the_sources_are",
        "camera": "cam_overview",
        "show": ("twin", "network"),
        "hide": ("skyline_rim_beyond_the_drawn_mesh", *(f"sources_{name}" for name in MODEL_NAMES)),
        "layers": {"skyline_rim": "direct_flux"},
    },
    {"name": "03_exposure_along_the_walk", "camera": "cam_overview", "show": ("twin", "walk")},
    {"name": "04_the_rays_from_one_standpoint", "camera": "cam_rays", "show": ("twin", "rays")},
    {"name": "05_standing_in_the_ray_fan", "camera": "cam_pedestrian", "show": ("twin", "rays")},
    {"name": "06_what_arrives", "camera": "cam_lobe", "show": ("twin", "arrival")},
    {"name": "07_the_body", "camera": "cam_body", "show": ("twin", "body")},
    {
        "name": "08_what_the_segmenter_said",
        "camera": "cam_evidence",
        "show": ("twin", "semantics"),
        "objects": ("support_mesh", "fishnet_vistas"),
        "layers": {"fishnet_vistas": "class"},
    },
    {
        "name": "09_how_sure_the_segmenter_was",
        "camera": "cam_evidence",
        "show": ("twin", "semantics"),
        "objects": ("support_mesh", "fishnet_vistas"),
        "layers": {"fishnet_vistas": "confidence"},
    },
    {
        # The cut surface alone, with the mesh switched off. Five sixths of the
        # faces are at zero entropy and render as black, so against the world
        # background this is a map of the mixed ones and nothing else, which is
        # the question. Photographed from above because the split faces are
        # scattered over all four crops and no ground level bearing sees them
        # all.
        "name": "10_where_the_posterior_is_split",
        "camera": "cam_overview",
        "show": ("semantics",),
        "objects": ("fishnet_vistas",),
        "layers": {"fishnet_vistas": "entropy_bits"},
    },
    {
        "name": "11_the_material_taxonomy",
        "camera": "cam_evidence",
        "show": ("twin", "semantics"),
        "objects": ("support_mesh", "fishnet_sam3"),
        "layers": {"fishnet_sam3": "class"},
    },
    {"name": "12_what_the_cutter_refused", "camera": "cam_evidence", "show": ("twin", "refused")},
    {
        "name": "13_clean_against_withheld",
        "camera": "cam_evidence",
        "show": ("twin", "evidence"),
        "layers": {"support_evidence": "withheld_fraction"},
    },
    {
        "name": "14_the_first_hit_the_twin_uses",
        "camera": "cam_evidence",
        "show": ("depth",),
        "objects": ("depth_mesh",),
        "layers": {"depth_mesh": "decision"},
    },
    {
        "name": "15_the_depth_the_gate_refused",
        "camera": "cam_evidence",
        "show": ("twin", "depth"),
        "objects": ("support_mesh", "depth_monocular"),
        "layers": {"depth_monocular": "decision"},
    },
    {"name": "16_where_the_panoramas_stand", "camera": "cam_registration", "show": ("twin", "panoramas")},
    {"name": "17_the_bystanders", "camera": "cam_bystanders", "show": ("twin", "bodies")},
    {"name": "18_how_deep_the_bounces_go", "camera": "cam_rays", "show": ("twin", "bounces")},
    {
        # The method itself. A few dozen rays leave the head and bounce, and
        # every vertex of them, the head included, throws one thin line at a
        # site sampled on the facade tip. The lines are the estimate. The rim is
        # shown with them because a connection has to be seen landing on
        # something, and the band clouds are hidden for the same reason as in
        # figure two.
        "name": "21_next_event_estimation",
        "camera": "cam_rays",
        "show": ("twin", "network", "nee", "body"),
        "hide": ("skyline_sites", "skyline_rim_beyond_the_drawn_mesh", *(f"sources_{name}" for name in MODEL_NAMES)),
        "layers": {"estimator_connections": "visibility", "skyline_rim": "direct_flux"},
    },
    {
        # The same rim from where it matters. The overview shows that the sources
        # ring the standpoint, and this shows what the person under them sees:
        # the skyline, lit along the part of it that delivers.
        "name": "22_the_skyline_from_the_standpoint",
        "camera": "cam_pedestrian",
        "show": ("twin", "network"),
        "hide": ("skyline_rim_beyond_the_drawn_mesh", *(f"sources_{name}" for name in MODEL_NAMES)),
        "layers": {"skyline_rim": "direct_flux"},
    },
    {
        # The same fan as figure four, shaded by the power each segment carries
        # rather than by what became of it. Thickness says the same thing, so
        # the two readings agree and the colour is the one you can put a number
        # against.
        "name": "20_how_much_power_each_ray_carries",
        "camera": "cam_rays",
        "show": ("twin", "rays"),
        "layers": dict.fromkeys(RAY_STYLE, "power_db"),
    },
    {
        "name": "19_everything_at_once",
        # Not from outside and not from overhead. The ray fan is a thousand
        # polylines through one point, so any camera aimed at that point turns
        # the whole frame into a starburst and nothing else in the scene
        # survives it. From the capture point the fan converges twenty metres
        # away and sits in a corner of the picture, which leaves the walls, the
        # cloud, the walk and the bystanders room to be seen next to it.
        "camera": "cam_evidence",
        "show": (
            "twin",
            "rays",
            "arrival",
            "network",
            "walk",
            "body",
            "semantics",
            "depth",
            "panoramas",
            "bodies",
        ),
        # Three things are left out of the everything shot and each is left out
        # for a reason that is not aesthetic. ``evidence`` and ``refused`` are
        # drawn on the same support triangles the semantics are cut from, so
        # showing them together is z fighting rather than information. The
        # monocular cloud is the surface the gate refused and putting it in a
        # picture captioned everything would say the twin uses it. ``bounces``
        # is the ray fan a second time, and the two taxonomies cover the same
        # walls as each other, so Vistas is shown and SAM 3 has figure 11.
        "hide": (
            "depth_monocular",
            "fishnet_sam3",
            "skyline_rim_beyond_the_drawn_mesh",
            *(f"sources_{name}" for name in MODEL_NAMES),
        ),
        "layers": {"fishnet_vistas": "class", "depth_mesh": "decision"},
    },
)

#: Collections that start switched off. Most of them exist only when the payload
#: carries them and are dropped when it does not. A quarter of a million points
#: and eighteen SMPL-X bodies are worth having and are not worth waiting for on
#: every open. ``bounces`` is always built and is off for a different reason: it
#: is the same paths as ``rays`` cut differently, so drawing both at once draws
#: every ray twice.
EVIDENCE_COLLECTIONS = ("bounces", "nee", "semantics", "evidence", "refused", "depth", "panoramas", "bodies")


def hide_heavy_collections() -> None:
    """Start the heavy layers switched off, and leave the empty ones in place.

    Every collection in :data:`COLLECTION_NAMES` exists in every blend whether
    or not the site had the data for it. A site with no panorama then shows an
    empty ``06 panorama captures`` rather than no such row, so what is missing is
    visible instead of being something you have to already know to look for.

    Hiding is a separate question from existing. A quarter of a million depth
    points and eighteen SMPL-X bodies are worth having and are not worth waiting
    for on every open, so the evidence layers and the bounce split start off in
    the viewport and in the render.
    """
    view_layer = bpy.context.view_layer
    for key in COLLECTION_NAMES:
        group = collection(key)
        if key in EVIDENCE_COLLECTIONS:
            group.hide_render = True
            layer = view_layer.layer_collection.children.get(group.name)
            if layer is not None:
                layer.hide_viewport = True
        state = "empty" if not group.objects else f"{len(group.objects)} objects"
        switched = "off" if key in EVIDENCE_COLLECTIONS else "on"
        print(f"[collection] {group.name}: {state}, {switched} by default", flush=True)


def render_every_figure(args: argparse.Namespace) -> None:
    """One PNG per entry in :data:`FIGURE_VIEWS` the scene can actually take.

    Renders happen after the blend is saved, so the shipped file is the one the
    figures came from and no render setting or visibility toggle leaks into it.
    A figure whose camera or objects the payload never produced is skipped rather
    than raising, because a site with no panorama still has twelve of them.
    """
    scene = bpy.context.scene
    if args.gpu:
        print(f"[render] {use_gpu()}", flush=True)
    scene.cycles.samples = args.samples
    scene.render.resolution_x = int(1920 * args.resolution_scale)
    scene.render.resolution_y = int(1080 * args.resolution_scale)
    scene.render.image_settings.file_format = "PNG"
    args.render_dir.mkdir(parents=True, exist_ok=True)
    for figure in FIGURE_VIEWS:
        name, camera = str(figure["name"]), str(figure["camera"])
        shown = tuple(figure["show"])
        if args.figures is not None and not any(name.startswith(wanted) for wanted in args.figures):
            continue
        lit = {COLLECTION_NAMES.get(key, key) for key in shown}
        # A figure is about the object its layer entry names, and a site that
        # never built that object has nothing to say in that frame. Without this
        # New York rendered the SAM 3 materials and the refused monocular depth
        # as two pictures of a bare mesh, which is worse than not rendering
        # them: it looks like the layer exists and is empty.
        subject = {name for name in dict(figure.get("layers", {})) if name not in bpy.data.objects}
        if camera not in bpy.data.objects or subject:
            print(f"[render] skipped {name}, this site has no {', '.join(sorted(subject)) or camera}", flush=True)
            continue
        # The mesh is scenery in most of these, so a figure that shows the mesh
        # and one empty layer is a figure of the mesh. Krakow was rendering the
        # refusals that way.
        over = [key for key in shown if key != "twin"]
        if over and not any(BUILT[key].objects for key in over if key in BUILT):
            print(f"[render] skipped {name}, this site built none of {', '.join(over)}", flush=True)
            continue
        wanted = figure.get("objects")
        dropped = set(figure.get("hide", ()))
        for group in bpy.data.collections:
            group.hide_render = group.name not in lit
            for obj in group.objects:
                obj.hide_render = (
                    group.name not in lit or obj.name in dropped or (wanted is not None and obj.name not in wanted)
                )
        for obj_name, channel in dict(figure.get("layers", {})).items():
            if obj_name in bpy.data.objects:
                show_layer(bpy.data.objects[obj_name], channel)
        scene.camera = bpy.data.objects[camera]
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
    parser.add_argument(
        "--rim-width-scale",
        type=float,
        default=0.04,
        help="Rim radius in metres per square root metre of slant range",
    )
    parser.add_argument(
        "--rim-site-step",
        type=int,
        default=10,
        help="One drawn site every this many azimuths. Ten of 720 is every five degrees",
    )
    parser.add_argument("--nee-ray-radius-m", type=float, default=0.09)
    parser.add_argument("--nee-line-radius-m", type=float, default=0.05)
    parser.add_argument(
        "--nee-sky-leg-m",
        type=float,
        default=30.0,
        help="Drawn length of the leg that left the scene, which in 09 runs to the sky sphere",
    )
    parser.add_argument("--point-radius-m", type=float, default=0.09, help="Drawn size of one depth cloud point")
    parser.add_argument(
        "--pose-sigma-scale",
        type=float,
        default=10.0,
        help="Life sizes the pose covariance ellipsoid is drawn at. One sigma here is centimetres",
    )
    parser.add_argument("--render-dir", type=pathlib.Path, help="Also render one PNG per camera")
    parser.add_argument(
        "--gpu", action="store_true", help="Render on the accelerator, and fail loudly if there is none"
    )
    parser.add_argument(
        "--figures",
        nargs="+",
        help="Render only the figures whose name starts with one of these, for iterating on one layer",
    )
    parser.add_argument("--samples", type=int, default=64)
    parser.add_argument("--resolution-scale", type=float, default=1.0)
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    return parser.parse_args(argv)


#: The sources a blend is built from. A blend whose fingerprint over these does
#: not match today's is a build artefact from different code, exactly the way a
#: compiled binary is, and on 3 August every blend in the tree was one.
BUILDER_SOURCES = (
    "propagation_blender.py",
    "export_propagation_payload.py",
    "semantic_twin/propagation/walk.py",
    "semantic_twin/propagation/route.py",
)


def builder_fingerprint() -> str:
    """A hash over the code that writes a blend, stamped into the blend.

    A timestamp cannot answer "was this built by today's code". Committing an
    unchanged file moves its commit time forward and makes a perfectly current
    blend look stale, which is what happened the first time this was checked.
    Hashing the bytes answers it exactly and says nothing about when.
    """
    root = pathlib.Path(__file__).resolve().parent
    digest = hashlib.sha256()
    for name in BUILDER_SOURCES:
        path = root / name
        digest.update(path.read_bytes() if path.exists() else b"")
    return digest.hexdigest()[:16]


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
    legs = build_ray_depth(payload, collection("bounces"), base_radius=args.ray_radius_m)
    connections: dict[str, object] = {}
    if "nee_origin_m" in payload.files:
        connections = build_next_event(
            payload,
            collection("nee"),
            drawn_radius_m=float(manifest["drawn_radius_m"]),
            ray_radius=args.nee_ray_radius_m,
            line_radius=args.nee_line_radius_m,
            sky_leg_m=args.nee_sky_leg_m,
        )
    peaks = build_arrival(
        payload,
        hero,
        collection("arrival"),
        scale_m=args.lobe_scale_m,
        offset_m=args.lobe_offset_m,
        floor=args.lobe_floor,
    )
    sources = build_network(
        payload,
        hero,
        manifest,
        collection("network"),
        width_scale=args.rim_width_scale,
        site_step=args.rim_site_step,
    )
    walk_range = build_walk(payload, collection("walk"), args.walk_model)
    sab_range = build_body(payload, hero, ground_z, collection("body"))

    evidence: dict[str, object] = {}
    semantics = collection("semantics")
    for taxonomy in ("vistas", "sam3"):
        built = build_fishnet(payload, manifest, taxonomy, semantics)
        if built is not None:
            evidence[f"fishnet_{taxonomy}"] = built
    evidence["support_evidence"] = build_support_evidence(payload, manifest, collection("evidence"))
    evidence["refused"] = build_refused(payload, manifest, collection("refused"))
    evidence["depth"] = build_depth(payload, manifest, collection("depth"), radius=args.point_radius_m)
    evidence["panoramas"] = build_panoramas(
        payload, manifest, collection("panoramas"), sigma_scale=args.pose_sigma_scale
    )
    evidence["bodies"] = build_bodies(payload, manifest, collection("bodies"))
    evidence = {key: value for key, value in evidence.items() if value is not None}

    cameras = collection("cameras")
    build_cameras(twin, hero, ground_z, cameras)
    build_evidence_cameras(twin, payload, hero, ground_z, cameras)
    build_lighting(hero)
    hide_heavy_collections()
    frame_the_viewport(twin, hero)

    scene = bpy.context.scene
    scene["site"] = manifest["site"]
    scene["builder_fingerprint"] = builder_fingerprint()
    scene["frequency_ghz"] = manifest["frequency_hz"] / 1.0e9
    scene["traced_crop_radius_m"] = manifest["traced_crop_radius_m"]
    scene["drawn_radius_m"] = manifest["drawn_radius_m"]
    scene["hero_sky_fraction"] = manifest["hero"]["sky_fraction"]
    scene["hero_susceptibility"] = json.dumps(manifest["hero"]["susceptibility"])
    scene["ray_bundle_counts"] = json.dumps(rays)
    scene["ray_leg_counts"] = json.dumps(legs)
    scene["next_event_counts"] = json.dumps(connections)
    scene["evidence_layers"] = json.dumps(evidence, default=str)
    scene["reading_note"] = (
        "Every object here is measured. Ray thickness is the cube root of throughput. "
        "The lobes are normalised by their own peak so their shapes compare and their "
        "levels do not. The drawn mesh is smaller than the traced mesh, see "
        "drawn_radius_m against traced_crop_radius_m. The evidence collections start "
        "hidden and each of their objects carries several colour layers, listed on the "
        "object as colour_layers. PAYLOAD.md says what each one means."
    )
    if "evidence" in manifest:
        offset = manifest["evidence"].get("semantic_surface_offset_from_drawn_mesh")
        if offset is not None:
            scene["semantic_surface_offset_from_drawn_mesh"] = json.dumps(offset)
        camera = manifest["evidence"].get("camera")
        if camera is not None:
            scene["evidence_camera"] = json.dumps(camera)

    args.blend.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(args.blend.resolve()), compress=True)

    if args.render_dir is not None:
        render_every_figure(args)

    print(f"[twin] {len(twin.data.polygons)} triangles inside {manifest['drawn_radius_m']:g} m", flush=True)
    print(f"[rays] {rays}", flush=True)
    print(f"[bounces] {legs}", flush=True)
    print(f"[arrival] peak rho per sr { {k: round(v, 5) for k, v in peaks.items()} }", flush=True)
    print(f"[network] {json.dumps(sources)}", flush=True)
    print(f"[nee] {json.dumps(connections)}", flush=True)
    print(f"[walk] chi range {walk_range[0]:.2f} to {walk_range[1]:.2f} dB", flush=True)
    print(f"[body] Sab {sab_range[0]:.4g} to {sab_range[1]:.4g} W/m2", flush=True)
    print(f"[evidence] {json.dumps(evidence, default=str)}", flush=True)
    print(f"[done] {args.blend} ({args.blend.stat().st_size / 1e6:.1f} MB)", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
