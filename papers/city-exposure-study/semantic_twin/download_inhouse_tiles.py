"""Compatibility command for the historical tile acquisition filename.

Use ``python -m semantic_twin.cli.tiles`` for new work. The old filename stays
because acquisition records and mesh documentation still reference it.
"""

from __future__ import annotations

from semantic_twin.cli.tiles import api_key, arguments, finite_float, main, positive_int  # noqa: F401


if __name__ == "__main__":
    raise SystemExit(main())
