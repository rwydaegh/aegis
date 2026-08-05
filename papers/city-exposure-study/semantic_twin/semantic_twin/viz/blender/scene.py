"""The Blender vocabulary: collections, meshes, attributes, materials and cameras.

Everything here calls ``bpy`` and nothing here knows what a ray is. That is the
line the split is drawn on. A function in this module takes a name, some arrays
and a collection, and produces an object. Deciding which arrays is somebody else's
job, and that job lives in :mod:`~semantic_twin.viz.blender.estimator` and
:mod:`~semantic_twin.viz.blender.evidence`.

One convention runs through all of it. Every object carries its measured
quantities twice: once as a float or integer attribute holding the exact value,
which the spreadsheet editor shows, and once as a colour attribute holding the
shaded version. Switching what a surface shows is a click in the colour attribute
list rather than a rebuild, and the exact number survives next to the picture of
it.
"""

from __future__ import annotations

import json
import math
import pathlib
import colorsys
from collections.abc import Mapping, Sequence
from typing import Any

import bpy
import numpy as np

from .payload import builder_fingerprint, camera_rotation, production_scene_properties
from .style import colour_ramp


def stamp_scene(
    manifest: dict,
    *,
    rays: dict,
    legs: dict,
    connections: dict,
    layers: dict,
    root: pathlib.Path,
) -> None:
    """Write reading notes and measured counts onto the Blender scene."""
    current = bpy.context.scene
    current["site"] = manifest["site"]
    current["builder_fingerprint"] = builder_fingerprint(root)
    current["frequency_ghz"] = manifest["frequency_hz"] / 1.0e9
    current["traced_crop_radius_m"] = manifest["traced_crop_radius_m"]
    current["drawn_radius_m"] = manifest["drawn_radius_m"]
    current["hero_sky_fraction"] = manifest["hero"]["sky_fraction"]
    current["hero_susceptibility"] = json.dumps(manifest["hero"]["susceptibility"])
    current["ray_bundle_counts"] = json.dumps(rays)
    current["ray_leg_counts"] = json.dumps(legs)
    current["next_event_counts"] = json.dumps(connections)
    current["evidence_layers"] = json.dumps(layers, default=str)
    for name, value in production_scene_properties(manifest).items():
        current[name] = value
    atlas = manifest.get("surface_atlas")
    if isinstance(atlas, Mapping):
        current["surface_atlas_provenance"] = json.dumps(atlas, default=str)
        vocabularies = atlas.get("vocabularies", {})
        if isinstance(vocabularies, Mapping):
            current["surface_atlas_entity_vocabulary"] = json.dumps(vocabularies.get("entity", []))
            current["surface_atlas_material_vocabulary"] = json.dumps(vocabularies.get("material", []))
    outer = BUILT.get("outer_support")
    outer_built = outer is not None and len(outer.objects) > 0
    if outer_built:
        support_note = "The exact traced support is split into a strong inner view and a muted outer annulus. "
    elif (
        outer is not None and outer.get("reason") == "the exact full support has no faces outside the close-view radius"
    ):
        support_note = "The exact full support fits inside the close-view radius, so its outer annulus is empty. "
    else:
        support_note = "This legacy payload contains only the close-view support. The trace radius remains recorded. "
    current["reading_note"] = (
        "Every object here is measured. Ray thickness is the cube root of throughput. "
        "The lobes are normalised by their own peak so their shapes compare and their "
        f"levels do not. {support_note}The evidence collections start "
        "hidden and each of their objects carries several colour layers, listed on the "
        "object as colour_layers. PAYLOAD.md says what each one means."
    )
    record = manifest.get("evidence", {})
    offset = record.get("semantic_surface_offset_from_drawn_mesh")
    if offset is not None:
        current["semantic_surface_offset_from_drawn_mesh"] = json.dumps(offset)
    camera = record.get("camera")
    if camera is not None:
        current["evidence_camera"] = json.dumps(camera)


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
    BUILT.clear()


