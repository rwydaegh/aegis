"""The evidence ladder, once it is a question about a site rather than a list.

The ladder used to be three hard coded Korenmarkt stems, which was correct while
Korenmarkt held the only binding and became a reason not to notice that six more
sites had acquired one. These tests pin the two things that generalisation can
break: that the published Korenmarkt stems are still the published Korenmarkt
stems, and that a site is offered a rung only when the evidence behind it would
survive the coverage ledger's own admission rule.
"""

from __future__ import annotations

import json

import numpy as np
import pytest

from semantic_twin.exposure import study as run_exposure


@pytest.fixture
def ledger(tmp_path, monkeypatch):
    """Point the ladder at a writable coverage ledger and an empty output tree."""
    monkeypatch.setattr(run_exposure, "EVIDENCE_COVERAGE", tmp_path / "evidence_coverage.json")
    monkeypatch.setattr(run_exposure, "OUTPUT", tmp_path / "out")
    (tmp_path / "out").mkdir()

    def write(*rows: dict) -> None:
        (tmp_path / "evidence_coverage.json").write_text(json.dumps({"rows": list(rows)}))

    return write


def bound_fishnet(site: str, **overrides) -> dict:
    return {
        "site": site,
        "semantic_coverage": {"mesh": "inhouse_leaf_130m.ply", "views": 24, "covered_fraction_by_area": 0.187},
        "fishnet_panoramas": ["pano_00", "pano_01"],
        "fishnet_panoramas_admitted": ["pano_00"],
    } | overrides


def only_walk(monkeypatch, *, walk: bool = True, fishnet: bool = True) -> None:
    monkeypatch.setattr(run_exposure, "site_walk_semantics", lambda site, crop_m: "binding.npz" if walk else None)
    monkeypatch.setattr(run_exposure, "site_fishnet", lambda site: ("dir", "mesh") if fishnet else None)


def test_the_published_korenmarkt_stems_survive_the_generalisation():
    # These three names are quoted in the paper and in half a dozen working
    # documents. Renaming them would orphan every one of those references.
    stems = tuple(tag for tag, _materials, _evidence in run_exposure.coverage_ladder("korenmarkt", 130))
    assert stems == tuple(stem for stem, _description in run_exposure.COVERAGE_LADDER)


def test_every_other_rung_carries_its_site_crop_and_seed_in_the_name():
    # A binding is indexed by triangle with no join key, so the crop radius is
    # part of the identity of a run, and the seed redraws the walk. A file name
    # that carried neither would be unreadable a week later.
    assert run_exposure.ladder_tag("prague_staromestske", 250, "walk", 9) == "ladder250_prague_staromestske_s9_walk"
    assert run_exposure.ladder_tag("korenmarkt", 250, "walk", 7) == "ladder250_korenmarkt_s7_walk"
    assert run_exposure.ladder_tag("korenmarkt", 130, "walk", 8) == "ladder130_korenmarkt_s8_walk"


def test_a_site_with_a_fused_binding_and_no_fishnet_climbs_two_rungs(ledger, monkeypatch):
    ledger()
    only_walk(monkeypatch, fishnet=False)
    modes = [materials for _tag, materials, _evidence in run_exposure.coverage_ladder("tokyo_hachiko", 250)]
    assert modes == ["geometric", "walk"]


def test_surfaces_cut_from_cameras_inside_the_buildings_are_not_a_rung(ledger, monkeypatch):
    # Times Square has eight fishnet views and no admitted pose. The surfaces are
    # on disk, so a rung offered on the files existing would put a square into
    # the cross site table on evidence the study elsewhere refuses.
    ledger(bound_fishnet("newyork_timessquare", fishnet_panoramas_admitted=[]))
    only_walk(monkeypatch, walk=False)
    modes = [materials for _tag, materials, _evidence in run_exposure.coverage_ladder("newyork_timessquare", 250)]
    assert modes == ["geometric"]


def test_a_fishnet_covering_nothing_is_not_a_rung_either(ledger, monkeypatch):
    coverage = {"mesh": "inhouse_leaf_130m.ply", "views": 4, "covered_fraction_by_area": 0.0}
    ledger(bound_fishnet("madrid_plazamayor", semantic_coverage=coverage))
    only_walk(monkeypatch, walk=False)
    assert [m for _t, m, _e in run_exposure.coverage_ladder("madrid_plazamayor", 250)] == ["geometric"]


