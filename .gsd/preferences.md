---
version: 1

# === Model routing ===
models:
  research: claude-opus-4-7
  planning: claude-opus-4-7
  execution: claude-sonnet-4-6
  execution_simple: claude-haiku-4-5-20251001
  completion: claude-sonnet-4-6
  subagent: claude-sonnet-4-6

token_profile: balanced

# === Git ===
auto_push: true
main_branch: master
merge_strategy: squash
isolation: worktree
commit_docs: true
manage_gitignore: true

# === Verification ===
verification_commands:
  - "python -m ruff check src/ tests/"
  - "python -m ruff format --check src/ tests/"
  - "python -m pytest tests/ -m 'not slow' -x"
verification_auto_fix: true
verification_max_retries: 2

# === Budget ===
budget_enforcement: pause

# === Reports ===
auto_report: true
---

# AEGIS project preferences

## Project context

AEGIS computes absorbed power density on human bodies in wireless environments. The core equation is `Sab(r) = Sinc * T0 * ReLU[n_hat(r) * (-k_hat)]`. Nine fidelity levels (0-8), from O(1) bounds to coherent MIMO beamforming.

## Python environment

This machine has Python 3.14 (system) and 3.12 (user). AEGIS is installed under 3.12. Use `python` (with venv or PATH set to 3.12). On Windows with multiple versions, `py -3.12` also works.

## Custom instructions

- NumPy-only core. No JAX yet.
- Type annotations on public API. No docstrings on private helpers unless non-obvious.
- No em dashes, no semicolons. Sentence case for headings.
- Never weaken assertions to make tests pass. Fix the code, not the test.
- The Mie regression test is the CI canary. If it passes, physics are correct.
- Theory lives in `../monograph/`. Read before implementing physics.
- Ground truth scripts live in `../scripts/`. Validate extractions against them.
- Phantom meshes (STL) and IT'IS tissue database live in `data/`.
