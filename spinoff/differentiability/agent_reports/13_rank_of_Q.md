# The rank and effective rank of the AEGIS exposure operator Q

Agent report for the differentiability study. Written 2026-07-09. Scope is the narrow technical
question the orchestrator botched, not the business case. Every claim is marked `verified` (source
cited or code run and shown), `inferred` (reasoned, reasoning shown), or `could-not-check`.

Style: no em dashes, no semicolons, sentence case headings.

---

## 0. The one sentence that matters, at the top

The repo's settled answer and my own calculation **agree**, and the orchestrator's two conflicting
numbers were both partly right and partly an artifact. The algebraic rank of `Q` is
`min(M, 3 * n_tri)`, which is `M` (full) for any real body. The *effective* rank is small but
**threshold dependent**: median **8 eigenvalues reach 90 percent of the trace**, but **about 23
reach 99 percent** (I measured 7 and 23 on the real ray-traced grid, the paper says 8 and "at least
21"). The single mode holds 45 to 60 percent. The low effective rank is **not** a property of the
body. It is what survives after the body's intrinsically high-rank surface kernel is projected
through the finite angular aperture of the array. The number is set by the illumination aperture,
and it is frequency invariant when the array is half-wavelength spaced. All three of those
statements are the repo's own most recent position and I reproduced each numerically.

The orchestrator's `PR = 1.00` was a **mesh unit double-scaling bug**, not physics. The `PR = 5.15`
driver was correct.

---

## 1. The bug, plainly

The orchestrator's four drivers live in the scratchpad. `rank_q.py` reported participation ratio
`PR = 5.15` (M = 256, 28 GHz). `diff_check.py`, `rank_mp.py`, and `bugfind.py` reported `PR = 1.00`
at what looked like identical settings. `bugfind.py` then "proved" the two `build_G` functions
return byte-identical arrays and concluded the bug must be elsewhere. That inference was wrong.

**Root cause (`verified`, I ran all four).** The phantom meshes are already in **meters**. I checked
every phantom:

```
duke  n_tri=56024  extent=[0.541 0.284 1.806] m   ella 1.636 m   eartha 1.386 m   thelonious 1.182 m
```

- `rank_q.py` guards the millimeter-to-meter conversion behind `if ext.max() > 10:`. Since duke's
  true extent is 1.806 < 10, it correctly **skips** the divide and keeps the body at human scale.
  Array 3 m away, 8 cm aperture, resolves about 5 modes. `PR = 5.15`. **Correct.**
- `diff_check.py`, `rank_mp.py`, `bugfind.py` divide by 1000 **unconditionally**. That shrinks the
  1.8 m human to a **1.8 mm speck**. At 3 m a 1.8 mm object subtends 0.0006 rad, an unresolved point
  source, so all `M` array steering vectors become identical and `Q` collapses to exact rank one.
  `PR = 1.00`, `lam1/trace = 0.9998`, top-8 eigen fractions `[0.9998, 9e-5, 8e-5, 0, 0, ...]`.
  **Artifact.**

`bugfind.py` divides *before* calling `build_G`, so both `build_G` and the inline copy receive the
same already-corrupted millimeter centroids. They agree because they are both wrong, which is
exactly the trap the orchestrator fell into: "the functions are identical, so the bug is elsewhere."
The bug was one layer up, in the input scaling, and only `rank_q.py` dodged it by luck of the
`> 10` guard.

Verbatim reproduction (`verified`):

```
rank_q.py   f=28 GHz M=256 : lam1/tr=0.2671  r90=5  r99=10  PR=5.15   <- meters, correct
diff_check  f=28 GHz M=256 : lam1/tr=0.9998            PR=1.000       <- mm speck, artifact
bugfind     f=28 GHz M=256 : G1==G2 (max diff 0.0), both PR=1.000     <- both fed the mm speck
```

Do not carry any `PR = 1.00`, "rank one plaza", or "excitation design space is a single point"
conclusion forward from the orchestrator's run. It came from a body the size of a grain of rice.

---

## 2. What the repo's settled position actually is, and the scars

Primary sources, in order of authority: `papers/coherent-exposure-operator/code/results/claims.json`
(the machine-checked claim registry, 74 claims, `verified: true`, generated 2026-06-01), the
assembled paper `main/main.md`, the monograph `theory/monograph_v2.tex`, and the most recent theory
note `report/defactorization_note.tex` (2026-06-18).

### 2.1 The algebraic rank (settled, never really in dispute)

`verified`, monograph `theory/monograph_v2.tex:4549`: `Q` "has rank <= min(M, 3 M_tri) where M_tri
is the number of mesh triangles." `Q = sum_t area_t * G_t^H G_t` is a sum of `n_tri` outer products,
each `G_t` is `(3, M)` so contributes rank <= 3. For any real body `3 * n_tri >> M`, so the
algebraic rank is `M` (generically full). Claim `Q_rank_bounded_by_M_ant` records rank <= `M = 64`.

Sub-point (`verified`, `theory/monograph_v2.tex:4268`, `fresnel_operator.py` docstring): the
**per-path** Fresnel operator `F_n` is 3x3 and **rank 2** (it projects the incident field onto the
TE/TM plane perpendicular to `k_hat` and kills the longitudinal component). The **per-triangle**
channel `G_t` accumulates many paths from many directions, so it reaches rank 3 (the three field
components). So "rank <= 3 per triangle" and "the Fresnel response is a 3x3 rank-2 operator" are both
in the repo and both correct, they just describe different objects (per-triangle vs per-path). The
brief conflated them slightly.

### 2.2 The effective rank (settled number, and the scar chronology)

The canonical number is **effective rank 8 at 90 percent of the trace**. The current abstract
(`main/main.md:112`, `verified`) reads: "The operator is low rank, effective rank eight at ninety
percent trace energy and ninety-seven percent off-diagonal." The paper's definition of effective
rank (`verified`, `code/claims/effective_rank.py:40`) is the **number of descending eigenvalues
whose cumulative sum first reaches a fraction of the trace**, `searchsorted(cumsum/trace, 0.90) + 1`.
That is *not* the participation ratio the orchestrator computed. Both are legitimate, they just give
different numbers, which is a large part of why this keeps getting muddled. See the metric appendix
in section 6.

The number **walked three times**, and the walk is the scar:

1. **JSAC era: "rank-3-to-4 empirical regime."** `verified`, `papers/jsac_archeology.md`. This was
   the earliest informal figure, from the synthetic plaza scenes.
2. **First paper abstract: "effective rank 5 at 90 percent trace, regardless of multipath density."**
   `verified`, quoted inside `code/claims/effective_rank.py:7-11` and the `claims.json` docstring for
   `effective_rank_at_90pct_trace_indoor`. This came from the structured synthetic cone (E1), where
   array steering happens to align with body geometry.
3. **2026-05-13 headline correction: "rank 8."** `verified`, `code/claims/effective_rank.py:6-12`,
   header comment "Headline correction (2026-05-13): the original paper abstract claims effective
   rank 5 ... Under ray-traced indoor factory multipath at 28 GHz, the median rank at 90% trace
   energy is 8 (not 5). The 'regardless of density' framing is unverified." The correction also
   explicitly kills the "regardless of density" claim.

So the number rose 3-4 -> 5 -> 8 monotonically **as the model got more realistic** (synthetic plaza
-> synthetic cone -> ray-traced factory). Richer, more diffuse multipath **raises** the effective
rank. Hold that thought, it matters for the physics in section 4.

### 2.3 The 99-percent scar, which the orchestrator half-rediscovered

`verified`, `claims.json` claim `effective_rank_at_99pct_trace_indoor_capped`, docstring in full:
"the per-trial sweep only stored the top-20 eigenvalues of Q ... In 55 of 90 trials, the cumulative
sum of the top 20 eigenvalues does NOT reach 99 percent of tr(Q) ... The true median rank at 99
percent trace energy is therefore at LEAST 21 (could be 22-40)."

This is the single most important qualifier on the headline. **"Effective rank 8" is true only at
the 90 percent threshold.** At 99 percent it is 21 to 40. The choice of 90 percent is a decision, not
a fact about `Q`. The orchestrator's `r99` column (which reported 5 to 10 on his toy, and which I
measured as median 23 on the real grid) was quietly measuring this larger number and nobody
reconciled it against the abstract's "8".

