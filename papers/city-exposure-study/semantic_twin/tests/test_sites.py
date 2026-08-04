"""Tests for the site registry, against the literals it replaces.

Half of these read a hardcoded site list back out of the file that carries it and
check that the registry agrees with it. That is the only way to retire a fact that
was copied seven times: prove that the copies say the same thing, and where they
do not, say in a test which one is right and why.

The literals are read with :mod:`ast` rather than imported. Importing
``run_exposure`` pulls in Mitsuba, and a registry test should not need a ray
tracer to run.
"""

from __future__ import annotations

import ast
import json

import pytest

from semantic_twin import paths, sites
from semantic_twin.sites import GOOGLE_STREETVIEW, MAPILLARY, STUDY_ORDER, Site

pytestmark = pytest.mark.skipif(not paths.config_dir().is_dir(), reason="study config is not on this machine")


def literal(relative: str, name: str):
    """One module level assignment, read without executing the module."""
    tree = ast.parse((paths.root() / relative).read_text())
    for node in tree.body:
        targets = (
            node.targets if isinstance(node, ast.Assign) else [node.target] if isinstance(node, ast.AnnAssign) else []
        )
        for target in targets:
            if isinstance(target, ast.Name) and target.id == name and node.value is not None:
                return ast.literal_eval(node.value)
    raise AssertionError(f"{relative} has no module level {name}")


#: Every file carrying all eleven sites, and the order it carries them in.
ELEVEN = (
    ("FIGURES/make_eleven_cities_exposure.py", "SITES"),
    ("measure_near_clutter.py", "SITES"),
)


# ------------------------------------------------------------------ the eleven


@pytest.mark.parametrize(("relative", "name"), ELEVEN)
def test_every_eleven_site_literal_holds_the_registry(relative, name):
    assert set(literal(relative, name)) == set(Site.names())


def test_the_registry_and_the_config_directory_hold_the_same_sites():
    """Neither one is trusted alone. A config with no entry here would be invisible."""
    assert set(sites.config_names()) == set(Site.names())
    assert len(Site.all()) == 11


def test_the_study_order_is_the_one_the_reporting_files_use():
    """Four orderings exist and this is which of them is right.

    Three files carry Milan ninth, and one of them says outright that the order is
    "the study's, not alphabetical". The eleven city figure the paper prints is
    among them. Three more files sort alphabetically and one puts Korenmarkt
    first, and none of those four gives a reason, so they are re-sorts of this one
    rather than a competing claim.
    """
    assert tuple(literal("FIGURES/make_eleven_cities_exposure.py", "SITES")) == STUDY_ORDER

    panorama_routes = (paths.root() / "summarise_panorama_routes.py").read_text()
    assert "sorted(STUDY_ORDER)" in panorama_routes
    assert tuple(literal("measure_near_clutter.py", "SITES")) == tuple(sorted(STUDY_ORDER))


def test_milan_is_out_of_alphabetical_order_because_it_joins_the_sweep_late():
    """The reason for the study order, stated as the fact it rests on."""
    assert STUDY_ORDER != tuple(sorted(STUDY_ORDER))
    assert STUDY_ORDER.index("milan_duomo") > STUDY_ORDER.index("prague_staromestske")
    assert 130 not in Site.get("milan_duomo").crops
    assert all(130 in site.crops for site in Site.all() if site.name != "milan_duomo")


# ------------------------------------------------------------------ the subsets


def test_the_site_builders_derive_their_site_sets_from_the_registry():
    """Eight of eleven, and the eight are derivable rather than chosen.

    London is the one that shows the predicate is the right one. It has fifteen
    panoramas on disk and no registered pose among them, so it is in the imagery
    list and out of the evidence list.
    """
    from semantic_twin.scene import site_fishnets, site_semantics

    assert site_fishnets.SITES == tuple(site.name for site in sites.with_registered_stations())
    assert site_semantics.SITES == Site.names()
    assert "london_trafalgar" in {site.name for site in sites.with_panoramas()}
    assert "london_trafalgar" not in {site.name for site in sites.with_registered_stations()}


