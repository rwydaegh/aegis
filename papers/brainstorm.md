# Three IEEE papers from the geometric-dosimetry monograph

This brainstorm proposes three standalone, complementary IEEE papers that
together cover the substance of `theory/monograph_v2.tex` and its four
companion notes (`system_formalism.tex`, `psSAR10g.tex`, `q_complement.tex`,
`section_below6ghz.tex`). The papers are designed to be read independently
and to overlap minimally on novelty (they may share preliminaries and
notation). Sizes are quoted in single-column IEEE pages for TAP/TWC.

The user's brief: high-impact TAP/TWC papers. Don't sell the codebase. The
monograph is the long-form record (arxiv); the papers must each derive
their results without assuming the monograph is in front of the reader. The
backflip posture-sensitivity figure is suspected buggy and is not quoted in
any of the three papers.


## What the framework actually contains, ranked by impact

A reader encountering this material for the first time meets four ideas in
sequence. Each could anchor a paper.

1. **The pseudo-Brewster compensation.** For biological tissue
   (`|n_tilde|` in 3-6 at mmWave), TE transmission falls and TM
   transmission rises with angle, and their unpolarised average stays
   within 5.6% of T_0 over [0, 75°]. This collapses the material factor
   to a single scalar, which is what makes everything that follows
   tractable. It is the closest the framework has to a *new physical
   mechanism*.

2. **The geometric absorption law.** Once T_0 is the only material
   parameter, the absorbed power density is `S_inc * T_0 * ReLU(n_hat .
   (-k_hat))`, a function of body geometry alone. Total power factors
   through the projected area; direction-averaged power satisfies a
   generalised Cauchy formula with the exposure fraction (ambient
   occlusion in graphics) absorbing all self-shadowing into one scalar
   `A_ab`. For multiple sources the formula is a single-hidden-layer
   ReLU network whose weights are ray-tracer outputs. This is the
   *connection* result: dosimetry inherits four decades of integral
   geometry, GPU rendering, and differentiable ML.

3. **The exposure operator Q.** For coherent MIMO, two well-bounded
   approximations (TM-direction substitution, universal depth coupling)
   collapse the coherent depth integral to a squared norm
   `||G_tilde(r) x||^2`. Integrating over the body yields a Hermitian
   PSD matrix Q whose eigendecomposition encodes the body's complete
   absorption response to any precoder. ECBF reduces to a closed-form
   `(lambda Q + nu I)^{-1} h*` precoder; MU-MIMO extends via per-person
   Q^(u). This is the *system theorem*: the same path data that yields
   the UE channel h yields a closed-form Q.

4. **The path-space factorisation.** `Q = J^T M J` where J is the
   element-to-path dispatch matrix (combinatorial), M is the N x N
   path-exposure Gram (geometric/material), and the worst-case
   eigenvalue lifts via push-through to an N-space problem. This is the
   *algebraic* result. It makes broadband, near-field, stochastic,
   low-rank, and multi-user extensions all near-trivial perturbations
   of one matrix.

The literature that already touched these ideas (Kodera, Diao, Funahashi,
Li, Samaras, Bamba, Flintoft, Zhang, Hochwald, Ying, Castellanos, Zhou,
Hallbjorner, Azzam) provides empirical or partial analytical evidence for
fragments of (1)-(2). None unify the picture; none derive Q in closed form
((3)-(4) are entirely new).


## Three proposed papers

### Paper A (TAP) - *Pseudo-Brewster compensation and the geometric absorption law for human tissue at millimetre waves*

The "physics paper". Targets TAP's dosimetry/propagation community.

**Single-line claim.** Biological tissue at mmWave occupies the
high-refractive-index regime where unpolarised Fresnel transmission is
nearly angle-independent; the resulting closed-form local absorption law
is a ReLU network whose weights are ray paths and whose accuracy matches
FDTD within tissue-property uncertainty.

