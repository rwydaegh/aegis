"""Walks of linked panoramas, and what makes two of them independent.

A site is not one capture. Mapillary publishes its imagery as *sequences*, the
ordered frames of a single continuous drive or ride, and the sequence is the
only officially linked structure the provider exposes. Traversing it is
therefore how a walk is assembled: pick any image near the site, ask which
sequence it belongs to, and enumerate that sequence in full.

That traversal is not a convenience. The bounding-box endpoint is sampled and
silently incomplete. A ``bbox`` query over a 200 m box at Korenmarkt returns two
frames of sequence ``u5WIQvkTXO7SbeL1l8UN6a``, while enumerating that same
sequence by identifier returns thirteen within 60 m of the site centre. Selecting
a walk from the box alone would have thrown away eleven of them without saying
so.

The second half of this module is about not fooling yourself with the result.
Fusing many panoramas raises every coverage number by construction, because a
union can only grow. The question that decides whether the growth means anything
is how much of it is genuinely new evidence, and two panoramas 3 m apart looking
at a facade 40 m away are very nearly one panorama. :func:`parallax_independence`
turns that into the per-observation weight the evidence accumulator already
accepts and nothing has ever supplied.
"""

from __future__ import annotations

import json
import math
import time
import urllib.parse
import urllib.request
from collections.abc import Iterable, Sequence
from dataclasses import asdict, dataclass, field
from typing import Any

import numpy as np

from .geo import EnuFrame

GRAPH = "https://graph.mapillary.com"
WALK_FIELDS = (
    "id,computed_geometry,computed_compass_angle,captured_at,is_pano,thumb_2048_url,thumb_original_url,"
    "camera_type,quality_score,width,height,camera_parameters,computed_rotation,sequence"
)
# Mapillary returns at most this many identifiers per images request.
_ID_BATCH = 50


@dataclass(frozen=True)
class WalkStation:
    """One panorama of a walk, placed in the scene's local ENU frame."""

    image_id: str
    sequence_id: str
    latitude: float
    longitude: float
    easting_m: float
    northing_m: float
    range_m: float
    captured_at: int | None
    quality: float
    width: int | None
    height: int | None
    has_computed_rotation: bool
    metadata: dict[str, Any] = field(repr=False)

    @property
    def position_xy(self) -> np.ndarray:
        return np.array([self.easting_m, self.northing_m], dtype=float)

    def summary(self) -> dict[str, Any]:
        record = asdict(self)
        record.pop("metadata")
        return record


def _request(url: str, *, timeout: float, attempts: int = 4) -> dict[str, Any]:
    """One Graph API call, retried on transient failure and never on a bad query.

    A rate limit or a truncated read is worth waiting out. A malformed request is
    not, and retrying it would turn one clear error into four slow ones.
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


def _get(path: str, access_token: str, *, timeout: float = 60.0, **params: Any) -> dict[str, Any]:
    params["access_token"] = access_token
    return _request(f"{GRAPH}/{path}?" + urllib.parse.urlencode(params), timeout=timeout)


def sequence_image_ids(access_token: str, sequence_id: str, *, timeout: float = 60.0) -> list[str]:
    """Every image identifier of one sequence, in capture order."""
    payload = _get("image_ids", access_token, timeout=timeout, sequence_id=sequence_id)
    return [str(item["id"]) for item in payload.get("data", [])]


def fetch_by_ids(
    access_token: str,
    image_ids: Sequence[str],
    *,
    fields: str = WALK_FIELDS,
    timeout: float = 60.0,
) -> list[dict[str, Any]]:
    """Metadata for an explicit identifier list, batched to the API's limit."""
    result: list[dict[str, Any]] = []
    for start in range(0, len(image_ids), _ID_BATCH):
        batch = image_ids[start : start + _ID_BATCH]
        payload = _get("images", access_token, timeout=timeout, image_ids=",".join(batch), fields=fields)
        result.extend(payload.get("data", []))
    return result


def seed_sequences(
    access_token: str,
    *,
    latitude: float,
    longitude: float,
    half_width_m: float = 150.0,
    cells: int = 6,
    panoramas_only: bool = True,
    timeout: float = 60.0,
) -> tuple[set[str], int]:
    """Sequence identifiers touching a box around the site, and the seed count.

    The box is tiled because a single Graph bbox query is both capped at 100
    results and constrained to under 0.01 degrees a side. Tiling raises the cap
    but does not repair the sampling, which is precisely why the seeds are used
    only to *name* sequences and never to select the walk.
    """
    if cells < 1:
        raise ValueError("cells must be at least one")
    metres_per_degree = 111320.0
    step_lat = 2.0 * half_width_m / (cells * metres_per_degree)
    step_lon = step_lat / max(math.cos(math.radians(latitude)), 1e-6)
    if step_lat >= 0.01 or step_lon >= 0.01:
        raise ValueError("cell is wider than the Graph API's 0.01 degree bbox limit, raise cells")
    sequences: set[str] = set()
    seeds = 0
    for row in range(cells):
        for column in range(cells):
            west = longitude + (column - cells / 2.0) * step_lon
            south = latitude + (row - cells / 2.0) * step_lat
            bbox = (west, south, west + step_lon, south + step_lat)
            payload = _get(
                "images",
                access_token,
                timeout=timeout,
                bbox=",".join(f"{value:.6f}" for value in bbox),
                fields="id,sequence,is_pano",
                limit=100,
            )
            for image in payload.get("data", []):
                if panoramas_only and not image.get("is_pano"):
                    continue
                seeds += 1
                if image.get("sequence"):
                    sequences.add(str(image["sequence"]))
    return sequences, seeds


