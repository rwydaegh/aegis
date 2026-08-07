from __future__ import annotations

from semantic_twin.vision.rf_agent import RfTargetContext
from semantic_twin.vision.rf_explorer import AGENT_POLICY, build_exploration_prompt


def test_exploration_prompt_supplies_path_context_without_forcing_tool_order() -> None:
    prompt = build_exploration_prompt(
        RfTargetContext(
            frequency_ghz=28.0,
            path_rank=2,
            bounce_order=1,
            incidence_deg=55.0,
            multipath_power_share=0.21,
            note="historic square",
        )
    )

    assert "line-of-sight path has already been removed" in prompt
    assert "28 GHz" in prompt
    assert "55.000 degrees" in prompt
    assert "21.0000 percent" in prompt
    assert "whichever tools genuinely help" in " ".join(prompt.split())
    assert "next tool or" in prompt


def test_agent_policy_allows_only_image_read_and_rf_mcp() -> None:
    assert 'toolName = "read_file"' in AGENT_POLICY
    assert 'mcpName = "aegis-rf"' in AGENT_POLICY
    assert 'toolName = "*"' in AGENT_POLICY
    assert AGENT_POLICY.count('decision = "allow"') == 2
    assert AGENT_POLICY.count('decision = "deny"') == 1
