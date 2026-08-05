from __future__ import annotations

import json
import pathlib
import subprocess
import sys
from dataclasses import dataclass
from typing import Any

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
