"""Assemble and render the showcase scene inside headless Blender.

This is the second stage of ``render_showcase.py``. It reads the payload that
the first stage wrote, imports the textured 3D Tiles leaves, builds one object
per semantic layer with its per-face colour channels attached, and renders every
requested view with Cycles.

Run it through the driver rather than by hand::

    python render_showcase.py --site korenmarkt

Direct invocation, for debugging one view::

    blender --background --python showcase_blender.py -- \
        --payload outputs/showcase_korenmarkt/payload.npz \
        --out outputs/showcase_korenmarkt/raw

Precision note. A Photorealistic 3D Tiles leaf carries its full ECEF placement,
around 6.4e6 m, in its glTF node matrix, and ``Object.matrix_world`` is single
precision with a spacing near 0.5 m at that magnitude. The tile placement is
therefore read out of the container in double precision and folded into the
mesh vertex data, and every object is left at the identity. No geometry in this
script is ever routed through ``matrix_world``.
"""

from __future__ import annotations

import argparse
import json
import math
import pathlib
import sys
from typing import Any

import bpy
import numpy as np
from mathutils import Matrix

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from semantic_twin.geo import enu_rotation, llh_to_ecef  # noqa: E402
from semantic_twin.gltf import mesh_node_matrices  # noqa: E402
from semantic_twin.showcase import read_payload  # noqa: E402

MATCH_TOLERANCE_M = 2.0


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--payload", type=pathlib.Path, required=True)
    parser.add_argument("--out", type=pathlib.Path, required=True)
    parser.add_argument("--blend", type=pathlib.Path)
    parser.add_argument("--views", nargs="*", help="Render only these view names")
    parser.add_argument("--samples", type=int, help="Override the sample count of every view")
    parser.add_argument("--resolution-scale", type=float, default=1.0)
    parser.add_argument("--device", default="GPU", choices=["GPU", "CPU"])
    parser.add_argument("--skip-tiles", action="store_true", help="Leave the textured leaves out, for fast iteration")
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    return parser.parse_args(argv)


def reset_scene() -> None:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0


def build_mesh(name: str, vertices: np.ndarray, faces: np.ndarray) -> bpy.types.Object:
    """One Blender object holding a triangle soup, placed at the identity."""
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
            f"{name}: Blender kept {len(mesh.polygons)} of {len(faces)} triangles. "
            "A dropped triangle would silently shift every per-face colour after it, "
            "so the payload has to arrive with no degenerate or duplicate faces."
        )
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def attach_channel(obj: bpy.types.Object, name: str, colours: np.ndarray) -> None:
    """Store a per-face colour as a corner colour attribute.

    Corner domain rather than face domain because the Attribute shader node
    reads corner colours directly and interpolation across a flat triangle with
    three identical corners is the identity.
    """
    mesh = obj.data
    attribute = mesh.color_attributes.new(name=name, type="FLOAT_COLOR", domain="CORNER")
    corner = np.repeat(np.ascontiguousarray(colours, dtype=np.float32), 3, axis=0)
    attribute.data.foreach_set("color", corner.ravel())


def flat_material(name: str, channel: str) -> bpy.types.Material:
    """A pure emitter at exactly the colour stored in one colour attribute.

    These layers encode a category. Their job is to put the legend colour on
    the screen, and anything that lights them puts something else there: total
    irradiance above one drives every saturated entry towards white, and a view
    transform with a shoulder finishes the job, so two classes that differ only
    in hue stop being distinguishable exactly where the reader is counting on
    them. An emission shader at unit strength, with the payload already in
    linear light and the Standard view transform on the way out, makes the
    rendered pixel equal to the legend swatch by construction.

    The cost is that the geometry loses its shading. That is the right trade for
    a figure whose content is which class a surface belongs to. The textured
    establishing view is the one that is lit, and it is lit like a photograph.
    """
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    material.cycles.emission_sampling = "NONE"
    tree = material.node_tree
    tree.nodes.clear()
    attribute = tree.nodes.new("ShaderNodeAttribute")
    attribute.attribute_name = channel
    attribute.location = (-400, 0)
    emission = tree.nodes.new("ShaderNodeEmission")
    emission.location = (-200, 0)
    emission.inputs["Strength"].default_value = 1.0
    output = tree.nodes.new("ShaderNodeOutputMaterial")
    output.location = (0, 0)
    tree.links.new(attribute.outputs["Color"], emission.inputs["Color"])
    tree.links.new(emission.outputs["Emission"], output.inputs["Surface"])
    return material


