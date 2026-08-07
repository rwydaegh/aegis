"""Open-ended Gemini experiment with an RF surface MCP workbench."""

from __future__ import annotations

import json
import pathlib
import shutil
import subprocess
import tempfile
from dataclasses import dataclass

from semantic_twin.vision.rf_agent import GEMINI_MODEL, RfTargetContext

AGENT_POLICY = """[[rule]]
toolName = "read_file"
decision = "allow"
priority = 999

[[rule]]
mcpName = "aegis-rf"
decision = "allow"
priority = 999

[[rule]]
toolName = "*"
decision = "deny"
priority = 998
denyMessage = "Use the attached image and the AEGIS RF workbench only."
"""


@dataclass(frozen=True)
class GeminiExplorerRun:
    """Raw agent trace plus the final response extracted from it."""

    transcript_jsonl: str
    final_response: str
    tool_calls: tuple[dict[str, object], ...]
    stderr: str


def build_exploration_prompt(context: RfTargetContext) -> str:
    """Give the agent an objective and context without prescribing a workflow."""
    incidence = "unknown" if context.incidence_deg is None else f"{context.incidence_deg:.3f} degrees"
    share = (
        "unknown" if context.multipath_power_share is None else f"{100.0 * context.multipath_power_share:.4f} percent"
    )
    return f"""You are the RF surface investigator for one propagation-selected view.
The line-of-sight path has already been removed. This view points from the
receiver toward bounce {context.bounce_order} of multipath component rank
{context.path_rank}. Frequency: {context.frequency_ghz:g} GHz. Incidence angle:
{incidence}. Share of received multipath power: {share}. Extra context:
{context.note or "none"}.

Inspect the attached image and investigate the dominant RF-relevant surface near
the centre. You have a small AEGIS RF workbench. Use whichever tools genuinely
help you, in whatever order you judge useful. The tools calculate consequences
and expose local priors, but you remain responsible for seeing and reasoning.

We want your best physical judgment, including:
- what the interaction surface actually is
- the closest ITU-R P.2040 material row
- one best classic effective RMS height in mm and a plausible range
- what that roughness means for this particular frequency and incidence
- a short, visually discriminative SAM 3 prompt, or a small prompt set if one
  phrase would merge unlike surfaces
- any ambiguity that could materially alter this multipath component

Do not hide behind the need for a profilometer. Make a numerical estimate, test
it if useful, revise it if the evidence warrants it, and explain the decisive
visual and RF cues. End with a compact recommendation and name the next tool or
observation you would request if allowed one more move. This is an exploration,
not a fixed production schema."""


def run_gemini_explorer(
    image: pathlib.Path,
    context: RfTargetContext,
    *,
    model: str = GEMINI_MODEL,
    executable: str = "gemini",
    python_executable: pathlib.Path | None = None,
    server_script: pathlib.Path | None = None,
    timeout_s: float = 600.0,
) -> GeminiExplorerRun:
    """Run Gemini in isolation with only image reading and the RF MCP tools."""
    source = pathlib.Path(image).resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    if shutil.which(executable) is None:
        raise FileNotFoundError(f"Gemini CLI executable not found: {executable}")

    project = pathlib.Path(__file__).resolve().parents[2]
    python_path = (python_executable or project / ".venv" / "bin" / "python").resolve()
    server_path = (server_script or project / "rf_agent_mcp.py").resolve()
    for required in (python_path, server_path):
        if not required.is_file():
            raise FileNotFoundError(required)

    with tempfile.TemporaryDirectory(prefix="aegis-rf-explorer-") as temporary:
        workspace = pathlib.Path(temporary)
        target = workspace / f"target{source.suffix.lower()}"
        shutil.copyfile(source, target)
        gemini_dir = workspace / ".gemini"
        gemini_dir.mkdir()
        settings = {
            "mcp": {"allowed": ["aegis-rf"]},
            "mcpServers": {
                "aegis-rf": {
                    "command": str(python_path),
                    "args": [str(server_path)],
                    "cwd": str(project),
                    "timeout": 120000,
                    "trust": True,
                }
            },
        }
        (gemini_dir / "settings.json").write_text(json.dumps(settings))
        policy = workspace / "rf_agent_policy.toml"
        policy.write_text(AGENT_POLICY)
        prompt = f"@{target.name} {build_exploration_prompt(context)}"
        completed = subprocess.run(  # noqa: S603 - explicit local CLI executable
            [
                executable,
                "--model",
                model,
                "--skip-trust",
                "--approval-mode",
                "default",
                "--policy",
                policy.name,
                "--allowed-mcp-server-names",
                "aegis-rf",
                "--output-format",
                "stream-json",
                "--prompt",
                prompt,
            ],
            cwd=workspace,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise RuntimeError(f"Gemini explorer failed with exit code {completed.returncode}: {detail[-4000:]}")

    final_parts: list[str] = []
    tool_calls: list[dict[str, object]] = []
    for line in completed.stdout.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") == "message" and event.get("role") == "assistant":
            content = event.get("content")
            if isinstance(content, str):
                final_parts.append(content)
        if event.get("type") == "tool_use":
            tool_calls.append(event)
    return GeminiExplorerRun(
        transcript_jsonl=completed.stdout,
        final_response="".join(final_parts),
        tool_calls=tuple(tool_calls),
        stderr=completed.stderr,
    )
