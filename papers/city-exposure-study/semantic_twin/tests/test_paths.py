"""Tests for the one path module, against the disk it was read off.

The point of these is not that a function returns what it was told. It is that
the layout written down in :mod:`semantic_twin.paths` is the layout that is
actually there. So most of these resolve a path and then open the file, and the
ones that do not are the ones about the irregular cases: Milan's missing 130 m
build, Times Square's missing double precision file, and the exposure directory
named after one of the eleven cities it holds.
"""

from __future__ import annotations

import json
import re

import pytest

from semantic_twin import paths

pytestmark = pytest.mark.skipif(not paths.data_dir().is_dir(), reason="study data is not on this machine")


def test_the_root_is_the_directory_holding_config_data_and_outputs():
    root = paths.root()
    assert (root / "config").is_dir()
    assert (root / "data").is_dir()
    assert (root / "run_exposure.py").is_file()
    assert paths.config_dir().parent == root


def test_korenmarkt_at_130_m_resolves_to_the_double_precision_rebuild():
    """The one case where two builds of the same crop sit side by side.

    Korenmarkt has a version 2 mesh and an ``_f64`` version 3 rebuild at 130 m.
    Picking the wrong one costs up to a metre of seaming along tile boundaries,
    and the file names alone do not say which is which.
    """
    mesh = paths.site_mesh("korenmarkt", 130)
    assert mesh.exists()
    assert mesh.name.endswith("_f64.ply")
    assert json.loads(paths.mesh_manifest(mesh).read_text())["format_version"] >= 3


def test_times_square_resolves_although_it_has_no_double_precision_file():
    """The case a suffix-only rule loses.

    Times Square has no ``_f64`` file at any radius. Its plain build is already
    version 3, so the version gate admits it and the name gate would not.
    """
    mesh = paths.site_mesh("newyork_timessquare", 250)
    assert mesh.exists()
    assert not mesh.name.endswith("_f64.ply")


def test_every_configured_site_has_a_mesh_at_250_m():
    """250 m is the radius the cross city sweep runs at, so all eleven must have one."""
    for name in sorted(path.stem for path in paths.config_dir().glob("*.json")):
        if not (paths.geometry_dir(name)).is_dir():
            continue
        assert paths.site_mesh(name, 250).exists()


def test_milan_has_no_130_m_mesh_and_says_so_by_raising():
    with pytest.raises(FileNotFoundError):
        paths.site_mesh("milan_duomo", 130)
    assert 130 not in paths.mesh_crops("milan_duomo")
    assert 170 in paths.mesh_crops("milan_duomo")


def test_the_crop_set_is_read_off_the_disk_and_every_member_opens():
    crops = paths.mesh_crops("korenmarkt")
    assert crops == tuple(sorted(crops))
    assert 130 in crops and 250 in crops
    for crop in crops:
        assert paths.site_mesh("korenmarkt", crop).exists()


def test_the_crop_set_excludes_the_superseded_single_precision_builds():
    """Korenmarkt's 60, 100 and 120 m builds are version 1 and 2 and must not appear."""
    crops = paths.mesh_crops("korenmarkt")
    assert not {60, 100, 120} & set(crops)
    assert (paths.geometry_dir("korenmarkt") / "inhouse_leaf_120m.ply").exists()


def test_a_missing_mesh_names_the_directory_it_looked_in():
    with pytest.raises(FileNotFoundError, match="korenmarkt"):
        paths.site_mesh("korenmarkt", 999)


