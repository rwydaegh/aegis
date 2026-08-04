from __future__ import annotations

import json
from types import SimpleNamespace

import numpy as np
import pytest

import run_exposure
from semantic_twin.exposure.execution import (
    ExecutionConfig,
    MaterialBinding,
    OutputFiles,
    PreparedRun,
    PreparedScene,
    _build_walk,
    _manifest,
    _transport_provenance,
    _trace_config,
    _trace_rows,
    _validate_run,
    execute,
)
from semantic_twin.exposure.sweeps import LadderSweepConfig, SweepEnvironment, run_coverage_ladder
from semantic_twin.runconfig import RunConfig
from semantic_twin.transport.tracer import TraceConfig


def escape_config(**changes) -> RunConfig:
    config = RunConfig(
        site="korenmarkt",
        law="band",
        models=("isotropic", "rooftop", "street_small_cell"),
        estimator="escape",
        next_event=None,
        walk="grid",
        materials="geometric",
        tag="trial",
    )
    return config.replace(**changes)


def test_the_legacy_driver_builds_the_live_run_config_without_changing_its_defaults():
    config, execution = run_exposure._escape_config(
        0,
        200_000,
        15.0e9,
        variant="llvm_ad_rgb",
        seed=7,
        tag="korenmarkt",
        local_cells=512,
        walk_radius_m=90.0,
        walk_spacing_m=3.0,
        max_bounces=6,
        materials="geometric",
        site="korenmarkt",
        crop_m=250,
    )

    assert config.locations == 0
    assert config.models == tuple(run_exposure.MODELS)
    assert config.estimator == "escape"
    assert config.walk == "grid"
    assert config.crop_m == 250
    assert config.max_bounces == 6
    assert config.roulette_start == 4
    assert config.transport_kernel == "numpy"
    assert config.head_height_m == 1.5
    assert execution == ExecutionConfig()


def test_explicit_none_keeps_the_legacy_tracer_default_at_a_larger_bounce_budget():
    options = {
        "variant": "llvm_ad_rgb",
        "seed": 7,
        "tag": "korenmarkt",
        "local_cells": 512,
        "walk_radius_m": 90.0,
        "walk_spacing_m": 3.0,
        "max_bounces": 6,
        "materials": "geometric",
        "roulette_start": None,
    }

    config, _execution = run_exposure._escape_config(1, 100, 15.0e9, **options)

    assert config.roulette_start == 4
    assert RunConfig(site="korenmarkt", max_bounces=6).effective_roulette_start == 7


@pytest.mark.parametrize(
    ("config", "message"),
    [
        (RunConfig(site="korenmarkt"), "band/escape/grid"),
        (escape_config(models=("isotropic",)), "requires the rooftop model"),
        (escape_config(models=("rooftop", "invented")), "unknown illumination models: invented"),
        (escape_config(transport_kernel="drjit"), "transport_kernel='drjit'"),
    ],
)
def test_executor_rejects_unsupported_configs_before_it_creates_output(tmp_path, config, message):
    output = tmp_path / "output"
    environment = SimpleNamespace(
        output=output,
        models={"isotropic": object(), "rooftop": object(), "street_small_cell": object()},
    )

    with pytest.raises(ValueError, match=message):
        execute(config, ExecutionConfig(), environment)

    assert not output.exists()


@pytest.mark.parametrize("models", [("rooftop",), ("isotropic", "rooftop")])
def test_executor_accepts_supported_model_subsets(models):
    available = {"isotropic": object(), "rooftop": object(), "street_small_cell": object()}
    _validate_run(escape_config(models=models), available)


