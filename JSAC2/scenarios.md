# JSAC2 in silico scenarios

Companion to `rihb_theory_v3.tex` (the two-contribution spine: live SAR receipt + RIHB capacity). Four candidate experiments, ranked by what they buy us. Each entry specifies geometry, parameters, what to compute, the predicted effect size, the falsification condition, and the implementation path.

**Spine update (post-v3).** The optimization is rate-only. There is no exposure-vs-rate Pareto trade in any scenario; the dose receipt is informational and is computed in parallel with the rate optimization, displayed but not optimized against. Body-to-phone direction is treated near-field (see `rihb_theory_v3.tex` §2.4) — the constant `k_out_{u→UE}` is shorthand for a per-point `eta(r; r_p)` inside the surface integral.

The hero figure for the JSAC2 SI submission is from scenario S1. S2 is the second figure if S1 lands. S3 is the multi-user followup paper. S4 is a discussion ablation. We build them in that order.

---

## Glossary

- **Pose move**: a change `Δθ ∈ R^72` from baseline `θ⁰` such that the comfort cost `C(Δθ) = Σ cᵢ Δθᵢ²` lies below a budget `ρ`.
- **Comfortable budget**: `ρ = 1` calibrated such that one unit corresponds to a `5°` torso rotation at the L4-L5 joint, baseline-relative.
- **Pareto-on-pose**: the curve `(P_abs(θ, x*(θ)), R(θ, x*(θ)))` traced out as `θ` sweeps the comfort ball, with `x*(θ)` the inner-precoder optimum at fixed pose.
- **Hero number**: the dB-difference between baseline rate `R(θ⁰)` and the gradient-optimal rate `R(θ*)` at `C(θ* - θ⁰) ≤ 1`.

---

## S1. Body-shadowed LOS at the window (hero)

**Story.** User is seated at a desk. Base station is on a tower outside, visible through a window. The user's torso partially shadows the LOS path. Small pose moves (torso azimuth, neck pitch, phone-hand height) re-route the LOS by un-shadowing or by adding a useful body-mediated specular path. The hero figure is the rate-vs-pose surface with iso-exposure contours.

### Geometry

- BS array: 64-element URA (8×8), `λ/2` spacing, mounted at `(0, 0, 25 m)`. Boresight along `+x`.
- User torso center: `(30 m, 0, 1.4 m)` (seated, eye-height representative).
- Window: rectangular aperture `(28-32 m × -1.5-+1.5 m × 2.0-3.5 m)` perpendicular to BS-user line, at `x = 25 m`. Walls outside this aperture block.
- Phone receiver: anchored at right wrist, baseline at `(30 m, 0.20 m, 1.20 m)` — phone held shoulder-low in front of the user.

### Parameters

- Carrier `f_c = 28 GHz`, bandwidth `B = 100 MHz`.
- TX power: `P_tx = 43 dBm` (typical for FR2 BS, matches JSAC v5 binding regime).
- Noise floor: `N₀B = -84 dBm` at NF = 6 dB (matches JSAC v5).
- Tissue: skin Gabriel parameters at 28 GHz, `T₀ ≈ 0.63`, `(1-T₀)/T₀ ≈ 0.59`.
- Body mesh: SMPL-X neutral, `β = 0` (or Thelonious as fallback), `θ⁰ = T-pose offset by typical seated posture (torso forward 5°, arms forward 30°)`.

### Pose move vocabulary

Three actuated DOF, all "comfortable" per `rihb_theory.tex` §3.1:

1. Torso yaw at L4-L5 spinal joint: `±20°`.
2. Neck pitch: `±15°`.
3. Right-shoulder pitch (phone-hand height): `±20°`.

Other joints frozen at `θ⁰`. Comfort cost `C` is `Σᵢ (Δθᵢ / 5°)²` over the three actuated joints.

### What to compute

For each pose `θ` on a 3D grid (e.g., `15 × 15 × 15 = 3375` poses):

