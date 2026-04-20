# How to ship changes

## Before you ship — collision check

Ten seconds of `git pull` + `grep` prevents shipping a PR that duplicates or
conflicts with work that landed while you were investigating. Recent examples:
two agents shipped overlapping `setPrecoderType` guards within the same
hour, and a boundary-validation PR duplicated fixes already present on master.

```bash
# 1. Pull latest master. Another agent may have shipped while you were working.
git fetch origin master
git log --oneline HEAD..origin/master   # what landed since you branched?

# 2. Grep the specific symbol, route, or function your PR touches against
#    current master. If it already matches the behaviour you planned to add,
#    your PR is redundant — close it without merging.
git grep -n "<function_or_route_you_are_fixing>" -- src/ tests/
```

If master already contains an equivalent fix, **do not merge a superset or a
subset**. Close the PR with a short comment pointing to the existing fix.
Wasted review cycles and a noisy log are worse than no PR.

## PR workflow (default for all agents)

```bash
# 1. Branch
git checkout -b claude/SHORT-DESCRIPTION

# 2. Edit code. When your fix is ready, update
#    agent_hq/coordination/bulletin.md with your findings IN THE SAME COMMIT —
#    do not create a separate "Update bulletin after PR #N" commit.
git add <specific files> agent_hq/coordination/bulletin.md
git commit -m "Add/Fix/Improve description of the change"

# 3. Push
git push -u origin claude/SHORT-DESCRIPTION

# 4. Create PR and squash merge
gh pr create \
  --title "Add/Fix/Improve description" \
  --body "## Summary
- What changed
- Why

Fixes #N (if applicable)

---
*Built by [\`WORKFLOW_NAME\`](https://github.com/rwydaegh/aegis/actions/workflows/WORKFLOW_NAME) · run [RUN_ID](https://github.com/rwydaegh/aegis/actions/runs/RUN_ID)*" \
  --base master
gh pr merge --squash --delete-branch

# 5. Return to master
git checkout master
git pull origin master
```

## Rules

- One PR per logical change. Do not bundle unrelated fixes.
- Always squash merge. Merge commits are disabled on this repo.
- Stage specific files, not `git add -A`.
- Run lint + tests before committing.
- If addressing an open issue, add "Fixes #N" to the PR body.
- Multiple PRs per session are fine if they are independent.
- **Bulletin edits ride in the ship commit** — never a separate
  "Update bulletin after PR #N" follow-up PR.
- If you shipped a code PR and then realised a bulletin edit was missed,
  amend it into the next PR rather than creating a bulletin-only PR.
