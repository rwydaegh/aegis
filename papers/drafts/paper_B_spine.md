# Paper B — Medium-level plan

**Working title:** *The absorption-cross-section identity: closed-form
whole-body dosimetry from 100 MHz to 100 GHz, validated against three
independent measurement campaigns.*

**Target venue:** IEEE Transactions on Antennas and Propagation (the
dosimetry / RC community is the natural home).

**Target length:** 12 two-column pages, 7 figures, 4 tables.

**Status:** strongest evidence path. Literature data and FDTD validation
both in hand. Estimated 1 week of writing once the Flintoft supplement
is fetched and the headline waterfall figure is rendered.


## The question (one paragraph)

For 25 years the bioelectromagnetics community has been measuring whole-
body absorption cross-sections of human volunteers in reverberation
chambers and parameterising the result as the product of a body-area
quantity and a near-constant ratio. Bamba (2014) calls the ratio η.
Flintoft (2014) calls a related quantity ⟨Q^a⟩. Zhang (2017) calls his
ξ. Each identifies a different decomposition; each fits its parameters
empirically to FDTD or to volunteer data; none derives the ratio from
first principles, nor explains a persistent dip in the curve near
3 GHz. Independently of this work, Kodera (2024) fits the same kind
of constant T_tr to plane-wave whole-body SAR above 10 GHz from
parametric FDTD on anatomical phantoms. The community has been measuring
the same quantity in five notations and four formulations for a quarter
century. **What is that quantity in closed form?**


## The answer (one paragraph)

The direction-averaged whole-body absorbed power on a body in a
reverberant or richly-multipath field is exactly

  ⟨P_abs⟩ = S_inc · T̄(f) · A_ab / 4

