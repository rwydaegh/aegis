from __future__ import annotations

import json
import pathlib
import subprocess
import sys
from dataclasses import dataclass
from typing import Any

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from golden import capture


@dataclass(frozen=True)
class _FakeCase:
    ident: str
    fixture: pathlib.Path
    payload: dict[str, Any]
    tier: str = "fast"
    driver: str = "fake_driver.py"
    argv: tuple[str, ...] = ("--tag", "golden_fake")
    what_it_locks: str = "the fake result"
    writes: tuple[str, ...] = ()
    prerequisites: tuple[str, ...] = ()
    clears: tuple[str, ...] = ()

    def command(self) -> list[str]:
        return [self.driver, *self.argv]

    def reduce(self) -> dict[str, Any]:
        return self.payload


def test_partial_capture_records_only_the_selected_case_provenance(tmp_path: pathlib.Path, monkeypatch: Any) -> None:
    golden = tmp_path / "golden"
    golden.mkdir()
    old_fixture = golden / "old.json"
    new_fixture = golden / "new.json"
    old_fixture.write_text('{"old": true}\n')
    old = _FakeCase("old", old_fixture, {"old": True}, argv=("--tag", "golden_old"))
    new = _FakeCase("new", new_fixture, {"new": True}, argv=("--tag", "golden_new"))
    legacy = {
        "captured_utc": "2025-01-01T00:00:00Z",
        "git_sha": "legacy-sha",
        "git_dirty": False,
    }
    old_entry = {
        "tier": old.tier,
        "driver": old.driver,
        "command": "python fake_driver.py --tag golden_old",
        "argv": list(old.argv),
        "what_it_locks": old.what_it_locks,
        "writes": [],
        "prerequisites": [],
        "clears": [],
        "wall_seconds": 2.0,
        "fixture": old_fixture.name,
        "fixture_bytes": old_fixture.stat().st_size,
    }
    manifest = {
        **legacy,
        "what": "existing manifest",
        "study_root": "/old/root",
        "machine": {"platform": "old machine"},
        "cases": {old.ident: old_entry},
    }
    (golden / "MANIFEST.json").write_text(json.dumps(manifest))

    source_calls = 0

    def source_provenance() -> dict[str, object]:
        nonlocal source_calls
        source_calls += 1
        return {"git_sha": "new-sha", "git_dirty": True, "source_dirty": False}

    monkeypatch.setattr(capture, "GOLDEN_DIR", golden)
    monkeypatch.setattr(capture, "CASES", (old, new))
    monkeypatch.setattr(capture, "source_provenance", source_provenance)
    monkeypatch.setattr(capture, "run_case", lambda *_args, **_kwargs: 1.25)
    monkeypatch.setattr(sys, "argv", ["capture.py", "--case", "new"])

    assert capture.main() == 0

    written = json.loads((golden / "MANIFEST.json").read_text())
    assert source_calls == 1
    assert {key: written[key] for key in legacy} == legacy
    assert not ({"captured_utc", "git_sha", "git_dirty"} & written["cases"]["old"].keys())
    assert written["cases"]["new"]["git_sha"] == "new-sha"
    assert written["cases"]["new"]["git_dirty"] is True
    assert written["cases"]["new"]["source_dirty"] is False
    assert written["cases"]["new"]["captured_utc"].endswith("Z")
    assert json.loads(new_fixture.read_text()) == {"new": True}


def _git(root: pathlib.Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, text=True)


def test_source_dirty_excludes_fixtures_and_handoffs_but_keeps_executable_inputs(tmp_path: pathlib.Path) -> None:
    study = tmp_path / "papers" / "city-exposure-study" / "semantic_twin"
    golden = study / "tests" / "golden"
    docs = study / "docs"
    aegis = tmp_path / "src" / "aegis"
    golden.mkdir(parents=True)
    docs.mkdir()
    aegis.mkdir(parents=True)
    source = study / "semantic_twin.py"
    aegis_source = aegis / "engine.py"
    fixture = golden / "case.json"
    manifest = golden / "MANIFEST.json"
    prompt = study / "CODEX_PROMPT.md"
    handoff = study / "HANDOFF.md"
    material_handoff = docs / "HANDOFF_MATERIALS.md"
    sibling = tmp_path / "sibling.txt"
    for path in (source, aegis_source, fixture, manifest, prompt, handoff, material_handoff, sibling):
        path.write_text("committed\n")

    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "golden@example.invalid")
    _git(tmp_path, "config", "user.name", "Golden test")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-qm", "initial")

    for path in (fixture, manifest, prompt, handoff, material_handoff, sibling):
        path.write_text("excluded change\n")
    (golden / "new_fixture.json").write_text("untracked fixture\n")
    (docs / "HANDOFF_SCENE.md").write_text("untracked handoff\n")
    assert capture._git_dirty(study) is True
    assert capture._git_dirty(study, capture.SOURCE_PATHSPECS) is False

    source.write_text("relevant study change\n")
    assert capture._git_dirty(study, capture.SOURCE_PATHSPECS) is True

    source.write_text("committed\n")
    aegis_source.write_text("relevant aegis change\n")
    assert capture._git_dirty(study, capture.SOURCE_PATHSPECS) is True


