# JSAC v5 critical review

Reviewer perspective: a JSAC SI guest editor or a careful reviewer who has spent
two evenings on the math, the figures, and a partial code spot-check.
References below are to `paper_jsac_v5.tex` line numbers and to artefacts in
`JSAC/code/experiments/plaza_run/`.

---

## 5 serious issues

### 1. The main proposition is a regime-characterisation in disguise, and the body twin has structurally shrunk to "supply one scalar per slot"

Proposition 1 (`prop:projection-optimality`, lines 755–799) says: if α²·SINR_min^ZF
≥ 2^S_max − 1, then α·W_ZF attains the K-stream MCS upper bound. The proof is
five lines of arithmetic on a per-stream rate clip. The non-trivial content
sits entirely in the *hypothesis*, which is an empirical claim about the
deployed regime.

Stripped of decoration, the result says: **in a regime where ZF saturates the
rate cap with SINR headroom, any feasible precoder also saturates the cap.**
That is regime characterisation, not an algorithmic theorem. The post-hoc
admission at lines 822–827 ("does not single out projected ZF as the unique
global optimum: any K-stream method that saturates the cap and meets the
per-body constraints is co-optimal") is honest, but it deflates the headline.

The body twin's role inside this result is to compute one scalar
α = √(η_S · min_u L^(u)/P_abs^(u)) per slot. The evolution log
(`paper_jsac_evolution.md` §1.2) is candid about this:

> v5: twin is a per-body absorbed-power estimator. It computes P_abs^(u) so
> the projection can set α. That's it.

The paper itself never makes this admission. It still positions the twin as
the central contribution (abstract lines 105–161; intro contribution list
lines 218–264; conclusion §VIII). A reviewer who reads carefully will see
that under the operational claim, the entire twin pipeline (path dictionary,
tiered telemetry, virtual IMU, CSI calibration) reduces to "supply a per-body
P_abs estimate", and ask: why do we need the elaborate construction when a
worst-case Cauchy envelope on the detected set would do almost as well at
sub-percent cost?

This is the central tension. Either:
- (a) acknowledge it directly and reframe the proposition as
  "the twin is what enables the one-line precoder", quantifying the α-vs-WC
  gap (currently nowhere), or
- (b) demonstrate a regime where the per-body, per-pose Q is strictly
  necessary — none of the four regimes in Table II witness this.

### 2. The "0.0% violation by construction" headline relies on the oracle variant; the deployable numbers are 1.2–2.4%

The abstract (lines 134–137) leads with "projected ZF holds violations at
0.0% across all detected bodies at 74.0 Gbps... by feasibility-by-construction."
Table II (lines 1108–1136) shows this is true only for **ZF + proj (oracle)**,
which sets α against the ground-truth Q on the *full population including
undetected tier-C bystanders*. The deployable variant — what a real BS would
run, which sees only the detected set — is at 1.2% (K=25), 0.7% (K=10),
0.05% (K=5), 0.3% (bystander-binding).

The paper does explain the mechanism (sensing-pipeline floor, lines 1173–1199)
and reports both rows. But the abstract and intro both quote the 0.0% number
without the qualifier "on the detected set". A reader who skims the abstract
walks away with "ZF + proj is perfectly compliant by construction", which is
not true under deployable inputs. This is a classic AI-writing tell:
the strongest number is foregrounded, the qualifier appears later in the
section that explains it.

The fix is small: replace "0.0% across all detected bodies" with
"0.0% on the detected set, 1.2% aggregate" in the abstract, and likewise
in §I.

### 3. The multi-seed cross-check is N = 2; the "statistically tied" claim cannot be supported

Lines 1081–1087 disclose that seed 42 has ZF+proj at 1.21% / dual ascent at
2.39% (proj wins), while seed 1729 reverses to 0.58% / 0.32% (dual ascent
wins). The paper concludes "the two methods are therefore statistically tied
on aggregate compliance" with σ_viol ≈ 1.5 pp on **two-seed estimates**.

A pp-scale standard deviation from N=2 has an enormous confidence interval.
The honest version of this sentence is "we cannot distinguish the two
methods at this seed count"; "statistically tied" implies a hypothesis test
that has not been run. Table II caption (lines 1077–1080) still says
"$1.05\times$ to $19\times$ on violation rate", which is the seed-42 ratio
and is undermined by the same disclosure.

The fix is to run N ≥ 10 seeds at K=25 and report distributions, not point
estimates. This is a one-night experiment on the existing infrastructure.
Without it the head-to-head result is anecdotal at the binding regime.

### 4. `rank_cdf.pdf` is a spectrum plot, not the CDF the caption describes

The figure (`rank_cdf.png`, viewed) plots λ_k/λ_1 vs eigenvalue index k for
the median plus 10–90% band. Title on the figure: "Spectrum of Q^(u) on
Thelonious, 20 bodies, 20-80 m range, ±60° azimuth."

The paper caption (lines 1005–1013, `\label{fig:rank-cdf}`) says
"Effective rank of Q^(u) at trace fractions ε ∈ {10^-1, 10^-2, 10^-3} over
20 Thelonious bodies... Median is 3 to 4 at ε = 10^-2 across both path
models." The reader is told to expect a CDF over effective rank values; what
is actually rendered is a per-eigenvalue magnitude curve. The "rank 3–4 at
ε = 10^-2" claim is implicitly readable from the plot (find smallest r such
that Σ_{k>r} λ_k/Σλ_k ≤ ε), but that requires an integral the figure does
not perform.

