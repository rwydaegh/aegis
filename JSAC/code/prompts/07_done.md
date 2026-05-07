# 07 — Tier-C decision: completed

*Author: Claude (`claude-opus-4-7`), 2026-05-04. Companion to `07_tier_c_decision.md`.*

## TL;DR

**Option (a) — modelled.** The monostatic radar link budget closes by ≥30 dB at the paper's plaza range, so the tier-C ISAC row in §VI stays. But two numbers in the paper are wrong: **azimuth HPBW is 12.7°, not 6°**, and **range resolution is 0.375 m at the 400 MHz NR FR2 carrier, not 5 m** (the 5 m only matches SSB-sync-band processing). The decision artefact carries a one-paragraph drop-in §VI rewrite that fixes both.

Tier D is preserved as the regulator-defined fallback for sensing blind spots; option (b) lives there, where it always belonged.

## What I did

1. **Read context first**:
   - `paper_v2.tex` §V tab:what-twin-needs, §VI tab:tiers + cadence + closed-loop ops, §VII scenario.
   - `brainstorm_opus_round3.md` retreat reasoning (vital-signs killed; RCS-only kept).
   - `01_bystander_detection_alternatives_answer.md` agent-1 background research.
   - `JSAC/code/ROADMAP.md` to understand where new code should live.

2. **Computed the link budget**: 26 GHz, 8×8 panel (~21 dBi each side), 30 dBm Tx (51 dBm EIRP), 0 dBsm body, 400 MHz, NF 6 dB, Pfa 1e-6, three CPI choices. At R = 50 m: single-snapshot SNR ≈ 14.3 dB; with 10 ms CPI (600 OFDM symbols at μ=2) integrated SNR is 42.1 dB and Pd → 1 by Albersheim.

3. **Built `src/aegis/sensing/`**: ~250 LOC, no GPU dependence.
   - `monostatic_snr_db()` — radar equation in dBm.
   - `detection_probability()` — Albersheim Pd, closed-form inversion at N = 1.
   - `angular_resolution_deg()`, `range_resolution_m()`, `crossrange_resolution_m()`, `tier_c_cell_area_m2()` — textbook resolutions.
   - `occupancy_envelope_density()` — Fruin-anchored density presets (quiet 0.05, Brussels 0.25, Shibuya 0.5, dense 1.0 bodies/m²) for tier-D.
   - `SensingGeometry` and `DetectionResult` dataclasses, plus a bundled `detection()` helper.

4. **Tests** (`tests/test_sensing_rcs.py`, 19 tests, all pass):
   - Textbook formulas for range / HPBW / crossrange.
   - Radar equation against a hand-computed reference at the paper's operating point.
   - Albersheim Pd against Skolnik Table 2.1 values (Pd=0.5 at 11.2 dB, Pd=0.9 at 13.2 dB).
   - Monotonicity, integration-gain additivity, validators with `match=` strings.
   - Density-preset ordering and validation.

5. **Experiment artefacts** in `JSAC/code/experiments/tier_c_decision/`:
   - `detection_vs_range.py` — runs the sweep, writes the figure + JSON.
   - `detection_vs_range.{pdf,png}` — two-panel figure (integrated SNR vs R; Pd vs R; three CPI choices; plaza-range annotation).
   - `link_budget.json` — operating point, geometry, SNR, Pd at R=50 m, max-Pd99 ranges.
   - `decision.md` — the full decision artefact with link-budget numbers, two paper-number corrections, drop-in §VI prose, and a list of what was deliberately left out.
   - `README.md` — reproduction recipe.

6. **Lint / format / tests** all clean: `ruff check`, `ruff format --check`, `pytest tests/test_sensing_rcs.py`.

## Files touched / created

```
new   src/aegis/sensing/__init__.py
new   src/aegis/sensing/rcs.py
new   tests/test_sensing_rcs.py
new   JSAC/code/experiments/tier_c_decision/decision.md
new   JSAC/code/experiments/tier_c_decision/README.md
new   JSAC/code/experiments/tier_c_decision/detection_vs_range.py
new   JSAC/code/experiments/tier_c_decision/detection_vs_range.pdf
new   JSAC/code/experiments/tier_c_decision/detection_vs_range.png
new   JSAC/code/experiments/tier_c_decision/link_budget.json
new   JSAC/code/prompts/07_done.md   (this file)
```

No existing files modified.

## Numbers, for the paper team

At R = 50 m on 8×8 @ 26 GHz, 30 dBm Tx, 0 dBsm body, 400 MHz, NF 6 dB, Pfa = 1e-6:

| Quantity | Value | Paper §VI claim |
|---|---|---|
| Single-snapshot SNR | 14.3 dB | (not stated) |
| Integrated SNR (10 ms CPI) | 42.1 dB | (not stated) |
| Pd at 10 ms CPI | 1.0 (saturated) | (not stated) |
| Azimuth HPBW | 12.69° | "~6°" — wrong by 2× |
| Range resolution at 400 MHz | 0.375 m | "~5 m" — wrong (5 m only at SSB ~30 MHz) |
| Crossrange at 50 m | 11.07 m | (implied 5 m) |
| Cell footprint at 50 m | 4.15 m² | (not stated) |
| Bodies per cell at Brussels Grand Place peak (0.25/m²) | ~1.0 | (not stated) |

Max range at Pd ≥ 0.99: 137 m (1 ms CPI), ≥200 m (10 ms / 100 ms CPI).

## What this is NOT

- A tracker, multi-target deconfliction module, clutter rejector, or micro-Doppler stack — the brief explicitly capped scope at "can we detect at all."
- A field measurement — the link budget is theory + textbook RCS values; closest published precedent is Ericsson's NR-DL bistatic indoor trial.
- A deletion of tier D — tier D survives as the regulator-defined fallback for sensing blind spots, and now has Fruin-anchored density presets.
- A change to the algorithmic side — both tier C and tier D feed the same Cauchy worst-case precoder budget.

## Status

Not committed. Awaiting Robin's call on whether to lump as one commit (module + tests + experiment + decision) or split (module + tests vs experiment + decision).
