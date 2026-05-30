# JSAC2 v3 audit synthesis (2026-05-11)

Compiled from 7 parallel audit agents. Per-agent reports in this directory.

The user's directive was: substantive issues that distort or invalidate results.
Minor stylistic/edge-case issues were filtered out.

## Verdict in one paragraph

The qualitative storyline (body-mediated channel matters, pose moves help, IMU
drift is tolerable, exposure stays well below ICNIRP) is plausible. But almost
every quantitative claim in the paper is built on top of one or more of: a
broken Fresnel coefficient that suppresses h_body 16-22 dB on real scenes, a
mis-unpacked Sionna `paths.cir()` return that destroys carrier phase across
paths, a "naturalness ball" framing that excludes every real walking pose
ever measured, a "brute-force optimum" with N=100 random shots in 32-D, an
MCS-cap-saturated baselines table, several proofs whose error bounds are
wrong by 6-9x, and a calibration figure that is literally from a different
manuscript on a different problem. The headline numbers in the abstract
need to be re-derived after these are fixed; under the current code they do
not measure what the paper says they measure.

## Showstoppers (publication-blocking)

### S1. Kirchhoff `K = (r_s + r_p)/2` vanishes at normal incidence

`kirchhoff.py:260` and `kirchhoff_jax.py:74` compute the per-triangle
reflection coefficient as `r0 = 0.5*(r_s + r_p)`. Under the standard Fresnel
sign convention used in `aegis.tissue.fresnel`, r_s and r_p have OPPOSITE
signs at normal incidence, so r0 is exactly 0 at θ=0° and tiny near it:

| θ    | code's r0 | paper's √(1-T0) |
|------|-----------|------------------|
| 0°   | 0.000     | 0.681            |
| 30°  | 0.041     | 0.681            |
| 60°  | 0.200     | 0.681            |
| 80°  | 0.515     | 0.681            |

K vanishes exactly where the body channel has its biggest contributions
(specularly aligned triangles).

**Empirical impact** (verified on real scenes by audit agent):
- Munich Scene 0 (LOS):  ‖h_body‖ underestimated by 16 dB; cascaded SINR
  shifts by 5 dB (33.2 → 37.9 with proper PO).
- Munich Scene 15 (NLOS): ‖h_body‖ underestimated by 22 dB; cascaded SINR
  shifts by 3.2 dB.
- Sphere body (analytical PO): underestimate is 38 dB.
- Flat dielectric mirror (analytical image-source): code returns numerical
  noise (1e-17) instead of 0.6.

**The whole numerical study is on a wrong Lambda_KH operator.** The K_99
SVD basis is dominated by edge-on triangles instead of specular ones. The
8.6 dB "body-as-reflector rescue" on scene 17 is computed under a kernel
that suppresses the reflector. Calibration absorbs constant scaling, but
this bug is angle-dependent so calibration only partially compensates.

**Fix.** Use `K = -2 j k_0 sqrt(1 - T_0)` for the pseudo-Brewster reduction
(or the polarization-aware Fresnel operator already implemented in
`src/aegis/coherent/_fast.py` lines 81-103). Re-run all 18 Munich scenes.
Add a unit test against the analytical image-source result on a flat
dielectric.

### S2. Sionna `paths.cir()` is mis-unpacked

`munich_trace.py:104-108` reads `np.asarray(a_raw)[0]` as `a_theta` and `[1]`
as `a_phi`. In Sionna v2.0.1 with `out_type='drjit'`, the return is
`(re_TensorXf, im_TensorXf)` — REAL and IMAGINARY parts of the same complex
V-pol scalar coefficient, not theta/phi polarization components.

Confirmed by direct comparison: `paths.cir(out_type='numpy')` returns
complex64; `np.asarray(paths.cir())[0] == .real`, `[1] == .imag`. Munich
`body_amp_path` is identically `1+0j` (mean=1.0, std=7.8e-17) and
`body_psi_path` is purely real per path.

**Impact.** Carrier phase is destroyed across paths. Polarization is
randomly split between e_theta and e_phi instead of being along V-pol.
Magnitudes are preserved (|psi|² = Re² + Im²), so SINR magnitudes are in
the right ballpark, but coherent superposition across paths — which the
RIHB story requires — is broken.

**Fix.** Read complex CIR from Sionna (`out_type='numpy'` or unpack the
drjit tuple as Re + jIm), then form `psi = a_complex * e_theta` if
V-pol-only, or compute the full polarization vector from the trace.
Re-trace and re-run the 18 Munich scenes.

## Serious issues (would block careful reviewers)

### T1. Pseudo-Brewster collapse claim is misstated

