from __future__ import annotations

import json
import pathlib
import urllib.parse

import numpy as np
import pytest

from download_inhouse_tiles import (
    BoundedHttpClient,
    DownloadLimitExceeded,
    InhouseTilesDownloader,
    RegionOfInterest,
    llh_to_ecef,
    sanitized_uri,
)
from semantic_twin.geo import enu_rotation


class FakeHttp:
    def __init__(self, responses: dict[str, object]) -> None:
        self.responses = responses
        self.urls: list[str] = []
        self.request_count = 0
        self.total_bytes = 0
        self.max_requests = 20
        self.max_bytes = 10_000

    def get_json(self, url: str) -> dict:
        self.urls.append(url)
        self.request_count += 1
        value = self.responses[urllib.parse.urlsplit(url).path]
        assert isinstance(value, dict)
        self.total_bytes += len(json.dumps(value).encode())
        return value

    def download(self, url: str, destination: pathlib.Path) -> int:
        self.urls.append(url)
        self.request_count += 1
        value = self.responses[urllib.parse.urlsplit(url).path]
        assert isinstance(value, bytes)
        destination.write_bytes(value)
        self.total_bytes += len(value)
        return len(value)


class FakeResponse:
    def __init__(self, body: bytes, content_length: int | None = None) -> None:
        self.body = body
        self.offset = 0
        self.headers = {} if content_length is None else {"Content-Length": str(content_length)}

    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self, size: int) -> bytes:
        result = self.body[self.offset : self.offset + size]
        self.offset += len(result)
        return result


def world_box(center: np.ndarray, half_size_m: float = 1000.0) -> list[float]:
    return [
        *center.tolist(),
        half_size_m,
        0.0,
        0.0,
        0.0,
        half_size_m,
        0.0,
        0.0,
        0.0,
        half_size_m,
    ]


def test_sanitized_uri_removes_all_query_values_and_fragments() -> None:
    uri = "/v1/3dtiles/tile.glb?session=secret&key=also-secret&other=value#part"
    assert sanitized_uri(uri) == "/v1/3dtiles/tile.glb"


def unit_box(center: np.ndarray, half_size_m: float) -> tuple[list[float], np.ndarray]:
    transform = np.eye(4)
    transform[:3, 3] = center
    box = [0.0, 0.0, 0.0, half_size_m, 0.0, 0.0, 0.0, half_size_m, 0.0, 0.0, 0.0, half_size_m]
    return box, transform


def test_obb_intersection_uses_tile_transform() -> None:
    roi = RegionOfInterest(51.055, 3.722, 100.0, 3000.0)
    east = enu_rotation(51.055, 3.722)[0]
    box, transform = unit_box(roi.center + 102.0 * east, 5.0)
    assert roi.intersects_box(box, transform)
    box, transform = unit_box(roi.center + 130.0 * east, 5.0)
    assert not roi.intersects_box(box, transform)


def test_roi_reaches_the_full_radius_at_terrain_height() -> None:
    """A ball on the ellipsoid loses horizontal reach with height. The cylinder does not."""
    lat, lon, radius = 45.4642, 9.19, 200.0
    roi = RegionOfInterest(lat, lon, radius, 3000.0)
    east, _, up = enu_rotation(lat, lon)
    for height_m in (0.0, 163.0, 400.0):
        near = roi.center + height_m * up + 0.99 * radius * east
        far = roi.center + height_m * up + 1.01 * radius * east
        assert roi.distance_to_point(near) == 0.0
        assert roi.distance_to_point(far) > 0.0
    # The old ball on the ellipsoid reached only sqrt(r^2 - h^2) at height h.
    milan = roi.center + 163.0 * up + 0.99 * radius * east
    assert float(np.linalg.norm(milan - roi.center)) > radius


def test_roi_rejects_only_beyond_the_vertical_band() -> None:
    lat, lon = 45.4642, 9.19
    roi = RegionOfInterest(lat, lon, 200.0, 500.0)
    up = enu_rotation(lat, lon)[2]
    assert roi.distance_to_point(roi.center + 499.0 * up) == 0.0
    assert roi.distance_to_point(roi.center + 501.0 * up) > 0.0


def test_roi_box_test_never_prunes_a_touching_box() -> None:
    """The oriented-box predicate must have no false negatives against a sampled truth."""
    rng = np.random.default_rng(20260801)
    lat, lon, radius = 45.4642, 9.19, 200.0
    roi = RegionOfInterest(lat, lon, radius, 300.0)
    basis = enu_rotation(lat, lon).T
    for _ in range(400):
        offset = basis @ rng.uniform(-600.0, 600.0, size=3)
        axes = basis @ np.diag(rng.uniform(5.0, 250.0, size=3)) @ np.linalg.qr(rng.normal(size=(3, 3)))[0]
        box = [*(roi.center + offset).tolist(), *axes[:, 0], *axes[:, 1], *axes[:, 2]]
        corners = np.array(
            [
                roi.center + offset + i * axes[:, 0] + j * axes[:, 1] + k * axes[:, 2]
                for i in (-1.0, 1.0)
                for j in (-1.0, 1.0)
                for k in (-1.0, 1.0)
            ]
        )
        weights = rng.dirichlet(np.ones(8), size=200)
        samples = weights @ corners
        touches = any(roi.distance_to_point(point) == 0.0 for point in samples)
        assert roi.intersects_box(box, np.eye(4)) or not touches


