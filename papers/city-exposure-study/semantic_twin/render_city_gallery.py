"""One establishing render per acquired city, from the cached Photorealistic 3D Tiles.

The full showcase in ``render_showcase.py`` needs a registered panorama, semantics
and a fishnet, so it only runs at sites that have been taken all the way through.
This is the geometry and texture half of it, which needs nothing but the tile
cache, so it runs at every city the moment acquisition finishes and gives a
comparable picture of built form across the whole set.

Camera framing is derived from each city's own geometry rather than hand placed,
so the cities are directly comparable and nothing is chosen per site.

Run headless:
    blender --background --python render_city_gallery.py -- --out gallery
"""

from __future__ import annotations

import argparse
import math
import pathlib
import sys

import bpy
import numpy as np
from mathutils import Euler, Vector

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from showcase_blender import import_tiles  # noqa: E402

TITLES = {
    "brussels_grandplace": "Grand-Place, Brussels",
    "istanbul_sultanahmet": "Sultanahmet Meydani, Istanbul",
    "korenmarkt": "Korenmarkt, Ghent",
    "krakow_rynek": "Rynek Glowny, Krakow",
    "london_trafalgar": "Trafalgar Square, London",
    "madrid_plazamayor": "Plaza Mayor, Madrid",
    "mexico_zocalo": "Plaza de la Constitucion, Mexico City",
    "milan_duomo": "Piazza del Duomo, Milan",
    "newyork_timessquare": "Times Square, New York",
    "prague_staromestske": "Staromestske namesti, Prague",
    "tokyo_hachiko": "Hachiko square, Shibuya, Tokyo",
    "toulouse_capitole": "Place du Capitole, Toulouse",
}


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tiles-root", type=pathlib.Path, default=SCRIPT_DIR / "data/tiles")
    parser.add_argument("--out", type=pathlib.Path, default=SCRIPT_DIR / "outputs/city_gallery")
    parser.add_argument("--sites", nargs="*", help="Restrict to these site directories")
    parser.add_argument("--crop-radius-m", type=float, default=130.0)
    parser.add_argument("--samples", type=int, default=96)
    parser.add_argument("--width", type=int, default=1600)
    parser.add_argument("--height", type=int, default=1000)
    parser.add_argument("--azimuth-deg", type=float, default=215.0)
    parser.add_argument("--elevation-deg", type=float, default=30.0)
    parser.add_argument("--fov-deg", type=float, default=46.0)
    parser.add_argument("--margin", type=float, default=1.12, help="Standoff slack beyond a tight fit")
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    return parser.parse_args(argv)


def use_gpu() -> str:
    """Cycles on whatever accelerator this build actually offers, else CPU."""
    preferences = bpy.context.preferences.addons["cycles"].preferences
    offered = {item.identifier for item in preferences.bl_rna.properties["compute_device_type"].enum_items}
    for kind in ("OPTIX", "CUDA", "HIP", "METAL", "ONEAPI"):
        if kind not in offered:
            continue
        preferences.compute_device_type = kind
        preferences.get_devices()
        usable = [device for device in preferences.devices if device.type == kind]
        if usable:
            for device in preferences.devices:
                device.use = device.type in (kind, "CPU")
            print(f"[render] {kind} on {[d.name for d in usable]}", flush=True)
            return "GPU"
    print("[render] no GPU backend offered by this build, using CPU", flush=True)
    return "CPU"


def scene_extent(collection: bpy.types.Collection) -> tuple[Vector, float, float]:
    """Ground level, a robust horizontal reach, and a robust skyline height."""
    heights = []
    reach = []
    for obj in collection.all_objects:
        if obj.type != "MESH":
            continue
        count = len(obj.data.vertices)
        coordinates = np.empty(count * 3, dtype=np.float64)
        obj.data.vertices.foreach_get("co", coordinates)
        coordinates = coordinates.reshape(-1, 3)
        heights.append(coordinates[:, 2])
        reach.append(np.linalg.norm(coordinates[:, :2], axis=1))
    z = np.concatenate(heights)
    r = np.concatenate(reach)
    # Percentiles rather than extrema, so one stray tile or one spire does not
    # set the framing for a whole city.
    return (
        Vector((0.0, 0.0, float(np.percentile(z, 2.0)))),
        float(np.percentile(r, 90.0)),
        float(np.percentile(z, 99.5) - np.percentile(z, 2.0)),
    )


def render_site(site: str, tiles_dir: pathlib.Path, args: argparse.Namespace) -> None:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = use_gpu()
    scene.cycles.samples = args.samples
    scene.cycles.use_denoising = True
    scene.render.resolution_x = args.width
    scene.render.resolution_y = args.height
    scene.render.image_settings.file_format = "PNG"
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Base Contrast"

    collection = import_tiles(tiles_dir, args.crop_radius_m)
    ground, radius, height = scene_extent(collection)
    print(f"[frame] {site}: ground {ground.z:.1f} m, p90 reach {radius:.0f} m, skyline {height:.0f} m", flush=True)

    anchor = ground + Vector((0.0, 0.0, 0.35 * height))
    az = math.radians(args.azimuth_deg)
    el = math.radians(args.elevation_deg)

    # Pull back far enough that the whole region of interest fits, horizontally
    # and vertically. A fixed multiple of the horizontal reach frames a low rise
    # square well and puts the camera inside the canyon at Times Square, whose
    # skyline is 254 m against a 27 m square in Toulouse.
    fov = math.radians(args.fov_deg)
    half_h = fov / 2.0
    half_v = math.atan(math.tan(half_h) * args.height / args.width)
    distance = args.margin * max(radius / math.tan(half_h), 0.5 * height / math.tan(half_v))
    print(f"[frame] {site}: standoff {distance:.0f} m", flush=True)
    eye = anchor + Vector((math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el))) * distance

    camera_data = bpy.data.cameras.new("orbit")
    camera_data.lens_unit = "FOV"
    camera_data.angle = fov
    camera_data.clip_start = 0.5
    camera_data.clip_end = 6000.0
    camera = bpy.data.objects.new("orbit", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera.location = eye
    camera.rotation_euler = (anchor - eye).normalized().to_track_quat("-Z", "Y").to_euler()

    sun_data = bpy.data.lights.new("sun", type="SUN")
    sun_data.energy = 3.2
    sun_data.angle = math.radians(2.0)
    sun = bpy.data.objects.new("sun", sun_data)
    sun.rotation_euler = Euler((math.radians(52.0), 0.0, math.radians(125.0)), "XYZ")
    scene.collection.objects.link(sun)

    world = bpy.data.worlds.new("sky")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.58, 0.70, 0.86, 1.0)
    world.node_tree.nodes["Background"].inputs[1].default_value = 1.0
    scene.world = world

    args.out.mkdir(parents=True, exist_ok=True)
    scene.render.filepath = str(args.out / f"{site}.png")
    bpy.ops.render.render(write_still=True)
    print(f"[wrote] {args.out / f'{site}.png'}  {TITLES.get(site, site)}", flush=True)


def main() -> None:
    args = arguments()
    sites = sorted(p.name for p in args.tiles_root.iterdir() if (p / "manifest.json").is_file())
    if args.sites:
        sites = [s for s in sites if s in set(args.sites)]
    print(f"[gallery] {len(sites)} sites: {', '.join(sites)}", flush=True)
    for site in sites:
        try:
            render_site(site, args.tiles_root / site, args)
        except Exception as error:  # one bad tile cache must not lose the gallery
            print(f"[skip] {site}: {type(error).__name__}: {error}", flush=True)


if __name__ == "__main__":
    main()
