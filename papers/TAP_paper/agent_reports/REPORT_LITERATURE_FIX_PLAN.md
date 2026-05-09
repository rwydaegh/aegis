# Literature comparison — fix plan and citation plan

This is the prep document the user asked for. No edits to `paper.tex` or
`lit_waterfall.py` yet. Each section ends with the concrete proposed change so
you can sign off section by section.

Important contextual point flagged by the user (and a thing I missed in the first
pass): the framework is a **mmWave** method. It does not claim a tight numerical
match at 1–2 GHz. The Bamba "trend mismatch" reading in the previous report was
too strong on its own; it is a real effect, but the conclusion should be
"converges to T̄ in the GO regime, deviates in the body-Mie regime as expected,"
not "the trends disagree." Same logic applies to the 1–3 GHz dip in Flintoft and
Zhang — that band is intentionally outside the geometric-optics validity window.

---

## 1. Bamba citation bug — also present in `monograph_v2.tex`

The bibliography bug is identical in both documents: the `Bamba2014` key in
`monograph_v2.tex` (lines 5798–5804) and in `paper.tex` both point at the BEM
2013 paper "Validation of experimental whole-body SAR assessment method in a
complex indoor environment", but every quantitative claim attached to that key
is from the **PMB 2014** paper "A formula for human average whole-body SARwb
under diffuse fields exposure in the GHz region."

The two are different papers with different scopes (BEM 2013 = chamber-method
validation at 1.8 GHz only, no η formula; PMB 2014 = the η(f) regression on
ellipsoid FDTD over 1.45–5.8 GHz, the formula we actually use).

**Proposed fix (both docs)**: rename and add. Change `Bamba2014` to point at
the PMB 2014 paper. Keep `Bamba2012` (TEMC 2012) for the experimental
room-electromagnetics paper. Add a third entry `Bamba2013bem` for the BEM 2013
validation paper (only if it is cited anywhere — currently it is **not** cited
in the TAP paper body, only in the broken bib entry, so we can drop it).

Replacement bib entry for the TAP paper (IEEE style, matching the format
already used):

```
\bibitem{Bamba2014}
A.~Bamba, W.~Joseph, G.~Vermeeren, A.~Thielens, E.~Tanghe, and L.~Martens,
  ``A formula for human average whole-body SARwb under diffuse fields
  exposure in the GHz region,'' \emph{Phys. Med. Biol.}, vol.~59, no.~23,
  pp.~7435--7456, Dec. 2014, doi: \doi{10.1088/0031-9155/59/23/7435}.
```

This is also the fix that needs porting back into `monograph_v2.tex` line
5798.

---

## 2. Bamba panel — what the actual numbers are, what to plot

The user asked: what are the right numbers, then?

**Answer**: the seven black diamonds in panel (c) are mathematically Bamba's
own published η values per frequency. He averaged the four ellipsoid-FDTD
runs into a single η per frequency, then fit the line. The seven points and
the line are the same data because R² = 0.9981 — they sit on top of each
other (Bamba 2014 PMB Fig. 3 is the same picture).

So the issue is not "wrong numbers" — it is "redundant presentation that hides
the actual phantom-to-phantom scatter." Bamba reports per-phantom variation
explicitly: "the maximum relative difference from the mean value is about 6 %
and this occurs at 5800 MHz" (Sec. 3.1.2, p. 7442 of PMB 2014). The implication
is that the per-phantom η ranges from ≈ 0.51 to ≈ 0.51 ± 6 % at 5.8 GHz,
i.e. roughly 0.45–0.51 across the four ellipsoids; tighter at lower
frequencies.

There are two more numbers Bamba reports that the panel should expose:
- **Validation residuals on Virtual Family at 3 GHz** (his Table 7, DMC):
  Thelonious −39.4 %, Billie −11.7 %, Ella +10.7 %, Duke +10.6 %.
  This tells the reader that even at the central frequency where Bamba's
  formula is calibrated, anatomical phantoms scatter by 10–40 % from the
  ellipsoid-fit prediction. The framework cannot do better than this on the
  same anatomical phantoms in the same band, and that is fine — both are
  outside the GO band.