where T̄(f) is the flux-weighted Fresnel transmission of the skin (one
numerical quadrature per frequency from the IT'IS dielectric tables) and
A_ab = ∫_Σ η(r) dA is the surface area of the body weighted pointwise
by an ambient-occlusion factor identical to Flintoft's γ_s. The classical
Cauchy projected-area formula (1841) is the special case of a convex
body where η ≡ 1 and T̄ ≡ T_0. The 3 GHz dip that Flintoft and Zhang
both observe is the Fabry-Pérot resonance in the subcutaneous fat layer
that Zhang himself derives in his planar-tissue-stack model; we promote
that planar prediction to a body-surface average and recover the
empirical dip. With this single identity, every plateau, every dip, and
every BSA-correlation reported in Bamba, Flintoft, and Zhang is a direct
evaluation. Validated against FDTD on the Thelonious anatomical phantom
to 1.2 % at 5.8 GHz, and against three independent volunteer campaigns
spanning 168 subjects, the formula reduces compliance, reverberation-
chamber dosimetry, and the whole population-level threshold table to
three precomputed scalars (T̄, A_ab, m).


## Section-by-section plan

### 1. Introduction (1.5 pages, 0 figures)

**Argument:** five independent measurement and modelling streams
(Bamba, Flintoft, Zhang, Kodera, Diao) reach the same limiting form of
direction-averaged absorbed power. None derives the limit from Maxwell's
equations. We do.

- Open with a single graph showing Bamba η, Flintoft ⟨Q^a⟩/γ_s, and
  Zhang ξ on one axis, all converging into a ~0.45–0.55 band above
  6 GHz. The reader sees the unification visually before any equation.
  *(This is a placeholder version of the headline waterfall figure;
  see §6 for the full waterfall.)*
- Three-sentence framing of what's missing: a closed form, a derivation,
  and a quantitative explanation of the dip near 3 GHz.
- Three-bullet contributions list:
  1. The closed-form identity ⟨P_abs⟩ = S_inc T̄ A_ab / 4 (exact for any
     body opaque at the wavelength).
  2. Identification of the ambient-occlusion ratio A_ab/A as Flintoft's
     γ_s and as the non-convexity correction in Zhang's ξ. Computation
     by GPU rendering.
  3. The Fabry-Pérot mechanism for the 3 GHz dip, made quantitative by
     promoting Zhang's planar-tissue-stack model to a body-surface
     average.
- One paragraph deferring local-map physics (Paper A) and coherent MIMO
  (Paper C) explicitly.

### 2. The geometric framework (1.5 pages, 1 figure)

**Argument:** the absorbed power per unit surface area on biological
tissue at mmWave reduces to a closed form; we summarise the result
(deferring derivation to Paper A) and turn directly to the integrated
quantity.

- One-equation summary: `S_ab(r) ≈ S_inc T_0 ReLU(n̂ · (-k̂))`. Cite
  Paper A for the derivation.
- Total absorbed power per direction: `P_abs(k̂) = S_inc T_0 A_perp(k̂)`.
- **Figure 2 (existing):** the η(r) map on the Thelonious phantom. Caption
  emphasises: "η(r) is computed by ambient occlusion. Inner armpits and
  inner thighs drop to η ≈ 0.5; the rest of the body is fully exposed.
  Area-weighted mean η = 0.87 (paper) / 0.865 (measured by AEGIS's own
  AO solver)."
  Source: `theory/figures/eta_3d_phantom.png`.
- Self-shadowing as occlusion: `O(r, k̂)` is binary visibility; η(r) is
  the cosine-weighted hemispheric integral. **The mathematical identity
  with ambient occlusion in computer graphics (Zhukov 1998) imports four
  decades of GPU-optimised algorithms into electromagnetic dosimetry.**
- Define A_ab = ∫_Σ η(r) dA. For convex bodies A_ab = A; for Thelonious
  A_ab/A = 0.865.

### 3. The generalised Cauchy formula (2 pages, 1 figure)

**Argument:** we generalise the 1841 formula to non-convex bodies and
recover an *exact* identity at any frequency by substituting the
flux-averaged transmission T̄ for T_0.

- Theorem 1 (one-paragraph proof via Fubini): for any body,
  ⟨P_abs⟩ = S_inc · T_0 · A_ab / 4. The proof reuses the Fubini argument
  of the convex case with the occlusion factor restricting the
  integration domain. The visibility integrates out into A_ab, the
  body's single non-convexity scalar.
- Convex-hull energy bound as a strict upper bracket:
  ⟨P_abs⟩ ≤ S_inc · A_CH / 4 (Cauchy applied to the hull).
- Inter-body multi-bounce reflections: body-averaged correction below
  1 % on Thelonious; recapture mechanism self-compensates (deep
  concavities recapture more, but they're already low η). Two-line
  treatment with a citation to the monograph for the radiosity series.
- **Theorem 2 (the exact identity):** define
  T̄(f) = 2 ∫₀¹ T_avg(μ, f) μ dμ. Then
  ⟨P_abs⟩ = S_inc · T̄(f) · A_ab / 4 is exact at any frequency where
  the body is opaque (~ 100 MHz upward). Proof: replace T_0 in the
  Cauchy step with the full angle-dependent T_avg(θ), apply Fubini
  again, and the cosine-weighted angle integral collapses to T̄. *No
  pseudo-Brewster approximation is invoked.*
- **Figure 3 (existing):** R(f) = T_0 / T̄ across 0.3–100 GHz, the
  pseudo-Brewster sweet spot at 40 GHz. Source:
  `theory/figures/R_of_f_landscape.pdf`. Caption: "Below 40 GHz the T_0
  approximation underestimates absorbed power (R < 1, conservative
  for compliance). Above 40 GHz it overestimates by at most 3.5 %.
  T̄ is exact at any frequency."
- Numerical table (existing in monograph): T_0, T̄, R for skin from
  0.3 to 100 GHz. Reproduce verbatim.

### 4. The Fabry-Pérot dip near 3 GHz (1.5 pages, 1 figure)

**Argument:** below 6 GHz the homogeneous half-space breaks down because
the wavelength approaches the subcutaneous-fat layer thickness. A
three-layer skin/fat/muscle stack with transfer-matrix Fresnel produces
a frequency-dependent T_lay(f) with a resonance dip; this is what
Flintoft and Zhang both observe. Quantitative match.

- Reproduce the Zhang planar-stack derivation (eq. 2.11 in his thesis)
  in our notation. Reference Zhang explicitly: *"Zhang derived this
  identity in 2017 for the convex limit. We extend it to non-convex
  bodies via A_ab and remark that he used T_lay where we use T̄, the
  flux-weighted analogue."*
- Show the resonance: at ~3.5 GHz destructive interference reduces
  absorption by ~27 %; at ~0.9 GHz the fat acts as a quarter-wave match
  and absorption rises by ~40 % (numbers from monograph
  `section_below6ghz.tex`).
- **Figure 4 (NEW):** overlay the transfer-matrix prediction T_lay(f)
  for skin/fat/muscle on Flintoft's ⟨Q^a⟩(f) (60 volunteers) and
  Zhang's ξ(f) (Fig. 4.11 envelope). Three curves on one panel, one
  framework prediction. **This is the second-strongest evidence in the
  paper.** Caption emphasises: "The dip Flintoft attributed to
  'reflections between layers of tissue' and the dip Zhang named
  'Fabry-Pérot resonance' are the same phenomenon, predicted by a
  three-layer transfer matrix with no fitted parameters."
- One paragraph honest about the breakdown of the local surface map:
  below 6 GHz, S_ab(r) loses pointwise meaning because the skin depth
  exceeds the surface layer; the integrated formula <P_abs> survives
  via T̄ (or T_lay).

### 5. Closed-form compliance (1.5 pages, 1 figure, 1 table)

**Argument:** the integrated identity collapses ICNIRP whole-body SAR
compliance to three precomputed scalars and reveals the population-
scaling explicitly.

- Whole-body SAR: SAR_wb = ⟨P_abs⟩ / m = S_inc T̄ A_ab D(k̂) / (4m).
- Hemisphere bound D ≤ 2; worst-case threshold:
  S_inc < 0.16 m / (T̄ A_ab). (The "0.16" is 0.08 W/kg × 2 from
  ICNIRP general-public limit and the directivity bound.)
- Anthropometric scaling via Du Bois A(m, h) = 0.007184 m^0.425 h^0.725.
  Express m/A as BMI^0.575 · h^0.425.
- **Table 1 (existing in monograph):** S_inc^max for infant / child /
  adolescent / adult / large adult at 28 GHz. Threshold varies by 2×
  across the population.
- **Figure 5 (NEW):** anthropometric-compliance landscape — contour
  plot of S_inc^max in W/m² with x-axis BMI and y-axis height,
  overlaid with representative population markers. Caption notes that
  smaller and lighter individuals have lower thresholds under
  worst-case directional exposure; a one-sentence framing that this is
  a quantitative scaling and the basic restriction (50× safety factor)
  remains the regulatory anchor.
- One short subsection on psSAR-from-S_ab via the energy-conservation
  shortcut from `theory/psSAR10g.tex`:
  ⟨SAR⟩_cube = (S_inc T_0 / (ρ_m L)) · (|k_x| + |k_y| + |k_z|).
  At 28 GHz under uniform S_ab = 20 W/m² (the ICNIRP local limit):
  psSAR ≈ 0.93 W/kg. Headroom for compliance.

### 6. The literature waterfall (3 pages, 1 figure, 2 tables)

**Argument:** with all our pieces in place, every direction-averaged
ACS / efficiency / coefficient reported in 25 years of dosimetry
measurements is a direct evaluation of one identity. Show this
graphically and quantitatively.

- Quick recap of each study's ratio definition (6 lines):
  Flintoft ⟨Q^a⟩ = 4⟨σ_a⟩ / (γ_s · BSA);
  Zhang ξ = ⟨σ_a⟩ / (BSA/4);
  Bamba η = empirical scalar from FDTD;
  Kodera T_tr = empirical from 1D slab.
  Map each onto our identity and show the ratio of measured to
  predicted converges within experimental scatter.
- **Figure 6 (NEW, the headline of the paper):** the literature
  waterfall. 5 panels (one per study) plus a unification panel. Each
  panel shows the published values (with error bars where available)
  and our prediction overlaid. The unification panel collapses all
  five onto one axis using each study's notation-conversion to T̄ ·
  (A_ab/A). One curve, one prediction, three measurement campaigns
  spanning 168 volunteers.
- **Table 2 (NEW, the headline table):** for each plateau / dip /
  scaling reported in the literature, list (i) the published value,
  (ii) our prediction, (iii) the discrepancy. Rows:
  - Flintoft 7-11 GHz ⟨Q^a⟩ = 0.40-0.42 / γ_s = 0.85 → 0.47-0.49 vs T_0 = 0.48 → 2 %
  - Bamba 1.5-6 GHz η = 0.50-0.56 vs T̄ = 0.47-0.50 → 6-12 %
  - Zhang 6-18 GHz ξ = 0.45-0.65 vs T̄ · A_ab/A = 0.43-0.49 → within scatter
  - Kodera 10-100 GHz T_tr to within 5 % of A_perp / W → recovered
  - Diao 28 GHz T = 0.52 vs T_0 = 0.536 → 3 %
  - Flintoft d_SF slope at 3 GHz: -0.0061 mm⁻¹ vs transfer-matrix
    prediction → quantitative match (ranges to be filled in)

### 7. FDTD validation on the Thelonious phantom (1 page, 1 figure)

**Argument:** the literature-comparison evidence above is a meta-test;
this section is a direct, single-laboratory ground-truth check on
anatomical-FDTD.

- Tier 0 result: 12 directions × 2 polarisations × 9 frequencies
  (450 MHz–5.8 GHz) of full-Sim4Life FDTD on Thelonious. Direction-
  averaged ⟨P_abs⟩^AEGIS / ⟨P_abs⟩^FDTD = 1.012 at 5.8 GHz, dropping
  to 0.39 at 700 MHz (where body-scale Mie/resonance dominates and
  the geometric-optics limit fails — predicted, not failure).
- **Figure 7 (existing):** kernels-vs-FDTD across 0.45–5.8 GHz. Source:
  `validation/fig_kernels_vs_fdtd.png`. Caption emphasises: at the
  upper end of the data range (5.8 GHz, where the geometric-optics
  asymptotic is expected to apply), the closed-form Cauchy prediction
  matches FDTD to 1.2 % using A_ab from AEGIS's own ambient-occlusion
  solver and T̄ from its Fresnel kernel. No fitted parameters.
- One-line carve-out of the Tier 1 7 GHz total-power ratio. Per the
  user, likely a Sim4Life setup bug (absorbed-vs-incident-power); the
  peak 4-cm² SAPD ratio at the same frequency is 1.027 (within 3 %)
  on the IEC/IEEE 63195 metric.
- One paragraph: AEGIS's predicted A_ab/A = 0.865 vs the paper's pre-
  measurement value 0.87 — internal consistency check on the AO solver.

### 8. Reverberation-chamber dosimetry, in three precomputed scalars (0.5 pages)

**Argument:** the formula replaces decades of FDTD calibration in the
small-animal exposure community.

- ⟨P_abs⟩ = S_total T̄ A_ab / 4 directly from the chamber's measured
  scalar S_total, the body's T̄ (one quadrature), and the body's A_ab
  (one ray-tracing pass). No direction sampling, no FDTD per
  configuration.
- Example: a mouse phantom (η ≈ 1 by convex morphology) at 2.45 GHz
  with S_total = 1 W/m². Three numbers: T̄ = 0.488, A_ab = 65 cm²,
  m = 25 g → ⟨SAR_wb⟩ = 0.317 W/kg. One line.

### 9. Conclusion (0.5 pages)

- Three quantitative claims in three sentences: identity, FDTD match
  at 5.8 GHz to 1.2 %, literature unification across 168 volunteers.
- Forward look: Paper A for the local map physics; Paper C for
  coherent MIMO. Reverberation-chamber community: stop calibrating.


## Headline numerical claims (the "things that have to be true")

| Claim | Numeric value | Evidence source |
|---|---|---|
| Direction-averaged Cauchy formula matches FDTD | 1.2 % discrepancy at 5.8 GHz on Thelonious | `validation/tier0_findings.md` |
| Ambient occlusion η measured by AEGIS solver | A_ab/A = 0.865 (predicted 0.87) | Same |
| Flintoft plateau, gamma_s-corrected | ⟨Q^a⟩ / γ_s = 0.47–0.49 vs T_0 = 0.48 | `papers/extracted/flintoft_summary.md` |
| Bamba plateau | η = 0.50–0.56 across 1.45–5.8 GHz vs T̄ | `papers/extracted/gosselin_summary.md` (Bamba) |
| Zhang plateau and 4 GHz dip | ξ = 0.45–0.65 above 6 GHz; named dip at ~4.4 GHz | `papers/extracted/zhang_summary.md` |
| Anthropometric range | S_inc^max varies by 2× from infant to large adult | monograph tab:anthropometric |
| Polarisation worst case on body | Δ ≤ 12 % on compliance threshold | monograph eq:Pabs-worst-pol |
| psSAR at 28 GHz under ICNIRP local limit | 0.93 W/kg | `theory/psSAR10g.tex` |


## Headline figures with caption sketches

1. **Figure 1 (intro teaser, NEW):** simplified waterfall — Bamba η,
   Flintoft ⟨Q^a⟩/γ_s, Zhang ξ on one axis vs frequency. Visual
   convergence into a ~0.45–0.55 band above 6 GHz. Caption: "Three
   independent measurement campaigns, three notations, one underlying
   quantity."

2. **Figure 2 (existing): η(r) on Thelonious.** From
   `theory/figures/eta_3d_phantom.png`. Caption emphasises area-weighted
   mean η = 0.865 = Flintoft's γ_s.

3. **Figure 3 (existing): R(f) landscape.** From
   `theory/figures/R_of_f_landscape.pdf`. Caption: "Below 40 GHz the
   T_0 approximation is conservative; above, overestimates by at most
   3.5 %. T̄ is exact at any frequency."

4. **Figure 4 (NEW): the 3 GHz dip overlay.** Transfer-matrix
   T_lay(f) for skin/fat/muscle vs Flintoft 60-volunteer scatter and
   Zhang ξ envelope. Caption: "Same physics, two notations, one
   prediction."

5. **Figure 5 (NEW): anthropometric-compliance landscape.** S_inc^max
   contour over (BMI, height) with population markers.

6. **Figure 6 (NEW, headline): the literature waterfall.** Five panels
   (Bamba / Flintoft / Zhang / Kodera / Diao) plus a unification panel.
   Caption: "Every direction-averaged ACS / efficiency / coefficient
   reported in 25 years of dosimetry measurements is one evaluation of
   ⟨P_abs⟩ = S_inc T̄ A_ab/4."

7. **Figure 7 (existing): Tier 0 FDTD comparison.** From
   `validation/fig_kernels_vs_fdtd.png`. Caption: "Cauchy + T̄
   (black stars, right panel) matches FDTD to 1.2 % at 5.8 GHz. No
   fitted parameters."


## Adversarial-positioning manifest

**"This is a survey, not a derivation."**
Counter: Theorem 1 (Cauchy generalisation via Fubini), Theorem 2 (exact
T̄ at any frequency), and the layered-tissue mechanism for the 3 GHz
dip are derivations, not surveys. The unification of three measurement
streams is the *result* of the derivation. Lead with the theorems in
the abstract.

**"Cauchy 1841 is in every textbook."**
Counter: the convex case is Cauchy. The non-convex generalisation via
ambient occlusion is not in any dosimetry paper or any integral-
geometry textbook in the form we use. The contribution is the
*identification*: A_ab = exposure-fraction integral = ambient-occlusion
integral = Flintoft's γ_s computed by the body mesh. This bridge has
not been made before.

**"Zhang already had your identity."**
Counter: Zhang derived the planar limit (his Eq. 2.11). We extend to
non-convex bodies and validate the extension against FDTD on
Thelonious. We also resolve the dip mechanism quantitatively across
two independent volunteer studies. Frame the contribution as: "Zhang
proved this for slabs. We complete the picture for human bodies."

**"Flintoft already named γ_s as the illuminated-area ratio."**
Counter: yes, in words. We provide the closed-form computation by
ambient occlusion, validate γ_s = A_ab/A = 0.865 on Thelonious vs
Flintoft's geometric estimate of 0.75–0.85, and show this single
substitution turns Flintoft's 60-volunteer plateau into a quantitative
match (within 2 %) with the Fresnel T_0.

**"Bamba's η = 0.5 was already known to be the diffuse-field
absorption efficiency."**
Counter: yes, empirically. We derive it from Fresnel theory (T̄ from
one quadrature) and connect to Zhang's planar limit and Flintoft's
plateau within a single closed form. Bamba's η was a fit; we predict
the same number with no fitted parameters.

**"You're claiming children are non-compliant under ICNIRP. Public
health implication."**
Counter: per the user, do not lead with this. It happens every day in
dosimetry. State the population scaling factually, do not editorialise.
Recommendation: factual table, factual contour plot, no alarm bell, no
policy recommendation.

**"You haven't shown the FDTD comparison above 5.8 GHz."**
Counter: Tier 1 at 7 GHz gives a peak 4-cm² SAPD ratio of 1.027 (within
the IEC/IEEE 63195 acceptance band). Total power at 7 GHz is currently
under-converged on the FDTD side (per discussion in
`validation/tier1_findings.md`); we report the peak metric, which is
the regulatory-relevant quantity, and defer total-power FDTD
validation above 6 GHz to follow-up.

**"Your A_ab is computed by your own ambient-occlusion solver. Is
that internally consistent?"**
Counter: A_ab measured by AEGIS = 0.865. Paper A's pre-measurement
prediction (from η-integral on the same mesh, monograph) = 0.87. Two
independent computations on the same mesh agree to 0.6 %. Add this as
a one-line internal-consistency check.


## Open decisions before writing

1. **Fetch Flintoft supplementary data** at
   `stacks.iop.org/PMB/59/3297/mmedia` and replot Fig. 5 with all 60
   per-subject curves overlaid with our prediction. Highest-leverage
   action; ~1 hour with an agent if the link still works.
2. **Render the literature waterfall figure (Fig. 6).** Plot 5 panels
   from the data we now have (Flintoft Tables 3 + 6, Zhang Table 4.4
   + Fig 4.11 envelope, Bamba's eta(f) regression, Kodera's reported
   ratios, Diao's 28 GHz number). Single concrete dataset. Roughly half
   a day with a sim agent.
3. **Promote or demote the children-compliance section** based on the
   user's directive (do not editorialise). My current spine: factual
   table only.
4. **Scope the Fabry-Pérot subsection** (§4): include the transfer-
   matrix derivation in main text or only the result with citation to
   monograph appendix? Lean towards: result + numerical match in main
   text; derivation in monograph appendix (cited).
5. **Confirm Bamba 2014 citation** with the user. The PDF was
   labelled "A formula for human average whole-body SAR" but the agent
   identified it as Bamba 2014 (PMB 59:7435). Re-tag.


## Source files (final)

| Source | Section used |
|---|---|
| `theory/monograph_v2.tex` | §sec:geometry, sec:cauchy, sec:Tbar, sec:compliance, sec:Rf-landscape, sec:diffuse-limit, sec:app-reverb, sec:traffic-light, tab:lit:predictions, sec:exact-bounds (worst pol) |
| `theory/section_below6ghz.tex` | §sec:layered (transfer-matrix model, the 3 GHz dip mechanism) |
| `theory/psSAR10g.tex` | §sec:cube and eq:SAR-energy (the energy-conservation shortcut) |
| `validation/tier0_findings.md` | The 1.2 % at 5.8 GHz result (Section 7) |
| `validation/fig_kernels_vs_fdtd.png` | Figure 7 |
| `validation/scripts/geometry.py` | A_ab solver implementation cite |
| `papers/extracted/flintoft_summary.md` + crops | Section 6, Figure 6 panel 1 |
| `papers/extracted/zhang_summary.md` + crops | Section 6, Figure 6 panel 2; Figure 4 overlay |
| `papers/extracted/gosselin_summary.md` (= Bamba) + crops | Section 6, Figure 6 panel 3 |


## Estimated writing path

Day 1: Fig. 6 (waterfall) + Fig. 4 (dip overlay) + Fig. 5 (compliance landscape).
Day 2: §1, §2, §3.
Day 3: §4, §5, §6.
Day 4: §7, §8, §9, abstract, polish.
Day 5: internal review + revisions.
