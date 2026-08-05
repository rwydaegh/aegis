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
from collections.abc import Mapping
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from typing import Any

import numpy as np
from PIL import Image

from ...pano_geometry import PerspectiveView, extract_perspective, panorama_to_world_matrix

KORENMARKT_HERO_CAPTURE = "walk_05_1084407470281938"
SUPPORT_OVERLAY_SCALE = 0.99999
SUPPORT_OVERLAY_OPACITY = 0.08
NEARBY_MARKER_NAME = "Nearby registered capture marker"
ACQUISITION_COLLECTION_NAME = "Registered panorama acquisition poses"
RECTILINEAR_FOV_DEG = 90.0
RECTILINEAR_MAX_SIZE_PX = 1024
RECTILINEAR_PLANE_DISTANCE_M = 1.0
PANORAMA_DISPLAY_CLIP_START_M = 2.0
PANORAMA_DISPLAY_CLIP_RULE = (
    "The equirectangular camera ignores display geometry within 2 m of its acquisition pose. The linked photograph "
    "is composited independently. Companion markers and scene geometry beyond 2 m remain visible."
)


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
    position_sigma_m: float | None = None
    pose_uncertainty_json: str = "null"
    registration_record_json: str = "{}"
    atlas_panorama_sha256: str | None = None
    atlas_panorama_verification: str = "surface atlas panorama provenance unavailable"
    companion_assets: tuple[PanoramaAsset, ...] = ()
    unavailable_admitted_captures: tuple[str, ...] = ()
    omitted_admitted_captures_json: str = "[]"

    @property
    def acquisition_assets(self) -> tuple[PanoramaAsset, ...]:
        """The active capture followed by other admitted acquisition poses."""
        return (self, *self.companion_assets)


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


def _explicit_admitted_captures(value: Any) -> set[str]:
    """Read admission lists when a production manifest includes them.

    Older visualization manifests contain registration audit verdicts only.
    Newer manifests can carry the actual semantic admission decision as either
    ``admitted_captures`` or ``stations_admitted``. Registration quality and
    production admission remain separate facts.
    """
    found: set[str] = set()
    if isinstance(value, Mapping):
        for key, child in value.items():
            if key == "admitted_captures" and isinstance(child, list):
                found.update(str(item) for item in child if isinstance(item, str))
            elif key == "stations_admitted" and isinstance(child, list):
                for item in child:
                    if isinstance(item, str):
                        found.add(item)
                    elif isinstance(item, Mapping) and item.get("admitted", True):
                        name = item.get("capture") or item.get("station")
                        if name:
                            found.add(str(name))
            else:
                found.update(_explicit_admitted_captures(child))
    elif isinstance(value, list):
        for child in value:
            found.update(_explicit_admitted_captures(child))
    return found


def _path_from_record(record: Mapping[str, Any], root: pathlib.Path, *names: str) -> pathlib.Path | None:
    for name in names:
        value = record.get(name)
        if isinstance(value, str) and value:
            path = pathlib.Path(value)
            return path if path.is_absolute() else root / path
    return None


def _surface_atlas_document(manifest: Mapping[str, Any], root: pathlib.Path) -> Mapping[str, Any] | None:
    """Load the all-camera atlas manifest when the Blender manifest names it."""
    surface = manifest.get("surface_atlas")
    if isinstance(surface, Mapping):
        if isinstance(surface.get("cameras"), list):
            return surface
        atlas_manifest = _path_from_record(surface, root, "manifest", "manifest_path")
        if atlas_manifest is not None and atlas_manifest.is_file():
            value = json.loads(atlas_manifest.read_text())
            if isinstance(value, Mapping):
                return value
    final = manifest.get("final_surface_atlas")
    if isinstance(final, Mapping) and isinstance(final.get("cameras"), list):
        return final
    return None


