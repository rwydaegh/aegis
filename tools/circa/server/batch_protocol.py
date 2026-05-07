from __future__ import annotations
import json
import re
from enum import Enum
from typing import Any

from .annotation import Annotation


_STATUS_FENCE_RE = re.compile(r"```circa-status\s*\n(.*?)\n```", re.DOTALL)


class ParseFallback(str, Enum):
    OK = "ok"
    MISSING = "missing"
    MALFORMED = "malformed"
    PARTIAL = "partial"
    UNKNOWN_IDS = "unknown_ids"
    TIMEOUT = "timeout"


def build_batch_text(pass_: int, annotations: list[Annotation], build_status_text: str) -> str:
    lines = [f"You are reviewing annotations from reading pass {pass_}. Process each in order.", ""]
    lines.append(
        "For mode=edit: apply the edit. Wrap every edit in\n"
        "  % [circa:<id>:begin] / % [circa:<id>:end] fence comments.\n"
        "After the closing fence, on its OWN LINE, if pdfcomment is enabled, append:\n"
        "  \\pdfcomment[author={circa}]{<short summary>} % [circa:<id>]\n"
    )
    lines.append("For mode=ask: do NOT edit; reply via the JSON `clarification` field only.")
    lines.append("")
    lines.append(
        "Conflict policy: two annotations are 'overlapping' if their fenced line ranges in paper.tex would\n"
        "intersect (NOT merely touch the same paragraph). For overlaps, either merge into\n"
        "  % [circa:<id1>+<id2>:begin] / :end\n"
        "(both ids report `status: done` with `one_liner = 'merged with <other id>: <summary>'`),\n"
        "OR set one to `needs_clarification` and edit only the other."
    )
    lines.append("")
    if "broken" in build_status_text.lower():
        lines.append(
            f"Build is broken: {build_status_text}; fix the build first, then handle the annotations."
        )
    else:
        lines.append(f"Build status: {build_status_text}")
    lines.append("")
    lines.append(
        "End your response with a JSON block on its own line, exactly this format:\n"
        "```circa-status\n"
        '{"<id>": {"status": "done"|"needs_clarification", "one_liner": "...", "clarification": "..."}, ...}\n'
        "```\n"
        "Every annotation id in this batch MUST appear in the JSON block."
    )
    lines.append("")
    for i, a in enumerate(annotations, start=1):
        lines.append(f"Annotation {i}: id={a.id}, page {a.page}, shape={a.shape}, mode={a.mode.value}")
        if a.shape == "rect" and len(a.points) == 2:
            (x1, y1), (x2, y2) = a.points
            lines.append(f"  Bounding box (page-normalized): x={x1:.2f}..{x2:.2f}, y={y1:.2f}..{y2:.2f}")
        elif a.shape == "arrow" and len(a.points) == 2:
            (x1, y1), (x2, y2) = a.points
            lines.append(f"  Arrow (page-normalized): start=({x1:.2f}, {y1:.2f}) -> end=({x2:.2f}, {y2:.2f})")
        elif a.shape == "text" and len(a.points) == 1:
            x, y = a.points[0]
            lines.append(f"  Anchor (page-normalized): x={x:.2f}, y={y:.2f}")
        elif a.shape == "pen" and a.points:
            xs = [p[0] for p in a.points]
            ys = [p[1] for p in a.points]
            lines.append(
                f"  Bounding box (page-normalized): x={min(xs):.2f}..{max(xs):.2f}, y={min(ys):.2f}..{max(ys):.2f}"
            )
        lines.append(f'  Note: "{a.text}"')
        if a.parent_id:
            lines.append(f"  parent_id: {a.parent_id} (this is a clarification reply)")
            if a.reply:
                lines.append(f'  Reply text: "{a.reply}"')
        lines.append("")
    return "\n".join(lines)


def parse_status_block(
    message_text: str, expected_ids: list[str]
) -> tuple[dict[str, dict[str, Any]], ParseFallback]:
    matches = _STATUS_FENCE_RE.findall(message_text)
    if not matches:
        return _all_clar(
            expected_ids, "Claude did not return a status block; please rephrase your note."
        ), ParseFallback.MISSING
    last = matches[-1]
    try:
        parsed = json.loads(last)
        if not isinstance(parsed, dict):
            raise ValueError("not a dict")
    except (json.JSONDecodeError, ValueError):
        return _all_clar(
            expected_ids, "Claude did not return a status block; please rephrase your note."
        ), ParseFallback.MALFORMED
    statuses: dict[str, dict[str, Any]] = {}
    fb = ParseFallback.OK
    expected = set(expected_ids)
    for id, info in parsed.items():
        if id not in expected:
            fb = ParseFallback.UNKNOWN_IDS
            continue
        statuses[id] = info
    missing = expected - set(statuses.keys())
    if missing:
        fb = ParseFallback.PARTIAL if fb == ParseFallback.OK else fb
        for id in missing:
            statuses[id] = {
                "status": "needs_clarification",
                "clarification": "Claude did not include this id in the status block; please rephrase.",
            }
    return statuses, fb


def _all_clar(ids: list[str], msg: str) -> dict[str, dict[str, Any]]:
    return {id: {"status": "needs_clarification", "clarification": msg} for id in ids}