### 2.4 The two competing mechanism claims, and the note that reconciled them

The paper carries **two different explanations** for why the effective rank is low, and they point in
opposite directions:

- `effective_rank_saturates_at_body_aperture_modes` (`main/main.md:823-827`, `verified`): "the
  practical dimension of Q is set by the body aperture seen through the array, **not by multipath
  richness**."
- `Q_effective_rank_bounded_by_N_clusters` (`main/main.md:924-926`, `verified`): the number of modes
  "is bounded by the count of distinct arrival clusters." That **is** multipath richness.

These read as a contradiction. The reconciliation is the most recent theory document,
`report/defactorization_note.tex:263-285` (2026-06-18), and it is the deepest and most correct
statement in the whole repo (`verified`, quoted):

> "It is tempting to read the paper's rank-8 as a small intrinsic mode count of the body. *That
> reading is wrong* ... the body kernel T is intrinsically *high* rank, its space-bandwidth product
> is `A_Sigma / lambda^2 ~ 7e3` at 28 GHz ... The rank-8 is not the body, it is what survives after
> the high-rank body kernel is projected through the *finite angular aperture* of the array-plus-
> scene ... rank is set by the illumination aperture, not by the phantom."

So the settled mechanism is: the body has roughly `A_Sigma / lambda^2 ~ 7000` intrinsic surface
degrees of freedom (speckle modes). The array and scene present a finite angular aperture. The
effective rank is the number of those body modes the aperture can resolve. The "body aperture" and
"cluster count" claims are two faces of the same projection, and the earlier `main.md` phrasings are
each half of it. This is, in all but name, the Bucci-Franceschetti "spatial bandwidth of scattered
fields" count and the Landau-Pollak 2WT theorem. The repo **does not cite either** (`verified`,
zero matches for `Landau|Bucci|Pollak|Franceschetti` in the monograph or the paper). If the closed
form is written down and attributed, that is a result, not a nuisance. See section 4.4.

