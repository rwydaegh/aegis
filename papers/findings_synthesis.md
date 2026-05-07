# Synthesis of findings — what we now know that changes the papers

Compiled from the three PDF-extraction agents, the validation/ md files,
and the AEGIS coherent-code inventory. Drives the revised paper plans.


## A. The literature is closer to our framework than the monograph implies

### Zhang (2017 York PhD thesis, 48 subjects, 1–18 GHz)

- **Zhang's Eq. 2.11 is literally our identity in the convex limit:**
  `xi_plane = sigma_a / S_silhouette = T(f)` where T is the multilayer
  Fresnel transmission. He uses this for planar tissue stacks; we
  generalise it to non-convex bodies via the exposure fraction.
- **Zhang names the Fabry-Perot fat-layer resonance explicitly.**
  His Fig. 2.7-2.8 derive the planar-model xi(f) for fat thicknesses
  2–18 mm with named "enhancement point" (peak ~110 % above homogeneous
  muscle near 1.4 GHz for 10 mm fat) and "reduction point" (dip 46 %
  below near 4.4 GHz). Zhang writes verbatim: *"the fat layer may act
  as a matching layer between skin and muscle."* Our use of this
  mechanism is not speculative; it is Zhang's own published model.
- **Plateau quantitatively pinned: xi(f) ~ 0.45–0.65 across 48 subjects
  from 6–18 GHz.**
- **What we can extract:** Table 4.4 (all 48 subjects' H/W/sex/age/SFT
  measurements), C1(f) and C2(f) regression coefficients, planar-model
  xi(f) curves, three highlighted subject traces. Per-subject Fig 4.11
  envelope is digitisable but per-subject identification requires York
  email.
- **PNGs at:** `papers/extracted/zhang/` (14 files).

### Flintoft 2014 (PMB 59:3297, 60 subjects, 1–12 GHz)

- **Flintoft's gamma_s is literally our ambient-occlusion ratio.**
  Verbatim from the paper (p. 3301): *"the proportion of total surface
  area of the body that is illuminated by the reverberant field."* He
  estimates 0.75–0.85 from Tomita 1999 surface-area data via geometric
  argument (sitting posture, arms ~7.5 % shadowed, legs ~17 %). Our
  contribution is the closed-form computation of A_ab/A from the body
  mesh via ambient occlusion algorithms.
- **Plateau predicted at <Q^a> = 0.41 ± 0.01 at 7/9/11 GHz.** True Q^a
  (dividing by gamma_s = 0.85) gives 0.47–0.49, matching our T_0 = 0.48
  to within 2 %.
- **3 GHz dip mechanism named:** *"reflections between the layers of
  tissues at these frequencies"* (p. 3308). The Q^a vs d_SF (mean
  subcutaneous fat thickness) slope is steepest at 3 GHz: beta =
  −0.0061 mm⁻¹, R² = 0.40 — strong evidence for the fat-layer mechanism.
- **N = 60 (36M/24F), mass 45.8–109.5 kg, BSA 1.43–2.36 m², d_SF 2.3–
  20.4 mm.** Subject group somewhat underweight vs UK reference.
- **Supplementary data exists at `stacks.iop.org/PMB/59/3297/mmedia`.**
  Worth fetching for raw per-subject CSV before drafting.
- **PNGs at:** `papers/extracted/flintoft/` (10 files including 4 tables).

### Bamba 2014 (PMB 59:7435–7456, NOT "Gosselin" as I wrote earlier)

- **The PDF labelled "A formula for human average whole-body SAR" is
  Bamba 2014, not Gosselin 2011.** Re-tag throughout.
- Their formula: `SAR = 0.21 * m^(-0.3534) * eta(f) * k(phi,psi) * I`
  with `eta(f) = -1.78e-5 * f + 0.5859` (f in MHz). eta = 0.50–0.56
  across 1.45–5.8 GHz.
- **No |t|² / Fresnel coefficient anywhere.** eta is a single empirical
  scalar fit from full-body FDTD on ellipsoids — bundles polarisation,
  Fresnel, creeping waves, curvature into one number per frequency.
