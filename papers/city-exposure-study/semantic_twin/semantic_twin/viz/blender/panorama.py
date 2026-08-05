"""A registered source panorama behind measured Blender overlays.

The photograph stays a linked file. Blender renders the measured objects on a
transparent equirectangular camera and the compositor places those pixels over
the unchanged source image. The support mesh is a holdout in this scene only,
so it hides paths behind buildings without replacing the photograph with clay.

The camera transform is the same one used by the panorama projection code. A
Blender camera looks along local minus Z, with local X to the right and local Y
up. The panorama frame is right, forward, up. Its Blender columns are therefore
right, up, minus forward.
"""

from __future__ import annotations

import hashlib
import json
import math
import pathlib
from datetime import UTC, datetime
from dataclasses import dataclass
from typing import Any, Mapping

import numpy as np
from PIL import Image

from ...pano_geometry import panorama_to_world_matrix

KORENMARKT_HERO_CAPTURE = "walk_05_1084407470281938"
SUPPORT_OVERLAY_SCALE = 0.99999
SUPPORT_OVERLAY_OPACITY = 0.08
NEARBY_MARKER_NAME = "Nearby registered capture marker"


@dataclass(frozen=True)
class PanoramaAsset:
    """One linked equirectangular image and its registered ENU camera."""

    capture: str
    provider: str
    image_id: str
    image_path: pathlib.Path
    image_sha256: str
    width: int
    height: int
    pose_path: pathlib.Path
    position_enu_m: tuple[float, float, float]
    heading_deg: float
    pitch_deg: float
    roll_deg: float
    skyline_residual_deg: float
    sky_with_mesh_hit_fraction: float
    registration_verdict: str
    captured_at: str
    semantic_evidence_origin_distance_m: float | None = None
    hero_trace_origin_distance_m: float | None = None


def _registration_records(manifest: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...]:
    evidence = manifest.get("evidence")
    if not isinstance(evidence, Mapping):
        return ()
    registration = evidence.get("registration")
    if not isinstance(registration, Mapping):
        return ()
    records = registration.get("poses")
    if not isinstance(records, list):
        return ()
    return tuple(record for record in records if isinstance(record, Mapping))


def _source_image(folder: pathlib.Path) -> pathlib.Path:
    for name in ("panorama_original.jpg", "panorama_z5.jpg"):
        path = folder / name
        if path.is_file():
            return path
    raise FileNotFoundError(f"{folder} has no linked equirectangular source image")


def _capture_identity(metadata_path: pathlib.Path) -> tuple[str, str, str]:
    metadata = json.loads(metadata_path.read_text())
    image_id = str(metadata.get("id") or metadata.get("panoId") or "")
    if not image_id:
        raise ValueError(f"{metadata_path} does not name an image id")
    provider = "Mapillary" if "id" in metadata else "Street View"
    captured_value = metadata.get("captured_at") or metadata.get("date")
    if isinstance(captured_value, (int, float)):
        captured_at = datetime.fromtimestamp(float(captured_value) / 1000.0, UTC).isoformat()
    else:
        captured_at = str(captured_value or "unrecorded")
    return image_id, provider, captured_at


def _distance_between(position: tuple[float, float, float], candidate: Any) -> float | None:
    other = np.asarray(candidate, dtype=np.float64)
    if other.shape != (3,) or not np.isfinite(other).all():
        return None
    return float(np.linalg.norm(other - np.asarray(position)))