def test_the_fishnet_builder_routes_a_canonical_mesh_name_through_the_shared_resolver(tmp_path, monkeypatch):
    from semantic_twin.scene import site_fishnets

    expected = tmp_path / "preferred.ply"
    monkeypatch.setattr(paths, "site_mesh", lambda site, crop_m: expected)
    assert site_fishnets.site_mesh("korenmarkt", "inhouse_leaf_250m.ply") == expected


def test_the_fishnet_builder_keeps_support_for_an_arbitrary_mesh_filename(tmp_path, monkeypatch):
    from semantic_twin.scene import site_fishnets

    mesh = tmp_path / "experimental_surface.ply"
    mesh.write_bytes(b"fixture")
    paths.mesh_manifest(mesh).write_text(json.dumps({"format_version": 3}))
    monkeypatch.setattr(paths, "geometry_dir", lambda site: tmp_path)

    assert site_fishnets.site_mesh("korenmarkt", mesh.name) == mesh


def test_the_station_calibration_lists_are_the_sites_with_a_fused_binding_at_250_m():
    """Two files carry these seven and only one of them says why."""
    expected = {site.name for site in sites.with_station_binding(250)}
    assert set(literal("run_station_calibration.py", "SITES")) == expected
    assert set(literal("summarise_station_calibration.py", "SITES")) == expected
    assert len(expected) == 7


def test_the_walk_cities_figure_is_a_subset_of_the_sites_with_a_binding():
    """Six of the seven, and the missing one is not derivable from anything here.

    Milan has a fused binding and one camera, so it cannot chain into a route.
    "Enough admitted stations to chain" is a property of the route builder rather
    than of the site, so this checks containment and stops there.
    """
    figure = set(literal("FIGURES/make_walk_cities.py", "SITES"))
    assert figure < {site.name for site in sites.with_station_binding(250)}
    assert "milan_duomo" not in figure


def test_the_cross_city_sweep_gate_drops_milan_at_130_m_and_nobody_at_250_m():
    assert len(sites.with_mesh(250)) == 11
    assert {site.name for site in sites.with_mesh(130)} == set(Site.names()) - {"milan_duomo"}


# ------------------------------------------------------------------- the config


@pytest.mark.parametrize("name", STUDY_ORDER)
def test_every_site_loads_and_carries_what_its_config_says(name):
    """The load is not a copy. Every field is checked back against the JSON."""
    document = json.loads(paths.site_config(name).read_text())
    site = Site.get(name)

    assert site.name == document["name"]
    assert (site.lat, site.lon) == (document["location"]["lat"], document["location"]["lon"])
    assert site.radius_m == document["location"]["radius_m"]
    assert site.camera_ground_z_m == document["camera_ground_z_m"]
    assert site.camera_height_m == document["camera_height_m"]
    assert site.built_crop_m == document["geometry_selection"]["crop_radius_m"]
    assert site.acquisition_radius_m == document["geometry_selection"]["acquisition_radius_m"]
    assert site.frequencies_hz == tuple(document["frequencies_hz"])
    assert site.document == document


@pytest.mark.parametrize("name", STUDY_ORDER)
def test_the_enu_origin_round_trips_through_its_own_frame(name):
    """A frame that does not return its own anchor is not a frame."""
    site = Site.get(name)
    lat, lon, height = site.frame().to_llh([0.0, 0.0, 0.0])
    assert lat == pytest.approx(site.enu_origin[0], abs=1e-9)
    assert lon == pytest.approx(site.enu_origin[1], abs=1e-9)
    assert height == pytest.approx(site.enu_origin[2], abs=1e-6)


@pytest.mark.parametrize("name", STUDY_ORDER)
def test_the_site_has_a_traceable_mesh_at_the_crop_radius_its_config_declares(name):
    site = Site.get(name)
    crop = int(site.built_crop_m)
    assert crop in site.crops
    assert site.mesh(crop).exists()
    assert f"_{crop}m" in paths.root().joinpath(site.document["source_mesh"]).name