**Key figures (existing).**
- `apd_angle_dependence.pdf` -- TE/TM/avg transmission vs theta, showing
  the compensation visually. Headline figure 1.
- `R_of_f_landscape.pdf` -- pseudo-Brewster accuracy across 0.3-100 GHz,
  with the R=1 sweet spot at ~40 GHz. Headline figure 2.
- `mie_validation_corrected.pdf` -- framework error vs sphere size and
  frequency. Headline figure 3.
- `body_directivity_thelonious.pdf` -- D(k_hat) Mollweide projection.
- `apd_direction_analysis.pdf` -- distribution of P_abs across 128
  directions and three polarisations on the Thelonious phantom.
- `error_budget_comprehensive.pdf` -- error budget summary.

**Outline (target ~14 pages two-column TAP).**
1. Introduction. The 10^12-cell problem, prior empirical observations
   (Kodera/Diao/Li/Samaras), why no first-principles derivation exists.
2. Local absorption law from Poynting + Fresnel. Polarisation-aware
   `T_eff = T_avg + (q/2) DeltaT` decomposition. The exact law.
3. Pseudo-Brewster mechanism. Azzam's high-index criterion, tissue
   occupies that regime, T_avg/T_0 within 5.6% at 28 GHz, sphere ratio
   R=1 at ~40 GHz. Frequency dependence; "traffic light" validity table.
4. Geometric reduction. Total power = T_0 * A_perp; absorption
   directivity D(k_hat); spherical-harmonic compression to L=6.
5. ReLU network interpretation. `S_ab = a^T ReLU(W n_hat)`.
   Differentiability; matrix form; hierarchical computation.
6. Validation. Mie spheres (Bohren-Huffman exact), Thelonious phantom,
   literature comparison table (matches Kodera 5%, Diao 3%, Flintoft 8%,
   Zhang within scatter).
7. Limitations and conclusion.