@pytest.mark.parametrize(
    ("build", "reason"),
    [
        (None, "no such mesh"),
        ("no sidecar", "no sidecar inhouse_leaf_250m.json"),
        ("bad sidecar", "carries no readable format_version"),
        ("version 2", "format_version 2, below 3"),
    ],
)
def test_a_refused_mesh_says_which_of_the_four_things_is_wrong_with_it(tmp_path, build, reason):
    """Four causes that need four different fixes, and they all used to read the same.

    The old message was "no double precision 250 m mesh", which is wrong twice
    over: the gate is the format version and not the precision, and Times Square
    passes it with no double precision file anywhere. Someone reading this at hour
    two of a sweep has to know whether to rebuild a mesh, rebuild a sidecar or fix
    a crop radius.
    """
    directory = tmp_path / "data" / "geometry" / "somewhere"
    directory.mkdir(parents=True)
    if build is not None:
        (directory / "inhouse_leaf_250m.ply").write_bytes(b"ply\n")
    if build == "bad sidecar":
        (directory / "inhouse_leaf_250m.json").write_text("{not json")
    if build == "version 2":
        (directory / "inhouse_leaf_250m.json").write_text(json.dumps({"format_version": 2}))

    paths.forget_disk_reads()
    with pytest.raises(FileNotFoundError, match=re.escape(reason)):
        paths.site_mesh("somewhere", 250, root_dir=tmp_path)


def test_the_disk_is_read_again_after_a_mesh_is_written(tmp_path):
    """A build-then-verify script runs in one process, and the answer was cached.

    The format version and the crop set are both held for the life of the
    process, which is right for a sweep asking eleven sites the same question and
    wrong for the script that writes the mesh. There was no way to say so.
    """
    directory = tmp_path / "data" / "geometry" / "somewhere"
    directory.mkdir(parents=True)
    mesh = directory / "inhouse_leaf_250m.ply"
    manifest = directory / "inhouse_leaf_250m.json"
    mesh.write_bytes(b"ply\n")
    manifest.write_text(json.dumps({"format_version": 2}))

    paths.forget_disk_reads()
    with pytest.raises(FileNotFoundError):
        paths.site_mesh("somewhere", 250, root_dir=tmp_path)

    manifest.write_text(json.dumps({"format_version": 3}))
    with pytest.raises(FileNotFoundError):
        paths.site_mesh("somewhere", 250, root_dir=tmp_path)

    paths.forget_disk_reads()
    assert paths.site_mesh("somewhere", 250, root_dir=tmp_path) == mesh


def test_the_two_panorama_layouts_both_yield_camera_directories():
    """Nested and flat, and both have to answer the same question.

    Prague has one subdirectory per camera. Korenmarkt's Street View capture
    predates that script and put its single camera's files in the set directory,
    so the set directory is its own camera directory.
    """
    nested = paths.panorama_stations("prague_staromestske", "pano_")
    assert len(nested) >= 10
    assert all(paths.panorama_semantics(station).exists() for station in nested)

    flat = paths.panorama_stations("korenmarkt")
    assert len(flat) == 1
    assert flat[0] == paths.panorama_set("korenmarkt")
    assert paths.panorama_semantics(flat[0]).exists()


def test_the_korenmarkt_walk_is_a_separate_set_from_the_korenmarkt_capture():
    """Twelve Mapillary stations against one Street View camera, same square."""
    walk = paths.panorama_stations("korenmarkt_walk", "walk_")
    assert len(walk) == 12
    assert paths.panorama_set("korenmarkt") not in walk


def test_a_fishnet_directory_names_the_mesh_it_was_cut_against():
    """The mesh in the manifest, not the mesh of the run.

    A binding is indexed by triangle with no join key, so it is only valid
    against the exact mesh it was cut on. Milan's bare directory is a 170 m cut
    while every other bare directory is a 130 m one, which is precisely why the
    manifest is the authority.
    """
    for site, expected_crop in (("korenmarkt", 130), ("milan_duomo", 170)):
        directory = paths.fishnet_dir(site)
        assert paths.fishnet_manifest(directory) is not None
        mesh = paths.fishnet_source_mesh(directory, site)
        assert mesh is not None and mesh.exists()
        assert f"_{expected_crop}m" in mesh.name


def test_the_suffixed_fishnet_directory_is_the_wider_cut():
    directory = paths.fishnet_dir("korenmarkt", 250)
    assert directory.name.endswith("_250m")
    assert directory.is_dir()
    assert any(directory.glob("*_fishnet.npz"))