def test_two_sites_trace_a_different_file_from_the_one_their_config_names():
    """Which mesh a run traces, where the config and the resolver disagree.

    Every config's ``source_mesh`` names the unsuffixed build. At Korenmarkt and
    Milan that file is version 2, read back through Blender in single precision
    and carrying up to a metre of seaming along tile boundaries, and a ``_f64``
    rebuild sits beside it. ``paths.site_mesh`` refuses the first and takes the
    second, so the config names one file and the run traces another.

    The old test asserted ``startswith(named.stem)``, which passes for
    ``inhouse_leaf_130m_f64.ply`` against ``inhouse_leaf_130m`` and therefore
    could not see this at all. It is the same divergence that put Korenmarkt's
    material binding through a cross-mesh join, recorded as finding 8b in
    ``docs/BUGS.md``: the fishnet was cut against the version 2 file and the run
    traces the rebuild, so 13 percent of the segmented triangles are refused and
    the rest land a quarter of a metre from where they were cut.
    """
    diverging = {}
    for site in Site.all():
        named = paths.root() / site.document["source_mesh"]
        traced = site.mesh(int(site.built_crop_m))
        if traced != named:
            diverging[site.name] = (named.name, traced.name)

    assert set(diverging) == {"korenmarkt", "milan_duomo"}
    for named, traced in diverging.values():
        assert traced == named.replace(".ply", "_f64.ply")
    assert (
        json.loads(paths.mesh_manifest(paths.root() / Site.get("korenmarkt").document["source_mesh"]).read_text())[
            "format_version"
        ]
        == 2
    )


def test_an_unknown_site_names_the_ones_that_exist():
    with pytest.raises(KeyError, match="korenmarkt"):
        Site.get("ghent_vrijdagmarkt")


def test_a_registry_pointed_at_a_different_config_directory_can_be_told_to_look_again(tmp_path, monkeypatch):
    """The registry is cached for the process, and there was no way to drop it.

    A test that points ``paths.config_dir`` at a fixture tree leaves the real
    eleven cached behind it for everything that runs afterwards in the same
    session. :func:`sites.reload` is the way back, and it clears the path module's
    disk caches with it so a registry rebuilt against one ``config/`` cannot
    answer about another ``data/``.
    """
    for name in STUDY_ORDER:
        document = json.loads(paths.site_config(name).read_text())
        if name == "korenmarkt":
            document["camera_height_m"] = 99.0
        (tmp_path / f"{name}.json").write_text(json.dumps(document))

    assert Site.get("korenmarkt").camera_height_m != 99.0
    monkeypatch.setattr(paths, "config_dir", lambda: tmp_path)
    assert Site.get("korenmarkt").camera_height_m != 99.0, "the cache is what makes reload necessary"

    sites.reload()
    try:
        assert Site.get("korenmarkt").camera_height_m == 99.0
    finally:
        monkeypatch.undo()
        sites.reload()
    assert Site.get("korenmarkt").camera_height_m != 99.0


# -------------------------------------------------------------------- the names


def test_the_gallery_titles_are_square_then_city():
    """Two files carry twelve titles each and they agree character for character."""
    for relative in ("semantic_twin/viz/blender/city_gallery.py", "semantic_twin/viz/city_sheet.py"):
        titles = literal(relative, "TITLES")
        for site in Site.all():
            assert titles[site.name] == site.title


def test_the_law_ordering_labels_are_the_city_alone():
    labels = literal("run_law_ordering.py", "LABEL")
    for site in Site.all():
        assert labels[site.name] == site.label


def test_the_eleven_city_figure_labels_are_city_then_short_square():
    pretty = literal("FIGURES/make_eleven_cities_exposure.py", "PRETTY")
    for site in Site.all():
        assert pretty[site.name] == site.pretty


def test_the_short_names_agree_everywhere_except_one_squeezed_axis():
    """Ten of eleven match, and the eleventh is a figure abbreviating to fit.

    The multipath surplus figure writes "Times Sq". Two other figures write "Times
    Square", so the site keeps the whole name and squeezing it is the figure's
    business.
    """
    short = literal("FIGURES/make_multipath_surplus.py", "SHORT")
    disagreeing = {name for name, value in short.items() if value != Site.get(name).short}
    assert disagreeing == {"newyork_timessquare"}
    assert short["newyork_timessquare"] == "Times Sq"
    assert Site.get("newyork_timessquare").short == "Times Square"

    diffraction = literal("FIGURES/make_diffraction_bound_figure.py", "SITES")
    for name, value in diffraction.items():
        assert value == Site.get(name).short