1. Mesh `Σ(θ)` and phone position `r_p(θ)`.
2. Path set from BS to body and to phone via the window. Use a simple analytical multipath: direct LOS through window, one ground reflection, two wall reflections off the windowsill. ~5 paths total at the body, ~3 at the phone after the body.
3. Channel `h(θ)` at the phone (length `M`).
4. Exposure operator `Q_abs(θ)` at the body (size `M × M`), the JSAC v5 way.
5. Inner-precoder optimum: single-stream MRT-MMSE with the per-body cap, closed form.
6. Achievable rate `R(θ, x*(θ))` from eq. (15) of `rihb_theory.tex`.
7. Realised exposure `P_abs(θ, x*(θ))`.

### Outputs

- **Hero figure**: 2D heatmap of `R(θ)` projected onto the (torso-yaw, shoulder-pitch) plane at neck-pitch = 0, with iso-`P_abs` overlay.
- **Pareto figure**: scatter of `(P_abs(θ), R(θ))` across the comfort ball, shaded by `C(θ - θ⁰)`. Expected: a sharp efficient frontier.
- **Gradient-trajectory figure**: starting from `θ⁰`, plot 30 steps of gradient descent on `L = -R + λ_E[P_abs - L_RL]_+ + λ_M C`, with `(R, P_abs, C)` over iterations.
- **Number**: `R(θ*) / R(θ⁰)` in dB at `C(θ* - θ⁰) ≤ 1` and `P_abs(θ*) ≤ L_RL`.

### Predicted effect size

Body shadow loss at 28 GHz from a 30 cm-thick torso is `25-40 dB` (Geng 2018, Rappaport 2014). At baseline `θ⁰`, the LOS path through the window is partially blocked by the torso; even a 5° torso rotation moves the body's projected-area along the LOS by `~13 cm` (`30 m × tan(5°) ≈ 2.6 m` at the BS, `0.13 m` at the body). For a body-width of ~30 cm, this is a 40% un-shadowing. Predicted rate gain: `+10 to +18 dB` on the link. Pre-experiment estimate: **`+14 dB`**.

### Falsification condition

If the rate gain at `C ≤ 1` is below `+6 dB`, the spine is dead. The pose moves are not buying enough capacity to be worth a UI notification. Look for what's wrong: maybe the body shadow is small at this geometry; maybe the precoder is steering around the body without help.

If the gain is between `+6 dB` and `+10 dB`, the spine is alive but the pitch becomes "we save you from holding your phone wrong" rather than "we close 5G." Adjust framing.

If the gain is above `+10 dB`, the spine is healthy.

### Implementation path

- Reuse `src/aegis/coherent/exposure_operator.py` for `Q_abs`.
- Reuse `src/aegis/coherent/field_channel.py` for `G_tilde` at the body surface.
- Reuse `src/aegis/geometry/parametric.py` for SMPL-X mesh from pose; **drop `torch.no_grad()` or replace with JAX LBS** for differentiability.
- New: a thin wrapper that takes `θ` → mesh → `Q_abs` and `θ` → `r_p` → `h` and computes `R(θ)`.
- New: a simple multipath generator for the windowed-LOS scene (analytical, no Sionna needed for S1).
- Compute budget: 3375 poses × ~30 ms per pose = `~2 minutes` on CPU with NumPy backend; `~10 seconds` with JAX-on-GPU.

### Code home

`JSAC2/poc/s1_window/`: `geometry.py`, `multipath.py`, `pose_sweep.py`, `pareto_figure.py`.

---

## S2. NLOS coffee shop with corner turn

**Story.** User is in a café, BS is on the building across the street, around a corner. No LOS. The only paths are reflections off the café's interior surfaces and off other bodies. The user's pose can either redirect a useful specular off their own body toward the phone, or turn the body so a wall-reflected path reaches the phone unobstructed.

### Geometry

- BS array: 64-element URA at `(0, 0, 8 m)`, boresight `+x`.
- Café interior: `(20-30 m × -10-0 m × 0-3 m)`, glass storefront on `+y` side at `y = 0`.
- User torso center: `(25 m, -5 m, 1.4 m)`.
- Phone: at right wrist, baseline `(25 m, -4.8 m, 1.2 m)`.
- Reflectors: glass storefront, side wall at `x = 30 m`, ceiling.