### 2.5 Other retracted-claim scars, for completeness

The honesty ratchet left more scars around this exact area (`verified`, all in the claim code):

- `mscaling_gep_drops_with_M` **retracted** (`m_scaling.py:47`): measured at an unusable zero-signal
  operating point. Replaced by the 50-percent-signal version.
- `mscaling_diag_dominance_shrinks_with_M` **retracted 2026-05-13** (`m_scaling.py:111`): the metric
  `diag/(diag+off)` mechanically scales as `1/N`, so the "finding" was baked into the metric.
- `Q_diag_frobenius_fraction_below_10pct` "replaces the previous (broken) L1 ratio that scaled as
  1/N mechanically" (`effective_rank.py:104`).

Pattern worth internalizing: **every prior mistake here was a scale- or threshold-dependent metric
mistaken for a physical law.** The orchestrator's `PR = 1.00` is the newest instance.

---

## 3. Settling it numerically myself, on real ray-traced operators

The repo ships a grid of **real** ray-traced `Q` operators at `data/studio/qop/*.npz` (352 files,
provenance string `studio_precompute qoperator ... Q=sum_t area_t G_t^H G_t`, built by the full
AEGIS pipeline: DiffeRT/Sionna rays -> `body_channel` with real Fresnel and tissue depth coupling ->
`Q`). Meshes {duke, ella, eartha, thelonious}, arrays 8x8 (M=64) and 16x16 (M=256), frequencies
{8, 10, 12, 15, 20, 28} GHz, LOS and NLOS, seeded. This is a real `G_tilde`, not the orchestrator's
toy. Code I ran: `spinoff/differentiability/agent_reports/_rankq_studio.py`.

**Grand summary over 336 real ray-traced trials (`verified`):**

| metric | median | p10 | p90 | min | max |
|---|---|---|---|---|---|
| r90 (eigs to 90% trace) | **7** | 5 | 11 | 5 | 12 |
| r99 (eigs to 99% trace) | **23** | 18 | 32 | 16 | 34 |
| participation ratio `(sum l)^2/sum l^2` | **2.64** | 2.32 | 4.12 | 2.15 | 5.90 |
| stable rank `trace/lam_max` | 1.67 | 1.56 | 2.87 | 1.48 | 3.72 |
| top mode share `lam_max/trace` | **0.60** | 0.35 | 0.64 | 0.27 | 0.67 |
| numerical rank (> 1e-6 lam_max) | 66 | 53 | 90 | 49 | 96 |

