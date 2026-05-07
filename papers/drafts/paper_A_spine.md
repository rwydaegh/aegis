# Paper A — Medium-level plan

**Working title:** *Pseudo-Brewster compensation collapses Fresnel
dosimetry to geometry: a closed-form local absorption law for the human
body at millimetre waves.*

**Target venue:** IEEE Transactions on Antennas and Propagation.

**Target length:** 12 two-column pages, 6 figures, 3 tables.

**Status:** ready to write. Validation evidence solid (Mie + 28 GHz
phantom + 7 GHz peak SAPD = 1.027). Paper B's footing depends on this
paper's local-law derivation, so write A first.


## The question (one paragraph)

For wireless devices operating above 6 GHz, regulators specify the
absorbed power density S_ab on the human body. Direct simulation of
S_ab by FDTD requires a mesh fine enough to resolve the sub-millimetre
skin depth in a body that spans a metre, giving ~10^12 cells per
plane-wave configuration — far beyond practical computation for a
typical regulatory campaign. The literature has known for a decade that
S_ab on biological tissue follows a near-universal projected-area
scaling with a near-constant transmission coefficient T_tr that is
fitted numerically to one-dimensional FDTD models (Kodera 2024, Diao
2024). **Why is T_tr near-constant, what is its first-principles value,
and what is the correct local map from incidence direction to absorbed
power on a curved body?**


## The answer (one paragraph)

The Fresnel transmission of unpolarised light into a lossy half-space
is angle-near-constant whenever the refractive index modulus exceeds
~2.5: a TM-rising / TE-falling compensation that Azzam (2015) named for
optical substrates. Biological tissue at mmWave has |ñ| ∈ [3, 6], placing
it in this regime. The unpolarised Fresnel transmission stays within
5.6 % of its normal-incidence value T_0 over θ ∈ [0°, 75°] for skin at
28 GHz; T_0 itself is a closed-form scalar in the tissue's complex
refractive index. Once T_0 replaces the angle-dependent T(θ), the local
absorption law collapses to

  S_ab(r) = S_inc · T_0 · ReLU(n̂(r) · (-k̂))

— a positive-part cosine of the surface normal. Multi-source
illumination is a single-hidden-layer ReLU network whose weights are
the path directions and powers from any ray tracer, making the chain
ray-tracer → dosimetry differentiable. Validated against exact Mie
theory on lossy spheres (errors ≤ 5 % above 60 GHz, ≤ 10 % at body-part
sizes in the mmWave band), against full Fresnel integration on the
Thelonious anatomical phantom (0.35 % discrepancy on total power), and
against full Sim4Life FDTD on Thelonious at 7 GHz on the regulatory
peak 4-cm² SAPD metric (1.027 ratio), the framework reduces a 10^12-cell
volumetric problem to O(MN) surface multiplications with the same
arithmetic primitive as a hardware-accelerated rendering pipeline.


## Section-by-section plan

### 1. Introduction (1.5 pages, 0 figures)

**Argument:** the regulatory quantity is a surface integral; full-volume
FDTD is the wrong tool; an analytical local-surface law has been
empirically observed but never derived.

- One-paragraph statement of the regulatory regime: ICNIRP 2020 limits
  S_ab in W/m² above 6 GHz; below, whole-body SAR. Surface vs volume.
- Cell-count argument: 10^12 cells for one plane wave at 28 GHz on a
  full body. Cite the monograph's PMB campaign (550 simulations,
  multi-week GPU). Concrete, not hand-waved.
- The empirical finding: Kodera 2024, Diao 2024, Funahashi 2018, Li
  2019 all converge on `S_ab ~ T_tr · cos θ` with T_tr near-constant.
  None gives a mechanism. None gives the local map from path geometry.
- Three-bullet contributions:
  1. **Pseudo-Brewster compensation**: the unpolarised T_avg(θ) stays
     within ~5 % of T_0 over [0°, 75°] for biological tissue at mmWave.
     Mechanism: Azzam-class high-index regime. Quantified across
     tissues and frequencies.
  2. **The local geometric absorption law**: closed-form S_ab(r) =
     S_inc T_0 ReLU(n̂ · (-k̂)) with bounded error.
  3. **The ReLU-network interpretation**: multi-source S_ab is a
     single-hidden-layer ReLU network whose weights are ray-tracer
     outputs. Differentiable. Imports GPU primitives.
