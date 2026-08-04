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
from dataclasses import fields
from types import SimpleNamespace

import numpy as np
import pytest

from semantic_twin.exposure import study as run_exposure
from semantic_twin.exposure.execution import ExecutionConfig
from semantic_twin.exposure.reuse import model_identity
from semantic_twin.exposure.sweeps import LadderSweepConfig
from semantic_twin.runconfig import NextEventConfig, RunConfig


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


def complete_result_row(index, models):
    row = {
        "index": index,
        "x": float(index),
        "y": 0.0,
        "z": 1.5,
        "ground_z_m": 0.0,
        "seconds": 1.0,
        "sky_fraction": 0.25,
        "mean_bounces": 1.0,
        "mean_excess_delay_ns": 2.0,
        "escaped_fraction": 0.5,
        "truncated_throughput_share": 0.01,
    }
    for name in models:
        row[f"chi_{name}"] = 0.2
        row[f"chi_{name}_direct"] = 0.1
        for suffix in (
            "reference_s0_w_m2",
            "arriving_power_density_w_m2",
            "susceptibility",
            "peak_sab_w_m2",
            "mean_sab_w_m2",
            "absorbed_power_w",
            "sar_wb_w_kg",
        ):
            row[f"{name}_{suffix}"] = 0.1
    return row


def write_complete_spectra(path, indices, local_cells):
    local_grid = np.zeros((local_cells, 3))
    local_grid[:, 2] = 1.0
    np.savez(
        path,
        index=np.asarray(indices),
        rho_rooftop=np.zeros((len(indices), local_cells)),
        local_grid=local_grid,
        solid_angle=np.asarray(4.0 * np.pi / local_cells),
    )


def complete_run(output, stem, **overrides):
    rows = "".join(json.dumps(complete_result_row(index, run_exposure.MODELS)) + "\n" for index in range(80))
    (output / f"{stem}_locations.jsonl").write_text(rows)
    write_complete_spectra(output / f"{stem}_spectra.npz", np.arange(80), replay_config().local_cells)
    manifest = {
        "site": "korenmarkt",
        "crop_radius_m": 130,
        "locations_requested": 80,
        "locations_traced": 80,
        "walk": {"candidates_after_clearance": 100},
        "trace_config": {"rays": 200_000, "seed": 7, "max_bounces": 6},
        "illumination_models": {name: model_identity(model) for name, model in run_exposure.MODELS.items()},
    } | overrides
    (output / f"{stem}_manifest.json").write_text(json.dumps(manifest))


def replay_config() -> RunConfig:
    return RunConfig(
        site="korenmarkt",
        crop_m=130,
        law="band",
        models=tuple(run_exposure.MODELS),
        estimator="escape",
        next_event=None,
        walk="grid",
        locations=80,
        max_bounces=6,
        roulette_start=4,
        materials="walk",
        rays=200_000,
        seed=7,
        tag="korenmarkt_walk",
    )


def test_a_run_already_on_disk_at_the_same_settings_is_not_retraced(ledger):
    complete_run(run_exposure.OUTPUT, "korenmarkt_walk_15ghz")
    assert run_exposure.reusable(replay_config())


def complete_identified_run(output, recorded: RunConfig, *, path_config: RunConfig | None = None):
    path_config = path_config or recorded
    stem = f"{path_config.tag}_{path_config.frequency_ghz:g}ghz"
    rows = "".join(
        json.dumps(complete_result_row(index, recorded.models)) + "\n" for index in range(recorded.locations)
    )
    (output / f"{stem}_locations.jsonl").write_text(rows)
    write_complete_spectra(output / f"{stem}_spectra.npz", np.arange(recorded.locations), recorded.local_cells)
    models = {name: model_identity(run_exposure.MODELS[name]) for name in recorded.models}
    manifest = {
        "locations_requested": recorded.locations,
        "locations_traced": recorded.locations,
        "walk": {"candidates_after_clearance": recorded.locations + 20},
        "illumination_models": models,
        "run_digest": recorded.digest(),
        "run": recorded.as_dict(),
    }
    (output / f"{stem}_manifest.json").write_text(json.dumps(manifest))