def test_every_trace_field_in_run_config_reaches_the_tracer():
    run = escape_config(
        frequency_hz=28.0e9,
        rays=123,
        local_cells=32,
        exit_bands=7,
        max_bounces=6,
        roulette_start=3,
        roulette_floor=0.2,
        ray_epsilon_m=0.004,
        range_weighted_escape=True,
        seed=19,
        batch=41,
    )

    traced = _trace_config(run, SimpleNamespace(trace_config_type=TraceConfig))

    assert traced.as_dict() == {
        "frequency_hz": 28.0e9,
        "rays": 123,
        "local_cells": 32,
        "exit_bands": 7,
        "max_bounces": 6,
        "roulette_start": 3,
        "roulette_floor": 0.2,
        "ray_epsilon_m": 0.004,
        "range_weighted_escape": True,
        "seed": 19,
        "batch": 41,
    }


def test_head_height_in_run_config_reaches_walk_construction():
    received = {}

    def build_walk(geometry, **options):
        received.update(options)
        return object()

    run = escape_config(head_height_m=1.72)
    replay = SimpleNamespace(walk_probe_z_m=None)
    scene = SimpleNamespace(geometry=object(), datum=5.0)

    _build_walk(run, replay, scene, SimpleNamespace(build_walk=build_walk))

    assert received == {
        "ground_datum_m": 5.0,
        "radius_m": 90.0,
        "spacing_m": 3.0,
        "head_height_m": 1.72,
        "seed": 7,
    }


def test_standpoint_seed_row_and_spectrum_order_are_kept(tmp_path):
    captured = {}

    class Result:
        local_grid = np.array([0.0])
        local_solid_angle = 0.5
        seconds = 1.0

        def __init__(self, value):
            self.rho = {"rooftop": np.array([value, value + 1.0])}

        def scalars(self):
            return {"chi_rooftop": 2.0, "sky_fraction": 0.25}

    def trace_standpoints(tracer, standpoints, models, workers):
        captured["standpoints"] = standpoints
        captured["models"] = tuple(models)
        captured["workers"] = workers
        return iter(((0, Result(10.0)), (1, Result(20.0))))

    class Coupler:
        def couple(self, *args):
            return SimpleNamespace(as_dict=lambda: {"peak_sab_w_m2": 0.1})

    walk = SimpleNamespace(
        points=np.array([[1.0, 0.0, 0.0], [2.0, 0.0, 0.0], [3.0, 0.0, 0.0]]),
        ground_z_m=np.array([5.0, 6.0, 7.0]),
    )
    run = escape_config(seed=7, local_cells=2, models=("rooftop",))
    environment = SimpleNamespace(
        models={"rooftop": object()},
        trace_standpoints=trace_standpoints,
        reference_s0_w_m2=1.0,
    )
    prepared = PreparedRun(
        run,
        environment,
        None,
        None,
        walk,
        np.array([2, 0]),
        None,
        object(),
        Coupler(),
    )
    files = OutputFiles(tmp_path / "rows.jsonl", tmp_path / "spectra.npz", tmp_path / "manifest.json")

    _trace_rows(prepared, ExecutionConfig(workers=3), files)

    assert [seed for _point, _ground, seed in captured["standpoints"]] == [2007, 7]
    assert captured["models"] == ("rooftop",)
    assert captured["workers"] == 3
    assert [json.loads(line)["index"] for line in files.rows.read_text().splitlines()] == [2, 0]
    saved = np.load(files.spectra)
    assert saved["index"].tolist() == [2, 0]
    assert saved["rho_rooftop"].tolist() == [[10.0, 11.0], [20.0, 21.0]]