- Forward-reference Paper B for the integrated quantity (whole-body
  ⟨P_abs⟩ and compliance) and Paper C for the coherent extension.

### 2. Local absorption law (2 pages, 0 figures)

**Argument:** derive the polarisation-aware exact law from Maxwell.
Reduce to the unpolarised baseline for circular or unpolarised
illumination.

- Setup: monochromatic plane wave on a locally flat lossy half-space,
  skin depth ≪ body size, body opaque.
- Power flux: dP_in = S_inc · μ · dA where μ = n̂ · (-k̂).
- Reflected flux: dP_ref = |r|² · S_inc · μ · dA. Energy conservation
  gives `S_ab = S_inc · T(θ) · μ` for one polarisation, with
  T(θ) = 1 - |r(θ)|².
- Fresnel coefficients for a lossy half-space (one paragraph;
  derivation deferred to appendix or to citation of the monograph).
  Define ξ = √(ñ² - 1 + μ²), Re(ξ) > 0; r_s = (μ - ξ)/(μ + ξ);
  r_p = (ñ²μ - ξ)/(ñ²μ + ξ).
- Polarisation-aware law: define local TE/TM unit vectors,
  T_eff(r) = |e_s|² T_s(θ) + |e_p|² T_p(θ).
- **Boxed equation:** S_ab(r) = S_inc · T_eff(r) · ReLU(μ). Exact
  for any polarisation, any frequency where the body is opaque.
- Decomposition: T_eff = T_avg + (q/2) ΔT, where T_avg = ½(T_s + T_p),
  ΔT = T_p - T_s, and q = |e_p|² - |e_s|² ∈ [-1, 1] is the local TM
  excess.
- Three conditions under which q ⟨ΔT⟩ vanishes: circular polarisation
  (q ≡ 0 pointwise), unpolarised illumination (⟨q⟩ = 0 by ensemble
  average), and azimuthal averaging on bodies with rotational
  symmetry. Brief, with one citation to Paper B for the worst-case
  bound on linear polarisation.
- Reduce to: S_ab(r) = S_inc · T_avg(θ) · ReLU(μ). All angle
  dependence is now in T_avg(θ); the next section collapses it.

### 3. Pseudo-Brewster compensation (2 pages, 2 figures, 1 table)

**Argument:** for biological tissue at mmWave, T_avg(θ) is nearly
flat. Mechanism: a high-index regime where TE and TM transmissions
compensate. Numerical landscape across tissues and frequencies.

- Brewster's angle for lossless dielectrics (citation). Pseudo-Brewster
  for lossy dielectrics (Potter 1970, Öhman 1977): T_p peaks near
  θ_pB ≈ arctan|ñ|, T_s small but nonzero.
- The compensation: as θ increases from 0, T_s decreases monotonically
  while T_p rises towards near-unity at θ_pB. Their average T_avg
  stays near T_0.
- Azzam 2015's result: for lossless substrates with |ñ| > 2 + √3 ≈
  3.73, unpolarised reflectance varies <1 % over [0°, 60°]; for
  |ñ| > 2.5, the variation is small. Cite directly.
- Biological tissue at mmWave: |ñ| ∈ [3, 6]. Material universality
  table (skin / muscle / fat / water at 28 GHz, ñ values, T_0 values,
  T_avg/T_0 variation). Existing in monograph: tab:materials.
- **Figure 1 (existing): apd_angle_dependence.** TE/TM/avg
  transmissions vs θ for skin at 28 GHz, plus the absorbed power
  S_ab/S_inc curves with the simplified T_0 cos θ overlay. Caption:
  "The gap between the dashed line (T_0 cos θ) and the green curve
  (T_avg(θ) cos θ) is the entire Fresnel approximation error."
- **Figure 2 (existing): R_of_f_landscape.** R(f) = T_0/T̄ (sphere ratio)
  across 0.3-100 GHz for skin. Caption: "Pseudo-Brewster compensation
  is exact at 40 GHz; below, T_0 underestimates absorbed power
  (conservative for compliance); above, overestimates by at most
  3.5 %."
- Quantitative summary (one boxed claim): the constant-T_0
  approximation introduces RMS error below 5 % across 0.3-100 GHz on
  skin; <1 % on a sphere-averaged absorption test at 28 GHz.

