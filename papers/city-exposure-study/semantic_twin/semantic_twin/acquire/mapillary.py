"""Mapillary imagery, reached by sequence and never by bounding box.

Mapillary is the provider behind the twelve station Korenmarkt walk, which is
the only multi station set in the study and the one carrying the SAM 3 material
binding. Every other site is Google Street View. See
:mod:`semantic_twin.acquire.source` for why that choice matters.

## The bounding box endpoint returns a sample and does not say so

This is the reason the module is shaped the way it is, and it is the failure
most likely to quietly corrupt somebody else's panorama study. Anyone selecting
street level imagery for a site does the obvious thing and queries a bounding
box. The box does not return what is in the box.

Measured at Korenmarkt. One ``GET /images`` with a ``bbox`` covering roughly
200 m around 51.055 N, 3.722 E and ``limit=100`` returned 43 images, of which 2
belonged to sequence ``u5WIQvkTXO7SbeL1l8UN6a``. Enumerating that same sequence
through ``GET /image_ids`` returns 135 frames, 13 of them within 60 m of the
site centre. The box returned 2 of 13 and reported no truncation.

What makes it dangerous is that nothing in the reply distinguishes a complete
answer from a sample. There is no truncation flag, no paging cursor and no total
count. It is not the documented ``limit``, since the query was capped at 100 and
returned 43. It is not a geometry error, since the 11 missing frames are inside
the box by their own published ``computed_geometry``. And the loss is
spatially structured rather than random: thinning a dense drive removes the
tightly spaced frames first, which are exactly the short baselines a multi view
study needs, so a naive study loses them and never learns that it did.

## What this module does about it

The box is allowed to *name* sequences and nothing else.
:func:`seed_sequence_ids` is the only function here that sends a ``bbox``, it
asks for the three seed fields alone, and it returns identifiers rather than
image records. Image records come from :func:`images_by_id` or
:func:`traverse`, both of which address images explicitly, and the identifier
endpoints have been complete in every case checked here.

:func:`_graph` refuses a ``bbox`` query that asks for more than
:data:`SEED_FIELDS`, so the sampled route cannot be widened back into a
selection route by adding a field. That guard is the structural half of the fix.
The docstring above is the half that explains it.
"""

from __future__ import annotations

import json
import math
import os
import pathlib
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Iterable, Sequence
from dataclasses import asdict, dataclass
from io import BytesIO
from typing import Any

import numpy as np
from PIL import Image

from .. import sites
from ..pano_geometry import panorama_to_world_matrix
from ..scene.camera_ground import camera_altitude
from ..scene.enu import EnuFrame
from .source import PanoramaPose, load_support_mesh

GRAPH = "https://graph.mapillary.com"

#: Everything a bbox query is allowed to ask for. Enough to name a sequence and
#: to tell a spherical capture from a flat one, and not enough to select a walk.
SEED_FIELDS = "id,sequence,is_pano"

#: The full record, fetched only by explicit identifier.
IMAGE_FIELDS = (
    "id,computed_geometry,computed_compass_angle,captured_at,is_pano,thumb_2048_url,thumb_original_url,"
    "camera_type,quality_score,width,height,camera_parameters,computed_rotation,sequence"
)

#: Mapillary returns at most this many identifiers per images request.
ID_BATCH = 50

#: The Graph API refuses a bbox wider than this in either dimension.
MAX_BBOX_DEGREES = 0.01


class SampledEndpointError(ValueError):
    """Raised when a caller asks the bounding box endpoint to select imagery.

    Separate from a plain ``ValueError`` because it is not a typo. It is a
    caller reaching for the endpoint that the measurement at the top of this
    module says returns 2 frames of 13, and the fix is a different endpoint
    rather than a different argument.
    """


@dataclass(frozen=True)
class SequenceSeeds:
    """What a box sweep is allowed to hand back: names, and how many it looked at.

    The two counts are not comparable and the pair is kept together so nobody
    quotes one as the other. ``seed_images`` is what the sampled endpoint chose
    to show. ``sequence_ids`` is what those samples name, and expanding those
    names at Korenmarkt turns 112 seeds into 1,359 linked images.
    """

    sequence_ids: frozenset[str]
    seed_images: int


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


