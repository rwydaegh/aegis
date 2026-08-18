"""Two imagery providers, checked against the photographs actually on disk.

The registry in :mod:`semantic_twin.sites` claims a provider per imagery set.
Until now nothing checked that claim, and it was arrived at by reading metadata
keys off the disk once. So these tests read the same disk again and make the
claim falsifiable: a Street View capture carries ``panoId`` and a Mapillary one
carries ``computed_geometry``, and no record carries both.

``data/panoramas`` is gitignored, so the disk-facing tests skip rather than fail
where it is absent. The registry and protocol tests do not need it.
"""

from __future__ import annotations

import json
import pathlib

import pytest

from semantic_twin import paths, sites
from semantic_twin.acquire import PanoramaSource, load_support_mesh, source_for, source_for_site
from semantic_twin.acquire.mapillary import Mapillary
from semantic_twin.acquire.streetview import GoogleStreetView

IMPLEMENTATIONS = [GoogleStreetView(), Mapillary()]

STREETVIEW_RECORD = {
    "panoId": "sqF_X7Lx3QDikLALUtGhMA",
    "lat": 45.464206509962104,
    "lng": 9.190013102997568,
    "heading": 359.6104,
    "tilt": 85.794815,
    "roll": 354.46985,
}

MAPILLARY_RECORD = {
    "id": "986493819697753",
    "is_pano": True,
    "computed_geometry": {"coordinates": [3.7220, 51.0550]},
    "computed_compass_angle": 12.0,
    "computed_rotation": [0.11427616920294, 2.050205324748, -2.1771815255044],
}

SCENE = {"enu_origin": {"lat": 51.0, "lon": 3.0}, "camera_ground_z_m": 10.0, "camera_height_m": 2.0}


def test_support_mesh_uses_the_version_gated_resolver(monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path) -> None:
    mesh = tmp_path / "traceable.ply"
    seen: list[tuple[str, int, pathlib.Path | None]] = []

    def resolve(site: str, crop_m: int, root_dir: pathlib.Path | None = None) -> pathlib.Path:
        seen.append((site, crop_m, root_dir))
        return mesh

    monkeypatch.setattr(paths, "site_mesh", resolve)
    monkeypatch.setattr("semantic_twin.scene.mesh.read_binary_ply", lambda path: (path, path))
    scene = {
        "name": "korenmarkt",
        "source_mesh": "data/geometry/korenmarkt/inhouse_leaf_130m.ply",
        "geometry_selection": {"crop_radius_m": 130.0},
    }

    assert load_support_mesh(scene, root=tmp_path) == (mesh, mesh)
    assert seen == [("korenmarkt", 130, tmp_path)]


def station_records(entry: sites.ImagerySet) -> list[tuple[pathlib.Path, dict]]:
    """Every camera of one set that has a metadata file, with its record."""
    found = []
    for station in paths.panorama_stations(entry.directory, entry.station_prefix):
        path = station / "metadata.json"
        if path.exists():
            found.append((station, json.loads(path.read_text())))
    return found


# --- the two providers are not interchangeable ---------------------------------


@pytest.mark.parametrize("source", IMPLEMENTATIONS, ids=lambda s: s.provider)
def test_both_providers_satisfy_the_one_interface(source: PanoramaSource) -> None:
    """Add a third provider and it inherits this, which is the point of a protocol."""
    assert isinstance(source, PanoramaSource)
    # The name an implementation answers to has to be the name the registry
    # files sites under, or a site config resolves to nothing.
    assert type(source_for(source.provider)) is type(source)
    in_use = {entry.provider for entries in sites.IMAGERY.values() for entry in entries}
    assert source.provider in in_use


def test_neither_provider_reports_an_assumed_orientation_as_a_measured_one() -> None:
    """A missing solution and a level camera look identical in the numbers.

    Both arrive as tilt 90 and roll 0. Three of the five sites screened for this
    study reported exactly that, and they are photospheres with no pose solution
    behind them, so a consumer that reads the numbers alone is trusting a
    default it was never given.
    """
    streetview, mapillary = GoogleStreetView(), Mapillary()
    assert streetview.orientation_source({"tilt": 90.0, "roll": 0.0}).startswith("degenerate")
    assert streetview.orientation_source({"heading": 12.0}).startswith("absent")
    assert mapillary.orientation_source({"computed_compass_angle": 12.0}).startswith("absent")

    assert "tilt and roll" in streetview.orientation_source(STREETVIEW_RECORD)
    assert "computed_rotation" in mapillary.orientation_source(MAPILLARY_RECORD)


