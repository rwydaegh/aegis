"""Source-checkout package shim for the ``src`` layout.

This repository uses ``src/aegis`` for the real package code. Creating a
lightweight package at the repository root keeps ``python -m aegis...``
working from an uninstalled checkout, which is important for subprocess CLIs
and local developer workflows.
"""

from __future__ import annotations

from pathlib import Path

_SRC_PACKAGE = Path(__file__).resolve().parent.parent / "src" / "aegis"

if not _SRC_PACKAGE.is_dir():
    raise ImportError(f"Expected source package at {_SRC_PACKAGE}")

__path__ = [str(_SRC_PACKAGE)]
__file__ = str(_SRC_PACKAGE / "__init__.py")

with (_SRC_PACKAGE / "__init__.py").open("rb") as f:
    exec(compile(f.read(), __file__, "exec"), globals(), globals())