def tile_transform(tiles_dir: pathlib.Path) -> tuple[np.ndarray, list[tuple[dict[str, Any], pathlib.Path]]]:
    """The ECEF to local ENU transform of a tile cache, in double precision."""
    manifest = json.loads((tiles_dir / "manifest.json").read_text())
    records = manifest["tiles"]
    payloads = [(record, tiles_dir / record["file"]) for record in records]
    missing = [str(path) for _, path in payloads if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"{len(missing)} tile payloads are missing, first is {missing[0]}")
    lat = float(manifest["lat"])
    lon = float(manifest["lon"])
    rotation = enu_rotation(lat, lon)
    anchor = llh_to_ecef(lat, lon, 0.0)
    transform = np.eye(4)
    transform[:3, :3] = rotation
    transform[:3, 3] = -rotation @ anchor
    return transform, payloads


def import_tiles(tiles_dir: pathlib.Path, crop_radius_m: float) -> bpy.types.Collection:
    """Import the textured leaves and bake their exact placement into the meshes.

    Blender is asked only for the tile-local mesh data and the material graph.
    The placement comes from the glTF node matrices read in float64, and it is
    applied to the vertex coordinates here, so every imported object ends up at
    the identity with coordinates of order a hundred metres.
    """
    transform, payloads = tile_transform(tiles_dir)
    collection = bpy.data.collections.new("tiles")
    bpy.context.scene.collection.children.link(collection)

    kept = 0
    dropped = 0
    fallbacks = 0
    for index, (_record, path) in enumerate(payloads):
        known = set(bpy.data.objects)
        bpy.ops.import_scene.gltf(filepath=str(path))
        fresh = sorted((obj for obj in bpy.data.objects if obj not in known), key=lambda obj: obj.name)
        candidates = mesh_node_matrices(path)
        for obj in fresh:
            if obj.type != "MESH":
                bpy.data.objects.remove(obj, do_unlink=True)
                continue
            rounded = np.asarray(obj.matrix_world, dtype=np.float64)[:3, 3]
            distances = [float(np.linalg.norm(candidate[:3, 3] - rounded)) for candidate in candidates]
            best = int(np.argmin(distances)) if distances else -1
            if best >= 0 and distances[best] <= MATCH_TOLERANCE_M:
                placement = candidates[best]
            else:
                placement = np.asarray(obj.matrix_world, dtype=np.float64)
                fallbacks += 1
            world = transform @ placement
            coordinates = np.empty(len(obj.data.vertices) * 3, dtype=np.float64)
            obj.data.vertices.foreach_get("co", coordinates)
            coordinates = coordinates.reshape(-1, 3) @ world[:3, :3].T + world[:3, 3]
            obj.data.vertices.foreach_set("co", coordinates.astype(np.float32).ravel())
            obj.data.update()
            place(obj, np.eye(4))
            if float(np.linalg.norm(coordinates[:, :2], axis=1).min()) > crop_radius_m:
                dropped += 1
                bpy.data.objects.remove(obj, do_unlink=True)
                continue
            for current in list(obj.users_collection):
                current.objects.unlink(obj)
            collection.objects.link(obj)
            kept += 1
        if (index + 1) % 50 == 0:
            print(f"[tiles] {index + 1}/{len(payloads)}", flush=True)
    print(
        f"[tiles] kept {kept}, dropped {dropped} outside the crop, {fallbacks} single-precision fallbacks", flush=True
    )
    if fallbacks:
        raise RuntimeError(f"{fallbacks} tile objects could not be matched to a double-precision node matrix")
    return collection