def use_gpu() -> str:
    """Point Cycles at whatever accelerator this machine has, or say so and stop.

    Half a million depth points and a quarter of a million ray legs is a minute a
    frame on four contended cores and seconds on the A6000, so the figures are
    worth moving. This is opt in rather than automatic, because a silent fallback
    to the CPU is the failure mode where you wait an hour and never learn why.
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


# ---------------------------------------------------------------------------
# Collections
# ---------------------------------------------------------------------------

#: Internal key -> the name a person reads in the outliner. The keys stay short
#: because the figure table and the build code index on them. The names are
#: written for someone who opens the file having never read this script, which is
#: the only audience the outliner has. Order is the order they are created in, and
#: that is the order they appear in.
COLLECTION_NAMES: dict[str, str] = {
    "twin": "01 city mesh",
    "outer_support": "01B outer traced support",
    "support_extent": "01C support extent markers",
    "fused_semantics": "02A all-camera fused semantic and material evidence",
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
    "path_animation": "16 ranked path animation",
    "nee_animation": "17 NEE explanation animation",
}

COLLECTION_DESCRIPTIONS: dict[str, str] = {
    "twin": (
        "Exact inner propagation support with the whole-face geometric fallback classes. "
        "On atlas runs, supported ray hits use the joint atlas at the hit position."
    ),
    "outer_support": (
        "Exact outer part of the traced support mesh, from the close-view radius to the trace radius. "
        "It is muted for display and carries whole-face geometric fallback classes."
    ),
    "support_extent": (
        "Reference rings for the close-view radius and the full transport trace radius. "
        "The rings mark XY limits and are not propagation surfaces."
    ),
    "fused_semantics": (
        "Display audit of the joint semantic and material atlas used at supported ray-hit positions. "
        "Its shown classes are posterior winners; transport retains the full compatible material mixture."
    ),
    "semantics": (
        "Legacy single-panorama fishnet surfaces for audit. They preserve the older Vistas and SAM 3 views "
        "and are separate from the joint hit-position atlas."
    ),
    "evidence": "Image coverage and support-surface admission decisions.",
    "refused": "Image fragments refused by the support binding rules, grouped by exact refusal reason.",
    "depth": "Depth evidence used to test image-to-support agreement.",
    "panoramas": (
        "Registered panorama capture poses and their registration uncertainty. "
        "These are source-image locations, not exposure standpoints."
    ),
    "bodies": "Image-reconstructed transient bystanders. They are not the exposure phantom.",
    "walk": (
        "Exposure standpoints along the registered walk. Each point is a separate receiver position "
        "on the shared city twin."
    ),
    "arrival": (
        "Source-bearing angular power at the receiver. A lobe points along the reciprocal escape direction "
        "+local_grid; physical wave travel and the body coupler use k_hat = -local_grid."
    ),
}

#: Collections that start switched off. Most of them exist only when the payload
#: carries them and are dropped when it does not. A quarter of a million points and
#: eighteen SMPL-X bodies are worth having and are not worth waiting for on every
#: open. ``bounces`` is always built and is off for a different reason: it is the
#: same paths as ``rays`` cut differently, so drawing both at once draws every ray
#: twice.
EVIDENCE_COLLECTIONS: tuple[str, ...] = (
    "bounces",
    "nee",
    "outer_support",
    "support_extent",
    "fused_semantics",
    "semantics",
    "evidence",
    "refused",
    "depth",
    "panoramas",
    "bodies",
)

#: key -> the collection, so the rest of the build and the figure table can keep
#: using short keys while the file shows sentences.
BUILT: dict[str, Any] = {}


def collection(key: str) -> Any:
    """The collection for a key, created on first use and numbered for reading.

    Every key gets a collection whether or not anything goes in it. An empty one is
    the honest answer to a site that has no panorama: the structure is the same
    everywhere, and a layer that is missing is missing visibly rather than by not
    being there to notice.
    """
    if key in BUILT:
        return BUILT[key]
    made = bpy.data.collections.new(COLLECTION_NAMES.get(key, key))
    bpy.context.scene.collection.children.link(made)
    if key in COLLECTION_DESCRIPTIONS:
        made["description"] = COLLECTION_DESCRIPTIONS[key]
    if key == "semantics":
        made["legacy_display_layer"] = True
    if key == "fused_semantics":
        made["production_evidence_layer"] = True
    BUILT[key] = made
    return made


# ---------------------------------------------------------------------------
# Geometry
# ---------------------------------------------------------------------------


def build_mesh(name: str, vertices: np.ndarray, faces: np.ndarray, into: Any) -> Any:
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


def build_curves(name: str, points: np.ndarray, lengths: np.ndarray, radius: np.ndarray, into: Any) -> Any:
    """A hair curves object, which is the only curve type that carries attributes.

    A legacy Blender curve has a per point radius and nothing else, so the power a
    ray carries could be drawn and could not be read. A ``Curves`` datablock takes
    named attributes on its points, so the same number is both the thickness and a
    column in the spreadsheet, which is the convention the rest of this file uses
    everywhere else.
    """
    if len(lengths) == 0:
        # Blender 4.5 crashes when an empty Hair Curves datablock reaches the
        # dependency graph. Some ray bundles are legitimately empty, so keep an
        # empty mesh placeholder with the same point-attribute API instead.
        mesh = bpy.data.meshes.new(name)
        obj = bpy.data.objects.new(name, mesh)
        into.objects.link(obj)
        obj["curve_type"] = "POLY"
        obj["empty_curve_placeholder"] = True
        return obj

    curves = bpy.data.hair_curves.new(name)
    curves.add_curves([int(value) for value in lengths])
    # Hair Curves with no curve_type attribute evaluate as Catmull-Rom. That
    # smooth default can overshoot far beyond recorded bounce points.
    curves.set_types(type="POLY")
    curves.attributes["position"].data.foreach_set("vector", points.astype(np.float32).ravel())
    if "radius" not in curves.attributes:
        curves.attributes.new("radius", "FLOAT", "POINT")
    curves.attributes["radius"].data.foreach_set("value", radius.astype(np.float32))
    obj = bpy.data.objects.new(name, curves)
    into.objects.link(obj)
    obj["curve_type"] = "POLY"
    return obj


def point_cloud(name: str, points: np.ndarray, into: Any, *, radius: float, material: Any) -> Any:
    """A vertex only mesh turned into renderable points by one geometry node.

    A quarter of a million points as triangles would be a quarter of a million
    triangles and three times the vertices. As loose vertices it is one position
    each, and ``Mesh to Points`` gives Cycles something to shade without any of
    that reaching the file. The material has to be set inside the node group: the
    point component is new geometry and does not inherit the mesh's slots, and the
    symptom of forgetting is a cloud that renders pure black.
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


