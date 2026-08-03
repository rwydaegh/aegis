"""Publishing nested fishnet views, which `bind` reads by a non recursive glob."""

from __future__ import annotations

import json

import numpy as np
import pytest

import flatten_fishnet_outputs
from flatten_fishnet_outputs import (
    broken,
    fishnet_directories,
    flat_name,
    main,
    nested_views,
    publish,
    published_views,
    site_directory,
)


def fishnet(root, site, *, segmentation="vistas", panoramas=("pano_00_abc",), views=("h+00_000", "h+00_090")):
    directory = root / "outputs" / f"{site}_fishnet_{segmentation}"
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "site_fishnet_manifest.json").write_text(json.dumps({"mesh": "inhouse_leaf_130m.ply"}))
    for panorama in panoramas:
        folder = directory / panorama
        folder.mkdir(exist_ok=True)
        for view in views:
            np.savez(folder / f"{view}_fishnet.npz", face_area_m2=np.ones(3))
    return directory


def test_a_nested_view_is_published_under_the_panorama_that_produced_it(tmp_path, monkeypatch):
    monkeypatch.setattr(flatten_fishnet_outputs, "SCRIPT_DIR", tmp_path)
    directory = fishnet(tmp_path, "prague_staromestske")
    publish(directory, dry_run=False)
    assert [p.name for p in published_views(directory)] == [
        "pano_00_abc_h+00_000_fishnet.npz",
        "pano_00_abc_h+00_090_fishnet.npz",
    ]


def test_the_published_name_matches_the_convention_used_by_the_hand_flattened_site():
    # New York was flattened before this script existed and the two layouts have
    # to be indistinguishable to a reader, so the convention is pinned here.
    assert flat_name("pano_07_CAoSFkNJSE0wb2dL", "h+00_000_fishnet.npz") == (
        "pano_07_CAoSFkNJSE0wb2dL_h+00_000_fishnet.npz"
    )


def test_a_published_view_actually_opens(tmp_path, monkeypatch):
    # The first version of this script wrote targets relative to the parent
    # rather than to the directory holding the link, so every name globbed and
    # none of them opened, which is worse than publishing nothing at all.
    monkeypatch.setattr(flatten_fishnet_outputs, "SCRIPT_DIR", tmp_path)
    directory = fishnet(tmp_path, "prague_staromestske")
    publish(directory, dry_run=False)
    for path in published_views(directory):
        assert np.load(path)["face_area_m2"].size == 3


def test_a_link_that_does_not_resolve_is_removed_rather_than_left(tmp_path, monkeypatch):
    monkeypatch.setattr(flatten_fishnet_outputs, "SCRIPT_DIR", tmp_path)
    directory = fishnet(tmp_path, "prague_staromestske")
    (directory / "pano_00_abc" / "h+00_000_fishnet.npz").unlink()
    (directory / "pano_00_abc" / "h+00_000_fishnet.npz").symlink_to("nowhere.npz")
    with pytest.raises(SystemExit, match="does not resolve"):
        publish(directory, dry_run=False)
    assert not (directory / "pano_00_abc_h+00_000_fishnet.npz").is_symlink()


def test_publishing_twice_publishes_nothing_the_second_time(tmp_path, monkeypatch):
    monkeypatch.setattr(flatten_fishnet_outputs, "SCRIPT_DIR", tmp_path)
    directory = fishnet(tmp_path, "prague_staromestske")
    assert publish(directory, dry_run=False)["published"] == 2
    again = publish(directory, dry_run=False)
    assert again == {"published": 0, "already": 2, "occupied": 0}


def test_a_link_pointing_somewhere_else_is_repaired(tmp_path, monkeypatch):
    monkeypatch.setattr(flatten_fishnet_outputs, "SCRIPT_DIR", tmp_path)
    directory = fishnet(tmp_path, "prague_staromestske")
    wrong = directory / "pano_00_abc_h+00_000_fishnet.npz"
    wrong.symlink_to("pano_00_abc/h+00_090_fishnet.npz")
    tally = publish(directory, dry_run=False)
    assert tally["already"] == 0, "a link to the wrong view is not an already published one"
    assert wrong.readlink().name == "h+00_000_fishnet.npz"