IDENTITY_CHANGES = {
    "site": "milan_duomo",
    "crop_m": 250,
    "law": "roofline",
    "models": ("rooftop",),
    "estimator": "next_event",
    "walk": "route",
    "walk_path": "street",
    "walk_radius_m": 75.0,
    "walk_spacing_m": 2.5,
    "walk_stride_m": 4.0,
    "head_height_m": 1.72,
    "locations": 81,
    "frequency_hz": 28.0e9,
    "max_bounces": 5,
    "roulette_start": 3,
    "roulette_floor": 0.2,
    "ray_epsilon_m": 0.004,
    "range_weighted_escape": True,
    "materials": "geometric",
    "walk_npz": "outputs/another_walk.npz",
    "rays": 100_000,
    "batch": 100_000,
    "local_cells": 256,
    "exit_bands": 12,
    "seed": 9,
    "variant": "cuda_ad_rgb",
}


def test_the_identity_change_table_covers_every_run_field_that_can_change_this_escape_run():
    identity_fields = {field.name for field in fields(RunConfig)} - {"tag", "next_event"}
    assert set(IDENTITY_CHANGES) == identity_fields


@pytest.mark.parametrize(("field", "value"), IDENTITY_CHANGES.items())
def test_every_run_identity_field_prevents_reuse(ledger, field, value):
    recorded = replay_config()
    requested = recorded.replace(**{field: value})
    complete_identified_run(run_exposure.OUTPUT, recorded, path_config=requested)

    assert not run_exposure.reusable(requested)


@pytest.mark.parametrize("field", [field.name for field in fields(NextEventConfig)])
def test_every_nested_next_event_field_prevents_reuse(ledger, field):
    recorded = replay_config().replace(estimator="next_event")
    changed_source_set = NextEventConfig(**(recorded.next_event.__dict__ | {field: 2}))
    requested = recorded.replace(next_event=changed_source_set)
    complete_identified_run(run_exposure.OUTPUT, recorded, path_config=requested)

    assert not run_exposure.reusable(requested)


@pytest.mark.parametrize("models", [("rooftop",), ("isotropic", "rooftop")])
def test_an_exact_model_subset_is_reusable(ledger, models):
    config = replay_config().replace(models=models)
    complete_identified_run(run_exposure.OUTPUT, config)

    assert run_exposure.reusable(config)


def test_a_multi_model_run_keeps_the_deliberate_rooftop_only_spectrum(ledger):
    config = replay_config().replace(models=("isotropic", "rooftop", "street_small_cell"))
    complete_identified_run(run_exposure.OUTPUT, config)
    with np.load(run_exposure.OUTPUT / "korenmarkt_walk_15ghz_spectra.npz") as spectra:
        names = spectra.files

    assert names == ["index", "rho_rooftop", "local_grid", "solid_angle"]
    assert run_exposure.reusable(config)


def test_the_output_tag_is_a_label_and_does_not_change_reuse_identity(ledger):
    recorded = replay_config()
    requested = recorded.replace(tag="copied_run")
    complete_identified_run(run_exposure.OUTPUT, recorded, path_config=requested)

    assert run_exposure.reusable(requested)


def test_a_tampered_run_digest_is_not_reusable(ledger):
    config = replay_config()
    complete_identified_run(run_exposure.OUTPUT, config)
    manifest = run_exposure.OUTPUT / "korenmarkt_walk_15ghz_manifest.json"
    document = json.loads(manifest.read_text())
    document["run_digest"] = "not-the-run"
    manifest.write_text(json.dumps(document))

    assert not run_exposure.reusable(config)


