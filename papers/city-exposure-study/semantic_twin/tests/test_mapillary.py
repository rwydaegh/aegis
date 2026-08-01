from __future__ import annotations

import pytest

from semantic_twin.geo import EnuFrame
from semantic_twin.mapillary import (
    diversify,
    download_panorama_image,
    fetch_images,
    pose_from_metadata,
    rank_for_target,
)


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
