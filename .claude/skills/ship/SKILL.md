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
3. If any files in `kernels/`, `tissue/`, or `coherent/` are in the diff, review the physics changes carefully against `../monograph/summary_paper.tex`
4. List available labels with `gh label list` and pick appropriate ones (create new labels with `gh label create` if none fit)
5. Create GitHub issue with `gh issue create --label <labels>`
6. Create feature branch from master
7. Stage specific files and commit (reference issue with `Closes #N`)
8. Push and create PR with `gh pr create --label <labels>` (same labels as the issue, plus PR-specific ones like `ready for review`)
9. Squash merge with `gh pr merge --squash --delete-branch`
10. Return to master, pull, verify tests pass

## Labels

Always label both issues and PRs. Use multiple labels — be generous. Check existing labels first with `gh label list`. Create new ones freely if no existing label fits well.

Common label categories to apply:
- **Type**: `bug`, `enhancement`, `refactor`, `docs`, `test`, `chore`
- **Area**: `physics`, `geometry`, `viewer`, `kernels`, `tissue`, `coherent`, `compliance`, `integration`, `viz`, `ci`
- **Priority**: `high priority`, `low priority`
- **Status**: `ready for review`, `blocked`

Create new labels with: `gh label create "label-name" --color <hex> --description "short description"`

## Rules

- One PR per logical unit. No bundling unrelated changes.
- Every PR references an issue.
- Both issues and PRs must have labels. No unlabeled items.
- Pre-flight checks must pass before PR creation.
- Squash merge to keep master clean.
- Ship in dependency order when doing multiple phases.
- Handoff docs go in the same PR as their code.