- **k(φ,ψ) polarisation correction**, k_V ∈ [0.12, 0.21], k_H ∈ [0.18, 0.21]
  (his Fig. 4). This is what Bamba uses to map η_diffuse to η_LOS; it is the
  empirical analogue of the framework's polarisation correction in
  `subsec:exact-law`.

**Proposed change to `lit_waterfall.py` panel (c) and surrounding text**:

1. Keep the seven Bamba points and the regression line, but draw the line
   thinner and dashed. Add a label "Bamba 2014, ellipsoid-fit (PMB)" once.
2. Add a vertical error bar on each Bamba point, scaled linearly from 0 % at
   1.45 GHz to ±6 % at 5.8 GHz (Bamba's stated phantom scatter).
3. Add four scatter points at 3 GHz from Bamba Table 7, marker style "x":
   −39.4 %, −11.7 %, +10.7 %, +10.6 % relative to the regression value
   η(3 GHz) = 0.532. Label "Bamba 2014, anatomical-phantom validation".
4. In the figure caption, drop "4 FDTD phantoms" and replace with
   "η(f) regression on four FDTD ellipsoids; anatomical-phantom validation
   at 3 GHz."
5. In the body text, soften "tracks T̄ within 5–10 %" to:
   > Bamba's ellipsoid-fit η(f) coincides with T̄(f) within 3 % at 5.8 GHz
   > and crosses below T̄ above 6 GHz, with a divergence at the 1.5 GHz end
   > of the band consistent with the body-Mie correction expected outside
   > the geometric-optics regime (sec. V.A and `tab:bands`).
6. In `tab:waterfall`, change the Bamba match column from "5–10 %" to
   "3 % at 5.8 GHz; convergent with frequency."

This does not weaken the comparison; it correctly bounds it.

---

## 3. Bamba caption — ellipsoids, not anatomical

The body text in Sec. V.D already says "ellipsoidal phantoms." Only the figure
caption says "4 FDTD phantoms" without qualifier. The proposed change in
section 2 above also fixes this.

---

## 4. Kodera panel — what the actual T_tr values are

**Source**: Kodera 2024 Fig. 9 (right axis, "Power Transmission Coefficient").
The right-axis curve is the homogeneous-skin theoretical T from a 1-D plane-wave
calculation (same physics as the framework's T₀). The colored curves on the
left axis (1 mm, 1.5 mm, 2 mm skin layered models) show Fabry–Pérot
oscillations *around* the homogeneous baseline below ~6 GHz.

Reading the smooth black curve from Fig. 9 (with ±0.01 visual uncertainty):

| f [GHz] | Kodera T_tr (homog.) | Framework T₀ |
|--:|--:|--:|
|   1 | ≈ 0.43 | 0.451 (interp.) |
|   3 | ≈ 0.45 | 0.474 |
|   6 | ≈ 0.47 | 0.481 |
|  10 | ≈ 0.49 | 0.489 |
|  30 | ≈ 0.55 | 0.541 |
|  60 | ≈ 0.62 | 0.622 |
| 100 | ≈ 0.70 | 0.701 |

Not a circular plot anymore — these are read off Kodera Fig. 9 right axis. They
agree with framework T₀ within 1–2 % at every point above 6 GHz. The visible
deviations are within reading uncertainty.

**Layered T_tr (Kodera left-axis curves, normalised to S_in = 1 W/m²)**: shows
the Fabry–Pérot enhancement / dip around 1.5 GHz / 4 GHz for the 1 mm and
1.5 mm skin models. This is the same mechanism as the TAP paper's `\Tlay(f, d_SF)`
fat-layer correction in `subsec:fp` — Kodera does it on skin thickness, the TAP
paper does it on subcutaneous fat thickness, but the formal structure is the
same (multilayer transfer-matrix). This deserves a sentence.

**Proposed change to `lit_waterfall.py` panel (d)**:

```python
# Replace:
KODERA_GHZ = np.array([10.0, 28.0, 60.0, 100.0])
KODERA_T0_AT_F, _ = framework_curves(KODERA_GHZ)
KODERA_T = KODERA_T0_AT_F.copy()
# With (digitised from Kodera 2024 Fig. 9 right axis,
# ±0.01 visual uncertainty):
KODERA_GHZ = np.array([1.0, 3.0, 6.0, 10.0, 30.0, 60.0, 100.0])
KODERA_T   = np.array([0.43, 0.45, 0.47, 0.49, 0.55, 0.62, 0.70])
KODERA_T_ERR = np.array([0.015]*7)   # visual digitisation envelope
```

Show error bars. Keep the Diao point as a single * marker at 28 GHz at
T = 0.52 (his Fig. 9 / Sec. IV.B; see section 5 below). The ±5 % grey band
around the framework T₀ curve makes the agreement legible without the false
claim of "perfect overlay."

---

## 5. Kodera Fig. 13 description — replace with the actual content

The user is right that Fig. 13 is a goldmine. Cropped and zoomed, the legend
contains 11 entries and the x-axis is **1–10 GHz**, S_in = 10 W/m²:

- Kodera 2024 (presented): Model I (TARO, scheme 1); Model I (HANAKO,
  scheme 1); Model I (TARO, scheme 4).
- Nagaoka & Watanabe 2008: TARO; HANAKO.
- Dimbylow 2002: NORMAN.
- Dimbylow 2005: NAOMI.
- Wang et al. 2006: TARO.
- Uusitupa et al. 2010: NORMAN, TARO, HANAKO, Brucks, Duke, Ella.
- Bakker et al. 2011: Duke; Ella.
- Lee et al. 2012: Korean male.
- Wang et al. 2012 (measured).
- Flintoft et al. 2014 (measured).

So 9 prior numerical studies (one per author/year row), plus 2 measurement
studies. Total ≈ 22 phantom × frequency points. The y-axis spread is
0.03–0.10 W/kg, with a clear minimum near 4–6 GHz.

**Proposed prose** (replaces the existing paragraph in Sec. V.D ending "across
about ten prior numerical and experimental studies (TARO, HANAKO, ..., plus the
four parametric Models I–IV). The data span 1–100 GHz at 10 W/m².",
`paper.tex` ≈line 1212):

> Kodera \emph{et al.}~\cite{Kodera2024} report the closest numerical
> counterpart to the present analysis. Their Fig.~13 compiles whole-body
> absorbed-SAR data over $1$--$10$~GHz at $\Sinc = 10$~W/m$^2$ across nine
> numerical studies (NORMAN \cite{Dimbylow2002}; NAOMI \cite{Dimbylow2005};
> TARO and HANAKO from Nagaoka and Watanabe~\cite{Nagaoka2008}, Wang
> \emph{et al.}~\cite{Wang2006}, and Uusitupa
> \emph{et al.}~\cite{Uusitupa2010}; Duke and Ella from Uusitupa
> \emph{et al.}~\cite{Uusitupa2010} and Bakker \emph{et al.}~\cite{Bakker2011};
> Korean male from Lee \emph{et al.}~\cite{Lee2012}) and two reverberation-chamber
> studies (Wang \emph{et al.}~\cite{Wang2012}, Flintoft
> \emph{et al.}~\cite{Flintoft2014}). All datasets cluster within a factor of
> two between $1$ and $10$~GHz, with a shared minimum near $5$~GHz that
> \cref{eq:cauchy-exact} reproduces through $\Tbar(f)$ and the layered correction
> of \cref{subsec:fp}. Their Fig.~6 extends the same comparison to $100$~GHz on
> five parametric layered models (Models I--V) and shows the same asymptotic
> plateau.

Note the model count change: I–V (five), not I–IV (four). And the range fix:
Fig. 13 is 1–10 GHz, Fig. 6 is 1–100 GHz. The original paragraph conflated the
two figures.

---

## 6. Flintoft error bars

Already verified: Table 6 SEs are ±0.013, ±0.009, ±0.007, ×4. Script has
±0.013, ±0.011, ±0.009, ±0.008, ±0.008, ±0.007. **Proposed change**:

```python
FLINTOFT_QA_ERR = np.array([0.013, 0.009, 0.007, 0.007, 0.007, 0.007])
```

---

## 7. Zhang ξ values — better numbers

Two improvements available:

**a) Use Zhang's own population-level fit instead of the eyeballed
Fig. 4.11 envelope.** From Zhang Sec. 4.5 / Fig. 4.9: above 6 GHz, ⟨σ_a⟩ is
linear in BSA with slope C₁(f) and intercept C₂(f) ≈ 0; population mean
ξ ≈ 4 C₁(f). C₁ runs from ≈ 0.10 at 6 GHz to ≈ 0.14 at 18 GHz, so

| f [GHz] | Zhang population ξ |
|--:|--:|
|  6 | ≈ 0.40 |
|  9 | ≈ 0.48 |
| 12 | ≈ 0.52 |
| 15 | ≈ 0.54 |
| 18 | ≈ 0.56 |

These are **lower** than the script's median (0.49–0.60). The script values
sit closer to the upper edge of Fig. 4.11 than to the population fit. The Zhang
population fit also matches T̄ (≈ 0.49–0.51 over 6–18 GHz) much more cleanly
than the eyeballed median, so the panel will look better with these numbers.

**b) For the 1–6 GHz part of the curve, keep the envelope band** (it is real,
the per-subject curves do span 0.4–1.0 at 1 GHz) but mark it as digitised, not
tabulated.

