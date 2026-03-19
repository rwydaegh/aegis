---
name: ship
description: Full DevOps workflow - create issue, branch, commit, PR, and merge using gh CLI
user-invocable: true
---

# /ship - DevOps shipping workflow

Ship a logical unit of work through the full GitHub workflow: issue, branch, commit, PR, merge.

## Usage

```
/ship                    # auto-detect and ship current changes
/ship <description>      # ship with a description
/ship --phase <name>     # ship a named phase
```

## Steps

1. Analyze changes with `git status -s` and `git diff --stat`
2. Run pre-flight: ruff check, ruff format, pytest fast tests
3. If any files in `kernels/`, `tissue/`, or `coherent/` are in the diff, run `/physics-review` first
4. Create GitHub issue with `gh issue create`
4. Create feature branch from master
5. Stage specific files and commit (reference issue with `Closes #N`)
6. Push and create PR with `gh pr create`
7. Squash merge with `gh pr merge --squash --delete-branch`
8. Return to master, pull, verify tests pass

## Rules

- One PR per logical unit. No bundling unrelated changes.
- Every PR references an issue.
- Pre-flight checks must pass before PR creation.
- Squash merge to keep master clean.
- Ship in dependency order when doing multiple phases.
- Handoff docs go in the same PR as their code.
