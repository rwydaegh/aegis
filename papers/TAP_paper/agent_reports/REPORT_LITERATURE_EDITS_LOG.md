# Edits log — literature fact-check session

All file changes made during the literature fact-check and rewrite, in
chronological order. Reference reports for context:

- `papers/TAP_paper/agent_reports/REPORT_LITERATURE_FACTCHECK.md` (initial
  audit, 10 issues identified)
- `papers/TAP_paper/agent_reports/REPORT_LITERATURE_FIX_PLAN.md` (proposed
  fixes with real numbers from the source PDFs, plus citation plan)

---

## New files created

| Path | Purpose |
|---|---|
| `papers/TAP_paper/agent_reports/REPORT_LITERATURE_FACTCHECK.md` | Initial audit, 10 issues with severity tags |
| `papers/TAP_paper/agent_reports/REPORT_LITERATURE_FIX_PLAN.md` | Fix plan with real digitised numbers from Bamba PMB 2014, Kodera Fig. 9 / Fig. 13, Diao 2024, Zhang Fig. 4.9 + Fig. 4.11; plus citation plan with 11 candidate additions |
| `theory/errata_monograph.txt` | Errata note for the same `Bamba2014` bib bug present in `monograph_v2.tex` line 5798 |
| `papers/TAP_paper/agent_reports/REPORT_LITERATURE_EDITS_LOG.md` | This file |

---

## `papers/TAP_paper/paper.tex` — edits

### 1. Bamba 2014 bibliography entry (`\bibitem{Bamba2014}`, lines ≈1779–1784)

**Before**: pointed at Bamba 2013 BEM paper "Validation of experimental
whole-body SAR assessment method in a complex indoor environment"
(Bioelectromagnetics 34, 122–132).

**After**: points at the actual paper containing the η(f) regression —
Bamba *et al.*, "A formula for human average whole-body SAR_wb under
diffuse fields exposure in the GHz region," *Phys. Med. Biol.* 59 (23),
7435–7456, 2014, doi:10.1088/0031-9155/59/23/7435.

### 2. Intro third-gap claim (≈line 189)

**Before**: "Third, the 3 GHz dip observed by Flintoft and Zhang has no
quantitative explanation."

**After**: "Third, the 3 GHz dip observed by Flintoft and Zhang admits a
planar multilayer-transmission interpretation~\cite{Zhang2017thesis} but
has not been embedded in a body-surface integral, so the connection to a
closed-form direction-averaged whole-body identity is missing."

### 3. Intro first-gap claim (≈line 186)

**Before**: "First, the empirical scalars are fitted, not derived from
Maxwell's equations, so they encode geometry, polarization, and tissue
physics in a single number."

**After**: "First, the empirical scalars are obtained from numerical FDTD
or one-dimensional multilayer solutions~\cite{Kodera2024,Bamba2014} per
phantom and per frequency, not from a closed-form expression, so they
encode geometry, polarization, and tissue physics in a single number that
varies between studies."

### 4. Sec. III.A Bamba claim (≈lines 888–895)

**Before**: "Bamba's empirical efficiency η(f) for diffuse-field exposure
tracks T̄(f) within 5%–10% across 1.45–5.8 GHz~\cite{Bamba2014}. The
systematic offset is consistent with finite-curvature creeping-wave
contributions on ellipsoidal phantoms."

**After**: Reframed to acknowledge the framework is a mmWave method,
quote the actual 3 % match at 5.8 GHz, and explicitly note that
agreement at 1–2 GHz is not claimed. Body-Mie language preserved for the
divergence at the low edge of Bamba's calibration band.

### 5. Sec. V.D figure caption for `\Cref{fig:waterfall}` (≈lines 1167–1174)

**Before**: described panels (b), (c), (d) without enough detail; (c)
said "Bamba 2014, 4 FDTD phantoms" without distinguishing
ellipsoid-fit phantoms from validation anatomical phantoms; (d) said
"Diao 2024 (anatomical FDTD, 28 GHz) and Kodera 2024 (parametric FDTD,
10–100 GHz) on T₀(f)".

**After**: Panel (b) caption now distinguishes Zhang's Fig. 4.9
population fit from his Fig. 4.11 envelope. Panel (c) caption mentions
the four ellipsoid phantoms, the per-phantom 6 % scatter, and the four
anatomical-phantom validation residuals (Thelonious/Billie/Ella/Duke at
3 GHz). Panel (d) caption now describes Kodera Fig. 9 plus Diao
plane-wave T_eff(f) on TARO plus the 5 G patch back-fit at 28 GHz, and
notes the body-Mie regime explicitly.