**Proposed change to `lit_waterfall.py`**: split into two arrays. Tabulated
plateau values from Zhang C₁(f) for 6–18 GHz; digitised envelope for 1–6 GHz
with a clear caption.

```python
# Tabulated population mean from Zhang 2017 Fig. 4.9 (C1 fit, plateau band):
ZHANG_PLATEAU_GHZ = np.array([6.0, 9.0, 12.0, 15.0, 18.0])
ZHANG_PLATEAU_XI  = np.array([0.40, 0.48, 0.52, 0.54, 0.56])
# Digitised envelope from Zhang 2017 Fig. 4.11 (1-6 GHz, body-Mie regime):
ZHANG_ENV_GHZ = np.array([1.0, 2.0, 3.0, 4.0, 6.0])
ZHANG_ENV_LO  = np.array([0.70, 0.60, 0.50, 0.40, 0.40])
ZHANG_ENV_HI  = np.array([1.00, 0.90, 0.75, 0.62, 0.55])
```

Caption update: "Zhang 2017 envelope (1–6 GHz, digitised from Fig. 4.11) and
population mean (6–18 GHz, from Fig. 4.9 linear fit)."

---

## 8. Fabry–Pérot framing

Agreed it should be complementary, not centerpiece. Two proposed prose
changes:

