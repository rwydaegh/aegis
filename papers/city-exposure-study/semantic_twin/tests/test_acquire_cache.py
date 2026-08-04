"""The one cache rule: a thing is named by what it is, not by where it came from.

Two of these are digest pins. They look like tests of a hash function and they
are not. Both digests name files that are already on disk and were already paid
for, roughly 400 leaf tiles at Milan alone and one routing request per site, so
a change to either recipe silently throws that money away and the next run buys
everything again without saying anything.
"""

from __future__ import annotations

import json
import pathlib

import numpy as np
import pytest

from semantic_twin.acquire.cache import ManifestCache, placement_key, route_key

#: A tile box and its world placement, standing in for one leaf near Ghent.
TILE = {"boundingVolume": {"box": [1.0, 2.0, 3.0, 10.0, 0, 0, 0, 10.0, 0, 0, 0, 10.0]}}
ECEF = (4207000.0, 273000.0, 4780000.0)
GEOMETRIC_ERROR_M = 2.006368774808128

#: Two cameras on the Brussels walk, at the seven decimals the key rounds to.
WAYPOINTS = [(50.8467300, 4.3524700), (50.8465580, 4.3517429)]


def placed(offset_m: tuple[float, float, float] = (0.0, 0.0, 0.0), *, error_m: float = GEOMETRIC_ERROR_M) -> str:
    transform = np.eye(4)
    transform[:3, 3] = np.array(ECEF) + np.array(offset_m)
    return placement_key(TILE["boundingVolume"], transform, error_m, 0)


def test_the_tile_key_still_names_the_tiles_already_on_disk() -> None:
    assert placed() == "fa09752fd51aa74f7b6e98b2cdcf9e45"


def test_the_route_key_still_names_the_routes_already_on_disk() -> None:
    assert route_key(WAYPOINTS, True) == "d7f852fa3671d1a2"
    assert route_key(WAYPOINTS, False) == "a1b68c0cde1b9d63"


def test_a_tile_key_survives_a_rounding_wobble_and_not_a_real_move() -> None:
    """A millimetre is below the metres-across size of the smallest leaf."""
    assert placed((0.0004, 0.0, 0.0)) == placed()
    assert placed((1.0, 0.0, 0.0)) != placed()


def test_two_payloads_of_one_tile_do_not_share_a_name() -> None:
    """Nothing in the hierarchy forbids a tile carrying several payloads."""
    transform = np.eye(4)
    transform[:3, 3] = ECEF
    first = placement_key(TILE["boundingVolume"], transform, GEOMETRIC_ERROR_M, 0)
    second = placement_key(TILE["boundingVolume"], transform, GEOMETRIC_ERROR_M, 1)
    assert first != second


def test_the_same_ground_at_two_levels_of_detail_is_two_things() -> None:
    assert placed(error_m=2.0) != placed(error_m=4.0)


def test_a_tile_with_no_bounding_volume_still_keys_on_its_placement() -> None:
    """The region and extension volume forms are left unpruned, so they arrive here."""
    transform = np.eye(4)
    transform[:3, 3] = ECEF
    bare = placement_key({}, transform, GEOMETRIC_ERROR_M, 0)
    moved = np.eye(4)
    moved[:3, 3] = np.array(ECEF) + np.array([50.0, 0.0, 0.0])
    assert bare != placement_key({}, moved, GEOMETRIC_ERROR_M, 0)


# --- the manifest as the cache -------------------------------------------------


def manifest_with(directory: pathlib.Path, entries: list[tuple[str, str, bytes]]) -> ManifestCache:
    records = []
    for key, name, payload in entries:
        (directory / name).write_bytes(payload)
        records.append({"tile_key": key, "file": name, "size": len(payload)})
    (directory / "manifest.json").write_text(json.dumps({"tiles": records}))
    return ManifestCache(directory / "manifest.json")


def test_an_entry_is_spent_once_so_a_second_claimant_pays(tmp_path: pathlib.Path) -> None:
    """Two things that key the same must not both be handed one file.

    Pointing both at it would leave one of them holding bytes that are not its
    own, and nothing downstream would raise.
    """
    cache = manifest_with(tmp_path, [("abc", "tile_0000.glb", b"payload")])
    assert cache.claim("abc") is not None
    assert cache.claim("abc") is None
    assert cache.reused == 1


def test_a_file_whose_size_disagrees_is_not_reused(tmp_path: pathlib.Path) -> None:
    """A truncated download and a half written file both look like this."""
    cache = manifest_with(tmp_path, [("abc", "tile_0000.glb", b"payload")])
    del cache
    (tmp_path / "tile_0000.glb").write_bytes(b"short")
    assert ManifestCache(tmp_path / "manifest.json").claim("abc") is None


def test_a_manifest_written_before_the_key_existed_matches_nothing(tmp_path: pathlib.Path) -> None:
    (tmp_path / "tile_0000.glb").write_bytes(b"payload")
    (tmp_path / "manifest.json").write_text(json.dumps({"tiles": [{"file": "tile_0000.glb", "size": 7}]}))
    assert ManifestCache(tmp_path / "manifest.json").claim("abc") is None


def test_a_fresh_download_never_lands_on_a_kept_file(tmp_path: pathlib.Path) -> None:
    """Kept files keep their old name, fresh ones count up from the traversal.

    The two schemes collide the moment the hierarchy changes: a tile new to this
    run takes position zero, the kept file is already tile_0000.glb, and the
    fresh bytes land on top of it.
    """
    cache = manifest_with(tmp_path, [("kept", "tile_0000.glb", b"old")])
    assert cache.free_name(0) == "tile_0001.glb"
    assert cache.free_name(0) == "tile_0002.glb"


def test_a_missing_or_broken_manifest_is_an_empty_cache_rather_than_a_failure(tmp_path: pathlib.Path) -> None:
    assert ManifestCache(tmp_path / "manifest.json").claim("abc") is None
    (tmp_path / "manifest.json").write_text("{ not json")
    assert ManifestCache(tmp_path / "manifest.json").claim("abc") is None


@pytest.mark.parametrize("optimise", [True, False])
def test_two_waypoint_sets_that_differ_by_a_camera_are_two_routes(optimise: bool) -> None:
    extended = [*WAYPOINTS, (50.8460000, 4.3510000)]
    assert route_key(WAYPOINTS, optimise) != route_key(extended, optimise)
