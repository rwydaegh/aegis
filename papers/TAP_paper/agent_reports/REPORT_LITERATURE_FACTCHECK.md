# Literature fact-check report — TAP paper

Cross-checked `papers/TAP_paper/paper.tex` and `scripts/lit_waterfall.py` against the
underlying source papers (Flintoft 2014, Bamba 2014, Zhang 2017 thesis, Kodera 2024,
Diao 2024) and against the corresponding section of `theory/monograph_v2.tex`. Sources
read: `papers/key_literature/Flintoft_2014...pdf`, `papers/key_literature/A formula
for human average whole-body SAR .pdf` (this is Bamba 2014 PMB, **not** a Hirata
paper despite the file name), `papers/key_literature/zhang.pdf`, and
`papers/key_literature/Kodera2024.pdf`. No Diao PDF is in the repo.

The core question the user raised: are we comparing the right things, and are the
"matches" really matches? The honest answer is **no, not in several panels**. There
are also one citation error and one figure-caption error that should be fixed before
review. Below, every issue is documented with the source page or table.

---

## 1. Bamba citation points to the wrong paper

`paper.tex` (bib entry `Bamba2014`):

```
A. Bamba, W. Joseph, ..., L. Martens,
"Validation of experimental whole-body SAR assessment method in a complex
indoor environment," Bioelectromagnetics, vol. 34, no. 2,
pp. 122-132, Feb. 2013.
```

That entry is the wrong paper. Every quantitative claim attached to `\cite{Bamba2014}`
in the body of the TAP paper (the η(f) formula, the 0.50–0.56 range, the 4 phantoms,
the 1.45–5.8 GHz band) is **from Bamba 2014 PMB**:

> A. Bamba, W. Joseph, G. Vermeeren, A. Thielens, E. Tanghe, L. Martens,
> "A formula for human average whole-body SARwb under diffuse fields exposure
> in the GHz region," Phys. Med. Biol. 59 (2014) 7435–7456,
> doi:10.1088/0031-9155/59/23/7435.

The Bioelectromagnetics 2013 paper cited in the bibliography is a chamber-method
validation paper at 1.8 GHz only and does **not** contain the η(f) formula. The
monograph (`monograph_v2.tex` lines 627–631 and 795–796) splits these correctly as
`Bamba2012` and `Bamba2014`. The TAP bib needs the same split.

---

## 2. Bamba panel: the trend is wrong, not just the offset

This is the most important factual issue. The TAP paper writes:

> Bamba's empirical efficiency η(f) for diffuse-field exposure tracks T̄(f)
> within 5%–10% across 1.45–5.8 GHz. (sec V.D and Table I, Bamba row)