**Methods/results balance (the user's concern).** Methods is the new
physics (pseudo-Brewster + Stokes decomposition + geometric reduction)
and is the contribution. Results section is light by design but rich in
*independent validation*: Mie at multiple body-part sizes, phantom over
all directions, plus the head-to-head comparison against four
independent FDTD studies in the literature. The framing should be
"methods = the new derivations; results = three independent
verifications" rather than apologising for a thin results section.

**What to leave out.** The polarisation Stokes vector framework (Part II
sec:polarisation) is a natural extension but bloats the paper; defer to
Paper B. The coherent MIMO machinery is a different paper (Paper C). The
sub-6 GHz extension only enters as a sentence about T-bar.

**Risk.** Reviewers may say Kodera 2024 already showed that
`SAR_wb = T_tr * A_perp * S_inc / W` reproduces full FDTD. The novelty
defence is twofold: (i) Kodera extracts `T_tr` numerically from a 1D
slab model and offers no mechanism for its near-constancy; we *derive*
T_tr from Fresnel theory and *prove* its angle-independence via
pseudo-Brewster. (ii) Kodera's result is total-power only; we derive a
local map and a multi-source ReLU network. Make this the first
distinguishing paragraph in the introduction.


### Paper B (TAP) - *Direction-averaged whole-body absorption from first principles: a generalised Cauchy formula and closed-form compliance from 100 MHz to 100 GHz*

The "compliance paper". Sister to Paper A, targets TAP's compliance/RC
dosimetry community. Centres on the *integrated* quantity rather than the
local map. Less original physics, but a cleaner empirical hit-rate
against Flintoft / Zhang / Bamba's volunteer measurements.

**Single-line claim.** Direction-averaged whole-body absorbed power is
`S_inc * T-bar * A_ab / 4`, exact from 100 MHz to 100 GHz, where A_ab is
the body's surface area weighted by ambient occlusion; this single
identity reproduces every empirical absorption-cross-section measurement
in the literature, yields a closed-form ICNIRP compliance threshold with
explicit anthropometric scaling, and applies directly to reverberation
chamber dosimetry.

**Key figures (existing).**
- A new "literature waterfall": predicted vs measured ACS for
  Flintoft (60 volunteers), Zhang (48 subjects), Bamba (4 subjects),
  Diao (28 GHz), Kodera (10-100 GHz), each as a panel. The prediction
  is one curve `T-bar(f) * A_ab/4` evaluated with each subject's BSA.
  This needs to be made; the underlying numbers are tabulated in the
  monograph (`tab:lit:predictions`).
- `R_of_f_landscape.pdf` -- accuracy of T_0 vs T-bar across frequency.
- `eta_3d_phantom.png` -- the spatial map of eta(r) on Thelonious.
- `body_directivity_sh_fit_thelonious.pdf` -- SH compression of D(k_hat).
- A new "compliance landscape" plot: S_inc^max(m, h) vs body size,
  contoured by frequency (existing tabulated data, easy to plot).
- `polarization_mollweide_thelonious.pdf` -- the polarisation-aware
  worst-case correction (one panel; the other panels live in Paper A or
  the monograph).

**Outline (target ~12 pages two-column TAP).**
1. Introduction. Reverberation-chamber ACS measurements have been
   accumulating for two decades (Bamba, Flintoft, Zhang); each defines a
   different ratio (`eta`, `xi`, `<Q^a>`); none has a first-principles
   derivation. We give one identity that explains them all.
2. Generalised Cauchy formula. Convex case (1841), exposure fraction =
   ambient occlusion, A_ab definition, `<P_abs> = S_inc * T_0 * A_ab/4`,
   replace T_0 with T-bar to get exactness at any frequency. Convex-hull
   energy bound; inter-body reflection cancellation.
3. Anthropometric compliance. Du Bois A(m,h), the m/A scaling, infant
   vs adult vulnerability, polarisation worst case (12% shift), local
   peak compliance via the exact bound `max S_ab = S_inc T_0`.
4. Frequency extension to sub-6 GHz. T-bar definition, layered tissue
   correction (skin/fat/muscle Fabry-Perot), at what frequency the local
   surface map breaks but the integrated formula survives.
5. Literature comparison. Flintoft 7-11 GHz `<Q^a> = 0.41` vs
   `T_0 * A_ab/A = 0.41`, Zhang `xi = 0.45-0.65` vs `T-bar * A_ab/A`
   prediction, Bamba `eta` vs T-bar at 1.5-6 GHz, Diao 28 GHz, Kodera
   10-100 GHz. Use the monograph's tab:lit:predictions verbatim,
   transcribe into a plotted comparison.
6. Reverberation-chamber dosimetry as the showcase. The closed-form
   replaces the FDTD calibration step; small-animal phantoms have eta
   approx 1 by convexity; the formula reduces to three precomputed
   scalars (T-bar, A_ab, and m).
7. Conclusion.

**Methods/results balance.** Naturally balanced: the methods are the
generalised Cauchy formula plus T-bar plus the anthropometric scaling,
each one paragraph plus an equation. The results are the literature
comparison, which is broad and quantitative -- this is the strongest
part of the paper because every prediction is *independently* checked.

**What to leave out.** No coherent MIMO content (Paper C). The
psSAR-over-10g material lives here as a short section bridging surface
APD to peak SAR (uses `psSAR10g.tex`); psSAR is what ICNIRP cares about
at the upper end of the band, so including it makes the compliance
story complete.

**Risk.** Some referees will see this as a methods note or extension to
Kodera 2024. Counter-positioning: Kodera predicts whole-body SAR for
plane waves; we predict reverberation-chamber ACS, anthropometric
compliance thresholds, the absorption coefficient `xi`, and tie all of
these together via the *exposure fraction* concept (which is missing
from Kodera). Lead with the literature waterfall figure; that figure
itself is the contribution.


### Paper C (TWC) - *A closed-form exposure operator for coherent millimetre-wave: body absorption, signal-exposure alignment, and exposure-constrained beamforming*

The "MIMO paper". Targets TWC's beamforming/MIMO/JSAC community.

**Single-line claim.** For an M-element array radiating with precoder x,
the whole-body absorbed power on a person illuminated by N propagation
paths equals `x^H Q x`, where Q is a Hermitian PSD matrix derived in
closed form from the propagation paths and Fresnel coefficients (no FDTD
calibration); the resulting exposure-constrained beamforming problem has
a closed-form solution `x* propto (lambda Q + nu I)^{-1} h*` and extends
to MU-MIMO without new approximations.

**Key figures (existing).**
- `channel_block_diagram.pdf` -- the architecture: signal vs exposure
  branch sharing a propagation pipeline. Headline figure.
- `fresnel_curves.pdf` -- amplitude magnitudes and phases of t_s, t_p
  vs theta, motivating why the pseudo-Brewster scalar approximation
  fails in the coherent regime.
- `approx2_gamma_validation.pdf` -- numerical proof that Approximation 2
  (universal depth coupling) introduces <0.5% error.
- `tab:coherent-scaling` (existing as a table) -- coherent N^2 vs
  incoherent N peak scaling.

**Key figures (to be made).** The results in the monograph for Part III
are mostly *qualitative discussion* (hotspot scaling table; structural
remarks about rho, ECBF limits, MU-MIMO). To turn this into a TWC paper
we need quantitative simulations:

- An ECBF Pareto curve. Plot `|h^T x|^2` (received signal power)
  vs `x^H Q x` (whole-body absorbed power) for: MRT, ECBF at varying
  lambda, GEP optimum (`Q^{-1} h*`), random precoders. Need a
  representative scenario: 64-element URA at 3 m, Thelonious phantom,
  one UE behind/beside the body, 28 GHz. Single figure, clear story.
- The exposure-signal alignment rho across UE positions. Heatmap or
  Mollweide of rho(r_UE) for fixed BS, for Thelonious. Shows the
  geometric protection regions where MRT is benign for the body.
- Hotspot pattern on the body for MRT vs ECBF. Two surface heatmaps
  side by side, demonstrating the "body hotspot does not coincide with
  signal focus" claim quantitatively. (Spatial maps - good visual.)
- Comparison vs FDTD-calibrated SAR matrix in the spirit of Hochwald
  2014 / Castellanos 2020. Optional but extremely strong if feasible.
  Specific ask: do we have authority/data to reproduce one of those
  FDTD-calibrated S matrices and compare entry-by-entry?
- Path-space spectrum of M*P (the worst-case eigenvalue lift). Shows
  the rank truncation argument from `system_formalism.tex` -
  `dim(reachable absorption modes) <= M`.

**Outline (target ~14 pages two-column TWC).**
1. Introduction. Massive-MIMO downlink, the SAR matrix problem
   (Hochwald 2014), why FDTD calibration is intractable above 6 GHz,
   what a closed-form analytical Q would unlock.
2. Setup: paths, polarisation-amplitude vectors psi_n, the field
   channel matrix G(r) = Psi Phi(r) J. Signal branch via
   antenna pattern projection -> h. Exposure branch: per-path
   Fresnel transmission operator F_n.
3. Coherent absorption law. Depth integral, the Lambda matrix, the two
   approximations (TM polarisation direction, universal depth coupling)
   with bounded errors. Theorem: `S_ab(r) = ||G_tilde(r) x||^2`.
   Single-wave limit recovers Part I; incoherent limit recovers
   multi-source Part I.
4. Exposure operator Q. Definition, eigendecomposition = exposure
   modes. Path-space factorisation `Q = J^T M J` (this is the
   `system_formalism.tex` content). Worst-case absorbed power
   `lambda_max(Q) = lambda_max(MP)` lives on the N-dimensional path
   space, not the M-dimensional element space.
5. Signal-exposure alignment rho. Geometric mechanisms preventing the
   body hotspot from coinciding with the signal focus. Three structural
   differences (vector vs scalar sum; Fresnel filtering vs antenna
   projection; per-path phase between r_UE and r in Sigma).
6. ECBF closed form. QCQP, S-procedure, optimal precoder
   `(lambda Q + nu I)^{-1} h*`, push-through to path space
   `J^T (nu I_N + lambda M P)^{-1} b`. Limiting regimes. Generalised
   eigenvalue problem (signal-per-absorbed-power). Compare against
   Ying 2015 (same algebraic form, but their S is FDTD-calibrated, ours
   is closed form).
7. MU-MIMO. Per-person Q^(u), incoherent stream superposition,
   exposure-constrained sum rate, integration into WMMSE.
8. Results. ECBF Pareto, rho landscape, hotspot maps,
   approximation-error budget.

**Methods/results balance.** This is the paper where the user's concern
is sharpest. The methods is genuinely large (Sec 2-7) because deriving
Q from scratch is the contribution. To balance, the results section
must be vivid: ECBF Pareto, rho heatmap, hotspot side-by-side, all
with quantitative comparisons against MRT and against the
FDTD-calibrated baseline. New simulations are required; the AEGIS
codebase already supports them.

**What to leave out.** The reflection-operator / JSAC duality
(`q_complement.tex`) is intriguing but speculative; it deserves its own
paper later, not a section here. The thermal / Kirchhoff dual is the
same. The transparency subspace deserves a results section but only if
we can numerically measure its dimension on a real array.

**Risk.** Most TWC reviewers will compare to Hochwald 2014 / Ying 2015
/ Castellanos 2020. The defence is the closed-form derivation of Q from
propagation paths, no FDTD step in the loop. Make this the first
distinguishing claim in the abstract.


## Why these three and not other splits

I considered three alternative partitions and rejected each.

**Split-by-Part (I vs II vs III).** Part II (polarisation Stokes vector;
T-bar) doesn't have enough body to anchor a high-impact paper on its
own. Splitting it across Paper A (the local Stokes correction) and
Paper B (the integrated T-bar) is more impactful.

**Polarisation as its own paper.** Considered "Polarisation-aware mmWave
body absorption: an absorption Stokes vector and its multipath
suppression" as a TAP paper. The headline result (16% worst case on a
human, 27.9% cylinder bound, suppressed below 2.5% at N=20) is
elegant but narrow. It works better as a section in Paper A (the local
correction term) and Paper B (the worst-case bound on the compliance
threshold).