Inconsistencies between figure-as-rendered and figure-as-described are red
flags for AI-assisted writing where the description was generated against an
expected output rather than the actual output. Either regenerate as a CDF
of the effective-rank random variable across the 20-body sample, or rewrite
the caption to describe a spectrum.

### 5. The 700× wall-clock comparison is hardware-asymmetric and inflates the gap

The headline ratio (lines 287–291, 829–831, 1196–1197, 1601–1603) is
"projected ZF ~0.5 ms vs dual ascent ~350 ms, 700× advantage". Table I
(lines 645–651) lists both numbers honestly: the dual ascent is ~350 ms on
CPU NumPy and ~25 ms on a single GPU under JAX vmap. The 700× number is
CPU vs CPU; the JAX-on-GPU number gives ~50×.

The production runs (e.g. `outputs/.../bind3v_v8_imu4.json`) ran with
JAX on GPU at ~131 ms total precoder time per slot for *all six precoders*
combined, not 350 ms for the dual ascent alone. The CPU 350 ms number is
representative of *one configuration of the dual ascent that was deliberately
not the production setting*, against the projected ZF number which IS the
production setting. A reviewer who looks at the cadence JSON will spot this.

The fix is a one-line apples-to-apples comparison: run both methods on the
same backend (JAX vmap on GPU is the deployable setting for both, since both
benefit from low-rank batched LAPACK); report the ratio there; and segregate
the CPU-NumPy comparison as a separate row labelled "single-thread server
without GPU." The 700× number doesn't have to disappear — it just needs the
qualifier "on CPU NumPy" front-and-centre, not buried in Table I.

---

## 5 ways to improve the paper

### 1. Restore a closed-loop / DTN / application-aware title and add one paragraph of SI framing

Per `paper_jsac_evolution.md` §4, this is the weakest SI fit in the lineage.
The current title — "Body Digital Twins for Compliance-Aware mmWave Downlink:
Per-Slot Primal Projection under European Reference Levels" — buries the
twin in the first half, leads with "Compliance-Aware" (a SP-journal phrase),
and the subtitle is the *algorithm name*, not the *contribution*.

The v0b/v2 title pattern that maps cleanly to the SI:

> "Closed-Loop Body Digital Twins for Application-Aware mmWave Downlink:
>  Compliance under European Reference Levels"

Plus one paragraph in §I that says explicitly: "the JSAC SI thesis is that
future networks are not the thing being twinned — they are the adaptive
substrate over which twins of the application run a closed control loop.
This paper addresses an application that has been absent from the DTN
literature: the human body in the coverage cell." This is a 2-sentence
addition. The rest of the paper does not need to change.

### 2. Reframe Proposition 1 as a twin-enabling result

Current statement: "any K-stream precoder satisfying the SINR-margin condition
and the per-body caps attains the K-stream upper bound."

Proposed reframe: "Under the deployable MCS-cap rate model and the empirical
SINR-margin condition, the body twin's per-slot
{P_abs^(u)}_{u ∈ A ∪ B ∪ C-detected} estimate is what makes the closed-form
projection feasible at every slot. Without the twin, the only feasible
fallback is the unconditional Cauchy envelope of `app:cauchy`, which is
breached on 49–70% of unconstrained precoders and on which uniform back-off
costs ~6 dB on α (i.e. ~6 dB on every served stream's SINR), losing the cap
saturation."

This requires one new measurement: the α-vs-WC quantitative gap. With η_bar
= 0.5 in WC and the actual ρ ∈ [1, 20] under projected ZF, the WC fallback
divides the precoder by √(2 · max-projected-area-ratio). The 6 dB number
should be measured rather than asserted; the figure data already exists in
the WC column of Table II (sum-rate degradation from MCS-cap to whatever WC
hits). This frames the body twin as load-bearing rather than decorative.

### 3. Cut the IMU subsection in half

§II.C (Virtual-IMU pose estimator, lines 542–590) plus §VI.D (Pose-information
triage, lines 1206–1342) plus the imu_sweep figure together account for ~250
lines of paper. Per the proposition, IMU pose modulates compliance at
sub-percent scale. The IMU-vs-T-pose gap is the *only* remaining degree of
freedom the twin's pose information buys (paper's own admission, lines
1591–1594).