### 6. Sec. V.D Bamba paragraph after `\Cref{tab:waterfall}` (≈lines 1178–1187)

**Before**: explained the "5–10 % offset" as creeping-wave / curvature
contributions and noted convergence at 5.8 GHz to 5 %.

**After**: Quotes the actual 3 % match at 5.8 GHz; explicitly states
that 1.45–3 GHz lies outside the geometric-optics validity window
(`tab:bands`); notes that the same body-Mie mechanism appears in
Diao's plane-wave TARO sweep (panel (d)), where T_eff rises from 0.43
at 10 GHz to nearly 0.9 at 1 GHz on the same anatomical phantom.

### 7. Sec. V.D Kodera paragraph (≈lines 1236–1248)

**Before**: described Fig. 13 as compiling "TARO, HANAKO, Bahillo,
Kuhn, Christ, Andersen, Hirata 2008, Drossos, plus the four parametric
Models I–IV" over 1–100 GHz.

**After**: Fig. 13 is correctly described as 1–10 GHz with nine
numerical phantom studies and two RC measurement campaigns; Fig. 6 is
named separately for the 1–100 GHz five-model (Models I–V) extension.
Also adds the observation that Kodera's homogeneous-skin curve (Fig. 9
right axis) reproduces Fresnel T₀ within 1–2 % above 6 GHz and
oscillates around it below 6 GHz with the same Fabry–Pérot structure
as our `\Tlay` in `subsec:fp`.

### 8. `tab:waterfall` Bamba row (≈line 1193)

**Before**: "η(f) = 0.50–0.56 at 1.5–5.8 GHz, 4 FDTD phantoms" matched
in "5%–10%".

**After**: "η(f) = 0.48–0.56 at 1.45–5.8 GHz, four FDTD ellipsoids"
matched in "3 % at 5.8 GHz; convergent with frequency".

---

## `papers/TAP_paper/scripts/lit_waterfall.py` — edits

### 9. Flintoft SE error bars

**Before**: `[0.013, 0.011, 0.009, 0.008, 0.008, 0.007]` (Table-6 SEs
inflated at 3, 5, 7, 9 GHz).

**After**: `[0.013, 0.009, 0.007, 0.007, 0.007, 0.007]` matching
Flintoft 2014 Table 6 exactly.

### 10. Flintoft unification axis (`FLINTOFT_UNI`)

**Before**: `FLINTOFT_QA * A_AB_OVER_A`, a double application of γ_s.

**After**: `FLINTOFT_QA` directly, because Flintoft's
⟨Q^a⟩ at γ_s=1 = 4σ_a/BSA already equals T̄·A_ab/A in the framework's
notation. Removes a systematic 0.865 displacement of the Flintoft
points in panel (e).

### 11. Zhang ξ — split into two presentations

**Before**: a single hand-eyeballed median + envelope from Fig. 4.11
spanning 1–18 GHz.

**After**: two arrays
  - `ZHANG_PLATEAU_GHZ` / `ZHANG_PLATEAU_XI`: 6/9/12/15/18 GHz at
    ξ = 4·C₁(f) = 0.40 / 0.48 / 0.52 / 0.54 / 0.56, read off Zhang
    Fig. 4.9 linear-fit slope (his Sec. 4.5).
  - `ZHANG_ENV_GHZ` / `ZHANG_ENV_LO` / `ZHANG_ENV_HI`: 1/2/3/4/6 GHz
    digitised envelope from Fig. 4.11 with explicit caption note that
    the envelope is digitised, the plateau is from a published linear
    fit.

### 12. Bamba presentation

**Before**: solid regression line + seven diamond markers on the same
line (the diamonds are evaluations of the fit, not raw data; this
double-counted the same information).