def _atlas_camera_records(manifest: Mapping[str, Any], root: pathlib.Path) -> tuple[Mapping[str, Any], ...]:
    document = _surface_atlas_document(manifest, root)
    if document is None:
        return ()
    cameras = document.get("cameras")
    if not isinstance(cameras, list):
        return ()
    records = tuple(record for record in cameras if isinstance(record, Mapping))
    if len(records) != len(cameras):
        raise ValueError("surface atlas cameras must all be records")
    camera_ids = document.get("camera_ids")
    if camera_ids is not None:
        if not isinstance(camera_ids, list) or len(camera_ids) != len(records):
            raise ValueError("surface atlas camera_ids and cameras must have the same length")
        record_ids = [_capture_name(record) for record in records]
        if [str(value) for value in camera_ids] != record_ids:
            raise ValueError("surface atlas camera_ids do not match the ordered camera records")
    return records


def _capture_name(record: Mapping[str, Any]) -> str:
    return str(record.get("capture") or record.get("camera_id") or record.get("station") or "")


def _require_unique_capture_ids(records: tuple[Mapping[str, Any], ...], source: str) -> None:
    names = [_capture_name(record) for record in records]
    empty = sum(not name for name in names)
    duplicates = sorted({name for name in names if name and names.count(name) > 1})
    if empty or duplicates:
        detail = []
        if empty:
            detail.append(f"{empty} unnamed record(s)")
        if duplicates:
            detail.append(f"duplicate id(s): {', '.join(duplicates)}")
        raise ValueError(f"{source} must have unique named camera records. {'. '.join(detail)}")


def _combined_camera_record(camera: Mapping[str, Any], registration: Mapping[str, Any] | None) -> Mapping[str, Any]:
    combined = dict(camera)
    combined["capture"] = _capture_name(camera)
    if registration is not None:
        for key, value in registration.items():
            if key not in {"capture", "camera_id", "station"}:
                combined[key] = value
    return combined


def _record_or_pose(
    record: Mapping[str, Any],
    pose: Mapping[str, Any],
    key: str,
    *,
    default: float | None = None,
) -> float:
    """Read one pose value without evaluating an absent fallback eagerly."""
    if record.get(key) is not None:
        return float(record[key])
    if pose.get(key) is not None:
        return float(pose[key])
    if default is not None:
        return float(default)
    raise KeyError(key)


def _atlas_panorama_provenance(record: Mapping[str, Any], actual_sha256: str) -> tuple[str | None, str]:
    inputs = record.get("input_files")
    panorama = inputs.get("panorama") if isinstance(inputs, Mapping) else None
    if not isinstance(panorama, Mapping):
        return None, "surface atlas panorama provenance unavailable"
    expected_value = panorama.get("sha256")
    expected = str(expected_value).lower() if expected_value else None
    if expected is None:
        status = "surface atlas records no panorama input"
        if panorama.get("present") is True:
            status = "surface atlas says panorama present but records no SHA-256"
        return None, status
    if panorama.get("present") is False:
        raise ValueError("surface atlas panorama provenance records a SHA-256 for an absent file")
    if len(expected) != 64 or any(character not in "0123456789abcdef" for character in expected):
        raise ValueError("surface atlas panorama SHA-256 is malformed")
    if actual_sha256.lower() != expected:
        raise ValueError(
            "linked panorama SHA-256 does not match the image recorded by the surface atlas: "
            f"expected {expected}, got {actual_sha256.lower()}"
        )
    return expected, "verified against surface atlas panorama SHA-256"


def _verify_linked_atlas_panorama(asset: PanoramaAsset) -> None:
    if asset.atlas_panorama_sha256 is None:
        return
    linked_sha256 = hashlib.sha256(asset.image_path.read_bytes()).hexdigest()
    if linked_sha256 != asset.atlas_panorama_sha256:
        raise RuntimeError(
            f"linked panorama {asset.image_path} changed after atlas verification: "
            f"expected {asset.atlas_panorama_sha256}, got {linked_sha256}"
        )


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