def test_a_modern_manifest_missing_a_default_run_field_is_not_reusable(ledger):
    config = replay_config()
    complete_identified_run(run_exposure.OUTPUT, config)
    manifest = run_exposure.OUTPUT / "korenmarkt_walk_15ghz_manifest.json"
    document = json.loads(manifest.read_text())
    del document["run"]["batch"]
    manifest.write_text(json.dumps(document))

    assert not run_exposure.reusable(config)


@pytest.mark.parametrize("field", ["elevation_min_deg", "height_band_m", "range_band_m"])
def test_a_numeric_source_model_change_prevents_reuse(ledger, monkeypatch, field):
    config = replay_config()
    complete_identified_run(run_exposure.OUTPUT, config)
    model = run_exposure.MODELS["rooftop"]
    values = {
        "elevation_min_deg": model.elevation_min_deg + 1.0,
        "elevation_max_deg": model.elevation_max_deg,
        "law": model.law,
        "height_band_m": (12.0, 42.0) if field == "height_band_m" else model.height_band_m,
        "range_band_m": (30.0, 240.0) if field == "range_band_m" else model.range_band_m,
    }
    if field != "elevation_min_deg":
        values["elevation_min_deg"] = model.elevation_min_deg
    monkeypatch.setitem(run_exposure.MODELS, "rooftop", SimpleNamespace(**values))

    assert not run_exposure.reusable(config)


def test_a_truncated_final_json_row_is_not_reusable(ledger):
    config = replay_config()
    complete_identified_run(run_exposure.OUTPUT, config)
    rows = run_exposure.OUTPUT / "korenmarkt_walk_15ghz_locations.jsonl"
    rows.write_text(rows.read_text().rsplit("\n", 2)[0] + '\n{"index":')

    assert not run_exposure.reusable(config)


def test_a_coordinated_short_modern_run_is_not_reusable(ledger):
    config = replay_config()
    complete_identified_run(run_exposure.OUTPUT, config)
    stem = run_exposure.OUTPUT / "korenmarkt_walk_15ghz"
    manifest_path = stem.with_name(f"{stem.name}_manifest.json")
    document = json.loads(manifest_path.read_text())
    document["locations_traced"] = 79
    manifest_path.write_text(json.dumps(document))
    rows_path = stem.with_name(f"{stem.name}_locations.jsonl")
    rows_path.write_text("\n".join(rows_path.read_text().splitlines()[:79]) + "\n")
    write_complete_spectra(stem.with_name(f"{stem.name}_spectra.npz"), np.arange(79), config.local_cells)

    assert not run_exposure.reusable(config)


def test_a_walk_shorter_than_the_requested_pilot_remains_reusable(ledger):
    config = replay_config()
    complete_identified_run(run_exposure.OUTPUT, config)
    stem = run_exposure.OUTPUT / "korenmarkt_walk_15ghz"
    manifest_path = stem.with_name(f"{stem.name}_manifest.json")
    document = json.loads(manifest_path.read_text())
    document["walk"]["candidates_after_clearance"] = 63
    document["locations_traced"] = 63
    manifest_path.write_text(json.dumps(document))
    rows_path = stem.with_name(f"{stem.name}_locations.jsonl")
    rows_path.write_text("\n".join(rows_path.read_text().splitlines()[:63]) + "\n")
    write_complete_spectra(stem.with_name(f"{stem.name}_spectra.npz"), np.arange(63), config.local_cells)

    assert run_exposure.reusable(config)


def test_a_malformed_manifest_is_not_reusable(ledger):
    config = replay_config()
    complete_identified_run(run_exposure.OUTPUT, config)
    manifest = run_exposure.OUTPUT / "korenmarkt_walk_15ghz_manifest.json"
    manifest.write_text("{not json")

    assert not run_exposure.reusable(config)


