"""Gemini vision analysis of one propagation-selected surface crop.

The ray tracer decides where to look. Gemini decides what the dominant surface
is, maps it to the nearest ITU-R P.2040 material, estimates the classic RMS
height used by the rough-surface model, and writes the short noun phrase that
SAM 3 should segment. This module is deliberately only that one turn. Mask
inspection and iterative retracing can be added once the one-turn contract has
been measured.
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import shutil
import subprocess
import tempfile
import time
from dataclasses import asdict, dataclass
from typing import Any

GEMINI_MODEL = "gemini-3.6-flash"
PROMPT_VERSION = "rf-mpc-surface-v1"

ONE_TURN_POLICY = """[[rule]]
toolName = "read_file"
decision = "allow"
priority = 999

[[rule]]
toolName = "*"
decision = "deny"
priority = 998
denyMessage = "This is a one-turn RF image analysis. Use the attached image and answer now."
"""

ITU_P2040_MATERIALS = (
    "vacuum_air",
    "concrete",
    "brick",
    "plasterboard",
    "wood",
    "glass",
    "ceiling_board",
    "chipboard",
    "plywood",
    "marble",
    "floorboard",
    "vinyl_tile",
    "carpet_tile",
    "asphalt_concrete",
    "metal",
)


@dataclass(frozen=True)
class RfTargetContext:
    """Propagation facts supplied beside the view of one surface interaction."""

    frequency_ghz: float
    path_rank: int = 1
    bounce_order: int = 1
    incidence_deg: float | None = None
    multipath_power_share: float | None = None
    note: str = ""

    def __post_init__(self) -> None:
        if self.frequency_ghz <= 0.0:
            raise ValueError("frequency_ghz must be positive")
        if self.path_rank < 1:
            raise ValueError("path_rank must be at least one")
        if self.bounce_order < 1:
            raise ValueError("bounce_order must be at least one")
        if self.incidence_deg is not None and not 0.0 <= self.incidence_deg <= 90.0:
            raise ValueError("incidence_deg must lie in [0, 90]")
        if self.multipath_power_share is not None and not 0.0 <= self.multipath_power_share <= 1.0:
            raise ValueError("multipath_power_share must lie in [0, 1]")


@dataclass(frozen=True)
class RfSurfaceEstimate:
    """Validated material and roughness answer from the vision model."""

    observation: str
    dominant_surface: str
    itu_p2040_material: str
    rms_height_mm: float
    rms_height_range_mm: tuple[float, float]
    roughness_reasoning: str
    confidence: float
    sam3_prompt: str

    def __post_init__(self) -> None:
        for name in ("observation", "dominant_surface", "roughness_reasoning", "sam3_prompt"):
            if not str(getattr(self, name)).strip():
                raise ValueError(f"{name} must not be empty")
        if self.itu_p2040_material not in ITU_P2040_MATERIALS:
            raise ValueError(f"unknown ITU-R P.2040 material {self.itu_p2040_material!r}")
        low, high = self.rms_height_range_mm
        if self.rms_height_mm < 0.0 or low < 0.0 or high < low:
            raise ValueError("RMS height and its range must be nonnegative and ordered")
        if not low <= self.rms_height_mm <= high:
            raise ValueError("rms_height_mm must lie inside rms_height_range_mm")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must lie in [0, 1]")
        if "\n" in self.sam3_prompt or len(self.sam3_prompt.split()) > 12:
            raise ValueError("sam3_prompt must be one short noun phrase")

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class GeminiSurfaceRun:
    """One replayable Gemini CLI call and its validated answer."""

    estimate: RfSurfaceEstimate
    model: str
    prompt_version: str
    prompt_sha256: str
    image_sha256: str
    elapsed_s: float
    session_id: str | None
    stats: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "estimate": self.estimate.as_dict(),
            "model": self.model,
            "prompt_version": self.prompt_version,
            "prompt_sha256": self.prompt_sha256,
            "image_sha256": self.image_sha256,
            "elapsed_s": self.elapsed_s,
            "session_id": self.session_id,
            "stats": self.stats,
        }


def build_rf_prompt(context: RfTargetContext) -> str:
    """Write the exact RF question given to Gemini beside the target crop."""
    incidence = "unknown" if context.incidence_deg is None else f"{context.incidence_deg:.3f} degrees"
    share = (
        "unknown"
        if context.multipath_power_share is None
        else f"{100.0 * context.multipath_power_share:.4f} percent of received multipath power"
    )
    return f"""The attached image points from the receiver toward the surface interaction of
rank {context.path_rank} after the line-of-sight component was removed. It is
bounce {context.bounce_order} of that multipath component at {context.frequency_ghz:g} GHz.
The ray incidence angle is {incidence}. This component carries {share}.
Additional context: {context.note or "none"}