def _resolve_panorama_asset(
    manifest: Mapping[str, Any],
    root: pathlib.Path,
    record: Mapping[str, Any],
) -> PanoramaAsset:
    capture = _capture_name(record)
    if not capture:
        raise KeyError("capture")
    pose_path = _path_from_record(record, root, "pose_file", "pose", "pose_path")
    if pose_path is None:
        raise KeyError("pose_file")
    if not pose_path.is_file():
        raise FileNotFoundError(pose_path)
    folder_path = _path_from_record(record, root, "folder")
    folder = folder_path if folder_path is not None else pose_path.parent.parent
    metadata_path = _path_from_record(record, root, "metadata", "metadata_path") or folder / "metadata.json"
    if not metadata_path.is_file():
        raise FileNotFoundError(metadata_path)
    image_path = _path_from_record(record, root, "panorama", "panorama_path", "image_path")
    if image_path is None:
        image_path = _source_image(folder)
    if not image_path.is_file():
        raise FileNotFoundError(image_path)
    pose = json.loads(pose_path.read_text())
    if not isinstance(pose, Mapping):
        raise TypeError(f"{pose_path} must contain a pose record")
    image_id, provider, captured_at = _capture_identity(metadata_path)
    with Image.open(image_path) as image:
        width, height = image.size
    if width != 2 * height:
        raise ValueError(f"{image_path} is {width} by {height}, not a 2:1 equirectangular image")
    verdict = str(record.get("verdict", "admitted by surface atlas"))
    position_value = record.get("position_enu_m", pose.get("position_enu_m"))
    position_array = np.asarray(position_value, dtype=np.float64)
    if position_array.shape != (3,) or not np.isfinite(position_array).all():
        raise ValueError(f"registered panorama {capture!r} has no finite three-dimensional ENU position")
    position = tuple(float(value) for value in position_array)
    evidence = manifest.get("evidence") if isinstance(manifest.get("evidence"), Mapping) else {}
    camera = evidence.get("camera") if isinstance(evidence.get("camera"), Mapping) else {}
    hero = manifest.get("hero") if isinstance(manifest.get("hero"), Mapping) else {}
    uncertainty = pose.get("pose_uncertainty")
    sky_conflict = pose.get("sky_conflict") if isinstance(pose.get("sky_conflict"), Mapping) else {}
    image_sha256 = hashlib.sha256(image_path.read_bytes()).hexdigest()
    atlas_panorama_sha256, atlas_panorama_verification = _atlas_panorama_provenance(record, image_sha256)
    return PanoramaAsset(
        capture=capture,
        provider=provider,
        image_id=image_id,
        image_path=image_path.resolve(),
        image_sha256=image_sha256,
        width=width,
        height=height,
        pose_path=pose_path.resolve(),
        position_enu_m=position,
        heading_deg=_record_or_pose(record, pose, "heading_deg"),
        pitch_deg=_record_or_pose(record, pose, "pitch_correction_deg", default=0.0),
        roll_deg=_record_or_pose(record, pose, "roll_correction_deg", default=0.0),
        skyline_residual_deg=float(
            record.get("skyline_residual_deg", record.get("residual_deg", pose.get("skyline_score_mean_deg", math.nan)))
        ),
        sky_with_mesh_hit_fraction=float(
            record.get(
                "sky_with_mesh_hit_fraction",
                sky_conflict.get("sky_with_mesh_hit_fraction", math.nan),
            )
        ),
        registration_verdict=verdict,
        captured_at=captured_at,
        semantic_evidence_origin_distance_m=_distance_between(position, camera.get("position_enu_m")),
        hero_trace_origin_distance_m=_distance_between(position, hero.get("point_enu_m")),
        position_sigma_m=float(record["position_sigma_m"]) if record.get("position_sigma_m") is not None else None,
        pose_uncertainty_json=json.dumps(uncertainty, sort_keys=True, separators=(",", ":")),
        registration_record_json=json.dumps(record, sort_keys=True, separators=(",", ":")),
        atlas_panorama_sha256=atlas_panorama_sha256,
        atlas_panorama_verification=atlas_panorama_verification,
    )


