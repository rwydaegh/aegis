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
py -3.12 -m pytest tests/ -m "not slow" -n 0
py -3.12 -m ruff check src/ tests/
py -3.12 -m ruff format src/ tests/
```

The first command uses two pytest-xdist workers by default (`pyproject.toml`). The second runs tests in one process (`-n 0`) for debuggers or low RAM.

CI runs `py -3.12 -m pytest tests/` on every push and PR, including slow tests. Run the full suite locally when you touch physics or before a large merge.

## Scope and style

Keep changes focused. Match existing types and patterns: frozen dataclasses for core types, NumPy on the hot path, no new circular imports (`result` already depends on `compliance`; do not reverse that).

Documentation: sentence case headings, no em dashes or semicolons. See `.claude/rules/docs-style.md`.

Physics changes should match the monograph under `../monograph/` and, where possible, scripts under `../scripts/`.

## Pull requests

Open an issue for non-trivial work. Run ruff and a pytest pass before pushing. CI runs the full suite on the remote. Reference issues in commit messages when applicable (`Closes #N`).