**a) Intro (`paper.tex` line ≈189), change**

> Third, the 3~GHz dip observed by Flintoft and Zhang has no quantitative
> explanation.

**to**

> Third, the 3~GHz dip observed by Flintoft and Zhang admits a planar
> multilayer-transmission interpretation~\cite{Zhang2017thesis,Christ2006}, but
> has not been embedded in a body-surface integral, so the connection to a
> closed-form direction-averaged whole-body identity is missing.

**b) `subsec:fp` keeps the existing Zhang attribution but the framing should
be adjusted upstream so it reads as a sub-6 GHz extension of the framework, not
as a new physical mechanism.** A single adjective in the contribution list
(item 1 or item 4 of the intro `\begin{enumerate}`) along the lines of
"…with a layered Fabry–Pérot extension that integrates the planar
multilayer-transmission analysis of Zhang and Christ into the Cauchy
direction-averaged identity, enabling a 1–6 GHz pointwise SAR
correction…" would close the loop without rewriting the section.

The pSAR_10g chapter already needs Tlay; that connection is the place to
emphasise it, since regulatory SAR_10g is the practical motivation for keeping
the multilayer correction in the framework at all.

---

## 9. "Empirical scalars not derived from Maxwell" — softening

Replace, intro line ≈186:

> First, the empirical scalars are fitted, not derived from Maxwell's
> equations, so they encode geometry, polarization, and tissue physics in a
> single number.