### Parameters

Same as S1.

### Pose move vocabulary

- Torso yaw `±30°` (more freedom than S1; user is standing or in casual seating).
- Translation along table edge `±0.5 m` (the user can scoot).

### What to compute

Same as S1, plus a multipath generator that includes the café surfaces.

### Outputs

- Same triplet of figures as S1, plus a "path-attribution" plot showing which propagation path dominates at each pose. This is the figure that proves RIHB-as-passive-RIS, because we can show pose moves where the dominant path is body-mediated.

### Predicted effect size

NLOS with sparse reflectors: baseline rate is low (often near zero — fully blocked by the side wall). Pose-gradient finds a wall-bounce or body-bounce that lights up. Effect size potentially huge: from "no signal" to "MCS27 cap." Pre-experiment estimate: **`+30 dB or more`** — but with a low absolute floor.

The interesting question is whether the gradient finds the bounce reliably from a cold start, or only from a warm start (informed initial guess). This goes to whether the loop is deployable.

### Falsification condition

If the gradient never finds a usable bounce from a generic initial pose, deployment is fragile. The escape is multi-start (the BS suggests a few different starting moves), but this complicates the UX.

### Implementation path

Same structure as S1. The multipath generator now wraps a small specular ray tracer over the café geometry (3-5 walls); this is straightforward without Sionna.

### Code home

`JSAC2/poc/s2_cafe/`.

---

## S3. K=2 cooperative case

**Story.** Two users in the same scene, both opted in. User A's pose changes affect user B's channel via cross-body bistatic scattering (`F_b^(A)(k_out_A→B)`). The Pareto frontier becomes joint: A pays in dose to give B rate, and vice versa. In the symmetric case both users gain.

### Geometry

- BS array: 64-element URA at `(0, 0, 25 m)`.
- User A torso center: `(30 m, -1 m, 1.4 m)`.
- User B torso center: `(30 m, +1 m, 1.4 m)`.
- Phones: each at right wrist of their respective user.
- Both behind a window aperture (same as S1).

### Parameters

Same as S1, but with two users, two phones, and per-user `Q_abs^(A)`, `Q_abs^(B)`.

### Pose move vocabulary

- Each user has the S1 three-DOF vocabulary independently.
- Joint search space `R^6` per pose, `15^6 ≈ 11M` poses on a grid — too many. Use gradient descent from `θ⁰_A, θ⁰_B`, not grid sweep.

### What to compute

- Two-user achievable rate region: for each `θ` configuration, compute `R_A`, `R_B` under MIMO-2 precoding (zero-forcing across the two users).
- Per-user exposure `P_abs^(A)`, `P_abs^(B)`.
- The 4D Pareto: `(P_abs^A, P_abs^B, R_A, R_B)`.
- Project to 2D: the per-user `(P_abs, R)` curves with the other user's pose marginalised by gradient-optimum.

### Outputs

- 2D scatter of `(R_A + R_B, P_abs^A + P_abs^B)` across joint poses, with a Pareto envelope.
- A figure showing user A's rate gain attributable to user B's pose move at fixed `θ_A`. This is the body-as-passive-RIS effect, made explicit and quantitative.

### Predicted effect size

From `rib.tex` §11 the multi-body capacity scaling is `~K · M_eff / M`. For `K = 2`, `M_eff ≈ 5` per body, `M = 64`, the rank lift is `~10/64 ≈ 0.15` per user — additive maybe `+1-2 dB` per user from the cross-body lift, on top of the single-user S1 gain.

### Falsification condition

Cross-body lift is `< +0.5 dB`: the two users are behaving as independent S1 cases and the multi-user story doesn't earn its keep. Demote to a sentence in the discussion of the JSAC2 paper.

### Implementation path

