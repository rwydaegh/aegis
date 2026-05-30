# Existence + reachability sweep agent log

JSAC2 §VIII three-part convergence study, parts A and B (existence and
reachability). Part C (failure-mode taxonomy) is deferred to a follow-up
agent that consumes ``failure_indicator`` from the reachability NPZ.

## Files

- ``JSAC2/code/existence_sweep.py`` — Part A driver
- ``JSAC2/code/reachability_sweep.py`` — Part B driver
- ``JSAC2/code/outputs/existence_sweep.npz`` — Part A NPZ
- ``JSAC2/code/outputs/fig_existence.{pdf,png}`` — Part A figure
- ``JSAC2/code/outputs/reachability_sweep.npz`` — Part B NPZ
- ``JSAC2/code/outputs/fig_reachability.{pdf,png}`` — Part B figure

## Part A: Existence sweep

### Setup

- N = 200 random scenes, ``np.random.default_rng(42)``.
- AMASS pose pool: 12,782 plausible frames across 60 walk sequences in
  ``data/poses/plaza_run_walks/``. Plausibility filter: per-frame max
  spine-joint magnitude < 30°.
- 200 sampled scenes drew from **53 unique walks / 199 unique frames**
  (one frame per scene; sampling without replacement on the frame
  level).
- AMASS global_orient (joint 0) is zeroed: AMASS bakes Y-up orientation
  into joint 0 and ``scene_smplx._smplx_to_world_rotation`` already
  carries the Y-up → Z-up conversion. This is the pattern used by the
  plaza_run scenario as well.
- BS regimes drawn uniformly from
  ``[(0,0,8) far30m, (20,0,5) mid10m, (25,0,3) close5m]``.
- Scene loss drawn uniformly from ``{35, 55, 80}`` dB.
- Azimuth-offset sampled uniformly from ``[-30°, +30°]``; the BS panel
  is rotated about the body centroid in the world XY plane and re-aimed
  at the body.
- Comfort joints (6 of upper-body DoFs):
  ``spine1, spine2, spine3, neck, L_shoulder, R_shoulder`` —
  axes ``[Y, Y, Y, Y, X, X]`` in SMPL-X local frame. Each joint is a
  scalar perturbation Δθ_j ∈ [-15°, +15°] applied on its chosen axis.
- Comfort metric: ``C(Δθ) = sum_j (Δθ_j / 5°)²``; budget ``ρ = 1``.
- Search: 3 random restarts × K=20 inner iters × 7-candidate joint
  sweep per iter. Coordinate descent: at each iter pick a joint at
  random, sweep its axis over ``{-15, -10, -5, 0, +5, +10, +15}`` deg,
  reject candidates with ``C > ρ``, take best.
- Rate-gain metric: SINR delta in dB on the *uncapped* Shannon channel
  (``ΔR_dB := SINR_after - SINR_baseline``). The MCS27 cap saturates
  in the LOS-attenuated regime so a rate metric measured against the
  capped Shannon curve would be dishonest; the failure-mode taxonomy
  in Part C will explicitly account for cap-saturation.

### Results

| regime              | $\Delta R \geq 3$ dB | $\Delta R \geq 6$ dB | $\Delta R \geq 10$ dB | n  |
|---------------------|----------------------|----------------------|------------------------|----|
| Far (30 m, h=8 m)   | 81%                  | 49%                  | 18%                    | 77 |
| Mid (10 m, h=5 m)   | 72%                  | 46%                  | 18%                    | 61 |
| Close (5 m, h=3 m)  | 60%                  | 26%                  |  8%                    | 62 |

Mean best-gain per regime (brute-force coordinate descent):

| regime              | mean ΔR (dB) | max ΔR (dB) | top-5 ΔR (dB) |
|---------------------|--------------|-------------|----------------|
| Far (30 m, h=8 m)   | 6.6          | 16.2        | 14.6, 14.8, 15.4, 15.6, 16.2 |
| Mid (10 m, h=5 m)   | 5.9          | 16.1        | 12.1, 12.1, 12.3, 14.0, 16.1 |
| Close (5 m, h=3 m)  | 4.3          | 15.3        | 11.0, 11.4, 12.1, 12.8, 15.3 |

By scene-loss:

