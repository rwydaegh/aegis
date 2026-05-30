# Audit: JSAC2 v3 empirical study vs. NPZ contents

Date: 2026-05-11
Scope: jsac2_v3.tex / jsac2_v3_supp.tex sections VIII.D-G + SI S5/S6/Compliance,
      against /home/user/aegis/JSAC2/code/outputs/*.npz and the scripts that
      generated them.

Verdict: a mix of supported, partially supported, and several substantively
flawed claims. The biggest issues are (1) a hard MCS rate cap that destroys
the head-to-head precoder comparison in §VIII.G, (2) a per-joint sensitivity
mass claim that is wrong by ~30 percentage points, (3) a "brute-force"
optimum in §VIII.D-E that is N=100 random shots in a 32-D ball, and (4)
two different ICNIRP limit values used inconsistently in the compliance
section (10 W/m^2 in scripts, 4 W/m^2 in paper text).

----------------------------------------------------------------------
## What checks out

**Existence numbers (§VIII.D, lines 1052-1062).** munich_existence.npz keys
match: 18 scenes, N=100 latent samples, rho_z=2.0, seed=42. Per-scene
SINRs reproduce paper claims exactly:

- 9 LOS scenes: gains 0.60 to 2.43 dB, mean 1.74 dB. Paper: "0.6 to 2.4 dB
  (mean 1.7 dB)". MATCH.
- 9 NLOS scenes: mean 4.13 dB. Paper: "4.1 dB on NLOS". MATCH.
- Scene 17: baseline 10.91 dB, best 19.51 dB, gain 8.59 dB, scene loss
  -109.09 dB. Paper: "10.9 dB SINR, best-of-100 random 19.5 dB, Δ=8.6 dB,
  Rx at (-69,115), -109 dB". MATCH (scene_17.npz confirms phone_xyz =
  [-69, 115, 1.5]).

**Reachability §VIII.E lines 1077-1102.** The K=20 success counts are 8/9
LOS and 8/9 NLOS using the 1 dB tolerance, and scene 17 terminal gap is
1.15 dB ≈ "within 1.1 dB" as claimed. (But see "brute-force redefinition"
issue below.)

**IMU sweep SI §S5.** munich_imu_sweep.npz: 18 scenes × 5 sigma values
× 5 trials, N_TRIALS=5, K_ITER=8 — matches "5 Monte-Carlo trials per cell"
and "K=8". Computed loss statistics:

- sigma=4: LOS mean 0.40 dB, NLOS mean 0.02 dB. Paper: "<= 0.4 LOS, <= 0.1
  NLOS". MATCH.
- sigma=16: mean 0.27 LOS, 0.16 NLOS. Paper: "<= 0.3". MATCH.
- p90 single-trial loss across the swept range: max 1.83 dB at sigma=16
  NLOS. Paper: "stays under ~1.8 dB". MATCH (tight).

The script design correctly evaluates the perturbed-channel gradient at
z+delta_z (twin's biased view) and reports the achieved SINR at the true
channel — issue (g) does not apply.

**Hero scene location.** Scene 17 (the body-RIS rescue) is selected by
fig_hero_munich.py as the highest-gain NLOS scene, not hand-picked. The
paper text (Rx at -69, 115) matches scene_17.npz exactly.

**Per-joint top-5 identification.** The top-5 joint names (pelvis, L hip,
R hip, spine1, spine2) match the paper claim. The agent_per_joint
ranking is correct.

**Peak-APD location fragility (SI §S6).** Computed peak-distance-versus-
sigma is 52.3 cm (sigma=2) → 57.8 cm (sigma=16). Paper: "52 cm at sigma=2,
58 cm at sigma=16, saturating". MATCH.

----------------------------------------------------------------------
## Substantive issues

### 1. Per-joint sensitivity — top-5 mass claim is wrong by ~28 pts

Paper §VIII.F (line 1113): "Together they [pelvis, L/R hip, spine1, spine2]
carry over 80% of the gradient mass."

Actual from per_joint_sensitivity.npz: top-5 cumulative mass is **51.8%**,
not "over 80%". The agent log
(agent_logs/agent_per_joint_sensitivity.md, line 56) flags this explicitly:
"Top-3 carry 35.2% of gradient mass (expected >60% — DOES NOT MEET
expectation)" and "Top-6 carry 58.8% of gradient mass (expected >85% — DOES
NOT MEET expectation)". K(80%) = 11 joints, K(95%) = 17 joints. The 80%
claim survived into the paper despite the agent flagging it.

Detail: cumulative mass goes 14.5% (pelvis) → 26.1% (+L hip) → 35.2%
(+R hip) → 44.4% (+spine1) → 51.8% (+spine2). Paper's claim corresponds to
roughly the top-12 joints, not the top-5.

The "wrists, elbows, ankles, head are flat" claim is loosely defensible
(those joints together carry 10.7% of mass) but elbows individually are
1.9-2.4% each (33% of the spine2 mass), so "flat" is an overstatement.

### 2. Whole-body P_abs SAR claim understates by ~10x

Paper SI §Compliance line 678: "the whole-body SAR is <= 1.2 × 10^-4 W/kg,
more than two orders of magnitude below the limit."

Data from sab_receipt.npz: P_abs = 71.74 mW (panel a) or 77.7 mW (median
time series). For an adult mass of ~70 kg (the SI assumes neither
Thelonious mass nor any explicit mass), that is **1.0 × 10^-3 W/kg ≈ 8.5x
higher than claimed**. To recover the paper's 1.2 × 10^-4 W/kg, body
mass would have to be ~600 kg. Either the script computes an unrealistic
P_abs or the SAR sentence is off by an order of magnitude. The cumulative
dose ratio (5.65% of the dose limit) computed in the same script is
internally consistent, suggesting the SAR sentence is the wrong one.

### 3. Peak-local APD compliance: 0.58 % is computed against 10 W/m^2,
       paper claims it is against 4 W/m^2

Paper main text line 1205: "P_abs sits at 0.58 % of the ICNIRP general-
public reference of 4 W/m^2". Paper SI §Compliance line 683: "ICNIRP 2020
general-public limit above 6 GHz is 4 W/m^2".

Data: peak_local_apd.py and its summary use ICNIRP_LIMIT_WM2 = **10 W/m^2**.
peak_local_apd_summary.txt: "ICNIRP 2020 limit (general public, >6 GHz):
10.0 W/m^2". Peak APD at 30 m is 5.799e-2 W/m^2, which is 0.58 % of 10
W/m^2 — that is where the 0.58 % comes from. Compared to **4 W/m^2** as the
paper states, the same peak APD is **1.45 %**. The paper's 0.58 % vs 4
W/m^2 sentence is internally inconsistent: the percentage corresponds to
the 10 W/m^2 limit (peak averaged over 4 cm^2), and the 4 W/m^2 number is
the incident-PD limit for whole-body, not the local averaged limit. So the
sentence's combination of "0.58 %" with "4 W/m^2" is wrong by 2.5x.

Also: 0.58 % is the value at 30 m (peak_local_apd.py uses
BODY_WORLD_CENTROID_BASE = [30, 0, 1.2]). The companion sab_receipt.py uses
body at [10, 0, 1.2] m and gets peak APD = 0.379 W/m^2 = **3.79 %** of 10
W/m^2 (or 9.5 % of 4 W/m^2). The agent log confirms this:
agent_sab_receipt.md line 14: "Peak-local APD = 3.7924e-01 W/m^2 (3.79 %
of ICNIRP 10 W/m^2)". The paper picks the more flattering 30-m number for
the abstract / SI text, but the §IX live-SAR receipt is the 10-m
experiment. The two are not the same operating point.

### 4. Baselines comparison is destroyed by an undocumented MCS rate cap

The baselines comparison in §VIII.G claims:
- LOS-attenuated band: no-twin ZF -18 % vs no-twin MRT.
- Binding (55 dB): RIHB +7.1 % over MRT, T-pose +5.8 %.
- Body-dominant (80 dB): both T-pose and RIHB +13.8 %.

Verifying baselines.npz / baselines_table.txt: the raw rates show that
**96 of 120 cells (80 %) are exactly 740.00 Mbps**, with std exactly
0.00. 740 Mbps is not a Shannon rate at the relevant SINRs; the current
rate_bps_shannon in kirchhoff.py is uncapped, but the version that
generated baselines.npz on 2026-05-10 12:59 (kirchhoff.py was modified
2026-05-10 14:02, after the npz) had an MCS27 cap at log2(1+SINR)*100 MHz
= 740 Mbps, which corresponds to ~22.25 dB SINR.

Cap saturation by cell:
- LOS-attenuated: no_twin_mrt 10/10 capped, tpose_twin_mrt 10/10 capped,
  rihb_mrt 10/10 capped. The 0% spread among twin-aware methods is a cap
  artifact, not a genuine "all twin-aware methods reach the same operating
  point".
- Binding: tpose_twin_mrt 8/10 capped, rihb_mrt 9/10 capped. The +5.8 %
  vs +7.1 % gap is the difference between "T-pose hits cap 8 times" and
  "RIHB hits cap 9 times". Without the cap, both could be much further
  apart, equal, or even reversed.
- NLOS: tpose_twin_mrt 10/10 capped, rihb_mrt 10/10 capped. The +13.8 %
  identity for both is a pure cap artifact: the gap is (740 - 650.15) /
  650.15 = 13.81 %. The two methods are indistinguishable in capped rate
  by construction.

The script author flagged this in agent_logs/agent_comfort_baselines.md
line 47: "In NLOS, both T-pose and RIHB rescue the link to cap (740 Mbps =
+13.8 % over MRT). RIHB SINR gain >= 2.8 dB over no-twin MRT (actual likely
much higher since both twins are above cap)". The paper text "the body-
comparable band is where the body-side calibration most clearly separates
RIHB from a static-pose prior" rests entirely on the 1-cell cap-saturation
difference; it does not survive an uncapped Shannon comparison.

The paper does not disclose the MCS cap.

### 5. Twin-mismatch column in the baselines table is not a fidelity metric

Paper SI §S3 (and the figure caption) does not discuss the mismatch column,
but baselines_table.txt reports it. The script's `twin_mismatch` is
||h_meas - h_pred|| / ||h_meas||. For NLOS, no-twin gives mismatch ≈ 1.000
(predicting h_los which is essentially zero against ||h_true|| ≈ ||h_body||),
while RIHB gives mismatch ≈ 2.23. **The "better" precoder (RIHB) has WORSE
mismatch by this metric** because the Tier-D scalar gamma can over-amplify
||h_pred|| relative to ||h_true||. The agent log calls this an "anomaly"
(line 48). This metric is a red herring — it should not appear in publication
material.

### 6. "Brute-force optimum" in §VIII.D-E is N=100 random shots in a
       32-D ball

Paper §VIII.D: "best of N=100 random latent samples within ‖z‖ <= rho_nat
= 2". §VIII.E: "Success is defined as terminal SINR within 1 dB of the
brute-force optimum, taken as the naturalness-ball maximum found by N=100
random samples".

100 samples in a 32-D ball corresponds to 100^(1/32) = **1.155 points/axis
of grid coverage**. Expected nearest-neighbor distance is R * N^(-1/d) =
2 * 100^(-1/32) = **1.73** in a ball of radius 2. This is essentially "no
coverage" in any meaningful sense; calling it a brute-force baseline is
misleading.

The downstream effect on the 8/9 + 8/9 reachability claim is severe.
Inspecting munich_existence.npz, the gradient ascent **beats** the random-
sample max on 9 of 18 scenes (scenes 0, 2, 4, 6, 7, 8, 9, 14, 15 — gradient
> random by 0.07 to 1.63 dB):

  Scene  2 (LOS): grad 56.65 > random 55.84 (gradient wins by 0.81)
  Scene  9 (NLOS): grad 44.35 > random 42.73 (gradient wins by 1.63)

For these scenes the "1 dB tolerance" is automatically satisfied because
the random baseline is below the gradient endpoint. The two scenes that
"fail" (scene 3 LOS at 1.19 dB, scene 17 NLOS at 1.15 dB) "fail" only
because random sampling LUCKED INTO better latent points than gradient
ascent reached in K=20 iterations.

A more honest experiment would use a much larger random sample budget
(say N=10^4-10^5) and compare gradient ascent to that. As the experiment
stands, both 8/9 numbers are noise estimates rather than measurements
against a real optimum.

### 7. Comfort-Pareto X-axis label and prose disagree with the data

Paper §VIII.G line 1135-1144 / fig:pareto: caption says X-axis is
"latent comfort radius ‖z - z_0‖" and claims "0.5-radius latent step buys
~6 dB; unit step ~7.5 dB; saturates above 1.2".

comfort_pareto_baselines.py never touches VPoser; the X-axis is
**joint-space** comfort cost C(Δθ) = sum_j (Δθ_j/5°)^2 over 6 actuated
joints, ranging 0 to 4. The figure title and X-axis label say "Comfort cost
C(Δθ) [comfort units]". The Pareto frontier has gain 5.9 dB at C=0.83
and 7.55 dB at C=1.55 — the numbers loosely match the paper's
"6 dB, 7.5 dB" if you re-interpret "0.5 radius" as sqrt(C) ~ 0.91 and
"unit" as sqrt(C) ~ 1.24, but that is a 2x rescaling that nothing in the
script supports. As written, **the paper attributes the Pareto curve to
the latent space when it is actually in joint-axis-angle space**.

The Pareto figure is also evaluated at a single synthetic free-space scene
(55 dB scalar loss, BS at 10 m) — not on the Munich scenes. The text
acknowledges "one representative NLOS-class scene from the parametric
scalar-loss companion sweep (SI §S3)". The companion sweep is not the
Munich sweep; readers may conflate the two.

### 8. Hero figure renders a different "best pose" than the headline number

Paper §VIII.D figure 2 hero: "best of N=100, Δ=8.6 dB", panel (b) is the
rendered best pose. Inspecting fig_hero_munich.py:

- Panel (a) baseline rendered at z_0, title shows SINR =
  sinr_baseline[scene_17] from the npz = 10.9 dB. OK.
- Panel (b) "best-found pose" is rendered at the local NumPy-recomputed
  best_z, with title `best_sinr_seen` = **17.8 dB**.
- The Δ label and the green dashed reference in panel (c) come from the
  npz `best_gain` = **8.6 dB**, i.e. the JAX-pipeline best.

**Self-inconsistency**: 17.8 - 10.9 = 6.9 dB, not 8.6 dB. The panel (b)
silhouette is the NumPy/j_idx kirchhoff best (only 17.8 dB), but the Δ
label uses the JAX/steering-ramp best (19.5 dB).

The two implementations agree at z = z_0 (10.9126 NumPy vs 10.9125 JAX,
verified in this audit), but the ranking of the N=100 random samples
diverges by ~1-2 dB, and the JAX best (19.5) is unreachable under NumPy
(best of N=100 NumPy is 17.8). The figure visually claims a best pose that
delivers 17.8 dB, but advertises 8.6 dB of gain that the visualised pose
does not achieve.

### 9. Loose stratification of NLOS scenes vs. paper's tidy ranges

Paper §VIII.D: "Mild-shadow NLOS (~75 to 90 dB scene loss) returns the
same 1 to 4 dB pose uplift as LOS. Strong-shadow NLOS (~90 to 100 dB)
opens 4 to 8 dB". Actual data:

- Mild-shadow (75-90 dB scene loss, 5 scenes): gains 0.94 to 7.91 dB.
  Scene 9 (81 dB scene loss, 7.91 dB gain) is the clear outlier — it is
  in the mild-shadow band but achieves strong-shadow uplift. The paper's
  "1 to 4 dB" range hides this scene.
- Strong-shadow (90-100 dB, 3 scenes): gains 3.30, 4.01, 6.61 dB. Scene
  13 (98 dB, 3.30 dB) is **below** the paper's "4 to 8 dB" range.
- Deep-shadow: scene 17 only.

Stratification ranges are reverse-engineered to be neat.

### 10. Quantitative drift in the Peak-APD whole-body P_abs ratio numbers

SI §S6 lists at sigma=4 "mean -0.5 %, ± 1.4 %" and at sigma=16 "mean
-3.2 %, ± 4.5 %". Recomputing per-trial fractional change from
pabs_ratio_db (10*log10(P_perturbed/P_oracle)) in
munich_peak_apd_sensitivity.npz:

  sigma=2:  +0.03 % / 0.65 %  (paper: -0.0 % / 0.7 %  — match)
  sigma=4:  -0.43 % / 1.38 %  (paper: -0.5 % / 1.4 %  — match)
  sigma=8:  -1.46 % / 2.64 %  (paper: -1.2 % / 2.8 %  — mean is off by
                                ~0.25 pts; std a hair tight)
  sigma=16: -3.12 % / 4.23 %  (paper: -3.2 % / 4.5 %  — close, paper std
                                a hair generous)

These are not catastrophic; they look like the paper computed mean(dB)
first, then converted dB → %, instead of per-trial percent → mean. Both
conventions are defensible if disclosed; neither is.

----------------------------------------------------------------------
## Sample-count and seed bookkeeping (issue (a))

Reading the npz contents: all sample counts match the paper, with the
following exceptions:

| claim                              | paper says    | npz says    |
|------------------------------------|---------------|-------------|
| Munich existence samples per scene | N=100         | N=100 OK    |
| Comfort Pareto Sobol               | N=500         | N=500 OK    |
| Munich scenes                      | 18            | 18 OK       |
| IMU MC trials per cell             | 5             | 5 OK        |
| Peak-APD trials per cell           | 8             | 8 OK        |
| Baselines: 30 AMASS scenes         | 10/band       | 10/band OK  |
| Per-joint poses averaged           | 50            | 50 OK       |

Seeds: SEED=42 throughout. The free-space existence_sweep.npz is a separate
deprecated experiment and not referenced by the v3 paper.

----------------------------------------------------------------------
## Issue index from the prompt

(a) Sample counts: PASS (all 8 categories match).
(b) Statistics in figures: ONE issue — Pareto X-axis label mismatch
    (#7). Other figures appear correct.
(c) Hero vs existence vs reachability sample selection: hero figure has
    self-inconsistency between rendered best pose and labelled Δ
    (#8). Same SEED + same N = 100 in all three, but two different
    kirchhoff backends (steering-ramp for npz vs j_idx for hero render)
    diverge by ~1-2 dB on the best.
(d) "Brute-force" in §VIII.D-E is N=100 random samples in 32-D, not a
    real brute-force search (#6).
(e) Reachability uses the same brute-force figure of merit as existence
    (best of N=100). PASS for consistency, FAIL for honesty (#6).
(f) Pareto + baselines scenes: the v3 paper SI §S3 specifies the
    "parametric scalar-loss companion sweep" with bands at 35/55/80 dB,
    but the actual baselines.npz uses random ranges 25-35/50-60/70-85
    dB and the Pareto sweep uses a single point (55 dB, 10 m).
    Disclosed loosely; not a substantive flaw beyond #7.
(g) IMU sweep correctly evaluates SINR on the true model with a
    twin-perceived gradient (perturbed_grad_ascent in
    imu_sweep_munich.py line 60-92). PASS.
(h) SAR receipt: P_abs in W vs ICNIRP in W/m^2, body-area question
    noted in #2 + #3.
(i) Per-joint sensitivity is finite-difference (one-sided forward
    `(r_p - r0) / delta` in per_joint_sensitivity.py line 209), not
    autodiff. delta = 1° per axis. Not a flaw given the cap-free regime
    (rates 100-700 Mbps, no MCS saturation), but the choice should be
    disclosed if the paper claims gradient. The joint ordering matches
    SMPL-X convention (0=pelvis, 1=L_hip, 2=R_hip, ..., 22=R_wrist).
(j) "Brute-force" misnomer covered in #6.

----------------------------------------------------------------------
## Bottom line

The descriptive existence/IMU/peak-APD numbers are largely supported by
the npz contents; the paper's narrative about reachability, baselines,
per-joint mass, and compliance contains four substantive claims that
either contradict or substantially overstate the data:

1. Per-joint top-5 mass: **51.8 % actual vs ">80 %" claimed** (#1).
2. Whole-body SAR: **~10x understated**, off by an order of magnitude (#2).
3. Peak-APD 0.58 % is at 10 W/m^2 / 30 m, not at 4 W/m^2 / 10 m as the
   paper / hero scene implies (#3).
4. Baseline precoder comparison is **dominated by an undisclosed MCS rate
   cap** (#4, #5).

Any of these four would be a reviewer flag in revision. #1 is the cleanest
to fix (replace "over 80 %" with "about 50 %" or restate "top-12 carry
over 80 %"). #2 needs a body-mass disclosure. #3 needs a single
operating-point definition with the actual ICNIRP-style limit (10 W/m^2 over
4 cm^2). #4 needs either an uncapped Shannon comparison or an explicit
disclosure that the binding metric is MCS27, with the SINR-margin gap
quoted alongside.
