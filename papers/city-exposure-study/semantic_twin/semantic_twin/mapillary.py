"""Small, bounded Mapillary acquisition helper for multi-view observations.

The module fetches metadata only. Image downloads remain an explicit later
decision after candidates have been ranked for baseline, direction, date and
quality. It is intentionally source-specific at the boundary and feeds the
generic observation ledger downstream.

Its one piece of real geometry is :func:`orientation_from_computed_rotation`.
Mapillary's structure from motion already solves for gravity and publishes the
answer in ``computed_rotation``, so a Mapillary panorama arrives with a measured
tilt and roll rather than an assumed level camera. The three panoramas selected
at Korenmarkt tilt by 4.52, 7.75 and 26.82 degrees off gravity.
"""

from __future__ import annotations

import json
import math
import os
import pathlib
import urllib.parse
import urllib.request
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from io import BytesIO
from typing import Any

import numpy as np
from PIL import Image

from .geo import EnuFrame
from .pano_geometry import panorama_to_world_matrix
from .panorama import PanoramaPose, load_support_mesh
from .scene import load_scene
from .support_mesh import camera_altitude

GRAPH = "https://graph.mapillary.com/images"
FIELDS = (
    "id,computed_geometry,computed_compass_angle,captured_at,is_pano,thumb_2048_url,thumb_original_url,"
    "camera_type,quality_score,width,height,camera_parameters,computed_rotation"
)


@dataclass(frozen=True)
class MapillaryCandidate:
    image_id: str
    latitude: float
    longitude: float
    range_m: float
    off_axis_deg: float
    quality: float
    captured_at: int | None
    is_pano: bool
    width: int | None
    height: int | None
    metadata: dict[str, Any]


def token() -> str:
    value = os.environ.get("MAPILLARY_TOKEN")
    if value:
        return value
    env_file = pathlib.Path("/home/user/aegis/.env")
    for line in env_file.read_text().splitlines() if env_file.exists() else []:
        if line.startswith("MAPILLARY_TOKEN="):
            return line.split("=", 1)[1].strip()
    raise SystemExit("MAPILLARY_TOKEN is not configured")


def fetch_images(
    access_token: str, bbox: tuple[float, float, float, float], *, limit: int = 100
) -> list[dict[str, Any]]:
    """Fetch one small metadata cell, respecting Mapillary's bbox constraint."""
    west, south, east, north = bbox
    if not west < east or not south < north or east - west >= 0.01 or north - south >= 0.01:
        raise ValueError("bbox must be ordered and smaller than 0.01 degrees in each dimension")
    if not 1 <= limit <= 100:
        raise ValueError("limit must lie in [1, 100]")
    query = urllib.parse.urlencode(
        {
            "access_token": access_token,
            "fields": FIELDS,
            "bbox": ",".join(f"{value:.6f}" for value in bbox),
            "limit": str(limit),
        }
    )
    with urllib.request.urlopen(f"{GRAPH}?{query}", timeout=60) as response:
        return json.loads(response.read())["data"]


def rank_for_target(
    images: list[dict[str, Any]],
    frame: EnuFrame,
    *,
    target_lat: float,
    target_lon: float,
    min_range_m: float = 4.0,
    max_range_m: float = 120.0,
    max_off_axis_deg: float = 50.0,
) -> list[MapillaryCandidate]:
    """Rank images that genuinely face a target, rather than merely being nearby."""
    target_xy = frame.to_enu(target_lat, target_lon)[:2]
    result: list[MapillaryCandidate] = []
    for image in images:
        geometry = image.get("computed_geometry", {})
        coordinates = geometry.get("coordinates")
        heading = image.get("computed_compass_angle")
        if coordinates is None or heading is None or len(coordinates) != 2:
            continue
        longitude, latitude = map(float, coordinates)
        image_xy = frame.to_enu(latitude, longitude)[:2]
        target_vector = target_xy - image_xy
        range_m = float(np.linalg.norm(target_vector))
        if not min_range_m <= range_m <= max_range_m:
            continue
        direction = target_vector / range_m
        radians = math.radians(float(heading))
        look = np.array((math.sin(radians), math.cos(radians)))
        off_axis = math.degrees(math.acos(float(np.clip(look @ direction, -1.0, 1.0))))
        is_pano = bool(image.get("is_pano"))
        if not is_pano and off_axis > max_off_axis_deg:
            continue
        quality = float(image.get("quality_score") or 0.0)
        # Panoramas can point anywhere but pay a resolution penalty at a target.
        score = (
            quality
            * math.exp(-0.5 * (min(off_axis, 90.0) / 25.0) ** 2)
            * math.exp(-0.5 * ((range_m - 28.0) / 38.0) ** 2)
        )
        if is_pano:
            score *= 0.45
        result.append(
            MapillaryCandidate(
                image_id=str(image["id"]),
                latitude=latitude,
                longitude=longitude,
                range_m=range_m,
                off_axis_deg=off_axis,
                quality=quality,
                captured_at=int(image["captured_at"]) if image.get("captured_at") else None,
                is_pano=is_pano,
                width=int(image["width"]) if image.get("width") else None,
                height=int(image["height"]) if image.get("height") else None,
                metadata={**image, "selection_score": score},
            )
        )
    return sorted(result, key=lambda candidate: candidate.metadata["selection_score"], reverse=True)