**After**: dashed-thin regression line; diamonds with vertical error
bars scaled linearly from 0 % at 1.45 GHz to ±6 % at 5.8 GHz
(Bamba's published per-phantom scatter, Sec. 3.1.2 of PMB 2014); plus
× markers at 3 GHz showing his Table 7 anatomical-phantom validation
residuals (Thelonious −39.4 %, Billie −11.7 %, Ella +10.7 %, Duke
+10.6 %, all relative to η(3 GHz) = 0.532).

### 13. Kodera T_tr — replace circular plot with real values

**Before**:

```python
KODERA_GHZ = np.array([10.0, 28.0, 60.0, 100.0])
KODERA_T0_AT_F, _ = framework_curves(KODERA_GHZ)
KODERA_T = KODERA_T0_AT_F.copy()    # plotted framework T_0 as Kodera
```

**After**: seven values digitised from Kodera 2024 Fig. 9 right-axis
homogeneous-skin curve, with ±0.015 visual-uncertainty bars:

```python
KODERA_GHZ = np.array([1.0, 3.0, 6.0, 10.0, 30.0, 60.0, 100.0])
KODERA_T   = np.array([0.43, 0.45, 0.47, 0.49, 0.55, 0.62, 0.70])
KODERA_T_ERR = np.full_like(KODERA_T, 0.015)
```

### 14. Diao 2024 — split patch and plane-wave datasets

**Before**: a single point at 28 GHz with T = 0.52, no plane-wave data.

**After**: two distinct datasets from the same paper:
  - `DIAO_PATCH_GHZ` / `DIAO_PATCH_T`: T = 0.52 at 28 GHz from his
    Sec. IV.B 5G patch-array configuration on TARO (back-fit from
    WBASAR/IPD = 0.0043 m²/kg, PA = 0.54 m², W = 65 kg).
  - `DIAO_PW_GHZ` / `DIAO_PW_WBASAR` / `DIAO_PW_T_EFF`: seven points
    from his Fig. 8 plane-wave WBASAR sweep on TARO at 1, 3, 6, 10,
    20, 25, 30 GHz, converted via T_eff = WBASAR·W/(PA·S_in) =
    12.04·WBASAR.

### 15. Panel functions updated

- `_panel_zhang`: uses split plateau + envelope arrays; legend now
  identifies the source figures.
- `_panel_bamba`: dashed regression line, per-phantom error bars,
  anatomical-phantom validation scatter; y-range expanded to 0.30–0.62
  to fit the −40 % validation point.
- `_panel_kodera_diao`: x-range extended to 0.85–115 GHz to show the
  Diao plane-wave low-frequency body-Mie rise; y-range expanded to
  0.30–1.00; both Kodera and Diao plane-wave plotted with error bars
  and connecting line respectively.
- `_panel_unification`: same dataset additions as panel (d); error
  bars on Bamba and Kodera; both Diao datasets plotted distinctly.
- `build_summary`: same updates for the one-panel summary version.

### 16. CSV writer

Updated to emit one row per data point in every dataset, with proper
labels and uncertainties:

- Flintoft 2014: native value Q^a, uncertainty = Table-6 SE.
- Zhang 2017: separate rows for plateau (4·C₁ fit) and envelope
  (Fig. 4.11 lo/hi).
- Bamba 2014: regression points with per-phantom scatter; Table 7
  validation as separate rows.
- Kodera 2024: Fig. 9 right-axis readings with ±0.015 uncertainty.
- Diao 2024: patch (28 GHz) and plane-wave (1–30 GHz) as separate
  studies.
- AEGIS-vs-FDTD ratio: unchanged.

---

## Generated artifacts

- `papers/TAP_paper/scripts/lit_waterfall.pdf` and `.png` regenerated.
- `papers/TAP_paper/figures/lit_waterfall.pdf` and `.png` synced from the
  scripts directory (same as before — Makefile reads from `figures/`).
- `papers/TAP_paper/scripts/lit_waterfall_data.csv` regenerated with
  the new schema.
- `papers/TAP_paper/scripts/lit_waterfall_framework_T.csv` unchanged.
- `papers/TAP_paper/paper.pdf` rebuilt — 16 pages, no LaTeX errors.

---

## What was *not* edited

- `paper_SI.tex` — not touched in this session.
- `monograph_v2.tex` — not touched; `theory/errata_monograph.txt`
  describes the change to be applied.
- Citation additions from the plan document (Andersen 2007, Hallbjorner
  2005, Diao 2021, Li 2019, Sasaki 2017, Christ 2020a, Christ 2006,
  Colombi 2018, Bamba 2012, Gosselin 2011, Vermeeren 2008): held for
  the next round per user request ("start with this, then I'll continue
  on citation plan").

---

## What still depends on user sign-off

The fixes above are conservative and factual. The proposed citation
additions and the broader set of "passing-by" `[X]` slots in
section B of `REPORT_LITERATURE_FIX_PLAN.md` are still pending your
read-through.
