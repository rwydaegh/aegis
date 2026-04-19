# Mutation audit, Wave 5 Agent I

Mutmut v3.5 against two targets, following the Phase 4 plan in `testing_roadmap.md`. Not wired to PR CI. The minor-release job in `release.yml` runs the same command on `vX.Y.0` tags (report-only, `continue-on-error: true`).

## Headline

| Target | Before | After | Delta | Wall time |
|---|---|---|---|---|
| `src/aegis/tissue/fresnel.py` | 160 / 208 killed (77%) | 186 / 208 killed (89%) | +26 kills | ~16 s |
| `src/aegis/viewer/routes/compute/_parsing.py` | 164 / 233 killed (70%) | 223 / 233 killed (96%) | +59 kills | ~34 s |

Reachable mutants exclude the 10 "not reached" (🫥) mutants for `_parsing.py` (generated trampoline dispatch branches that no test path touches). All 22 remaining fresnel survivors and 10 remaining `_parsing` survivors are classified below. None point at production bugs.

Tests added: fresnel grew from 27 to 42 cases, parsing-helpers grew from 66 to 83 cases.

## Target 1: `src/aegis/tissue/fresnel.py`

Setup: ~15 s per run, 208 AST mutations covering `n_complex`, `_fresnel_core`, the three public wrappers (`fresnel_transmission`, `fresnel_reflection`, `fresnel_amplitude`), `xi_from_mu`, and `T0`.

### Top weak-test survivors from the first run

1. `_fresnel_core:18  xi = xp.sqrt(n2 - 1 + mu**2)  ->  xi = xp.sqrt(n2 - 1 + mu**3)`. Classification: **weak test**. The monograph Table 1 golden test used `abs=2e-3`, but the typical numeric corruption from `mu**2 -> mu**3` is only ~5e-4 at skin-28-GHz. Fix: added `TestFresnelHighPrecision` with 10-decimal reference values computed from the unmutated formula and asserted at `abs=1e-9` (power) and `abs=1e-12` (amplitude, reflection). Tightened Table 1 tolerance to `1e-3`.

2. `_fresnel_core:29  t_s = 2 * mu / (mu + xi)  ->  t_s = 2 * mu * (mu + xi)`. Classification: **weak test**. `test_amplitude_transmission_nonzero_at_normal` only checked `abs(t_s) > 0`, so any mutation of the divide still produced a nonzero complex. Fix: anchored `t_s`, `t_p`, `r_s`, `r_p` against closed-form references at normal incidence and at `theta=45`.

3. `xi_from_mu` — a whole family of arithmetic mutations (`n_tilde**2 -> n_tilde*2`, `n2 - 1 + mu**2 -> n2 + 1 + mu**2`, etc.) all survived because only one test (`test_xi_branch_selection`) exercised this function, and it only asserted `Re(xi) >= 0`. Fix: added `test_xi_from_mu_45deg_exact` (10-decimal reference) and `test_xi_from_mu_normal_equals_n_tilde` (analytic closed form at `mu=1`).

4. `_fresnel_core:33  T_s = xp.where(mu_real < 1e-10, 0.0, T_s)  ->  T_s = xp.where(None, 0.0, T_s)`. Classification: **weak test**. The grazing clamp only fired at mu=0, where T was already 0 from the formula, so the clamp was untested at tiny-but-nonzero mu. Fix: added `TestGrazingClamp` that uses `mu=1e-11` (clamped) and `mu=1e-9` (not clamped).

5. `n_complex:2  eps_complex = eps_r - 1j * sigma / (omega * EPS_0)  ->  eps_complex = eps_r + 1j * sigma / (omega * EPS_0)`. Classification: **weak test** (convention drift). The `-j` sign fixes `Im(n_tilde) < 0` under the exp(-jωt) physics convention. Flipping the sign breaks coherent phase tracking silently because power transmission `|r|²` is modulus-based. Fix: added `TestSignConvention` asserting `n.imag < 0` for any lossy medium and that `|Im(n)|` grows monotonically with conductivity.

### Remaining survivors (22, all equivalent under physical inputs)

- 18 mutants touch the two defensive `xp.where(Re(x) < 0, -x, x)` branches inside `_fresnel_core` and `xi_from_mu`. These are dead-branch code — `np.sqrt` of a complex number always returns the principal branch with `Re >= 0`. I verified this across eps_r=[0.1, 100], sigma=[0, 100] S/m, freq=[1 MHz, 100 GHz]: no input ever produces `Re(n) < 0` or `Re(xi) < 0`. Mutations like `< 0 -> <= 0`, `< 0 -> < 1`, `-xi -> +xi`, `xp.where(None, ...)` are therefore semantically equivalent under the physical-tissue constraint `Re(n) >= 1`. Keeping the defensive code is the right call; killing these survivors would require either a test with `Re(n) < 1` (unphysical) or deleting the defensive branch.
- 4 mutants replace `dtype=complex` with `dtype=None` in the array wrappers. The downstream computation promotes to complex naturally (`n2 - 1 + mu**2` with a complex `n_tilde` lifts `mu` to complex), so the result is bit-exact. Equivalent.

## Target 2: `src/aegis/viewer/routes/compute/_parsing.py`

