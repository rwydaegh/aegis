# Agent environment (GitHub Actions ubuntu-latest)

## What you have

- Python 3.x (use python3). Full scientific stack after `pip install -e '.[dev]'`.
- Node.js and npm (for frontend work: `cd aegis-web && npm install && npm run build`).
- Phantom mesh STL files in `data/` (tracked in git, available after checkout).
- IT'IS tissue database in `data/itis_v5.db`.
- Channel presets in `data/channel_presets/`.
- All tests work, including `@pytest.mark.slow` mesh-dependent tests.
- Playwright for E2E testing against production (`npx playwright open`).
- gh CLI for GitHub API (issues, PRs, labels).
- Full internet access (Overpass API, npm registry, PyPI, etc.).

## What you do NOT have

- No GPU. Sionna RT runs on CPU (slower but works). JAX runs on CPU.
- No display server. Cannot visually verify frontend changes, but can lint
  (`npx tsc --noEmit`), build (`npm run build`), and reason from code.
- No access to the production server (deploy is automatic on push to master).

## Setup

```bash
python3 -m pip install -e '.[dev]' --quiet
```

## Testing

```bash
python3 -m pytest tests/ -x --tb=short -q           # all tests including slow/mesh
python3 -m pytest tests/ -m 'not slow' -x --tb=short -q  # fast tests only
python3 -m ruff check src/ tests/                    # lint
python3 -m ruff format src/ tests/                   # format
```
