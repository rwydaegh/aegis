from __future__ import annotations

from pathlib import Path

import pytest

from semantic_twin.cli import material_evidence_ablation as command
from semantic_twin.report.material_evidence_ablation import (
    MaterialAblationArtifacts,
    MaterialEvidenceAblationError,
)


def test_arguments_preserve_typed_paths() -> None:
    parsed = command.arguments(["atlas", "geometric", "--output", "report"])

    assert vars(parsed) == {
        "atlas_directory": Path("atlas"),
        "geometric_directory": Path("geometric"),
        "output": Path("report"),
    }


def test_main_forwards_pair_and_lists_artifacts(monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    calls = []
    artifacts = MaterialAblationArtifacts(
        Path("report/result.json"),
        Path("report/result.csv"),
        Path("report/result.pdf"),
        Path("report/result.png"),
        Path("report/manifest.json"),
    )
    monkeypatch.setattr(
        command,
        "write_material_evidence_ablation",
        lambda atlas, geometric, output: calls.append((atlas, geometric, output)) or artifacts,
    )

    assert command.main(["atlas", "geometric", "--output", "report"]) == 0
    assert calls == [(Path("atlas"), Path("geometric"), Path("report"))]
    assert capsys.readouterr().out.startswith("wrote report/result.json")


def test_main_maps_pair_validation_to_parser_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def reject(*_args, **_kwargs):
        raise MaterialEvidenceAblationError("identity drift")

    monkeypatch.setattr(command, "write_material_evidence_ablation", reject)
    with pytest.raises(SystemExit) as error:
        command.main(["atlas", "geometric", "--output", "report"])
    assert error.value.code == 2
