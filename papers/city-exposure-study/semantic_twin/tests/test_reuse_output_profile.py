from __future__ import annotations

import json

import pytest

from semantic_twin.exposure import reuse, study
from semantic_twin.runconfig import RunConfig


def _config() -> RunConfig:
    return RunConfig.escape_grid(site="korenmarkt", locations=1, rays=10, tag="trial")


def _stub_validators(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(reuse, "complete_output", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(reuse, "same_output_generation", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(reuse, "same_run_identity", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(reuse, "same_models", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(reuse, "same_support_mesh", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(reuse, "same_atlas_artifact", lambda *_args, **_kwargs: True)


@pytest.mark.parametrize(
    ("stored", "requested", "expected"),
    [
        ("minimal", "standard", False),
        ("minimal", "full", False),
        ("standard", "minimal", True),
    ],
)
def test_reuse_requires_the_requested_retention_tier(
    tmp_path, monkeypatch: pytest.MonkeyPatch, stored: str, requested: str, expected: bool
) -> None:
    _stub_validators(monkeypatch)
    config = _config()
    stem = f"{config.tag}_{config.frequency_ghz:g}ghz"
    (tmp_path / f"{stem}_locations.jsonl").touch()
    (tmp_path / f"{stem}_manifest.json").write_text(json.dumps({"storage_policy": {"profile": stored}}))

    assert reuse.reusable(config, tmp_path, {}, profile=requested) is expected


@pytest.mark.parametrize("requested", ["minimal", "standard"])
def test_a_legacy_manifest_is_treated_as_standard_for_lower_tiers(tmp_path, monkeypatch, requested: str) -> None:
    _stub_validators(monkeypatch)
    config = _config()
    stem = f"{config.tag}_{config.frequency_ghz:g}ghz"
    (tmp_path / f"{stem}_locations.jsonl").touch()
    (tmp_path / f"{stem}_manifest.json").write_text("{}")

    assert reuse.reusable(config, tmp_path, {}, profile=requested)


def test_a_legacy_manifest_does_not_satisfy_a_full_request(tmp_path, monkeypatch) -> None:
    _stub_validators(monkeypatch)
    config = _config()
    stem = f"{config.tag}_{config.frequency_ghz:g}ghz"
    (tmp_path / f"{stem}_locations.jsonl").touch()
    (tmp_path / f"{stem}_manifest.json").write_text("{}")

    assert not reuse.reusable(config, tmp_path, {}, profile="full")


def test_study_reuse_adapter_passes_the_requested_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    captured = {}

    def fake_reusable(*args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        return True

    monkeypatch.setattr(study, "reusable_output", fake_reusable)

    assert study.reusable(_config(), profile="minimal")
    assert captured["kwargs"] == {"profile": "minimal"}
