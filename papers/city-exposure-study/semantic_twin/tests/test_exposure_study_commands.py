"""The study commands translate arguments into stable domain configurations."""

from __future__ import annotations

import ast
import json
import pathlib
from typing import ClassVar

import numpy as np
import pytest

import measure_bounce_evidence
import run_monostatic
import run_seed_replicas
import run_station_calibration
import summarise_evidence_coverage
import summarise_station_calibration
from semantic_twin.exposure import monostatic_study, seed_replicas, station_calibration
from semantic_twin.report import evidence_coverage, station_calibration_summary
from semantic_twin.transport import bounce_evidence_study


@pytest.mark.parametrize(
    ("command", "argv", "expected"),
    [
        (
            run_monostatic,
            ["--sites", "korenmarkt,milan_duomo", "--frequency-ghz", "28", "--seed", "31", "--visibility"],
            {"sites": ("korenmarkt", "milan_duomo"), "frequency_hz": 28e9, "seed": 31, "visibility": True},
        ),
        (
            run_seed_replicas,
            ["--seeds", "31,37,41", "--frequency-ghz", "28", "--limit", "2"],
            {"seeds": (31, 37, 41), "frequency_hz": 28e9, "limit": 2},
        ),
        (
            run_station_calibration,
            ["--site", "korenmarkt", "--seeds", "31,37", "--stage", "exposure", "--workers", "3"],
            {"sites": ("korenmarkt",), "seeds": (31, 37), "stage": "exposure", "workers": 3},
        ),
        (
            summarise_station_calibration,
            ["--site", "korenmarkt", "--seeds", "31,37", "--tag", "_test"],
            {"sites": ("korenmarkt",), "seeds": (31, 37), "tag": "_test"},
        ),
        (
            summarise_evidence_coverage,
            ["--crop-m", "250", "--no-write", "--measure-semantic"],
            {"crops_m": (250,), "write": False, "measure_semantic": True},
        ),
        (
            measure_bounce_evidence,
            ["--site", "korenmarkt", "milan_duomo", "--crop-m", "250", "--seed", "31"],
            {"sites": ("korenmarkt", "milan_duomo"), "crops_m": (250,), "seed": 31},
        ),
    ],
)
def test_commands_pass_typed_configuration_to_the_domain(monkeypatch, command, argv, expected):
    seen = []
    monkeypatch.setattr(command, "execute", lambda config: seen.append(config) or 0)

    assert command.main(argv) == 0
    assert len(seen) == 1
    for field, value in expected.items():
        assert getattr(seen[0], field) == value