def configure_outline(scene: bpy.types.Scene, settings: dict[str, Any]) -> None:
    """Draw silhouette and crease lines over the flat categorical layers.

    A pure emitter has no shading, so a building and the ground it stands on
    are the same flat colour and the geometry disappears. Freestyle puts the
    form back as a thin line along silhouettes, borders and hard creases. It
    only touches the pixels on those lines, so the interior of every class is
    still exactly its legend colour and the palette check still passes.
    """
    scene.render.use_freestyle = True
    scene.render.line_thickness_mode = "ABSOLUTE"
    scene.render.line_thickness = float(settings.get("thickness_px", 1.1))
    freestyle = scene.view_layers[0].freestyle_settings
    freestyle.as_render_pass = False
    for existing in list(freestyle.linesets):
        freestyle.linesets.remove(existing)
    lineset = freestyle.linesets.new("form")
    lineset.select_silhouette = True
    lineset.select_border = True
    lineset.select_crease = True
    lineset.select_edge_mark = False
    lineset.select_contour = False
    lineset.select_external_contour = False
    lineset.select_material_boundary = False
    freestyle.crease_angle = math.radians(float(settings.get("crease_angle_deg", 125.0)))
    style = lineset.linestyle
    style.color = tuple(settings.get("colour", [0.0, 0.0, 0.0]))[:3]
    style.alpha = float(settings.get("alpha", 0.55))
    style.thickness = float(settings.get("thickness_px", 1.1))


def flat_world(colour: list[float], strength: float) -> bpy.types.World:
    """A uniform white dome, for the views that are data maps rather than scenes.

    A class colour has to survive to the image. Under a sun it does not: the
    irradiance is far above one, so every saturated palette entry clips towards
    white and two classes that differ only in hue stop being distinguishable.
    A uniform dome near unit strength returns the albedo almost exactly, and
    the shading that remains is the geometry occluding its own sky, which is
    the depth cue the reader actually needs.
    """
    world = bpy.data.worlds.new("flat")
    world.use_nodes = True
    tree = world.node_tree
    tree.nodes.clear()
    background = tree.nodes.new("ShaderNodeBackground")
    background.inputs["Color"].default_value = tuple(colour)
    background.inputs["Strength"].default_value = strength
    output = tree.nodes.new("ShaderNodeOutputWorld")
    tree.links.new(background.outputs["Background"], output.inputs["Surface"])
    return world


def world_background(scene: bpy.types.Scene, zenith: list[float], horizon: list[float]) -> bpy.types.World:
    """A two-colour sky so the scene lights itself without an external HDRI."""
    world = bpy.data.worlds.new("showcase")
    scene.world = world
    world.use_nodes = True
    tree = world.node_tree
    tree.nodes.clear()
    geometry = tree.nodes.new("ShaderNodeNewGeometry")
    separate = tree.nodes.new("ShaderNodeSeparateXYZ")
    ramp = tree.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = -0.15
    ramp.color_ramp.elements[0].color = tuple(horizon)
    ramp.color_ramp.elements[1].position = 0.7
    ramp.color_ramp.elements[1].color = tuple(zenith)
    background = tree.nodes.new("ShaderNodeBackground")
    output = tree.nodes.new("ShaderNodeOutputWorld")
    tree.links.new(geometry.outputs["Incoming"], separate.inputs["Vector"])
    tree.links.new(separate.outputs["Z"], ramp.inputs["Fac"])
    tree.links.new(ramp.outputs["Color"], background.inputs["Color"])
    tree.links.new(background.outputs["Background"], output.inputs["Surface"])
    return world