with:

> First, the empirical scalars are obtained from numerical FDTD or 1-D
> multilayer solutions per phantom and per frequency~\cite{Kodera2024,Bamba2014},
> not from a closed-form expression, so they encode geometry, polarization,
> and tissue physics in a single number that varies between studies.

This is technically accurate (Kodera's T_tr does come from Maxwell, just
numerically) and removes the strawman.

---

## 10. Diao 2024 — fully verified, plus extra data

Read the Diao 2024 PDF in full. The T = 0.52 number comes from a specific
configuration:

> "The ratio of WBASAR to the averaged IPD was maintained at approximately
> 0.0043 m²/kg, therefore the transmittance for the TARO model from the
> front can be estimated as 0.52" (Diao 2024 PMB IEEE TEMC Sec. IV.B,
> p. 1356).

Configuration: TARO body model, 65 kg, projected area 0.54 m², 28 GHz, **8×16
patch array antenna at 1–8 m distance** (5G base-station scenario), front
exposure. The T = 0.52 is a back-fit from
WBASAR = PA × IPD × T / W. Framework T₀ = 0.536; gap 0.016, i.e. 3 %.

Diao 2024 Fig. 8 also gives plane-wave WBASAR on TARO from 1 to 30 GHz
(IPD = 10 W/m²), which is *not* in the TAP paper's Bamba/Flintoft/Zhang/Kodera
mix and would be a strong cross-check. Reading the figure:

| f [GHz] | Diao WBASAR (TARO, plane wave) [W/kg] |
|--:|--:|
|  1 | 0.073 |
|  3 | 0.064 |
|  6 | ≈ 0.040 |
| 10 | 0.036 |
| 20 | ≈ 0.044 |
| 25 | ≈ 0.044 |
| 30 | 0.045 |

The minimum near 10 GHz is the same body-Mie minimum that shows up in Kodera
Fig. 13 and in the Flintoft / Zhang chamber data. To get this on the same
T̄ × Aab/A axis we need TARO's projected area (0.54 m²) and mass (65 kg):

Diao T_eff(f) = WBASAR(f) × W / (PA × Sinc) = WBASAR × 65 / (0.54 × 10)
            = 12.04 × WBASAR

| f [GHz] | Diao WBASAR | Diao T_eff (TARO, plane-wave) |
|--:|--:|--:|
|  1 | 0.073 | 0.879 |
|  3 | 0.064 | 0.770 |
|  6 | 0.040 | 0.481 |
| 10 | 0.036 | 0.433 |
| 20 | 0.044 | 0.530 |
| 25 | 0.044 | 0.530 |
| 30 | 0.045 | 0.542 |

That table has its own story: Diao's T_eff is *bigger* than 1 below 3 GHz,
which means the TARO-FDTD absorbs more than the projected area × homogeneous
T₀ allows. That is body-Mie/whole-body resonance, exactly the mechanism the
TAP paper attributes the body-Mie correction to. Above 6 GHz, T_eff converges
to T₀ within 5 % (0.481 at 6 GHz, framework 0.481; 0.542 at 30 GHz, framework
0.541).

This is, frankly, a much cleaner test of the framework than the Bamba
ellipsoid-fit. **Suggested addition**: a Diao-2024 plane-wave overlay on panel
(d) of the waterfall figure, with the Diao-Kodera intercomparison Table IV
(both papers cross-check at 1, 3, 10, 25 GHz on TARO with very small
differences) as a sanity tie.