Paper Sec III.B (line 460-467): "TE and TM transmittances pinch together
within 5% of T_0=0.54 across [0°, 80°]". Wrong by inspection: at θ=80°
T_s=0.13 (76% off) and T_p=0.95 (76% off). Only the average (T_s+T_p)/2
stays near T_0. The summary paper at `theory/summary_paper.tex` line
321-327 states it correctly using T_avg; the JSAC paper drops the average.

### T2. "K = jk_0 (1−T_0)" is amplitude vs power confusion

Sec IV line 635-636 writes `K = jk_0 r_0` with `r_0 = 1 - T_0 ≈ 0.46`.
T_0 is a power transmittance (per eq. Sab-single line 449), so `1 - T_0`
is the power reflectance R_0; the amplitude is √R_0 ≈ 0.679 (matching
|r_s(0)|). The paper formula introduces a 3.36 dB error in body channel
power — separate from the showstopper above (which is the code-side bug)
but compounding it.

### T3. Approximation 1 error bound is wrong by ~9×

Supp Prop. S-approx1 (line 83) argues sin(θ_t)·sin(θ_t') = O(1/|ñ|²) and
concludes the inner-product mismatch is O(1/|ñ|²) ≈ 4%. But the
substitution error sin(θ)sin(θ') − sin(θ_t)sin(θ_t') = sin(θ)sin(θ')·
(1 − 1/|ñ|²) is O(1), not O(1/|ñ|²). Numerical sweep: inner-product
mismatch reaches 89%; combined with Fresnel weighting, depth-integrated
TM-TM cross-term P_abs error reaches 35% at (0°, 75°), not 4%.

### T4. Approximation 2 error bound is wrong by ~6×

Supp Prop. S-approx2 (line 129) expands `(1/2)(Δα/ᾱ)² + (1/4)(Δβ/ᾱ)²`,
which is the bound for `|1 − |Γ||`, not `|1 − Γ|`. Correct leading-order
behavior of `|1 − Γ|` is `|Δβ|/(2ᾱ)`, **first-order** in the spread.
With ᾱ ≈ k_0 · 1.79 and Δβ amplified by Re(ξ)/|Im(ξ)| ≈ 2.5, numerical
max `|1 − Γ| = 2.65%` not 0.44%.

### S3. Naturalness ball excludes every real walking pose

`latent_sweep_munich_jax.py:47` sets ρ_nat = 2 anchored at the origin. On
the production pose pool of 459 plaza-walk frames, |z_0| has mean 3.09,
range [2.20, 4.32]. **17 of 18 Munich scenes start with |z_0| > 2.** The
first projected gradient step physically forces the user out of their
natural pose down to a smaller ball. The earlier `latent_sweep_munich.py`
used ρ_z = 1.5 anchored at z_0 (relative ball, paper-consistent); the JAX
rewrite switched to absolute and broke the framing. SI Sec S3 line 304-309
("excludes the contortionist tail") does not match what the experiment
actually does.

### S4. "Brute-force optimum" is N=100 random shots in 32-D

§VIII.D-E uses N=100 random latent samples in a 32-D ball as ground truth.
Expected nearest-neighbor distance is 1.73 in a ball of radius 2 —
essentially zero coverage. Gradient ascent **beats** this "brute force" on
9 of 18 scenes (e.g. scene 9: gradient 44.35 dB vs random 42.73 dB). The
two scenes that "fail" reachability (scenes 3 and 17) "fail" only because
random sampling lucked into better latent points than gradient ascent
reached in K=20. Both 8/9 numbers are noise estimates against a poor
reference, not measurements against a real optimum. A genuine baseline
needs N=10⁴-10⁵ samples or a global optimizer.

### S5. Baselines comparison saturated by undisclosed MCS cap

`baselines.npz`: 96/120 cells (80%) are exactly 740.00 Mbps with std 0.00 —
an MCS27 cap (~22.25 dB SINR) in the kirchhoff.py version that existed
when the npz was generated (later patched to be uncapped). The +13.8% NLOS
gain claim is purely (740 − 650)/650 by both T-pose and RIHB hitting the
cap on all 10 scenes, identically. The +5.8% vs +7.1% difference comes
from RIHB hitting cap on 9/10 vs T-pose 8/10. **The "RIHB closed loop
separates from the static T-pose prior" claim does not survive an uncapped
Shannon comparison.** Re-run with uncapped rates.

### S6. Whole-body SAR claim off by ~10×

SI Compliance (line 678) claims ≤1.2e-4 W/kg at the canonical operating
point. Data in `sab_receipt.npz`: P_abs = 71.74 mW; for a 70 kg body that
is 1.0e-3 W/kg ≈ 8.5× higher. Implied body mass for the paper claim is
~600 kg.

### S7. "0.58% of ICNIRP 4 W/m²" mixes two limits and two distances

The "0.58%" comes from `peak_local_apd.py` at body 30 m vs ICNIRP **10
W/m²** local limit (`peak_local_apd_summary.txt` line 3 confirms). Paper
abstract and §IX line 1205 say "0.58% of the ICNIRP general-public
reference of 4 W/m²" — wrong limit. Actual fraction at 4 W/m² would be
1.45%. Separately, the §IX live-SAR receipt is at 10 m where peak APD is
3.79% of 10 W/m² (or 9.5% of 4 W/m²). The paper picks the more flattering
30-m number for the abstract but cites the 10-m experiment.

### S8. SI calibration figure is from a different manuscript

`figures/residual_vs_snr.pdf` was generated by
`JSAC/code/experiments/csi_calibration/run_calibration.py` (the predecessor
JSAC manuscript), measuring BS-side per-path β calibration with no body
model, no Φ, no J. Its README explicitly says "calibration acts on α only".
SI puts this figure under headings about body-side Tier-B SVD calibration;
the ρ = ‖β̂ − γ‖/‖γ‖ expression mixes vectors that live in different
spaces in the JSAC2 setting. The actual JSAC2 calibration figure
(`outputs/fig3_calibration.pdf`) is uncited.

### S9. Identifiability proposition empirically violated at the stated 20 dB SNR

Appendix C: "non-trivial as long as K ≤ M and the pilot SNR exceeds K
σ_K^-2". Under the most charitable normalization (per-mode spectral mass),
the K_99=4 mode in the close-BS regime needs ≥ 22.5 dB UL SNR to be
identifiable; under the K-factor reading it needs 28.5 dB. The paper's
stated 20 dB operating point doesn't qualify. At 20 dB close-BS, K_99=4
gives 36.6% reconstruction error; K=2 (smaller than K_99) gives 31.9% —
the prescribed K isn't even optimal.

### S10. Per-joint top-5 mass: claimed >80%, actual 51.8%

`per_joint_sensitivity.npz` and the audit log of the agent that produced
the figure both flag this: top-3 carries 35.2%, top-6 carries 58.8%.
K(80%) = 11 joints, K(95%) = 17. Survived into Sec VIII.F line 1113
anyway. The qualitative ranking (torso joints dominant, periphery flat)
is correct.

### S11. Scene loss numbers off by +18 dB throughout §VIII

`munich_trace.py` summary line computes `20·log10(sum_m |h_scene[m]|)`
instead of `10·log10(‖h‖²)`. All "scene loss" prose values in §VIII.D
are off by +18 dB = 10·log10(64). "Hero scene 17 scene loss -109 dB"
should read "-127 dB". SINR numbers are unaffected (computed correctly
inside `_sinr_db_from_h`). Pure prose / table fix.

### S12. Comfort Pareto x-axis is not what the prose describes

Figure x-axis is joint-space comfort cost C(Δθ) = Σ(Δθ_j/5°)² over 6
actuated joints, range 0-4. Paper §VIII.G describes it as latent radius
‖z − z_0‖ and quotes thresholds at 0.5, 1.0, 1.2. The script never even
loads VPoser. Numbers loosely match if you re-interpret 0.5-radius as
√C ≈ 0.91, but that 2× rescaling is not in the script. Pareto is also
evaluated at a single synthetic free-space scene, not Munich.

### S13. Hero figure self-inconsistency

Panel (b) in `fig_hero_munich.png` renders the NumPy/j_idx kirchhoff
best (17.8 dB) while the Δ label and caption use the JAX/steering-ramp
best (19.5 dB). The two implementations agree at z_0 (10.91 dB both)
but rank N=100 random latents differently by 1-2 dB. The visualised
silhouette achieves 6.9 dB, not the headline 8.6 dB.

## Significant but more localised

- **K_99 sweep is on Thelonious phantom, not Munich** (S7 in calibration
  audit). `svd_spectrum.py` loads `data/thelonious.stl`, places synthetic
  panels at d ∈ {3, 5, 10, 30}m, runs LOS-only path dictionaries — no
  Munich GLB or Sionna trace. Reported `K_99 ∈ {1, 2, 4}` also omits the
  K_99=3 result at d=5m.

- **SI Tier-D + Tier-B chained pipeline doesn't match the code.** SI says
  "Tier-D: complex scalar on LOS + real on h_body, then Tier-B operates
  on the Tier-D residual". Code does: Tier-D fits one complex scalar on
  h_body (not LOS); D/C/B run as parallel independent fits (no chaining);
  there's an undisclosed Tier-C (R=6 anatomical regions) hardcoded for
  Thelonious.

- **"Robustness via the γ fit" against IMU drift is asserted but not
  measured.** `imu_sweep_munich.py` runs gradient ascent on perturbed-pose
  SINR with no γ calibration anywhere. The ≤0.5 dB loss is achieved
  without any γ correction, undercutting the SI's "via the γ fit"
  attribution.

- **Translation phasor remark gets the matrix axis wrong** (Sec IV remark,
  line 660-666). Paper says Φ(t) is "diagonal on the BS-element axis";
  actually `exp(-jk_0 k̂_n·t)` varies with the path arrival direction k̂_n,
  so it's diagonal on the path axis, not the BS-element axis. The "one
  diagonal multiply" is correct in spirit, wrong in axis.

- **Hero scene 17 — body presents back/sides to dominant energy.** Body
  faces BS, but in deep NLOS the dominant body-incident paths arrive from
  buildings to the north-west; only 25% of body-incident energy hits the
  front. Defensible (user looks at phone facing BS) but undisclosed.

- **NLOS stratification ranges reverse-engineered.** Mild-shadow scene 9
  (81 dB) actually delivers 7.91 dB (outside the "1-4 dB" range);
  strong-shadow scene 13 (98 dB) delivers 3.30 dB (below "4-8 dB").

- **UE polarization gating** (kirchhoff.py:273): paper says |g_UE|² ≡ 1
  isotropic; code projects to z-component only. On Munich Scene 0 this
  is a 0.5 dB difference in ‖h_body‖ but can flip the sign of LOS
  interference.

## Things that pass clean

- Body excluded from Sionna RT scene; `h = h_BS + h_body` Maxwell split is
  honest.
- BS placement, panel-normal, steering ramp, Sionna v2.0.1, RT settings —
  all match the paper.
- Per-scene SINR existence numbers reproduce the paper exactly from
  `munich_existence.npz`.
- IMU sensitivity sweep methodology is correct (true SINR with biased
  gradient).
- Peak-APD location numbers (52, 58 cm) reproduce.
- VPoser decoder JAX vs PyTorch: 1e-7 rad parity.
- SMPL-X LBS JAX vs official `smplx`: 0.4 micron parity.
- `kirchhoff_h_body_native` (memory-frugal) vs full per-element fanout:
  7e-16 relative — exact transformation, not an approximation.
- Autodiff is correct (the test FD step was just too coarse — at
  eps=1e-6, autodiff vs FD cosine = 1.0).
- `_surface_centroid` correctly matches `trimesh.Trimesh.centroid`.
- Q-matrix factorization Q_abs = J^H M(θ) J is valid for joint-angle
  ascent (J fixed).

## Recommended next steps

In rough priority order:

1. Fix the Kirchhoff K coefficient (S1). One-line code change in two
   files. Add a flat-mirror analytical regression test. Re-run the 18
   Munich scenes.
2. Fix the Sionna paths.cir() unpack (S2). Re-trace the 18 scenes.
3. After 1+2, re-derive every quantitative number in the abstract,
   §VIII, and SI S5/S6.
4. Reframe the "naturalness ball" (S3) — either anchor at z_0 (relative
   ball) consistently with the paper, or document and justify the
   absolute-ball choice.
5. Replace the "brute-force" reference (S4) with either a much larger
   sample size (10⁴-10⁵) or a global optimizer like CMA-ES; re-derive
   reachability fractions.
6. Rerun baselines comparison without the MCS cap (S5).
7. Fix the SAR (S6) and ICNIRP (S7) numerical claims.
8. Replace the SI calibration figure (S8) with the actual JSAC2
   calibration result.
9. Re-derive the Approximation 1 and 2 error bounds (T3, T4) — they
   matter less for the empirical claims (calibration absorbs the
   numerical scale errors) but they will not survive review of the
   physics chapter.
10. Restate the pseudo-Brewster collapse using T_avg (T1), and either
    fix the K formula (T2) or document the implementation choice.
11. Fix the per-joint top-5 mass claim (S10) — easy, just report 51.8%.
12. Fix the comfort Pareto axis-vs-prose mismatch (S12).
13. Fix the hero figure (b) label inconsistency (S13).
14. Fix the +18 dB scene-loss prose values (S11).

Items 1, 2, 5, 6 affect the abstract and headline numbers — the paper
needs to be re-numbered after these. Items 3, 4 are framing fixes that
change interpretation but not raw numbers. The rest are localised.
