from __future__ import annotations

import math

import numpy as np
import pytest

from semantic_twin.geo import EnuFrame
from semantic_twin.mapillary import (
    diversify,
    download_panorama_image,
    fetch_images,
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


def test_fetch_images_rejects_an_oversized_bbox_before_network() -> None:
    with pytest.raises(ValueError, match="smaller"):
        fetch_images("token", (3.0, 51.0, 3.02, 51.001))


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

    monkeypatch.setattr("semantic_twin.mapillary.urllib.request.urlopen", fake_urlopen)
    path, source_field = download_panorama_image(metadata, tmp_path / "pano.jpg")
    assert path.exists()
    assert source_field == "thumb_original_url"
    assert seen == [metadata["thumb_original_url"]]