def test_monostatic_seed_schedule_stays_tied_to_the_walk_index(monkeypatch):
    calls = []
    monkeypatch.setattr(monostatic_study, "OUTPUT", pathlib.Path("unused"))

    class Walk:
        points = np.array([[1.0, 0.0, 1.5], [2.0, 0.0, 1.5], [3.0, 0.0, 1.5]])
        ground_z_m = np.zeros(3)
        provenance: ClassVar[dict] = {}

    class Geometry:
        vertices = np.zeros((3, 3))
        faces = np.zeros((1, 3), dtype=int)
        face_count = 1

    class Binding:
        permittivity = np.ones(3)
        rms_height_m = np.ones(3)

        def as_dict(self):
            return {}

    class Result:
        seconds = 0.0

        def scalars(self):
            return {"chi_isotropic": 1.0}

    class Mono:
        seconds = 0.0
        range_profile = np.zeros(1)
        coverage: ClassVar[dict] = {}

        def scalars(self):
            return {"mono_gain_db": 0.0, "mono_glint_share": 0.0, "mono_relative_standard_error": 0.0}

    monkeypatch.setattr(monostatic_study, "site_mesh", lambda *_: pathlib.Path("mesh.ply"))
    monkeypatch.setattr(monostatic_study, "MitsubaGeometry", lambda *_args, **_kwargs: Geometry())
    monkeypatch.setattr(
        monostatic_study, "measure_ground_datum", lambda *_args, **_kwargs: type("D", (), {"z_m": 0.0})()
    )
    monkeypatch.setattr(monostatic_study, "classify_faces", lambda *_: np.zeros(1, dtype=int))
    monkeypatch.setattr(monostatic_study, "load_table", lambda *_: Binding())
    monkeypatch.setattr(monostatic_study, "build_walk", lambda *_args, **_kwargs: Walk())
    monkeypatch.setattr(monostatic_study, "stratified_subset", lambda *_: np.array([2, 0]))
    monkeypatch.setattr(monostatic_study, "SbrTracer", lambda *_: object())

    def trace(_tracer, _point, _models, *, seed, **_kwargs):
        calls.append(seed)
        return Result(), Mono()

    monkeypatch.setattr(monostatic_study, "trace_monostatic", trace)
    monkeypatch.setattr(pathlib.Path, "mkdir", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(pathlib.Path, "write_text", lambda *_args, **_kwargs: 0)
    monkeypatch.setattr(pathlib.Path, "open", lambda *_args, **_kwargs: _NullWriter())
    monkeypatch.setattr(np, "savez_compressed", lambda *_args, **_kwargs: None)

    monostatic_study.run_site(
        "korenmarkt",
        locations=2,
        rays=4,
        frequency_hz=15e9,
        max_bounces=3,
        crop_m=250,
        seed=31,
        variant="scalar_rgb",
        tag="test",
        walk_radius_m=90.0,
        walk_spacing_m=3.0,
        evidence=False,
    )

    assert calls == [2031, 31]


class _NullWriter:
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def write(self, _value):
        return 0

    def flush(self):
        return None


def test_station_reductions_keep_the_two_published_statistics_distinct():
    baseline = np.array([1.0, 4.0, 9.0])
    changed = np.array([2.0, 4.0, 18.0])

    result = station_calibration.reductions(baseline, changed)

    assert result["paired_median_shift_db"] == pytest.approx(10.0 * np.log10(2.0))
    assert result["distribution_median_shift_db"] == pytest.approx(0.0)


def test_seed_replica_interval_and_report_helpers_are_package_owned():
    interval = seed_replicas._sd_interval(np.array([1.0, 2.0, 3.0, 4.0]))

    assert interval[0] < interval[1]
    assert evidence_coverage.markdown
    assert station_calibration_summary.pooled_scatter


def test_station_trace_preserves_seed_schedule_and_result_order(monkeypatch):
    schedules = []

    class Binding:
        permittivity = np.ones(3)
        rms_height_m = np.ones(3)

    class Result:
        def __init__(self, value):
            self.value = value

        def scalars(self):
            return {
                "chi_isotropic": self.value,
                "chi_rooftop": self.value,
                "chi_street_small_cell": self.value,
                "sky_fraction": self.value,
                "truncated_throughput_share": self.value,
            }

    monkeypatch.setattr(
        station_calibration,
        "bind_materials",
        lambda *_args, **_kwargs: (np.zeros(1, dtype=int), Binding(), {"covered_fraction_by_area": 0.25}),
    )
    monkeypatch.setattr(station_calibration, "SbrTracer", lambda *_args, **_kwargs: object())

    def trace(_tracer, standpoints, _models, *, workers):
        schedules.append((standpoints, workers))
        yield 1, Result(20.0)
        yield 0, Result(10.0)

    monkeypatch.setattr(station_calibration, "trace_standpoints", trace)
    origins = np.array([[0.0, 0.0, 1.5], [1.0, 0.0, 1.5]])
    grounds = np.array([0.0, 0.0])
    config = station_calibration.StationCalibrationConfig(sites=("korenmarkt",), seeds=(31, 37), workers=3)

    result = station_calibration._trace_rung(
        "korenmarkt",
        250,
        {"geometry": object(), "areas": np.ones(1), "face_class": np.zeros(1, dtype=int)},
        "geometric",
        "pose",
        origins,
        grounds,
        config,
    )

    assert [[entry[2] for entry in schedule] for schedule, _workers in schedules] == [[31, 1031], [37, 1037]]
    assert [workers for _schedule, workers in schedules] == [3, 3]
    assert result["per_seed"]["chi_rooftop"] == [[10.0, 20.0], [10.0, 20.0]]


def test_bounce_budget_reuses_the_same_seed_stream_at_every_budget(monkeypatch):
    calls = []

    class Binding:
        permittivity = np.ones(3)
        rms_height_m = np.ones(3)

    class Result:
        def scalars(self):
            return {
                "chi_isotropic": 1.0,
                "chi_rooftop": 2.0,
                "chi_street_small_cell": 3.0,
                "truncated_throughput_share": 0.0,
                "sky_fraction": 0.5,
                "mean_bounces": 2.0,
            }

    class Tracer:
        def trace(self, _point, _models, *, seed, **_kwargs):
            calls.append(seed)
            return Result()

    monkeypatch.setattr(bounce_evidence_study, "SbrTracer", lambda *_args, **_kwargs: Tracer())
    config = bounce_evidence_study.BounceEvidenceConfig(seed=31, rays=4)
    measurement = bounce_evidence_study._Measurement(
        site="korenmarkt",
        crop_m=250,
        geometry=object(),
        face_class=np.zeros(1, dtype=int),
        binding=Binding(),
        masks={},
        points=np.zeros((2, 3)),
        datums=np.zeros(2),
        datum=0.0,
        config=config,
    )

    report = bounce_evidence_study._budget_cost(measurement)

    assert calls == [31, 32] * len(bounce_evidence_study.BUDGETS)
    assert report["cost_reference"] == "L8_roulette99"
    assert list(report["budgets"]) == [
        f"L{bounces}_roulette{roulette}" for bounces, roulette in bounce_evidence_study.BUDGETS
    ]


def test_evidence_report_keeps_the_existing_gate_schema(monkeypatch, tmp_path):
    output = tmp_path / "coverage.json"
    monkeypatch.setattr(evidence_coverage, "SITES", ())

    evidence_coverage.execute(
        evidence_coverage.EvidenceCoverageConfig(crops_m=(250,), out=output, into=tmp_path / "absent.md")
    )

    gate = json.loads(output.read_text())["gate"]
    assert gate["crop_m"] == [250]
    assert gate["no_write"] is False
    assert "crops_m" not in gate
    assert "write" not in gate


@pytest.mark.parametrize(
    "name",
    (
        "run_monostatic.py",
        "run_seed_replicas.py",
        "run_station_calibration.py",
        "summarise_station_calibration.py",
        "summarise_evidence_coverage.py",
        "measure_bounce_evidence.py",
    ),
)
def test_study_commands_define_only_main(name):
    root = pathlib.Path(__file__).resolve().parents[1]
    tree = ast.parse((root / name).read_text())

    assert [node.name for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))] == ["main"]


@pytest.mark.parametrize(
    "relative",
    (
        "exposure/monostatic_study.py",
        "exposure/seed_replicas.py",
        "exposure/station_calibration.py",
        "report/station_calibration_summary.py",
        "report/evidence_coverage.py",
        "transport/bounce_evidence_study.py",
    ),
)
def test_domain_modules_have_no_command_parser_or_main(relative):
    package = pathlib.Path(__file__).resolve().parents[1] / "semantic_twin"
    tree = ast.parse((package / relative).read_text())
    imported = {alias.name for node in tree.body if isinstance(node, ast.Import) for alias in node.names}

    assert "argparse" not in imported
    assert not any(
        isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "main" for node in tree.body
    )
