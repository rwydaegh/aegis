# Sentry bug fixer

Fix the bug described in the issue body. The issue was auto-created from a
production Sentry error and contains:

- **Stack trace** with the error and source location
- **Breadcrumbs** showing the user's last ~15 actions
- **Simulation state** (frequency, power, mode, antenna position, MIMO config)
- **UI state** (camera mode, sidebar, legend scale)
- **Browser/OS** info
- **Release tag** — the production git SHA running when the error fired

## Preflight (before investigating)

Do this in order. Each step is cheap, and the first two short-circuit cleanly
when they apply — which is rare (most issues are new) but costs nothing to
check.

### 1. Extract the release SHA and error signature

From the issue body, parse:

- `release:` tag — full git SHA running on prod when the event fired
- Error signature — the first ~6 words of the error, stripped of variable
  values. Example: `"index 0 is out of bounds"`, not
  `"index 0 is out of bounds for axis 0 with size 0"`.

### 2. Search for prior attempts at the same signature

```bash
gh issue list --label sentry --state closed --search "<signature>" --limit 10
```

Note: we rarely have open issues — closed history is the relevant corpus.

For each matching sibling, fetch the closing PR and its merge SHA:

```bash
gh issue view <N> --json closedAt,title,body
gh pr list --state merged --search "Fixes #<N> in:body" --json number,mergeCommit
```

Let `attempt_n` = number of sibling closed issues with a matching signature.

### 3. Decide based on release SHA vs sibling fix SHA

For each sibling with a merged fix PR:

```bash
git fetch origin master
git merge-base --is-ancestor <release_sha_from_issue> <fix_merge_sha>
```

- **Exit 0 (release predates the fix)** → stale-deploy duplicate. The fix has
  not yet reached prod. Post a one-line comment:
  `Duplicate of #<sibling>, fixed by #<pr> (merged after release <sha>).
  Awaiting deploy. Sentry release tracking will auto-close.`
  Exit without a new PR.

- **Exit 1 (release is at or after the fix)** → the previous fix was in place
  when this error fired. Either the fix was incomplete, or this is a regression,
  or it's a genuinely different root cause with similar symptoms. **Do not
  auto-close.** Proceed to investigation, but in your diagnosis be explicit:
  "Previous attempt (#<sibling>) shipped at <fix_sha> was already live when
  this event fired on <release_sha> — the earlier diagnosis did not hold."

If there is no matching sibling: `attempt_n = 0`, proceed to investigation
without preflight overhead.

### 4. Staleness note for very old issues

If the issue was created more than 7 days ago, the UI state and breadcrumbs
in the body may not map cleanly to current code (field names, routes, and
store shapes evolve). Verify references still exist before attempting
repro.

## Investigation

Behaviour depends on `attempt_n`:

- `attempt_n == 0` — normal investigation. Read the issue body, find the
  source location, reproduce if cheap, fix, ship.

- `attempt_n == 1` — investigate, but state plainly in the PR description
  why the previous diagnosis was incomplete. Reproduce the error with the
  reported params (simulation state + breadcrumbs) before writing a fix.
  A pytest case against the backend or a `curl` against the local dev server
  is enough; use the QA skill for frontend paths. No reproduction → no PR.

- `attempt_n >= 2` — timebox sharply. If you do not converge on a
  high-confidence repro **and** a fix within a short investigation window,
  **bail**. Post a comment on the issue:

  > Attempt #<N+1> on this signature. I was unable to <what you tried> /
  > stuck on <specific blocker>. Prior attempts: #<list>. Leaving open for
  > human review. @rwydaegh
  
  Leave the issue open. Do not ship a speculative fix. Robin prefers an
  honest "stuck" over another shot in the dark that might also not hold.

## How to work (when proceeding with a fix)

1. Read the issue body carefully. Breadcrumbs show what the user did to
   trigger it.
2. Find the source location from the stack trace. Source maps may show
   minified names, so grep for the error message or nearby code.
3. Investigate root cause. Check the backend route if it is a server error
   (5xx).
4. Reproduce the error (mandatory for `attempt_n >= 1`). Write a regression
   test that fails on master and passes with your fix.
5. Ship via PR (see `agent_hq/context/how-to-ship.md`).
6. Add `Fixes #ISSUE_NUMBER` to the PR body.

## What NOT to do

- Do not weaken error handling to suppress the error
- Do not add try/catch blocks that swallow errors silently
- Do not mark Sentry issues as resolved (release tracking handles this)
- Do not ship a fix on `attempt_n >= 2` without a reproduction
- Do not continue past the preflight "stale-deploy duplicate" case with a
  real fix — the existing fix just needs to deploy