Bib entry already in the TAP paper for `Diao2024`. No new bib needed for the
plane-wave addition.

---

## Citation plan: passing-by attributions and which to add

The user asked for a strategy on "passing-by" citations: places where a single
extra `[X]` would correctly attribute prior art without forcing extra prose.

### A. Citations the TAP paper should add (with proposed slot)

All bib entries available verbatim from `monograph_v2.tex`. IEEE format, same
style as the existing `\bibitem`s in `paper.tex`.

| New cite | Where to add it (TAP paper section / line) | Reason |
|---|---|---|
| `Andersen2007` | end of Sec. III.A first paragraph (room electromagnetics framing) | Foundational room-electromagnetics formula `P_abs = S_total · ⟨σ_a⟩`, predates the framework's diffuse-field claims |
| `Hallbjorner2005` | end of Sec. III.A second paragraph (γ_s discussion) | Direction-averaged ACS depends only on permittivity of large lossy bodies, not shape — this is the prior result the framework's "T̄ depends on tissue, not body" claim builds on |
| `Diao2021` | Sec. II ("the empirical scalars are fitted…") and Sec. III.A "near-constancy across angle" line | Direct experimental confirmation of pseudo-Brewster: heating factor ≈ flat vs incidence angle, mmWave |
| `Li2019` | Sec. II "near-constancy across angle and polarization" and Sec. VII.B (high-frequency boundary) | Numerical confirmation of pseudo-Brewster, 6 GHz–1 THz |
| `Sasaki2017` | Sec. II.C (T₀ at normal incidence numerical reference) | MC-computed T₀(f) reference dataset, 10 GHz–1 THz |
| `Christ2020a` | Sec. VII.B (high-frequency boundary, stratum corneum matching) | Stratum corneum acts as quarter-wave matching layer above 15 GHz — directly relevant |
| `Christ2006` | Sec. III.B (`subsec:fp` introduction) | Earliest quantitative multilayer-tissue model in this band — credits the planar-stack lineage upstream of Zhang |
| `Colombi2018` | Sec. II ("a series of numerical studies confirmed…") | One of three references already used together (`Kodera2024,Diao2024,Colombi2018`) in the monograph; the TAP paper drops the third |
| `Bamba2012` | Sec. III.A (room-electromagnetics, alongside `Bamba2014`) | The experimental method paper that the η formula builds on |
| `Gosselin2011` | Sec. VI.A (compliance section) | Estimation formulas for SAR exposed to base-station antennas — direct prior art for closed-form compliance |
| `Vermeeren2008` | Sec. V.D (waterfall comparison, child-phantom note) | Child-phantom WBASAR study directly relevant to `\cref{rem:reflevel-shortfall}` |

The Wang2006, Wang2012, Lee2012, Bakker2011, Uusitupa2010, Nagaoka2008,
Dimbylow2005 references are needed only if the rewritten Kodera Fig. 13
paragraph (section 5) keeps its detailed enumeration. If we contract that
paragraph to "compiles ten prior FDTD and chamber studies on TARO, HANAKO and
Virtual Family phantoms~\cite{Kodera2024}", we can avoid adding seven new bib
entries. Recommend the contracted form.

### B. Sentences in the current TAP paper that could carry an extra `[X]`

Pick the cheap ones — places where one extra `[X]` strengthens credit without
opening a side discussion.

1. **Sec. I, intro, "Direct evaluation uses Finite-Difference Time-Domain
   (FDTD) simulation on an anatomical phantom~\cite{Kodera2024,Diao2024}."**
   → add `Christ2006, Colombi2018` to the existing list. The two foundational
   FDTD references that the monograph uses for this same sentence.

2. **Sec. I, intro, the Bamba paragraph "Bamba et al. \cite{Bamba2014} divide
   $\sigma_a$ by phantom mass and fit an empirical efficiency..."**
   → add `Bamba2012` (the experimental room-electromagnetics paper that the
   formula builds on).