def test_manifest_keys_keep_the_published_insertion_order(tmp_path):
    class Model:
        elevation_min_deg = 0.0
        elevation_max_deg = 90.0
        law = "law"
        height_band_m = (10.0, 20.0)
        range_band_m = None
        description = "model"

    table = SimpleNamespace(class_names=("facade",), as_dict=lambda: {"classes": ["facade"]})
    scene = PreparedScene(
        tmp_path / "mesh.ply",
        SimpleNamespace(face_count=1),
        5.0,
        {"rule": "measured"},
        np.array([0]),
        np.array([2.0]),
    )
    environment = SimpleNamespace(
        reference_s0_w_m2=1.0,
        frequency_note="frequency",
        crop_bound_note="crop",
        models={"isotropic": Model(), "rooftop": Model(), "street_small_cell": Model()},
        describe_body=lambda coupler: {"phantom": "duke"},
    )
    prepared = PreparedRun(
        escape_config(locations=1),
        environment,
        scene,
        MaterialBinding(np.array([0]), table, {"materials": "geometric"}),
        SimpleNamespace(provenance={"rule": "grid"}),
        np.array([0]),
        TraceConfig(),
        object(),
        object(),
    )

    manifest = _manifest(prepared)

    assert list(manifest) == [
        "generator",
        "created_utc",
        "site",
        "mesh",
        "mesh_triangles",
        "crop_radius_m",
        "ground_datum_m",
        "ground_datum_source",
        "ground_datum",
        "reference_s0_w_m2",
        "trace_config",
        "surface_binding",
        "semantic_binding",
        "class_area_fractions",
        "frequency_note",
        "crop_bound_note",
        "walk",
        "locations_requested",
        "locations_traced",
        "illumination_models",
        "body",
        "variant",
        "transport",
        "python",
        "storage_policy",
        "run_digest",
        "run",
    ]
    assert list(manifest["illumination_models"]) == ["isotropic", "rooftop", "street_small_cell"]
    assert manifest["run"] == prepared.run.as_dict()
    assert manifest["run_digest"] == prepared.run.digest()
    assert manifest["transport"] == {"kernel": "numpy"}


def test_device_transport_provenance_names_its_arithmetic_rng_and_versions(monkeypatch):
    monkeypatch.setattr(
        "semantic_twin.exposure.execution._distribution_version",
        lambda name: {"mitsuba": "3.8.0", "drjit": "1.3.1"}[name],
    )

    assert _transport_provenance(escape_config(transport_kernel="drjit")) == {
        "kernel": "drjit",
        "floating_point": "float32",
        "rng": {"family": "counter", "algorithm": "tea32"},
        "versions": {"mitsuba": "3.8.0", "drjit": "1.3.1"},
    }


def test_ladder_sweep_remains_seed_major_and_reuses_one_body(tmp_path):
    calls = []
    bodies = []

    def body(*args, **kwargs):
        value = object()
        bodies.append(value)
        return value

    def execute(run, execution):
        calls.append((run.seed, run.site, run.materials, execution.coupler))
        return tmp_path / "rows.jsonl"

    environment = SweepEnvironment(
        output=tmp_path,
        phantom="phantom.stl",
        phantom_mass_kg=72.4,
        body_coupler_type=body,
        site_mesh=lambda site, crop: tmp_path / "mesh.ply",
        ladder_sites=lambda sites, crop: (list(sites), {}),
        coverage_ladder=lambda site, crop, seed: (
            (f"{site}_{seed}_geometric", "geometric", "none"),
            (f"{site}_{seed}_walk", "walk", "images"),
        ),
        reusable=lambda run: False,
        execute=execute,
        coverage_report=lambda *args, **kwargs: tmp_path / "coverage.json",
        coverage_ladder_report=lambda *args, **kwargs: tmp_path / "summary.json",
        cross_city_report=lambda *args, **kwargs: None,
    )

    result = run_coverage_ladder(
        escape_config(locations=8),
        ExecutionConfig(workers=2),
        LadderSweepConfig(("alpha", "beta"), (7, 9)),
        environment,
    )

    assert result == tmp_path / "summary.json"
    assert [(seed, site, material) for seed, site, material, _body in calls] == [
        (7, "alpha", "geometric"),
        (7, "alpha", "walk"),
        (7, "beta", "geometric"),
        (7, "beta", "walk"),
        (9, "alpha", "geometric"),
        (9, "alpha", "walk"),
        (9, "beta", "geometric"),
        (9, "beta", "walk"),
    ]
    assert len(bodies) == 1
    assert all(used is bodies[0] for *_run, used in calls)