This is a one-turn image analysis. After reading the attached image, do not call
search, shell, repository, or other tools. Answer directly from the image and
the RF context supplied here.

Use broad visual and architectural knowledge to analyze the dominant RF-relevant
surface at the center of the image. Say concretely what you see. Match it to the
closest ITU-R P.2040 material row from this exact list:
{", ".join(ITU_P2040_MATERIALS)}.

Make your best numerical estimate of the classic effective RMS surface height in
millimetres for this surface patch. Use all visible texture, joints, relief,
weathering, construction style, scale, and RF context. Give both one best value
and a plausible range. Do not decline to estimate merely because a profilometer
would be better. Explain the cues behind the estimate.

Finally, give the short noun phrase SAM 3 should use to segment this surface.
Return one JSON object and nothing else, with exactly these keys:
{{
  "observation": "what is visibly present",
  "dominant_surface": "specific surface description",
  "itu_p2040_material": "one exact row name",
  "rms_height_mm": 0.0,
  "rms_height_range_mm": [0.0, 0.0],
  "roughness_reasoning": "brief physical and visual reasoning",
  "confidence": 0.0,
  "sam3_prompt": "short noun phrase"
}}"""


def parse_surface_estimate(raw: str | dict[str, Any]) -> RfSurfaceEstimate:
    """Validate the model JSON without silently repairing physical fields."""
    payload = _json_object(raw)
    expected = {
        "observation",
        "dominant_surface",
        "itu_p2040_material",
        "rms_height_mm",
        "rms_height_range_mm",
        "roughness_reasoning",
        "confidence",
        "sam3_prompt",
    }
    if set(payload) != expected:
        missing = sorted(expected - set(payload))
        extra = sorted(set(payload) - expected)
        raise ValueError(f"surface estimate keys differ from the contract: missing={missing}, extra={extra}")
    interval = payload["rms_height_range_mm"]
    if not isinstance(interval, list | tuple) or len(interval) != 2:
        raise ValueError("rms_height_range_mm must contain exactly two values")
    return RfSurfaceEstimate(
        observation=str(payload["observation"]),
        dominant_surface=str(payload["dominant_surface"]),
        itu_p2040_material=str(payload["itu_p2040_material"]),
        rms_height_mm=float(payload["rms_height_mm"]),
        rms_height_range_mm=(float(interval[0]), float(interval[1])),
        roughness_reasoning=str(payload["roughness_reasoning"]),
        confidence=float(payload["confidence"]),
        sam3_prompt=str(payload["sam3_prompt"]),
    )


def run_gemini_cli(
    image: pathlib.Path,
    context: RfTargetContext,
    *,
    model: str = GEMINI_MODEL,
    executable: str = "gemini",
    timeout_s: float = 300.0,
) -> GeminiSurfaceRun:
    """Analyze one image through Gemini CLI in an isolated temporary workspace.

    The copy is intentional. Production crops live under the ignored ``outputs``
    tree, which Gemini CLI refuses to inject with ``@``. Isolation also prevents
    the coding agent from searching the repository instead of answering the
    visual question.
    """
    source = pathlib.Path(image).resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    if shutil.which(executable) is None:
        raise FileNotFoundError(f"Gemini CLI executable not found: {executable}")
    prompt = build_rf_prompt(context)
    started = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="aegis-rf-agent-") as temporary:
        workspace = pathlib.Path(temporary)
        target = workspace / f"target{source.suffix.lower()}"
        shutil.copyfile(source, target)
        policy = workspace / "one_turn_policy.toml"
        policy.write_text(ONE_TURN_POLICY)
        completed = subprocess.run(  # noqa: S603 - explicit local CLI executable
            [
                executable,
                "--model",
                model,
                "--approval-mode",
                "default",
                "--policy",
                policy.name,
                "--output-format",
                "json",
                "--prompt",
                f"@{target.name} {prompt}",
            ],
            cwd=workspace,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise RuntimeError(f"Gemini CLI failed with exit code {completed.returncode}: {detail[-2000:]}")
    envelope = _json_object(completed.stdout)
    if "response" not in envelope:
        raise ValueError("Gemini CLI JSON contains no response")
    estimate = parse_surface_estimate(envelope["response"])
    return GeminiSurfaceRun(
        estimate=estimate,
        model=model,
        prompt_version=PROMPT_VERSION,
        prompt_sha256=hashlib.sha256(prompt.encode()).hexdigest(),
        image_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        elapsed_s=time.perf_counter() - started,
        session_id=str(envelope["session_id"]) if envelope.get("session_id") else None,
        stats=envelope.get("stats", {}),
    )


def _json_object(raw: str | dict[str, Any]) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    text = str(raw).strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].strip().lower() in ("```", "```json"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    value = json.loads(text)
    if not isinstance(value, dict):
        raise ValueError("expected one JSON object")
    return value
