"""Compatibility facade for the historical next-event runner.

Use ``python -m semantic_twin.cli.next_event`` for new work.  The historical
filename remains importable because captures and notebooks refer to it.
"""

from __future__ import annotations

import sys

from semantic_twin.cli import next_event as _command
from semantic_twin.exposure.next_event_study import NextEventStudyConfig, run_next_event_study  # noqa: F401

arguments = _command.arguments
config_from_arguments = _command.config_from_arguments


def main(argv: list[str] | None = None) -> int:
    """Delegate parsing and dispatch while preserving the old monkeypatch hook."""
    original = _command.run_next_event_study
    try:
        _command.run_next_event_study = run_next_event_study
        return _command.main(argv)
    finally:
        _command.run_next_event_study = original


if __name__ == "__main__":
    sys.exit(main())
