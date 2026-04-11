# Handling Sentry bug reports

When you are tagged on a GitHub issue with the `sentry` label, it was auto-created from a production error. The issue body contains:

- **Stack trace** with the error and source location
- **Breadcrumbs** showing the user's last ~15 actions (clicks, fetches, navigation)
- **Simulation state** (frequency, power, mode, antenna position, MIMO config, etc.)
- **UI state** (camera mode, sidebar, legend scale)
- **Browser/OS** info

## Workflow

1. Read the issue body carefully. The breadcrumbs show exactly what the user did to trigger the error.
2. Find the source location from the stack trace. Source maps may show minified names, so grep for the error message or nearby code.
3. Investigate the root cause. Check the backend route if it is a server error (5xx).
4. Fix the bug on a feature branch (`fix/sentry-ISSUE_ID`).
5. Run lint and tests: `python -m ruff check src/ tests/` and `python -m pytest tests/ -m "not slow" -x`.
6. Create a PR referencing the issue. Squash merge it.
7. After the PR is merged, deploy happens automatically. Sentry release tracking auto-resolves the issue if the error stops recurring.

## Post-merge verification

After the deploy completes (~5 min after merge), the fix is live on production. You do not need to verify manually. If the fix is wrong, the same error will recur and Sentry will create a new regression issue automatically.

## What not to do

- Do not weaken error handling to suppress the error
- Do not add try/catch blocks that swallow errors silently
- Do not mark Sentry issues as resolved (release tracking handles this)
- Do not push directly to master. Always use a branch and PR with squash merge.

# Important 

It's OK to give up at one point if you don't feel confident you can fix the error (eg its too obscure or you cant in this environment, or you're just guessing a lot). This is an automated script environment after all, and the maintainer isn't here for you at this time. Instead it would be better to delegate it sometimes to the user paired up with an interactive claude code session. If so, just keep the issue open and comment about it on GitHub. Tag the maintainer.