| scene loss  | $\Delta R \geq 3$ dB | $\Delta R \geq 6$ dB | $\Delta R \geq 10$ dB |
|-------------|----------------------|----------------------|------------------------|
| 35 dB       | 74%                  | 38%                  | 11%                    |
| 55 dB       | 67%                  | 46%                  | 23%                    |
| 80 dB       | 73%                  | 41%                  | 13%                    |

### Wall clock

- 200 scenes × 3 restarts × 20 iters × ≤ 7 candidates per iter
  ≈ 84,000 SMPL-X + Kirchhoff renders.
- 12 multiprocessing workers, 547 s wall clock (2.74 s/scene wall,
  ≈ 230 ms/render including the SMPL-X PyTorch forward pass).
- ``lru_cache`` on the SMPL-X torch model amortises the ~1 s
  per-process startup cost.

### Notes vs. the spine v2 prediction

Spine v2 predicted ~80–100% existence in LOS-attenuated and ~10–30% in
deep NLOS at the 6 dB target. Observed:

- LOS-attenuated (35 dB): **38%** at 6 dB.
- Deep NLOS (80 dB): **41%** at 6 dB.

The LOS-attenuated number is below v2's prediction; deep NLOS is at the
top of v2's range. Two reasons for the LOS-attenuated discrepancy:

1. The cap-saturation regime: many LOS-attenuated scenes already have
   SINR > 30 dB before pose tuning (the LOS path alone is comfortably
   above MCS27), so adding 6 dB is geometrically harder — the body
   reflection has to add coherently without pushing the cas channel into
   destructive interference.
2. The comfort budget ρ = 1 (single 5° single-joint move) is tight.
   Loosening to ρ = 4 (a coordinated upper-body move spanning ~10° per
   joint) would raise the existence fraction substantially. We keep
   ρ = 1 to honour the spec; the failure-mode taxonomy will surface
   "comfort-tight" as one bin.

The "close5m" regime degrades hardest (60% / 26% / 8%) because the body
sees the BS at a steep elevation angle, leaving little geometric room
for a torso/shoulder twist to redirect the dominant specular path. This
matches the v2 expectation that close-BS regimes are reflectively
saturated.

## Part B: Reachability sweep

(Status: writing in progress; results land here when the sweep finishes.)

### Setup

- Top-N = 20 highest-brute-force-gain existence-positive scenes per
  regime, capped at 20 (close5m has only 16 existence-positive scenes
  at 6 dB so 16 are used).
- 56 scenes total × 9 (SNR × IMU σ) cells × K_max = 20 iter trajectory.
- Calibration: ``fit_tier_b`` with K=8 SVD modes on the per-iter Λ;
  reduced to a scalar γ_0 := ⟨h_body, h_body_calib⟩ / ‖h_body‖² for
  use inside the inner FD loop. Full per-mode γ_k coefficients are
  recomputed every iteration (this is the ‘BS-pilot-corrected
  twin-side prediction’).
- Optimiser: cycling coordinate-descent with 3-candidate line search
  over Δθ_j ∈ {-3°, 0°, +3°} relative to the current operating point,
  best-so-far rewind if SINR drops > 2 dB. The ±3° step is coarse on
  purpose: smaller FD steps fall inside the O(2π) phase fringes of
  the cascaded SINR (an empirical observation: 0.5° FD gives
  |grad| ≈ 15 dB/deg dominated by phase-fringe sign flips, and is not
  a usable gradient for this physics).
- IMU noise corrupts proposed Δθ → executed Δθ via per-joint
  Gaussian noise with std σ ∈ {0, 4, 8} deg.
- UL pilot SNR ∈ {10, 20, 40} dB. Pilot is the BS-side noisy
  observation of the cascaded channel.
- Success: best SINR within K iterations is within 1 dB of the
  brute-force optimum from Part A.

### Compute optimisations

- ``PoseCache`` per scene worker, keyed on Δθ rounded to 0.1°. The 9
  (SNR, IMU σ) trajectories for one scene reuse the same physics
  renders when they visit the same Δθ — common at SNR=40, σ=0 where
  trajectories are deterministic given the cycling joint schedule.
- One scene-level worker processes all 9 cells; 12 workers in the
  multiprocessing pool.

(Results table + monotonicity checks + corner-case verification will be
appended here when the sweep completes.)

## Part B results

(Filled in by the script via `_write_log`.)
