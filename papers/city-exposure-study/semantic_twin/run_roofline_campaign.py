"""Compatibility entry point for the production roofline campaign command."""

from __future__ import annotations

from semantic_twin.cli.roofline_campaign import main


if __name__ == "__main__":
    raise SystemExit(main())
