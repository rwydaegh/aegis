# Contributing to AEGIS

## Setup

Use **Python 3.12**. From the repo root:

```bash
pip install -e ".[dev]"
```

On Windows: `py -3.12` instead of `python` if you have multiple versions.

## Test and lint

```bash
py -3.12 -m pytest tests/ -m "not slow" -x
py -3.12 -m ruff check src/ tests/
py -3.12 -m ruff format src/ tests/
```

Full test suite: `py -3.12 -m pytest tests/` (includes slow tests and mesh-dependent cases).

## Scope and style

Keep changes focused. Match existing types and patterns: frozen dataclasses for core types, NumPy on the hot path, no new circular imports (`result` already depends on `compliance`; do not reverse that).

Documentation: sentence case headings, no em dashes or semicolons. See `.claude/rules/docs-style.md`.

Physics changes should match the monograph under `../monograph/` and, where possible, scripts under `../scripts/`.

## Pull requests

Open an issue for non-trivial work. Run the fast tests and ruff before pushing. Reference issues in commit messages when applicable (`Closes #N`).
