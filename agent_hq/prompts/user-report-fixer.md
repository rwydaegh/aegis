# User bug report fixer

Fix the bug described in the issue body. This issue was filed by a real user
via the in-app bug reporter (Shift+B). The issue body has:

- **Description** in the user's own words (may be vague or non-technical)
- **Screenshot** of the full page at the time of reporting (may have annotations)
- **App state** table: mode, frequency, power, corrections, antenna position,
  camera mode, sidebar state, legend scale

## How to work

1. Read the issue body carefully. The user's description is the primary signal.
   The screenshot shows exactly what they saw. The app state table tells you what
   configuration they were using.
2. Reproduce mentally: based on the state table, can you figure out what code path
   they hit? A frequency of 60 GHz means above-6GHz quantities. An antennaPos of
   null means no antenna was placed yet. Check these details.
3. Find the relevant source code. For frontend/UI bugs, check `aegis-web/src/`.
   For backend/compute bugs, check `src/aegis/viewer/routes/` and `src/aegis/`.
4. Fix the bug. Run lint and tests.
5. Ship via PR (see `agent_hq/context/how-to-ship.md`).
6. Add "Fixes #ISSUE_NUMBER" to the PR body.

The full cycle is: fix -> commit -> push -> pr create -> pr merge.
Do not stop at just pushing a branch.

## Important differences from automated reports

- **Users may be wrong about what the bug is.** They describe symptoms, not causes.
  A user saying "the heatmap disappeared" might actually be hitting a compute
  failure, a rendering bug, or a state management issue. Investigate before assuming.
- **The description may be minimal.** "It broke" with a screenshot is still useful.
  Look at the screenshot and the state table to figure out what went wrong.
- **Do not dismiss reports.** If you cannot reproduce or identify the issue from
  the information given, comment on the issue explaining what you checked and
  ask for more details. Do not close it.
- **Be conservative with fixes.** User-reported bugs are real-world usage patterns.
  The fix should handle the case, not paper over it.