3. **Sec. III.A, "the empirical scalars in the literature reduce to specific
   quantities in the closed forms"** → add `Hallbjorner2005` for the
   prior-art claim about ACS shape-independence.

4. **Sec. III.A, "γ_s is set by hand from surface-area tables \cite{Tomita1999}"**
   → fine as-is.

5. **Sec. III.B, "Pseudo-Brewster compensation"**: existing
   `\cite{Azzam2015,Potter1970,Ohman1977,BornWolf1999}` is good. Add
   `\cite{Li2019,Diao2021}` once at "Empirically, the near-constancy extends
   to $|\ntilde| > 2.5$" (subsec:pB-mech) — these two are the dosimetry-side
   confirmations of exactly this near-constancy.

6. **Sec. IV.A "Self-shadowing and ambient occlusion"**: existing
   `\cite{Zhukov1998,Landis2002,AkenineMoller2018}` is good. Optionally add
   `Pharr2016` (the canonical PBR text) for completeness, low priority.

7. **Sec. IV.D `subsec:fp` "A three-layer transfer-matrix model"**: existing
   `\cite{Chew1995,BornWolf1999}` is good. Add `Christ2006` here as a
   passing-by — the earliest multilayer-tissue model.

8. **Sec. V.A "Mie theory on lossy spheres"**: existing
   `\cite{BohrenHuffman1983}` is good.