- Validation: 4 Virtual Family phantoms (Thelonious, Billie, Ella, Duke)
  at 3 GHz with plane waves. LOS errors 12–29 %; DMC −39 % to +11 %;
  background FDTD uncertainty itself ~21 %.
- **Their `eta * BSA_T,pr` ≡ our `T_bar * A_ab/4`** in different notation
  for the diffuse-isotropic case. They extract empirically; we derive
  from Fresnel + Cauchy. Bamba uses a 2D-azimuth integration giving
  empirical `BSA_T,pr / BSA = 2.20`; we use Cauchy's theorem analytically.
- **PNGs at:** `papers/extracted/gosselin/` (6 files; folder mis-labelled,
  rename to `bamba/` in the next pass).


## B. The validation evidence is much stronger than I credited

### Tier 0 (sub-6 GHz, 12 dirs × 2 pols × 9 freqs, no new FDTD runs)

- **Cauchy direction-averaged formula matches FDTD to 1.2 % at 5.8 GHz**
  on the Thelonious anatomical phantom. <P_abs>^AEGIS / <P_abs>^FDTD =
  1.012, with A_ab from AEGIS's own ambient occlusion (eta = 0.865 vs
  paper's 0.87) and T_bar from AEGIS's own Fresnel kernel.
- **Polarisation correction averages to zero across (theta, phi) pairs.**
  L_all kernel (with polarisation, curvature, diffraction all on) gives
  the same direction-averaged ratio as L6 (curvature+diff only). Paper
  §6.1 prediction confirmed on real data.
- **Below 5 GHz the Cauchy ratio drops monotonically to 0.39 at 700 MHz.**
  Body-scale Mie/resonance regime; not a failure but a known limit.
- **Lateral D_B at 5.8 GHz is 19.5 %**, slightly exceeding the paper's
  16 % universal bound (which was at 28 GHz). Either residual frequency
  dependence through |n_tilde|, or skin-mesh perforation in the FDTD
  voxel model. Stays under the cylinder bound (27.9 %).
- **Files:** `validation/tier0_findings.md`, `validation/fig_kernels_vs_fdtd.png`.

### Tier 1 (7 GHz, 3 directions completed, full Thelonious)

- **Peak 4-cm² SAPD ratio = 1.027** (within 3 %) — IEC/IEEE 63195
  regulatory metric. AEGIS sweet spot for peaks is real.
- Total P_abs ratio = 0.479 at 7 GHz appears to underpredict by 2.1×.
  Per the user, likely a Sim4Life setup bug (absorbed-vs-incident-power
  conflation) rather than a genuine framework breakdown. Treat with
  caution; do not headline.
- **Files:** `validation/tier1_findings.md`, `validation/tier1_kernels_vs_fdtd.png`.

### What this validation gives us

For Paper B (compliance / Cauchy), the Tier 0 result IS the validation
section. 1.2 % at 5.8 GHz on a real phantom is the cleanest single-number
test we will get. Pair with the literature waterfall and Paper B's
results section is essentially complete.

For Paper A (geometric law), the peak 4-cm² SAPD = 1.027 at 7 GHz is the
local-map validation. Combined with the existing Mie-sphere validation,
we have two independent ground truths.

For Paper C (coherent MIMO), no FDTD coherent multi-source comparison
exists. Validation of Paper C must rest on (i) the bounded approximation
errors (Approx 1 ≤ 4 %, Approx 2 ≤ 0.5 %, both numerical), (ii) the
single-wave limit reducing to Paper A's validated case, and (iii)
internal consistency on simulated scenarios.


## C. The AEGIS coherent code is complete and runnable

Modules in `src/aegis/coherent/`:

- `field_channel.py` — assembles G(r) = Psi Phi(r) J
- `fresnel_operator.py` — F_n per path
- `body_channel.py` — G_tilde = exposure channel matrix
- `exposure_operator.py` — Q = ∫ G_tilde^H G_tilde dA assembly
- `ecbf.py` — closed-form ECBF solver via S-procedure
- `multibody_ecbf.py` — MU-MIMO version with per-person Q^(u)

Kernels: `level7_coherent.py` and `level8_ecbf.py` are the orchestration
points.

