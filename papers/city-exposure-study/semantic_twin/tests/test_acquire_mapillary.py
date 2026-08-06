from __future__ import annotations

import math
import urllib.parse

import numpy as np
import pytest

from semantic_twin.scene.enu import EnuFrame
from semantic_twin.acquire import mapillary
from semantic_twin.acquire.mapillary import (
    SEED_FIELDS,
    SampledEndpointError,
    diversify,
    download_panorama_image,
    orientation_from_computed_rotation,
    pose_from_metadata,
    rank_for_target,
    rodrigues,
)
from semantic_twin.pano_geometry import panorama_to_world_matrix


def _image(image_id: str, lat: float, lon: float, heading: float, *, pano: bool = False) -> dict:
    return {
        "id": image_id,
        "computed_geometry": {"coordinates": [lon, lat]},
        "computed_compass_angle": heading,
        "quality_score": 0.9,
        "is_pano": pano,
        "width": 4000,
        "height": 3000,
    }


def test_rank_for_target_rejects_nearby_camera_facing_away() -> None:
    frame = EnuFrame(51.0, 3.0)
    images = [_image("toward", 51.0, 2.9998, 90.0), _image("away", 51.0, 2.9998, 270.0)]
    result = rank_for_target(images, frame, target_lat=51.0, target_lon=3.0)
    assert [candidate.image_id for candidate in result] == ["toward"]


def test_pano_is_retained_despite_its_reported_heading() -> None:
    frame = EnuFrame(51.0, 3.0)
    result = rank_for_target([_image("pano", 51.0, 3.0002, 90.0, pano=True)], frame, target_lat=51.0, target_lon=3.0)
    assert result[0].image_id == "pano"


def test_diversify_drops_near_duplicate_camera_centres() -> None:
    frame = EnuFrame(51.0, 3.0)
    candidates = rank_for_target(
        [_image("a", 51.0, 2.9998, 90.0), _image("b", 51.0, 2.99979, 90.0), _image("c", 51.0, 2.9996, 90.0)],
        frame,
        target_lat=51.0,
        target_lon=3.0,
    )
    assert [candidate.image_id for candidate in diversify(candidates, frame, count=3, separation_m=6.0)] == ["c", "b"]


def _rotation_vector(heading_deg: float, tilt_deg: float, roll_deg: float) -> list[float]:
    """Build the ``computed_rotation`` a camera with this pose would report."""
    world = panorama_to_world_matrix(heading_deg, pitch_deg=tilt_deg - 90.0, roll_deg=roll_deg)
    rotation = np.stack([world[:, 0], -world[:, 2], world[:, 1]])
    angle = math.acos(float(np.clip((np.trace(rotation) - 1.0) / 2.0, -1.0, 1.0)))
    axis = np.array(
        [
            rotation[2, 1] - rotation[1, 2],
            rotation[0, 2] - rotation[2, 0],
            rotation[1, 0] - rotation[0, 1],
        ]
    ) / (2.0 * math.sin(angle))
    return (axis * angle).tolist()


def test_rodrigues_matches_a_quarter_turn_about_the_vertical() -> None:
    rotation = rodrigues([0.0, 0.0, math.pi / 2.0])
    assert np.allclose(rotation @ np.array([1.0, 0.0, 0.0]), [0.0, 1.0, 0.0], atol=1e-12)
    assert np.allclose(rodrigues([0.0, 0.0, 0.0]), np.eye(3))


@pytest.mark.parametrize(
    ("heading", "tilt", "roll"),
    [(0.0, 90.0, 0.0), (189.2, 93.7, -2.7), (305.1, 116.7, -3.1), (47.0, 84.0, 5.5)],
)
def test_orientation_from_computed_rotation_round_trips(heading: float, tilt: float, roll: float) -> None:
    recovered = orientation_from_computed_rotation(_rotation_vector(heading, tilt, roll))
    assert recovered[0] == pytest.approx(heading % 360.0, abs=1e-6)
    assert recovered[1] == pytest.approx(tilt, abs=1e-6)
    assert recovered[2] == pytest.approx(roll, abs=1e-6)


def test_measured_gravity_tilt_survives_into_the_pose() -> None:
    """The three selected Korenmarkt panoramas tilt by 4.5, 7.8 and 26.8 degrees."""
    observed = {
        "1829740437845894": ([0.11427616920294, 2.050205324748, -2.1771815255044], 4.517),
        "1210809344096709": ([0.097102119403296, 2.0052356219295, -2.2932342697249], 7.751),
        "1115822493667753": ([0.990626082998, 0.57043169665009, -0.82648971036163], 26.821),
    }
    scene = {"enu_origin": {"lat": 51.0, "lon": 3.0}, "camera_ground_z_m": 10.0, "camera_height_m": 2.0}
    for rotation_vector, gravity_tilt in observed.values():
        metadata = _image("pano", 51.0, 3.0, 0.0, pano=True)
        metadata["computed_rotation"] = rotation_vector
        pose = pose_from_metadata(metadata, scene)
        tilt = math.degrees(
            math.acos(
                math.cos(math.radians(pose.tilt_deg - 90.0)) * math.cos(math.radians(pose.roll_deg)),
            )
        )
        assert tilt == pytest.approx(gravity_tilt, abs=0.01)
        assert "computed_rotation" in pose.orientation_source


