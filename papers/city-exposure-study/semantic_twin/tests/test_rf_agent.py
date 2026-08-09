"""Contract tests for the propagation-selected Gemini surface analyst."""

from __future__ import annotations

import json
import pathlib
import subprocess

import pytest

from semantic_twin.vision.rf_agent import (
    PROMPT_VERSION,
    RfTargetContext,
    build_rf_prompt,
    parse_surface_estimate,
    run_gemini_cli,
)


def answer(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "observation": "Weathered red brick with recessed mortar joints.",
        "dominant_surface": "historic brick masonry",
        "itu_p2040_material": "brick",
        "rms_height_mm": 2.0,
        "rms_height_range_mm": [0.8, 4.0],
        "roughness_reasoning": "The joint recess and irregular fired faces dominate the patch height.",
        "confidence": 0.82,
        "sam3_prompt": "weathered brick facade",
    }
    payload.update(overrides)
    return payload


def test_prompt_stays_close_to_the_ranked_multipath_question() -> None:
    prompt = build_rf_prompt(
        RfTargetContext(
            frequency_ghz=28.0,
            path_rank=1,
            bounce_order=2,
            incidence_deg=63.25,
            multipath_power_share=0.34,
            note="receiver panorama pano_07",
        )
    )
    assert "after the line-of-sight component was removed" in prompt
    assert "rank 1" in prompt
    assert "bounce 2" in prompt
    assert "28 GHz" in prompt
    assert "63.250 degrees" in prompt
    assert "34.0000 percent" in prompt
    assert "Make your best numerical estimate" in prompt
    assert "receiver panorama pano_07" in prompt


def test_surface_estimate_accepts_a_concrete_rms_guess() -> None:
    estimate = parse_surface_estimate(answer())
    assert estimate.itu_p2040_material == "brick"
    assert estimate.rms_height_mm == pytest.approx(2.0)
    assert estimate.rms_height_range_mm == pytest.approx((0.8, 4.0))
    assert estimate.sam3_prompt == "weathered brick facade"


def test_surface_estimate_accepts_json_fences_from_a_model() -> None:
    estimate = parse_surface_estimate(f"```json\n{json.dumps(answer())}\n```")
    assert estimate.confidence == pytest.approx(0.82)


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"itu_p2040_material": "limestone"}, "unknown ITU-R P.2040 material"),
        ({"rms_height_mm": 5.0}, "must lie inside"),
        ({"rms_height_range_mm": [4.0, 0.8]}, "nonnegative and ordered"),
        ({"confidence": 1.1}, "confidence must lie"),
        (
            {"sam3_prompt": "one two three four five six seven eight nine ten eleven twelve thirteen"},
            "short noun phrase",
        ),
    ],
)
def test_surface_estimate_refuses_invalid_physics_contract(overrides: dict[str, object], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        parse_surface_estimate(answer(**overrides))


def test_surface_estimate_requires_the_exact_schema() -> None:
    payload = answer()
    payload["commentary"] = "not part of the machine contract"
    with pytest.raises(ValueError, match="keys differ from the contract"):
        parse_surface_estimate(payload)


def test_gemini_cli_isolated_copy_accepts_an_ignored_source_image(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "outputs" / "target.png"
    source.parent.mkdir()
    source.write_bytes(b"representative image bytes")
    observed: dict[str, object] = {}

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        workspace = pathlib.Path(str(kwargs["cwd"]))
        observed["command"] = command
        observed["target"] = (workspace / "target.png").read_bytes()
        observed["policy"] = (workspace / "one_turn_policy.toml").read_text()
        envelope = {
            "session_id": "session-7",
            "response": json.dumps(answer()),
            "stats": {"models": {"gemini-3.6-flash": {"requests": 1}}},
        }
        return subprocess.CompletedProcess(command, 0, stdout=json.dumps(envelope), stderr="")

    monkeypatch.setattr("semantic_twin.vision.rf_agent.shutil.which", lambda _name: "/usr/bin/gemini")
    monkeypatch.setattr("semantic_twin.vision.rf_agent.subprocess.run", fake_run)
    run = run_gemini_cli(source, RfTargetContext(15.0))

    assert observed["target"] == b"representative image bytes"
    assert 'toolName = "*"' in str(observed["policy"])
    assert "@target.png" in observed["command"][-1]
    assert "--policy" in observed["command"]
    assert run.session_id == "session-7"
    assert run.prompt_version == PROMPT_VERSION
    assert run.estimate.rms_height_mm == pytest.approx(2.0)
    assert run.image_sha256
    assert run.prompt_sha256
