"""Smoke tests for the completed illumination studies kept in the archive."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from archive.studies.escape_range_study import surplus_db, trace_both_ways  # noqa: E402
from archive.studies.source_thickness_study import coverage, prepare  # noqa: E402

COMMANDS = (
    "measure_escape_range_term.py",
    "measure_source_construction.py",
    "measure_source_near_share.py",
    "measure_source_thickness.py",
)


def test_archived_study_helpers_remain_importable() -> None:
    assert callable(surplus_db)
    assert callable(trace_both_ways)
    assert callable(coverage)
    assert callable(prepare)


@pytest.mark.parametrize("command", COMMANDS)
def test_archived_study_command_help(command: str) -> None:
    completed = subprocess.run(
        [sys.executable, PROJECT_ROOT / "archive" / "scripts" / command, "--help"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        check=False,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert "usage:" in completed.stdout