def select_panorama_asset(
    manifest: Mapping[str, Any],
    root: pathlib.Path,
    *,
    capture: str = KORENMARKT_HERO_CAPTURE,
) -> PanoramaAsset:
    """Resolve a registered capture named by the visualization manifest.

    The registration record is the admission point. Paths are then resolved
    from its exact pose file, rather than guessed from a panorama number.
    """
    matches = [record for record in _registration_records(manifest) if record.get("capture") == capture]
    if len(matches) != 1:
        raise ValueError(f"manifest must name exactly one registered panorama {capture!r}, found {len(matches)}")
    record = matches[0]
    pose_path = pathlib.Path(str(record["pose_file"]))
    if not pose_path.is_absolute():
        pose_path = root / pose_path
    if not pose_path.is_file():
        raise FileNotFoundError(pose_path)
    folder = pose_path.parent.parent
    metadata_path = folder / "metadata.json"
    if not metadata_path.is_file():
        raise FileNotFoundError(metadata_path)
    image_path = _source_image(folder)
    pose = json.loads(pose_path.read_text())
    image_id, provider, captured_at = _capture_identity(metadata_path)
    with Image.open(image_path) as image:
        width, height = image.size
    if width != 2 * height:
        raise ValueError(f"{image_path} is {width} by {height}, not a 2:1 equirectangular image")
    verdict = str(record.get("verdict", "unrecorded"))
    if verdict != "usable":
        raise ValueError(f"registered panorama {capture!r} has verdict {verdict!r}, not 'usable'")
    position = tuple(float(value) for value in pose["position_enu_m"])
    evidence = manifest.get("evidence") if isinstance(manifest.get("evidence"), Mapping) else {}
    camera = evidence.get("camera") if isinstance(evidence.get("camera"), Mapping) else {}
    hero = manifest.get("hero") if isinstance(manifest.get("hero"), Mapping) else {}
    return PanoramaAsset(
        capture=capture,
        provider=provider,
        image_id=image_id,
        image_path=image_path.resolve(),
        image_sha256=hashlib.sha256(image_path.read_bytes()).hexdigest(),
        width=width,
        height=height,
        pose_path=pose_path.resolve(),
        position_enu_m=position,
        heading_deg=float(pose["heading_deg"]),
        pitch_deg=float(pose["pitch_correction_deg"]),
        roll_deg=float(pose["roll_correction_deg"]),
        skyline_residual_deg=float(record["skyline_residual_deg"]),
        sky_with_mesh_hit_fraction=float(record["sky_with_mesh_hit_fraction"]),
        registration_verdict=verdict,
        captured_at=captured_at,
        semantic_evidence_origin_distance_m=_distance_between(position, camera.get("position_enu_m")),
        hero_trace_origin_distance_m=_distance_between(position, hero.get("point_enu_m")),
    )


def camera_matrix(asset: PanoramaAsset) -> np.ndarray:
    """Blender camera-local to ENU transform for the source panorama."""
    rotation = panorama_to_world_matrix(
        asset.heading_deg,
        pitch_deg=asset.pitch_deg,
        roll_deg=asset.roll_deg,
    )
    matrix = np.eye(4, dtype=np.float64)
    matrix[:3, 0] = rotation[:, 0]
    matrix[:3, 1] = rotation[:, 2]
    matrix[:3, 2] = -rotation[:, 1]
    matrix[:3, 3] = asset.position_enu_m
    return matrix


def _layer_collection(root: Any, name: str) -> Any | None:
    if root.collection.name == name:
        return root
    for child in root.children:
        found = _layer_collection(child, name)
        if found is not None:
            return found
    return None


