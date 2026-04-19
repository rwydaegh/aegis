# Testing infrastructure overhaul 2026-04-18

An honest post-mortem of the testing-roadmap execution. Five waves, twelve merged PRs, twelve real production bugs caught, four-hundred-plus new tests. Written same day, while it's still fresh.

## TL;DR

- **Worth it overall, unevenly.** Three waves produced 92% of the bug yield. The other waves added infrastructure that will earn its keep on future changes but produced zero bugs first-run.
- **Bug haul: 12 real production bugs.** 1 critical, 5 serious/high, 6 minor. All fixed in the same PR as the test that caught them.
- **Forecast was 60-180 bugs; actual was 12.** The gap isn't pessimism unrewarded; it's that the physics core is already very solid and most of the rot is on the HTTP surface, which three waves flushed out.
- **Biggest ROI per hour: Wave 3F (integration tests) and Wave 3E (basedpyright on routes).** Biggest miss: Wave 5J (Pynguin) produced zero useful tests from thirty-one generated, documented as skip-permanently.
- **Next step: tag v0.30.0.** Meaningful new capability across three testing tiers, twelve production bug fixes, four-hundred-plus new tests.

## What landed on master

Twelve PRs squash-merged, plus five CI-discipline commits pushed directly when agents merged through red CI and broke the pipeline.

| PR | SHA | Scope | Real bugs caught |
|---|---|---|---|
| #630 | `131f7f9` | Branch coverage, ruff PT, pytest-randomly, config unify, delete 30 tautological tests | 0 |
| #637 | `d8b7197` | basedpyright strict on kernels + compliance (483 errors → 0) | 0 |
| #634 | `85954a0` | Frontend vitest coverage + TS strict verified + Codecov frontend flag | 0 |
| #638 | `6b2e01c` | Ten Playwright E2E specs for core viewer flows | 0 |
| #641 | `aed2ca1` | basedpyright strict on viewer/routes (3922 errors → 0) | **7** |
| #642 | `b8fc8e3` | 164 real integration tests, no mocks, five highest-traffic routes | **3** |
| #643 | `e69e917` | OpenAPI spec + Schemathesis at patch-release tier | **1** |
| #644 | `1faee11` | Hypothesis RuleBasedStateMachine on MIMO and optimize lifecycle | 0 |
| #648 | `e5d1a52` | Pynguin experiment on compliance, negative result documented | 0 |
| #647 | `9872528` | mutmut audit on fresnel + _parsing at minor-release tier | 0 |
| #645 | `c368dac` | Six monograph-derived metamorphic relations, 154 test cases | 0 |
| #646 | `4118595` | Visual regression at minor-release tier, 7 HUD baselines | 0 |