9. **Sec. V.D "Combined dosimetry literature"**: existing
   `\cite{Bamba2014,Flintoft2014,Zhang2017thesis,ZhangRobinson2020,Diao2024,Kodera2024}`
   is good. Add `Andersen2007` ("the room-electromagnetics formula
   $P_{\mathrm{abs}} = S_{\mathrm{total}}\,\langle\sigma_a\rangle$") at the
   start of the paragraph that introduces ⟨Q^a⟩, since the chamber method
   itself comes from there.

10. **Sec. VI.A "Whole-body SAR threshold"**: existing
    `\cite{ICNIRP2020,Hirata2007corr,Dimbylow2002}` is good. Add
    `\cite{Gosselin2011}` to the "matches the observation in the dosimetry
    literature" sentence — Gosselin specifically derives compliance estimation
    formulas, the closest prior art to the closed-form compliance the section
    is presenting.

11. **Sec. VII.B "High-frequency boundary"**: add `\cite{Sasaki2017,Christ2020a}`
    once — Sasaki for the 10 GHz–1 THz T₀ Monte-Carlo dataset, Christ for the
    stratum-corneum quarter-wave matching that the discussion of the
    `|\ntilde| > 2.5` weakening above 200 GHz is implicitly leaning on.

### C. Are the chosen "comparators" the right ones?

Honest answer: **mostly yes, with one structural gap.** The chosen
comparators (Bamba, Flintoft, Zhang, Kodera, Diao) cover all of:

- ✓ Reverberation-chamber volunteer studies (Flintoft, Zhang).
- ✓ FDTD on anatomical phantoms (Kodera Fig. 13, Diao TARO).
- ✓ Closed-form-fit prior art (Bamba η, Kodera T_tr).
- ✓ Independent ground truth at 28 GHz (Diao).

What is missing or under-weighted:

1. **Andersen 2007 / Bamba 2012**: the foundational room-electromagnetics
   step. Including it changes nothing quantitatively but corrects the
   intellectual lineage.
2. **Hallbjorner 2005**: shape-independence of ACS for large lossy bodies in
   an RC. This is the closest prior art to the framework's central claim that
   T̄ depends only on tissue, not body. Worth a passing cite.
3. **Diao 2021 / Li 2019**: angular near-constancy of the heating factor.
   The TAP paper currently rests the pseudo-Brewster claim on Azzam 2015
   (optics) without naming the dosimetry-side prior confirmations. One
   passing cite each strengthens this.
4. **Christ 2006**: oldest quantitative multilayer-tissue model. The
   subsec:fp introduction implies this is novel; Christ 2006 already does
   the multilayer math, just at sub-6 GHz on a planar geometry.
5. **Gosselin 2011**: compliance estimation formulas. Closest prior art to
   Sec. VI compliance.

None of these threaten the contribution; all five sharpen the credit.

### D. Other papers I'd want to look at if you can find them

In rough priority order. You said cite without comparing numbers is OK for
most of these, so a single bib entry is enough.

1. **Wang et al. 2006** (TARO at GHz bands, FDTD): the earliest TARO study
   in Kodera Fig. 13. Citation needed only if the Kodera Fig. 13 sentence
   keeps its detailed enumeration; otherwise can be elided.
2. **Uusitupa et al. 2010** (multi-phantom WBASAR at GHz): same.
3. **Nagaoka & Watanabe 2008** (TARO/HANAKO development paper): same.
4. **Foster & Ziskin 2018 / similar mmWave heating reviews**: not in the
   monograph but worth checking for the high-frequency boundary discussion.
5. **Hirata et al. 2010** ("formula on the basis of the analogy of the human
   body and a half-dipole antenna at the resonance frequency", cited inside
   Bamba 2014 PMB): credits the dipole-resonance prior art for the
   sub-300 MHz bound that Sec. VII discusses but does not cite.
6. **Kuhn / Christ 2009-era WBASAR-on-Virtual-Family**: another foundational
   reference that the monograph also doesn't have. Not a blocker.
7. The **Wydaeghe NPJ / PMB papers** the monograph self-cites
   (`Wydaeghe2026npj`, `WydaegheEtAl2026PMB`): include only if they support
   a specific claim, e.g. the 550-FDTD-run base-station campaign mentioned
   in Sec. VI.

If you can dig out PDFs for items 1–4 I can fact-check the lit-comparison
panels against them with the same rigor as Flintoft / Bamba / Kodera.

---

## Summary of proposed edits, ordered by impact

1. **`paper.tex` bib**: replace `Bamba2014` entry with the PMB 2014 paper.
   Same fix in `monograph_v2.tex` line 5798.
2. **`lit_waterfall.py`**: replace `KODERA_T = KODERA_T0_AT_F.copy()` with
   the seven Fig. 9 readings and ±1.5 % error bars.
3. **`lit_waterfall.py`**: split Zhang into a population-fit plateau
   (6–18 GHz from Fig. 4.9) plus a digitised envelope (1–6 GHz from
   Fig. 4.11), with appropriate caption.
4. **`lit_waterfall.py`**: thin Bamba regression line, add per-phantom
   error bars scaled to ±6 % at 5.8 GHz, add anatomical-phantom validation
   scatter at 3 GHz.
5. **`lit_waterfall.py`**: fix Flintoft SEs to Table-6 values
   (`[0.013, 0.009, 0.007, 0.007, 0.007, 0.007]`).
6. **Optional `lit_waterfall.py`**: add Diao 2024 plane-wave T_eff(f) curve
   (1–30 GHz) on panel (d). Strong cross-check.
7. **`paper.tex` Sec. V.D**: rewrite the Kodera Fig. 13 paragraph (section 5
   above).
8. **`paper.tex` intro**: soften "no quantitative explanation" and
   "fitted, not derived from Maxwell's equations" (sections 8 and 9).
9. **`paper.tex` Sec. V.D**: tighten the Bamba match column in
   `tab:waterfall` to "3 % at 5.8 GHz; convergent with frequency."
10. **`paper.tex` body text**: 6–8 passing-by `[X]` additions per
    section B above. Lowest editorial cost, highest credit yield.

Items 1, 2, 5 are pure fact-fixes. Items 3, 4, 7 are presentation upgrades
that make the figure honest. Items 8–10 are credit-preservation. Item 6 is
optional but the data is good enough to be worth showing.

Sign off section by section and I'll execute.