Read this against the paper. My r90 median 7 matches the paper's 8 (mine is corridor LOS/NLOS, the
paper's 8 is indoor factory, both land at 5 to 13). My r99 median 23 **independently confirms the
99-percent scar** (paper: "at least 21"). The single-mode share 0.60 is a touch higher than the
paper's 0.45 because the corridor is more LOS-concentrated than the factory. Every settled number
reproduces.

A concrete spectrum, so "effective rank" is not abstract (`verified`, duke LOS bs8 28 GHz):

```
top-12 eigenvalue fractions: [0.562 0.126 0.109 0.078 0.031 0.018 0.014 0.013 0.008 0.008 0.006 0.004]
1 mode = 56%,  4 modes = 87%,  r90 = 5,  r99 = 19,  r99.9 = 36
```

One mode carries more than half. Four carry 87 percent. Then a long, shallow tail of small but
nonzero modes runs out to `r99.9 = 36`. That tail is the "high-rank body kernel projected through
the aperture" from section 2.4. The algebraic rank is effectively full (numerical rank 49 to 96 out
of 64 to 256, limited by numerical floor, not by a hard cutoff).

**Caveat (`verified`).** `_channel.py` warns the on-disk channel packs are float16 and "do NOT
preserve the tiny / null-space eigenvalues." The `qop` packs store `Q` as complex128 but were built
from that pipeline, so I trust the top of the spectrum (r90, r99, PR, top1, all robust) and I do
**not** lean on the studio grid for the smallest eigenvalues. The algebraic-rank statement rests on
the monograph bound and on my own full-precision build in section 4.1, not on the grid.

---

## 4. The physics, tested with the real machinery, claim by claim

Code: `spinoff/differentiability/agent_reports/_rankq_physics.py`, which drives the **real**
`aegis.coherent.body_channel.compute_body_channel` (real Fresnel `t_s`/`t_p`, real Cole-Cole skin
`n_tilde` and `sigma`, real depth coupling) fed by the paper's own far-field cluster path model
(`synthetic_paths_for_target` + `expand_paths_to_array`), on the real duke mesh (2000 triangles).
Illumination lit fraction 0.52 confirms the array actually sees the body.

### 4.1 A single far-field cluster gives exactly rank one (`verified`)

This is the algebraic fact behind the paper's synthetic-cone numbers, and it needs to be stated so
nobody over-reads them.

```
E1: rank(Q) vs number of clusters   (16x16 array, lambda/2 at 28 GHz, D=5m, 28 GHz)
 n_clusters   numrank(>1e-6)   r99    PR    top1
     1              1            1    1.00   1.000   <- exactly rank one
     2              2            2    1.12   0.941
     4              4            4    1.45   0.816
     8              8            4    2.13   0.637
    16             14            7    3.39   0.454
```

In AEGIS's far-field model every element shares a cluster's direction `k_hat` and differs only by the
steering phase `exp(i k0 k_hat . offset_j)`. So for one cluster `G_t = v_t a^H` (a per-triangle
3-vector times one shared M-dimensional steering vector), and `Q = (sum_t area_t |v_t|^2) a a^H` is
**exactly rank one** (`inferred`, derivation, confirmed by the table). With `C` clusters,
`rank(Q) <= C` exactly, because `Q = A M_gram A^H` with `A` being `M x C`. This is the algebraic
content of `Q_effective_rank_bounded_by_N_clusters`. **Consequence for reading the paper:** the
synthetic-cone "rank ~ 5" was partly an artifact of using few clusters in a shared-direction model,
which is exactly why the ray-traced factory number came out higher (8) once every path carried its
own direction. The real grid in section 3 has hundreds of distinct directions and never collapses
like this.

### 4.2 Frequency invariance at half-wavelength spacing (`verified`, the orchestrator's cleanest claim)

```
E2: lambda/2-scaled array (aperture shrinks with lambda), 8 clusters, D=5m, tissue fixed at 28GHz
 f_GHz   aperture_cm   numrank   r90   r99    PR    top1
   8        28.11         8        3     4    2.09   0.645
  15        14.99         8        3     4    2.17   0.625
  28         8.03         8        3     4    2.13   0.637
```