def test_a_single_panorama_site_with_unattributed_views_still_climbs_it(ledger, monkeypatch):
    # Korenmarkt and Milan wrote their views with no panorama in the name. The
    # ledger declines to guess which camera they came from rather than refusing
    # them, and the ladder follows the ledger rather than inventing its own rule.
    ledger(bound_fishnet("milan_duomo", fishnet_panoramas=None, fishnet_panoramas_admitted=None))
    only_walk(monkeypatch, walk=False)
    assert [m for _t, m, _e in run_exposure.coverage_ladder("milan_duomo", 250)] == ["geometric", "semantic"]


def test_with_no_ledger_on_disk_the_fishnet_rung_is_refused(tmp_path, monkeypatch):
    # The safe failure is the one that leaves a square out of the table, not the
    # one that puts an unadmitted camera into it.
    monkeypatch.setattr(run_exposure, "EVIDENCE_COVERAGE", tmp_path / "absent.json")
    only_walk(monkeypatch, walk=False)
    assert [m for _t, m, _e in run_exposure.coverage_ladder("brussels_grandplace", 250)] == ["geometric"]


def test_a_site_the_ledger_has_never_heard_of_is_refused(ledger, monkeypatch):
    ledger(bound_fishnet("brussels_grandplace"))
    only_walk(monkeypatch, walk=False)
    assert not run_exposure.fishnet_rests_on_an_admitted_pose("krakow_rynek")


def test_the_two_refusals_a_site_can_earn_are_reported_apart(ledger, monkeypatch):
    ledger()
    monkeypatch.setattr(run_exposure, "site_fishnet", lambda site: None)
    monkeypatch.setattr(
        run_exposure, "site_walk_semantics", lambda site, crop_m: "binding.npz" if site == "korenmarkt" else None
    )

    def mesh(site, crop_m):
        if site == "milan_duomo":
            raise FileNotFoundError("no mesh")
        return "mesh.ply"

    monkeypatch.setattr(run_exposure, "site_mesh", mesh)
    admitted, refused = run_exposure.ladder_sites(("korenmarkt", "milan_duomo", "krakow_rynek"), 130)
    assert admitted == ["korenmarkt"]
    assert "no 130 m mesh" in refused["milan_duomo"]
    assert "no image binding" in refused["krakow_rynek"]


def test_a_nested_fishnet_refuses_the_site_rather_than_dropping_a_rung(ledger, monkeypatch):
    # Surfaces one level down are built and unreachable, which needs a different
    # fix from surfaces that were never built, so the site is named and not
    # quietly demoted to a two rung ladder.
    ledger()
    monkeypatch.setattr(run_exposure, "site_mesh", lambda site, crop_m: "mesh.ply")
    monkeypatch.setattr(run_exposure, "site_walk_semantics", lambda site, crop_m: None)

    def nested(site):
        raise ValueError("holds its fishnet surfaces one level down")

    monkeypatch.setattr(run_exposure, "site_fishnet", nested)
    admitted, refused = run_exposure.ladder_sites(("newyork_timessquare",), 250)
    assert admitted == []
    assert "one level down" in refused["newyork_timessquare"]


def rows_at(path, values, key="chi_rooftop"):
    with path.open("w") as handle:
        for value in values:
            row = dict.fromkeys(run_exposure.LADDER_MODELS, 1.0)
            row[key] = value
            handle.write(json.dumps(row) + "\n")


def ladder_on_disk(output, site, crop_m, seed, geometric, walk, *, covered=0.046, stations=8):
    for tag, values, fraction, provenance in (
        ("geometric", geometric, 0.0, {}),
        ("walk", walk, covered, {"stations": stations}),
    ):
        stem = f"{run_exposure.ladder_tag(site, crop_m, tag, seed)}_15ghz"
        rows_at(output / f"{stem}_locations.jsonl", values)
        (output / f"{stem}_manifest.json").write_text(
            json.dumps({"semantic_binding": {"covered_fraction_by_area": fraction, **provenance}})
        )


def test_the_shift_is_paired_standpoint_by_standpoint(ledger, monkeypatch):
    ledger()
    only_walk(monkeypatch, fishnet=False)
    base = np.array([1.0, 2.0, 4.0, 8.0])
    ladder_on_disk(run_exposure.OUTPUT, "prague_staromestske", 250, 7, base, 2.0 * base)
    path = run_exposure.coverage_report(15.0e9, site="prague_staromestske", crop_m=250, seed=7)
    walk = json.loads(path.read_text())["ladder"][1]
    assert walk["against_no_evidence"]["median_shift_db"] == pytest.approx(10.0 * np.log10(2.0))
    assert walk["against_no_evidence"]["distribution_median_shift_db"] == pytest.approx(10.0 * np.log10(2.0))
    assert walk["covered_fraction_by_area"] == pytest.approx(0.046)
    assert walk["stations"] == 8


