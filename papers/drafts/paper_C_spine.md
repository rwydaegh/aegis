# Paper C — Medium-level plan

**Working title:** *A closed-form exposure operator for coherent
millimetre-wave: from path geometry to exposure-constrained beamforming
without FDTD calibration.*

**Target venue:** IEEE Transactions on Wireless Communications.

**Target length:** 14 two-column pages, 7 figures, 2 tables.

**Status:** AEGIS coherent code is complete and runnable. The paper
needs new simulations for §10. No FDTD coherent multi-source ground
truth exists — the validation argument rests on (i) Approximation 1 and
2 error bounds (numerical), (ii) the single-wave limit recovering Paper
A's validated case, and (iii) internal consistency on simulated
scenarios.


## The question (one paragraph)

In coherent MIMO beamforming with M antenna elements and a precoding
vector x ∈ C^M, the absorbed power on a person near the array is a
quadratic form x^H S x where S is a Hermitian PSD matrix (Hochwald
2014). The optimal exposure-constrained beamformer is closed-form
(Ying 2015), provided one has S. In every published instance, S is
calibrated by FDTD per device per body configuration, which becomes
intractable above 6 GHz where mmWave systems operate. **What is S in
closed form, derived from the same propagation paths that yield the UE
channel h?**


## The answer (one paragraph)