**JSAC duality as its own paper.** `q_complement.tex` derives the
reflection operator Q_ref, proves an eigenvector-locking proposition
under pseudo-Brewster (Q_ref ~ ((1-T_0)/T_0) Q_abs), and sketches
sensing-communication duality plus a Kirchhoff dual. This is *very*
publishable but the user flagged that companion as "wandering, not a
theorem-proof paper". To turn it into TAP/TWC requires firming up the
locking proof, numerical verification of the eigenvector overlap on a
real body+array configuration, and at least one quantitative sensing
example. Worth doing later as Paper D, not in this initial batch.


## Methods/results balance: a unified position

The user is right to flag the imbalance. My recommendation: don't try
to inflate results to match methods. Instead, frame each paper so the
results section is doing one specific thing.

- **Paper A**: results = independent validation. Mie + phantom + four
  literature studies. The story is "the methods derive a closed form;
  here are five independent checks." Three pages of validation are
  plenty if each check is a different geometry / frequency / source.

- **Paper B**: results = the literature waterfall figure. One headline
  figure with predicted-vs-measured for every empirical ACS study,
  evaluated subject-by-subject where data is available, with body-size
  scatter. Backed up by the compliance-threshold table across
  anthropometric population.

- **Paper C**: results = ECBF and MU-MIMO simulations (new) + approx
  error budget. This is the only paper where new simulation is
  *needed*; the AEGIS codebase already produces the underlying paths
  via DiffeRT/Sionna and the Q assembly via the coherent module.