Flat across a 3.5x frequency range while the aperture shrinks from 28 to 8 cm. **Confirmed.** When
the array is half-wavelength spaced the physical aperture scales as `lambda`, so the aperture in
wavelengths is fixed, so the number of resolvable body modes is fixed. This is the falsifiable claim
and it held with the real body channel.

### 4.3 The counterfactual: fixed physical aperture (`verified`)

```
E3: fixed physical aperture (lambda/2 at 28 GHz held fixed), 8 clusters, D=5m
 f_GHz   numrank   r90   r99    PR    top1
   8        6        2     2    1.24   0.894
  15        7        2     3    1.55   0.789
  28        8        3     4    2.13   0.637
```

Here the effective rank **grows** with frequency (r99 2 -> 4, PR 1.24 -> 2.13), because a fixed
aperture spans more wavelengths at higher frequency and resolves more modes. The studio grid shows
the same direction but much weaker (r99 29 -> 32 over 8 to 28 GHz on bs16 LOS), because the corridor
multipath is angularly concentrated, so the *scene* angular spread binds before the array resolution
does. So the honest statement of the mechanism is: **effective rank = min(array-resolvable modes,
scene angular DoF, algebraic bound).** Fixed aperture plus rich angular spread -> grows with
frequency. Fixed aperture plus concentrated LOS -> nearly flat. Half-wavelength spacing -> invariant
regardless. The frequency invariance is the clean special case, and it is real.

### 4.4 Aperture up, oversampling flat (`verified`, the M question, done right)

The orchestrator's "does not grow with M once M oversamples the aperture" is correct **only if you
hold the aperture fixed**. The repo's own M-sweep (`main.md:1352`) grows the aperture with M at
half-wavelength spacing and sees the effective rank rise (rank/element ratio 0.25 -> 0.04, so eff
rank ~4 at M=16 to ~10 at M=256). These are two different experiments. I ran both:

```
E5a: half-wavelength (M grows AND aperture grows), 8 clusters, 28 GHz
 M_side   M     aperture_cm   r99    PR
    4     16       1.61        2    1.21
    8     64       3.75        3    1.51
   16    256       8.03        4    2.13
   24    576      12.31        5    2.57      <- grows with aperture

E5b: oversample a FIXED aperture (aperture = 16*lambda/2 fixed, elements packed denser), 28 GHz
 M_side   M    spacing/lambda   r99    PR
    8     64      1.143          5    2.28
   16    256     0.533          5    2.20
   24    576     0.348          5    2.18
   32   1024     0.258          5    2.17      <- dead flat
```

**Both confirmed.** Aperture growth adds modes. Packing more elements into a fixed aperture (going
sub-Nyquist) adds **nothing** to the effective rank. So "adding elements adds no exposure-relevant
degrees of freedom" is true for the oversampling axis and false for the aperture-growth axis. The
repo's `mscaling_q_lambda_max_M_independent` (lam_max is M-independent) and
`mscaling_mrt_pabs_roughly_M_independent` are the related settled claims (`verified`).

### 4.5 Distance shrinks the rank, in the near-field regime only (`verified`, with a caveat)

AEGIS's far-field cluster model fixes the cluster cone angle independent of distance, so its
effective rank is distance-invariant (I checked: r99 = 4 flat from D = 2 to 20 m). That is a property
of the model, not of the world. In a near-field / geometric illumination where the body's subtended
angle actually shrinks as `1/D`, the rank falls. Code:
`spinoff/differentiability/agent_reports/_rankq_nearfield_dist.py` (toy near-field spherical-wave
channel, correct units, no Fresnel, so labelled as a geometry-isolating probe not AEGIS's model):

```
 D_m   body_subtend_deg   r90   r99    PR    top1
 1.5        62.1           12    20   10.54  0.147
 3.0        33.5            5    10    5.11  0.262
 6.0        17.1            3     5    2.71  0.492
12.0         8.6            2     3    1.59  0.764
24.0         4.3            1     2    1.16  0.926
```

The effective rank tracks the subtended angle almost linearly and collapses toward one as the body
becomes a point. **Confirmed** that distance reduces rank whenever it reduces the body's angular
size. This is the `1/d^2` in the orchestrator's `A_array * A_body / (lambda d)^2` count (here the
body is tall and thin so it reads closer to `1/d`). Caveat: this effect is invisible in AEGIS's
default far-field-per-cluster synthetic scenes, so anyone quoting distance dependence must say which
illumination model they mean.

