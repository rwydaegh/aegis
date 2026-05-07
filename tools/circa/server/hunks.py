"""Per-annotation diff hunks captured at edit-time, reverse-applied via git apply -R.

Hunks are extracted from a unified diff (3 lines of context) between the snapshot
and post-batch paper.tex. Each hunk is assigned to the annotation id(s) found in
% [circa:<id>...] markers within its added lines. Reverse-apply uses default
context-line verification (NO --unidiff-zero) to prevent silent line-shift corruption.
"""

from __future__ import annotations

import difflib
import json
import re
import subprocess
from pathlib import Path
from typing import Optional

from . import paths


_FENCE_RE = re.compile(r"%\s*\[circa:([^\]]+):(?:begin|end)\]")


def _ids_from_fence_payload(payload: str) -> set[str]:
    """'abc' -> {'abc'}, 'abc+def' -> {'abc', 'def'}."""
    return set(payload.split("+"))


def _split_unified_diff_into_hunks(diff_text: str) -> list[str]:
    """Split a unified diff into per-hunk diffs, each prefixed with the file headers."""
    lines = diff_text.splitlines(keepends=True)
    if not lines:
        return []
    headers: list[str] = []
    body_start = 0
    for i, line in enumerate(lines):
        if line.startswith("--- "):
            headers = lines[i : i + 2]
            body_start = i + 2
            break
    chunks: list[list[str]] = []
    cur: list[str] = []
    for line in lines[body_start:]:
        if line.startswith("@@"):
            if cur:
                chunks.append(cur)
            cur = [line]
        else:
            cur.append(line)
    if cur:
        chunks.append(cur)
    return ["".join(headers + c) for c in chunks]


def _ids_in_hunk(hunk_text: str) -> set[str]:
    ids: set[str] = set()
    for line in hunk_text.splitlines():
        if not line.startswith("+"):
            continue
        for m in _FENCE_RE.finditer(line):
            ids |= _ids_from_fence_payload(m.group(1))
    return ids


class HunkManager:
    def __init__(self, paper_dir: Path) -> None:
        self.paper_dir = paper_dir
        self.paper_tex = paper_dir / "paper.tex"

    def extract_for_batch(self, batch_id: str, annotation_ids: list[str]) -> dict[str, str]:
        snap = paths.snapshots_dir(self.paper_dir) / f"{batch_id}.tex"
        pre = snap.read_text().splitlines(keepends=True)
        post = self.paper_tex.read_text().splitlines(keepends=True)
        diff = "".join(difflib.unified_diff(pre, post, fromfile="a/paper.tex", tofile="b/paper.tex", n=3))
        result: dict[str, str] = {}
        for hunk in _split_unified_diff_into_hunks(diff):
            for aid in _ids_in_hunk(hunk) & set(annotation_ids):
                result[aid] = hunk
        return result

    def persist_for_batch(self, batch_id: str, annotation_ids: list[str]) -> None:
        hunks = self.extract_for_batch(batch_id, annotation_ids)
        out = paths.hunks_dir(self.paper_dir) / f"{batch_id}.jsonl"
        with out.open("w") as f:
            for aid, hunk in hunks.items():
                f.write(json.dumps({"id": aid, "batch_id": batch_id, "hunk": hunk}) + "\n")

    def load_hunk(self, annotation_id: str) -> Optional[str]:
        for p in paths.hunks_dir(self.paper_dir).glob("*.jsonl"):
            for line in p.read_text().splitlines():
                if not line:
                    continue
                entry = json.loads(line)
                if entry["id"] == annotation_id:
                    return entry["hunk"]
        return None

    def apply_reverse(self, annotation_id: str) -> None:
        hunk = self.load_hunk(annotation_id)
        if hunk is None:
            raise RuntimeError(f"no hunk for annotation {annotation_id}")
        # Pre-check with default context verification (NOT --unidiff-zero).
        check = subprocess.run(
            ["git", "apply", "--check", "-R", "--whitespace=nowarn", "-"],
            input=hunk,
            text=True,
            cwd=self.paper_dir,
            capture_output=True,
        )
        if check.returncode != 0:
            raise RuntimeError(f"conflict applying reverse hunk for {annotation_id}: {check.stderr}")
        apply = subprocess.run(
            ["git", "apply", "-R", "--whitespace=nowarn", "-"],
            input=hunk,
            text=True,
            cwd=self.paper_dir,
            capture_output=True,
        )
        if apply.returncode != 0:
            raise RuntimeError(f"git apply failed: {apply.stderr}")