def test_the_report_scores_all_three_illumination_models(ledger, monkeypatch):
    # The street model's Monte Carlo noise is thirty times the isotropic model's,
    # so reporting only the quiet one would flatter the result.
    ledger()
    only_walk(monkeypatch, fishnet=False)
    base = np.array([1.0, 2.0, 4.0])
    ladder_on_disk(run_exposure.OUTPUT, "mexico_zocalo", 250, 7, base, base)
    path = run_exposure.coverage_report(15.0e9, site="mexico_zocalo", crop_m=250, seed=7)
    assert set(json.loads(path.read_text())["ladder"][1]["by_model"]) == set(run_exposure.LADDER_MODELS)


def test_a_missing_rung_leaves_the_row_out_rather_than_filling_it(ledger, monkeypatch):
    ledger()
    only_walk(monkeypatch, fishnet=False)
    stem = f"{run_exposure.ladder_tag('tokyo_hachiko', 250, 'geometric', 7)}_15ghz"
    rows_at(run_exposure.OUTPUT / f"{stem}_locations.jsonl", [1.0, 2.0])
    (run_exposure.OUTPUT / f"{stem}_manifest.json").write_text(json.dumps({"semantic_binding": {}}))
    path = run_exposure.coverage_report(15.0e9, site="tokyo_hachiko", crop_m=250, seed=7)
    ladder = json.loads(path.read_text())["ladder"]
    assert [entry["run"] for entry in ladder] == [run_exposure.ladder_tag("tokyo_hachiko", 250, "geometric", 7)]


def test_the_standard_error_comes_from_the_spread_over_seeds(ledger, monkeypatch):
    ledger()
    only_walk(monkeypatch, fishnet=False)
    base = np.array([1.0, 2.0, 4.0, 8.0])
    for seed, gain in ((7, 2.0), (8, 4.0)):
        ladder_on_disk(run_exposure.OUTPUT, "madrid_plazamayor", 250, seed, base, gain * base)
        run_exposure.coverage_report(15.0e9, site="madrid_plazamayor", crop_m=250, seed=seed)
    path = run_exposure.coverage_ladder_report(["madrid_plazamayor"], 250, (7, 8), 15.0e9)
    row = json.loads(path.read_text())["rows"][0]
    shift = row["shift_db"]["chi_rooftop"]
    expected = [10.0 * np.log10(2.0), 10.0 * np.log10(4.0)]
    assert shift["per_seed_db"] == pytest.approx(expected)
    assert shift["mean_db"] == pytest.approx(np.mean(expected))
    assert shift["standard_error_db"] == pytest.approx(np.std(expected, ddof=1) / np.sqrt(2))


def test_one_seed_reports_no_standard_error_rather_than_zero(ledger, monkeypatch):
    ledger()
    only_walk(monkeypatch, fishnet=False)
    base = np.array([1.0, 2.0, 4.0])
    ladder_on_disk(run_exposure.OUTPUT, "korenmarkt", 250, 7, base, 2.0 * base)
    run_exposure.coverage_report(15.0e9, site="korenmarkt", crop_m=250, seed=7)
    path = run_exposure.coverage_ladder_report(["korenmarkt"], 250, (7,), 15.0e9)
    row = json.loads(path.read_text())["rows"][0]
    assert row["shift_db"]["chi_rooftop"]["standard_error_db"] is None
    assert "one seed" in run_exposure.ladder_markdown([row])


def test_a_bound_fraction_that_moves_with_the_seed_is_a_fault_and_says_so():
    assert run_exposure._one_value([0.046, 0.046]) == pytest.approx(0.046)
    assert run_exposure._one_value([0.046, 0.051]) == [0.046, 0.051]


def test_every_shift_in_the_table_is_quoted_beside_its_bound_area():
    # The rule this whole report exists under: a 4.6 percent bound run is a run
    # where 95.4 percent of the area still came from the orientation rule, and a
    # shift printed without that invites the reader to misread it.
    row = {
        "site": "brussels_grandplace",
        "rung": "walk",
        "covered_fraction_by_area": 0.0458,
        "stations": 8,
        "views": None,
        "locations": [80, 80],
        "seeds": [7, 8],
        "shift_db": {key: run_exposure._spread([0.1, 0.2]) for key in run_exposure.LADDER_MODELS},
    }
    line = run_exposure.ladder_markdown([row]).splitlines()[-1]
    assert "4.6 %" in line
    assert "8 stations" in line
    assert line.count("+0.150") == 3