@pytest.mark.parametrize(
    "damage",
    [
        "missing",
        "short_index",
        "short_rho",
        "wrong_rho_width",
        "missing_grid",
        "wrong_grid",
        "nonscalar_solid_angle",
    ],
)
def test_missing_or_short_spectra_are_not_reusable(ledger, damage):
    config = replay_config()
    complete_identified_run(run_exposure.OUTPUT, config)
    spectra = run_exposure.OUTPUT / "korenmarkt_walk_15ghz_spectra.npz"
    if damage == "missing":
        spectra.unlink()
    elif damage == "short_index":
        write_complete_spectra(spectra, np.arange(79), config.local_cells)
    elif damage == "short_rho":
        np.savez(
            spectra,
            index=np.arange(80),
            rho_rooftop=np.zeros((79, config.local_cells)),
            local_grid=np.zeros((config.local_cells, 3)),
            solid_angle=0.1,
        )
    elif damage == "wrong_rho_width":
        np.savez(
            spectra,
            index=np.arange(80),
            rho_rooftop=np.zeros((80, config.local_cells - 1)),
            local_grid=np.zeros((config.local_cells, 3)),
            solid_angle=0.1,
        )
    elif damage == "missing_grid":
        np.savez(
            spectra,
            index=np.arange(80),
            rho_rooftop=np.zeros((80, config.local_cells)),
            solid_angle=0.1,
        )
    elif damage == "wrong_grid":
        np.savez(
            spectra,
            index=np.arange(80),
            rho_rooftop=np.zeros((80, config.local_cells)),
            local_grid=np.zeros((config.local_cells, 2)),
            solid_angle=0.1,
        )
    else:
        np.savez(
            spectra,
            index=np.arange(80),
            rho_rooftop=np.zeros((80, config.local_cells)),
            local_grid=np.zeros((config.local_cells, 3)),
            solid_angle=np.array([0.1]),
        )

    assert not run_exposure.reusable(config)


@pytest.mark.parametrize(
    "missing",
    ["x", "sky_fraction", "chi_rooftop", "chi_rooftop_direct", "rooftop_peak_sab_w_m2"],
)
def test_a_row_missing_a_required_result_is_not_reusable(ledger, missing):
    config = replay_config()
    complete_identified_run(run_exposure.OUTPUT, config)
    rows_path = run_exposure.OUTPUT / "korenmarkt_walk_15ghz_locations.jsonl"
    rows = [json.loads(line) for line in rows_path.read_text().splitlines()]
    del rows[37][missing]
    rows_path.write_text("".join(json.dumps(row) + "\n" for row in rows))

    assert not run_exposure.reusable(config)


@pytest.mark.parametrize(
    "damage",
    ["duplicate", "spectrum_order", "coordinated_unsorted", "spectrum_float", "float_index"],
)
def test_row_and_spectrum_indices_must_match_exactly(ledger, damage):
    config = replay_config()
    complete_identified_run(run_exposure.OUTPUT, config)
    rows_path = run_exposure.OUTPUT / "korenmarkt_walk_15ghz_locations.jsonl"
    spectra_path = run_exposure.OUTPUT / "korenmarkt_walk_15ghz_spectra.npz"
    if damage == "duplicate":
        rows = [json.loads(line) for line in rows_path.read_text().splitlines()]
        rows[40]["index"] = rows[39]["index"]
        rows_path.write_text("".join(json.dumps(row) + "\n" for row in rows))
    elif damage == "spectrum_order":
        indices = np.arange(80)
        indices[[20, 21]] = indices[[21, 20]]
        write_complete_spectra(spectra_path, indices, config.local_cells)
    elif damage == "coordinated_unsorted":
        rows = [json.loads(line) for line in rows_path.read_text().splitlines()]
        rows[20], rows[21] = rows[21], rows[20]
        rows_path.write_text("".join(json.dumps(row) + "\n" for row in rows))
        indices = np.arange(80)
        indices[[20, 21]] = indices[[21, 20]]
        write_complete_spectra(spectra_path, indices, config.local_cells)
    elif damage == "spectrum_float":
        write_complete_spectra(spectra_path, np.arange(80, dtype=float), config.local_cells)
    else:
        rows = [json.loads(line) for line in rows_path.read_text().splitlines()]
        rows[40]["index"] = 40.0
        rows_path.write_text("".join(json.dumps(row) + "\n" for row in rows))

    assert not run_exposure.reusable(config)


