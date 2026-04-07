# Review: PR #323 `Add differentiable optimization to viewer`

Date: 2026-04-03
Reviewer: Codex

## Scope

Reviewed merged PR `#323` found via `gh pr list --state merged`.

Reviewed at merge commit:
- `c8f42397b078eb24e7984ebedff1a44d5644cff2`

Feature area covered:
- placement optimization
- tilt/power optimization
- MIMO peak optimization
- SSE streaming route and frontend consumer

## Findings

### 1. High: `tilt_power` cannot start after a normal compute because it reads the wrong cache

`/api/compute` stores the latest dosimetry result on `app.config`, but PR `#323`'s optimize route reads `_last_dosimetry_result` and `_last_dosimetry_body` from the shared `cache` dict instead.

Relevant code:
- `src/aegis/viewer/routes/compute.py`
- `src/aegis/viewer/routes/optimize.py`

Impact:
- A user can run compute successfully and still get `No dosimetry result cached. Run /api/compute first.`
- One of the headline optimization modes is effectively broken end-to-end.

Note:
- This was a shipped bug in PR `#323`, even though current `master` has since changed the route.

### 2. High: placement mode was exposed in the UI but impossible to invoke from the frontend

The frontend sends ordinary JSON for placement mode, but the backend in PR `#323` rejected placement unless `evaluate_fn` was present in the request body.

Relevant code:
- `aegis-web/src/components/panels/OptimizePanel.tsx`
- `aegis-web/src/hooks/useOptimization.ts`
- `src/aegis/viewer/routes/optimize.py`

Impact:
- Browser clients cannot send a Python callable.
- Placement mode was dead on arrival despite being presented as available functionality.

### 3. Medium: `tilt_power` omitted Fresnel transmission `T0`, making the optimizer too conservative

The PR computed `sab` from weighted incident power and cosine incidence only. The spatial dosimetry model includes the normal-incidence Fresnel transmission factor `T0`, so the optimization target was physically inconsistent with the compute pipeline.

Relevant code:
- `src/aegis/optim/tilt_power.py`

Impact:
- `S_ab` is overestimated.
- The optimizer drives transmit power lower than necessary to satisfy the same exposure limit.

Follow-up:
- This was later fixed by PR `#331`, and the full pipeline passthrough was fixed by PR `#343`.

### 4. Medium: the optimization UI could freeze in `running` state if the SSE stream ended abnormally

In PR `#323`, the frontend set `running=true` when starting optimization, but only cleared it on explicit `done` or `error` events. If the stream terminated early or the request was aborted outside those paths, the panel could remain latched in a running state.

Relevant code:
- `aegis-web/src/hooks/useOptimization.ts`

Impact:
- The button can stay stuck on `Stop`.
- Users may be unable to launch another optimization run without refreshing.

Follow-up:
- This was later fixed by PR `#339` with a `finally` block.

## Notes

- I reviewed the feature at the PR merge commit, not against the current dirty worktree.
- Current `master` appears to have repaired these issues, so this note documents bugs that shipped with PR `#323`.
- The biggest test gap in PR `#323` was missing end-to-end coverage for `compute -> optimize` handoff and browser-driven placement mode.