**Implication for Paper C:** every simulation in §10 (ECBF Pareto, ρ
landscape, MRT vs ECBF hotspot, M·P spectrum) is computable today with
existing code. No new physics development needed. The bottleneck is
choosing scenarios and rendering figures, not infrastructure.

**Suggested first scenario for Paper C:**
- 8×8 (M=64) URA at 3 m from Thelonious, 28 GHz
- Single UE at 5 m behind the phantom (one panel) and 5 m in front
  (second panel) — gives the hotspot/non-hotspot contrast
- ~30–60 multipath paths via DiffeRT bridge (already in repo)
- Run ECBF for lambda in [0, infty] sweep (~40 points), MRT, GEP optimum
- Single-day compute on GPU; can be parallelised


## D. Revised positioning — three sentences each

**Paper A:** the geometric absorption law `S_ab = S_inc T_0 ReLU(mu)`
follows from a pseudo-Brewster compensation that makes the unpolarised
Fresnel transmission near-constant for biological tissue at mmWave; we
derive this from Maxwell's equations, validate against Mie spheres and
against full-Fresnel integration on the Thelonious phantom (peak
4-cm² SAPD ratio = 1.027 at 7 GHz vs FDTD), and cast the multi-source
form as a ReLU network for differentiable design. Position vs Kodera
2024 / Diao 2024: they fit T_tr numerically; we derive it analytically
and explain its angle-near-constancy from optics first principles.

**Paper B:** the direction-averaged whole-body absorbed power obeys
`<P_abs> = S_inc T_bar A_ab/4`, exact at any frequency above ~100 MHz,
where A_ab is the body's surface area weighted by ambient occlusion
(identical in name and in fact to Flintoft's gamma_s) and T_bar is the
flux-averaged Fresnel transmission (which equals Bamba's empirical eta
and Zhang's planar-limit T); on the Thelonious phantom this matches FDTD
to 1.2 % at 5.8 GHz. Position vs the empirical literature: Zhang's Eq.
2.11 *is* our identity in the convex limit; Flintoft *defines* gamma_s
as ambient occlusion in words and we provide it computationally; the
3 GHz dip both Zhang and Flintoft observe is the Fabry-Pérot resonance
they themselves attribute to fat-layer reflections. We unify three
parallel empirical streams under one closed form.

**Paper C:** for an M-element coherent array radiating with precoder x
into an N-path environment containing a body, the whole-body absorbed
power equals `x^H Q x` where Q is a Hermitian PSD matrix derived in
closed form from the propagation paths and Fresnel coefficients with
no FDTD calibration step; the path-space factorisation Q = J^T M J
reduces the worst-case eigenvalue to an N-dimensional problem and
admits broadband, near-field, stochastic, low-rank, and multi-user
extensions as small perturbations. The exposure-constrained beamforming
problem retains the closed-form solution structure of Hochwald 2014 /
Ying 2015 but with our analytical Q replacing their FDTD-calibrated
SAR matrix.


## E. Key decisions remaining

1. Paper B writes itself once Flintoft and Zhang per-subject data are in
   hand. The Flintoft supplement at `stacks.iop.org/PMB/59/3297/mmedia`
   should be fetched. Zhang Table 4.4 should be transcribed from the
   thesis PNGs. *Action: agent for both, ~2 hours.*

2. Paper A's 28 GHz validation in the monograph is on full-Fresnel vs
   simplified — not vs FDTD. The 7 GHz Tier 1 peak SAPD = 1.027 is the
   FDTD-validation hook. *Action: confirm peak SAPD validation is
   defensible at the user's claimed sim4life-bug carve-out for total
   P_abs; if so, headline it.*

3. Paper C simulations: pick one canonical scenario (8×8 URA, 28 GHz,
   Thelonious, two UE positions). Run ECBF Pareto, hotspot pair, ρ
   landscape, M·P spectrum. *Action: dispatch a sim agent with the
   canonical scenario spec.*

4. Order of writing: Paper B (strongest validation + literature),
   Paper A (foundational and short), Paper C (heaviest, needs sim
   results). *Recommendation: write A and B in parallel; start C's
   simulations during the writing.*