def traverse(
    access_token: str,
    sequence_ids: Iterable[str],
    *,
    fields: str = WALK_FIELDS,
    timeout: float = 60.0,
    progress: bool = False,
) -> dict[str, dict[str, Any]]:
    """Expand every named sequence to its full linked membership."""
    images: dict[str, dict[str, Any]] = {}
    ordered = sorted(set(sequence_ids))
    for index, sequence_id in enumerate(ordered, start=1):
        identifiers = sequence_image_ids(access_token, sequence_id, timeout=timeout)
        pending = [identifier for identifier in identifiers if identifier not in images]
        for image in fetch_by_ids(access_token, pending, fields=fields, timeout=timeout):
            images[str(image["id"])] = image
        if progress:
            print(
                f"[walk] sequence {index}/{len(ordered)} {sequence_id} n={len(identifiers)} total={len(images)}",
                flush=True,
            )
    return images


def stations_from_images(
    images: Iterable[dict[str, Any]],
    frame: EnuFrame,
    *,
    target_lat: float,
    target_lon: float,
    radius_m: float = 60.0,
    require_rotation: bool = True,
) -> list[WalkStation]:
    """Spherical captures inside the site radius, placed in the ENU frame.

    ``require_rotation`` keeps the measured gravity tilt mandatory. A panorama
    with no ``computed_rotation`` would have to be assumed level, and at this
    site the measured tilts reach 27 degrees, so admitting one silently would put
    an unregistrable pose into a walk that reports a covariance for every member.
    """
    target = frame.to_enu(target_lat, target_lon)[:2]
    stations: list[WalkStation] = []
    for image in images:
        if not image.get("is_pano"):
            continue
        coordinates = image.get("computed_geometry", {}).get("coordinates")
        if coordinates is None or len(coordinates) != 2:
            continue
        has_rotation = image.get("computed_rotation") is not None
        if require_rotation and not has_rotation:
            continue
        longitude, latitude = map(float, coordinates)
        easting, northing = frame.to_enu(latitude, longitude)[:2] - target
        range_m = float(math.hypot(easting, northing))
        if range_m > radius_m:
            continue
        stations.append(
            WalkStation(
                image_id=str(image["id"]),
                sequence_id=str(image.get("sequence", "")),
                latitude=latitude,
                longitude=longitude,
                easting_m=float(easting),
                northing_m=float(northing),
                range_m=range_m,
                captured_at=int(image["captured_at"]) if image.get("captured_at") else None,
                quality=float(image.get("quality_score") or 0.0),
                width=int(image["width"]) if image.get("width") else None,
                height=int(image["height"]) if image.get("height") else None,
                has_computed_rotation=has_rotation,
                metadata=dict(image),
            )
        )
    return stations


def select_walk(
    stations: Sequence[WalkStation],
    *,
    count: int = 12,
    separation_m: float = 8.0,
    per_sequence_cap: int | None = None,
) -> list[WalkStation]:
    """Choose the walk: nearest first, thinned by separation, capped per capture.

    Nearest-first is the right greedy order because the quantity being bought is
    directly observed facade, and a panorama at 5 m resolves a facade the same
    panorama at 55 m cannot. The separation floor removes frames that would be
    near-duplicates. ``per_sequence_cap`` exists so a single dense drive cannot
    fill the whole walk and leave the fusion with no independent capture to
    cross-validate against.
    """
    if count < 1:
        raise ValueError("count must be at least one")
    if separation_m < 0.0:
        raise ValueError("separation_m cannot be negative")
    ordered = sorted(stations, key=lambda station: (station.range_m, station.image_id))
    chosen: list[WalkStation] = []
    per_sequence: dict[str, int] = {}
    for station in ordered:
        if per_sequence_cap is not None and per_sequence.get(station.sequence_id, 0) >= per_sequence_cap:
            continue
        if any(float(np.linalg.norm(station.position_xy - other.position_xy)) < separation_m for other in chosen):
            continue
        chosen.append(station)
        per_sequence[station.sequence_id] = per_sequence.get(station.sequence_id, 0) + 1
        if len(chosen) == count:
            break
    return chosen


def pairwise_baselines(stations: Sequence[WalkStation]) -> np.ndarray:
    """Horizontal camera-to-camera distances, in metres."""
    points = np.array([station.position_xy for station in stations], dtype=float)
    if not len(points):
        return np.zeros((0, 0))
    difference = points[:, None, :] - points[None, :, :]
    return np.sqrt(np.einsum("ijk,ijk->ij", difference, difference))