Trim:
- Move §II.C's full estimator equations to an appendix or to the companion
  paper (`paper_jsac_companion.tex` already exists).
- Compress §VI.D to one paragraph + the pose_info figure.
- Drop the imu_sweep figure entirely or move to supplementary; the table
  values cover the same ground.

That is ~150 lines saved. The narrative loses nothing because the headline
result (oracle/IMU/T-pose all sub-percent at the MCS cap) is the same in
one paragraph as in two pages.

### 4. Run N ≥ 10 seeds at K = 25 and replace the "statistically tied" claim with an actual distribution

The infrastructure runs in ~8 minutes per seed (`v8_imu4` config, GPU JAX).
Ten seeds ≈ 80 min wall-clock. Report mean ± std on violation rate per
algorithm; produce a small table or a swarm plot. This converts the head-to-head
from "two anecdotes" to "an empirical distribution at a useful sample size",
and lets the paper make a defensible "statistically equivalent" claim
backed by a t-test or Mann-Whitney.

This is the single change with the largest credibility return per hour
of compute.

### 5. Demonstrate the K → M regime where the proposition fails

The discussion limitation 6 (lines 1639–1651) admits this regime is where
the dual ascent earns its keep algorithmically. The paper then runs a K=50
stress test on the same M=64 panel and reports the SINR margin still
holds at K/M=0.78, with both methods saturating the MCS sum-cap.

A reviewer reading this concludes: the regime where the dual ascent matters
was tested and projected ZF still won. That is *not* the right reading: the
K=50 test had **no non-served bodies**, so the SINR margin was preserved by
removing the binding constraints rather than by the algorithm handling them.

Fix: add one row to Table II at K = 40 served + 25 bystanders on M = 64
(K + B = 65 ≈ M) on the same plaza geometry. Either:
- (a) projected ZF still wins, in which case the proposition is robust and
  the paper's scope claim strengthens, or
- (b) the dual ascent wins, which is the boundary the paper currently only
  asserts, and gives a real reason to keep the dual ascent in the appendix.

Either outcome strengthens the paper. The current "K=50 stress test"
language reads as a stress test that wasn't actually stressful.

---

## Smaller cleanups (not in the top 5 but worth a pass)

- `phy.py` line 4 docstring still says "MCS28"; the constant comment on
  line 17 says "MCS=27". Inconsistent with the v5 paper's MCS27 correction.
- `tier_c.SensingConfig` defaults to `tx_power_dbm = 30.0`. Production runs
  use 43 dBm for the precoder. Either the radar link budget paragraph
  (lines 1418–1429) needs an "ISAC subset" qualifier explaining the power
  asymmetry, or the SensingConfig default should be 43 dBm with the link
  budget reworked.
- Spatial heatmap caption (lines 1366–1376) describes a white contour at
  P_abs/L_RL = 1 in *both* panels. Only the left (ZF unconstrained) panel
  has the contour visible; the right (ZF + proj) panel has all values
  below 1 so no contour is drawn.
- Abstract line 137 reads "$74.0$ Gbps, the MCS27 sum-cap, by
  feasibility-by-construction" — feasibility-by-construction applies to the
  per-body caps, not to the rate. Reorder: "0.0% violations on detected
  bodies by feasibility-by-construction, at 74.0 Gbps, the MCS27 sum-cap".
- The bystander-binding regime in `bystander_binding.py` uses 45 bodies
  (10A + 25B + 10C), not 50. Table II row label says "Bystander-binding"
  without specifying the count. A reader who runs the code will find the
  N=50 vs N=45 difference and wonder. One footnote on Table II resolves it.

---

## One-line recommendation

The paper is technically the strongest in the v0a → v5 lineage and the
experiments are honest. It needs (a) a 50-line title-and-framing rewrite to
reach the SI, (b) an N=10 multi-seed pass to defend the head-to-head, and
(c) one paragraph that admits the body twin's role has shrunk to a scalar
estimator and frames that admission as the result rather than as something
to hide. The math will hold under any reviewer pressure; the framing as
written will not.