def test_roi_rejects_a_degenerate_configuration() -> None:
    with pytest.raises(ValueError):
        RegionOfInterest(51.0, 3.7, 0.0, 100.0)
    with pytest.raises(ValueError):
        RegionOfInterest(51.0, 3.7, 100.0, 0.0)


def test_zero_cutoff_descends_through_zero_error_parent_and_external_tileset(tmp_path: pathlib.Path) -> None:
    center = llh_to_ecef(51.055, 3.722)
    box = world_box(center)
    root = {
        "root": {
            "boundingVolume": {"box": box},
            "geometricError": 0,
            "content": {"uri": "/parent.glb?session=session-secret&key=returned-key"},
            "children": [
                {
                    "boundingVolume": {"box": box},
                    "geometricError": 0,
                    "content": {"uri": "/branch/tileset.json"},
                }
            ],
        }
    }
    branch = {
        "root": {
            "boundingVolume": {"box": box},
            "geometricError": 0,
            "content": {"uri": "leaf.glb?session=session-secret&key=returned-key"},
        }
    }
    http = FakeHttp(
        {
            "/v1/3dtiles/root.json": root,
            "/branch/tileset.json": branch,
            "/branch/leaf.glb": b"leaf-glb",
            "/parent.glb": b"parent-glb",
        }
    )
    downloader = InhouseTilesDownloader(
        "real-api-key",
        lat=51.055,
        lon=3.722,
        radius_m=100.0,
        geometric_error_cutoff_m=0.0,
        out_dir=tmp_path,
        http=http,  # type: ignore[arg-type]
    )

    manifest = downloader.run()

    assert [tile["uri"] for tile in manifest["tiles"]] == ["leaf.glb"]
    assert (tmp_path / "tile_0000.glb").read_bytes() == b"leaf-glb"
    assert not (tmp_path / "tile_0001.glb").exists()
    persisted = (tmp_path / "manifest.json").read_text()
    assert "session-secret" not in persisted
    assert "real-api-key" not in persisted
    assert "returned-key" not in persisted
    assert all(urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)["key"] == ["real-api-key"] for url in http.urls)
    assert urllib.parse.parse_qs(urllib.parse.urlsplit(http.urls[-1]).query)["session"] == ["session-secret"]


def leaf_scene(center: np.ndarray, leaves: list[str]) -> dict:
    """A root that refines straight into one child per named payload.

    Each child is given its own box, because real sibling tiles cover different
    ground and the cache key says which ground. Keyed by name rather than by
    position, so adding a leaf does not silently move another one's key.
    """
    return {
        "root": {
            "boundingVolume": {"box": world_box(center)},
            "geometricError": 0,
            "children": [
                {
                    "boundingVolume": {
                        "box": world_box(center + float(sum(map(ord, leaf)) % 40) * np.array([1.0, 0.0, 0.0]), 10.0)
                    },
                    "geometricError": 0,
                    "content": {"uri": leaf},
                }
                for leaf in leaves
            ],
        }
    }


def tile_downloader(tmp_path: pathlib.Path, http: FakeHttp) -> InhouseTilesDownloader:
    return InhouseTilesDownloader(
        "real-api-key",
        lat=51.055,
        lon=3.722,
        radius_m=100.0,
        geometric_error_cutoff_m=0.0,
        out_dir=tmp_path,
        http=http,  # type: ignore[arg-type]
    )


def test_a_second_run_over_the_same_output_buys_no_tile_twice(tmp_path: pathlib.Path) -> None:
    """The whole point of writing the manifest is that it is also the cache.

    Every site's tiles are paid for once against a daily cap, and the two caches
    on the downloader only ever stopped it buying the same tile twice inside one
    run. Re-running a site used to pay for the site again from nothing, which is
    155 to 1,178 requests depending on the site.
    """
    center = llh_to_ecef(51.055, 3.722)
    payloads = {
        "/v1/3dtiles/root.json": leaf_scene(center, ["/one.glb", "/two.glb"]),
        "/one.glb": b"one-glb",
        "/two.glb": b"two-glb",
    }

    first = FakeHttp(dict(payloads))
    tile_downloader(tmp_path, first).run()
    downloads = [url for url in first.urls if ".glb" in url]
    assert len(downloads) == 2

    second = FakeHttp(dict(payloads))
    manifest = tile_downloader(tmp_path, second).run()

    assert [url for url in second.urls if ".glb" in url] == []
    assert manifest["reused_from_disk"] == 2
    assert {tile["file"] for tile in manifest["tiles"]} == {"tile_0000.glb", "tile_0001.glb"}
    assert (tmp_path / "tile_0000.glb").read_bytes() == b"one-glb"