Build on S1's machinery. Add multi-user precoder (regularised ZF on the two-user channel matrix). The pose search is now 6D, so use Adam on the joint loss instead of a grid sweep.

### Code home

`JSAC2/poc/s3_pair/`.

---

## S4. Plaza-scale ablation

**Story.** Reuse the JSAC v5 plaza scenario (Brussels Grand Place, 50 SMPL-X bodies on AMASS walks) and ask: of the 50, what fraction need to be opted-in RIHBs to lift the served users' median rate by 20%? This becomes a one-bar-chart ablation in the JSAC2 paper's discussion section.

### Geometry

Same as JSAC v5 plaza_run.

### Parameters

Same as JSAC v5: 64-element URA at building rooftop, 25 served users + 35 bystanders, 1500-slot trace at 100 Hz pose updates.

### Pose move vocabulary

For opted-in users only: torso yaw `±10°`, fixed-walking-trajectory but with sub-degree torso adjustment per slot. (Walking users' poses are dictated by AMASS; the RIHB layer adds a small azimuth correction.)

### What to compute

Sweep opt-in fraction from 0% to 100% in 10% steps. For each fraction, run the same JSAC v5 evaluation but with the opted-in users' poses gradient-adjusted at each slot.

### Outputs

Bar chart: opt-in fraction vs median rate, with std-error bars across 10 seeds.

### Predicted effect size

At low opt-in (5-20%), the lift on the served users is modest, `+1-2 dB` median. At high opt-in (>50%), the lift on bystanders' shadow-blockers becomes coherent, `+3-5 dB`. Saturation around 70%.

### Falsification condition

If the lift is `< +0.5 dB` at any opt-in fraction, the multi-user RIHB doesn't scale and the paper's deployment story is weakened.

### Implementation path

Substantial. Reuses JSAC v5 plaza_run code and adds a per-slot pose-gradient layer. Estimated 1-2 weeks.

### Code home

`JSAC2/poc/s4_plaza/`. Probably built last, after the JSAC2 paper draft is in solid shape.

---

## Build order and timeline

| Order | Scenario | Effort | Decision gate |
|-------|----------|--------|---------------|
| 1 | S1 PoC (single-user gradient sweep, one geometry, one frequency) | 3-5 days | If hero number ≥ +10 dB, proceed. |
| 2 | S1 production figure (multi-seed, multi-baseline-pose, dB-domain Pareto) | 1 week | Hero figure for the JSAC2 paper. |
| 3 | S2 NLOS coffee shop | 1 week | Second figure if S1 holds. |
| 4 | Theory v3 update with S1+S2 numbers | 3 days | Concretises the spine. |
| 5 | S3 cooperative pair | 1 week | Third figure / future-work-paragraph if not. |
| 6 | S4 plaza ablation | 2 weeks | Discussion-section ablation. |
| 7 | JSAC2 paper draft | 3 weeks | Final deliverable. |

Total to JSAC2 draft: `~7 weeks` of focused work, or longer if S1 misses on the first try.

## What we are not doing

- Not implementing a new ray tracer. Use Sionna or DiffeRT, or analytical multipath where it suffices.
- Not implementing a new precoder. The JSAC v5 projected-ZF closed form is exactly what we want for the inner loop.
- Not running an FDTD validation. The PO/Kirchhoff residual budget is good enough; the Pareto bound is a `5%` statement and FDTD doesn't tighten it materially.
- Not running a real user study. The comfort cost weights are a free parameter of the model; calibrating them empirically is a follow-up paper.
- Not solving the privacy-preserving federated variant. It is a well-flagged loose thread but does not need to be in the JSAC2 paper.

## Cross-references

- Theory: `JSAC2/rihb_theory.tex` §10 (in silico validation).
- Companion: `JSAC/paper/rib.tex` (RIB physics, Pareto bound).
- Code reuse: `src/aegis/coherent/`, `src/aegis/geometry/`, `JSAC/code/experiments/plaza_run/`.
- Failed prior spine: `JSAC/paper/paper_jsac_v5.tex` (the body-twin-as-α-supplier collapse).