def add_sun(name: str, elevation_deg: float, azimuth_deg: float, strength: float, angle_deg: float) -> bpy.types.Object:
    light = bpy.data.lights.new(name, type="SUN")
    light.energy = strength
    light.angle = math.radians(angle_deg)
    obj = bpy.data.objects.new(name, light)
    bpy.context.scene.collection.objects.link(obj)
    elevation = math.radians(elevation_deg)
    azimuth = math.radians(azimuth_deg)
    direction = np.array(
        [
            -math.sin(azimuth) * math.cos(elevation),
            -math.cos(azimuth) * math.cos(elevation),
            -math.sin(elevation),
        ]
    )
    matrix = np.eye(4)
    matrix[:3, :3] = look_at_basis(direction)
    place(obj, matrix)
    return obj


def place(obj: bpy.types.Object, matrix: np.ndarray) -> None:
    """Set an object's world matrix from a row-major 4x4, and check it took.

    Assigning a plain nested list to ``matrix_world`` transposes it: Blender
    reads the sequence column-major. A transposed rotation is still a rotation,
    so nothing errors and the object is simply aimed somewhere else, which for a
    camera means a render that looks plausible and shows the wrong thing. The
    read-back is here because that failure is invisible otherwise.
    """
    obj.matrix_world = Matrix(np.asarray(matrix, dtype=np.float64).tolist())
    stored = np.asarray(obj.matrix_world, dtype=np.float64)
    if not np.allclose(stored, matrix, atol=1e-5):
        raise RuntimeError(f"{obj.name}: Blender stored a different world matrix than the one asked for")


def look_at_basis(direction: np.ndarray) -> np.ndarray:
    """Camera basis whose minus Z runs along ``direction`` and whose up is world up."""
    forward = np.asarray(direction, dtype=np.float64)
    forward = forward / np.linalg.norm(forward)
    up = np.array([0.0, 0.0, 1.0])
    if abs(float(forward @ up)) > 0.999:
        up = np.array([0.0, 1.0, 0.0])
    right = np.cross(forward, up)
    right /= np.linalg.norm(right)
    true_up = np.cross(right, forward)
    return np.column_stack([right, true_up, -forward])


def build_camera(name: str, spec: dict[str, Any]) -> bpy.types.Object:
    """One camera, either aimed at a target or given an explicit basis.

    A crop of the panorama carries a registered roll, which a look-at cannot
    express, so those views pass their rotation straight through.
    """
    camera = bpy.data.cameras.new(name)
    camera.lens = float(spec["lens_mm"])
    camera.clip_start = 0.05
    camera.clip_end = 5000.0
    obj = bpy.data.objects.new(name, camera)
    bpy.context.scene.collection.objects.link(obj)
    position = np.asarray(spec["position"], dtype=np.float64)
    if "basis" in spec:
        basis = np.asarray(spec["basis"], dtype=np.float64)
    else:
        basis = look_at_basis(np.asarray(spec["target"], dtype=np.float64) - position)
    # The basis is written straight into the object matrix. Going through Euler
    # angles is a silent-failure path: an angle convention that disagrees with
    # Blender's leaves a camera that is plausibly but wrongly aimed, and a
    # panorama crop carries a registered roll that makes the error easy to miss.
    matrix = np.eye(4)
    matrix[:3, :3] = basis
    matrix[:3, 3] = position
    place(obj, matrix)
    return obj


def configure_render(scene: bpy.types.Scene, device: str, seed: int) -> None:
    scene.render.engine = "CYCLES"
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.compression = 15
    scene.render.film_transparent = False
    cycles = scene.cycles
    cycles.seed = seed
    cycles.use_animated_seed = False
    cycles.use_adaptive_sampling = True
    cycles.adaptive_threshold = 0.01
    cycles.use_denoising = True
    cycles.denoiser = "OPENIMAGEDENOISE"
    cycles.denoising_input_passes = "RGB_ALBEDO_NORMAL"
    cycles.max_bounces = 6
    cycles.diffuse_bounces = 3
    cycles.glossy_bounces = 3
    cycles.transmission_bounces = 4
    cycles.transparent_max_bounces = 8
    cycles.caustics_reflective = False
    cycles.caustics_refractive = False
    cycles.sampling_pattern = "BLUE_NOISE"
    scene.render.use_motion_blur = False
    if device == "GPU":
        preferences = bpy.context.preferences.addons["cycles"].preferences
        # Which backends exist is a property of the build, not of the machine.
        # A Linux build carries no METAL entry, so assigning the name raises
        # rather than reporting an absent device, and the probe dies on a box
        # that has a perfectly good CUDA card.
        offered = {item.identifier for item in preferences.bl_rna.properties["compute_device_type"].enum_items}
        for kind in ("OPTIX", "CUDA", "HIP", "METAL", "ONEAPI"):
            if kind not in offered:
                continue
            preferences.compute_device_type = kind
            preferences.get_devices()
            usable = [d for d in preferences.devices if d.type == kind]
            if usable:
                for entry in preferences.devices:
                    entry.use = entry.type in (kind, "CPU")
                cycles.device = "GPU"
                print(f"[render] {kind} on {[d.name for d in usable]}", flush=True)
                return
        print("[render] no GPU backend found, falling back to CPU", flush=True)
    cycles.device = "CPU"


