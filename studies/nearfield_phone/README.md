# Near-field hand-held device exposure study

Computes ICNIRP 2020 exposure metrics for a smartphone (IFA/PIFA) held near a
phantom, across a large sweep of positions, distances, 3D orientations,
phantoms and FR1 bands, and answers the dose-model team's two questions
(distance dependence and uncertainty of normalized SAR). The whole pipeline is
differentiable.

## Layout

- `config.py` - phantoms, masses, bands, pattern loading, RNG for orientations.
- `run_sweep.py` - the big sweep -> `out/sweep_*.parquet` (one row per config).
- `analysis.py` - distance-law fit and uncertainty statistics.
- `make_assets.py` - report figures + the partner workbook `out/nearfield_dose_results.xlsx`.
- `make_methods_figs.py` - placement geometry and example APD map.
- `differentiable_poc.py` - sensitivity Jacobian, gradient-based orientation
  design, and Newton compliance-distance solve -> `out/poc_results.json`.
- `report/technical_report.tex` (+ `.pdf`) - the IEEE-style technical report.
- `report/email_to_hamed.md` - the plain-language reply for the dose-model team.

The physics lives in the reusable package `src/aegis/nearfield/`
(`patterns.py`, `phone.py`, `metrics.py`, `scenarios.py`); tests in
`tests/test_nearfield.py`.

## Reproduce

```bash
# 1. the sweep (numpy backend; ~15 min for Duke, lighter for the others)
python -m studies.nearfield_phone.run_sweep --phantoms duke --n-dist 20 --n-orient 64 --tag duke
python -m studies.nearfield_phone.run_sweep --phantoms ella thelonious eartha --n-dist 16 --n-orient 32 --tag others

# 2. figures + Excel
python -m studies.nearfield_phone.make_methods_figs
python -m studies.nearfield_phone.make_assets

# 3. differentiability PoC (JAX backend, set automatically)
python -m studies.nearfield_phone.differentiable_poc

# 4. compile the report
cd report && latexmk -pdf technical_report.tex
```

The free-space antenna patterns are read from `../../goliat_farfield_results/`
(eight FR1 bands, Sim4Life near-to-far transform).

## Normalization scope

The original sweep and its generated report/workbook use **1 W radiated**.
They are not CNR-normalized near-field deliverables. CNR specifies a
band-dependent **input power** calibrated on a flat phantom. Applying that
convention requires an explicit input-to-radiated conversion or empirical
calibration, followed by the target input power exactly once.

The original distance/orientation study uses geometric landmark proxies and
omits the body argument needed to activate the current Fock gate. Its fitted
distance correction is not a direct mass-averaged brain calculation. Re-run
and validate the requested physics and normalization before partner release.

## Headline results (Duke, front of eyes, 2450 MHz, per 1 W radiated)

- Distance law: `S(d) = S_ref * ((d_ref + delta)/(d + delta))^2`,
  delta ~ 6 mm, R^2 = 0.9999 for the local metrics.
- Orientation uncertainty: CV ~ 27% (whole-body) to ~42% (psSAR10g);
  inter-individual adds ~30-40%.
- Differentiable inverse design cuts head psSAR10g 4.5x below the nominal pose
  and beats a 512-sample brute-force orientation scan.