def diversify(
    candidates: list[MapillaryCandidate], frame: EnuFrame, *, count: int, separation_m: float = 6.0
) -> list[MapillaryCandidate]:
    """Keep distinct camera centres rather than adjacent frames from one drive."""
    chosen: list[MapillaryCandidate] = []
    for candidate in candidates:
        point = frame.to_enu(candidate.latitude, candidate.longitude)[:2]
        if any(
            np.linalg.norm(point - frame.to_enu(item.latitude, item.longitude)[:2]) < separation_m for item in chosen
        ):
            continue
        chosen.append(candidate)
        if len(chosen) == count:
            break
    return chosen


def rodrigues(rotation_vector: Sequence[float]) -> np.ndarray:
    """Rotation matrix from an axis-angle vector, as OpenSfM stores it."""
    vector = np.asarray(rotation_vector, dtype=float)
    if vector.shape != (3,):
        raise ValueError("a rotation vector has exactly three components")
    angle = float(np.linalg.norm(vector))
    if angle < 1e-12:
        return np.eye(3)
    axis = vector / angle
    cross = np.array(
        [
            [0.0, -axis[2], axis[1]],
            [axis[2], 0.0, -axis[0]],
            [-axis[1], axis[0], 0.0],
        ]
    )
    return np.eye(3) + math.sin(angle) * cross + (1.0 - math.cos(angle)) * (cross @ cross)


def orientation_from_computed_rotation(rotation_vector: Sequence[float]) -> tuple[float, float, float]:
    """Heading, tilt and roll in degrees from Mapillary's ``computed_rotation``.

    ``computed_rotation`` is the OpenSfM world-to-camera axis-angle vector in the
    reconstruction's topocentric east-north-up frame, and for a spherical camera
    the image centre column is the optical axis with x right and y down. Those
    three world-frame axes are exactly the panorama-local right, forward and up
    that ``pano_geometry.panorama_to_world_matrix`` composes, so the decomposition
    is a rearrangement rather than a convention guess.

    The returned heading is the azimuth of the *levelled* panorama frame. It is
    not ``computed_compass_angle``, which is the azimuth of the tilted optical
    axis, and the two separate by more than a degree once the camera is tilted
    far off gravity.
    """
    rotation = rodrigues(rotation_vector)
    world = np.column_stack([rotation[0, :], rotation[2, :], -rotation[1, :]])
    roll_deg = math.degrees(math.atan2(-world[2, 0], math.hypot(world[2, 1], world[2, 2])))
    pitch_deg = math.degrees(math.atan2(world[2, 1], world[2, 2]))
    levelled = world @ panorama_to_world_matrix(0.0, pitch_deg=pitch_deg, roll_deg=roll_deg).T
    heading_deg = math.degrees(math.atan2(levelled[0, 1], levelled[0, 0])) % 360.0
    return heading_deg, 90.0 + pitch_deg, roll_deg


