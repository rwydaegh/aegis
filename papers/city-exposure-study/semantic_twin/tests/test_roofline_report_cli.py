"""Focused command-boundary checks for the roofline report CLIs."""

from __future__ import annotations

from pathlib import Path

import pytest

from semantic_twin.cli import roofline_campaign_comparison as comparison_cli
from semantic_twin.cli import roofline_result_figures as figures_cli
from semantic_twin.report.roofline_campaign_comparison import CampaignComparisonError
from semantic_twin.report.roofline_result_figures import FigureArtifacts


def test_comparison_arguments_preserve_defaults() -> None:
    parsed = comparison_cli.arguments(["iid", "fibonacci", "--output", "comparison.json"])

    assert vars(parsed) == {
        "iid_directory": Path("iid"),
        "rotated_fibonacci_directory": Path("fibonacci"),
        "output": Path("comparison.json"),
        "looks": "4,8,12,16",
    }


def test_comparison_main_forwards_typed_paths_and_looks(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[Path, Path, Path, tuple[int, ...]]] = []
    monkeypatch.setattr(
        comparison_cli,
        "write_report",
        lambda iid, fibonacci, output, *, looks: calls.append((iid, fibonacci, output, looks)),
    )

    assert comparison_cli.main(["iid", "fibonacci", "--output", "comparison.json", "--looks", "2, 4,8"]) == 0
    assert calls == [(Path("iid"), Path("fibonacci"), Path("comparison.json"), (2, 4, 8))]


def test_comparison_main_reports_bad_input_and_report_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(SystemExit) as invalid:
        comparison_cli.main(["iid", "fibonacci", "--output", "comparison.json", "--looks", "not-a-look"])
    assert invalid.value.code == 2

    def reject(*_args: object, **_kwargs: object) -> None:
        raise CampaignComparisonError("campaign pair is incompatible")

    monkeypatch.setattr(comparison_cli, "write_report", reject)
    with pytest.raises(SystemExit) as rejected:
        comparison_cli.main(["iid", "fibonacci", "--output", "comparison.json"])
    assert rejected.value.code == 2


def test_figures_arguments_preserve_defaults() -> None:
    parsed = figures_cli.arguments(["--city", "fixture", "iid", "fibonacci", "--output", "results"])

    assert vars(parsed) == {
        "city": [["fixture", "iid", "fibonacci"]],
        "output": Path("results"),
        "looks": "4,8,12,16",
        "final_look": None,
    }


def test_figures_main_forwards_campaign_pairs_and_prints_artifacts(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    calls: list[tuple[list[object], Path, tuple[int, ...], int | None]] = []
    artifacts = FigureArtifacts(
        Path("results.pdf"),
        Path("results.png"),
        Path("results.json"),
        Path("results.csv"),
        Path("results.tex"),
    )

    def fake_write(
        campaigns: object, output: Path, *, looks: tuple[int, ...], final_look: int | None
    ) -> FigureArtifacts:
        calls.append((list(campaigns), output, looks, final_look))
        return artifacts

    monkeypatch.setattr(figures_cli, "write_publication_results", fake_write)
    assert (
        figures_cli.main(
            [
                "--city",
                "fixture",
                "iid",
                "fibonacci",
                "--output",
                "results",
                "--looks",
                "4,8",
                "--final-look",
                "8",
            ]
        )
        == 0
    )
    output = capsys.readouterr().out
    assert output == "wrote results.pdf, results.png, results.json, results.csv, results.tex\n"
    assert len(calls) == 1
    campaign, output_path, looks, final_look = calls[0]
    assert campaign[0].city == "fixture"
    assert campaign[0].iid_directory == Path("iid")
    assert campaign[0].rotated_fibonacci_directory == Path("fibonacci")
    assert output_path == Path("results")
    assert looks == (4, 8)
    assert final_look == 8


def test_figures_main_reports_comparison_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    def reject(*_args: object, **_kwargs: object) -> None:
        raise CampaignComparisonError("campaign pair is incompatible")

    monkeypatch.setattr(figures_cli, "write_publication_results", reject)
    with pytest.raises(SystemExit) as error:
        figures_cli.main(["--city", "fixture", "iid", "fibonacci", "--output", "results"])
    assert error.value.code == 2