def spread(stations: Sequence[WalkStation]) -> dict[str, Any]:
    """What the walk actually covers: extent, baselines, dates, sequences."""
    if not stations:
        return {"n_stations": 0}
    points = np.array([station.position_xy for station in stations], dtype=float)
    baselines = pairwise_baselines(stations)
    upper = baselines[np.triu_indices(len(stations), k=1)]
    nearest = np.min(baselines + np.eye(len(stations)) * 1e9, axis=1) if len(stations) > 1 else np.zeros(1)
    sequences = sorted({station.sequence_id for station in stations})
    days = sorted(
        {
            time.strftime("%Y-%m-%d", time.gmtime(station.captured_at / 1000.0))
            for station in stations
            if station.captured_at
        }
    )
    report = {
        "n_stations": len(stations),
        "n_sequences": len(sequences),
        "sequence_ids": sequences,
        "capture_days": days,
        "extent_east_m": float(points[:, 0].max() - points[:, 0].min()),
        "extent_north_m": float(points[:, 1].max() - points[:, 1].min()),
        "range_from_centre_m": {
            "min": float(min(station.range_m for station in stations)),
            "median": float(np.median([station.range_m for station in stations])),
            "max": float(max(station.range_m for station in stations)),
        },
        "baseline_m": {
            "min": float(upper.min()) if upper.size else 0.0,
            "median": float(np.median(upper)) if upper.size else 0.0,
            "max": float(upper.max()) if upper.size else 0.0,
        },
        "nearest_neighbour_m": {
            "min": float(nearest.min()),
            "median": float(np.median(nearest)),
        },
    }
    if len(stations) > 2:
        try:
            from scipy.spatial import ConvexHull

            report["convex_hull_area_m2"] = float(ConvexHull(points).volume)
        except Exception:
            report["convex_hull_area_m2"] = None
    return report


def parallax_angles_deg(stations: Sequence[WalkStation], surface_xy: np.ndarray) -> np.ndarray:
    """Angle subtended at each surface point by each pair of cameras, in degrees.

    Returns ``[surfaces, stations, stations]``. Parallax rather than baseline is
    the right axis because it is what actually decorrelates two observations: the
    two cameras see a different specular lobe, a different set of occluders and a
    different foreshortening only in so far as their directions to the surface
    differ. A 3 m baseline is a large parallax on a shopfront 4 m away and almost
    none on a gable 60 m away, and one number cannot describe both.
    """
    surface = np.atleast_2d(np.asarray(surface_xy, dtype=float))
    if surface.ndim != 2 or surface.shape[1] != 2:
        raise ValueError("surface_xy must have shape [surfaces, 2]")
    cameras = np.array([station.position_xy for station in stations], dtype=float)
    delta = cameras[None, :, :] - surface[:, None, :]
    norm = np.linalg.norm(delta, axis=2, keepdims=True)
    unit = np.divide(delta, norm, out=np.zeros_like(delta), where=norm > 1e-9)
    cosine = np.clip(np.einsum("sab,scb->sac", unit, unit), -1.0, 1.0)
    return np.degrees(np.arccos(cosine))


def parallax_independence(
    parallax_deg: np.ndarray,
    visible: np.ndarray,
    *,
    decorrelation_deg: float = 10.0,
) -> np.ndarray:
    """Per-station independence weights for one surface, from an effective count.

    The construction is the Kish effective sample size. Stations that both see a
    surface are correlated by a kernel in their parallax angle, and each station's
    weight is the reciprocal of the total correlation it carries::

        w_a = 1 / sum_b K(theta_ab)   over stations b that also see the surface

    Two co-located cameras get 1/2 each and contribute one observation between
    them, which is the correct answer and is what a naive union silently gets
    wrong. Two cameras far enough apart get 1 each. The weights sum to the
    effective number of independent looks, which is bounded above by the raw
    count and below by one, so this can never invent evidence.

    ``decorrelation_deg`` is the parallax at which the kernel falls to 1/e. Ten
    degrees is deliberately conservative: it is roughly the angular width over
    which a rough facade's scattering lobe and its occluder set change, and it
    makes the reported gain an underestimate rather than an overestimate.
    """
    parallax = np.asarray(parallax_deg, dtype=float)
    seen = np.asarray(visible, dtype=bool)
    if parallax.ndim != 3 or parallax.shape[1] != parallax.shape[2]:
        raise ValueError("parallax_deg must have shape [surfaces, stations, stations]")
    if seen.shape != parallax.shape[:2]:
        raise ValueError("visible must have shape [surfaces, stations]")
    if decorrelation_deg <= 0.0:
        raise ValueError("decorrelation_deg must be positive")
    kernel = np.exp(-((parallax / decorrelation_deg) ** 2))
    mask = seen[:, :, None] & seen[:, None, :]
    total = np.sum(kernel * mask, axis=2)
    weight = np.divide(1.0, total, out=np.zeros_like(total), where=total > 0.0)
    return np.where(seen, weight, 0.0)


def effective_looks(independence: np.ndarray) -> np.ndarray:
    """Effective independent observation count per surface."""
    return np.sum(np.asarray(independence, dtype=float), axis=1)