def _request(url: str, *, timeout: float, attempts: int = 4) -> dict[str, Any]:
    """One Graph API call, retried on transient failure and never on a bad query.

    A rate limit or a truncated read is worth waiting out. A malformed request
    is not, and retrying it would turn one clear error into four slow ones.
    """
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(url, timeout=timeout) as response:
                return json.loads(response.read())
        except urllib.error.HTTPError as error:
            if error.code in (400, 401, 403, 404) or attempt == attempts - 1:
                raise
            time.sleep(2.0 * (attempt + 1))
        except Exception:
            if attempt == attempts - 1:
                raise
            time.sleep(2.0 * (attempt + 1))
    raise RuntimeError("unreachable")


def _graph(path: str, access_token: str, *, timeout: float = 60.0, **params: Any) -> dict[str, Any]:
    """The one door to the Graph API, with the sampling guard on it.

    A ``bbox`` query may ask for :data:`SEED_FIELDS` and nothing else. Widening
    the field list is how a seed sweep becomes a selection, and a selection off
    this endpoint is a sample of the imagery presented as all of it.
    """
    if "bbox" in params and params.get("fields") != SEED_FIELDS:
        raise SampledEndpointError(
            "the bbox endpoint returns a silent sample of the imagery in the box, measured at 2 frames of 13 "
            f"at Korenmarkt, so it may only ask for {SEED_FIELDS!r} and name sequences. Expand those names with "
            "sequence_image_ids and fetch records with images_by_id."
        )
    params["access_token"] = access_token
    return _request(f"{GRAPH}/{path}?" + urllib.parse.urlencode(params), timeout=timeout)


def seed_sequence_ids(
    access_token: str,
    *,
    latitude: float,
    longitude: float,
    half_width_m: float = 150.0,
    cells: int = 6,
    panoramas_only: bool = True,
    timeout: float = 60.0,
) -> SequenceSeeds:
    """Sequence identifiers touching a box around the site. Names only.

    The box is tiled because a single Graph bbox query is both capped at 100
    results and constrained to under 0.01 degrees a side. Tiling raises the cap
    but does not repair the sampling, which is why the seeds are used only to
    name sequences and never to select the walk. Tiling Korenmarkt into 36 cells
    raised the count from 43 to 112 panorama seeds and still did not recover
    full sequence membership.
    """
    if cells < 1:
        raise ValueError("cells must be at least one")
    metres_per_degree = 111320.0
    step_lat = 2.0 * half_width_m / (cells * metres_per_degree)
    step_lon = step_lat / max(math.cos(math.radians(latitude)), 1e-6)
    if step_lat >= MAX_BBOX_DEGREES or step_lon >= MAX_BBOX_DEGREES:
        raise ValueError(f"cell is wider than the Graph API's {MAX_BBOX_DEGREES} degree bbox limit, raise cells")

    sequence_ids: set[str] = set()
    seeds = 0
    for row in range(cells):
        for column in range(cells):
            west = longitude + (column - cells / 2.0) * step_lon
            south = latitude + (row - cells / 2.0) * step_lat
            bbox = (west, south, west + step_lon, south + step_lat)
            payload = _graph(
                "images",
                access_token,
                timeout=timeout,
                bbox=",".join(f"{value:.6f}" for value in bbox),
                fields=SEED_FIELDS,
                limit=100,
            )
            for image in payload.get("data", []):
                if panoramas_only and not image.get("is_pano"):
                    continue
                seeds += 1
                if image.get("sequence"):
                    sequence_ids.add(str(image["sequence"]))
    return SequenceSeeds(frozenset(sequence_ids), seeds)


