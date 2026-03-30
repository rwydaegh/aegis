# QA bug fixer

Fix the bug described in the issue body. The issue was filed by an automated QA
agent that found the problem via Playwright testing on production. The issue body
has:

- Description of what happened vs what was expected
- Steps to reproduce
- Sometimes a screenshot

## How to work

1. Read the issue body. The repro steps show exactly how to trigger it.
2. Find the relevant source code. For frontend bugs, check `aegis-web/src/`.
   For backend bugs, check `src/aegis/viewer/routes/`.
3. Fix the bug. Run lint and tests.
4. Ship via PR (see `agent_hq/context/how-to-ship.md`).
5. Add "Fixes #ISSUE_NUMBER" to the PR body.

The full cycle is: fix -> commit -> push -> pr create -> pr merge.
Do not stop at just pushing a branch.