# ---------------------------------------------------------------------------
# Attributes and layers
# ---------------------------------------------------------------------------


def attach_face_colour(obj: Any, name: str, rgba: np.ndarray) -> None:
    """Store one colour per face on the corner domain, which shaders read directly."""
    attribute = obj.data.color_attributes.new(name=name, type="FLOAT_COLOR", domain="CORNER")
    corner = np.repeat(np.ascontiguousarray(rgba, dtype=np.float32), 3, axis=0)
    attribute.data.foreach_set("color", corner.ravel())


def attach_point_colour(obj: Any, name: str, rgba: np.ndarray, *, byte: bool = True) -> None:
    """One colour per vertex, byte encoded unless asked otherwise.

    Byte rather than float because a cloud is a quarter of a million points and
    four bytes against sixteen decides whether the file is worth downloading. Eight
    bits per channel is more than a shaded scalar carries anyway, and the exact
    value is on the float attribute next to it.

    Byte colours are stored non linearly, so a constant tint written this way comes
    back out of the shader at a visibly different colour. That does not matter for
    a ramp, where the reader is comparing one point against another and both moved
    the same way, and it does matter for a fixed key colour, so those pass
    ``byte=False``.
    """
    kind = "BYTE_COLOR" if byte else "FLOAT_COLOR"
    attribute = obj.data.color_attributes.new(name=name, type=kind, domain="POINT")
    attribute.data.foreach_set("color", np.ascontiguousarray(rgba, dtype=np.float32).ravel())


def attach_values(obj: Any, name: str, values: np.ndarray, domain: str) -> None:
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


def scalar_layers(
    obj: Any, columns: Mapping[str, np.ndarray], domain: str, *, ranges: Mapping[str, tuple[float, float]]
) -> None:
    """Attach every column twice, as its exact value and as a shaded colour."""
    attach = attach_face_colour if domain == "FACE" else attach_point_colour
    for name, values in columns.items():
        attach_values(obj, f"value_{name}", values, domain)
        low, high = ranges.get(name, (float(np.nanmin(values)), float(np.nanmax(values))))
        attach(obj, name, colour_ramp(np.nan_to_num(values, nan=low), low, max(high, low + 1.0e-9)))
        obj[f"{name}_range"] = [low, high]


#: Name of the attribute node every layered material carries. Renaming the
#: attribute it reads is the whole of switching a layer, so it is found by name
#: rather than by position in a node tree a reader may have rearranged.
LAYER_NODE = "layer"


def show_layer(obj: Any, channel: str) -> None:
    """Point an object's material and its viewport at one of its colour layers.

    Both are set, because they are read in different places: the shader path uses
    the attribute node, and solid shading with the colour source set to attribute
    uses whichever colour attribute is active. Setting one and not the other gives
    a viewport and a render that disagree, which is worse than either.

    A curves datablock holds colour attributes and has no active one to set, so
    only the shader half applies there.
    """
    for material in obj.data.materials:
        node = material.node_tree.nodes.get(LAYER_NODE) if material.use_nodes else None
        if node is not None:
            node.attribute_name = channel
    colours = obj.data.color_attributes
    if channel in colours and hasattr(colours, "active_color_index"):
        colours.active_color_index = colours.keys().index(channel)


def layered(obj: Any, channels: Sequence[str], default: str) -> None:
    """Record the layer list on the object and select the one it opens on."""
    obj["colour_layers"] = list(channels)
    obj["reading"] = "switch layer in Object Data Properties, Colour Attributes, or rename the 'layer' node"
    show_layer(obj, default)


# ---------------------------------------------------------------------------
# Materials
# ---------------------------------------------------------------------------