def test_a_panorama_without_computed_rotation_is_labelled_not_silently_levelled() -> None:
    scene = {"enu_origin": {"lat": 51.0, "lon": 3.0}, "camera_ground_z_m": 10.0, "camera_height_m": 2.0}
    pose = pose_from_metadata(_image("pano", 51.0, 3.0, 123.0, pano=True), scene)
    assert (pose.tilt_deg, pose.roll_deg) == (90.0, 0.0)
    assert pose.orientation_source.startswith("absent")
    assert pose.heading_deg == 123.0


def test_levelled_heading_differs_from_the_reported_compass_under_tilt() -> None:
    """``computed_compass_angle`` is the tilted optical axis, not the pose heading."""
    metadata = _image("pano", 51.0, 3.0, 303.55345366896, pano=True)
    metadata["computed_rotation"] = [0.990626082998, 0.57043169665009, -0.82648971036163]
    scene = {"enu_origin": {"lat": 51.0, "lon": 3.0}, "camera_ground_z_m": 10.0, "camera_height_m": 2.0}
    pose = pose_from_metadata(metadata, scene)
    assert abs(pose.heading_deg - float(metadata["computed_compass_angle"])) > 1.0


def test_mapillary_spherical_pose_uses_camera_heading_and_scene_height() -> None:
    metadata = _image("pano", 51.0001, 3.0002, 123.0, pano=True)
    scene = {
        "enu_origin": {"lat": 51.0, "lon": 3.0},
        "camera_ground_z_m": 10.0,
        "camera_height_m": 2.0,
    }
    pose = pose_from_metadata(metadata, scene)
    assert pose.heading_deg == 123.0
    assert pose.position_wgs84 == (51.0001, 3.0002)
    assert pose.position_enu_m[2] == 12.0


def test_panorama_download_prefers_provider_original_url(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    metadata = _image("pano", 51.0, 3.0, 0.0, pano=True)
    metadata.update(
        {
            "thumb_2048_url": "https://example.invalid/2048.jpg",
            "thumb_original_url": "https://example.invalid/original.jpg",
        }
    )

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self) -> bytes:
            from io import BytesIO

            from PIL import Image

            image = Image.new("RGB", (2, 1))
            payload = BytesIO()
            image.save(payload, format="JPEG")
            return payload.getvalue()

    seen: list[str] = []

    def fake_urlopen(url: str, timeout: int):
        seen.append(url)
        assert timeout == 90
        return Response()

    monkeypatch.setattr("semantic_twin.acquire.mapillary.urllib.request.urlopen", fake_urlopen)
    path, source_field = download_panorama_image(metadata, tmp_path / "pano.jpg")
    assert path.exists()
    assert source_field == "thumb_original_url"
    assert seen == [metadata["thumb_original_url"]]


# --- the bounding box endpoint returns a sample and does not say so -----------


class RecordedGraph:
    """A stand-in for the Graph API, recorded from the Korenmarkt measurement.

    One sequence of 135 frames along the Korenmarkt street, 13 of them inside
    60 m of the site centre. The bbox endpoint shows two of those thirteen and
    reports nothing about the other eleven, which is what was measured against
    the live API on 2026-08-04. The identifier endpoints are complete.
    """

    SEQUENCE = "u5WIQvkTXO7SbeL1l8UN6a"
    CENTRE = (51.0550, 3.7220)

    def __init__(self) -> None:
        # Frames every 9.5 m along a line through the site, which is the spacing
        # that puts 13 of the 135 inside 60 m and 15 inside 70 m, as measured.
        self.frames = [
            {
                "id": f"{100000 + index}",
                "sequence": self.SEQUENCE,
                "is_pano": True,
                "computed_geometry": {"coordinates": [self.CENTRE[1], self.CENTRE[0] + (index - 67) * 9.5 / 111320.0]},
                "computed_compass_angle": 0.0,
                "computed_rotation": [0.0, 2.2, -2.2],
                "quality_score": 0.8,
            }
            for index in range(135)
        ]
        self.shown_in_box = [self.frames[67], self.frames[70]]
        self.urls: list[str] = []

    def request(self, url: str, *, timeout: float, attempts: int = 4) -> dict:
        self.urls.append(url)
        query = dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(url).query))
        if "bbox" in query:
            west, south, east, north = (float(value) for value in query["bbox"].split(","))
            fields = query["fields"].split(",")
            inside = [
                frame
                for frame in self.shown_in_box
                if west <= frame["computed_geometry"]["coordinates"][0] < east
                and south <= frame["computed_geometry"]["coordinates"][1] < north
            ]
            return {"data": [{key: frame[key] for key in fields} for frame in inside]}
        if "sequence_id" in query:
            return {"data": [{"id": frame["id"]} for frame in self.frames]}
        wanted = set(query["image_ids"].split(","))
        return {"data": [frame for frame in self.frames if frame["id"] in wanted]}