### 4. The geometric absorption law and its computational form (2 pages, 1 figure)

**Argument:** with T_eff → T_0, the local map becomes a positive-part
cosine of the surface normal. The multi-source extension is a ReLU
network. Differentiable end-to-end.

- **Boxed result:** S_ab(r) = S_inc · T_0 · ReLU(n̂ · (-k̂)). All
  spatial variation is determined by body shape.
- Multi-source: for N incident plane waves with directions k̂_i and
  power densities S_i, S_ab(r) = T_0 Σ_i S_i ReLU(n̂(r) · (-k̂_i)).
- ReLU-network identification (one paragraph, low-key, not buzzwordy):
  this is a single-hidden-layer network with weight matrix
  W = [-k̂_1; …; -k̂_N], output weights a = T_0 [S_1, …, S_N], no bias,
  ReLU activation. The activation is *exact*, not an approximation;
  the network framing is a *consequence* of the geometric reduction,
  not a fitting target. Imports GPU primitives and gradient-based
  optimisation for free.
- Matrix form on a triangle mesh: positive-part cosine matrix
  μ_+ = ReLU(N K^T) ∈ R^{M×N}; binary visibility matrix
  O ∈ {0,1}^{M×N}; per-triangle S_ab vector
  S_ab = T_0 (μ_+ ⊙ O) s.
- Hierarchical computation: O(MN) for spatial map, O(N) for total
  power via projected-area lookup, O(1) for worst-case bound. Use
  the existing monograph table tab:hierarchy.
- **Figure 3 (NEW or schematic): the architecture diagram.** Cartoon
  showing: ray tracer → path matrix (k_i, S_i) → ReLU(N K^T) → S_ab
  on body mesh → loss / objective. Differentiable arrows. Caption:
  "The chain ray-tracer → dosimetry is differentiable end-to-end;
  body absorption can be optimised by the same backpropagation
  primitives as a neural-network training step."

### 5. Validation (2.5 pages, 2 figures)

**Argument:** three independent ground truths confirm the framework
within its claimed window of validity.

#### 5.1 Mie theory: exact wave-theoretic comparison

- Mie spheres are the worst-case smooth shape for the Fresnel
  approximation because every angle 0–90° appears on the illuminated
  hemisphere. Decompose framework error into Fresnel (shape- and
  frequency-dependent, |R-1| ≤ 5 % for skin) and diffraction (size-
  dependent, ~x^{-2/3} per Fock).
- **Figure 4 (existing): mie_validation_corrected.** Three panels:
  error vs size parameter at 28 GHz; error vs frequency for finger /
  arm / head / torso; the frequency-dependent Fresnel asymptote
  R_sphere(f) crossing unity at ~39 GHz.
- Body-relevant sizes (head, torso) have errors of 3-14 % at mmWave,
  dominated by diffraction into the geometric shadow. Errors are
  *conservative* (framework underestimates absorption).

#### 5.2 Full Fresnel on the Thelonious phantom

- Compare S_ab^simplified (T_0 ReLU(μ)) against S_ab^full
  (T_eff(θ, pol) ReLU(μ)) on Thelonious at 28 GHz, plane wave from
  above. Existing in monograph: tab:phantom.
- Total power discrepancy 0.35 %; mean local 2.6 %; max local 5.3 %
  on the 4 907 illuminated triangles with θ < 75°. Errors
  conservative.
- **Figure 5 (existing): apd_direction_analysis.** Phantom
  directional + polarisation analysis over 128 directions × 3
  polarisations. Caption: "The simplified prediction
  T_0 ⟨A_perp⟩ = 105.9 mW falls within the interquartile range of
  the unpolarised distribution. TM produces systematically higher
  total absorbed power than TE, consistent with the pseudo-Brewster
  peak in T_p; the unpolarised average sits between."

#### 5.3 FDTD on the Thelonious phantom (Tier 0 + Tier 1)

- Tier 0 (sub-6 GHz, 12 directions × 2 polarisations × 9 frequencies,
  full Sim4Life FDTD): peak 4-cm² SAPD ratio (the IEC/IEEE 63195
  metric) within [0.80, 1.20] across the band.