For Paper C specifically: budget 2-3 days to design, run, and produce
the four results figures listed above. This is the area where "be
smart about not running giant simulations" applies; one well-chosen
scenario (URA, Thelonious, single UE then 4 UEs) is enough.


## What I need from you

- Confirmation that this three-way split is the right framing.
- Decision on which paper to write first. My order of recommendation:
  Paper A first (it underpins the other two; cleanest story), Paper C
  second (highest TWC impact and most distinct from Paper A), Paper B
  third (writes itself once A is in place).
- For Paper C: a yes/no on running new simulations using the AEGIS
  codebase to produce the four results figures. If no, Paper C becomes
  more methods-heavy and shorter on quantitative results.
- For Paper B: do you want the layered-tissue / standing-wave
  sub-6 GHz section from `section_below6ghz.tex` to be a top-level
  section, or kept as a one-paragraph aside on validity limits?
- A go/no-go on dropping the backflip posture-sensitivity figure
  entirely (you suggested it has a variability bug). I am not quoting
  it in any paper as written; confirm.


## Headline figures inventory (existing in `theory/figures/`)

For quick reference. All exist as both .pdf and .png unless noted.
| Figure | Paper | Role |
|---|---|---|
| `apd_angle_dependence` | A | Pseudo-Brewster compensation, headline |
| `R_of_f_landscape` | A,B | Pseudo-Brewster across frequency |
| `mie_validation_corrected` | A | Mie validation |
| `body_directivity_thelonious` | A,B | D(k_hat) Mollweide |
| `body_directivity_hist_thelonious` | A | D distribution |
| `body_directivity_sh_fit_thelonious` | A,B | SH compression |
| `apd_direction_analysis` | A | Phantom directional/polarisation |
| `error_budget_comprehensive` | A | Error budget |
| `polarization_mollweide_thelonious` | A,B | Polarisation response |
| `multipath_convergence` | A | DB suppression with N |
| `sh_compression_polarization` | B | Stokes SH compression |
| `eta_3d_phantom` | B | Spatial eta map |
| `inter_body_*` (4 figs) | A | Inter-body reflection bound |
| `near_field_distance_sweep` | A | NF/FF transition |
| `fresnel_curves` | C | Amplitude+phase, motivates exact Fresnel |
| `approx2_gamma_validation` | C | Universal depth coupling check |
| `channel_block_diagram` | C | Architecture diagram (TikZ) |
| `incidence_plane_fig` | C | Single-path geometry (TikZ) |
| `delta_T_angle_dependence` | A | Polarisation splitting vs angle |

Need to make for Paper C: ECBF Pareto, rho landscape, MRT vs ECBF
hotspot pair, M*P spectrum.

Need to make for Paper B: literature waterfall plot (one panel per
study), compliance-threshold landscape contour.


## A note on style

The user's `papers/how_to_write_good/` rules apply at writing time, not
brainstorm time. The salient ones for this batch:

- IEEE journals expect dry, precise, conservative prose. The
  conversational tone of `q_complement.tex` ("Now the fun starts") will
  not fly.
- The monograph's "ReLU neural network" framing is exactly the kind of
  cross-disciplinary connection that high-impact reviewers like, but it
  must not feel like the paper is *primarily* about ML. Lead with the
  EM physics; close with the ML interpretation as a natural consequence.
- The four-decade ambient-occlusion identification is the same: lead
  with the dosimetry result, close with "this is mathematically
  identical to ambient occlusion in computer graphics" as a one-line
  reduction.
- No em dashes, no semicolons, sentence-case headings (per
  `CLAUDE.md`), strict imperative-mood commit messages. These apply to
  the paper-writing phase, not this brainstorm.