def select_panorama_asset(
    manifest: Mapping[str, Any],
    root: pathlib.Path,
    *,
    capture: str = KORENMARKT_HERO_CAPTURE,
) -> PanoramaAsset:
    """Resolve a registered capture named by the visualization manifest.

    The named registration record selects the active view. Production admission
    lists, when present, select the companion acquisition poses. Paths are
    resolved from pose files rather than guessed from panorama numbers.
    """
    registrations = _registration_records(manifest)
    _require_unique_capture_ids(registrations, "registration manifest")
    registration_by_capture = {_capture_name(record): record for record in registrations}
    atlas_cameras = _atlas_camera_records(manifest, root)
    if atlas_cameras:
        _require_unique_capture_ids(atlas_cameras, "surface atlas manifest")
    atlas_by_capture = {_capture_name(record): record for record in atlas_cameras}
    if capture in atlas_by_capture:
        matches = [_combined_camera_record(atlas_by_capture[capture], registration_by_capture.get(capture))]
    else:
        matches = [record for record in registrations if _capture_name(record) == capture]
    if len(matches) != 1:
        raise ValueError(f"manifest must name exactly one registered panorama {capture!r}, found {len(matches)}")
    record = matches[0]
    verdict = str(record.get("verdict", "unrecorded"))
    if capture not in atlas_by_capture and verdict != "usable":
        raise ValueError(f"registered panorama {capture!r} has verdict {verdict!r}, not 'usable'")
    active = _resolve_panorama_asset(manifest, root, record)

    if atlas_cameras:
        explicit = {_capture_name(item) for item in atlas_cameras}
        admitted = [
            _combined_camera_record(item, registration_by_capture.get(_capture_name(item))) for item in atlas_cameras
        ]
    else:
        explicit = _explicit_admitted_captures(manifest)
        if explicit:
            admitted = [item for item in registrations if _capture_name(item) in explicit]
        else:
            admitted = [
                item for item in registrations if bool(item.get("admitted", str(item.get("verdict", "")) == "usable"))
            ]
    companions: list[PanoramaAsset] = []
    omissions: list[dict[str, str]] = []
    available_records = {_capture_name(item) for item in admitted}
    unavailable: list[str] = sorted(explicit - available_records)
    omissions.extend(
        {"capture": name, "status": "omitted", "reason": "no matching camera record"} for name in unavailable
    )
    for item in admitted:
        name = _capture_name(item)
        if not name or name == capture:
            continue
        try:
            companions.append(_resolve_panorama_asset(manifest, root, item))
        except (FileNotFoundError, OSError, ValueError, KeyError) as error:
            unavailable.append(name)
            omissions.append(
                {
                    "capture": name,
                    "status": "omitted",
                    "reason": f"{type(error).__name__}: {error}",
                }
            )
    return replace(
        active,
        companion_assets=tuple(companions),
        unavailable_admitted_captures=tuple(unavailable),
        omitted_admitted_captures_json=json.dumps(omissions, sort_keys=True, separators=(",", ":")),
    )


def select_panorama_assets(
    manifest: Mapping[str, Any],
    root: pathlib.Path,
    *,
    capture: str = KORENMARKT_HERO_CAPTURE,
) -> tuple[PanoramaAsset, ...]:
    """Resolve the active panorama and every available admitted companion."""
    return select_panorama_asset(manifest, root, capture=capture).acquisition_assets


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
    overlay_group["panorama_overlay_collection"] = True
    overlay_group["panorama_overlay_role"] = "support registration overlay"
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
    """Draw one recorded neighbouring registered camera position.

    The combined panorama marker mesh also contains the active camera position.
    Rendering it from inside that marker fills the whole equirectangular image.
    One neighbouring capture is enough to verify the shared ENU registration and
    keeps the photograph readable.
    """
    import bpy

    origin = np.asarray(asset.position_enu_m, dtype=np.float64)
    candidates = []
    for obj in prepared_scene.objects:
        if (
            obj.type != "CAMERA"
            or obj.get("pose_role") != "registered panorama acquisition pose"
            or "capture" not in obj
            or str(obj["capture"]) == asset.capture
        ):
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
    marker["meaning"] = "recorded ENU position of the nearest other registered panorama camera"
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
    overlay["panorama_overlay_collection"] = True
    overlay["panorama_overlay_role"] = "nearby acquisition marker"
    overlay.objects.link(marker)
    return {
        "panorama_marker_capture": str(source["capture"]),
        "panorama_marker_distance_m": distance,
        "panorama_marker_radius_m": radius,
    }