Setup: ~34 s per run, 243 AST mutations covering `_parse_bool`, `_parse_vec3`, `_parse_rotation_y`, `_parse_freq_and_tissue`, `_parse_quantities_and_scenario`, `_parse_mode_or_level`. Needs `AEGIS_DATA_DIR` exported because the tests hit `resolve_skin_model` which opens the IT'IS SQLite database, and the 1.3 GB `data/` tree is not copied into `mutants/`.

### Top weak-test survivors from the first run

1. `_parse_freq_and_tissue:15  if not math.isfinite(freq_hz) or freq_hz <= 0:  ->  if not math.isfinite(freq_hz) and freq_hz <= 0:`. Classification: **near-bug, weak test**. The `or -> and` flip means `freq_hz = 0` (a finite value) slips through to `resolve_skin_model` because `not math.isfinite(0) = False`. Fix: added `test_zero_freq_rejected`, `test_negative_freq_rejected`, `test_nan_freq_rejected`, `test_inf_freq_rejected`, each also locking down the specific error message.

2. `_parse_bool:8  return value.lower() not in ("false", "0", "no", "")  ->  return value.lower() not in ("false", "0", "XXnoXX", "")`. Classification: **weak test** (missing coverage). The tuple item `"no"` was never exercised. Fix: added `test_string_no_lowercase`, `test_string_no_uppercase`, `test_string_no_mixed_case`.

3. `_parse_mode_or_level:1  default_level: int = 2  ->  default_level: int = 3`. Classification: **weak test** (but mutant is equivalent under the public API — the outer trampoline wrapper keeps `default_level=2` in its signature, so the mutated inner function's default never fires). The behavior-level assertion `test_default_level_value_is_2` still kills plausible mutants of the resolution logic.

4. `_parse_mode_or_level  out["diffraction"] = _parse_bool(params.get("diffraction"), False)  ->  out["diffraction"] = _parse_bool(None, False)`. Classification: **weak test**. The default-toggle behavior was never asserted. Fix: added `test_mode_spatial_default_corrections`, `test_mode_spatial_diffraction_can_be_enabled`, etc. All four spatial-mode toggles now have explicit default + enable tests.

5. Dozens of response-body mutations (`{"error": "msg"}` -> `{"XXerrorXX": "msg"}`, `"ERROR"`, `"msg" -> "MSG"`, `jsonify(None)`). Classification: **weak test**. Existing tests only checked `err[1] == 400`. Fix: introduced `_error_message(err_tuple)` helper that extracts and asserts the `error` key and string content, then retrofitted 10 existing tests to check specific substrings of the error message ("freq_hz", "finite", "level", "between", "bound", "aggregate, bound, spatial", etc.).

### Remaining survivors (10)

- 5 mutants wrap an error string with Mutmut's `XXfooXX` markers. The `in` substring check still matches because `"XXbody_rotation_y must be finiteXX"` contains `"body_rotation_y"`. Could be killed with an exact-equality assertion, but that is brittle to benign wording changes. Left as intentional.
- 2 mutants replace `dtype=np.float64` with `dtype=None` in `_parse_vec3`. Equivalent — the preceding `float(v)` coercion already guarantees float64 values.
- 1 mutant on `_parse_freq_and_tissue` changes `<= 0` to `<= 1`. I added `test_subhertz_freq_still_accepted` at 0.5 Hz using the `christ2025` analytic skin model to kill it. (Verified locally: mutant dies after this test. The baseline run before that test was recorded has it as survived.)
- 1 mutant in the outer trampoline default (equivalent under public API; see #3 above).
- 1 mutant replaces `str(exc)` with `str(None)` in the resolve_skin_model error path. My test now asserts `msg != "None"` and that the rejected model name appears in the body.

## Files touched

- `pyproject.toml` — added `mutmut>=3` to `[project.optional-dependencies.dev]` and a `[tool.mutmut]` config block.
- `tests/test_fresnel.py` — +15 tests (TestFresnelHighPrecision, TestScalarReturnTypes, TestGrazingClamp, TestSignConvention).
- `tests/test_compute_route_helpers.py` — +17 tests, +1 helper (`_error_message`).
- `scripts/run_mutmut.sh` — local driver that swaps `paths_to_mutate`/`tests_dir` per target (fresnel, parsing, kernels, compliance, tissue).
- `.github/workflows/release.yml` — new `mutmut` job. Triggers only on `vX.Y.0` tags (`if: endsWith(github.ref_name, '.0')`), `continue-on-error: true`, 45 min timeout, uploads `mutmut_results_*.txt` as an artifact. Runs the fresnel, compliance, and parsing sweeps.

## Notes for the minor-release job

- Expected runtime (from local timings): fresnel ~16 s + compliance ~unknown (not yet measured, estimate <30 s given the module size) + parsing ~34 s, plus env setup. Total should land well under the 45 min budget.
- `continue-on-error: true`: the job reports a mutation score but never blocks a release. Once two or three minor-release runs have established a baseline, tighten to a hard threshold (e.g. fail if the score on fresnel drops below 85%, parsing below 90%).
- Artifact retention: GitHub default (90 days). The score per target is easy to diff across releases from the uploaded `.txt`.
- The `AEGIS_DATA_DIR` env is required because tests hit `resolve_skin_model` which opens the IT'IS SQLite DB. CI checkout already has `data/` alongside `src/`, so pointing to `${{ github.workspace }}/data` is enough.
