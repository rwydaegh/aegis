# City-scale population exposure report

A LaTeX report on population RF exposure under a 28 GHz massive-MIMO deployment,
across ten cities of differing morphology, computed with the deterministic
ray-traced arm of the AEGIS study pipeline. This is the deterministic reference;
the stochastic-vs-deterministic comparison follows.

## One-command regeneration

From the repo root, with the study venv active:

```bash
# 1. Run the ten-city batch (writes results/cities/, ~1-2 h on CPU)
python -m aegis.study.run_cities --config configs/study/ten_cities.yaml --out results/cities

# 2. Pull the figure + per-city table into this report
python papers/city-exposure-study/report/make_report.py --results results/cities

# 3. Build the PDF
cd papers/city-exposure-study/report && pdflatex report.tex && pdflatex report.tex
```

`make_report.py` copies `results/cities/cities_cdf.pdf` into `figures/` and
writes `figures/cities_table.tex` (per-city median and p95) from
`cities_summary.json`.

## What the config controls

`configs/study/ten_cities.yaml`. The cities come from
`aegis.study.run_cities.DEFAULT_CITIES` (ten distinct morphologies) when
`cities.specs` is empty and `cities.count: 10`. Fidelity knobs dialled for
breadth (raise to converge):

- `mobility.n_agents`, `mobility.window_s`: crowd size and window
- `deployment.realizations_K`: deployment marginalisation (1 here)
- `channel.samples_per_src`, `channel.diffraction`: ray-trace fidelity
- `channel.max_center_paths`: caps the exposure-operator cost (strongest paths)
- `dosimetry.peak_sab`: per-triangle peak-Sab map (off here; scalar exposure only)

## Files

- `report.tex` - the report source
- `make_report.py` - assemble figure + table from a batch
- `figures/` - generated (CDF PDF + table tex); not the source of truth
