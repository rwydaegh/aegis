# Testing roadmap 2026-04

Decisions-grounded plan for introducing testing tools that catch real bugs in AEGIS. Written after a full audit (codebase, CI timings, Codecov 162-file breakdown, sampled test quality, Reddit sentiment across 10 tools). Priors that shaped the plan:

- App is still quite buggy; first-run bug yield matters more than long-term polish.
- Dumb tests (1+1=2 tautologies) are net-negative and should be deleted, not added to.
- Physics code is already well-tested. The rot is in HTTP glue and frontend types.
- Private repo: CI minutes are metered but not scarce. Don't be paranoid — tier the intensity by trigger so cheap checks run often and expensive sweeps run rarely.

## CI tiering by trigger

Every workflow has a different frequency and risk profile. Match the test cost to the trigger:

| Trigger | Frequency | Budget | What runs |
|---|---|---|---|
| **PR / branch push** | many per day | ≤ 2 min | ruff + basedpyright + full pytest + frontend vitest + coverage upload |
| **master push (after merge)** | tens per day | ≤ 5 min | PR tier + integration tests against real Flask routes + 10 E2E specs |
| **Patch release (vX.Y.Z tag)** | ~daily lately | ≤ 15 min | master tier + full matrix (Linux/Windows × 3.11/3.12/3.13, already running) + Schemathesis pass |
| **Minor release (vX.Y.0 tag)** | weeks-monthly | ≤ 60 min | patch tier + mutation testing sweep on critical modules + visual regression baseline refresh (if adopted) + full E2E flow suite |
| **Manual / local** | on demand | unbounded | anything — full Schemathesis sweep with stateful runner, mutation testing on all kernels, Pynguin experiments, ad-hoc exploration |

Rationale:
- Bugs catch-rate scales with test intensity, not test frequency. A mutation sweep that runs once per minor release catches as much as one that runs per PR, at 1/50th the cost.
- Patch releases already go through a full matrix (~3.5 min on release.yml). Adding Schemathesis there is a ~5 min delta on a workflow that runs once per release — trivial.
- Minor releases are natural checkpoints for expensive sweeps. `v0.29.x` has been shipping rapidly; `v0.30.0` is a natural "stop and audit" moment.
- Local invocation remains available for everything, so Claude Code sessions can run any heavy tool on demand without touching CI.

## TL;DR — the decision

Introduce tools in three waves. Each wave has a CI-time budget and an expected bug yield based on the audit.