@pytest.mark.parametrize(
    "damage",
    ["row_null", "row_nan", "rho_nan", "negative_rho", "grid_string", "zero_grid", "wrong_solid_angle"],
)
def test_results_and_spectra_must_be_finite_numbers(ledger, damage):
    config = replay_config()
    complete_identified_run(run_exposure.OUTPUT, config)
    rows_path = run_exposure.OUTPUT / "korenmarkt_walk_15ghz_locations.jsonl"
    spectra_path = run_exposure.OUTPUT / "korenmarkt_walk_15ghz_spectra.npz"
    if damage.startswith("row"):
        rows = [json.loads(line) for line in rows_path.read_text().splitlines()]
        rows[13]["chi_rooftop"] = None if damage == "row_null" else float("nan")
        rows_path.write_text("".join(json.dumps(row) + "\n" for row in rows))
    elif damage in ("rho_nan", "negative_rho"):
        rho = np.zeros((80, config.local_cells))
        rho[13, 7] = np.nan if damage == "rho_nan" else -0.01
        local_grid = np.zeros((config.local_cells, 3))
        local_grid[:, 2] = 1.0
        np.savez(
            spectra_path,
            index=np.arange(80),
            rho_rooftop=rho,
            local_grid=local_grid,
            solid_angle=4.0 * np.pi / config.local_cells,
        )
    elif damage == "grid_string":
        np.savez(
            spectra_path,
            index=np.arange(80),
            rho_rooftop=np.zeros((80, config.local_cells)),
            local_grid=np.full((config.local_cells, 3), "north"),
            solid_angle=4.0 * np.pi / config.local_cells,
        )
    elif damage == "zero_grid":
        np.savez(
            spectra_path,
            index=np.arange(80),
            rho_rooftop=np.zeros((80, config.local_cells)),
            local_grid=np.zeros((config.local_cells, 3)),
            solid_angle=4.0 * np.pi / config.local_cells,
        )
    else:
        local_grid = np.zeros((config.local_cells, 3))
        local_grid[:, 2] = 1.0
        np.savez(
            spectra_path,
            index=np.arange(80),
            rho_rooftop=np.zeros((80, config.local_cells)),
            local_grid=local_grid,
            solid_angle=0.1,
        )

    assert not run_exposure.reusable(config)


@pytest.mark.parametrize("count", [80.0, True, -1])
def test_locations_traced_is_an_exact_nonnegative_integer(ledger, count):
    config = replay_config()
    complete_identified_run(run_exposure.OUTPUT, config)
    manifest = run_exposure.OUTPUT / "korenmarkt_walk_15ghz_manifest.json"
    document = json.loads(manifest.read_text())
    document["locations_traced"] = count
    manifest.write_text(json.dumps(document))

    assert not run_exposure.reusable(config)


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
    assert not run_exposure.reusable(replay_config())


def test_a_run_made_under_the_superseded_illumination_law_is_refused(ledger):
    # This is the one the manifest hides. Korenmarkt's three published 130 m
    # stems are complete runs whose every other field matches, and reusing one
    # would put a different physics into a row of a cross site table silently.
    superseded = {name: {"law": "uniform_sites"} for name in run_exposure.MODELS}
    complete_run(run_exposure.OUTPUT, "korenmarkt_walk_15ghz", illumination_models=superseded)
    assert not run_exposure.reusable(replay_config())


def test_a_half_written_run_is_not_reusable(ledger):
    complete_run(run_exposure.OUTPUT, "korenmarkt_walk_15ghz")
    (run_exposure.OUTPUT / "korenmarkt_walk_15ghz_locations.jsonl").write_text("{}\n" * 31)
    assert not run_exposure.reusable(replay_config())


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
            replay_config().replace(tag="", materials="geometric"),
            ExecutionConfig(),
            LadderSweepConfig(("korenmarkt",), (7,)),
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
