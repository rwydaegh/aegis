# Pynguin experiment on aegis.compliance (Wave 5J)

**Date:** 2026-04-18
**Branch:** `feature/phase5-pynguin-experiment`
**Verdict:** Not useful for this module.

## Setup

- Target: `aegis.compliance` (the ICNIRP 2020 compliance module, 1107 lines in
  `__init__.py`, 267 lines in `__main__.py`).
- Tool: `pynguin` (DYNAMOSA algorithm, 300 s search budget) via
  `uvx pynguin --project-path src --module-name aegis.compliance
  --output-path /tmp/pynguin_out --maximum-search-time 300
  --algorithm DYNAMOSA`.
- Command ran with `PYNGUIN_DANGER_AWARE=1`.
- Baseline: `tests/test_compliance*.py` already contains 196 hand-written tests
  (138 + 15 + 10 + 33 across the four files).

## Results

| Metric | Value |
| --- | --- |
| Wall time | ~ 420 s (including uvx cold bootstrap, tool-discovery, and mutation-analysis phases) |
| Search time configured | 300 s |
| Branch coverage reported by Pynguin | 51.1 % |
| Tests generated | 31 |
| Tests accepted after review | 0 |
| Tests rejected | 31 |

Raw artifacts (generated file, `statistics.csv`, CLI params) are archived in
`docs/internal/pynguin_raw/` for transparency. They are NOT in `tests/` and
are NOT collected by pytest.

## Rejection category breakdown

| Category | Count | Why rejected |
| --- | --- | --- |
| Module-constant tautologies | 31 | Every case re-asserts `ICNIRP_2020.sab_peak == 20.0`, `ICNIRP_2020.sar_wb == 0.08`, `ICNIRP_2020.averaging_area_cm2 == 4.0`, and `type(x).__module__ + qualname` strings. These are not behaviour tests; they would only fail if someone renamed a module or a class. |
| Brittle summary-string assertions | 6 (test_case_21, 22, 24, 25, 26) | Assert verbatim multi-line output of `summary_text(...)`. Any cosmetic change to the summary format (added unit, reworded header, tweaked precision) breaks them without signalling a real regression. |
| Nonsense xfail cases | 5 (test_case_1, 5, 20, 28, 29) | Pass pathological inputs (e.g. `tx_power_w=299_999_999_991.25, distance_m=299_999_999_991.25, freq_hz=299_999_999_991.25`, all the same absurd number) and mark `xfail(strict=True)`. The tests assert nothing about the failure mode and duplicate existing validation coverage without adding signal. |
| Duplicate validation tests | 7 (test_case_3, 9, 10, 12 + several link-budget cases) | `link_budget_compliance` with zero/negative/absurd inputs -> ValueError. Already covered in `tests/test_compliance.py::TestLinkBudget` with clearer, labelled tests. |
| Trivial `margin_db` corners | 3 (test_case_4, 6, 8) | Already covered by `TestMarginDbStandalone` (tests/test_compliance.py:329-359), including the zero-limit branch that returns `-inf` and the negative-value branch that raises ValueError. |

Every generated test either duplicates existing coverage, asserts module-identity
invariants that provide no regression protection, or hardcodes a formatting string
that will rot on the next copy-edit. Not one test exercised a behaviour that the
hand-written suite misses.

## Why Pynguin struggled on this module

1. **Rich dataclass surface.** `aegis.compliance` exposes `ICNIRPLimits`,
   `ComplianceCheck`, `ComplianceResult` (frozen dataclasses with computed
   properties). Pynguin spent much of its budget on cheap structural identity
   assertions rather than on driving the numerical branches (frequency-table
   lookups, margin computations near boundaries, etc.).
2. **Floating-point-heavy logic gated by narrow validity windows.**
   `_validate_freq`, `icnirp_limits` piecewise table, `margin_db`, and
   `link_budget_compliance` all reject out-of-range inputs with ValueError.
   Pynguin's random-float search generates mostly rejected inputs; the ones
   that do land in-range rarely cross interesting branch boundaries (6 GHz
   S_ab switchover, local vs whole-body, general public vs occupational).
3. **No semantic oracle.** Pynguin's mutation-analysis assertion generator
   only knows about return values and attribute reads. The important
   properties for a compliance module are physical (margin positive iff
   compliant, linearity of S_ab in transmit power, conservativeness of link
   budget). Those are checked by the hand-written suite's property tests
   and invariant checks, which Pynguin cannot generate.
4. **Existing suite already at ~95 % line coverage.** Pynguin's reported 51 %
   branch coverage is a lower bound for what it independently achieved, not
   what the module has overall. The marginal value of anything Pynguin could
   contribute was tiny to begin with.

## Bugs found

None. No generated test identified a real defect. All "failing" cases were either
expected ValueErrors on invalid inputs (already covered) or `xfail` markers on
nonsense inputs that assert nothing.

## Recommendation

- **Do not commit Pynguin output for `aegis.compliance`.** The generated tests
  would add maintenance burden (brittle snapshot strings, module-identity
  tautologies) without catching any bug the hand-written suite misses.
- **Do not add Pynguin to CI.** It runs for hundreds of seconds per module,
  uses stochastic search, and its output requires human triage every run.
  Adding it to CI would produce a flaky, costly job with no signal improvement.
- **Consider Pynguin selectively for pure-logic modules without a hand-written
  suite yet.** Modules that are heavy on primitives (int/float in, int/float
  out) and have no existing tests may benefit from Pynguin as a bootstrap.
  `aegis.compliance` is the wrong shape: rich dataclasses, physical invariants,
  and an already-comprehensive suite.
- **Hypothesis remains the better tool here.** Property tests on
  `margin_db` (monotonicity, sign flip at limit), `max_compliant_power`
  (scaling with `ref_power_w`), and `link_budget_compliance` (S_ab <= S_inc)
  give stronger guarantees per line of test code and are already the pattern
  used in `tests/`.

## What goes on master

Only this write-up and the archived raw Pynguin artifacts in
`docs/internal/pynguin_raw/`. No generated tests are promoted to `tests/`.
No CI integration.
