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
- Run `py -3.12 -m pytest tests/ -m "not slow" -x` before committing. All fast tests must pass.
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

## What not to commit

No `.env`/credentials, no large binaries (STL), no generated files (`site/`, `__pycache__/`, coverage). All covered by `.gitignore`.