def _asset_pose_properties(asset: PanoramaAsset) -> dict[str, Any]:
    properties: dict[str, Any] = {
        "capture": asset.capture,
        "image_id": asset.image_id,
        "provider": asset.provider,
        "captured_at": asset.captured_at,
        "pose_role": "registered panorama acquisition pose",
        "exposure_standpoint": False,
        "source_image_path": str(asset.image_path),
        "source_image_sha256": asset.image_sha256,
        "surface_atlas_panorama_sha256": asset.atlas_panorama_sha256 or "unrecorded",
        "surface_atlas_panorama_verification": asset.atlas_panorama_verification,
        "pose_file": str(asset.pose_path),
        "position_enu_m_json": json.dumps(asset.position_enu_m),
        "heading_deg": asset.heading_deg,
        "pitch_correction_deg": asset.pitch_deg,
        "roll_correction_deg": asset.roll_deg,
        "skyline_residual_deg": asset.skyline_residual_deg,
        "sky_with_mesh_hit_fraction": asset.sky_with_mesh_hit_fraction,
        "registration_verdict": asset.registration_verdict,
        "pose_uncertainty_json": asset.pose_uncertainty_json,
        "registration_record_json": asset.registration_record_json,
        "registration_limit": (
            "The pose is an estimate. The recorded residual and uncertainty describe remaining disagreement."
        ),
    }
    if asset.position_sigma_m is not None:
        properties["position_sigma_m"] = asset.position_sigma_m
    return properties


def _stamp_properties(target: Any, properties: Mapping[str, Any]) -> None:
    for name, value in properties.items():
        target[name] = value


def _new_panorama_camera(collection: Any, asset: PanoramaAsset) -> Any:
    import bpy
    from mathutils import Matrix

    camera_data = bpy.data.cameras.new(f"Acquisition 360 | {asset.capture}")
    camera_data.type = "PANO"
    camera_data.panorama_type = "EQUIRECTANGULAR"
    camera_data.longitude_min = -math.pi
    camera_data.longitude_max = math.pi
    camera_data.latitude_min = -math.pi / 2.0
    camera_data.latitude_max = math.pi / 2.0
    camera_data.clip_start = PANORAMA_DISPLAY_CLIP_START_M
    camera_data.clip_end = 2000.0
    camera = bpy.data.objects.new(camera_data.name, camera_data)
    collection.objects.link(camera)
    camera.matrix_world = Matrix(camera_matrix(asset).tolist())
    properties = _asset_pose_properties(asset)
    properties.update(
        {
            "view_role": "true equirectangular 360 acquisition camera",
            "projection": "equirectangular, full longitude and latitude",
            "panorama_display_clip_start_m": PANORAMA_DISPLAY_CLIP_START_M,
            "panorama_display_clip_rule": PANORAMA_DISPLAY_CLIP_RULE,
        }
    )
    _stamp_properties(camera, properties)
    return camera


def _safe_capture_name(capture: str) -> str:
    return "".join(character if character.isalnum() or character in "-_" else "_" for character in capture)


def _rectilinear_crop(asset: PanoramaAsset, blend_path: pathlib.Path) -> pathlib.Path:
    output = blend_path.parent / f"{blend_path.stem}_panorama_views"
    output.mkdir(parents=True, exist_ok=True)
    size = min(RECTILINEAR_MAX_SIZE_PX, asset.width)
    fov = f"{RECTILINEAR_FOV_DEG:g}".replace(".", "p")
    filename = f"{_safe_capture_name(asset.capture)}_{asset.image_sha256[:12]}_forward_{fov}_{size}px.png"
    crop_path = output / filename
    if crop_path.is_file():
        return crop_path.resolve()
    with Image.open(asset.image_path) as panorama:
        crop = extract_perspective(
            panorama,
            PerspectiveView("forward", 0.0, 0.0, RECTILINEAR_FOV_DEG),
            width=size,
            height=size,
        )
        crop.save(crop_path)
    return crop_path.resolve()