### 4.6 Angular spread raises the rank (`verified`)

LOS vs NLOS on the real grid, 28 GHz (`_rankq_studio.py`):

```
 bs 8  LOS : r90=5.5  r99=21.5  PR=2.76  top1=0.578
 bs 8  NLOS: r90=6.0  r99=19.0  PR=4.70  top1=0.309
 bs16  LOS : r90=8.5  r99=32.0  PR=2.99  top1=0.559
 bs16  NLOS: r90=11.0 r99=28.0  PR=5.85  top1=0.273
```

NLOS (richer angular spread) roughly **doubles the participation ratio** and roughly halves the
dominant-mode share. This is the same direction as the 5 -> 8 abstract correction and as E1 (more
clusters -> higher rank). **Confirmed:** more multipath / wider angular spread -> higher effective
rank. Note this directly contradicts the literal wording of
`effective_rank_saturates_at_body_aperture_modes` ("not by multipath richness"), and the
defactorization note is right to have reframed it.

### 4.7 Scorecard on the orchestrator's three sub-claims

| sub-claim | verdict | evidence |
|---|---|---|
| Frequency invariant at half-wavelength spacing | **confirmed** | E2, r99 flat 8-28 GHz |
| Grows with aperture and with angular spread, shrinks with distance | **confirmed, with model caveat** | E5a, E1, LOS/NLOS, near-field distance probe. Distance effect absent in far-field model |
| Does not grow with M once M oversamples a fixed aperture | **confirmed** | E5b, dead flat M=64 to 1024 |

The underlying formula `eff_rank ~ A_array * A_body_projected / (lambda d)^2` is the **array
resolution ceiling** (a Landau-Pollak / Bucci count). The measured effective rank is the minimum of
that ceiling, the scene's own angular DoF, and the algebraic bound `M`. In the paper's concentrated
scenes the scene binds, which is why the fixed-aperture frequency growth is weak. The formula is a
good upper bound and a correct scaling law, not an equality in every regime.

---

## 5. Why anyone cares: the number cuts both ways

The brief asked for the consequence for two ideas. Conditioned on what I measured (effective rank 7
to 8 at 90 percent trace, about 23 at 99 percent, single mode 45 to 60 percent, all `<< M`):

### 5.1 Excitation-side differentiability is decorative for the exposure objective (downgrade)

`inferred`, and I stand behind it. The worst-case exposure is `lambda_max(Q)` and its optimal
precoder is the top eigenvector, closed form (`eigendecompose_Q`, and the eigenvalue-lift corollary
`main.md:794`). The exposure-constrained beamformer is
`x* ~ (lambda Q + nu I)^{-1} h*`, also closed form. When one mode holds half the trace and eight
hold 90 percent, a gradient walk over a 512-real-dimensional precoder is optimizing an objective that
lives in an 8-to-23-dimensional subspace. The brief's mechanism (a) needs a genuinely high-
dimensional design vector, and the exposure operator does not provide one. So for the plain exposure
objective, autodiff on `x` buys essentially nothing over the eigen-solution. Honest qualifier: the
**per-element-power-constrained** variant is not solved by a single eigenvector, it needs an SDP, and
there autodiff has marginal value, but Xu et al. 2018 already published that SDP (per the brief's
section 5), so even the marginal case is not novel. Net: excitation-side differentiability is
decorative to marginal. Do not build the business case on it.

Caveat that keeps this honest: "8" is the 90-percent number. If a use case needs 99-percent-accurate
exposure control, the design subspace is ~23-dimensional, still `<< 512` but no longer trivially
low. The closed-form-optimum argument is strongest for the whole-body worst case (rank effectively
one to a few) and weakens as you demand tail accuracy.

### 5.2 Low-rank Q underwrites compressed exposure sensing (upgrade)