def _support_overlay(prepared_scene: Any, support: Any, asset: PanoramaAsset) -> tuple[Any, int]:
    """A translucent copy of the traced support, on the same camera rays.

    Scaling about the panorama centre moves the copy just in front of the
    holdout without changing any angular coordinate. The copied mesh exists in
    this prepared scene only. Production geometry and recorded paths stay
    untouched.
    """
    import bpy
    from mathutils import Matrix, Vector

    material = bpy.data.materials.new(f"Panorama support overlay | {asset.capture}")
    material.use_nodes = True
    nodes = material.node_tree.nodes
    nodes.clear()
    transparent = nodes.new("ShaderNodeBsdfTransparent")
    emission = nodes.new("ShaderNodeEmission")
    emission.inputs["Color"].default_value = (0.02, 0.68, 0.92, 1.0)
    emission.inputs["Strength"].default_value = 1.0
    mixed = nodes.new("ShaderNodeMixShader")
    mixed.inputs[0].default_value = SUPPORT_OVERLAY_OPACITY
    output = nodes.new("ShaderNodeOutputMaterial")
    material.node_tree.links.new(transparent.outputs[0], mixed.inputs[1])
    material.node_tree.links.new(emission.outputs[0], mixed.inputs[2])
    material.node_tree.links.new(mixed.outputs[0], output.inputs["Surface"])

    overlay_group = bpy.data.collections.new(f"Panorama support overlay | {asset.capture}")
    prepared_scene.collection.children.link(overlay_group)
    centre = Matrix.Translation(Vector(asset.position_enu_m))
    scale = Matrix.Diagonal((SUPPORT_OVERLAY_SCALE, SUPPORT_OVERLAY_SCALE, SUPPORT_OVERLAY_SCALE, 1.0))
    display_transform = centre @ scale @ centre.inverted()
    count = 0
    for source in support.collection.all_objects:
        if source.type != "MESH":
            continue
        overlay = source.copy()
        overlay.data = source.data.copy()
        overlay.name = f"Panorama support registration | {source.name}"
        overlay.data.name = f"Panorama support display mesh | {source.data.name}"
        overlay.data.materials.clear()
        overlay.data.materials.append(material)
        overlay.matrix_world = display_transform @ source.matrix_world
        overlay.hide_select = True
        if hasattr(overlay, "visible_shadow"):
            overlay.visible_shadow = False
        overlay["role"] = "display-only support registration overlay"
        overlay["scale_about_panorama_camera"] = SUPPORT_OVERLAY_SCALE
        overlay["angular_projection_changed"] = False
        overlay["production_geometry_changed"] = False
        overlay_group.objects.link(overlay)
        count += 1
    if not count:
        raise RuntimeError("support collection contains no mesh object for the panorama registration overlay")
    return overlay_group, count


def _add_nearby_capture_marker(prepared_scene: Any, asset: PanoramaAsset) -> dict[str, Any] | None:
    """Draw one exact neighbouring registered camera position.

    The combined panorama marker mesh also contains the active camera position.
    Rendering it from inside that marker fills the whole equirectangular image.
    One neighbouring capture is enough to verify the shared ENU registration and
    keeps the photograph readable.
    """
    import bpy

    origin = np.asarray(asset.position_enu_m, dtype=np.float64)
    candidates = []
    for obj in prepared_scene.objects:
        if obj.type != "CAMERA" or "capture" not in obj or str(obj["capture"]) == asset.capture:
            continue
        position = np.asarray(obj.matrix_world.translation, dtype=np.float64)
        distance = float(np.linalg.norm(position - origin))
        if distance > 0.1:
            candidates.append((distance, obj, position))
    if not candidates:
        return None
    distance, source, position = min(candidates, key=lambda candidate: candidate[0])

    radius = 0.42
    vertices = np.array(
        [
            [radius, 0.0, 0.0],
            [-radius, 0.0, 0.0],
            [0.0, radius, 0.0],
            [0.0, -radius, 0.0],
            [0.0, 0.0, radius],
            [0.0, 0.0, -radius],
        ]
    )
    faces = (
        (0, 2, 4),
        (2, 1, 4),
        (1, 3, 4),
        (3, 0, 4),
        (2, 0, 5),
        (1, 2, 5),
        (3, 1, 5),
        (0, 3, 5),
    )
    mesh = bpy.data.meshes.new(NEARBY_MARKER_NAME)
    mesh.from_pydata(vertices.tolist(), (), faces)
    marker = bpy.data.objects.new(NEARBY_MARKER_NAME, mesh)
    marker.location = tuple(float(value) for value in position)
    marker["meaning"] = "exact ENU position of the nearest other registered panorama camera"
    marker["capture"] = str(source["capture"])
    marker["distance_from_active_capture_m"] = distance

    from .scene import emissive_material

    marker.data.materials.append(
        emissive_material(
            NEARBY_MARKER_NAME,
            None,
            colour=(1.0, 0.24, 0.04),
            strength=4.0,
        )
    )
    overlay = bpy.data.collections.new(f"Panorama registration overlay | {asset.capture}")
    prepared_scene.collection.children.link(overlay)
    overlay.objects.link(marker)
    return {
        "panorama_marker_capture": str(source["capture"]),
        "panorama_marker_distance_m": distance,
        "panorama_marker_radius_m": radius,
    }


