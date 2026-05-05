# CSI per-path calibration residual (paper §V.B)

This experiment characterises the bridge §V.B describes: the BS holds an
in-silico path dictionary `D` (rays + per-path complex amplitudes
`α_n`), but the *deployed* channel has different per-path amplitudes
because of uncatalogued scatterers, foliage, building-material
mismatches, weather. §V.B closes the gap with a per-path complex scale
factor `β_n` fit by least squares against measured uplink CSI.

The paper describes the procedure in prose; there is no code, no figure,
and no statement of how well calibration tracks the deployed channel
when the uplink SNR is finite. This experiment supplies that one
figure: post-calibration residual vs. UL SNR, for a few path-set sizes
and two LS variants (plain and ridge-Tikhonov).

## What it does

For one body in one cell, the experiment runs Monte Carlo over

* 7 uplink SNRs (0 .. 30 dB in 5 dB steps, per BS-element receive SNR)
* 3 path-set sizes (`N_paths ∈ {20, 40, 60}`, matching the rank-CDF
  experiment's 60 used for 3GPP UMa-LOS)
* 200 trials per `(SNR, N_paths)` cell

For each trial we

1. Sample `N_paths` BS-side departure directions uniformly inside
   ±60° azimuth × ±30° elevation around an 8×8 (M = 64) UPA broadside.
2. Sample in-silico per-path amplitudes `α_n ~ CN(0, 1)`.
3. Sample IID multiplicative perturbations `γ_n` with log-normal
   magnitude (`σ_mag = 3 dB`) and von-Mises phase (`κ = 4 ⇒ ~30°
   circular stddev`). These play the role of the deployed-vs-in-silico
   gap.
4. Form the deployed CSI `h = A diag(γ) α` where `A ∈ ℂ^{M×N}` is the
   BS-side steering matrix; add per-element AWGN at the requested SNR.
5. Run the §V.B LS calibration (`aegis.twin.path_dictionary
   .calibrate_amplitudes`) twice — plain LS (`ridge=0`) and ridge LS
   (`ridge=0.01`) — to recover `β̂`.
6. Record the parameter-space residual
   `ρ = ‖β̂ − γ‖ / ‖γ‖`, reported in dB. Also record the
   no-calibration baseline `ρ_nc = ‖1 − γ‖ / ‖γ‖` (the residual you'd
   pay if you trusted the in-silico amplitudes verbatim).

The figure plots median `ρ` vs. SNR for both LS variants (one curve per
`N_paths`) with the 10th / 90th-percentile band shaded for plain LS.
The dotted horizontal line is the median no-calibration baseline.

## Headline result

For these settings, the median no-calibration residual sits at
**−4.7 dB**: trusting the in-silico amplitudes alone leaves a ~58 %
relative error on `α`. Where calibration becomes worthwhile depends
jointly on `N_paths` and SNR.

| Regime | Plain LS beats no-cal at | Ridge LS beats no-cal at |
|---|---|---|
| `N=20` (heavily overdetermined) | ≥ 15 dB UL SNR (−21 dB at 30 dB) | similar |
| `N=40` (mildly overdetermined)  | only at extremely high SNR        | ≥ 20 dB UL SNR |
| `N=60` (`N → M_ant`)            | not in 0–30 dB sweep              | ≥ 25 dB UL SNR (barely) |

The plain-LS failure at `N → M_ant` is the standard story: the
column-correlated steering matrix has small singular values that
amplify noise. Ridge-Tikhonov regularisation (here `λ = 10⁻²`) buys
back ~25 dB of headroom at `N = 60`. Production calibration should
either pick `N_paths < M_ant / 2`, regularise, or merge correlated
paths into clusters before fitting.

## Files

* `run_calibration.py` — the experiment. ~10 s on a laptop.
* `residual_vs_snr.{pdf,png}` — the figure.
* `residual_table.md` — median (90th-percentile) residual per cell, per
  LS variant.
* `residuals.npz` — raw per-trial residuals.

## What this is NOT

* A deployed-vs-in-silico mismatch *model*. The IID log-normal /
  von-Mises perturbation is a stand-in, not a calibrated noise floor.
  A more honest model would have correlated perturbations across paths
  sharing a reflector; that's deferred to brief 08 if it matters.
* A real-time loop. One-shot LS, single coherence interval, single
  cooperating UE.
* A statement that this calibration is good enough for production. We
  measure and report only.

## Notes on the LS formulation

The paper writes the calibration as
`β_k ← argmin ‖h^meas − β_k^T · ĥ_k‖²` where
`ĥ_k = α_k^T Φ(t_k) J`. In this brief there is no body translation
`Φ(t)` or Jacobian `J` — calibration acts on `α` only, so we collapse
the predicted channel to `ĥ_k = A · diag(α^insilico) · 1`, and the
design matrix becomes `A · diag(α^insilico)`. Brief 08 can fold the
`Φ J` factor in at the plaza level without changing the solver — the
LS is still linear in `β`.

The reusable helper lives at `aegis.twin.path_dictionary
.calibrate_amplitudes`.