def test_a_real_file_holding_the_name_is_never_clobbered(tmp_path, monkeypatch):
    # The hand flattened site moved its files rather than linking them, so the
    # name is a real npz there and this script must not touch it.
    monkeypatch.setattr(flatten_fishnet_outputs, "SCRIPT_DIR", tmp_path)
    directory = fishnet(tmp_path, "newyork_timessquare")
    np.savez(directory / "pano_00_abc_h+00_000_fishnet.npz", face_area_m2=np.zeros(9))
    tally = publish(directory, dry_run=False)
    assert tally["occupied"] == 1 and tally["published"] == 1
    assert np.load(directory / "pano_00_abc_h+00_000_fishnet.npz")["face_area_m2"].size == 9


def test_a_dry_run_writes_nothing(tmp_path, monkeypatch):
    monkeypatch.setattr(flatten_fishnet_outputs, "SCRIPT_DIR", tmp_path)
    directory = fishnet(tmp_path, "prague_staromestske")
    assert publish(directory, dry_run=True)["published"] == 2
    assert published_views(directory) == []


def test_a_site_that_is_already_flat_is_left_alone(tmp_path, monkeypatch):
    monkeypatch.setattr(flatten_fishnet_outputs, "SCRIPT_DIR", tmp_path)
    directory = tmp_path / "outputs" / "milan_duomo_fishnet_vistas"
    directory.mkdir(parents=True)
    np.savez(directory / "pano_00_abc_h+00_000_fishnet.npz", face_area_m2=np.ones(2))
    assert nested_views(directory) == []
    assert publish(directory, dry_run=False)["published"] == 0
    assert len(published_views(directory)) == 1


def test_an_unknown_site_is_refused(tmp_path, monkeypatch):
    monkeypatch.setattr(flatten_fishnet_outputs, "SCRIPT_DIR", tmp_path)
    with pytest.raises(SystemExit, match="no fishnet directory"):
        site_directory("atlantis")


def test_a_site_with_two_segmentations_has_to_be_named_explicitly(tmp_path, monkeypatch):
    # Korenmarkt carries vistas, sam3 and a fused set, and guessing between them
    # would silently publish into the wrong binding.
    monkeypatch.setattr(flatten_fishnet_outputs, "SCRIPT_DIR", tmp_path)
    fishnet(tmp_path, "korenmarkt", segmentation="vistas")
    fishnet(tmp_path, "korenmarkt", segmentation="sam3")
    with pytest.raises(SystemExit, match="more than one fishnet directory"):
        site_directory("korenmarkt")


def test_directories_are_listed_in_site_order_and_exclude_stray_files(tmp_path, monkeypatch):
    monkeypatch.setattr(flatten_fishnet_outputs, "SCRIPT_DIR", tmp_path)
    fishnet(tmp_path, "prague_staromestske")
    fishnet(tmp_path, "brussels_grandplace")
    (tmp_path / "outputs" / "notes_fishnet_vistas.txt").write_text("")
    assert [d.name for d in fishnet_directories()] == [
        "brussels_grandplace_fishnet_vistas",
        "prague_staromestske_fishnet_vistas",
    ]


def test_a_dangling_published_name_is_reported(tmp_path, monkeypatch):
    monkeypatch.setattr(flatten_fishnet_outputs, "SCRIPT_DIR", tmp_path)
    directory = fishnet(tmp_path, "prague_staromestske")
    (directory / "orphan_fishnet.npz").symlink_to("gone/h+00_000_fishnet.npz")
    assert [p.name for p in broken(directory)] == ["orphan_fishnet.npz"]


def test_exactly_one_of_site_and_all_is_required(tmp_path, monkeypatch):
    monkeypatch.setattr(flatten_fishnet_outputs, "SCRIPT_DIR", tmp_path)
    with pytest.raises(SystemExit, match="exactly one"):
        main([])
    with pytest.raises(SystemExit, match="exactly one"):
        main(["--site", "prague_staromestske", "--all"])


def test_all_covers_every_site_at_once(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(flatten_fishnet_outputs, "SCRIPT_DIR", tmp_path)
    fishnet(tmp_path, "prague_staromestske")
    fishnet(tmp_path, "brussels_grandplace")
    assert main(["--all"]) == 0
    printed = capsys.readouterr().out
    assert "prague_staromestske_fishnet_vistas" in printed
    assert "brussels_grandplace_fishnet_vistas" in printed