def configure_panorama_scene(
    prepared_scene: Any,
    asset: PanoramaAsset,
    *,
    blend_path: pathlib.Path,
    support_collection_name: str = "01 city mesh",
) -> dict[str, Any]:
    """Make one prepared scene a registered 360 photograph overlay.

    Collections must already be linked into ``prepared_scene``. New objects are
    linked only to that scene, while their camera, material, mesh and image
    datablocks live in the blend as Blender requires. Geometry and recorded ray
    coordinates are left untouched.
    """
    import bpy
    from mathutils import Matrix

    camera_data = bpy.data.cameras.new(f"Panorama camera | {asset.capture}")
    camera_data.type = "PANO"
    camera_data.panorama_type = "EQUIRECTANGULAR"
    camera_data.longitude_min = -math.pi
    camera_data.longitude_max = math.pi
    camera_data.latitude_min = -math.pi / 2.0
    camera_data.latitude_max = math.pi / 2.0
    camera_data.clip_start = 0.01
    camera_data.clip_end = 2000.0
    camera = bpy.data.objects.new(camera_data.name, camera_data)
    prepared_scene.collection.objects.link(camera)
    camera.matrix_world = Matrix(camera_matrix(asset).tolist())
    prepared_scene.camera = camera

    prepared_scene.render.engine = "CYCLES"
    prepared_scene.render.resolution_x = asset.width
    prepared_scene.render.resolution_y = asset.height
    prepared_scene.render.resolution_percentage = 100
    prepared_scene.render.pixel_aspect_x = 1.0
    prepared_scene.render.pixel_aspect_y = 1.0
    prepared_scene.render.film_transparent = True
    prepared_scene.render.image_settings.file_format = "PNG"
    prepared_scene.render.image_settings.color_mode = "RGBA"
    prepared_scene.render.image_settings.color_depth = "8"
    prepared_scene.view_settings.view_transform = "Standard"
    prepared_scene.view_settings.look = "None"
    prepared_scene.view_settings.exposure = 0.0
    prepared_scene.view_settings.gamma = 1.0

    image = bpy.data.images.load(str(asset.image_path), check_existing=True)
    image.name = f"Linked panorama | {asset.provider} | {asset.image_id}"
    image.colorspace_settings.name = "sRGB"
    image.filepath = bpy.path.relpath(str(asset.image_path), start=str(blend_path.parent.resolve()))
    if image.packed_file is not None:
        raise RuntimeError(f"source panorama {asset.image_id} is packed; the scene contract requires a linked image")

    prepared_scene.use_nodes = True
    tree = prepared_scene.node_tree
    tree.nodes.clear()
    photograph = tree.nodes.new("CompositorNodeImage")
    photograph.name = "Linked source panorama"
    photograph.label = f"{asset.provider} {asset.image_id} | linked, not packed"
    photograph.image = image
    photograph_scale = tree.nodes.new("CompositorNodeScale")
    photograph_scale.name = "Fit panorama to render percentage"
    photograph_scale.space = "RENDER_SIZE"
    photograph_scale.frame_method = "STRETCH"
    overlay = tree.nodes.new("CompositorNodeRLayers")
    overlay.name = "Measured overlays"
    overlay.scene = prepared_scene
    overlay.layer = prepared_scene.view_layers[0].name
    alpha_over = tree.nodes.new("CompositorNodeAlphaOver")
    alpha_over.name = "Registered support overlay on source panorama"
    alpha_over.inputs[0].default_value = 1.0
    composite = tree.nodes.new("CompositorNodeComposite")
    tree.links.new(photograph.outputs["Image"], photograph_scale.inputs["Image"])
    tree.links.new(photograph_scale.outputs["Image"], alpha_over.inputs[1])
    tree.links.new(overlay.outputs["Image"], alpha_over.inputs[2])
    tree.links.new(alpha_over.outputs["Image"], composite.inputs["Image"])

    support = _layer_collection(prepared_scene.view_layers[0].layer_collection, support_collection_name)
    if support is None:
        raise KeyError(f"panorama scene has no support collection {support_collection_name!r}")
    support.holdout = True
    support_overlay, support_overlay_objects = _support_overlay(prepared_scene, support, asset)

    marker_properties = _add_nearby_capture_marker(prepared_scene, asset)

    linked_path = image.filepath
    properties = {
        "panorama_capture": asset.capture,
        "panorama_provider": asset.provider,
        "panorama_image_id": asset.image_id,
        "panorama_image_sha256": asset.image_sha256,
        "panorama_linked_path": linked_path,
        "panorama_image_packed": False,
        "panorama_projection": "equirectangular, full longitude and latitude",
        "panorama_pose_file": str(asset.pose_path),
        "panorama_skyline_residual_deg": asset.skyline_residual_deg,
        "panorama_sky_with_mesh_hit_fraction": asset.sky_with_mesh_hit_fraction,
        "panorama_registration_verdict": asset.registration_verdict,
        "panorama_captured_at": asset.captured_at,
        "panorama_support_overlay_collection": support_overlay.name,
        "panorama_support_overlay_objects": support_overlay_objects,
        "panorama_support_overlay_scale_about_camera": SUPPORT_OVERLAY_SCALE,
        "panorama_support_overlay_opacity": SUPPORT_OVERLAY_OPACITY,
        "panorama_support_overlay_offset_rule": (
            "display offset toward the panorama camera equals "
            f"(1 - {SUPPORT_OVERLAY_SCALE}) times camera range; angular projection is unchanged"
        ),
        "panorama_support_overlay_limit": (
            "The source photograph has no compositor depth. Foreground people, bicycles and the camera rig can "
            "therefore appear under the translucent support surface that lies behind them."
        ),
        "panorama_layers_excluded": "semantic fishnets; hero visual rays; hero NEE rays",
        "panorama_layers_excluded_reason": (
            "Their camera or trace origin differs from this photograph. They remain in their own prepared scenes."
        ),
        "panorama_overlay_note": (
            "The camera projection matches the source sphere exactly. The skyline residual records the remaining "
            "image-to-support-mesh disagreement. The one orange marker is the exact position of the nearest other "
            "registered panorama. Production ray coordinates are unchanged."
        ),
    }
    if marker_properties is not None:
        properties.update(marker_properties)
    if asset.semantic_evidence_origin_distance_m is not None:
        properties["panorama_semantic_evidence_origin_distance_m"] = asset.semantic_evidence_origin_distance_m
    if asset.hero_trace_origin_distance_m is not None:
        properties["panorama_hero_trace_origin_distance_m"] = asset.hero_trace_origin_distance_m
    for name, value in properties.items():
        prepared_scene[name] = value
        camera[name] = value
    return properties


__all__ = [
    "KORENMARKT_HERO_CAPTURE",
    "PanoramaAsset",
    "SUPPORT_OVERLAY_OPACITY",
    "SUPPORT_OVERLAY_SCALE",
    "camera_matrix",
    "configure_panorama_scene",
    "select_panorama_asset",
]