Bamba's regression (PMB 2014, eq. 8): η(f) = −1.7827×10⁻⁵·f_MHz + 0.5859.
Framework T̄ from `paper.tex` Table I (skin, IT'IS Cole–Cole):

| f [GHz] | Bamba η | Framework T̄ | (η − T̄)/T̄ |
|--:|--:|--:|--:|
| 1.45 | 0.560 | ≈ 0.481 | **+16.4 %** |
| 2.00 | 0.550 | ≈ 0.485 | +13.4 % |
| 2.45 | 0.542 | ≈ 0.488 | +11.1 % |
| 3.00 | 0.532 | ≈ 0.491 |  +8.4 % |
| 5.80 | 0.482 | ≈ 0.496 |  −2.8 % |

The "5%–10%" range only describes the upper half of the band. At the bottom of the
band the gap is 16 %, not 5–10 %. More importantly, **the slopes have opposite sign**:
Bamba's η decreases with frequency; the framework's T̄ increases. The two lines cross
near 5–6 GHz. Calling this "tracking" is misleading.

The TAP paper hand-waves this with a creeping-wave / finite-curvature argument:

> their η is fit from full-body FDTD on ellipsoidal phantoms in diffuse-field
> exposure, and absorbs creeping-wave and finite-curvature contributions that the
> planar-tissue T̄ omits.

That story is plausible (body-Mie diffraction adds absorption at low f and decays as
ka grows), but it is asserted, not derived. There is no quantitative estimate of the
diffraction tail in the TAP paper to back the convergence claim. The panel in
`lit_waterfall.pdf` and the row in Table I should be honest about the slope mismatch
and the band-edge gap, not paper over it with the "5–10 %" framing.

Also note: in panel (c) of `lit_waterfall.py`, the small black "Bamba FDTD points"
diamonds are **not** Bamba's published FDTD results either — they are the seven
frequencies of his linear regression, evaluated on his eq. 8. So that panel shows the
fit twice (line + the same fit's seven evaluation points) and labels both as
"Bamba". The actual scatter of η around the line at the seven simulation
frequencies (Bamba 2014 Fig. 3) is not in the panel.

---

## 3. Bamba "4 FDTD phantoms" caption is mis-leading

Figure caption (`paper.tex` line ≈1160):

> (c) Bamba 2014, 4 FDTD phantoms, 1.45–5.8 GHz, against T̄(f).

In Bamba 2014 PMB, the 7 frequencies ×4 phantoms used to fit η are **four
ellipsoids** (average man, average woman, 10-yo, 5-yo), not the four Virtual Family
heterogeneous models (Bamba 2014, Sec. 3.1: "the ellipsoidal models are assigned with
the appropriate dielectric properties"). The Virtual Family phantoms (Thelonious,
Billie, Ella, Duke) are used **only for validation, only at 3 GHz**.

So "4 FDTD phantoms" is technically defensible (it is 4 ellipsoid phantoms in FDTD)
but it lets a reader assume those phantoms are anatomical. The body text in
sec V.D ("ellipsoidal phantoms") is correct; the figure caption is the one that is
loose. The monograph version of the same row says explicitly "FDTD simulations of
ellipsoidal body models" (`monograph_v2.tex` line 630), which is what the figure
caption should say.

---

## 4. Kodera panel is circular: it plots framework T₀ as if it were Kodera's data

`scripts/lit_waterfall.py`:

```python
KODERA_GHZ = np.array([10.0, 28.0, 60.0, 100.0])
KODERA_T0_AT_F, _ = framework_curves(KODERA_GHZ)
KODERA_T = KODERA_T0_AT_F.copy()        # <-- Kodera "data" is just framework T_0
```

The Kodera triangles in panel (d) and panel (e) of the waterfall figure are not
Kodera's reported T_tr values. They are the **framework's own T₀(f)** sampled at
the four Kodera frequencies. Plotting them on top of the framework T₀ curve produces
a perfect overlay, which is what the published figure shows.

This is not a fact-check issue with Kodera — it is a self-referential plot. Either
digitize the actual T_tr values from Kodera 2024 Fig. 9 (his 1-D multilayer slab
calculation, with values that are ≈ 0.4–0.6 across 1–100 GHz and depend on skin
thickness) or remove the Kodera markers and rely on the verbal claim "≤ 5 %" only.

A related framing issue: the TAP paper identifies Kodera's T_tr with the
normal-incidence Fresnel T₀. T_tr in Kodera is computed from a 1-D skin/SAT/fat/
muscle stack (his Fig. 5 and eq. 4), not from a half-space. At mmWave the stack
collapses to T₀ because the skin penetration depth is small, but the identification
"T_tr ≡ T₀" is only an asymptote. The introduction wording "Kodera et al. fit a
transmission coefficient T_tr that matches FDTD to 5 %" is fine; the later phrase
"the Kodera transmission coefficient T_tr is the normal-incidence Fresnel
transmission T₀" is a simplification that does not hold below 6 GHz.

---

## 5. Kodera Fig. 13 is described incorrectly

`paper.tex` (sec V.D, last paragraph):

> Their Fig. 13 compiles whole-body absorbed SAR data across about ten prior
> numerical and experimental studies (TARO, HANAKO, Bahillo, Kuhn, Christ,
> Andersen, Hirata 2008, Drossos, plus the four parametric Models I–IV).
> The data span 1–100 GHz at 10 W/m².

Kodera 2024 Fig. 13 caption (verbatim from the PDF):

> Fig. 13. Comparison of WBASAR at frequencies ranging from **1 to 10 GHz**.
> S_in = 10 W/m².

And the legend in Fig. 13 lists, in order: Model I (HANAKO) with scheme 1; Model I
(TARO) with scheme 4; **Nagaoka & Watanabe 2008** (TARO, HANAKO); Dimbylow 2002
(NORMAN); Dimbylow 2005 (NAOMI); Wang et al. 2006 (TARO); **Uusitupa et al. 2010**
(NORMAN, TARO, HANAKO, Brucks, Duke, Ella); Bakker et al. 2011 (Duke, Ella); Lee
et al. 2012 (Korean male); Wang et al. 2012; Flintoft et al. 2014 (measured).

So the description is wrong on three counts:

1. **Range**: 1–10 GHz, not 1–100 GHz.
2. **Models**: Only Model I appears in Fig. 13 (HANAKO scheme 1, TARO scheme 4).
   Models II–V exist in Kodera but are in different figures (Fig. 6 onward).
3. **Studies**: "Bahillo, Kuhn, Christ, Andersen, Hirata 2008, Drossos" are not in
   Fig. 13. The actual list is Nagaoka & Watanabe 2008, Dimbylow 2002, Dimbylow
   2005, Wang 2006, Uusitupa 2010, Bakker 2011, Lee 2012, Wang 2012, Flintoft 2014.

The Kodera paragraph either describes the wrong figure or is summarizing several
figures collectively. Fix the citation: Fig. 13 if it is really 1–10 GHz, otherwise
point at Fig. 6 (1-D vs 3-D, Models I–V, 1–100 GHz) plus Fig. 13 (sub-10 GHz
literature comparison) separately.

---

## 6. Flintoft panel: numbers match, error bars are slightly inflated

Flintoft Table 6 ⟨Q^a⟩ at γ_s = 1 (the column α): 0.700, 0.507, 0.417, 0.403,
0.414, 0.419 at 1/3/5/7/9/11 GHz. The TAP figure (`lit_waterfall.py` line 78)
matches exactly. ✓

Standard errors in Table 6: ±0.013, ±0.009, ±0.007, ±0.007, ±0.007, ±0.007. The
script uses ±0.013, ±0.011, ±0.009, ±0.008, ±0.008, ±0.007. The four middle bars
are inflated by 0.001–0.002. Cosmetic, not consequential, but the comment in the
script says "Table 6 SEs" so it ought to use the actual SEs.

Flintoft cohort N = 60 ✓ (Table 1, p. 3303). Mean d_SF range 2.3–20.4 mm ✓ — TAP
says "2–20 mm" which is fine. The β slope at 3 GHz (−0.0061 mm⁻¹, R² = 0.40) ✓.
The slope falling to −0.0030 mm⁻¹ at 9 GHz ✓ (it is −0.0034, −0.0030, −0.0034 at
7/9/11 GHz; calling the band's value −0.0030 is at the low edge of the band).

The γ_s value used in the panel (0.865, the AEGIS Thelonious AO mean) is **above**
the upper edge of Flintoft's geometric estimate (0.75–0.85, p. 3301). The TAP paper
already notes this ("near the upper end of Flintoft's band"); fine, just keep the
note next to the panel where the dividing happens, not only in sec III.A.

---

## 7. Zhang panel: envelope is hand-eyeballed from a 48-curve overlay

The values in `lit_waterfall.py`:

```python
ZHANG_GHZ    = [1, 2, 3, 4, 6, 9, 12, 15, 18]
ZHANG_XI_MED = [0.85, 0.75, 0.62, 0.50, 0.49, 0.52, 0.55, 0.57, 0.60]
ZHANG_XI_LO  = [0.70, 0.60, 0.50, 0.40, 0.45, 0.45, 0.45, 0.45, 0.45]
ZHANG_XI_HI  = [1.00, 0.90, 0.75, 0.62, 0.55, 0.60, 0.65, 0.65, 0.68]
```

These are not in any table in Zhang's thesis. They are eyeballed from Fig. 4.11
(p. 102), which is 48 individual ξ(f) curves overlaid with no per-subject
identification. The envelope shape is qualitatively right (drop from ~0.85 at 1 GHz
to ~0.5 minimum at 4–6 GHz, gentle rise to ~0.55–0.65 by 18 GHz), but the precise
median values, particularly the 0.49 at 6 GHz, are below the visual median in the
figure (which sits closer to 0.55). The high-end envelope at 6 GHz (0.55) also
looks low against the figure.

This is not a fabrication — it is a digitized envelope of an undigitized figure —
but the figure caption and the table row should make that clear ("envelope
digitized from Zhang 2017 Fig. 4.11"). As written, the panel reads as if these were
published numbers.

The published statement in Zhang's thesis (p. 101, with Fig. 4.11):
"plateau ξ ≈ 0.45–0.65 across all 48 subjects, 6–18 GHz" ✓. So the band
0.45–0.65 in TAP Table I row is correct; the per-frequency triplets in the panel
are an interpretation.

---

## 8. The Fabry–Pérot mechanism is not as new as the intro implies

`paper.tex` introduction (sec I, third gap):

> Third, the 3 GHz dip observed by Flintoft and Zhang has no quantitative
> explanation.

That is overstated. Zhang's thesis does provide a quantitative model for the dip:

- Zhang Sec. 2.2, "Multilayer planar absorption" (pp. 19–27).
- Zhang eq. (2.11): ξ_plane = σ_a / S_silhouette = T (multilayer Fresnel
  transmission), under A_plane = S_silhouette. This is exactly the framework's
  identity in the convex limit.
- Zhang Fig. 2.7 (p. 20): ξ vs frequency for a 2 mm skin / fat / muscle stack
  with fat thickness 2/6/10/14/18 mm. The figure shows distinct enhancement peaks
  ("x" markers) and reduction dips ("o" markers) that shift to lower frequency as
  fat thickness grows — i.e. the fat layer behaves as a Fabry–Pérot etalon, even
  though Zhang names it a "matching layer" rather than calling out Fabry–Pérot.

Flintoft 2014 also explicitly attributes the 3 GHz dip to "reflections between the
layers of tissues" (p. 3308) — qualitative, but the mechanism is named.

What is genuinely new in the TAP paper is **not** the Fabry–Pérot mechanism. It is
(a) embedding T_lay(f, d_SF) in a Cauchy-style direction-averaged identity, and
(b) using the 0.0061 mm⁻¹ slope of ⟨Q^a⟩ vs d_SF as a quantitative comparator.

The paper text in `subsec:fp` does acknowledge Zhang's prior derivation. The
introduction needs to be brought in line: "the 3 GHz dip has no closed-form
direction-averaged form" or "no whole-body integral has been written for the
layered correction" — both are true and credit-preserving. "No quantitative
explanation" is not.

The monograph (`monograph_v2.tex` lines 640–655) is more careful: "no quantitative
model was given" is attached to Flintoft only, and Zhang is credited with the
fat-layer Fabry–Pérot interpretation.

---

## 9. "Empirical scalars not derived from Maxwell's equations"

`paper.tex` introduction:

> the empirical scalars are fitted, not derived from Maxwell's equations, so they
> encode geometry, polarization, and tissue physics in a single number.

Half-true. Bamba's η is fitted from FDTD, agreed. But Kodera's T_tr is computed
from a 1-D Maxwell solution of a multilayer slab (skin/SAT/fat/muscle/...), then
used to predict 3-D FDTD. So T_tr is **derived** from Maxwell, just not from a
closed-form Fresnel formula. The contribution of the TAP paper is the
closed-form derivation, not the Maxwell-vs-fitted distinction. The intro should be
softened: "are not given in closed form" rather than "are fitted, not derived from
Maxwell's equations".

---

## 10. Diao 2024: T = 0.52 at 28 GHz

We do not have the Diao 2024 PDF in the repo; the TAP and monograph both quote
T = 0.52 with the same words. The IT'IS skin Fresnel value is T₀ = 0.536 at
28 GHz (paper.tex Table I). The 3 % discrepancy is plausible: Diao's anatomical
FDTD includes layered tissue and curvature, which can shift T by a few percent
either way, and the IT'IS dielectric uncertainty alone gives ±7 % on T₀
(paper.tex sec V.D). Cannot fully verify without the source, but no flag.

---

## Summary table of issues

| # | Issue | Severity | Where in paper |
|---|---|---|---|
| 1 | `Bamba2014` bib entry points to 2013 Bioelectromagnetics paper, not 2014 PMB | **must fix** | bib |
| 2 | Bamba η has opposite slope to T̄; "5–10 % tracking" understates the band-edge gap (16 %) | **must fix** | sec V.D, Table I, Fig. waterfall (c) |
| 3 | Bamba "4 FDTD phantoms" caption hides that they are ellipsoids, not Virtual Family | should fix | Fig. waterfall caption |
| 4 | Kodera markers in waterfall (d) and (e) plot framework T₀, not Kodera T_tr | **must fix** | `lit_waterfall.py` and resulting figure |
| 5 | Fig. 13 of Kodera misdescribed (range, models, study list) | **must fix** | sec V.D last paragraph |
| 6 | Flintoft error bars in panel (a) inflated by 0.001–0.002 vs Table 6 | minor | `lit_waterfall.py` line 79 |
| 7 | Zhang ξ envelope is digitized from a 48-curve overlay; presented as if tabulated | should fix | sec V.D, panel (b) caption |
| 8 | Intro overstates novelty: the Fabry–Pérot mechanism is in Zhang Sec. 2.2 already | should fix | sec I third gap; `subsec:fp` is fine |
| 9 | "Empirical scalars not derived from Maxwell" is too strong (Kodera derives T_tr from a 1-D slab) | should fix | sec I |
| 10 | Diao T = 0.52 at 28 GHz | not verified, no flag | sec V.D |

Items 1, 2, 4, 5 are factual; the rest are framing or presentation. None of them
invalidate the closed-form derivation in sections II–IV; the issue is that the
literature comparison in sec V.D and Table I currently sells the agreement harder
than the data supports.

A more honest version of the literature panel would do three things:

1. Plot Bamba's actual seven simulated η values (Fig. 3 of Bamba 2014) with the
   linear fit, and overlay T̄(f). State explicitly that the slopes disagree and
   that they cross near 5.5 GHz; attribute the divergence to body-Mie diffraction
   on ellipsoidal phantoms (a verbal hypothesis, not a measurement).
2. Either digitize the actual T_tr values from Kodera Fig. 9 or remove the Kodera
   markers and rely on text only ("Kodera reports T_tr ∈ 0.4–0.6 over 10–100 GHz,
   matching framework T₀ to 5 % on the same band").
3. Mark the Zhang envelope as a digitization of Fig. 4.11, not a published table.

These changes would not weaken the paper. The closed-form result and the
phantom-level FDTD agreement (1.012 at 5.8 GHz) are strong on their own. The
literature panel would be more credible without the parts that are doing extra
work for it.