@pytest.fixture
def graph(monkeypatch: pytest.MonkeyPatch) -> RecordedGraph:
    recorded = RecordedGraph()
    monkeypatch.setattr(mapillary, "_request", recorded.request)
    return recorded


def near_centre(records: list[dict], radius_m: float = 60.0) -> list[dict]:
    frame = EnuFrame(*RecordedGraph.CENTRE)
    kept = []
    for record in records:
        longitude, latitude = record["computed_geometry"]["coordinates"]
        if float(np.linalg.norm(frame.to_enu(latitude, longitude)[:2])) <= radius_m:
            kept.append(record)
    return kept


def test_the_box_names_sequences_and_hands_back_no_image_records(graph: RecordedGraph) -> None:
    """The whole structural fix in one assertion: the return type is names.

    A caller cannot rank, score or select from this, because there is nothing
    here to rank. It has to expand the names, and expansion is complete.
    """
    seeds = mapillary.seed_sequence_ids("token", latitude=51.0550, longitude=3.7220, cells=2)
    assert seeds.sequence_ids == frozenset({RecordedGraph.SEQUENCE})
    assert all(isinstance(name, str) for name in seeds.sequence_ids)


def test_selecting_from_the_box_would_have_kept_two_of_thirteen(graph: RecordedGraph) -> None:
    """The measurement the module is shaped around, run as a test.

    The box shows 2 frames of a sequence that has 13 inside the site radius, and
    the reply carries no truncation flag, no cursor and no total. Traversal
    recovers all 13. A study that selected from the box would have concluded the
    site was thinly covered and never learned otherwise.
    """
    seeds = mapillary.seed_sequence_ids("token", latitude=51.0550, longitude=3.7220, cells=2)
    assert seeds.seed_images == len(graph.shown_in_box)

    traversed = mapillary.traverse("token", seeds.sequence_ids)
    assert len(traversed) == 135
    assert len(near_centre(list(traversed.values()))) == 13
    assert len(near_centre(list(traversed.values()), radius_m=70.0)) == 15
    assert len(near_centre(graph.shown_in_box)) == 2


def test_the_box_cannot_be_widened_into_a_selection(graph: RecordedGraph) -> None:
    """Adding a field is how the sampled route becomes a selection route.

    It is refused at the transport, so the guard holds for a caller that never
    reads the docstring above it.
    """
    with pytest.raises(SampledEndpointError, match="silent sample"):
        mapillary._graph("images", "token", bbox="3.0,51.0,3.001,51.001", fields=mapillary.IMAGE_FIELDS)
    with pytest.raises(SampledEndpointError):
        mapillary._graph("images", "token", bbox="3.0,51.0,3.001,51.001", fields="id,computed_geometry")
    with pytest.raises(SampledEndpointError):
        mapillary._graph("images", "token", bbox="3.0,51.0,3.001,51.001")


def test_every_box_query_the_module_sends_asks_only_for_the_seed_fields(graph: RecordedGraph) -> None:
    mapillary.seed_sequence_ids("token", latitude=51.0550, longitude=3.7220, cells=3)
    boxed = [url for url in graph.urls if "bbox" in url]
    assert boxed
    for url in boxed:
        query = dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(url).query))
        assert query["fields"] == SEED_FIELDS


def test_a_cell_wider_than_the_api_limit_is_refused_before_the_network() -> None:
    with pytest.raises(ValueError, match="bbox limit"):
        mapillary.seed_sequence_ids("token", latitude=51.055, longitude=3.722, half_width_m=5000.0, cells=1)


def test_ranking_takes_records_so_it_can_only_be_reached_by_identifier(graph: RecordedGraph) -> None:
    """A sampled reply carries no coordinates, so it cannot be ranked at all."""
    seeds = mapillary.seed_sequence_ids("token", latitude=51.0550, longitude=3.7220, cells=2)
    complete = list(mapillary.traverse("token", seeds.sequence_ids).values())
    ranked = rank_for_target(complete, EnuFrame(*RecordedGraph.CENTRE), target_lat=51.0551, target_lon=3.7221)
    assert ranked