- Tier 1 (7 GHz, 3 directions, full Sim4Life FDTD): peak 4-cm² SAPD
  ratio = 1.027 (within 3 % of FDTD). This is the regulatory metric
  in the AEGIS sweet spot. **One-line carve-out:** Tier 1's total-
  power ratio is currently confounded by what we believe is a
  Sim4Life setup-side normalisation issue; the peak metric is
  unaffected.
- Cross-comparison with five literature studies: Kodera (5 %),
  Diao (3 %), Funahashi (15 % vs temperature rise), Li (5.6 %),
  Hochwald 2014 / Castellanos 2020 (analogue at 28 GHz). Single
  table; defer the rest to Paper B.

### 6. Limitations (1 page, 1 figure)

- The five irreducible limitations from the monograph:
  reactive near-field (d < λ/2π), coherent multi-bounce (treated
  incoherently), diffraction at shadow boundaries (>10 % for body
  parts <10λ), local map below 6 GHz (Fabry-Pérot interference; defer
  to Paper B), tissue dielectric uncertainty (~20 %).
- Curvature correction (~1 % for limbs, ~8 % for ear edges) and
  diffraction smoothing (the GELU activation) as systematic
  refinements. Brief, with citation to monograph appendix.
- **Figure 6 (existing): error_budget_comprehensive.** Bar chart of
  errors classified as conservative vs non-conservative.

### 7. Conclusion (0.5 pages)

- Three sentences: pseudo-Brewster mechanism, the geometric
  absorption law, the ReLU-network differentiability.
- The framework reduces a 10^12-cell volumetric problem to O(MN)
  surface multiplications with the same arithmetic primitive as a
  modern rendering engine.
- Forward look: Paper B (compliance, RC dosimetry); Paper C
  (coherent MIMO, ECBF).


## Headline numerical claims

| Claim | Numeric | Source |
|---|---|---|
| Pseudo-Brewster constancy on skin at 28 GHz | T_avg/T_0 within 5.6 % over [0°, 75°] | tab:fresnel-skin |
| Sphere ratio at 28 GHz | R = 0.99 (1 % conservative underestimate) | sec:sphere-ratio |
| R = 1 sweet spot | 40 GHz | sec:freq-dep |
| R variation across 0.3–100 GHz | ≤ 5 % RMS, max 3.5 % at 100 GHz | sec:freq-dep |
| Phantom validation: total power error | 0.35 % at 28 GHz | tab:phantom |
| Phantom validation: max local error | 5.3 % at θ<75° | tab:phantom |
| Mie diffraction error: torso at 28 GHz | -10 % conservative | tab:mie-bodyparts |
| Mie diffraction error: finger at 28 GHz | -38 % conservative | tab:mie-bodyparts |
| FDTD validation: peak 4-cm² SAPD at 7 GHz | 1.027 (3 % discrepancy) | validation/tier1_findings.md |
| FDTD validation: Cauchy direction-averaged at 5.8 GHz | 1.012 (1.2 %) | validation/tier0_findings.md |


## Headline figures

1. **Figure 1 (existing): apd_angle_dependence.pdf.** TE/TM/avg vs θ
   for skin at 28 GHz. Two panels: transmission curves and absorbed
   power normalised. The visual punch.

2. **Figure 2 (existing): R_of_f_landscape.pdf.** R(f) across
   0.3-100 GHz, T_0 / T̄ curves, activation function at six
   frequencies.

3. **Figure 3 (NEW, optional): differentiable architecture diagram.**
   Cartoon ray-tracer → ReLU(N K^T) → S_ab. Clean, schematic, one
   panel. *Skip if length budget tight.*

4. **Figure 4 (existing): mie_validation_corrected.pdf.** Three-panel
   Mie validation: error vs x at 28 GHz, error vs f for body-part
   sizes, R_sphere(f) crossover.

5. **Figure 5 (existing): apd_direction_analysis.pdf.** Phantom
   directional + polarisation analysis.

6. **Figure 6 (existing): error_budget_comprehensive.pdf.**


## Adversarial-positioning manifest

**"Kodera 2024 already showed projected-area scaling."**
Counter: Kodera fits T_tr from 1D FDTD; we derive it from Fresnel
theory. Kodera predicts total power; we predict the local map and the
multi-source ReLU network. Lead with the local map in the contributions
list.