def configure_scene_for_view(
    scene: bpy.types.Scene,
    view: dict[str, Any],
    worlds: dict[str, bpy.types.World],
    suns: list[bpy.types.Object],
    render: dict[str, Any],
    resolution_scale: float,
    samples: int | None,
) -> None:
    """Resolution, sampling, world and view transform for one view."""
    width, height = view["resolution"]
    scene.render.resolution_x = max(16, int(round(width * resolution_scale)))
    scene.render.resolution_y = max(16, int(round(height * resolution_scale)))
    scene.render.resolution_percentage = 100
    scene.cycles.samples = int(samples or view["samples"])
    lighting = view.get("lighting", "flat")
    scene.world = worlds[lighting]
    scene.render.use_freestyle = lighting == "flat" and bool(render.get("outline", {}))
    for sun in suns:
        sun.hide_render = lighting != "photographic"
    transform = view.get("view_transform", "Standard")
    scene.view_settings.view_transform = transform
    scene.view_settings.look = "AgX - Medium High Contrast" if transform == "AgX" else "None"


def apply_view(
    objects: dict[str, bpy.types.Object], materials: dict[str, bpy.types.Material], view: dict[str, Any]
) -> None:
    """Show the layers this view asks for and bind each to its colour channel.

    The textured leaves are a collection rather than a single object, so their
    visibility is set here too. Leaving that to the caller once meant the saved
    blend rendered an empty sky, because the tiles were still hidden from the
    import and nothing had turned them back on yet.
    """
    for obj in objects.values():
        obj.hide_render = True
    wanted_layers = {entry["layer"] for entry in view["layers"]}
    if "tiles" in bpy.data.collections:
        for obj in bpy.data.collections["tiles"].all_objects:
            obj.hide_render = "tiles" not in wanted_layers
    for entry in view["layers"]:
        name = entry["layer"]
        obj = objects.get(name)
        if obj is None:
            print(f"[view] {view['name']}: layer {name} is not in the payload, skipped", flush=True)
            continue
        obj.hide_render = False
        key = f"{name}:{entry['channel']}" if entry.get("channel") else f"{name}:solid"
        material = materials.get(key)
        if material is not None:
            obj.data.materials.clear()
            obj.data.materials.append(material)


def duplicate_stack(
    objects: dict[str, bpy.types.Object],
    materials: dict[str, bpy.types.Material],
    view: dict[str, Any],
) -> list[bpy.types.Object]:
    """Copies of one layer lifted apart in z, each showing a different channel."""
    created: list[bpy.types.Object] = []
    for entry in view.get("stack", []):
        source = objects.get(entry["layer"])
        if source is None:
            continue
        copy = source.copy()
        copy.data = source.data.copy()
        copy.name = f"{entry['layer']}_stack_{entry['channel']}"
        bpy.context.scene.collection.objects.link(copy)
        copy.location = (0.0, 0.0, float(entry["dz_m"]))
        copy.hide_render = False
        material = materials.get(f"{entry['layer']}:{entry['channel']}")
        if material is not None:
            copy.data.materials.clear()
            copy.data.materials.append(material)
        created.append(copy)
    return created


