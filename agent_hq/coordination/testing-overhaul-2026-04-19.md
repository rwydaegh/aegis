# Testing infrastructure overhaul 2026-04-19

Record of what landed during the 2026-04-18/19 multi-agent run. Five waves, twelve merged PRs, twelve real production bugs fixed, around four hundred new tests.

## What landed

| PR | SHA | Scope |
|---|---|---|
| #630 | `131f7f9` | Branch coverage, ruff PT, pytest-randomly, config unified into a single packaged JSON resource, 30 tautological tests deleted |
| #637 | `d8b7197` | basedpyright strict on kernels + compliance (483 errors → 0) |
| #634 | `85954a0` | Frontend vitest coverage, TS strict verified, Codecov `frontend` flag |
| #638 | `6b2e01c` | 10 Playwright E2E specs for core viewer flows |
| #641 | `aed2ca1` | basedpyright strict on viewer/routes (3922 errors → 0) |
| #642 | `b8fc8e3` | 164 real integration tests, no mocks, five highest-traffic routes |
| #643 | `e69e917` | OpenAPI spec via apispec, Schemathesis wired at patch-release tier |
| #644 | `1faee11` | Hypothesis `RuleBasedStateMachine` on MIMO and optimize lifecycle |
| #648 | `e5d1a52` | Pynguin experiment on compliance (negative result documented) |
| #647 | `9872528` | mutmut audit on fresnel + _parsing, wired at minor-release tier |
| #645 | `c368dac` | 6 monograph-derived metamorphic relations, 154 test cases |
| #646 | `4118595` | Visual regression against HUD baselines, wired at minor-release tier |

Plus five direct-to-master CI-discipline commits (`5afbf0d`, `2d3629c`, `9c59b57`, `b21ecd9`, `ae3ab39`) fixing basedpyright config and vitest/Schemathesis wiring.

## Bugs caught and fixed

Twelve real production bugs, all fixed in the same PR as the test that caught them.

**Critical (1)**
- `/api/compute/rt` 500'd whenever `mode=bound` or `level <= 1` was passed. Non-RT path derived `A_ab` and `D_max`, RT path called the engine directly without them. Fixed in #642.

**Serious / high (5)**
- `/api/environment/geojson` crashed with `AttributeError` on numeric height properties.
- Placement optimize rejected valid requests as "Invalid mode/level parameters" when neither was passed.
- `_parse_vec3` accepted antenna positions at `|v| > 1e200`, overflowing to inf then silent NaN, surfacing as raw 500.
- `/api/compute` leaked `ValueError("Level 7 requires a precoder")` as 500 instead of 400.
- `/api/compute/rt` passed `env_mesh=None` to `to_differt_scene`, crashing on attribute access.

**Minor (6)**
- `compute/rt.py:192` passed `voxel_sizes=None` to `prepare_for_raytracing`.
- `optimize.py:327` and `:370` had the same None-pass pattern in placement.
- `analysis.py:282` had an unnarrowed Optional on `ref_sab`.
- `basestations/_data.py:80` passed `region=None` to `load_basestations`.
- `basestations/_data.py:111` + `_compute_mimo.py:137` missed cache-get `or []` guards.
- `mimo.py:403` missed a cache-get `or {}` guard.

## Test count

- `-30` tautological tests deleted (Wave 1)
- `+164` real integration tests (#642)
- `+32` test-quality assertions (#647 mutmut triage)
- `+154` metamorphic tests (#645)
- `+7` Schemathesis reproducers + smoke (#643)
- `+2` Hypothesis state machines + invariants (#644)
- `+7` visual regression HUD baselines (#646)

Full suite: ~2,400 → **2,564 non-slow tests**, runtime 67s → 75s.

## Tiering: what runs when

Don't run everything every time. Keep it all around, fire it at the right cadence.

- **PR tier (every PR):** ruff + basedpyright + pytest + pytest-randomly + branch coverage + vitest coverage + frontend TS strict. Fast, always.
- **Patch-release tier (every `vX.Y.Z`):** Schemathesis sweep against the OpenAPI spec, 5 min budget.
- **Minor-release tier (`vX.Y.0` only):** mutmut on physics-critical modules + visual regression against HUD baselines. Report-only, non-blocking.
- **Local on demand:** `scripts/fuzz_api.sh` for deep Schemathesis, `scripts/run_mutmut.sh` for mutation on any module, anything-goes.

All tools stay installed and invokable locally even when they aren't wired to CI. Easy to turn on ad-hoc when something feels off.

## Tools adopted

pytest-randomly, ruff PT, branch coverage, basedpyright strict, vitest coverage, TS strict, Playwright E2E, apispec + Schemathesis, Hypothesis stateful, mutmut, Playwright `toHaveScreenshot()`, metamorphic decorators (own implementation).

## Tools tried and dropped (with reasons, so nobody re-runs them)

- **Pynguin** — 0 useful tests from 31 generated on `compliance/`; see `docs/internal/pynguin_experiment_2026-04-18.md`.
- **GeMTest** — wrote own metamorphic decorators; framework didn't earn its dependency.
- **Chromatic / Argos / Percy** — baselines committed to git, no SaaS needed.
- **ty (Astral)** — wait for 1.0; basedpyright covers the need today.
- **pytest-testmon** — JAX JIT cache invalidation risk.

## Reference docs on master

- `agent_hq/coordination/testing-roadmap-2026-04-19.md` — the plan with CI tiering and tool decisions
- `docs/internal/metamorphic_testing.md` — how to add a new metamorphic relation
- `docs/internal/metamorphic_analysis_2026-04-18.md` — the 15 candidates and why 9 were rejected
- `docs/internal/mutation_audit_2026-04-18.md` — baseline mutation scores
- `docs/internal/pynguin_experiment_2026-04-18.md` — the negative result
- `tests/test_viewer_schemathesis_repro_*.py` — regression locks from fuzzing finds

Master tip after this wave: `4118595`, tagged `v0.30.0`.