`inferred`, and this is the mirror image. `generalization_map.md` section 7.5 (`verified`): "Low-rank
`Q_in` = compressed exposure sensing. If `rank(Q_in) << M` (a one-afternoon measurement), the body-
array channel is estimable from few pilots. Do this test, it underwrites several ideas." I did the
test. `rank(Q) << M` is confirmed: 8 pilots recover 90 percent of the operator, ~23 recover 99
percent, against `M = 256`. So a **self-calibrating compliance array** that estimates its own `Q` in
situ from a handful of pilots is on solid physical ground. The number that kills 5.1 is the number
that enables this. It is a genuine hardware/firmware IP direction ("the reciprocal self-calibrating
compliance array" in 7.5) with a concrete buyer (base-station self-compliance) and it depends on the
low rank *essentially*.

Same qualifier the other way: "few pilots" means 8 for a 90-percent-faithful `Q` and ~23 for 99
percent. Both are small, so the idea survives, but a compliance certificate that needs the tail would
need the larger pilot budget.

### 5.3 The clean statement

The effective rank is the pivot for both ideas and it decides them oppositely. It is small enough
(single digits at 90 percent trace) that closed-form beats gradients on the excitation, and small
enough (tens at 99 percent, still `<< M`) that the channel is cheaply estimable. If a realistic
diffuse-multipath deployment pushed the effective rank into the many-tens or hundreds, both
conclusions would flip: differentiable excitation design would regain value and compressed sensing
would lose it. I did not find that regime in the shipped scenes (worst case r99 = 34 on the grid,
r99 = 40 as the paper's upper bound), but I also did not test a genuinely rich outdoor macro scene,
so mark the "stays low in all deployments" extrapolation as **could-not-check**.

---

## 6. Appendix: the metric definitions, because the confusion lives here

Four different "effective rank" numbers are floating around the repo and this study. They are all
defined on the descending nonnegative eigenvalue spectrum `l_1 >= l_2 >= ... >= 0` of `Q`.

| name | formula | duke LOS bs8 28 GHz | what it emphasizes |
|---|---|---|---|
| cumulative-trace rank at p | `#{smallest k : sum_{i<=k} l_i >= p * trace}` | r90 = 5, r99 = 19 | how many modes to capture p of the energy. **The paper's number.** |
| participation ratio | `(sum l)^2 / sum l^2` | 2.65 | effective count weighted by `l^2`, dominated by the top mode. **The orchestrator's number.** |
| stable rank | `trace / lam_max` | ~1.7 | how far from pure rank one |
| numerical / algebraic rank | `#{l_i > tol * lam_max}` | 54 (tol 1e-6) | full-precision count, `-> M` |

The participation ratio is always smaller than the 90-percent cumulative rank for a skewed spectrum,
which is exactly why the orchestrator's `PR = 5.15` and the paper's `r90 = 8` are both correct and
look contradictory. **Any statement of "the effective rank is N" that does not name the metric and,
for the cumulative one, the threshold, is not falsifiable.** That, more than any single arithmetic
slip, is why this question has flip-flopped in the repo.

## 7. Files and code

- `spinoff/differentiability/agent_reports/_rankq_studio.py` runs the real ray-traced grid (section 3).
- `spinoff/differentiability/agent_reports/_rankq_physics.py` runs the controlled physics with the
  real `compute_body_channel` (section 4.1 to 4.4, 4.6).
- `spinoff/differentiability/agent_reports/_rankq_nearfield_dist.py` runs the near-field distance
  probe (section 4.5).
- The orchestrator's buggy drivers: `/tmp/claude-1001/-home-user-aegis/09a8d401-c47f-427d-804a-48196a28a48a/scratchpad/{rank_q,rank_mp,diff_check,bugfind}.py`.
- Primary repo sources: `papers/coherent-exposure-operator/code/results/claims.json`,
  `.../main/main.md`, `.../report/defactorization_note.tex`, `theory/monograph_v2.tex`,
  `src/aegis/coherent/{exposure_operator,body_channel,fresnel_operator}.py`,
  `spinoff/before-tom-meeting/generalization_map.md`.

`NEEDS_CONTEXT`: none. Everything needed was in the repo. The one thing I could not settle is whether
a rich outdoor macro-cell scene keeps the effective rank low (section 5.3), because no such scene is
shipped. If that matters for the business case, the ask would be one Sionna RT macro scene at 8 and
28 GHz with a body at 30 to 100 m, then rerun `_rankq_studio.py` against its `Q`.
