# How to ship changes

## PR workflow (default for all agents)

```bash
# 1. Branch
git checkout -b claude/SHORT-DESCRIPTION

# 2. Commit (imperative mood, under 72 chars)
git add <specific files>
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