def test_the_fused_station_binding_is_on_disk_for_the_sites_that_have_one():
    assert paths.site_semantics("korenmarkt", 250).exists()
    assert paths.site_semantics("korenmarkt", 250, ".json").exists()
    assert paths.walk_semantics().exists()
    assert not paths.site_semantics("krakow_rynek", 250).exists()


def test_joint_atlas_has_one_explicit_resolution():
    atlas = paths.joint_atlas("korenmarkt", 250, resolution=8)

    assert atlas.name == "joint_atlas_250m_r8.npz"


def test_atlas_artifact_path_refuses_an_empty_surface_grid():
    with pytest.raises(ValueError, match="at least 1"):
        paths.joint_atlas("korenmarkt", 250, resolution=0)


def test_the_exposure_directory_is_named_honestly_and_still_reads_the_old_one():
    """The published runs sit under a directory named for one of eleven cities.

    ``exposure_dir`` is the name a new run should use. ``exposure_file`` is what
    finds a published one, and the check that matters is that it finds a city
    that is not Korenmarkt inside the directory called ``exposure_korenmarkt``.
    """
    assert paths.exposure_dir().name == "exposure"
    assert paths.legacy_exposure_dir().name == "exposure_korenmarkt"

    found = paths.exposure_file("city250_L3_brussels_grandplace_15ghz_manifest.json")
    assert found.exists()
    assert found.parent == paths.legacy_exposure_dir()


def test_an_unwritten_exposure_file_resolves_to_the_honest_directory():
    missing = paths.exposure_file("no_such_run_15ghz_manifest.json")
    assert not missing.exists()
    assert missing.parent == paths.exposure_dir()


def test_one_run_resolves_to_its_whole_family_of_files():
    run = paths.exposure_run("city250_L3_korenmarkt_15ghz")
    assert run.complete
    assert run.locations.exists() and run.manifest.exists()
    assert json.loads(run.manifest.read_text())["site"] == "korenmarkt"
    assert {path.parent for path in (run.locations, run.manifest)} == {paths.legacy_exposure_dir()}


def test_a_run_is_read_out_of_one_directory_and_never_out_of_two():
    """The rerun case, which used to make one run object out of two runs.

    Resolving each of the six suffixes on its own is fine until a rerun streams
    rows into ``outputs/exposure`` while the published CDFs still sit in
    ``outputs/exposure_korenmarkt``. Then the object carries half of each and
    ``complete`` says True over a pair that never ran together. The rows decide,
    because the rows are the run.
    """
    published = paths.exposure_run("city250_L3_korenmarkt_15ghz")
    assert len({path.parent for path in (published.locations, published.manifest, published.spectra)}) == 1

    absent = paths.exposure_run("no_such_run_15ghz")
    assert not absent.complete
    assert {path.parent for path in (absent.locations, absent.manifest)} == {paths.exposure_dir()}


def test_the_eleven_city_sweep_left_one_run_per_city_on_disk():
    """The sweep is a real thing on disk, and this is the shape of it."""
    stems = paths.exposure_stems("city250_L3_*")
    assert len(stems) == 11
    assert all(stem.startswith("city250_L3_") for stem in stems)


def test_a_street_route_is_cached_under_its_request_key():
    routes = paths.street_routes("korenmarkt")
    assert routes
    for path in routes:
        assert path.exists()
        key = path.stem.removeprefix("korenmarkt_")
        assert paths.street_route("korenmarkt", key) == path


def test_the_tile_caches_are_two_roots_and_the_wide_one_is_partial():
    """Eight sites have a wide pull and the rest do not, which is a fact not a bug."""
    assert paths.tiles_dir("korenmarkt").is_dir()
    assert paths.tiles_dir("tokyo_hachiko", wide=True).is_dir()
    assert not paths.tiles_dir("korenmarkt", wide=True).is_dir()
