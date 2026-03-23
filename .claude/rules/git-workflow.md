---
description: Git commit, push, and branching conventions for AEGIS
---

# Git workflow

This is a vibe-coded project. Claude is often the only one making changes in a session, so committing and pushing is Claude's responsibility. Treat it as a reflex, not an afterthought.

## When to commit

- After completing a logical unit of work (new feature, bug fix, test suite, refactor).
- Before switching to a different area of the codebase.
- Before any risky or experimental change, so there is a clean rollback point.
- At the end of every session, commit any uncommitted work. Do not leave the repo dirty.
- Do NOT commit after every tiny edit. One commit per logical change, not per file touched.

## How to commit

- Run `py -3.12 -m ruff check src/ tests/` and `py -3.12 -m ruff format --check src/ tests/` before committing. Fix issues first.
- Optionally run `py -3.12 -m pytest tests/ -m "not slow" -x` locally. CI runs `pytest tests/` on every push and PR.
- Stage specific files, not `git add -A`. Review what you are committing.
- Write commit messages in imperative mood ("Add level 3 kernel", not "Added level 3 kernel").
- First line under 72 chars. Add a blank line and body for non-trivial changes.
- No fixup/wip commits on master. Every commit on master should be a clean, passing state.

## When to push

- After every commit, push to origin/master. GitHub Actions CI (lint + test matrix) runs on push but there is no branch protection, so pushing is safe and ensures work is backed up.
- If the push fails (someone else pushed, or network issues), pull with rebase first: `git pull --rebase origin master`.

## Branching

- For now, work directly on master. The project is young and single-developer.
- If a change is large or experimental (touching 5+ files across multiple modules), create a feature branch, commit there, then ask the user before merging to master.
- Branch naming: `feature/short-description`, `fix/short-description`, `refactor/short-description`.

## Versioning

Version is automatic via `hatch-vcs` (derived from git tags). Claude is responsible for tagging releases.

### When to tag

- **Patch** (`v0.3.0` -> `v0.3.1`): bug fix, test fix, doc fix, small correction.
- **Minor** (`v0.3.x` -> `v0.4.0`): new feature, new kernel, new module, meaningful capability added.
- **Major** (`v0.x` -> `v1.0.0`): only when the user says so (paper submission, stable API).

Tag after merging or committing work that fits one of these categories. Do not tag after pure refactors, CI changes, or config tweaks unless they fix a bug.

### How to tag

```bash
git tag v0.X.Y
git push origin master --tags
gh release create v0.X.Y --generate-notes
```

`--generate-notes` auto-builds a changelog from commits since the last tag. If the auto-generated notes are poor (too many commits, unclear), write a short summary in the release body instead.

### Between tags

Dev installs automatically show `0.X.Y.dev3+g<hash>`. No manual version bumps needed.

## What not to commit

No `.env`/credentials, no large binaries (STL), no generated files (`site/`, `__pycache__/`, `_version.py`, coverage). All covered by `.gitignore`.