def sequence_image_ids(access_token: str, sequence_id: str, *, timeout: float = 60.0) -> list[str]:
    """Every image identifier of one sequence, in capture order.

    This is the endpoint the bbox sweep exists to reach. A sequence is the
    ordered frames of one continuous drive or ride, the only officially linked
    structure the provider exposes, and it is complete.
    """
    payload = _graph("image_ids", access_token, timeout=timeout, sequence_id=sequence_id)
    return [str(item["id"]) for item in payload.get("data", [])]


def images_by_id(
    access_token: str,
    image_ids: Sequence[str],
    *,
    fields: str = IMAGE_FIELDS,
    timeout: float = 60.0,
) -> list[dict[str, Any]]:
    """Full records for an explicit identifier list, batched to the API's limit."""
    result: list[dict[str, Any]] = []
    for start in range(0, len(image_ids), ID_BATCH):
        batch = image_ids[start : start + ID_BATCH]
        payload = _graph("images", access_token, timeout=timeout, image_ids=",".join(batch), fields=fields)
        result.extend(payload.get("data", []))
    return result


def traverse(
    access_token: str,
    sequence_ids: Iterable[str],
    *,
    fields: str = IMAGE_FIELDS,
    timeout: float = 60.0,
    progress: bool = False,
) -> dict[str, dict[str, Any]]:
    """Expand every named sequence to its full linked membership."""
    images: dict[str, dict[str, Any]] = {}
    ordered = sorted(set(sequence_ids))
    for index, sequence_id in enumerate(ordered, start=1):
        identifiers = sequence_image_ids(access_token, sequence_id, timeout=timeout)
        pending = [identifier for identifier in identifiers if identifier not in images]
        for image in images_by_id(access_token, pending, fields=fields, timeout=timeout):
            images[str(image["id"])] = image
        if progress:
            print(
                f"[mapillary] sequence {index}/{len(ordered)} {sequence_id} n={len(identifiers)} total={len(images)}",
                flush=True,
            )
    return images


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
    """Rank images that genuinely face a target, rather than merely being nearby.

    Takes records, so it can only be reached from :func:`images_by_id` or
    :func:`traverse`. That is deliberate: ranking a bbox reply would be ranking
    a sample, and the ranking would look exactly as convincing.
    """
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


def mapillary_orientation_source(metadata: dict[str, Any]) -> str:
    """Whether this panorama carries a solved gravity or has to be assumed level."""
    if metadata.get("computed_rotation") is None:
        return "absent: no computed_rotation, camera assumed level"
    return "mapillary computed_rotation, structure from motion gravity"


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
    else:
        heading_deg, tilt_deg, roll_deg = orientation_from_computed_rotation(rotation_vector)
    return PanoramaPose(
        position_enu_m=(float(easting), float(northing), float(altitude)),
        position_wgs84=(latitude, longitude),
        heading_deg=heading_deg,
        tilt_deg=tilt_deg,
        roll_deg=roll_deg,
        camera_height_m=camera_height,
        altitude_source=str(altitude_provenance["altitude_source"]),
        orientation_source=mapillary_orientation_source(metadata),
        provenance=altitude_provenance,
    )


class Mapillary:
    """The Mapillary arm of :class:`~semantic_twin.acquire.source.PanoramaSource`."""

    provider = sites.MAPILLARY

    def image_id(self, metadata: dict[str, Any]) -> str:
        return str(metadata["id"])

    def orientation_source(self, metadata: dict[str, Any]) -> str:
        return mapillary_orientation_source(metadata)

    def pose(
        self,
        metadata: dict[str, Any],
        scene: dict[str, Any],
        *,
        support_mesh: tuple[np.ndarray, np.ndarray] | None = None,
    ) -> PanoramaPose:
        return pose_from_metadata(metadata, scene, support_mesh=support_mesh)


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
    from ..scene.site_config import load_scene

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
                "acquisition": "named by a bounded seed sweep, then fetched by explicit image identifier",
                "image": destination.name,
                "image_source_field": source_field,
                "declared_original_dimensions": [metadata.get("width"), metadata.get("height")],
                "note": "Mapillary camera pose is an initial prior and requires image-to-mesh refinement.",
            },
            indent=2,
        )
    )
    return destination
