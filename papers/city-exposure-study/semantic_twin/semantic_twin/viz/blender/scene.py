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
from typing import Any, Mapping, Sequence

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
    current["reading_note"] = (
        "Every object here is measured. Ray thickness is the cube root of throughput. "
        "The lobes are normalised by their own peak so their shapes compare and their "
        "levels do not. The drawn mesh is smaller than the traced mesh, see "
        "drawn_radius_m against traced_crop_radius_m. The evidence collections start "
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

#: Collections that start switched off. Most of them exist only when the payload
#: carries them and are dropped when it does not. A quarter of a million points and
#: eighteen SMPL-X bodies are worth having and are not worth waiting for on every
#: open. ``bounces`` is always built and is off for a different reason: it is the
#: same paths as ``rays`` cut differently, so drawing both at once draws every ray
#: twice.
EVIDENCE_COLLECTIONS: tuple[str, ...] = (
    "bounces",
    "nee",
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
    curves = bpy.data.hair_curves.new(name)
    curves.add_curves([int(value) for value in lengths])
    curves.attributes["position"].data.foreach_set("vector", points.astype(np.float32).ravel())
    if "radius" not in curves.attributes:
        curves.attributes.new("radius", "FLOAT", "POINT")
    curves.attributes["radius"].data.foreach_set("value", radius.astype(np.float32))
    obj = bpy.data.objects.new(name, curves)
    into.objects.link(obj)
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
    if channel in colours.keys() and hasattr(colours, "active_color_index"):
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


def build_evidence_cameras(twin: Any, payload: Any, hero: np.ndarray, ground_z: float, into: Any) -> None:
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


def hide_heavy_collections() -> None:
    """Start the heavy layers switched off, and leave the empty ones in place.

    Every collection in :data:`COLLECTION_NAMES` exists in every blend whether or
    not the site had the data for it. A site with no panorama then shows an empty
    ``06 panorama captures`` rather than no such row, so what is missing is visible
    instead of being something you have to already know to look for.

    Hiding is a separate question from existing. A quarter of a million depth points
    and eighteen SMPL-X bodies are worth having and are not worth waiting for on
    every open, so the evidence layers and the bounce split start off in the
    viewport and in the render.
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