def test_a_new_tile_does_not_overwrite_a_kept_one(tmp_path: pathlib.Path) -> None:
    """Names count up from the traversal position, kept files keep their own.

    Those two schemes collide the moment the hierarchy changes: a tile new to
    this run takes position zero, the file kept from last run is already called
    tile_0000.glb, and the fresh bytes land on top of the kept ones.
    """
    center = llh_to_ecef(51.055, 3.722)
    first = FakeHttp(
        {
            "/v1/3dtiles/root.json": leaf_scene(center, ["/old.glb"]),
            "/old.glb": b"old-glb",
        }
    )
    tile_downloader(tmp_path, first).run()

    second = FakeHttp(
        {
            "/v1/3dtiles/root.json": leaf_scene(center, ["/new.glb", "/old.glb"]),
            "/new.glb": b"new-glb",
            "/old.glb": b"old-glb",
        }
    )
    manifest = tile_downloader(tmp_path, second).run()

    assert manifest["reused_from_disk"] == 1
    assert [url for url in second.urls if ".glb" in url] == [url for url in second.urls if "new.glb" in url]
    kept = next(tile for tile in manifest["tiles"] if tile["tile_key"] and tile["uri"].endswith("/old.glb"))
    assert (tmp_path / kept["file"]).read_bytes() == b"old-glb"
    fresh = next(tile for tile in manifest["tiles"] if tile["tile_key"] and tile["uri"].endswith("/new.glb"))
    assert fresh["file"] != kept["file"]
    assert (tmp_path / fresh["file"]).read_bytes() == b"new-glb"


def test_a_changed_payload_is_fetched_again(tmp_path: pathlib.Path) -> None:
    """The size on disk has to match what the manifest says it should be.

    A truncated download, a half written file or an edited tile all show up as a
    size that disagrees, and reusing any of them would put corrupt geometry into
    every mesh built afterwards without a single error.
    """
    center = llh_to_ecef(51.055, 3.722)
    payloads = {
        "/v1/3dtiles/root.json": leaf_scene(center, ["/one.glb"]),
        "/one.glb": b"one-glb",
    }
    tile_downloader(tmp_path, FakeHttp(dict(payloads))).run()
    (tmp_path / "tile_0000.glb").write_bytes(b"truncated")

    http = FakeHttp(dict(payloads))
    manifest = tile_downloader(tmp_path, http).run()

    assert manifest["reused_from_disk"] == 0
    assert len([url for url in http.urls if ".glb" in url]) == 1
    assert (tmp_path / "tile_0000.glb").read_bytes() == b"one-glb"


def test_http_client_stops_stream_at_byte_cap(tmp_path: pathlib.Path) -> None:
    response = FakeResponse(b"123456")
    client = BoundedHttpClient(2, 5, opener=lambda request, timeout: response)

    with pytest.raises(DownloadLimitExceeded, match="byte cap"):
        client.download("https://tile.googleapis.com/tile.glb", tmp_path / "tile.glb")

    assert client.request_count == 1
    assert client.total_bytes == 0
    assert not (tmp_path / "tile.glb").exists()
    assert not (tmp_path / "tile.glb.part").exists()


def test_http_client_checks_request_cap_before_opening() -> None:
    opened = 0

    def opener(request: object, timeout: float) -> FakeResponse:
        nonlocal opened
        opened += 1
        return FakeResponse(b"{}")

    client = BoundedHttpClient(1, 100, opener=opener)
    assert client.get_json("https://tile.googleapis.com/first.json") == {}
    with pytest.raises(DownloadLimitExceeded, match="request cap"):
        client.get_json("https://tile.googleapis.com/second.json")
    assert opened == 1


def test_the_provider_names_are_harvested_from_every_tileset(tmp_path: pathlib.Path) -> None:
    """Google requires the data providers to be shown with the imagery."""
    downloader = tile_downloader(tmp_path, FakeHttp({}))
    downloader._collect_attribution({"asset": {"copyright": "Google;Airbus;Maxar Technologies"}})
    downloader._collect_attribution({"asset": {"copyright": "Google; Airbus"}})
    assert sorted(downloader._attributions) == ["Airbus", "Google", "Maxar Technologies"]


def test_a_tileset_with_no_copyright_adds_nothing(tmp_path: pathlib.Path) -> None:
    downloader = tile_downloader(tmp_path, FakeHttp({}))
    downloader._collect_attribution({"asset": {"version": "1.0"}})
    downloader._collect_attribution({"asset": {"copyright": "  ;  "}})
    downloader._collect_attribution({})
    assert downloader._attributions == set()