| # | Tool / change | Effort | Runs at | First-run bug yield |
|---|---|---|---|---|
| 1 | Branch coverage + ruff PT rules + pytest-randomly | 30 min | PR | 0-5 |
| 2 | Delete `test_constants.py`, `test_config_drift.py`, prune E2E screenshot tests | 15 min | — | -30 dumb tests |
| 3 | Frontend vitest coverage + TS strict + Codecov upload | 30 min | PR | 5-15 |
| 4 | basedpyright strict on `kernels/` + `viewer/routes/` + `compliance/` | 2 hr | PR | 10-30 |
| 5 | Enable Codecov Test Analytics (flaky detection) | 5 min | external | depends on history |
| 6 | 10 E2E specs via existing workflow (agent_hq + skills) | 3 hr | master / patch release | 5-15 |
| 7 | Real integration tests for viewer/routes/* (5 highest-traffic) | 2 days | master | **10-30** |
| 8 | Schemathesis against Flask API (stateful, full checks) | 1 day | patch release + local | **20-50** |
| 9 | Hypothesis stateful tests for MIMO precoder + optimize lifecycle | 1 day | PR | 5-15 |
| 10 | mutmut v3 on critical modules | 4 hr setup | minor release + local | 0, high test-quality signal |
| 11 | Visual regression | when needed | minor release | 3-10 UI drift |

Total expected bug yield on first introduction: ~60-180 real bugs. The biggest single win is (7) Schemathesis + (8) real integration tests against the Flask HTTP surface.

Skip for now: mutpy, cosmic-ray, Launchable, pytest-testmon, Mabl/Testim/Functionize, GeMTest (academic), ty (not 1.0), cross-browser cloud grids, record-and-replay tools, Slipcover.

## Current state — what the data shows

### CI times (last 20 runs)

| Workflow | Trigger | Typical | Notes |
|---|---|---|---|
| ci.yml | push / PR | 60-90s | slim matrix (ubuntu/3.12), lint + test + Codecov upload |
| deploy.yml | push to master | **400-550s on success**, 120-160s on failure | frontend build → docker → Hetzner; fails fast on frontend |
| release.yml | tag push | 180-230s | full Linux/Windows × 3.11/3.12/3.13 |
| benchmarks.yml | push to master | 75-90s | CodSpeed |

PR budget for additional tooling: can safely add ~100s without crossing the 2-min threshold. Deploy can absorb more because it's already long.

### Codecov truth (pulled from API, master, today)

**Overall: 50.75% line coverage (7,587 / 14,948 lines across 162 files). Branches: 0 (branch coverage off).**

The entire rot is in one place: Flask route handlers. Top uncovered surfaces (absolute uncovered-line count):

| File | Uncovered | Coverage | Type |
|---|---|---|---|
| viewer/compute.py | 280 | 29.5% | **business logic** |
| viewer/routes/analysis.py | 276 | **0%** | HTTP endpoint |
| viewer/routes/optimize.py | 274 | **0%** | HTTP endpoint |
| viewer/routes/environment.py | 270 | **0%** | HTTP endpoint |
| basestation/build.py | 253 | 8.3% | CLI/ETL |
| viewer/raytracer.py | 251 | 11.9% | **engine bridge** |
| viewer/routes/data.py | 246 | **0%** | HTTP endpoint |
| viewer/routes/mimo.py | 243 | **0%** | HTTP endpoint |
| viewer/routes/compute/dosimetry.py | 238 | **0%** | HTTP endpoint |
| viewer/routes/sentry_webhook.py | 202 | **0%** | HTTP endpoint |

**~2,500 uncovered lines in viewer/routes/** — the Flask HTTP surface is essentially untested. This lines up with Sentry issue pattern: production errors surface from endpoints, not from kernels.

### Test quality audit (sampled 10 files in full)

- **Genuinely good (~100 tests):** `test_compliance.py`, `test_coherent.py`, `test_fresnel.py`, `test_kernel_properties.py`, `tests/golden/*`, frontend `physics.test.ts`, frontend `useOptimization.test.ts`. Property-based invariants, golden tables, real regression locks. Keep and expand.
- **Dumb tests (~30 tests, specifically flagged):**
  - `tests/test_constants.py` — asserts `Z_0 == sqrt(MU_0/EPS_0)` when Z_0 is literally computed from MU_0 and EPS_0. Tautological. **Delete.** (If you want to validate constants, compare to CODATA.)
  - `tests/test_config_drift.py` — checks DEFAULTS dict equals default.json. The fix is to pick ONE source of truth; the test is patching over bad design. **Delete after unifying.**
  - `tests/e2e/test_mimo_e2e.py` screenshot tests — no assertions, just takes a screenshot. Keep only the `console.error` check. **Trim.**
  - `aegis-web/src/api/__tests__/coordinates.test.ts` — tests that `toServer([1,2,3])=[1,-3,2]`. Testing the definition. Borderline; converts definition drift to a regression, but if the whole file is 25 lines, the cost/benefit is thin.
- **Shallow-but-defensible (~200 tests):** Flask route tests with `test_client()` but heavy patching of DosimetryEngine / ray tracer. These catch serialization + route wiring but miss end-to-end correctness. Not dumb, but not enough.

**Owner's claim that there are "lots of dumb 1+1=2 tests" is partially right.** The concrete count is ~30. The bigger issue is missing integration tests on 2,500 lines of Flask routes.

### Existing-tool inventory

Already have: `pytest-xdist`, `pytest-cov`, `hypothesis` (25 `@given` usages = 7%), `pytest-codspeed`, `ruff`, `codespell`, Codecov, CodSpeed, Sentry, Playwright (package installed, one Python test).

Confirmed absent: mutation testing, pytest-randomly, pytest-rerunfailures, pytest-testmon, schemathesis, type checker (mypy/pyright/ty/basedpyright), ruff `PT` rules, diff-cover, branch coverage, visual regression, Storybook, `@testing-library/react`, MSW, vitest coverage provider.

## Strategy — why this specific set of tools

The bug-finding frontier in AEGIS is not "find more kernel bugs" — it's "exercise the 2,500 untested HTTP lines and lock down the type contract at the API seam." So the tool picks bias toward:

1. **Tools that exercise HTTP routes with real physics.** Schemathesis, real integration tests. Not mock-heavy unit tests — we have plenty of those.
2. **Tools that enforce type contracts at boundaries.** basedpyright on routes, strict TS on frontend, where the useOptimization.ts Deploy failure lived.
3. **Tools that catch regressions in the 100 good physics tests without adding noise.** pytest-randomly, branch coverage, ruff PT.
4. **Tools that catch UI drift without being visual-regression-theater.** Playwright MCP for test authoring, Argos for HUD-region snapshots (not whole-canvas).
5. **Audit tools, not CI tools, for mutation testing.** Running mutation per-PR is a fool's errand. Running once on `fresnel.py` tells you which of your "good" tests are actually asserting something.

Deliberately excluded:
- **GeMTest** (academic, zero adoption — write your own metamorphic decorators instead)
- **ty** (not 1.0 — Reddit sentiment in r/Python April 2026: "not even close")
- **pytest-testmon** (JAX JIT cache invalidation risk masks real dependencies)
- **Chromatic** (only makes sense if you already live in Storybook; you don't)
- **Enterprise E2E SaaS** (Mabl/Testim/Functionize — wrong shape for small scientific team)

## Tool-by-tool decisions, with honest verdicts

Reddit sentiment sourced from r/Python, r/ClaudeAI, r/devops, r/experiencedDevs, and issue trackers (March 2024 - April 2026). See sources at bottom.

### Adopt

**pytest-randomly** — adopt. Zero flame threads; randomized order finds real dependency bugs. If CI gets flaky after turning it on, that's an existing bug the plugin surfaced, not the plugin's fault.

**Branch coverage (`branch = true`)** — adopt. Two-character change. Immediately surfaces untested else-branches.

**Ruff `PT` rules** — adopt. Add `"PT"` to `select`. Catches `PT011` (pytest.raises without match), `PT004` (fixture doesn't return), `PT018` (composite assertion).

**`@vitest/coverage-v8`** — adopt. Frontend coverage is a black hole today. Upload to Codecov as a separate flag.

**TypeScript `strict: true`** — verify on; if off, turn on. Today's Deploy failure (the Peaks type literal-narrowing bug) is exactly the shape strict TS catches at write-time.

**basedpyright (strict)** — adopt on narrow surfaces first. Reddit consensus in r/Python (Nov 2025, Apr 2026): "basedpyright is just better than pyright these days"; ty is "not even close to ready"; pyright maintainer is hostile to EAFP. Pick basedpyright; start with `src/aegis/kernels/` and `src/aegis/viewer/routes/` in strict mode. Expand later.

**Codecov Test Analytics** — try. Free for public repos, drops into existing pipeline. Reddit sentiment is thin; Sentry's own claims dominate. Don't pay for Pro just for this.

**Existing E2E workflow** (`agent_hq/` + Claude Code skills) — keep as-is, don't add new tooling. Produces idiomatic Playwright TS that can be committed and run locally or in CI.

**Schemathesis** — adopt as nightly cron. Reddit + GitHub issues are honest about false positives in `negative_data_rejection` and `ignored_auth`; budget a day to suppress those. But it *does* find real schema/serializer mismatches and 500s — exactly what AEGIS's 0%-covered HTTP endpoints need.

**Visual regression (Argos CI / Chromatic)** — **defer.** Adds a subscription cost on top of CI minutes. If needed later, run Playwright `toHaveScreenshot()` locally with SwiftShader + fixed seeds and commit baselines to the repo (zero subscription, uses git for diff review). Revisit after Phase 3 if UI drift is a real pain point.

### Experiment once, don't wire to CI

**Mutation testing on one kernel file** — don't adopt as CI, use as a one-time audit. Reddit sentiment on `mutmut`: meh, abandonment-prone. New competitor `pytest-gremlins` (released late 2025 per r/Python) claims faster, watch first. For the audit: run mutmut v3 on `src/aegis/tissue/fresnel.py` or `src/aegis/kernels/level_7.py` and see which mutants survive. That single experiment tells you whether the "good" test files are actually asserting enough. If it surfaces ≥3 interesting survivors, expand to other kernels; if not, move on.

**Pynguin** — one experiment on `src/aegis/compliance/` (small, pure, typed). Reddit: solid on small typed modules, useless on shape-dependent numpy/JAX. Give it one afternoon.

**Stryker-JS (vitest-runner) on `aegis-web`** — defer until you have ≥ 30 frontend tests. Today's 60 test cases aren't enough surface to learn from. GitHub issues show vitest fixtures don't work, browser mode doesn't work; friction is real.

### Skip / delete

**test_constants.py** — delete. Tautological.

**test_config_drift.py** — delete after unifying DEFAULTS and default.json into one source of truth (ideally: default.json is the only source; Python imports it via `importlib.resources`).

**E2E screenshot tests in `test_mimo_e2e.py`** — trim to just the `console.error` check.

**Launchable** — acquired by CloudBees 2024, enterprise-only now.

**Diffblue / Mabl / Testim / Functionize / Machinet** — wrong shape for small scientific team.

**GeMTest** — Reddit verdict: academic fluff, zero organic adoption, no case studies outside the paper. Write your own `@metamorphic_relation(scale=2, invariant="sab doubles")` decorators; 30 lines of code replaces the dependency.

**ty (Astral)** — wait for 1.0. Currently beta (Dec 2025); gradual-guarantee design means it catches less than basedpyright today.

**pytest-testmon** — JAX JIT cache invalidation risk. Revisit if suite crosses 10 min.

**Chromatic** — only if you adopt Storybook, which isn't in scope this wave.

**BrowserStack / Sauce Labs / LambdaTest** — Playwright's built-in Chromium/Firefox/WebKit covers real-world browsers. Only need this if you get Safari-specific Sentry issues.

## Execution plan

### Phase 1 — Free wins (1 afternoon, +5s PR time)

```toml
# pyproject.toml

[tool.ruff.lint]
select = ["E", "F", "W", "I", "UP", "B", "SIM", "PT"]  # added PT

[tool.coverage.run]
source = ["src/aegis"]
branch = true  # added
parallel = true
```

```bash
uv add --dev pytest-randomly
```

Delete:

```bash
rm tests/test_constants.py
rm tests/test_config_drift.py  # only after unifying default.json as the sole config source
```

Trim `tests/e2e/test_mimo_e2e.py` to keep only the `console.error` check.

Enable Codecov Test Analytics in the Codecov project settings (checkbox).

**Expected bug yield:** 0-5 real bugs from pytest-randomly surfacing order-dependence. Branch coverage will immediately drop reported coverage from 50.75% to lower — that's a feature, not a bug, it means previously-hidden else-paths are now visible.

### Phase 2 — Type-safety + frontend coverage (1 day, +60s PR time)

```bash
npm -w aegis-web add -D @vitest/coverage-v8
```

```json
// aegis-web/package.json scripts
"test:coverage": "vitest run --coverage"
```

Add a CI job that runs `npm run test:coverage` in `aegis-web/` and uploads to Codecov with `flag: frontend`.

Verify / enforce `"strict": true` in `aegis-web/tsconfig.json`.

Install and configure basedpyright:

```bash
uv add --dev basedpyright
```

```toml
# pyproject.toml

[tool.basedpyright]
include = ["src/aegis/kernels", "src/aegis/viewer/routes", "src/aegis/compliance"]
strict = ["src/aegis/kernels", "src/aegis/viewer/routes", "src/aegis/compliance"]
pythonVersion = "3.12"
reportMissingTypeStubs = false
```

Add to `ci.yml` lint job:

```yaml
- run: uv run basedpyright
```

**Expected bug yield:** 10-30 real type bugs (mostly Optional handling in routes, None-vs-int confusion), 5-15 frontend TS bugs exposed by strict mode.

### Phase 3 — Bug-catching frontier (3 days, nightly + PR impact)

**3a. 10 E2E specs via existing workflow** (3 hr)

Use your existing setup (`agent_hq/` + Claude Code skills) to drive the viewer and emit specs for core flows: load scenario, set frequency, compute dosimetry, toggle fidelity levels, run optimize, export image, share link, multi-body scene, MIMO precoder apply, tilt/power optimize. Commit to `aegis-web/tests/e2e/`. Run locally; add to CI only if total added time stays under ~60s per PR.

**3b. Schemathesis against Flask viewer API** (1 day)

1. Add `flask-smorest` or `apispec` to generate an OpenAPI spec from existing routes. Start with `/api/compute/*` and `/api/optimize/*` since they're highest-traffic.
2. Run in two places:
   - **Patch release (`release.yml`):** Schemathesis pass with standard checks, 5-10 min budget. Blocks the release if it finds a new 500 or schema mismatch.
   - **Local:** full stateful sweep with all checks enabled, 15-30 min. Used for deeper audits and when touching route code.

Patch release CI step:

```yaml
# .github/workflows/release.yml — add to release job
- name: Schemathesis fuzz
  run: |
    uv run python -m aegis.viewer &
    sleep 10
    uvx schemathesis run http://localhost:5000/api/openapi.json \
      --checks=all --stateful=links --rate-limit=20/s \
      --exclude-checks=negative_data_rejection  # noisy, re-enable later
```

Local full sweep (script in `scripts/fuzz_api.sh`):

```bash
set -e
uv run python -m aegis.viewer &
SERVER_PID=$!
trap "kill $SERVER_PID" EXIT
sleep 5
uvx schemathesis run http://localhost:5000/api/openapi.json \
  --checks=all --stateful=links --rate-limit=20/s --max-examples=500
```

3. Commit high-signal findings as regression tests under `tests/test_viewer_integration_*.py` — those run at PR tier and never regress.
4. Expect noise from `negative_data_rejection` and `ignored_auth` false positives (GitHub issues #2312, #2482). Start excluded; re-enable as you suppress false positives per-route.

**3c. Real integration tests for 5 highest-traffic routes** (2 days)

Target `/api/compute/dosimetry`, `/api/compute/rt`, `/api/optimize/*`, `/api/analysis`, `/api/environment`. Write `tests/test_viewer_integration_*.py` that use the Flask `test_client()` + **real** DosimetryEngine, real PropagationPaths, real body meshes from `conftest.py` fixtures. No mocks of the compute stack. These will be slower (multi-second) — mark `@pytest.mark.slow` if they cross 5s.

Each route gets: happy path, invalid payload (400), coordinate-frame boundary conditions, large body smoke test, unicode / edge-float inputs.

**Expected bug yield from Phase 3:** 5-15 UI bugs via Playwright + **20-50 real HTTP bugs** via Schemathesis + 10-30 via integration tests. This is the single biggest wave.

### Phase 4 — Property deepening + audit (1-2 days)

**Hypothesis stateful tests** — `RuleBasedStateMachine` for:
- MIMO precoder lifecycle (set frequency → set power → apply mask → compute — invariants hold under any ordering)
- Optimize run lifecycle (start → iterate → stop/complete → restart — no race, no stale state)

These directly target the shape of the `useOptimization.ts` bug that broke Deploy today. Reddit warning: watch out for `Unsatisfiable` errors from over-filtered strategies (use `@precondition`, not `assume()`), and cap rule counts (perf regression at high counts — Hypothesis issue #4465).

**Mutation testing — minor-release CI + local**:

Local (any time):

```bash
uvx mutmut run --paths-to-mutate src/aegis/tissue/fresnel.py
uvx mutmut results
```

Minor-release CI (once per `vX.Y.0` tag, ~monthly): add a mutation-testing job scoped to the physics-critical modules (`src/aegis/kernels/`, `src/aegis/tissue/`, `src/aegis/coherent/`, `src/aegis/compliance/`). Budget 30-45 min. The job reports a mutation score and surviving mutants; it doesn't block the release initially. After a few runs, set a threshold (e.g. 75%) that must hold.

Review survivors. If 3+ are interesting (not equivalent), the kernel needs better assertions. Watch `pytest-gremlins` as a faster alternative.

**Expected yield:** Phase 4 catches 5-15 state-machine bugs; mutation surfaces test-quality gaps (not bugs directly — informs where to add assertions).

### Phase 5 — Visual regression (when UI drift becomes a pain)

Not priority-now, but the right home when it happens is **minor-release CI**: run `toHaveScreenshot()` against HUD components with Chromium launched under `--use-gl=swiftshader` + fixed camera + seeded scene, compare against baselines committed to the repo. No subscription. Baselines refresh per minor release, drift is caught on the next minor-release run. Don't adopt until you're seeing UI regression bugs in Sentry or PR review.

## Metamorphic testing — promising concept, needs real thought first

> **TODO: definitely check the monograph and really think about this before embarking on it.** The specific relations listed below (linearity, rotation invariance, scale invariance, level monotonicity, polarisation symmetry) are plausible-sounding but quite possibly wrong or only true under conditions I haven't verified. Don't take them as the plan — take the *concept* as the plan.

Metamorphic testing is more than a "fidelity-level" thing; it's a **concept** for scientific code where ground truth is hard to compute but transformations of the input produce predictable transformations of the output. The general shape: "if I do X to the input, Y should happen to the output." For AEGIS this could produce genuinely good tests — not 1+1=2 theater — *if* the chosen relations actually hold per the monograph.

If/when this wave is picked up: start by reading the monograph end-to-end with this lens and listing candidate relations, then validate each one mathematically before coding. Don't assume fidelity levels are monotone, don't assume scaling is linear, don't assume rotations preserve what you think they preserve. The relations are the hard part; the decorator framework around them is trivial.

Implementation choice (once relations are known): write simple Hypothesis-backed decorators in `tests/_metamorphic.py`. Skip GeMTest — the dependency doesn't earn its keep.

## A first, committable PR

Title: `Testing infra phase 1: branch coverage, ruff PT, pytest-randomly, delete tautological tests`

```diff
# pyproject.toml
 [tool.ruff.lint]
-select = ["E", "F", "W", "I", "UP", "B", "SIM"]
+select = ["E", "F", "W", "I", "UP", "B", "SIM", "PT"]

 [tool.coverage.run]
 source = ["src/aegis"]
+branch = true
 parallel = true

 dev = [
     "pytest>=9.0.3",
+    "pytest-randomly>=3.15",
     "pytest-xdist>=3.8.0",
     ...
 ]

- rm tests/test_constants.py
- rm tests/test_config_drift.py  # after unifying config source
```

Enable Codecov Test Analytics checkbox in the Codecov project UI (separate, not in the PR).

## Success criteria by end of month

- PR CI time: 120-180s (up from 60-90s, still under 3 min)
- Master push CI time: ~5 min (adds integration tests + E2E)
- Patch release CI: ~10 min (adds Schemathesis to existing matrix)
- Minor release CI: first run when `v0.30.0` ships — 30-45 min incl. mutation sweep
- Branch coverage on; frontend coverage reported
- basedpyright strict on kernels + routes + compliance with zero violations
- ≥ 10 real integration tests for high-traffic Flask routes, no mocks
- ≥ 10 E2E specs for core flows
- Codecov Test Analytics showing flaky history
- Deleted: `test_constants.py`, `test_config_drift.py`, screenshot-only E2E
- `scripts/fuzz_api.sh` for local deep Schemathesis sweeps
- Mutation-score baseline captured on first minor release after adoption

Expected cumulative bug haul: 60-180 real bugs surfaced on first introduction, distributed across HTTP routes, type contracts, and optimize lifecycle.

## Sources

Reddit: r/Python "MyPy vs Pyright" (Nov 2025), "Comparing Python Type Checkers" (Apr 2026), "Pyrefly Beta Release" (Nov 2025); r/AskVibecoders "Best MCP servers for Claude Code in 2026"; r/devops "Managing test analytics & flaky test detection"; r/Python pytest-gremlins release, "Agent-written tests missed 37% of bugs".

Issue trackers: Schemathesis #2312, #2482, #2726, #2978; Stryker-JS #3465, #5459; Hypothesis #3618, #4465.

Docs / vendor: Codecov Test Analytics (Sentry blog), Argos vs Chromatic pricing (Vizzly), Playwright MCP reviews (Skyvern, Testleaf), ty (Astral), Pyrefly (Meta), basedpyright (detachhead), mutmut v3 (boxed/mutmut), Schemathesis (schemathesis.io), GeMTest (ICSE 2025 demo paper).

Internal data: Codecov API pull 2026-04-18 (162 files, 50.75% coverage), gh run list timings (last 20 runs per workflow), audit of 10 sampled test files, pyproject.toml, aegis-web/package.json, conftest.py.