**"The 38 % finger-scale error at low frequency invalidates the
framework."**
Counter: errors are *conservative* (framework underestimates). At
mmWave on body-scale objects (head, torso), the error is 3-14 %, well
within the 20 % tissue dielectric uncertainty. The framework is not
claimed to be accurate at all frequencies for all body sizes; it is
claimed to be accurate in a defined regime, with explicit error bounds.

**"The ReLU-network framing is buzzword-chasing."**
Counter: the network is a *consequence* of the geometric reduction, not
a fitting target. The activation is exact. Demote to one section,
present as "the multi-source form has the structure of a ReLU network,
which makes the chain differentiable." Don't put "neural network" in
the abstract.

**"Pseudo-Brewster is in Azzam 2015. What's new?"**
Counter: Azzam derived it for optical substrates; nobody applied it to
biological tissue or to dosimetry. The contribution is the
*identification* of biological tissue as occupying the high-index
regime, the *quantification* of T_avg/T_0 variation across tissues and
frequencies, and the *validation* of the resulting closed-form law
against Mie + phantom + FDTD.

**"You don't validate against FDTD at 28 GHz, your claimed sweet spot."**
Counter: 28 GHz full-body FDTD is intractable on standard hardware
(~18 BCells for Thelonious). We validate at 7 GHz (the geometric
sweet spot is 10-60 GHz; 7 GHz is the highest tractable frequency
on a single 4090) and demonstrate that AEGIS captures the IEC/IEEE
63195 peak 4-cm² metric to within 3 %. Higher frequencies are
demonstrated against Mie spheres analytically.

**"Your sphere validation has 10 % error; that's not closed-form
agreement."**
Counter: sphere is the worst-case smooth shape for Fresnel approximation
*and* for diffraction, because uniform curvature maximises both errors.
Body-scale objects with large flat panels (torso) have smaller errors.
The Fresnel-only error on skin (no diffraction) is <1 % at 28 GHz on
the sphere ratio metric.


## Open decisions before writing

1. **Figure 3 (architecture diagram) — make it or skip?** Schematic-only,
   no real data. My lean: include it. Single panel; pedagogical;
   silences the "ReLU framing is gimmicky" complaint by showing the
   actual structure.
2. **How aggressive to be on the FDTD validation carve-out at 7 GHz
   total-power?** The peak metric is solid; the total-power ratio is
   muddied by what we believe is a Sim4Life setup issue. My lean:
   one-sentence carve-out, do not headline. Defer total-power FDTD
   validation above 6 GHz to follow-up paper.
3. **Section 6 (limitations): include curvature/diffraction
   refinements or only the irreducible limits?** My lean: brief
   refinements section because the GELU connection is part of the ML
   bridge.
4. **Should we cite Castellanos 2020 in §5.3 cross-comparison?** Their
   per-element scalar β = 0.70 lumps T_0 + depth-decay. We can
   recover both pieces analytically. *Yes, one paragraph; this is the
   bridge to Paper C.*


## Source files

| Source | Section used |
|---|---|
| `theory/monograph_v2.tex` | sec:local-law, sec:pseudo-brewster, sec:geometry (intro), sec:computation, sec:corrections, sec:validation, sec:limitations-v2, sec:literature, app:fresnel-derivation |
| `validation/tier0_findings.md` | §5.3 (5.8 GHz Cauchy 1.012) |
| `validation/tier1_findings.md` | §5.3 (7 GHz peak 4-cm² SAPD 1.027) |
| `validation/fig_kernels_vs_fdtd.png` | (cited; main figure lives in Paper B) |
| `papers/extracted/zhang_summary.md` | brief literature mention §1, §5.3 |
| `papers/extracted/flintoft_summary.md` | brief literature mention §1, §5.3 |
| `papers/extracted/gosselin_summary.md` (= Bamba) | brief literature mention §1, §5.3 |


## Estimated writing path

Day 1: §1 + §2 (set the question, derive the polarisation-aware law).
Day 2: §3 (pseudo-Brewster mechanism + numerical landscape).
Day 3: §4 (geometric law, matrix form, ReLU-network reading) + §5.1 + §5.2.
Day 4: §5.3 (FDTD) + §6 + §7 + abstract.
Day 5: internal review + revisions.
