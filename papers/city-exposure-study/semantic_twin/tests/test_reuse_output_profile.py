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


def test_reuse_rejects_a_manifest_with_the_historical_quadrature_material_rule() -> None:
    """Changing the roughness reduction must invalidate old material numbers."""
    config = _config()
    manifest = {
        "run": config.as_dict(),
        "run_digest": config.digest(),
        "surface_binding": {
            "provenance": {
                "roughness_rule": "quadrature",
            }
        },
    }

    manifest["surface_binding"]["provenance"]["roughness_rule"] = "finish_only"
    assert reuse.same_run_identity(manifest, config, {})

    manifest["surface_binding"]["provenance"]["roughness_rule"] = "quadrature"
    assert not reuse.same_run_identity(manifest, config, {})


def test_manifest_before_launch_sampling_means_iid_but_never_rotated_fibonacci() -> None:
    iid = _config()
    recorded = iid.as_dict()
    recorded.pop("launch_sampling")
    manifest = {"run": recorded, "run_digest": iid.digest()}

    assert reuse.same_run_identity(manifest, iid, {})
    assert not reuse.same_run_identity(manifest, iid.replace(launch_sampling="rotated_fibonacci"), {})


def test_manifest_before_transport_and_launch_fields_restores_both_historical_defaults() -> None:
    iid = _config()
    recorded = iid.as_dict()
    recorded.pop("transport_kernel")
    recorded.pop("launch_sampling")
    manifest = {"run": recorded, "run_digest": iid.digest()}

    assert reuse.same_run_identity(manifest, iid, {})
