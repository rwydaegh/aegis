# 06 — CSI per-path calibration residual — DONE

**Status:** shipped, committed `8eeb3c7`, pushed to `origin/master`.

## What was delivered

1. **Reusable LS helper** at `src/aegis/twin/path_dictionary.py`:

   ```python
   from aegis.twin import calibrate_amplitudes
   beta = calibrate_amplitudes(steering, alpha_insilico, h_meas, ridge=0.0)
   ```

   Plain LS (`ridge=0`) or Tikhonov-regularised. Takes the BS-side
   steering matrix `(M, N)`, in-silico per-path amplitudes `(N,)`,
   measured CSI `(M,)`. Returns the per-path complex scale factor
   `β ∈ ℂ^N`. Calibrated dictionary amplitudes for downstream Q
   construction are `α_calibrated = β * α_insilico`.

2. **Experiment** at `JSAC/code/experiments/csi_calibration/`:

   * `run_calibration.py` — Monte Carlo sweep (200 trials × 7 UL SNR
     ∈ {0, 5, …, 30} dB × 3 N_paths ∈ {20, 40, 60}, both plain and
     ridge LS, plus the no-calibration baseline).
   * `residual_vs_snr.{pdf,png}` — the §V figure: per-path scale
     residual (`20 log10 ‖β̂ − γ‖ / ‖γ‖`) vs. UL SNR with the
     no-cal baseline as a dotted reference line.
   * `residual_table.md` — median (90th-percentile) per cell, both
     LS variants.
   * `residuals.npz` — raw per-trial residuals.
   * `README.md` — design decisions, headline numbers, caveats,
     formulation notes.

3. **Unit tests** at `tests/test_twin_path_dictionary.py` (4 cases,
   <1 s, no `slow` marker):
   * Noiseless exact recovery (`β̂ == γ` to FP error).
   * Residual decreases ≥ 15 dB from 0 → 30 dB SNR.
   * Ridge shrinks `‖β̂‖` toward zero.
   * Shape / sign validation raises `ValueError` with informative
     messages.

## Key design choices (recorded in the experiment README)

| Choice | Value | Why |
|---|---|---|
| Perturbation model | IID, log-normal magnitude (σ=3 dB) + von-Mises phase (κ=4 ⇒ ~30° stddev) | Easy default the brief endorses; correlated perturbations across reflectors deferred to brief 08 |
| Array | 8×8 UPA, half-λ spacing, 26 GHz, isotropic elements | Matches `rank_check`; M = 64 |
| Path-set sizes | 20, 40, 60 | 60 matches the rank-CDF UMa-LOS setting; 20/40 sweep shows conditioning behaviour |
| SNR sweep | 0–30 dB step 5 (per-element receive SNR) | Standard UL pilot range |
| Trials | 200 per `(SNR, N_paths)` cell | Tight enough error bars |
| LS variants | plain (`ridge=0`) and Tikhonov (`ridge=1e-2`) | Plain LS overfits at N→M; ridge is the deployable fix |
| Residual metric | parameter-space `‖β̂ − γ‖ / ‖γ‖` in dB | Direct measure of how well calibration would feed Q construction |

## Headline result

No-calibration baseline (just trust in-silico amplitudes): **−4.7 dB**
(median, all trials).

| Regime | Plain LS beats no-cal at | Ridge LS beats no-cal at |
|---|---|---|
| `N = 20` (heavily overdetermined) | ≥ 15 dB UL SNR (−21 dB at 30 dB) | similar |
| `N = 40` (mildly overdetermined)  | only at very high SNR             | ≥ 20 dB UL SNR |
| `N = 60` (`N → M_ant`)            | not in 0–30 dB sweep              | ≥ 25 dB UL SNR (barely) |

The plain-LS failure at `N → M_ant` is the standard noise-amplification
story: column-correlated steering matrix → small singular values →
LS amplifies noise. Ridge buys back ~25 dB at `N = 60`. The honest
operational rule for the paper: pick `N_paths < M_ant / 2`,
regularise, or merge correlated paths into clusters before fitting.

## What was *not* delivered (deliberate scope cuts)

- No `PathDictionary` dataclass with grid lookup / load / save —
  that's brief 08's job (plaza assembly).
- No correlated-perturbation model (per-reflector LSP coupling) — the
  IID stand-in is sufficient for §V.B's "how good is calibration vs.
  SNR" answer.
- No real-time loop, no per-slot recalibration. One-shot LS, single
  cooperating UE.
- No claim that this calibration is good enough for production. The
  brief was "measure and report"; that's what the figure does.

## Verification

* `python -m ruff check src/aegis/twin tests/test_twin_path_dictionary.py` — clean.
* `python -m ruff format --check ...` — clean.
* `python -m pytest tests/test_twin_path_dictionary.py` — 4 passed.
* Sanity: 96 related tests (array_factor / coherent / coherent_edge_cases / paths / twin) still pass.

## Coordination notes

* Other agents are mid-flight on briefs 03 (`coherent/multibody_ecbf.py`),
  04 (`coherent/_fast.py`, `coherent/translation.py`), 07
  (`sensing/`), and the JSAC tree restructure. My commit only stages
  files inside my own scope (`src/aegis/twin/`, the test, the
  experiment dir) — no cross-brief edits, no JSAC restructure
  participation.
* The release reminder fired (66 commits since `v0.32.0`) but a
  release now would tag inconsistent state. Defer to after the hero
  figure lands; the natural moment is a `v0.33.0` minor that bundles
  twin/, sensing/, multibody ECBF, and §V.B as one coherent paper
  bump.