def _new_rectilinear_camera(
    collection: Any, asset: PanoramaAsset, blend_path: pathlib.Path
) -> tuple[Any, Any, pathlib.Path]:
    import bpy
    from mathutils import Matrix

    crop_path = _rectilinear_crop(asset, blend_path)
    crop_image = bpy.data.images.load(str(crop_path), check_existing=True)
    crop_image.name = f"Linked rectilinear panorama view | {asset.capture}"
    crop_image.colorspace_settings.name = "sRGB"
    crop_image.filepath = bpy.path.relpath(str(crop_path), start=str(blend_path.parent.resolve()))
    if crop_image.packed_file is not None:
        raise RuntimeError(f"rectilinear view for {asset.capture} is packed. It must stay linked")

    camera_data = bpy.data.cameras.new(f"Acquisition normal view | {asset.capture}")
    camera_data.type = "PERSP"
    camera_data.sensor_fit = "VERTICAL"
    camera_data.angle = math.radians(RECTILINEAR_FOV_DEG)
    camera_data.lens_unit = "FOV"
    camera_data.clip_start = 0.01
    camera_data.clip_end = 2000.0
    camera_data.show_background_images = True
    background = camera_data.background_images.new()
    background.image = crop_image
    background.alpha = 1.0
    background.display_depth = "BACK"
    background.frame_method = "FIT"

    camera = bpy.data.objects.new(camera_data.name, camera_data)
    collection.objects.link(camera)
    camera.matrix_world = Matrix(camera_matrix(asset).tolist())

    half_width = RECTILINEAR_PLANE_DISTANCE_M * math.tan(math.radians(RECTILINEAR_FOV_DEG) / 2.0)
    mesh = bpy.data.meshes.new(f"Projection-aligned image plane | {asset.capture}")
    mesh.from_pydata(
        [
            (-half_width, -half_width, 0.0),
            (half_width, -half_width, 0.0),
            (half_width, half_width, 0.0),
            (-half_width, half_width, 0.0),
        ],
        (),
        ((0, 1, 2, 3),),
    )
    uv_layer = mesh.uv_layers.new(name="Rectilinear crop UV")
    for loop, uv in zip(uv_layer.data, ((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)), strict=True):
        loop.uv = uv

    material = bpy.data.materials.new(f"Linked rectilinear crop | {asset.capture}")
    material.use_nodes = True
    nodes = material.node_tree.nodes
    nodes.clear()
    texture = nodes.new("ShaderNodeTexImage")
    texture.image = crop_image
    emission = nodes.new("ShaderNodeEmission")
    output = nodes.new("ShaderNodeOutputMaterial")
    material.node_tree.links.new(texture.outputs["Color"], emission.inputs["Color"])
    material.node_tree.links.new(emission.outputs[0], output.inputs["Surface"])
    mesh.materials.append(material)

    image_plane = bpy.data.objects.new(mesh.name, mesh)
    collection.objects.link(image_plane)
    plane_offset = Matrix.Translation((0.0, 0.0, -RECTILINEAR_PLANE_DISTANCE_M))
    image_plane.matrix_world = camera.matrix_world @ plane_offset
    image_plane.hide_render = True
    image_plane.hide_select = False
    image_plane["role"] = "projection-aligned rectilinear panorama image plane"
    image_plane["capture"] = asset.capture
    image_plane["linked_image_path"] = str(crop_path)
    image_plane["linked_image_sha256"] = hashlib.sha256(crop_path.read_bytes()).hexdigest()
    image_plane["projection_camera"] = camera.name
    image_plane["distance_from_camera_m"] = RECTILINEAR_PLANE_DISTANCE_M
    image_plane["fov_deg"] = RECTILINEAR_FOV_DEG
    image_plane["render_policy"] = (
        "Hidden in final renders. Use the camera background for overlays and this plane for spatial inspection."
    )
    image_plane["alignment_scope"] = (
        "Every point on this plane follows the matching rectilinear camera ray. Agreement with the support mesh "
        "is limited by the recorded pose residual, support-mesh error, image stitching, and scene change."
    )
    properties = _asset_pose_properties(asset)
    properties.update(
        {
            "view_role": "normal camera view with linked panorama crop",
            "rectilinear_crop_path": str(crop_path),
            "rectilinear_crop_sha256": hashlib.sha256(crop_path.read_bytes()).hexdigest(),
            "rectilinear_yaw_deg": 0.0,
            "rectilinear_pitch_deg": 0.0,
            "rectilinear_fov_deg": RECTILINEAR_FOV_DEG,
            "rectilinear_fov_axis": "vertical and horizontal within the square crop aperture",
            "rectilinear_scene_frame_rule": (
                "The panorama scene is 2:1. Vertical sensor fit and a FIT background put the square 90 degree "
                "crop in the centre half of that frame with the same pinhole rays as the image plane."
            ),
            "rectilinear_registration_limit": (
                "The crop and camera use the recorded registered pose without another adjustment. Mesh and image "
                "can still disagree by the recorded pose residual, support-mesh error, image stitching, and scene change."
            ),
            "background_scope": "Blender camera viewport background. The active hero scene compositor renders one capture",
        }
    )
    _stamp_properties(camera, properties)
    return camera, image_plane, crop_path


