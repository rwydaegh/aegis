from __future__ import annotations

from pathlib import Path

import pytest

from semantic_twin.cli import current_topology_convergence as command
from semantic_twin.report.current_topology_convergence import (
    EXPECTED_SITES,
    CurrentTopologyConvergenceArtifacts,
    CurrentTopologyConvergenceError,
)


def _argv() -> list[str]:
    values: list[str] = []
    for label in ("extended", "sealed"):
        for site in EXPECTED_SITES:
            values.extend((f"--{label}", f"{site}={label}/{site}"))
    return [*values, "--output", "report", "--bootstrap-replicates", "300", "--bootstrap-seed", "9"]


def test_arguments_require_and_map_all_five_campaign_pairs() -> None:
    parsed = command.arguments(_argv())

    assert parsed.extended == {site: Path("extended") / site for site in EXPECTED_SITES}
    assert parsed.sealed == {site: Path("sealed") / site for site in EXPECTED_SITES}
    assert parsed.output == Path("report")
    assert parsed.bootstrap_replicates == 300
    assert parsed.bootstrap_seed == 9


def test_main_forwards_maps_and_lists_all_artifacts(monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    calls = []
    artifacts = CurrentTopologyConvergenceArtifacts(
        Path("report/result.json"),
        Path("report/result.csv"),
        Path("report/result.pdf"),
        Path("report/result.png"),
        Path("report/manifest.json"),
    )
    monkeypatch.setattr(
        command,
        "write_current_topology_convergence",
        lambda extended, sealed, output, **options: calls.append((extended, sealed, output, options)) or artifacts,
    )

    assert command.main(_argv()) == 0
    assert calls[0][0] == {site: Path("extended") / site for site in EXPECTED_SITES}
    assert calls[0][1] == {site: Path("sealed") / site for site in EXPECTED_SITES}
    assert calls[0][2] == Path("report")
    assert calls[0][3] == {"bootstrap_replicates": 300, "bootstrap_seed": 9}
    assert capsys.readouterr().out.startswith("wrote report/result.json")


def test_main_maps_report_validation_to_parser_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def reject(*_args, **_kwargs):
        raise CurrentTopologyConvergenceError("identity drift")

    monkeypatch.setattr(command, "write_current_topology_convergence", reject)
    with pytest.raises(SystemExit) as error:
        command.main(_argv())
    assert error.value.code == 2
