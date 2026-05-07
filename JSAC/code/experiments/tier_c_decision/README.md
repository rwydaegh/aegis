# tier_c_decision

Closes the open question in `paper_v2.tex` §VI: does monostatic ISAC on the BS's own 8×8 panel actually deliver tier-C bystander localisation at 50 m? See `decision.md` for the answer (yes, with two number corrections to the paper).

## Files

- `decision.md` — the decision artefact, link budget, proposed §VI prose edit.
- `detection_vs_range.py` — runs the link-budget sweep and writes the figure + JSON summary.
- `detection_vs_range.{pdf,png}` — two-panel figure: integrated SNR vs range and Pd vs range, three CPI choices, plaza-range annotation.
- `link_budget.json` — operating point + geometry + SNR + Pd at R = 50 m.

## Reproducing

```
PYTHONPATH=src python3 JSAC/code/experiments/tier_c_decision/detection_vs_range.py
```

Takes <1 s. The figure regenerates deterministically from the constants at the top of the script.

## What this answers

| Question | Answer |
|---|---|
| Does the link budget close at 50 m on an 8×8 @ 26 GHz with 0 dBsm body? | Yes, 14 dB single-snapshot, 42 dB after a 10 ms CPI. Pd → 1 at Pfa=1e-6. |
| What is the actual angular cell at 50 m? | 12.69° HPBW × 0.375 m range = 11.07 m × 0.375 m ≈ 4.15 m² (paper currently claims 6° / 5 m, off by 2x and 13x respectively). |
| Does the literature support this regime? | Textbook radar; closest peer-reviewed demo is Ericsson NR-DL bistatic indoors, no outdoor 50 m monostatic single-panel trial published. |
| Should the paper retreat to occupancy envelope only (tier C → tier D)? | No. Keep tier C with a corrected prose paragraph; tier D continues as the sensing-blind-spot fallback. |

## What this is not

- A multi-target tracker, clutter rejector, or micro-Doppler module.
- A field measurement; the back-of-envelope assumes ideal monostatic conditions and plausibly 5–10 dB optimistic.
- A fix to the algorithmic side; tier C and tier D both feed the same Cauchy worst-case precoder budget.