def emissive_material(
    name: str,
    channel: str | None,
    colour: tuple[float, float, float] = (1.0, 1.0, 1.0),
    *,
    strength: float = 1.0,
) -> Any:
    """A pure emitter, either at a fixed colour or at a colour attribute.

    Emission rather than a lit BSDF because these layers encode a measured number.
    A lit surface multiplies that number by whatever the lighting does, and two
    values that differ only in hue stop being distinguishable exactly where the
    reader is counting on them.

    Strength above one is a display gain and nothing else. It multiplies every
    value on the layer by the same factor, so it moves no ordering and no ratio,
    and it exists because the sunlit mesh is brighter than an emitter at one and a
    thin line drawn over it stops looking like light. The layers that use it say so
    on the object.
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


def lit_material(name: str, channel: str) -> Any:
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


def assign(obj: Any, material: Any) -> None:
    obj.data.materials.append(material)


def _payload_has(payload: Any, key: str) -> bool:
    keys = payload.files if hasattr(payload, "files") else payload
    return key in keys


def _compact_faces(vertices: np.ndarray, faces: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    used, remapped = np.unique(np.asarray(faces, dtype=np.int64), return_inverse=True)
    return np.asarray(vertices)[used], remapped.reshape((-1, 3))


def _stamp_inner_support(payload: Any, inner: Any, drawn_radius: float, traced_radius: float) -> int:
    inner["support_role"] = "exact inner propagation support and whole-face geometric fallback"
    inner["atlas_hit_rule"] = "supported observed hits use the joint atlas at the hit position"
    inner["whole_face_class_role"] = "fallback for unsupported atlas texels, or production binding on non-atlas runs"
    inner["display_radius_m"] = drawn_radius
    inner["transport_radius_m"] = traced_radius
    inner["muted_for_display"] = False
    face_count = len(inner.data.polygons)
    for key, attribute_name in (
        ("mesh_face_class", "surface_class_id"),
        ("mesh_face_source", "material_source_id"),
        ("mesh_face_index", "full_support_face_index"),
    ):
        if not _payload_has(payload, key):
            continue
        values = np.asarray(payload[key])
        if values.shape != (face_count,):
            raise ValueError(f"{key} must have one value per inner support face")
        attach_values(inner, attribute_name, values, "FACE")
    for payload_key, attribute_name in (
        ("mesh_face_index", "source_face_index"),
        ("mesh_face_source", "source_mesh_id"),
    ):
        if not _payload_has(payload, payload_key):
            continue
        values = np.asarray(payload[payload_key])
        if values.shape == (face_count,) and np.issubdtype(values.dtype, np.number):
            attach_values(inner, attribute_name, values, "FACE")
    return face_count


def _build_support_extent_markers(
    extent_collection: Any,
    drawn_radius: float,
    traced_radius: float,
    ground_z_m: float,
) -> None:
    angles = np.linspace(0.0, 2.0 * math.pi, 257)
    z = ground_z_m + 0.08
    for name, radius, colour in (
        ("close_view_boundary", drawn_radius, (0.20, 0.85, 1.00)),
        ("trace_support_boundary", traced_radius, (1.00, 0.58, 0.16)),
    ):
        points = np.column_stack([radius * np.cos(angles), radius * np.sin(angles), np.full(angles.size, z)])
        ring = build_curves(
            name,
            points,
            np.array([angles.size], dtype=np.int32),
            np.full(angles.size, 0.16, dtype=np.float64),
            extent_collection,
        )
        assign(ring, emissive_material(f"{name}_material", None, colour, strength=2.2))
        ring["radius_m"] = radius
        ring["boundary_role"] = "XY reference marker only; not a propagation surface"
    extent_collection["status"] = "built"
    extent_collection["close_view_radius_m"] = drawn_radius
    extent_collection["trace_radius_m"] = traced_radius


def _full_support_arrays(payload: Any) -> tuple[np.ndarray, np.ndarray, np.ndarray] | None:
    required = ("support_full_vertices", "support_full_faces", "support_full_face_class")
    if not all(_payload_has(payload, key) for key in required):
        return None
    vertices = np.asarray(payload["support_full_vertices"], dtype=np.float64)
    faces = np.asarray(payload["support_full_faces"], dtype=np.int64)
    face_class = np.asarray(payload["support_full_face_class"], dtype=np.int32)
    if vertices.ndim != 2 or vertices.shape[1] != 3 or faces.ndim != 2 or faces.shape[1] != 3:
        raise ValueError("full support vertices and faces must have shapes (V, 3) and (F, 3)")
    if face_class.shape != (faces.shape[0],):
        raise ValueError("support_full_face_class must have one value per full support face")
    return vertices, faces, face_class


def _support_face_radii(
    payload: Any,
    vertices: np.ndarray,
    faces: np.ndarray,
    *,
    inner_faces: int,
    drawn_radius: float,
    traced_radius: float,
) -> np.ndarray:
    radius = np.linalg.norm(vertices[faces].mean(axis=1)[:, :2], axis=1)
    full_inner_faces = int(np.count_nonzero(radius <= drawn_radius))
    if full_inner_faces != inner_faces:
        raise ValueError(
            "cropped inner support does not match the full support at the recorded display radius: "
            f"{inner_faces} cropped faces against {full_inner_faces} full-mesh faces"
        )
    if np.any(radius > traced_radius + 1.0e-6):
        raise ValueError("full support payload contains face centroids beyond the recorded trace radius")
    if _payload_has(payload, "mesh_face_index"):
        supplied_inner = np.asarray(payload["mesh_face_index"], dtype=np.int64)
        expected_inner = np.flatnonzero(radius <= drawn_radius)
        if not np.array_equal(supplied_inner, expected_inner):
            raise ValueError("inner support face indices do not match the full support at the display radius")
    return radius


def _build_outer_support_object(
    payload: Any,
    vertices: np.ndarray,
    faces: np.ndarray,
    face_class: np.ndarray,
    outer_indices: np.ndarray,
    outer_collection: Any,
    *,
    drawn_radius: float,
    traced_radius: float,
) -> None:
    outer_vertices, outer_faces = _compact_faces(vertices, faces[outer_indices])
    obj = build_mesh("support_mesh_outer", outer_vertices, outer_faces, outer_collection)
    muted = np.tile(np.array([[0.115, 0.135, 0.165, 1.0]], dtype=np.float64), (outer_indices.size, 1))
    attach_face_colour(obj, "muted_support", muted)
    attach_values(obj, "full_support_face_index", outer_indices, "FACE")
    attach_values(obj, "surface_class_id", face_class[outer_indices], "FACE")
    for key, attribute_name in (
        ("support_full_face_index", "source_face_index"),
        ("support_full_face_source", "material_source_id"),
    ):
        if not _payload_has(payload, key):
            continue
        supplied = np.asarray(payload[key])
        if supplied.shape == (faces.shape[0],) and np.issubdtype(supplied.dtype, np.number):
            attach_values(obj, attribute_name, supplied[outer_indices], "FACE")
    assign(obj, lit_material("outer_support_muted", "muted_support"))
    obj["support_role"] = "exact traced support outside the close-view, with whole-face geometric fallback classes"
    obj["inner_radius_exclusive_m"] = drawn_radius
    obj["outer_radius_inclusive_m"] = traced_radius
    obj["muted_for_display"] = True
    obj["geometry_is_exact"] = True
    outer_collection["status"] = "built"
    outer_collection["faces"] = int(outer_indices.size)
    outer_collection["display_note"] = "Muted only by colour. Geometry is unchanged."


def build_support_display(
    payload: Any,
    manifest: Mapping[str, Any],
    inner: Any,
    outer_collection: Any,
    extent_collection: Any,
    *,
    ground_z_m: float,
) -> dict[str, int | float | str]:
    """Add the exact outer trace support and mark both support radii.

    ``inner`` is the existing close-view support and fallback display. The full arrays are
    optional so older payloads still open. When they are present, this function
    takes outer faces straight from that mesh. It never stretches or invents a
    shell at the trace boundary.
    """
    drawn_radius = float(manifest["drawn_radius_m"])
    traced_radius = float(manifest["traced_crop_radius_m"])
    if not (0.0 < drawn_radius <= traced_radius):
        raise ValueError("support radii must satisfy 0 < drawn radius <= traced radius")
    inner_faces = _stamp_inner_support(payload, inner, drawn_radius, traced_radius)
    _build_support_extent_markers(extent_collection, drawn_radius, traced_radius, ground_z_m)

    full_support = _full_support_arrays(payload)
    if full_support is None:
        outer_collection["status"] = "empty"
        outer_collection["reason"] = (
            "legacy payload has no support_full_* arrays; rebuild the payload to display the exact outer support"
        )
        return {
            "inner_faces": inner_faces,
            "outer_faces": 0,
            "status": "legacy payload has inner support only",
            "drawn_radius_m": drawn_radius,
            "traced_radius_m": traced_radius,
        }

    vertices, faces, face_class = full_support
    radius = _support_face_radii(
        payload,
        vertices,
        faces,
        inner_faces=inner_faces,
        drawn_radius=drawn_radius,
        traced_radius=traced_radius,
    )
    outer_mask = radius > drawn_radius
    outer_indices = np.flatnonzero(outer_mask)
    if outer_indices.size == 0:
        outer_collection["status"] = "empty"
        outer_collection["reason"] = "the exact full support has no faces outside the close-view radius"
        outer_collection["faces"] = 0
        return {
            "inner_faces": inner_faces,
            "outer_faces": 0,
            "full_faces": int(faces.shape[0]),
            "status": "full traced support displayed; outer annulus is empty",
            "drawn_radius_m": drawn_radius,
            "traced_radius_m": traced_radius,
        }
    _build_outer_support_object(
        payload,
        vertices,
        faces,
        face_class,
        outer_indices,
        outer_collection,
        drawn_radius=drawn_radius,
        traced_radius=traced_radius,
    )
    return {
        "inner_faces": inner_faces,
        "outer_faces": int(outer_indices.size),
        "full_faces": int(faces.shape[0]),
        "status": "full traced support displayed",
        "drawn_radius_m": drawn_radius,
        "traced_radius_m": traced_radius,
    }


def _class_colours(
    values: np.ndarray,
    names: Sequence[str],
    *,
    phase: float = 0.0,
) -> tuple[np.ndarray, list[dict[str, Any]]]:
    """Give every vocabulary entry a unique colour and return its named legend."""
    classes = np.asarray(values, dtype=np.int64)
    labels = [str(name) for name in names]
    if not labels:
        raise ValueError("atlas class vocabulary cannot be empty")
    if classes.size and (classes.min() < 0 or classes.max() >= len(labels)):
        raise ValueError("atlas class winner leaves its declared vocabulary")

    # The golden-ratio hue step keeps adjacent vocabulary IDs far apart. Three
    # saturation/value bands prevent a 65-class entity axis from repeating hues.
    palette = np.empty((len(labels), 3), dtype=np.float64)
    for index in range(len(labels)):
        hue = (phase + index * 0.6180339887498949) % 1.0
        saturation = (0.70, 0.88, 0.58)[index % 3]
        value = (0.96, 0.82, 0.72)[(index // 3) % 3]
        palette[index] = colorsys.hsv_to_rgb(hue, saturation, value)
    rgba = np.column_stack([palette[classes], np.ones(classes.size)])
    present = set(int(value) for value in np.unique(classes))
    legend = [
        {"id": index, "name": name, "rgba": [*palette[index].tolist(), 1.0], "present": index in present}
        for index, name in enumerate(labels)
    ]
    return rgba, legend


def _atlas_vocabularies(
    manifest: Mapping[str, Any],
    entity: np.ndarray,
    material: np.ndarray,
) -> tuple[Mapping[str, Any], list[str], list[str]]:
    atlas = manifest.get("surface_atlas", {})
    atlas = atlas if isinstance(atlas, Mapping) else {}
    vocabularies = atlas.get("vocabularies", {})
    vocabularies = vocabularies if isinstance(vocabularies, Mapping) else {}
    entity_names = [str(value) for value in vocabularies.get("entity", [])]
    material_names = [str(value) for value in vocabularies.get("material", [])]
    if not entity_names:
        entity_names = [f"entity class {index}" for index in range(int(entity.max(initial=-1)) + 1)]
    if not material_names:
        material_names = [f"material class {index}" for index in range(int(material.max(initial=-1)) + 1)]
    return atlas, entity_names, material_names


def _atlas_scalar_columns(
    payload: Any, face_count: int
) -> tuple[dict[str, np.ndarray], dict[str, tuple[float, float]]]:
    columns: dict[str, np.ndarray] = {}
    ranges: dict[str, tuple[float, float]] = {}
    for key, output_name in (
        ("atlas_confidence", "confidence"),
        ("atlas_camera_count", "camera_count"),
        ("atlas_observation_count", "observation_count"),
    ):
        if not _payload_has(payload, key):
            continue
        values = np.asarray(payload[key])
        if values.shape != (face_count,):
            raise ValueError(f"{key} must have one value per atlas face")
        columns[output_name] = values
    if "confidence" in columns:
        ranges["confidence"] = (0.0, 1.0)
    return columns, ranges


def _attach_atlas_probabilities(
    obj: Any,
    payload: Any,
    *,
    face_count: int,
    entity_names: Sequence[str],
    material_names: Sequence[str],
) -> None:
    for key, prefix, names in (
        ("atlas_entity_probabilities", "entity_probability", entity_names),
        ("atlas_material_probabilities", "material_probability", material_names),
    ):
        if not _payload_has(payload, key):
            continue
        probabilities = np.asarray(payload[key], dtype=np.float64)
        if probabilities.ndim != 2 or probabilities.shape[0] != face_count:
            raise ValueError(f"{key} must have shape (atlas faces, classes)")
        if probabilities.shape[1] != len(names):
            raise ValueError(f"{key} width must match the canonical atlas vocabulary")
        attributes = []
        attribute_names: dict[str, str] = {}
        for channel, class_name in enumerate(names):
            name = f"{prefix}_{channel:02d}"
            attach_values(obj, name, probabilities[:, channel], "FACE")
            attributes.append(name)
            attribute_names[name] = class_name
        obj[f"{prefix}_channels"] = int(probabilities.shape[1])
        obj[f"{prefix}_attributes"] = attributes
        obj[f"{prefix}_names"] = json.dumps(attribute_names)
        obj[f"{prefix}_values_on_faces"] = True


def build_fused_semantic_surface(payload: Any, manifest: Mapping[str, Any], into: Any) -> dict[str, int | str]:
    """Build a display audit of the joint atlas used by hit-position transport."""
    entity_key = "atlas_entity" if _payload_has(payload, "atlas_entity") else "atlas_entity_class"
    material_key = "atlas_material" if _payload_has(payload, "atlas_material") else "atlas_material_class"
    required = ("atlas_vertices", "atlas_faces", entity_key, material_key)
    if not all(_payload_has(payload, key) for key in required):
        into["status"] = "empty"
        into["reason"] = "payload contains no all-camera fused atlas geometry"
        return {"status": "omitted", "faces": 0}

    vertices = np.asarray(payload["atlas_vertices"], dtype=np.float64)
    faces = np.asarray(payload["atlas_faces"], dtype=np.int64)
    entity = np.asarray(payload[entity_key], dtype=np.int32)
    material = np.asarray(payload[material_key], dtype=np.int32)
    if entity.shape != (faces.shape[0],) or material.shape != (faces.shape[0],):
        raise ValueError("atlas entity and material class arrays must have one value per atlas face")
    atlas_manifest, entity_names, material_names = _atlas_vocabularies(manifest, entity, material)
    entity_rgba, entity_legend = _class_colours(entity, entity_names)
    material_rgba, material_legend = _class_colours(material, material_names, phase=0.17)

    obj = build_mesh("all_camera_fused_surface_atlas", vertices, faces, into)
    attach_face_colour(obj, "entity_posterior_winner", entity_rgba)
    attach_face_colour(obj, "material_posterior_winner", material_rgba)
    attach_values(obj, "entity_class_id", entity, "FACE")
    attach_values(obj, "material_class_id", material, "FACE")
    scalar_columns, ranges = _atlas_scalar_columns(payload, faces.shape[0])
    if scalar_columns:
        scalar_layers(obj, scalar_columns, "FACE", ranges=ranges)
    assign(obj, lit_material("all_camera_fused_atlas", "material_posterior_winner"))
    layered(
        obj,
        ("material_posterior_winner", "entity_posterior_winner", *scalar_columns),
        "material_posterior_winner",
    )
    obj["surface_role"] = "display audit of joint all-camera entity and material atlas"
    obj["display_class_rule"] = "argmax posterior winner for colour only"
    obj["transport_role"] = "full compatible material posterior is evaluated at supported ray-hit positions"
    obj["atlas_drives_supported_hit_transport"] = True
    obj["display_winner_changes_transport"] = False
    obj["changes_transport"] = True
    obj["is_transport_geometry"] = False
    obj["whole_face_fallback_collection"] = COLLECTION_NAMES["twin"]
    obj["entity_vocabulary"] = json.dumps(entity_names)
    obj["material_vocabulary"] = json.dumps(material_names)
    obj["entity_colour_legend"] = json.dumps(entity_legend)
    obj["material_colour_legend"] = json.dumps(material_legend)
    if atlas_manifest:
        obj["canonical_surface_atlas_provenance"] = json.dumps(atlas_manifest, default=str)
    _attach_atlas_probabilities(
        obj,
        payload,
        face_count=faces.shape[0],
        entity_names=entity_names,
        material_names=material_names,
    )
    into["status"] = "built"
    into["faces"] = int(faces.shape[0])
    return {"status": "built", "faces": int(faces.shape[0])}


# ---------------------------------------------------------------------------
# Cameras, lighting and the saved view
# ---------------------------------------------------------------------------


def add_camera(name: str, location: Any, target: Any, into: Any, *, lens: float = 35.0) -> Any:
    data = bpy.data.cameras.new(name)
    data.lens = lens
    data.clip_end = 8000.0
    obj = bpy.data.objects.new(name, data)
    into.objects.link(obj)
    obj.location = tuple(float(v) for v in location)
    obj.rotation_euler = camera_rotation(location, target)
    return obj


def free_distance(twin: Any, subject: np.ndarray, direction: np.ndarray, reach: float) -> tuple[float, bool]:
    """How far a ray from ``subject`` gets, and whether anything stopped it.

    The two are not the same question. A ray that runs out of ``reach`` and a ray
    that hits a wall at ``reach`` return the same distance, and only the second one
    needs a standoff.
    """
    hit, location, _, _ = twin.ray_cast(subject, direction, distance=reach)
    if not hit:
        return reach, False
    return float(np.linalg.norm(np.asarray(location, dtype=np.float64) - subject)), True


def clear_view(
    twin: Any,
    subject: np.ndarray,
    reach: float,
    elevations_deg: Sequence[float],
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

    So search instead. A canyon has clear bearings, up the street and upward, and
    this finds the best one available rather than insisting on a bearing chosen for
    a different city. Ties break towards the lower elevation, which keeps a three
    quarter view wherever a three quarter view exists and only climbs overhead when
    nothing else is open.
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
                # Stand off only from something that is actually there. A bearing
                # that ran out of reach is open, and shortening it would frame
                # every site more tightly than asked for.
                usable = max(margin * free, 3.0) if blocked else free
                best_offset = direction * min(reach, usable)
    return subject + best_offset


def build_cameras(twin: Any, hero: np.ndarray, ground_z: float, into: Any) -> None:
    """Five cameras, four of them clearance checked and one deliberately not.

    A camera whose subject is at the standpoint has to see it, so it is cast
    towards and stopped short of whatever blocks it. The overview camera is the
    opposite case: it is meant to be outside the scene looking in, and casting from
    the standpoint towards it just finds the nearest facade, which at Korenmarkt put
    a bird's eye view 3.7 m from the observer. It is placed above the tallest drawn
    geometry instead, which is the constraint that actually applies to it.
    """
    eye = np.array([hero[0], hero[1], ground_z + 1.6])
    lobe = hero + np.array([0.0, 0.0, 13.0])
    plan = (
        ("cam_rays", hero, 85.0, (28.0, 40.0, 55.0, 72.0), hero, 35.0),
        ("cam_lobe", lobe, 18.0, (8.0, 18.0, 32.0, 55.0), lobe, 55.0),
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
    # The pedestrian view is at the standpoint by definition, so it has nothing to
    # clear. It looks along the most open bearing the standpoint has.
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


def build_walk_camera(twin: Any, walk_points: np.ndarray, into: Any, *, aspect: float = 16.0 / 9.0) -> Any:
    """Frame the measured route with modest street context.

    The camera looks across the route rather than along it. This places the
    route's main axis across the wide image dimension. Orthographic projection
    keeps every measured standpoint legible and makes the framing independent
    of one unusually deep facade in the city mesh.
    """
    points = np.asarray(walk_points, dtype=np.float64)
    if points.ndim != 2 or points.shape[0] < 2 or points.shape[1] != 3:
        raise ValueError("walk camera needs at least two three-dimensional walk points")
    if not np.isfinite(points).all() or not math.isfinite(aspect) or aspect <= 0.0:
        raise ValueError("walk camera points and aspect must be finite and the aspect must be positive")

    centre = points.mean(axis=0)
    centred_xy = points[:, :2] - centre[:2]
    _, _, axes = np.linalg.svd(centred_xy, full_matrices=False)
    route_axis = axes[0]
    route_span = float(np.ptp(centred_xy @ route_axis))
    cross_axis = np.array([-route_axis[1], route_axis[0]])
    cross_span = float(np.ptp(centred_xy @ cross_axis))

    reach = 80.0
    candidates: list[tuple[float, float, np.ndarray, bool]] = []
    for elevation_deg in (38.0, 52.0):
        vertical = math.sin(math.radians(elevation_deg))
        horizontal = math.cos(math.radians(elevation_deg))
        for sign in (1.0, -1.0):
            direction = np.array([sign * horizontal * cross_axis[0], sign * horizontal * cross_axis[1], vertical])
            free, blocked = free_distance(twin, centre, direction, reach)
            candidates.append((free, -elevation_deg, direction, blocked))
    free, _negative_elevation, direction, blocked = max(candidates, key=lambda candidate: candidate[:2])
    distance = max(0.82 * free, 8.0) if blocked else reach
    camera = add_camera("cam_walk", centre + distance * direction, centre, into, lens=70.0)
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = max(24.0, 1.28 * route_span / aspect, 3.0 * cross_span)
    camera["framing_subject"] = "exact walk_points bounds"
    camera["walk_route_span_m"] = route_span
    camera["walk_cross_span_m"] = cross_span
    camera["framing_margin_fraction"] = 0.28
    camera["orthographic_scale_m"] = camera.data.ortho_scale
    print(
        f"[camera] cam_walk frames {route_span:.1f} m route at {camera.data.ortho_scale:.1f} m orthographic scale",
        flush=True,
    )
    return camera


def build_full_support_camera(
    hero: np.ndarray,
    traced_radius_m: float,
    into: Any,
) -> Any:
    """Add an overhead camera for the full trace support without changing close views."""
    if not math.isfinite(traced_radius_m) or traced_radius_m <= 0.0:
        raise ValueError("full support camera radius must be finite and positive")
    centre = np.asarray(hero, dtype=np.float64).copy()
    centre[:2] = 0.0
    reach = max(1.45 * traced_radius_m, 90.0)
    camera = add_camera(
        "cam_full_support",
        centre + np.array([0.0, -0.65 * reach, reach]),
        centre,
        into,
        lens=42.0,
    )
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 2.55 * traced_radius_m
    camera["framing_subject"] = "full traced support and both exact XY extent markers"
    camera["trace_radius_m"] = traced_radius_m
    camera["orthographic_scale_m"] = camera.data.ortho_scale
    camera["preserves_close_view_cameras"] = True
    return camera


def build_evidence_cameras(twin: Any, payload: Any, hero: np.ndarray, into: Any) -> None:
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
    # surfaces visible from the capture point, most of it facade, 2296 of the 3306
    # faces of the first crop being Building. Any vantage outside the square is
    # therefore behind a wall that owns part of the layer it is trying to
    # photograph, and raising the camera until the wall clears turns the facades
    # edge on and frames roofs. So it stands where the panorama stood, five metres
    # up to clear the bystanders, and looks along the most open bearing. Nothing it
    # can see is occluded, because seeing it is what put it there.
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
        # The bodies stand all round the capture point, four crops of one panorama,
        # so their centroid is the camera. Standing there and looking at the
        # centroid frames nothing. The crowd is framed from outside its own
        # bounding sphere instead.
        crowd = payload["body_layer_vertices"].astype(np.float64).reshape(-1, 3)
        centre = crowd.mean(axis=0)
        spread = float(np.linalg.norm(crowd - centre, axis=1).max())
        reach = max(2.4 * spread, 14.0)
        add_camera("cam_bystanders", clear_view(twin, centre, reach, (12.0, 22.0, 38.0, 58.0)), centre, into, lens=34.0)
        print(f"[camera] cam_bystanders {reach:.1f} m out, crowd spread {spread:.1f} m", flush=True)


def frame_the_viewport(twin: Any, hero: np.ndarray) -> None:
    """Save a view that opens on the square, in every workspace the file ships with.

    A blend built headlessly keeps the factory viewport, which looks at the origin
    from two metres away with a one hundred metre clip. The square is 220 m across
    and its origin is the standpoint, so opening the file shows a grey wall of one
    facade seen from inside it, and the first thing anyone does is fight the
    navigation. Setting the pivot, the distance, the rotation and the far clip once
    here is the difference between a file that opens on the subject and a file that
    opens on nothing.

    Every workspace is set rather than only the layout one, because whichever tab
    the reader lands on is the one that has to be right.
    """
    # Imported here rather than at module level: mathutils ships inside Blender and
    # is absent from the venv, and the pure geometry in this package is tested
    # outside Blender.
    import mathutils

    heights = np.empty(len(twin.data.vertices) * 3)
    twin.data.vertices.foreach_get("co", heights)
    points = heights.reshape(-1, 3)
    span = float(np.linalg.norm(points[:, :2] - hero[:2], axis=1).max())
    pivot = np.array([hero[0], hero[1], float(np.quantile(points[:, 2], 0.5))])
    # Looking down the negative Y axis from thirty degrees up, which is the three
    # quarter view the figures use and the one a square reads best from.
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


def _exclude_heavy_collection(view_layer: Any, key: str, group: Any) -> None:
    if key not in EVIDENCE_COLLECTIONS:
        return
    layer = view_layer.layer_collection.children.get(group.name)
    if layer is not None:
        layer.exclude = True


def _stamp_collection_status(group: Any) -> str:
    state = "empty" if not group.objects else f"{len(group.objects)} objects"
    if "status" not in group:
        group["status"] = "empty" if not group.objects else "built"
    if not group.objects and "reason" not in group:
        group["reason"] = "the payload contains no objects for this optional layer"
    return state


def hide_heavy_collections() -> None:
    """Start the heavy layers switched off, and leave the empty ones in place.

    Every collection in :data:`COLLECTION_NAMES` exists in every blend whether or
    not the site had the data for it. A site with no panorama then shows an empty
    ``06 panorama captures`` rather than no such row, so what is missing is visible
    instead of being something you have to already know to look for.

    Hiding is a separate question from existing. A quarter of a million depth points
    and eighteen SMPL-X bodies are worth having and are not worth waiting for on
    every open, so the raw archive view layer excludes the evidence layers and the
    bounce split. Prepared scenes set their own exclusions. Collection-wide render
    flags are not used because the same collections are linked into every scene.
    """
    view_layer = bpy.context.view_layer
    for key in COLLECTION_NAMES:
        group = collection(key)
        _exclude_heavy_collection(view_layer, key, group)
        state = _stamp_collection_status(group)
        switched = "off" if key in EVIDENCE_COLLECTIONS else "on"
        print(f"[collection] {group.name}: {state}, {switched} by default", flush=True)