def complete_run(output, stem, **overrides):
    (output / f"{stem}_locations.jsonl").write_text("{}\n" * 80)
    manifest = {
        "site": "korenmarkt",
        "crop_radius_m": 130,
        "locations_traced": 80,
        "trace_config": {"rays": 200_000, "seed": 7, "max_bounces": 6},
        "illumination_models": {name: {"law": model.law} for name, model in run_exposure.MODELS.items()},
    } | overrides
    (output / f"{stem}_manifest.json").write_text(json.dumps(manifest))


def test_a_run_already_on_disk_at_the_same_settings_is_not_retraced(ledger):
    complete_run(run_exposure.OUTPUT, "korenmarkt_walk_15ghz")
    assert run_exposure.reusable("korenmarkt_walk_15ghz", 80, 200_000, "korenmarkt", 130, 7, 6)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("locations_traced", 120),
        ("crop_radius_m", 250),
        ("site", "milan_duomo"),
        ("trace_config", {"rays": 400_000, "seed": 7, "max_bounces": 6}),
        ("trace_config", {"rays": 200_000, "seed": 9, "max_bounces": 6}),
        ("trace_config", {"rays": 200_000, "seed": 7, "max_bounces": 3}),
    ],
)
def test_any_setting_that_moves_the_number_forces_a_retrace(ledger, field, value):
    complete_run(run_exposure.OUTPUT, "korenmarkt_walk_15ghz", **{field: value})
    assert not run_exposure.reusable("korenmarkt_walk_15ghz", 80, 200_000, "korenmarkt", 130, 7, 6)


def test_a_run_made_under_the_superseded_illumination_law_is_refused(ledger):
    # This is the one the manifest hides. Korenmarkt's three published 130 m
    # stems are complete runs whose every other field matches, and reusing one
    # would put a different physics into a row of a cross site table silently.
    superseded = {name: {"law": "uniform_sites"} for name in run_exposure.MODELS}
    complete_run(run_exposure.OUTPUT, "korenmarkt_walk_15ghz", illumination_models=superseded)
    assert not run_exposure.reusable("korenmarkt_walk_15ghz", 80, 200_000, "korenmarkt", 130, 7, 6)


def test_a_half_written_run_is_not_reusable(ledger):
    complete_run(run_exposure.OUTPUT, "korenmarkt_walk_15ghz")
    (run_exposure.OUTPUT / "korenmarkt_walk_15ghz_locations.jsonl").write_text("{}\n" * 31)
    assert not run_exposure.reusable("korenmarkt_walk_15ghz", 80, 200_000, "korenmarkt", 130, 7, 6)


def test_a_sweep_refuses_to_overwrite_a_run_it_cannot_reuse(ledger, monkeypatch):
    # Korenmarkt at 130 m on seed 7 writes the three stems the paper quotes.
    # Without this guard, a sweep at a different standpoint count would trace
    # over them and say nothing.
    ledger()
    only_walk(monkeypatch, fishnet=False)
    monkeypatch.setattr(run_exposure, "site_mesh", lambda site, crop_m: "mesh.ply")
    monkeypatch.setattr(run_exposure, "BodyCoupler", lambda *a, **k: None)
    complete_run(run_exposure.OUTPUT, "korenmarkt_geometric_15ghz", locations_traced=120)
    (run_exposure.OUTPUT / "korenmarkt_geometric_15ghz_locations.jsonl").write_text("{}\n" * 120)
    with pytest.raises(ValueError, match="tag-suffix"):
        run_exposure.run_coverage_ladder(
            80,
            200_000,
            15.0e9,
            variant="llvm_ad_rgb",
            seeds=(7,),
            local_cells=512,
            walk_radius_m=90.0,
            walk_spacing_m=3.0,
            max_bounces=6,
            sites=("korenmarkt",),
            crop_m=130,
        )


def test_the_cross_site_report_carries_every_refusal_and_every_failure(ledger, monkeypatch):
    ledger()
    only_walk(monkeypatch, fishnet=False)
    base = np.array([1.0, 2.0, 4.0])
    ladder_on_disk(run_exposure.OUTPUT, "korenmarkt", 250, 7, base, 2.0 * base)
    run_exposure.coverage_report(15.0e9, site="korenmarkt", crop_m=250, seed=7)
    path = run_exposure.coverage_ladder_report(
        ["korenmarkt"],
        250,
        (7,),
        15.0e9,
        refused={"krakow_rynek": "no image binding at 250 m"},
        failures={"ladder250_milan_duomo_s7_walk_15ghz": "RuntimeError('datum')"},
    )
    summary = json.loads(path.read_text())
    assert summary["sites_refused"]["krakow_rynek"].startswith("no image binding")
    assert "ladder250_milan_duomo_s7_walk_15ghz" in summary["rungs_failed"]
    assert [row["site"] for row in summary["rows"]] == ["korenmarkt"]
