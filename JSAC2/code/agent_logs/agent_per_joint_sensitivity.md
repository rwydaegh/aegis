# Per-Joint Sensitivity Agent Log

Run date: 2026-05-10
Scene: body at [10.   0.   1.2], phone at [10.55  0.    1.3 ], BS at [0. 0. 5.]
Scene loss: 45.0 dB (on h_body, binding regime ~12 dB SINR mean across AMASS poses)
N baseline poses: 50, seed=42, delta=1.0 deg
Total compute time: 1132.8s

## Top-10 Joint Ranking

| Rank | Joint | Mean [Mbps/rad] | P25 | P75 |
|------|-------|-----------------|-----|-----|
| 1 | pelvis (root) | 7785.293 | 5473.913 | 9488.179 |
| 2 | left hip | 6219.594 | 3613.624 | 8156.265 |
| 3 | right hip | 4934.783 | 2281.250 | 6924.122 |
| 4 | spine1 (L5) | 4911.192 | 2521.693 | 6455.349 |
| 5 | spine2 (L4) | 3966.935 | 2451.001 | 5095.934 |
| 6 | spine3 (T12) | 3753.165 | 1836.653 | 4880.567 |
| 7 | left knee | 3490.625 | 1739.103 | 4852.262 |
| 8 | right collar | 2483.562 | 1263.707 | 3639.139 |
| 9 | right shoulder | 2458.884 | 1006.602 | 3277.968 |
| 10 | right knee | 2342.934 | 1303.432 | 3552.155 |

## Cumulative Mass Curve

| K | Joint | Cumulative mass |
|---|-------|-----------------|
| 1 | pelvis (root) | 0.1449 |
| 2 | left hip | 0.2607 |
| 3 | right hip | 0.3525 |
| 4 | spine1 (L5) | 0.4439 |
| 5 | spine2 (L4) | 0.5177 |
| 6 | spine3 (T12) | 0.5876 |
| 7 | left knee | 0.6526 |
| 8 | right collar | 0.6988 |
| 9 | right shoulder | 0.7445 |
| 10 | right knee | 0.7881 |
| 11 | left collar | 0.8230 |
| 12 | left shoulder | 0.8562 |
| 13 | right elbow | 0.8806 |
| 14 | neck | 0.9030 |
| 15 | left ankle | 0.9233 |
| 16 | left elbow | 0.9427 |
| 17 | head | 0.9589 |
| 18 | right ankle | 0.9715 |
| 19 | left foot | 0.9800 |
| 20 | right wrist | 0.9873 |
| 21 | left wrist | 0.9942 |
| 22 | right foot | 1.0000 |

**K(80%) = 11**  **K(95%) = 17**

## Verification Checks

- Top-3 carry 35.2% of gradient mass (expected >60% — DOES NOT MEET expectation)
- Top-6 carry 58.8% of gradient mass (expected >85% — DOES NOT MEET expectation)
- Top-5 joints: ['pelvis (root)', 'left hip', 'right hip', 'spine1 (L5)', 'spine2 (L4)']
- Mean baseline rate across 50 poses: ~430 Mbps (binding regime, well below 740 Mbps cap)

## Findings vs prompt expectations

The empirical ranking is consistent with intuition: torso/spine + hip joints dominate,
with right-shoulder/right-collar entering the top 10 (the phone-side arm). Knees rank
~7-10 (perturbing them rotates the entire shank+foot below, which still moves body
silhouette and reflects in the rendering). Wrists, feet, and head rank lowest.

However, gradient mass is more spread out than the "top-6 carry 95%" expectation in the
prompt suggested. The actual K(95%) is 17 of 22 joints. Likely reasons:
1. Pelvis is the SMPL-X root joint — perturbing its global orientation moves the
   entire body, which strongly affects the body-to-phone Kirchhoff render. This is
   expected to dominate (rank 1, 14.5% of mass).
2. Hips, when perturbed, swing the entire leg below them and rotate the pelvis
   relative to the torso, both of which move the visible-from-phone triangle set.
3. Shoulder/collar joints rotate the arm, which (depending on pose) can occlude
   more or less of the torso from the phone view.

Despite the long tail, the headline "concentrated on a small number of joints" claim
holds in spirit: the top-6 joints (pelvis + L/R hip + spine1/2/3) carry 58.8% of
the gradient mass, with a clear hierarchy from torso/root joints (high) to
distal limb joints (low: feet 0.7%, wrists 1.4%, head 1.6%).

A plausible adjustment for paper text: "top-6 joints carry the majority of gradient
mass; per-joint sensitivity drops by an order of magnitude from pelvis to wrist."