def test_the_walk_cities_figure_renames_prague_and_nothing_else_does():
    """The one label contradiction in the study, recorded rather than silently picked.

    Every other file calls it Staromestske, after the square. This figure calls it
    Prague Old Town, which is the tourist name for the district. The registry
    keeps the square, because the study is about squares.
    """
    figure = literal("FIGURES/make_walk_cities.py", "SITES")
    disagreeing = {name for name, value in figure.items() if value != Site.get(name).pretty}
    assert disagreeing == {"prague_staromestske"}
    assert figure["prague_staromestske"] == "Prague Old Town"
    assert Site.get("prague_staromestske").pretty == "Prague Staromestske"


def test_the_squares_and_countries_are_what_the_screener_proposed():
    """The registry's names trace back to the study's first statement of them."""
    tree = ast.parse((paths.root() / "semantic_twin" / "screening_workflow.py").read_text())
    proposed = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "Candidate":
            key, square, country, lat, lon, _form = (ast.literal_eval(arg) for arg in node.args)
            proposed[key] = (square, country, lat, lon)

    for site in Site.all():
        square, country, lat, lon = proposed[site.name]
        assert site.square == square
        assert site.country == country
        assert (site.lat, site.lon) == (lat, lon)


# ------------------------------------------------------------------ the imagery


def test_korenmarkt_is_the_only_site_with_two_providers():
    """The undocumented fact this registry exists to write down.

    Every single panorama site is Google Street View. The one multi station set,
    the twelve station walk that carries the SAM 3 binding, is Mapillary. No
    document in the study says the two arms use two providers.
    """
    mapillary = {site.name for site in Site.all() if any(entry.provider == MAPILLARY for entry in site.imagery)}
    assert mapillary == {"korenmarkt"}

    walk = Site.get("korenmarkt").imagery_by_role("walk")
    assert len(walk) == 1 and walk[0].provider == MAPILLARY
    assert len(Site.get("korenmarkt").stations("walk")) == 12


def test_every_declared_imagery_set_is_on_disk_and_its_provider_matches_the_metadata():
    """The declaration is checked against the evidence rather than believed.

    A Street View camera's metadata carries ``panoId`` and a street address. A
    Mapillary one carries ``computed_geometry``, the position their structure from
    motion solved for. That is how the providers were told apart in the first
    place, so it is how the declaration is tested.
    """
    for site in Site.all():
        for entry in site.imagery:
            stations = paths.panorama_stations(entry.directory, entry.station_prefix)
            assert stations, f"{site.name}: {entry.directory} has no camera directories"
            document = json.loads((stations[0] / "metadata.json").read_text())
            if entry.provider == GOOGLE_STREETVIEW:
                assert "panoId" in document and "computed_geometry" not in document
            else:
                assert "computed_geometry" in document and "panoId" not in document


def test_the_two_sites_with_no_photographs_are_krakow_and_toulouse():
    """Which is why they carry no image evidence anywhere downstream."""
    assert {site.name for site in Site.all() if not site.has_panoramas} == {"krakow_rynek", "toulouse_capitole"}


# ----------------------------------------------------------------- the evidence


def test_the_bare_fishnet_directory_belongs_to_the_sites_first_build():
    """Milan's is a 170 m cut and everyone else's is 130 m, and neither is suffixed."""
    assert Site.get("korenmarkt").fishnet_dir(130) == paths.fishnet_dir("korenmarkt")
    assert Site.get("milan_duomo").fishnet_dir(170) == paths.fishnet_dir("milan_duomo")
    assert Site.get("milan_duomo").fishnet_dir(250).name.endswith("_250m")


def test_korenmarkt_keeps_its_mapillary_binding_at_its_first_crop():
    """Every published walk number was measured on that file, so it wins at 130 m."""
    assert Site.get("korenmarkt").station_binding(130) == paths.walk_semantics()
    assert Site.get("korenmarkt").station_binding(250) == paths.site_semantics("korenmarkt", 250)


def test_a_site_with_no_binding_says_none_rather_than_handing_back_a_missing_path():
    assert Site.get("krakow_rynek").station_binding(250) is None
    assert not Site.get("krakow_rynek").has_station_binding(250)
