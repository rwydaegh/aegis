"""Smoke tests for the build CLI."""

import subprocess
import sys


def test_build_cli_help():
    """Verify the build CLI is importable and has expected subcommands."""
    result = subprocess.run(
        [sys.executable, "-m", "aegis.basestation.build", "--help"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0
    assert "extract" in result.stdout
    assert "merge" in result.stdout
    assert "validate" in result.stdout
    assert "report" in result.stdout