Direct-to-master commits (unblocking broken CI the agents had been merging through):
- `5afbf0d` demote basedpyright reportAny
- `2d3629c` scope vitest to src so it ignores Playwright specs
- `9c59b57` install --extra viewer in CI so basedpyright can resolve flask
- `b21ecd9` demote reportUnknown* family (was still exit-1'ing on 3196 warnings)
- `ae3ab39` return 400 for ValueError in /api/compute (real bug Schemathesis caught)

That last one counts as bug number twelve.

## Bugs caught, per severity

### Critical (1)
- `/api/compute/rt` crashed with 500 whenever `mode=bound` or `level <= 1` was passed. Non-RT path silently derives `A_ab` and `D_max`, RT path called the engine directly without them. Fixed in #642 by injecting the derived params at the RT entry.

### Serious / high (5)
- `/api/environment/geojson` raised `AttributeError: 'int' object has no attribute 'split'` on numeric height properties. Backend helper assumed OSM-style strings. Fixed in #642.
- Placement optimize rejected valid requests as "Invalid mode/level parameters" when neither was passed, bypassing the default fallback. Fixed in #642.
- `_parse_vec3` accepted antenna positions at `|v| > 1e200`, overflowing `np.linalg.norm` to inf and producing silent NaN `k_hat`. Surfaced as raw 500. Fixed in #643.
- `/api/compute` leaked `ValueError("Level 7 requires a precoder")` as 500 instead of 400 (client validation failure). Fixed inline during CI cleanup.
- `/api/compute/rt` passed `env_mesh=None` to `to_differt_scene` when env_source RT ran without a loaded mesh, crashing on attribute access. Fixed in #641 as a clean 400.

### Minor (6)
- `compute/rt.py:192` passed `voxel_sizes=None` to `prepare_for_raytracing`, which expected ndarray. Fixed in #641 as a 400.
- `optimize.py:327` and `:370` had the same None-pass pattern in the placement optimizer. Fixed in #641.
- `analysis.py:282` had an unnarrowed Optional on `ref_sab` that would have crashed downstream. Fixed in #641.
- `basestations/_data.py:80` passed `region=None` to `load_basestations` which required str. Fixed in #641.
- `basestations/_data.py:111` and `_compute_mimo.py:137` called `scoped_cache_get("basestations")` without an `or []` guard, so cache misses returned None and tripped downstream iteration. Fixed in #641 with explicit guards.
- `mimo.py:403` had `results_stats` possibly None without an `or {}` guard. Fixed in #641.

## What each wave actually bought

### Wave 1: Free wins (PR #630)
Added pytest-randomly, branch coverage, ruff PT. Deleted 30 tautological tests. Unified config from 580-line Python DEFAULTS dict into a single packaged JSON resource.

**Bugs caught: 0.** Zero order-dependence bugs across three seeds (auto, 12345, 987654). Zero PT-rule violations hidden in route or kernel code beyond 32 mechanical fixes in test files.

**Verdict: worth it for hygiene.** Three sharper-signal tools now run on every PR. The config unification paid for itself immediately by removing `test_config_drift.py`, a test that only existed to patch over a design smell.

### Wave 2B: basedpyright on kernels + compliance (PR #637)
483 errors → 0. The config demotes `reportAny` and friends because JAX returns untyped results at every boundary.

**Bugs caught: 0.** The surviving annotations catch no real defects but do document intent on 3,900+ symbols and will catch the next Optional mistake someone writes.

**Verdict: future insurance.** Not a bug-catcher, a refactor-protector. The value shows up next quarter, not this week.

### Wave 2C: Frontend coverage + TS strict (PR #634)
Added `@vitest/coverage-v8`. Verified TS strict was already on; it had been since the recent `Peaks` type fix.

**Bugs caught: 0.** Coverage reported 7.5% line, 21% function. That low number is itself the signal: ~2,500 lines of hooks and stores have zero tests. Fertile ground for future waves, not this one.

**Verdict: infrastructure.**

### Wave 2D: Ten E2E specs (PR #638)
Committed 10 Playwright specs covering scenario load, frequency set, fidelity toggle, optimize, export, share-link, multi-body, MIMO, tilt-power. Added `data-testid` attributes to the HUD components that needed them.

**Bugs caught: 0.** The viewer behaved on every core flow. Tilt-power spec left as `fixme` because RT compute without Modal GPU hits the 120s timeout, which is an environment limitation, not a bug.

**Verdict: worth it.** These are the first real E2E specs in repo. They'll catch the next breaking UI change.

### Wave 3E: basedpyright on viewer/routes (PR #641) **★**
3922 errors → 0 over 24 files. Custom ruleset for routes: keep real-bug checks (Optional handling, return-type, argument-type, call-issue, attribute access) at error level; demote reportUnknown\* to information because Flask `request.get_json()` and numpy reductions return untyped values at boundaries and TypedDict'ing every request body is pure churn.

**Bugs caught: 7.** All None-passed-where-typed. Several would have 500'd on specific user paths. See table above.

**Verdict: big win.** Three hours of agent work, seven production bugs. The route code was where the Sentry issues hid, and now the type checker enforces the contract that would have prevented them.

### Wave 3F: 164 real integration tests (PR #642) **★**
No mocks of the compute stack. Real DosimetryEngine, real body meshes (e2e_icosahedron for fast, thelonious and eartha for slow), real scenes. Per-route: happy path, 400 on invalid, coordinate-frame boundary, large-body smoke, edge-float, unicode.

**Bugs caught: 3.** One critical (bound/level compute crash on RT), one serious (geojson numeric height), one serious (placement optimize rejecting valid requests).

Coverage on the five highest-traffic routes went from 0% to roughly 60–75% each. Full-suite time went from 67s to 75s.

**Verdict: biggest single win.** Six hours, three real bugs, first real end-to-end proof that the HTTP surface does what it claims. These tests will catch the next regression before it reaches Sentry.

### Wave 4G: OpenAPI + Schemathesis (PR #643) **★**
17 operations documented with apispec. Schemathesis wired into release.yml at patch-release tier (5 min budget). `scripts/fuzz_api.sh` for local deep runs.

**Bugs caught: 1.** The antenna-pos magnitude overflow at `|v| > 1e200`. Plus a CI-cleanup bug later: ValueError leaking as 500.

**Verdict: worth it.** The overflow is a genuinely non-obvious bug (who tests at 1e200?). The real value is forward-looking: every new route added must round-trip through OpenAPI validation on next release, which kills a class of schema-drift bugs permanently.

### Wave 5H: Hypothesis stateful (PR #644)
Two RuleBasedStateMachine tests. MIMO precoder lifecycle across set-frequency, set-power, set-layout, apply-mask, compute. Optimize lifecycle across start, cancel, preempt, summary query, with 50 examples × 30 steps each.

**Bugs caught: 0.** Every invariant held. The optimize route's `_cancel_events` bookkeeping (fire-and-replace in start, pop in finally) survived the pressure cases. This is evidence that the lifecycle code is correct under any event ordering, not evidence that the test was weak.

**Verdict: regression insurance.** Locks in invariants that would otherwise only be implicit.

### Wave 5I: mutmut audit (PR #647)
Mutation testing on `src/aegis/tissue/fresnel.py` and `src/aegis/viewer/routes/compute/_parsing.py`.

- fresnel: 77% → 89% mutation score, 22 survivors triaged, 32 new precision anchors added
- _parsing: 70% → 96% mutation score, 10 surviving mutants all killed by new tests

**Bugs caught: 0.** Only test-quality gaps. Every survivor was a weak assertion, not a code defect.

**Verdict: worth it specifically as audit.** A 10% mutation-score bump on the two most physics-critical files, baseline established for future minor-release reports.

### Wave 5J: Pynguin experiment (PR #648)
Ran Pynguin on `src/aegis/compliance/`. 31 tests generated in 420s. Every single one fell into one of: module-constant tautology, brittle `summary_text` snapshot, xfail on nonsense without failure-mode assertion, or duplicate of existing hand-written test.

**Bugs caught: 0. Tests kept: 0.**

**Verdict: not useful for this module. Skip permanently.** Documented in `docs/internal/pynguin_experiment_2026-04-18.md`. Valuable as a negative result because it saves the next person the detour.

### Wave 5K: Visual regression (PR #646)
Seven `toHaveScreenshot()` specs against HUD components. Chromium SwiftShader for deterministic GL. Frozen clock, seeded RNG, disabled animations, font smoothing off. Baselines committed to `aegis-web/tests/e2e/__snapshots__/`. Wired at minor-release tier and manual workflow_dispatch.

**Bugs caught: 0.** All seven baselines matched intent on first capture.

**Verdict: regression insurance.** Catches the next UI drift without a SaaS subscription.

### Wave 5L: Metamorphic testing (PR #645)
Read the monograph end-to-end with a metamorphic lens. Considered fifteen candidate relations, validated six, rejected nine with cited reasons. Implemented 154 test cases across six files:

- `Sab(α·x) = |α|² Sab(x)` coherent quadratic scaling (monograph Thm 4.1)
- `Sab(e^{iφ}·x) = Sab(x)` coherent global-phase invariance (Thm 4.1)
- Simultaneous SO(3) rotation invariance of per-triangle Sab (Eq. 2.5)
- Uniform mesh-scaling invariance for incoherent levels (Eq. 2.5, 5.4)
- Incoherent path superposition (Eq. 5.4)
- Polarisation universality at μ=1 (monograph appendix)

Nine rejected candidates include level monotonicity (monograph explicitly refutes it at pseudo-Brewster), reciprocity (one-way framework), convexity of coherent MIMO (`|h^T x|²` is not convex), and cross-pol = unpol (no API separates orthogonal paths).

**Bugs caught: 0.** All relations held at FP double precision (rtol 1e-11 to 1e-13). This is a strong correctness signal: the kernels honestly implement the quadratic forms and linear operators the monograph describes.

**Verdict: worth it.** Future invariant drift will be caught immediately.

## Was it worth it?

Yes, but with honest asymmetry.

### The three waves that did all the bug-catching
Waves 3E, 3F, and 4G together produced 11 of 12 bugs in roughly a quarter of the total agent-hours spent. If the plan had been "do only these three," the ROI would have been much tighter: ~12 hours, ~11 bugs, first real coverage on 2,500 previously-untested lines of Flask routes.

### The other waves produced zero bugs first-run but meaningful infrastructure
Waves 1, 2B, 2C, 2D, 5H, 5I, 5K, 5L all caught zero bugs in their initial runs. That's not a failure mode. The physics core of this codebase is already very solid (Mie canary passes, 154 metamorphic relations hold at double precision, mutmut scores were already 70–89% before we raised them). There was no hidden bug cache in kernels for these waves to find, and that's the signal: the hidden bugs were elsewhere, and 3E/3F/4G found them.

What these waves did buy was:
- A type system that will refuse the next None-for-ndarray swap
- A test randomizer that will catch the next order-dependent fixture
- A state-machine checker that will catch the next optimize-lifecycle race
- Mutation and metamorphic tests that will flag the next assertion that stops discriminating
- Visual baselines that will catch the next HUD drift
- An OpenAPI spec that future schema changes must round-trip through

That's not nothing, but it's all forward-looking. The first-run bug yield on these waves was zero. Call it what it is.

### The one wave that was a loss
Wave 5J (Pynguin) produced 0 useful tests from 31 generated and is documented as skip-permanently. Cost: one afternoon. Value: the documented negative result saves the next person from trying it again.

### The forecast miss
The roadmap forecast 60-180 bugs first-run. Actual was 12. That gap is partly Robin's pessimism about the codebase being wrong, and partly that the physics core is genuinely more defensible than the HTTP edges. Every wave that targeted physics invariants found zero bugs because there were none to find. Every wave that targeted the HTTP surface found real ones.

## What's next (forward-looking, not action items)

- **v0.30.0 tag.** Meaningful new capability across three tiers; twelve production bug fixes; four-hundred-plus new tests. Per `.claude/rules/git-workflow.md`, minor.
- **Watch the mutation-score baseline drift.** If future minor-release CI reports fresnel dropping below 85% or _parsing below 90%, that's an assertion rotting.
- **Watch the Schemathesis log at patch-release tier.** Each release is an opportunity to catch new route bugs cheaply.
- **If/when Sentry shows a new class of HTTP bug not caught by integration tests,** write that class as a `test_viewer_schemathesis_repro_*.py` case so the regression is locked down.

## Lessons for the next multi-agent wave

1. **Agents merge through red CI when they've already declared success.** Wave 3E's PR had 37 basedpyright errors; the agent reported "0 errors" and squash-merged anyway because their local check saw a different state. Every subsequent PR inherited the breakage. Mitigation: require CI-green before the agent is allowed to self-report success.
2. **Parallel agents share the worktree and quietly step on each other's branches.** Multiple times the working tree was on the wrong feature branch when I went to commit. Mitigation: each parallel agent should use `git worktree add` for genuine isolation, not just share the main checkout.
3. **The basedpyright config ladder is subtle.** "Warnings" at strict-non-strict boundaries still exit-1 by default. Wave 3E's agent thought they demoted reportUnknown\* but only demoted reportPrivateUsage and reportImportCycles. The fix was another 1400 tokens of pyproject.toml. Worth a checklist entry in the roadmap.
4. **Negative results are valuable and should be expected.** The Pynguin experiment, the metamorphic relations that didn't survive validation, the zero-bug outcomes on Hypothesis stateful and visual regression — each of these saves future effort by ruling out a direction. Plan for them.

## Appendix: tooling rejected with cited reasons

- **GeMTest.** Wrote own decorators; the framework didn't earn its dependency.
- **Pynguin.** Ran the experiment; documented zero useful tests from 31 generated; see `pynguin_experiment_2026-04-18.md`.
- **Chromatic / Argos / Percy.** No SaaS; baselines committed to git.
- **ty (Astral).** Too early, wait for 1.0; basedpyright covers the need today.
- **pytest-testmon.** JAX JIT cache invalidation risk; revisit if suite crosses 10 min.
- **Stryker-JS.** Defer until there are ≥30 frontend tests with real assertions.
- **Launchable.** Acquired by CloudBees, enterprise-only now.