def test_only_mapillary_carries_a_solved_gravity_into_the_pose() -> None:
    """Mapillary's structure from motion solves for gravity and publishes it.

    Street View publishes tilt and roll too, so the difference is not that one
    has orientation. It is that Mapillary's came out of a reconstruction and can
    be argued with, while three of five Street View sites report the default.
    Measured tilts on the Korenmarkt walk reach 20.7 degrees off gravity.
    """
    levelled = dict(MAPILLARY_RECORD)
    levelled.pop("computed_rotation")
    with_gravity = Mapillary().pose(MAPILLARY_RECORD, SCENE)
    without = Mapillary().pose(levelled, SCENE)
    assert (without.tilt_deg, without.roll_deg) == (90.0, 0.0)
    assert abs(with_gravity.tilt_deg - 90.0) > 1.0


def test_each_provider_reads_its_own_identifier_and_would_fail_on_the_other() -> None:
    assert GoogleStreetView().image_id(STREETVIEW_RECORD) == "sqF_X7Lx3QDikLALUtGhMA"
    assert Mapillary().image_id(MAPILLARY_RECORD) == "986493819697753"
    with pytest.raises(KeyError):
        GoogleStreetView().image_id(MAPILLARY_RECORD)
    with pytest.raises(KeyError):
        Mapillary().image_id(STREETVIEW_RECORD)


# --- the registry resolves, and there is only one registry ---------------------


def test_the_walk_that_carries_the_material_binding_is_the_mapillary_one() -> None:
    """Korenmarkt is the only site whose sets do not share a provider.

    Its stations are Street View. Its twelve station walk and its three view
    reconstruction set are Mapillary, and the walk is the one every published
    material binding was measured on.
    """
    assert source_for_site("korenmarkt", "stations").provider == sites.GOOGLE_STREETVIEW
    assert source_for_site("korenmarkt", "walk").provider == sites.MAPILLARY
    assert source_for_site("korenmarkt", "multiview").provider == sites.MAPILLARY


def test_every_other_site_with_photographs_is_street_view() -> None:
    others = {
        site.name: {entry.provider for entry in site.imagery}
        for site in sites.with_panoramas()
        if site.name != "korenmarkt"
    }
    assert others
    assert set().union(*others.values()) == {sites.GOOGLE_STREETVIEW}


def test_new_route_extension_sites_name_their_acquired_provider() -> None:
    for name in ("krakow_rynek", "toulouse_capitole"):
        assert source_for_site(name).provider == sites.GOOGLE_STREETVIEW


def test_an_unknown_provider_names_the_two_that_exist() -> None:
    with pytest.raises(KeyError, match="streetview"):
        source_for("bing")


# --- against the disk ----------------------------------------------------------


def test_every_imagery_set_holds_the_records_its_provider_writes() -> None:
    """The registry's provider claim, checked against the metadata on disk.

    ``panoId`` and ``computed_geometry`` are the tells. They do not co-occur, so
    a set filed under the wrong provider fails here rather than surviving as an
    undocumented accident the way the split did until now.
    """
    checked = 0
    for site in sites.with_panoramas():
        for entry in site.imagery:
            records = station_records(entry)
            if not records:
                continue
            source = source_for(entry.provider)
            for station, metadata in records:
                assert source.image_id(metadata), station
                if entry.provider == sites.GOOGLE_STREETVIEW:
                    assert "computed_geometry" not in metadata, station
                else:
                    assert "panoId" not in metadata, station
                checked += 1
    if not checked:
        pytest.skip("data/panoramas is gitignored and absent here")
    assert checked >= 80


def test_a_camera_directory_is_named_for_the_identifier_its_provider_issued() -> None:
    """The one join between a directory on disk and a provider's own key.

    ``fetch_site_panoramas`` names a directory for the first sixteen characters
    of the identifier, which is what lets a re-run match a panorama it already
    holds. Nothing else on disk records which provider took a photograph.
    """
    checked = 0
    for site in sites.with_panoramas():
        for entry in site.imagery:
            if not entry.station_prefix:
                # The two sites acquired before the cohort fetcher put one
                # camera's files straight in the set directory, which is named
                # for the site and carries no identifier.
                continue
            source = source_for(entry.provider)
            for station, metadata in station_records(entry):
                assert station.name.endswith(source.image_id(metadata)[:16]), station
                checked += 1
    if not checked:
        pytest.skip("data/panoramas is gitignored and absent here")
    assert checked >= 80
