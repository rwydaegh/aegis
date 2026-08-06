from __future__ import annotations

import pathlib

import run_exposure

from semantic_twin.cli import exposure as exposure_cli
from semantic_twin.exposure.output_policy import OutputProfile


ROOT = pathlib.Path(__file__).resolve().parents[1]


def test_root_facade_does_not_own_the_command_line_parser() -> None:
    source = (ROOT / "run_exposure.py").read_text(encoding="utf-8")
    assert "import argparse" not in source
    assert "add_argument" not in source


def test_root_reexports_the_package_parser_and_compatibility_adapter() -> None:
    assert run_exposure.arguments is exposure_cli.arguments
    assert run_exposure._escape_config is exposure_cli._escape_config
    assert vars(run_exposure.arguments([])) == vars(exposure_cli.arguments([]))


def test_root_main_delegates_to_the_package_command(monkeypatch) -> None:
    calls: list[list[str] | None] = []

    def fake_main(argv: list[str] | None = None) -> int:
        calls.append(argv)
        return 17

    monkeypatch.setattr(exposure_cli, "main", fake_main)

    assert run_exposure.main(["--report", "trial"]) == 17
    assert calls == [["--report", "trial"]]


def test_package_main_dispatches_through_package_owned_callbacks(monkeypatch) -> None:
    calls: list[str] = []

    monkeypatch.setattr(exposure_cli, "report", lambda stem: calls.append(stem))

    assert exposure_cli.main(["--report", "trial"]) == 0
    assert calls == ["trial"]


def test_output_profile_defaults_and_forwards_to_execution(monkeypatch) -> None:
    assert exposure_cli.arguments([]).output_profile == "standard"

    calls: list[dict[str, object]] = []

    def fake_run(_locations, _rays, _frequency_hz, **options):
        calls.append(options)

    monkeypatch.setattr(exposure_cli, "run", fake_run)
    assert exposure_cli.main(["--output-profile", "minimal"]) == 0
    assert calls[0]["output_profile"] == "minimal"

    _config, execution = exposure_cli._escape_config(1, 100, 15.0e9, output_profile="full")
    assert execution.output_profile is OutputProfile.FULL