def test_seed_spread_reduces_cached_probe_rows_without_study_outputs(tmp_path: pathlib.Path, monkeypatch: Any) -> None:
    """Exercise the spread reducer with a tiny synthetic capture cache.

    The real spread command deliberately traces five 16-standpoint runs. This
    regression only needs to prove that its cache contract and reductions stay
    wired to the current capture code, so it supplies the completed rows in a
    temporary directory instead of requiring a mesh or a minute-long tracer
    run.
    """
    import golden.cases as cases

    exposure_out = tmp_path / "exposure_korenmarkt"
    exposure_out.mkdir()
    base = _FakeCase(
        ident="exposure_korenmarkt_130m_geometric",
        fixture=tmp_path / "unused.json",
        payload={},
        argv=("--seed", "7", "--tag", "golden_base"),
    )
    monkeypatch.setattr(capture, "CASES_BY_ID", {base.ident: base})
    monkeypatch.setattr(cases, "EXPOSURE_OUT", exposure_out)

    metric_names = (
        "chi_isotropic",
        "chi_rooftop",
        "chi_street_small_cell",
        "sky_fraction",
        "mean_bounces",
        "isotropic_peak_sab_w_m2",
        "rooftop_peak_sab_w_m2",
        "isotropic_sar_wb_w_kg",
        "rooftop_sar_wb_w_kg",
    )
    for seed in (7, 8):
        rows = []
        for index in range(16):
            rows.append(
                {
                    "index": index,
                    **{name: float(seed + index / 100.0) for name in metric_names},
                }
            )
        tag = f"golden_spread_seed{seed}_15ghz"
        (exposure_out / f"{tag}_locations.jsonl").write_text("".join(json.dumps(row) + "\n" for row in rows))
        (exposure_out / f"{tag}_manifest.json").write_text(json.dumps({"wall_seconds": 0.01}))

    result = capture.seed_spread(sys.executable, seeds=(7, 8))

    assert result["standpoint_sets_identical"] is True
    assert result["seeds"] == [7, 8]
    summary = result["median_over_16_standpoints"]
    assert summary["chi_isotropic"]["medians"] == [7.075, 8.075]
    import math

    assert summary["chi_isotropic"]["db_range"] == pytest.approx(10.0 * math.log10(8.075 / 7.075))


def test_monte_carlo_uses_current_material_and_walk_exports(tmp_path: pathlib.Path, monkeypatch: Any) -> None:
    """Exercise the fixed-point Monte Carlo helper without a local mesh.

    The helper is an optional, expensive measurement, but its imports are part
    of the capture tool's public command path. Small fakes let this test cover
    construction, two fixed standpoints, and the seed loop while keeping the
    golden test suite independent of ``outputs/`` and Mitsuba.
    """
    from types import SimpleNamespace

    import semantic_twin.materials as materials
    import semantic_twin.propagation as propagation
    import semantic_twin.walk as walk

    class FakeGeometry:
        vertices = __import__("numpy").zeros((3, 3))
        faces = __import__("numpy").zeros((1, 3), dtype=int)

    class FakeTracer:
        def __init__(self, *_args: Any) -> None:
            self.seeds: list[int] = []

        def trace(self, _origin: Any, models: Any, *, ground_z_m: float, seed: int) -> Any:
            del ground_z_m
            self.seeds.append(seed)
            return SimpleNamespace(susceptibility={name: float(seed) for name in models})

    tracer_instances: list[FakeTracer] = []

    def make_tracer(*args: Any) -> FakeTracer:
        tracer = FakeTracer(*args)
        tracer_instances.append(tracer)
        return tracer

    monkeypatch.setattr(capture, "ROOT", tmp_path)
    monkeypatch.setattr(materials, "classify_faces", lambda *_args, **_kwargs: __import__("numpy").zeros(1, dtype=int))
    monkeypatch.setattr(
        materials, "load_table", lambda *_args, **_kwargs: SimpleNamespace(permittivity=[1], rms_height_m=[0])
    )
    monkeypatch.setattr(walk, "measure_ground_datum", lambda *_args, **_kwargs: SimpleNamespace(z_m=0.0))
    monkeypatch.setattr(
        walk,
        "build_walk",
        lambda *_args, **_kwargs: SimpleNamespace(
            points=__import__("numpy").zeros((428, 3)),
            ground_z_m=__import__("numpy").zeros(428),
        ),
    )
    monkeypatch.setattr(propagation, "MODELS", {"isotropic": object()})
    monkeypatch.setattr(propagation, "MitsubaGeometry", lambda *_args, **_kwargs: FakeGeometry())
    monkeypatch.setattr(propagation, "TraceConfig", lambda **kwargs: SimpleNamespace(**kwargs))
    monkeypatch.setattr(propagation, "SbrTracer", make_tracer)

    result = capture.monte_carlo(seeds=2)

    assert result["rays"] == 200_000
    assert set(result["standpoints"]) == {"427", "213"}
    assert len(tracer_instances) == 1
    assert tracer_instances[0].seeds == [90_000, 90_001, 90_000, 90_001]