def main() -> None:
    args = arguments()
    layers, sidecar = read_payload(args.payload)
    args.out.mkdir(parents=True, exist_ok=True)

    reset_scene()
    scene = bpy.context.scene
    render = sidecar["render"]
    configure_render(scene, args.device, int(render["seed"]))
    worlds = {
        "photographic": world_background(scene, render["sky_zenith"], render["sky_horizon"]),
        "flat": flat_world(
            render.get("flat_world_colour", [1.0, 1.0, 1.0, 1.0]), float(render.get("flat_world_strength", 1.0))
        ),
    }
    if render.get("outline"):
        configure_outline(scene, render["outline"])
    suns = [
        add_sun(
            f"sun_{index}",
            float(sun["elevation_deg"]),
            float(sun["azimuth_deg"]),
            float(sun["strength"]),
            float(sun.get("angle_deg", 1.5)),
        )
        for index, sun in enumerate(render["suns"])
    ]

    objects: dict[str, bpy.types.Object] = {}
    materials: dict[str, bpy.types.Material] = {}
    for name, layer in layers.items():
        if not len(layer["faces"]):
            print(f"[layer] {name} is empty, skipped", flush=True)
            continue
        obj = build_mesh(name, layer["vertices"], layer["faces"])
        obj.data.shade_flat()
        for channel, colours in layer["channels"].items():
            attach_channel(obj, channel, colours)
            materials[f"{name}:{channel}"] = flat_material(f"{name}_{channel}", channel)
        objects[name] = obj
        print(f"[layer] {name}: {len(layer['faces'])} faces, channels {sorted(layer['channels'])}", flush=True)

    tiles = None if args.skip_tiles else sidecar.get("tiles")
    if tiles is not None:
        collection = import_tiles(pathlib.Path(tiles["directory"]), float(tiles["crop_radius_m"]))
        holder = bpy.data.objects.new("tiles_root", None)
        bpy.context.scene.collection.objects.link(holder)
        objects["tiles"] = holder
        for obj in collection.all_objects:
            obj.hide_render = True

    # Every view's camera is built here rather than inside the render loop, and
    # kept afterwards. A saved file with no camera cannot be rendered at all and
    # opens on whatever viewport orientation Blender last had, so the one artifact
    # a reader is most likely to open by hand was the one that could not
    # reproduce any of the figures beside it. Named cameras mean switching camera
    # reproduces a figure exactly, since each carries the framing the figure was
    # derived from.
    cameras = {view["name"]: build_camera(f"camera_{view['name']}", view["camera"]) for view in sidecar["views"]}

    if args.blend is not None:
        # Leave the file in the state of its first view, so opening it and
        # pressing render gives the establishing shot rather than a grey scene.
        opening = sidecar["views"][0]
        apply_view(objects, materials, opening)
        configure_scene_for_view(scene, opening, worlds, suns, render, args.resolution_scale, args.samples)
        scene.camera = cameras[opening["name"]]
        args.blend.parent.mkdir(parents=True, exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=str(args.blend.resolve()))
        print(f"[blend] {args.blend} with {len(cameras)} cameras, opening on {opening['name']}", flush=True)

    wanted = set(args.views) if args.views else None
    for view in sidecar["views"]:
        if wanted is not None and view["name"] not in wanted:
            continue
        apply_view(objects, materials, view)
        temporary = duplicate_stack(objects, materials, view)
        scene.camera = cameras[view["name"]]
        configure_scene_for_view(scene, view, worlds, suns, render, args.resolution_scale, args.samples)
        target = args.out / f"{view['name']}.png"
        scene.render.filepath = str(target)
        print(f"[render] {view['name']} at {scene.render.resolution_x}x{scene.render.resolution_y}", flush=True)
        bpy.ops.render.render(write_still=True)
        print(f"[render] wrote {target}", flush=True)
        for obj in temporary:
            bpy.data.objects.remove(obj, do_unlink=True)


if __name__ == "__main__":
    main()
