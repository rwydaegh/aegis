# 06 — CSI per-path calibration residual

**Goal.** Implement the §V.B per-path complex-amplitude calibration described in the paper, characterise its residual error vs. UL SNR, and produce one figure that can sit in §V.

## Blockers

None on the code side, but the brief depends on having a *path dictionary* `D` to calibrate against. You can synthesise one for this brief (see below); the more elaborate "real" dictionary is part of brief 08 (plaza_run).

## Why this matters

Paper §V (`sec:scene-dict`) introduces the scene path dictionary — a static catalogue of ray-traced paths between the BS and a per-body region — that the BS uses as the geometry input to Q construction. §V.B is the bridge between that *in-silico* dictionary and *deployed* reality: per-path complex amplitudes `α_n` are calibrated from observed UL CSI via least squares.

The paper describes the procedure in prose. There's no code, no figure, and no characterisation of how well calibration actually closes the in-silico-to-deployed gap. A reviewer will ask "how good is the calibration when SNR is 10 dB? 0 dB?". One residual-vs-SNR figure answers that.

## What's already in place

- `src/aegis/integration/differt.py` — produces ray-traced paths via DiffeRT for a given scene + endpoint.
- `src/aegis/modal_rt/` — Modal-hosted T4 + L4 ray tracers if you want to lean on cloud GPU.
- `src/aegis/paths.py` — `PropagationPaths` dataclass that already carries per-path `k̂`, `ψ`, `element_index`, etc. This is functionally the path-dictionary atom.
- `src/aegis/channel/` — 3GPP-aware preset loaders; useful as a "deployed" channel model to feed perturbed CSI back to calibration.
- Paper §V.B has the LS formulation; `theory/exposure_null_precoding.tex` mentions the calibration step in the multi-body context.

## The flow you're characterising

1. Generate or load a path dictionary `D` for one body in one scene (synthetic plaza is fine for this brief; doesn't need to be Brussels).
2. Pretend that's the in-silico ground truth. Apply per-path multiplicative complex perturbations to simulate the in-silico-vs-deployed gap (the calibration target). The size and structure of those perturbations is a modelling choice — start simple (Gaussian on log-magnitude, von Mises on phase, IID across paths), document it.
3. Synthesise UL CSI from the perturbed dictionary at a given SNR.
4. Run the LS calibration to recover the perturbations.
5. Measure residual: `‖α_calibrated - α_perturbed‖ / ‖α_perturbed‖` in dB, or whatever metric reads cleanly. Sweep SNR.

## Open questions for the dev

- **What perturbation model.** IID complex Gaussian on `α_n` is the easy default. A more honest model would have correlated perturbations (e.g. shadowing across paths from the same reflector). Pick whatever you can defend in one sentence.
- **How many paths in the test dictionary.** The rank-CDF experiment uses 60 subpaths for 3GPP UMa-LOS. Match that, or sweep dictionary size and show the calibration error as a function of `N_paths`.
- **SNR sweep range.** Probably 0–30 dB in 5 dB steps. Constrained by realism: BS UL pilots in Brussels-style mmWave deployment.
- **Whether to land calibration as a public API**. The ROADMAP suggests `src/aegis/twin/path_dictionary.py`. If a `calibrate(dictionary, csi) -> dictionary` method has obvious shape, ship it; if it'd be premature to commit to one, leave it as a script function in the experiment dir and let brief 08 promote it later.
- **Whether 38.901 LSP correlation helps or hurts.** The 91 channel presets in `data/channel_presets/` already encode log-normal shadowing and angular spread. They could double as the "deployed" channel for this brief. Or you can keep it synthetic. Decide based on what's cleanest to present.

## What "done" looks like

- A script in `JSAC/code/experiments/csi_calibration/` (or similar) that runs the SNR sweep and produces a `residual_vs_snr.pdf` figure.
- The figure shows post-calibration residual as a function of UL SNR, with at least one curve. Multiple curves (different `N_paths`, different perturbation magnitudes) are nice if they fit cleanly.
- A README documenting the perturbation model, the SNR sweep range, and the calibration LS formulation actually used (which may differ in details from the paper's prose; that's fine, just write down what you did).
- If the calibration code is generic enough, a stub at `src/aegis/twin/path_dictionary.py` (or wherever the dev places it) so brief 08 can call it later.

## What this is NOT

- A model of in-silico vs deployed mismatch. The perturbation is a stand-in, not a calibrated noise floor.
- A real-time calibration loop. One-shot LS is fine for the figure.
- A statement about whether the calibration is good enough for production use. Just measure and report.
- A replacement for §V's prose. Paper §V stays as it is; this brief produces the supporting figure.
