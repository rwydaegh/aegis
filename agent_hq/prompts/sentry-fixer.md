# Sentry bug fixer

Fix the bug described in the issue body. The issue was auto-created from a
production Sentry error and contains:

- **Stack trace** with the error and source location
- **Breadcrumbs** showing the user's last ~15 actions
- **Simulation state** (frequency, power, mode, antenna position, MIMO config)
- **UI state** (camera mode, sidebar, legend scale)
- **Browser/OS** info

## How to work

1. Read the issue body carefully. Breadcrumbs show what the user did to trigger it.
2. Find the source location from the stack trace. Source maps may show minified
   names, so grep for the error message or nearby code.
3. Investigate root cause. Check the backend route if it is a server error (5xx).
4. Fix the bug. Run lint and tests.
5. Ship via PR (see `agent_hq/context/how-to-ship.md`).
6. Add "Fixes #ISSUE_NUMBER" to the PR body.

## What NOT to do

- Do not weaken error handling to suppress the error
- Do not add try/catch blocks that swallow errors silently
- Do not mark Sentry issues as resolved (release tracking handles this)
