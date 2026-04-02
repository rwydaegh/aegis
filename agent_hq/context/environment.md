# Agent environment

## Common (all execution modes)

- Python 3.x (use python3). Full scientific stack after `pip install -e '.[dev]'`.
- Node.js and npm (for frontend work: `cd aegis-web && npm install && npm run build`).
- Phantom mesh STL files in `data/` (tracked in git, available after checkout).
- IT'IS tissue database in `data/itis_v5.db`.
- Channel presets in `data/channel_presets/`.
- All tests work, including `@pytest.mark.slow` mesh-dependent tests.
- Playwright for E2E testing against production (`npx playwright open`).
- gh CLI for GitHub API (issues, PRs, labels).
- Full internet access (Overpass API, npm registry, PyPI, etc.).
- No local GPU. Sionna RT and JAX run on CPU. GPU ray tracing is available via
  Modal (DiffeRT on T4, Sionna on L4) but has ~30s cold start on production.
  If you need a local GPU, flag it in the bulletin and Robin can provision one.

## When running locally (cron on the dev machine)

- You run in an isolated git worktree at `/tmp/aegis-agent-<name>-<pid>`.
- Per-agent lock files prevent the same agent from running twice. Different agents
  can run in parallel.
- The main repo at `/home/user/aegis` is Robin's working directory. Do not touch it
  directly. Your worktree is your workspace.
- gh CLI is authenticated as `rwydaegh`.

## When running on GitHub Actions

- Fresh ubuntu-latest checkout each run.
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