def _build_acquisition_views(
    prepared_scene: Any, asset: PanoramaAsset, blend_path: pathlib.Path
) -> tuple[Any, Any, dict[str, Any]]:
    import bpy

    acquisitions = asset.acquisition_assets
    capture_ids = [item.capture for item in acquisitions]
    if any(not capture for capture in capture_ids) or len(set(capture_ids)) != len(capture_ids):
        raise ValueError("panorama acquisition assets must have unique non-empty capture ids")
    for acquisition in acquisitions:
        position = np.asarray(acquisition.position_enu_m, dtype=np.float64)
        if position.shape != (3,) or not np.isfinite(position).all():
            raise ValueError(f"panorama acquisition {acquisition.capture!r} has an invalid ENU position")
        _verify_linked_atlas_panorama(acquisition)

    collection = bpy.data.collections.new(ACQUISITION_COLLECTION_NAME)
    prepared_scene.collection.children.link(collection)
    collection["panorama_overlay_collection"] = True
    collection["panorama_overlay_role"] = "registered acquisition cameras and projection planes"
    panorama_cameras = []
    normal_cameras = []
    image_planes = []
    crop_paths = []
    for acquisition in acquisitions:
        panorama_cameras.append(_new_panorama_camera(collection, acquisition))
        normal, image_plane, crop_path = _new_rectilinear_camera(collection, acquisition, blend_path)
        normal_cameras.append(normal)
        image_planes.append(image_plane)
        crop_paths.append(str(crop_path))
    collection["pose_role"] = "registered panorama acquisition poses"
    collection["separate_from"] = "walk exposure standpoints and interpolated route points"
    collection["capture_count"] = len(acquisitions)
    collection["captures_json"] = json.dumps(capture_ids)
    collection["unavailable_admitted_captures_json"] = json.dumps(asset.unavailable_admitted_captures)
    collection["omitted_admitted_captures_json"] = asset.omitted_admitted_captures_json
    return (
        panorama_cameras[0],
        collection,
        {
            "panorama_acquisition_collection": collection.name,
            "panorama_acquisition_capture_count": len(panorama_cameras),
            "panorama_acquisition_captures_json": collection["captures_json"],
            "panorama_acquisition_360_camera_count": len(panorama_cameras),
            "panorama_acquisition_rectilinear_camera_count": len(normal_cameras),
            "panorama_acquisition_image_plane_count": len(image_planes),
            "panorama_rectilinear_crop_paths_json": json.dumps(crop_paths),
            "panorama_unavailable_admitted_captures_json": collection["unavailable_admitted_captures_json"],
            "panorama_omitted_admitted_captures_json": collection["omitted_admitted_captures_json"],
            "panorama_pose_role_note": (
                "These cameras are registered image acquisition poses. The walk exposure standpoints are separate "
                "receiver positions, including route interpolation points."
            ),
        },
    )


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
    datablocks live in the blend as Blender requires. The active capture drives
    the compositor. Every available admitted capture also gets a true 360 camera
    and a normal camera with a linked rectilinear crop. Geometry and recorded
    ray coordinates are left untouched.
    """
    import bpy

    camera, _acquisition_collection, acquisition_properties = _build_acquisition_views(
        prepared_scene, asset, blend_path
    )
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
        raise RuntimeError(f"source panorama {asset.image_id} is packed. The scene contract requires a linked image")

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
    compositor_layer = prepared_scene.view_layers[0].name
    overlay.layer = compositor_layer
    alpha_over = tree.nodes.new("CompositorNodeAlphaOver")
    alpha_over.name = "Registered support overlay on source panorama"
    alpha_over.inputs[0].default_value = 1.0
    composite = tree.nodes.new("CompositorNodeComposite")
    tree.links.new(photograph.outputs["Image"], photograph_scale.inputs["Image"])
    tree.links.new(photograph_scale.outputs["Image"], alpha_over.inputs[1])
    tree.links.new(overlay.outputs["Image"], alpha_over.inputs[2])
    tree.links.new(alpha_over.outputs["Image"], composite.inputs["Image"])

    support = None
    support_holdout_layers = []
    for view_layer in prepared_scene.view_layers:
        layer_support = _layer_collection(view_layer.layer_collection, support_collection_name)
        if layer_support is None:
            raise KeyError(
                f"panorama scene view layer {view_layer.name!r} has no support collection {support_collection_name!r}"
            )
        layer_support.holdout = True
        support_holdout_layers.append(view_layer.name)
        if support is None:
            support = layer_support
    if support is None:
        raise RuntimeError("panorama scene has no view layers")
    support_overlay, support_overlay_objects = _support_overlay(prepared_scene, support, asset)

    marker_properties = _add_nearby_capture_marker(prepared_scene, asset)

    linked_path = image.filepath
    properties = {
        "panorama_capture": asset.capture,
        "panorama_provider": asset.provider,
        "panorama_image_id": asset.image_id,
        "panorama_image_sha256": asset.image_sha256,
        "panorama_surface_atlas_image_sha256": asset.atlas_panorama_sha256 or "unrecorded",
        "panorama_surface_atlas_image_verification": asset.atlas_panorama_verification,
        "panorama_linked_path": linked_path,
        "panorama_image_packed": False,
        "panorama_projection": "equirectangular, full longitude and latitude",
        "panorama_display_clip_start_m": PANORAMA_DISPLAY_CLIP_START_M,
        "panorama_display_clip_rule": PANORAMA_DISPLAY_CLIP_RULE,
        "panorama_pose_file": str(asset.pose_path),
        "panorama_skyline_residual_deg": asset.skyline_residual_deg,
        "panorama_sky_with_mesh_hit_fraction": asset.sky_with_mesh_hit_fraction,
        "panorama_registration_verdict": asset.registration_verdict,
        "panorama_captured_at": asset.captured_at,
        "panorama_support_overlay_collection": support_overlay.name,
        "panorama_support_overlay_objects": support_overlay_objects,
        "panorama_support_overlay_scale_about_camera": SUPPORT_OVERLAY_SCALE,
        "panorama_support_overlay_opacity": SUPPORT_OVERLAY_OPACITY,
        "panorama_support_holdout_view_layers_json": json.dumps(support_holdout_layers),
        "panorama_support_holdout_view_layer_count": len(support_holdout_layers),
        "panorama_support_overlay_offset_rule": (
            "display offset toward the panorama camera equals "
            f"(1 - {SUPPORT_OVERLAY_SCALE}) times camera range. Angular projection is unchanged"
        ),
        "panorama_support_overlay_limit": (
            "The source photograph has no compositor depth. Foreground people, bicycles and the camera rig can "
            "therefore appear under the translucent support surface that lies behind them."
        ),
        "panorama_layers_excluded": "semantic fishnets, hero visual rays, and hero NEE rays",
        "panorama_layers_excluded_reason": (
            "Their camera or trace origin differs from this photograph. They remain in their own prepared scenes."
        ),
        "panorama_compositor_render_layer_node": overlay.name,
        "panorama_compositor_view_layer": compositor_layer,
        "panorama_overlay_note": (
            "The camera uses the same spherical projection model as the source panorama. The skyline residual and "
            "pose uncertainty record the remaining image-to-support-mesh disagreement. The one orange marker is "
            "the recorded position of the nearest other registered panorama. Production ray coordinates are unchanged."
        ),
    }
    properties.update(acquisition_properties)
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
    "ACQUISITION_COLLECTION_NAME",
    "KORENMARKT_HERO_CAPTURE",
    "PANORAMA_DISPLAY_CLIP_START_M",
    "RECTILINEAR_FOV_DEG",
    "RECTILINEAR_PLANE_DISTANCE_M",
    "SUPPORT_OVERLAY_OPACITY",
    "SUPPORT_OVERLAY_SCALE",
    "PanoramaAsset",
    "camera_matrix",
    "configure_panorama_scene",
    "select_panorama_asset",
    "select_panorama_assets",
]