def pose_from_metadata(
    metadata: dict[str, Any],
    scene: dict[str, Any],
    *,
    support_mesh: tuple[np.ndarray, np.ndarray] | None = None,
) -> PanoramaPose:
    """Initial pose for a Mapillary spherical panorama, orientation included.

    Mapillary's structure from motion already solves for gravity, and the answer
    is in ``computed_rotation``. Discarding it and assuming a level camera is not
    conservative: the three Korenmarkt panoramas carry gravity tilts of 4.5, 7.8
    and 26.8 degrees, and the last of those is four times the pitch range the
    skyline refinement is allowed to search. Only a panorama with no
    ``computed_rotation`` at all gets the level assumption, and it is labelled.
    """
    longitude, latitude = map(float, metadata["computed_geometry"]["coordinates"])
    origin = scene["enu_origin"]
    frame = EnuFrame(float(origin["lat"]), float(origin["lon"]), float(origin.get("ellipsoid_height_m", 0.0)))
    camera_height = float(scene.get("camera_height_m", 2.5))
    easting, northing = frame.to_enu(latitude, longitude)[:2]
    altitude, altitude_provenance = camera_altitude(scene, float(easting), float(northing), support_mesh=support_mesh)

    rotation_vector = metadata.get("computed_rotation")
    if rotation_vector is None:
        heading_deg = float(metadata.get("computed_compass_angle") or 0.0)
        tilt_deg, roll_deg = 90.0, 0.0
        orientation_source = "absent: no computed_rotation, camera assumed level"
    else:
        heading_deg, tilt_deg, roll_deg = orientation_from_computed_rotation(rotation_vector)
        orientation_source = "mapillary computed_rotation, structure from motion gravity"
    return PanoramaPose(
        position_enu_m=(float(easting), float(northing), float(altitude)),
        position_wgs84=(latitude, longitude),
        heading_deg=heading_deg,
        tilt_deg=tilt_deg,
        roll_deg=roll_deg,
        camera_height_m=camera_height,
        altitude_source=str(altitude_provenance["altitude_source"]),
        orientation_source=orientation_source,
        provenance=altitude_provenance,
    )


def download_panorama_image(metadata: dict[str, Any], destination: pathlib.Path) -> tuple[pathlib.Path, str]:
    """Download the best provider-issued panorama image with validation.

    Original imagery is preferred when the Graph API explicitly supplies it.
    The 2048 px rendition remains a deliberate fallback, rather than silently
    pretending to be the declared original resolution.
    """
    source_field = "thumb_original_url" if metadata.get("thumb_original_url") else "thumb_2048_url"
    url = metadata.get(source_field)
    if not url:
        raise ValueError("Mapillary metadata has neither thumb_original_url nor thumb_2048_url")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(str(url), timeout=90) as response:
        payload = response.read()
    with Image.open(BytesIO(payload)) as image:
        image.verify()
    destination.write_bytes(payload)
    return destination, source_field


def persist_selected_panorama(
    metadata: dict[str, Any], scene_path: pathlib.Path, out_dir: pathlib.Path
) -> pathlib.Path:
    """Persist one selected spherical Mapillary observation and its full provenance."""
    if not metadata.get("is_pano"):
        raise ValueError("selected Mapillary image is not spherical")
    scene = load_scene(scene_path)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "metadata.json").write_text(json.dumps(metadata, indent=2))
    pose = pose_from_metadata(metadata, scene, support_mesh=load_support_mesh(scene))
    (out_dir / "pose_initial.json").write_text(json.dumps(asdict(pose), indent=2))
    image_name = "panorama_original.jpg" if metadata.get("thumb_original_url") else "panorama_thumb_2048.jpg"
    destination, source_field = download_panorama_image(metadata, out_dir / image_name)
    (out_dir / "provenance.json").write_text(
        json.dumps(
            {
                "provider": "Mapillary",
                "image_id": str(metadata["id"]),
                "image_type": "spherical panorama",
                "acquisition": "selected through a bounded Mapillary Graph API metadata query",
                "image": destination.name,
                "image_source_field": source_field,
                "declared_original_dimensions": [metadata.get("width"), metadata.get("height")],
                "note": "Mapillary camera pose is an initial prior and requires image-to-mesh refinement.",
            },
            indent=2,
        )
    )
    return destination