Under two well-bounded approximations — Approximation 1 (replace the
refracted TM polarisation direction by the incident, ≤ 4 % cross-term
error) and Approximation 2 (set normalised depth couplings Γ_{nn'} = 1,
≤ 0.5 % cross-term error) — the absorbed power density at any body
surface point r reduces to a squared norm

  S_ab(r) = ‖G̃(r) x‖²

where G̃(r) ∈ C^{3×M} is the Fresnel-filtered, depth-weighted body-
surface channel matrix assembled from the same propagation paths {ψ_n,
k̂_n} that produce the UE channel h. Integrating over the body yields
the **exposure operator**

  Q = ∫_Σ G̃(r)^H G̃(r) dA  ∈ C^{M×M},  P_abs = x^H Q x.

Q admits a path-space factorisation **Q = J^T M J** where J ∈ {0,1}^{N×M}
is a combinatorial element-to-path dispatch matrix and M ∈ C^{N×N} is
the Hermitian PSD path-pair Gram. The exposure-constrained beamforming
problem retains the closed-form Ying-2015 solution
x* ∝ (λQ + νI)^{-1} h*, but Q now comes from analytical Fresnel +
ray-tracing data with no FDTD step in the loop. The factorisation
admits broadband, near-field, stochastic, low-rank, and multi-user
extensions as small perturbations of M.


## Section-by-section plan

### 1. Introduction (1.5 pages, 0 figures)

**Argument:** the SAR-matrix problem is solved on paper for two decades,
but the SAR matrix itself is the bottleneck. We close the loop by
deriving it analytically from propagation paths.

- One-paragraph framing of coherent MIMO and the body-absorption
  problem. mmWave fields add as amplitudes; coherent peak ~ N² vs
  incoherent N.
- The SAR-matrix story: Hochwald 2014 introduced x^H S x; Ying 2015
  derived the closed-form ECBF; Ebadi-Shahrivar 2019 reduced compliance
  to λ_max(S); Castellanos 2020 calibrated per-element scalar Fresnel
  at 28 GHz. **In every case S is FDTD-fitted.** At mmWave this
  forecloses the analytical closed form.
- Position the contribution: derive Q in closed form from the same
  ray-tracing data used for h. Path-space factorisation. Five
  immediate extensions (broadband, near-field, stochastic, low-rank,
  multi-user) all become small perturbations.
- Five-bullet contributions list:
  1. Closed-form Q with no FDTD calibration.
  2. Two well-bounded approximations (TM polarisation direction,
     universal depth coupling) with explicit numerical error budgets.
  3. Path-space factorisation Q = J^T M J reducing the M×M spectral
     problem to an N×N problem on the element-tied subspace.
  4. ECBF closed-form retained from Ying 2015; multi-user extension
     via per-person Q^(u) integrating into WMMSE.
  5. Quantitative demonstration on a representative URA-Thelonious
     scenario at 28 GHz.

### 2. Setup (1 page, 0 figures)

**Argument:** propagation paths, dispatch matrix, phase diagonal, three
inherited assumptions.

- Base station with M elements, precoder x ∈ C^M with ‖x‖² = P.
- Propagation environment produces N paths from ray tracing. Path n
  carries (j(n), k̂_n, ψ_n) where j(n) is the originating element and
  ψ_n ∈ C^3 is the polarisation-amplitude vector.
- Three inherited assumptions: locally flat surface, thin skin
  (δ ≪ body), locally plane wave (last-scatter distance > 3λ).
- Field channel matrix G(r) = Ψ Φ(r) J. Define each block:
  Ψ ∈ C^{3×N} = stacked path polarisations (environment),
  Φ(r) ∈ C^{N×N} = diagonal of geometric phases at r,
  J ∈ {0,1}^{N×M} = element-to-path dispatch.

### 3. Three branches of one carrier (1 page, 1 figure)

**Argument:** the field, signal, and exposure channels are three linear
read-outs of the same path-amplitude carrier.

- Path-amplitude carrier c(r, x) = Φ(r) J x ∈ C^N. Single state
  variable from which every coherent observable follows.
- Three read-outs:
  - Field branch: E(r) = Ψ c.
  - Signal branch: y = α^T c(r_UE, x); UE channel h^* = J^T b with
    b = Φ(r_UE)^H α^*.
  - Exposure branch: Ẽ(r) = Ψ̃(r) c, with Ψ̃(r) = [√(σ/(4α_n)) F_n(r) ψ_n]
    containing the per-path Fresnel-filtered, depth-weighted read-out.
- **Figure 1 (existing): channel_block_diagram.** Architecture
  diagram. Caption emphasises: "Signal and exposure are reciprocal MRT
  problems sharing the path geometry (J, Φ) and differing only in
  whether the virtual source is a point r_UE or a distributed aperture
  Σ."

### 4. Coherent absorption law (2.5 pages, 2 figures)

**Argument:** the absorbed power density is the ohmic loss integrated
over depth. Two well-bounded approximations collapse the resulting
double sum to a squared norm.

- Begin from the depth integral S_ab(r) = (σ/2) ∫₀^∞ |Σ_n E_n^trans(r,z)|² dz.
- Expansion produces depth coupling factors
  Λ_{nn'} = 1/(α_n + α_{n'} - i(β_{n'} - β_n)), Hermitian PSD.
- **Approximation 1 (TM polarisation direction):** replace the refracted
  ê'_p,n by the incident ê_p,n. Self-terms exact; cross-term error
  ≤ 4 % at 28 GHz. Mechanism: the normal field component inside tissue
  is O(1/|ñ|); contribution to |E^trans|² is O(1/|ñ|²) ≤ 4 % for skin.
- **Figure 2 (existing): incidence_plane_fig.** Geometry of
  Approximation 1.
- **Approximation 2 (universal depth coupling):** define Γ_{nn'} =
  Λ_{nn'} / √(Λ_{nn} Λ_{n'n'}) and set Γ_{nn'} ≈ 1. By construction
  Γ_{nn} = 1; cross-term error ≤ 0.5 % at 28 GHz. Mechanism: high |ñ|
  compresses all refraction angles below 10° from normal, making α_n,
  β_n nearly angle-independent.
- **Figure 3 (existing): approx2_gamma_validation.** Numerical
  validation across all incidence-angle pairs. Caption: "≤ 0.44 %
  error over [0°, 85°]² with mean 0.17 %."
- **Theorem (coherent absorption law):** under Approximations 1 and
  2, S_ab(r) = ‖G̃(r) x‖². Boxed equation. One-paragraph proof: the
  Λ matrix factors as √Λ √Λ on the diagonal under Approx 2, and the
  squared modulus expansion turns into a squared norm.
- Single-wave limit: recovers the Part II polarisation-aware Fresnel
  law (validated in Paper A); under additional pseudo-Brewster reduces
  to the Part I geometric law.
- Incoherent limit (random relative phases): cross-terms average to
  zero; recovers Paper A's multi-source formula.
- Combined error budget: ≤ 5 % on cross-terms for any precoder, exact
  on self-terms (so exact in the incoherent limit). Quantify ‖ΔQ‖/‖Q‖
  on a representative scenario in §10 results.

### 5. The exposure operator (1 page, 0 figures)

**Argument:** integrating the coherent law over the body yields a
Hermitian PSD matrix Q ∈ C^{M×M} whose quadratic form is the absorbed
power.

- **Boxed definition:** Q = ∫_Σ G̃(r)^H G̃(r) dA, P_abs = x^H Q x.
- Hermitian PSD by construction; rank ≤ min(M, 3 M_tri).
- Eigendecomposition Q = Σ_k λ_k v_k v_k^H reveals exposure modes:
  v_1 maximises body absorption; λ_max is the maximum absorbed power
  per unit transmit power; tr(Q) is expected absorbed power under
  isotropic transmission (one paragraph).
- Comparison with prior art:
  - Hochwald 2014 / Ying 2015: same algebraic form (x^H S x), but
    their S is FDTD-calibrated for a fixed device-body geometry; ours
    is the analytical surface-integral counterpart over the *entire*
    body.
  - Ebadi-Shahrivar 2019: λ_max(S) bounds worst-case SAR; same
    identity holds for Q.
  - Castellanos 2020: their per-element calibration scalar β ≈ 0.70
    lumps Fresnel + depth-decay. We recover both analytically: 
    β = √T_0 · √Λ_{11} = √(T_0 cos θ / (2αZ_0)) per path.

### 6. Path-space factorisation (1.5 pages, 0 figures)

**Argument:** Q = J^T M J where M is path-pair Gram. The worst-case
eigenvalue lifts to an N-space problem. The factorisation gives
broadband, near-field, stochastic, low-rank, and multi-user extensions
for free.

- **Theorem:** Q = J^T M J where M = ∫_Σ Φ^H Ψ̃^H Ψ̃ Φ dA ∈ C^{N×N}
  is Hermitian PSD. M_{nn'} is a Fourier component of the body surface
  at the difference wave vector q_{nn'} = k_0(k̂_{n'} - k̂_n) weighted
  by Fresnel-filtered polarisation overlap.
- **Corollary:** λ_max(Q) = λ_max(M·P) where P = J J^T is the element-
  block projector. The relevant eigenproblem lives on N-dimensional
  path space, restricted to the rank-≤-M element-tied subspace
  E = range(J).
- **Element-tied subspace E ⊂ C^N**: the geometric locus of reachable
  absorption modes. Path-space directions orthogonal to E cannot be
  excited by any precoder.
- Five extensions in two paragraphs each:
  - Broadband: Q(ω) = J^T M(ω) J at each ω; the Lagrangian over
    integrated constraints separates pointwise.
  - Near-field: replace Φ(r) with Φ^NF(r) using confocal phase kernel
    1/R_n exp(-ik_0 R_n); the structure of the factorisation is
    unchanged.
  - Stochastic: Q̄ = J^T M̄ J with M̄ = E[M]; expected ECBF inherits
    the closed-form solution.
  - Low-rank: rank-r truncation has bound λ_{r+1} P on the absorbed-
    power error; r ≤ M, often r ≪ M for typical multipath.
  - Multi-user: K bodies → K matrices Q^(u), all closed-form, all
    integrating into existing WMMSE solvers.
- Computational consequence: spectral assembly of M·P is O(N²);
  spectral assembly of Q is O(MN²). When N ≪ M (sparse multipath), the
  N-space problem wins; when M ≪ N (massive multipath), the M-space
  problem wins. The factorisation gives both options.

### 7. Signal-exposure alignment ρ (1.5 pages, 0 figures)

**Argument:** under MRT, absorbed power = P · ρ · λ_max(Q). The
geometric mechanisms that decouple body hotspot from UE focus are
physically interpretable.

- ρ = (h^T Q h^*) / (‖h‖² λ_max(Q)) ∈ [0, 1]. Path-space form:
  ρ = (b^H P M P b) / ((b^H P b) λ_max(M·P)).
- **Three structural mechanisms decouple body hotspot from UE focus:**
  - Vector vs scalar: signal sums scalars h_j* h_j ∈ R^+; body field
    sums vectors h_j* g̃_j(r) ∈ C^3. Vector partial cancellation.
  - Fresnel filter vs antenna projection: a path with strong UE
    contribution may contribute weakly to absorption if it arrives at
    grazing incidence (low transmission).
  - Per-path phase between r_UE and r ∈ Σ: each path acquires an
    additional phase moving from UE position to body surface,
    degrading coherent alignment.
- Consequence: ρ small when dominant signal paths arrive at grazing
  incidence on the body or from self-shadowed directions. **Geometric
  protection.** Strong signal coexists with low absorption.
- Quantitative demonstration deferred to §10 (the ρ landscape).

### 8. Exposure-constrained beamforming (1.5 pages, 0 figures)

**Argument:** the QCQP retains its closed-form solution; the
push-through identity moves the inverse from M×M to N×N.

- QCQP: max |h^T x|² s.t. x^H Q x ≤ P_max, ‖x‖² ≤ P. Two PSD
  constraints; the S-procedure guarantees the KKT point is global.
- **Closed-form solution:** x* ∝ (λQ + νI)^{-1} h* with KKT multipliers
  λ, ν ≥ 0 from complementary slackness.
- Path-space push-through (Woodbury):
  x* ∝ J^T (νI_N + λM·P)^{-1} b. Inverse is N×N.
- Limiting regimes: λ→0 recovers MRT; λ→∞ steers into ker Q (the
  transparency subspace; mention but don't develop here, defer to a
  future paper that picks up `q_complement.tex`).
- Generalised eigenvalue formulation:
  max_x |h^T x|² / (x^H Q x) yields x* ∝ Q^{-1} h*; the Pareto front
  between MRT and the GEP optimum traces the ECBF family.
- One-paragraph multi-user extension: per-person Q^(u), incoherent
  stream superposition, exposure-constrained sum-rate fits directly
  into WMMSE.

### 9. Numerical demonstration: a canonical scenario (3 pages, 4 figures, 1 table)

**Argument:** on a single representative scenario, demonstrate (i)
approximation errors are bounded as claimed, (ii) ECBF Pareto trade-off
between signal and absorbed power, (iii) ρ varies dramatically across
UE positions (geometric protection is real), (iv) the body hotspot is
displaced from the UE focus quantitatively, (v) M·P spectrum is
low-rank (the path-space factorisation buys real computation).

**Canonical scenario:** 8×8 (M = 64) URA at 3 m from Thelonious phantom,
28 GHz, 30-60 multipath paths via DiffeRT bridge, single UE at 5 m.
Two UE configurations: (a) UE in front (signal direction aligned with
body absorption modes), (b) UE behind (geometrically protected).

#### 9.1 Approximation error budget

- Compute Q under the full Λ matrix (no Approx 2) and under
  Approximation 2; report ‖ΔQ‖/‖Q‖ for the canonical scenario.
- Predicted: ≤ 5 % combined error. Expected actual: 1-3 % typical.
- One-paragraph table.

#### 9.2 ECBF Pareto curve

- **Figure 4 (NEW, the central results figure):** received signal
  power |h^T x|² per unit transmit power vs whole-body absorbed power
  per unit transmit power. Curves: MRT (single point top right), GEP
  optimum (single point top left), ECBF family at varying λ tracing
  the Pareto frontier, random-precoder cloud, incoherent-superposition
  baseline (Paper A's multi-source formula). Single panel; the
  numerical headline.
- Caption: "ECBF reduces body absorbed power by N× while sacrificing
  M dB of signal power; the Pareto trade-off has a clean bend
  identifiable by the ratio λ/ν."

#### 9.3 ρ heatmap across UE positions

- **Figure 5 (NEW):** ρ Mollweide heatmap. Fix BS; sweep r_UE over a
  1 m × 1 m grid at human height around Thelonious; compute ρ at each
  grid point. Colour = ρ, overlay phantom silhouette.
- Caption: "Geometric protection regions (low ρ) cover ~30 % of UE
  positions in this scenario. In these regions, MRT uses less than
  10 % of the body's worst-case absorption. The mechanisms in §7
  predict this geometrically."

#### 9.4 MRT vs ECBF hotspot maps

- **Figure 6 (NEW):** two surface heatmaps of S_ab on Thelonious, MRT
  and ECBF at the same SNR target. Side by side, identical colour
  scale.
- Caption: "Under MRT (left), the body hotspot localises near the
  projection of the UE direction. Under ECBF (right) at 50 % SNR
  cost, the hotspot disperses; integrated absorption drops by a
  factor of N."
- Quantitative numbers in caption: peak S_ab MRT vs ECBF, integrated
  P_abs MRT vs ECBF, displacement of peak.

#### 9.5 M·P spectrum and rank truncation

- **Figure 7 (NEW):** cumulative eigenvalue fraction (Σ_k λ_k / tr(Q)
  sorted descending) vs k, for several N (e.g. 10, 50, 200) at fixed
  M = 64.
- Caption: "Effective dimensionality of body-absorption modes is
  ~10 even when M = 64 elements span 200 multipath paths. The
  path-space factorisation makes this rank-truncation explicit."

### 10. Conclusion (0.5 pages)

- Three sentences: closed-form Q replaces FDTD calibration; path-
  space factorisation handles broadband / near-field / stochastic /
  low-rank / multi-user; ECBF retains the closed-form Ying-2015
  solution.
- Forward look: a separate paper develops the reflection-operator
  complement Q_ref and the sensing-exposure duality under
  pseudo-Brewster locking (the q_complement.tex content as Paper D).
- One paragraph honest about the FDTD ground-truth gap: coherent
  multi-source FDTD comparison is not currently feasible; Paper A's
  validation underpins ours; future work would compare entry-by-entry
  on a Hochwald-2014-style scenario at 28 GHz when FDTD becomes
  tractable.


## Headline numerical claims

| Claim | Numeric | Source |
|---|---|---|
| Approximation 1 cross-term error | ≤ 4 % at 28 GHz on skin | tab:approx-accuracy |
| Approximation 2 cross-term error | ≤ 0.44 % over [0°, 85°]², mean 0.17 % | fig:approx2-validation |
| Combined cross-term error | ≤ 5 % | sec:coherent-absorption-law |
| ‖ΔQ‖/‖Q‖ on canonical scenario | TBD by simulation, expected 1-3 % | §9.1 |
| Coherent peak vs incoherent average for N co-phased paths | factor N | tab:coherent-scaling |
| ECBF reduction in body absorbed power | factor N achievable | §9.2 |
| Effective rank of Q on canonical scenario | ~10 (out of 64) | §9.5 |
| Geometric-protection coverage (low ρ) | ~30 % of UE positions | §9.3 |


## Headline figures

1. **Figure 1 (existing): channel_block_diagram.pdf.** Architecture
   diagram. Lead figure.

2. **Figure 2 (existing): incidence_plane_fig.pdf.** Approximation 1
   geometry.

3. **Figure 3 (existing): approx2_gamma_validation.pdf.** Numerical
   validation of Approximation 2.

4. **Figure 4 (NEW, central): ECBF Pareto.** MRT, GEP, ECBF family,
   random precoder cloud, incoherent baseline.

5. **Figure 5 (NEW): ρ heatmap.** UE position landscape.

6. **Figure 6 (NEW): MRT vs ECBF hotspot maps.** Side-by-side body
   surface heatmaps.

7. **Figure 7 (NEW): M·P spectrum.** Cumulative eigenvalue fraction
   vs rank.


## Adversarial-positioning manifest

**"Hochwald 2014 / Ying 2015 already solved the closed-form ECBF."**
Counter: They assume an oracle gives them S. We *derive* it. The
closed-form Q without FDTD calibration is the central novelty. Lead
the abstract with this.

**"Castellanos 2020 already used per-element Fresnel scalars at 28 GHz."**
Counter: their β = 0.70 lumps Fresnel + depth-decay. We recover both
pieces analytically: β = √(T_0 cos θ / (2αZ_0)) per path. Their
calibration is a one-number reduction; ours is a per-path operator.

**"Approximation 1 introduces 4 % error on cross-terms. In the
coherent regime, cross-terms can dominate."**
Counter: Self-terms are exact under both approximations; the only
errors are on cross-terms. The combined relative error on x^H Q x for
any precoder is bounded by the spectral perturbation argument (Weyl)
and is ≤ 5 % typical. Quantify on the canonical scenario in §10
results (§9.1). Approximation 2 alone is 0.5 %; Approximation 1
contributes the rest.

**"You don't validate against FDTD ground truth."**
Counter: No coherent multi-source FDTD reference is currently feasible
above 6 GHz on a full body. We validate by:
(i) Approximation error budgets (numerical, §9.1);
(ii) The single-wave limit of our coherent law recovers Paper A's
incoherent law, which is validated against Mie + phantom + Sim4Life
FDTD;
(iii) Internal consistency on the canonical scenario;
(iv) Comparison to literature ECBF formulations (Hochwald, Ying)
on the algebraic structure.
This is honest about what we have and don't have. Make it explicit in
§5 (or §10's conclusion). Future work: direct FDTD comparison when
multi-source coherent FDTD becomes tractable.

**"Path-space factorisation Q = J^T M J is just notation."**
Counter: Three concrete consequences (§6):
(i) Worst-case eigenvalue computed in N-space rather than M-space;
when N ≪ M this is a real saving.
(ii) Broadband, near-field, stochastic extensions are linear in M and
fixed in J → all extensions reuse the same J·P structure.
(iii) Low-rank approximation has provable error bound. Demonstrate
empirically in §9.5.

**"Where's the WMMSE simulation?"**
Counter: We show the formulation; the WMMSE integration is one
equation. Full MU-MIMO sum-rate simulation is a follow-up paper. We
keep §9 single-user to keep scope tight; multi-user extension is
algebraically immediate.

**"Why is your scenario only 64 elements? Massive MIMO needs 256+."**
Counter: 64 is a representative URA size for academic baselines and
for the FR3 mid-band where mmWave deployments are practical today. The
algorithm scales; the figure for M·P spectrum (§9.5) demonstrates
that effective rank of Q does not grow linearly with M, so the path-
space factorisation buys more as M increases. Add a paragraph in
discussion: "for M = 256 we expect rank(Q) ~ 30, computational saving
~ M/30 ≈ 8×."


## Open decisions before writing

1. **Run the canonical scenario simulations (§9).** 1-2 days with the
   existing AEGIS coherent code. Dispatch a sim agent with the
   scenario spec. *Critical path.*
2. **Defer Q_ref / JSAC duality to Paper D entirely.** No section, no
   teaser figure. The forward-citation in §11 conclusion suffices.
3. **Path-space factorisation: how much depth in main text?** Current
   spine has §6 deriving and §9.5 demonstrating. Five extensions
   bullet-listed without numerical demonstration. *Reasonable
   compromise.* If reviewers push back, can demote three of the five
   to a follow-up paper.
4. **Section 9.2 (ECBF Pareto): what is the right "incoherent
   baseline"?** Three candidates:
   (a) Paper A's multi-source incoherent formula evaluated at the same
       paths but with random relative phases.
   (b) MRT applied with phases from a different scenario (mismatched).
   (c) Fixed-element-power transmission (no precoding).
   Lean toward (a) for clarity; check by simulation which is most
   informative.
5. **Section 9.4 (hotspot pair): one frequency or two?** 28 GHz is
   the AEGIS sweet spot. 7 GHz is where we have validation. Lean: 28
   GHz for the headline, brief mention that the 7 GHz numerics behave
   the same way (incoherent superposition limit).


## Source files

| Source | Section used |
|---|---|
| `theory/monograph_v2.tex` | sec:coherent-setup, sec:field-channel, sec:fresnel-operator, sec:coherent-absorption-law, sec:exposure-operator, sec:MRT-body-section, sec:coherent-hotspot, sec:ecbf, sec:mu-mimo, app:depth-identity, app:depth-coupling |
| `theory/system_formalism.tex` | sec:carrier, sec:branches, sec:Q-factor, sec:wc-eig, sec:rho-path, sec:ecbf-path; broadband, near-field, stochastic, low-rank sections selectively |
| `src/aegis/coherent/exposure_operator.py` | Q assembly implementation |
| `src/aegis/coherent/ecbf.py` | ECBF solver implementation |
| `src/aegis/coherent/multibody_ecbf.py` | MU-MIMO solver implementation |
| `src/aegis/integration/` | DiffeRT path generation for canonical scenario |


## Estimated writing path

Day 1: Run canonical scenario simulations (Figure 4, 5, 6, 7 data).
Day 2: Render all four new figures.
Day 3: §1 + §2 + §3.
Day 4: §4 + §5.
Day 5: §6 + §7 + §8.
Day 6: §9 (text accompanying figures) + §10 + abstract.
Day 7: internal review + revisions.
