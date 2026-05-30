# Pose-pipeline audit report
2026-05-11. Scope: `JSAC2/code/pose_pipeline_jax.py` and the Sionna-RT data
that flows into it. Theory anchor: `jsac2_v3.tex` Sec VI.B, Algorithm 1, and
SI Sec S3 (VPoser).

## Summary table

| Issue | Severity | Affects paper claim | Status |
| --- | --- | --- | --- |
| 1. VPoser parity | OK | n/a | Verified to 1e-7 rad |
| 2. SMPL-X LBS parity | OK | n/a | Verified to 0.4 microns vs official `smplx` |
| 3. Surface centroid vs `trimesh.centroid` | OK | n/a | Both are area-weighted; verified to 1e-14 m |
| 4. Heaviside lit/facing gates | known | reachability landscape | Smooth gradient is correct; gate flips give large local nonlinearity |
| 5. Test FD step (1e-3) is misleading | OK code, bad test | n/a | Autodiff gradient is correct at eps <= 1e-6 |
| 6. NaN gradient at axis-angle = 0 | latent bug | none today | Saved by scatter-set drop, would NaN if global_orient or face joints became differentiable |
| 7. Encoder round-trip works | OK | minor | encoder gives 11 deg per-joint err as claimed |
| 8. Native-vs-full Kirchhoff equivalence | OK | n/a | Verified to 7e-16 relative |
| **9. Sionna-trace polarization bug** | **CRITICAL** | **Munich body channel data is wrong** | **Outside pose pipeline scope, but feeds it** |
| **10. AMASS-encoded `\|z_0\|` exceeds rho_nat=2** | **paper claim mismatch** | **reachability/baseline framing** | **100% of pose pool fails the constraint, baseline pose is outside the search ball** |
| 11. SI claims phone offset (-0.40, 0, **0.05**) but Munich uses (-0.40, 0, **0.30**) | minor | numerical reproducibility of SI text | The 0.05 figure refers to the parametric companion |
| 12. SINR_dB vs paper's R = log2(1+SINR) | cosmetic | none | Same direction, scales by constant; optimization unaffected |

The critical findings are #9 and #10. Everything else is a non-issue or a
known engineering trade-off.

## Findings in detail

### 1. VPoser decoder parity (OK)

`vposer_decode_jax` matches `JSAC2/code/vposer_v2.py:VPoser.decode` to
~1e-7 radians on test points (z=0 and a random z). The leaky_relu slope
0.2 matches the upstream `human_body_prior` (`F.leaky_relu(..., negative_slope=.2)`,
`/home/user/aegis/.venv/lib/python3.12/site-packages/human_body_prior/train/vposer_smpl.py:101`).
Layer indices `decoder_net.0/.3/.5` are correct; the slots .1, .2, .4 are
non-parametric activations. The 6-D continuous-rotation reshape is the
column-stacked Zhou et al. layout, identical to `_continuous_rot_to_matrix`
in the PyTorch reference.

### 2. SMPL-X LBS (OK)

`smplx_lbs_jax(theta22, betas, sm)` reproduces the official `smplx` PyTorch
forward to ~0.4 microns max vertex error across z in {0, randn(0.5),
randn(1.5), randn(3.0)}. The kinematic chain via `jax.lax.scan` is correct
because the SMPL-X `parents` array is topologically sorted (`parents[i] < i`
verified for all i = 0..54; `parents[0] = -1`). Pose blend shapes use
`(rotmats[1:] - I).reshape(-1)` of length 54*9 = 486, matching the
`posedirs` shape. Face/eye/hand joints (22..54) are zero-padded; this is
consistent with the SI's "global orientation and the hands excluded" wording.

The `_R_SMPLX_TO_WORLD` matrix is the same product `Rz(-90 deg) @ Rx(-90 deg)`
that `scene_smplx._smplx_to_world_rotation` returns. Verified element-by-element.

### 3. Surface centroid (OK; docstring is misleading but correct)

`_surface_centroid` is the area-weighted face-centroid average, which is
**exactly what `trimesh.Trimesh.centroid` returns**. I verified this by
calling both on the same mesh:

- `trimesh.Trimesh.centroid` docstring says: "The point in space which is
  the average of the triangle centroids weighted by the area of each
  triangle. This will be valid even for non-watertight meshes, unlike
  self.center_mass."
- Numerical comparison: trimesh `[-0.03928, 0.00372, -0.40881]`, JAX
  `[-0.03928, 0.00372, -0.40881]`. Identical to floating-point precision.

The `pose_pipeline_jax.py:236` docstring claims "trimesh-style **volume**
centroid", which is wrong (it's the area-weighted SURFACE centroid). The
function itself is correct; only the comment is misleading. Cosmetic fix.

End-to-end placement parity: `world_verts(...)` produces vertices that match
`scene_smplx.make_body_smplx(...)` to 0.36 microns max across face_az in
{0, pi/2, 1.234}.

### 4. Heaviside gate continuity (known limitation, well-handled)

`facing = (n . eta_hat) > 0` and `lit = mu > 1e-3` are non-differentiable.
At a typical optimizer step (eta=0.4, normalized gradient direction):

- ~82 of 20908 (~0.4%) phone-facing triangles flip
- ~52,297 of 11M (~0.5%) (path, triangle) lit pairs flip

JAX autodiff treats the boolean as a constant (verified: `jnp.where(cond, x, y)`
gives gradient 0 for `cond` and routes only through whichever branch is
active). This is the standard "smooth-on-each-side, jump-on-boundary"
approach in differentiable rendering, and it is consistent with the chain
the paper claims to differentiate.

The optimizer's empirical step-acceptance rule
(`latent_sweep_munich_jax.py:145`: `if s_new > sinr_traj[k] - 0.5: z = z_new
else fall back`) catches steps where gate flips reverse the actual SINR
delta from the predicted one. Linear extrapolation along `g/||g||` at z=0
shows >100% nonlinearity already at eta=0.05 (predicted dSINR -0.18 dB,
actual -0.07 dB), and at eta=0.4 (production step) the SINR change is
**opposite in sign** to the gradient prediction. This is consistent with the
control loop needing many rejections / step-shrinks; it is not a correctness
bug.

### 5. Test FD step is misleading (test bug, not pipeline bug)

`test_pose_pipeline_jax.py:138` uses `eps = 1e-3` for finite-difference
cross-check. At z=0:

| eps | FD for z[0] | autodiff |
| --- | --- | --- |
| 1e-1 | +2.71 | +2.09 |
| 1e-2 | +2.45 | +2.09 |
| 1e-3 | +3.40 | +2.09 |
| 1e-4 | +2.09 | +2.09 |
| 1e-5 | +2.09 | +2.09 |
| 1e-6 | +2.09 | +2.09 |

At eps=1e-3, FD reports ~50% relative error; at eps <= 1e-6, FD agrees with
autodiff to 1e-3 absolute. The eps=1e-3 step is large enough to flip dozens
of facing/lit gates, contaminating the FD estimate. The test prints these
misleading values and exits successfully (no assertion). I recommend
switching the test to `eps=1e-6` and adding an `np.allclose(g, fd, rtol=1e-2)`
assertion. The pipeline gradient itself is correct.

A more aggressive cross-check at random z (sigma=1.5, |z|~7-8) at eps=1e-5
shows max relative error <5% on all 32 coordinates across 3 trials. At
eps=1e-6 the agreement is 1e-3 absolute. **The smooth gradient through the
chain is correct.**

### 6. NaN gradient at axis-angle = 0 (latent bug, not currently active)

`_axisangle_to_rotmat` at exactly `aa = [0, 0, 0]` produces NaN gradient.
The forward is fine (returns I), but the Jacobian backwards is all NaN,
because `jnp.linalg.norm(aa)` has gradient 0/0 at aa=0. The `jnp.maximum(angle, 1e-12)`
clamp keeps the forward finite but doesn't fix the backward.

Why the production code does NOT NaN at z=0:

- The code does `theta22 = jnp.zeros((22, 3)).at[1:].set(body_aa)`.
  `theta22[0]` is a constant zero — the cotangent for `theta22[0]` does not
  flow back to `z`, so the NaN gradient at joint 0 is dropped by the scatter.
- `full_aa = jnp.zeros((55, 3)).at[:22].set(theta22)` — same: full_aa[22:]
  cotangents do not flow back.
- VPoser at z=0 produces axis-angle norms in [0.07, 0.92] rad on body
  joints 1..21, so none of those hit the NaN-at-zero cliff.
- Across 200 random z samples (sigma=1.5), the minimum body-joint axis-angle
  norm was 1.07e-4 rad, well clear of 0.

If a future change made `theta22[0]` (global_orient) or face/hand joints
depend on z (e.g., to optimize body azimuth as part of the latent), the
gradient would NaN out immediately. Recommended fix:

```python
def _axisangle_to_rotmat(aa):
    angle = jnp.linalg.norm(aa, axis=-1, keepdims=True)
    angle_safe = jnp.where(angle > 1e-8, angle, 1.0)  # safe denom only
    axis = aa / angle_safe
    sin = jnp.sin(angle)
    cos = jnp.cos(angle)
    # ... rest as before, but use angle_safe consistently
    R = eye + sin[..., None] * K + (1 - cos[..., None]) * (K @ K)
    # At small angle, fall back to first-order Lie expansion
    return jnp.where(angle[..., None] > 1e-8, R, eye + K_from_aa)
```

For now, the bug is dormant.

### 7. Encoder round-trip (OK)

`VPoser.encode` exists in `vposer_v2.py` and is called in
`latent_sweep_munich_jax.py:192` via `encode_pose_to_z(baseline_pose22, vp_torch)`.
The encoder uses `eval()` mode so BatchNorm running stats are used (not batch
stats). On the AMASS plaza-walk pose pool, encoder reconstruction error is
11.0 to 12.1 deg per joint, matching the SI's "~11 deg" claim.

### 8. Native-vs-full-fanout Kirchhoff equivalence (OK)

`kirchhoff_h_body_native` (uses `P_sionna ~ 350` paths plus an inline
per-element steering ramp) is mathematically identical to
`kirchhoff_jax._h_body_kernel` (uses `M*P_sionna ~ 22000` per-element paths).
Both produce the same `h_body` at machine precision (relative error 7e-16
on the Munich scene 0). The planewave-steering ramp is exact, not an
approximation, under the planewave-incidence assumption that holds for
Munich (BS at ~80 m, far field of an 8x8 URA at 28 GHz starts at the panel
diagonal 0.05 m, then 2D^2/lambda = 0.52 m — body easily in BS far field).

Side note on the planewave-at-body assumption: the Sionna trace samples
exactly one (k_dod, k_doa) per path, and the Kirchhoff render assumes the
same k_doa applies at every triangle on the body. A true spherical wave
from the BS would have k_doa varying by ~0.7 deg across the 2 m body, which
at 28 GHz gives a phase error of ~14 rad per path across the body — large
enough to scramble the relative phase between triangles for the same Sionna
path. This is a modelling approximation in the forward map; the gradient
is consistent with the same approximation, so the optimizer finds the
optimum of this planewave-Kirchhoff model, not the true spherical-wave
model. Not a bug, but worth noting in the SI's modelling-assumption section.

### 9. CRITICAL: Sionna RT polarization is wrong in the saved Munich data

This bug is in `JSAC2/code/scenes/munich_trace.py`, not in
`pose_pipeline_jax.py`. But the saved `body_psi_path`, `body_psi`, and
`h_scene` arrays that the pose pipeline consumes are corrupted as a result.

Sionna 2.0.1's `Paths.cir(out_type='drjit')` returns a tuple
`(re_TensorXf, im_TensorXf)` of the **complex** baseband-equivalent CIR
coefficients — the leading dim of size 2 is **(real, imaginary)**, not
**(theta, phi)** field components. The scalar Tx/Rx are V-polarized, so
each path has a single complex scalar, returned as its real and imaginary
parts.

`munich_trace.py:104-108` does:
```python
a_raw, tau_raw = paths.cir()
a_np = np.asarray(a_raw)  # (2, 1, 1, 1, 1, P, 1) float32 -- (re, im) of E
a_theta_all = a_np[0, 0, 0, 0, 0, :, 0]  # **WRONG** -- this is Re(E)
a_phi_all   = a_np[1, 0, 0, 0, 0, :, 0]  # **WRONG** -- this is Im(E)
```

It then assembles `psi = a_theta * e_theta + a_phi * e_phi`, where
`e_theta`, `e_phi` are real orthonormal spherical-basis vectors at the DOA
angles. The result `psi` is purely real (because `a_theta`, `a_phi`,
`e_theta`, `e_phi` are all real) with magnitude `|psi| = sqrt(Re(E)^2 +
Im(E)^2) = |E|`.

Consequences:

1. **Phase between paths is destroyed.** Sionna's CIR includes
   `exp(-j 2 pi f tau_i)`; the imaginary part of E carries the cross-path
   phase information. Splitting Re/Im across two real basis vectors
   (e_theta, e_phi) makes psi real per-path, so coherent path interference
   computations become incorrect.
2. **Polarization direction is wrong.** The body-channel render uses
   `g_UE_proj = psi[2] - eta_hat[2] * (psi . eta_hat)`. With psi pointed in
   a random Re/Im linear combination of e_theta and e_phi, instead of the
   true V-polarization direction at the body, the projection on the
   vertical-pol UE antenna is incorrect.
3. **Magnitude is preserved.** The |psi|^2 sum is right, so the average body
   channel power is plausible. The polarimetric details and per-path phases
   are wrong.

Verification:

```
a_raw, tau_raw = paths.cir()                # default drjit, returns list of 2 TensorXf
ret_numpy = paths.cir(out_type='numpy')     # returns complex64 directly
# True complex first 3:  [4.18e-10+3.35e-10j, 5.92e-10+5.78e-10j, -4.39e-10-3.74e-10j]
# Reconstructed from drjit: same as np.asarray(a_raw[0]) + 1j * np.asarray(a_raw[1])
# munich_trace's interpretation: a_np[0] = Re(E), a_np[1] = Im(E). Both real.
```

Also, `body_amp_path` is identically `1+0j` in all saved scenes (verified:
mean `|amp| = 1.0`, std `< 1e-15`). The `body_amp` (per-element fanout)
has unit magnitude too — only the per-element steering phase
`exp(-j k0 (bs_pos[m] - bs_center) . k_dod[p])` is in there. All path
amplitude information is in psi (which lost its phase). So the body-channel
data has lost both the per-path complex carrier phase AND has wrong
polarization direction.

This explains why `body_psi_path` is float32 instead of complex128 in the
saved NPZ — it never had imaginary part to begin with.

**Impact on the paper's reachability claim**: every body-channel SINR
number reported in the Munich numerical study is computed from a wrong
polarization model. The reachability percentages may still be qualitatively
right (the body still partially blocks/reflects), but the absolute SINR
values and the relative gain figures are not trustworthy. A re-trace with
the right cir() unpacking is needed.

Recommended fix in `munich_trace.py`:

```python
# Get true complex CIR
a_complex, tau = paths.cir(out_type='numpy')
a_np = a_complex[0, 0, 0, 0, :, 0]  # (P,) complex64

# For V-pol Tx + V-pol Rx, a_np IS the projection of E onto V-pol direction.
# So the polarization vector at the body is just the V-pol unit vector
# (world +z) times a_np. No theta/phi decomposition is recoverable from
# Sionna 2.x with V-pol arrays.
psi = a_np[:, None] * np.array([0.0, 0.0, 1.0])[None, :]  # (P, 3) complex
```

This will give the correct V-pol body channel. To recover full theta/phi
polarization, switch to `polarization='cross'` arrays in Sionna and unpack
the (theta, phi) channels separately.

### 10. CRITICAL: AMASS-encoded baseline `|z_0|` exceeds rho_nat = 2.0 always

Paper says `rho_nat = 2.0` keeps the search inside the "naturalness ball"
(jsac2_v3.tex line 821, supp Section S3 line 304: "this radius keeps poses
within 2 nats of the prior mode and excludes the contortionist tail").

The optimizer in `latent_sweep_munich_jax.py:projected_grad_ascent` starts
at `z = z0` (the encoded user pose), takes a gradient step, then projects
**inside** the rho=2 ball if `|z_new| > rho_nat`.

Empirical distribution of `|z_0|` from the 132-frame AMASS plaza-walk pool
that the script actually uses:

```
min=2.20, max=4.32, mean=3.09, median=3.05
fraction with |z0| > 2.0: 100%
fraction with |z0| > 3.0: 57%
```

**Every encoded baseline pose lies outside the rho_nat=2 ball.** This means
the very first projected iterate immediately projects the user's natural
pose down to the rho=2 ball, throwing away ~30% of the natural pose's
information. The trajectory's "natural-pose-relative gain" from
`SINR(z0) -> SINR(K-th iterate inside ball)` is comparing apples to oranges:
the baseline is at the user's REAL pose (outside the ball), the result is
clamped to a ball that excludes that pose.

The "8/9 LOS + 8/9 NLOS within 1 dB of brute-force" reachability claim is
internally consistent — both gradient ascent and brute-force operate inside
the same rho=2 ball. But it is misleading to call this "reachability from
the user's baseline pose" when the very first step physically leaves the
baseline pose.

VPoser's prior mode is not at z=0. The official VPoser reconstruction-error
target was reached at the prior mean (z=0), but actual AMASS-encoded poses
have `|z|` distributed roughly as a chi distribution with 32 dof and
mean-mode shifted by the encoder's scale. With sigma_z ~ 1, you expect
`E|z| ~ sqrt(32) = 5.7`; the observed mean of 3.09 is consistent with a
posterior collapse around half the prior std. So rho_nat=2 is actually
**inside** typical encoded pose density, not bounding it from outside.

Either:
- (a) Loosen rho_nat to ~5 (covers >95% of encoded AMASS poses), and
  re-run reachability;
- (b) Anchor at z0 with a relative ball `|z - z0| <= rho`, as in the
  earlier `latent_sweep_munich.py` (RHO_Z=1.5 around z_0); or
- (c) Re-frame the metric as "max-SINR-in-natural-region" rather than
  "improvement from baseline pose", since the user is being asked to leave
  the baseline pose anyway.

The current code's choice (b is the old behavior; the new JAX path uses (a)
with rho_nat=2 absolute, NOT relative) means the optimization is asking the
user to do something physically arbitrary on every first step.

### 11. Body placement vs SI text (minor, mostly OK)

Paper SI Sec S2 (jsac2_v3_supp.tex line 254-257) says:

> The phone is held at chest height, 40 cm in front of the body centroid,
> at world position r_p = r_u + (-0.40, 0, 0.05) m, so its broadside
> faces the BS in all three regimes.

The 0.05 m vertical offset is for the **parametric scalar-loss companion**
described in the same paragraph (free-space, three loss bands). The actual
Munich numerical study (used by the reachability claim) places the phone
at `body z + 0.30 m` (1.5 m phone over 1.2 m body), per the trace data:
"phone at chest height" matches if "body centroid at navel" and "chest at
~1.5 m". This is not a bug; the SI text just doesn't make clear that the
0.05 m figure does not apply to Munich.

I verified placement consistency across all 18 Munich scenes:
- xy-distance phone-to-body = 0.400 m exactly
- z-offset 0.30 m
- body face_azimuth_rad = bs azimuth from body, to 0.1 deg (body always
  looks at the BS)

### 12. SINR_dB vs paper's R = log2(1+SINR) (cosmetic)

`_sinr_db_from_h` returns `10 log10(SINR)`, but the paper objective is
`R = log2(1 + SINR)`. They differ by a positive monotone transform at
fixed sign — `dR/dSINR > 0` always, `dSINR_dB/dSINR > 0` always. The
optimizer normalizes by `g/||g||`, so the direction is unchanged. The
"gain" reported in dB is the SINR change, not the rate change. Fine, but
the variable name in the code (`sinr_traj`) is honest while the paper
language sometimes calls this "rate gain" — minor framing issue.

## Tests run

1. `python JSAC2/code/test_pose_pipeline_jax.py` — passes (no assertions),
   prints VPoser err 1e-7, LBS err 0 mm, SINR delta 0.000 dB, autodiff
   FD err 1.3 (eps=1e-3 noise, see #5).
2. Repeat FD at eps in {1e-2, 1e-3, 1e-4, 1e-5, 1e-6, 1e-7, 1e-8} on z=0
   for z[0], z[5], z[7], z[17]. Convergence to autodiff at eps <= 1e-6.
3. Cosine similarity between autodiff gradient and full-32-D FD gradient
   at random z (sigma=1.5, |z|~7-8): cos ~ 1.0 at eps in {1e-6, 1e-7,
   1e-8}; cos in {-0.16, +0.28, +0.77} at larger eps where gates flip.
4. SMPL-X LBS parity vs official `smplx` package: 0.4 microns max across
   z in {0, randn(0.5), randn(1.5), randn(3.0)}.
5. Centroid parity: `_surface_centroid` matches `trimesh.Trimesh.centroid`
   to 1e-14 m.
6. `_axisangle_to_rotmat` Jacobian at aa=[0,0,0]: all NaN. At aa=[1e-12,
   1e-12, 1e-12]: finite (-8e-28).
7. End-to-end gradient at z=0 with `theta22 = zeros.at[1:].set(body_aa)`:
   finite. With explicit `theta22[0] = 0 * z[0]`: NaN at z[0].
8. Gate flip count at eta=0.4 step: 82/20908 facing flips, 52297/11M
   lit flips. At eta=0.0001: 0 facing flips, 11 lit flips.
9. Native-vs-full Kirchhoff equivalence at z=0: relative error 7e-16.
10. AMASS pose pool encoder norms: 132 samples, all `|z_0| > 2.0`, mean
    3.09, max 4.32.
11. Sionna `paths.cir(out_type='numpy')` returns complex64; `out_type='drjit'`
    returns `(re_TensorXf, im_TensorXf)` tuple; `paths.a` likewise.
12. `body_amp` magnitudes in saved Munich NPZs: mean 1.0, std 7.8e-17 —
    pure steering phase, no carrier phase or path amplitude.

## Files inspected

- `/home/user/aegis/JSAC2/code/pose_pipeline_jax.py`
- `/home/user/aegis/JSAC2/code/vposer_v2.py`
- `/home/user/aegis/JSAC2/code/scene_smplx.py`
- `/home/user/aegis/JSAC2/code/test_pose_pipeline_jax.py`
- `/home/user/aegis/JSAC2/code/animate_pose.py`
- `/home/user/aegis/JSAC2/code/kirchhoff.py`
- `/home/user/aegis/JSAC2/code/kirchhoff_jax.py`
- `/home/user/aegis/JSAC2/code/latent_sweep_munich.py`
- `/home/user/aegis/JSAC2/code/latent_sweep_munich_jax.py`
- `/home/user/aegis/JSAC2/code/scenes/munich_trace.py`
- `/home/user/aegis/JSAC2/paper/jsac2_v3.tex` (Sec VI.B, Algorithm 1)
- `/home/user/aegis/JSAC2/paper/jsac2_v3_supp.tex` (Sec S2, S3)
- Sionna v2.0.1 sources: `Paths.cir`, `Paths.a`
- `human_body_prior` v1 source for leaky_relu slope check

## Recommendations (priority-ordered)

1. **Fix `munich_trace.py` cir() unpacking** (issue #9). Use
   `out_type='numpy'` and treat the result as scalar complex per path.
   Re-run all 18 Munich traces and re-run the reachability sweep. This
   matters most.
2. **Reconcile rho_nat with the actual AMASS pose distribution** (issue #10).
   Either widen rho_nat to ~5 or anchor the ball at z_0 (the original
   `latent_sweep_munich.py` behavior). Update Algorithm 1 line 850-853
   accordingly. If kept as-is, document clearly that the "baseline pose"
   metric is comparing the user's actual pose against a clamped version
   inside the ball, and that the user is asked to physically leave the
   baseline on every first step.
3. **Fix the test** (issue #5). Use eps=1e-6 and add an `np.allclose`
   assertion. Optionally add a per-coordinate "cosine similarity between
   autodiff and centered-FD" check at small eps.
4. **Make `_axisangle_to_rotmat` numerically safe at aa=0** (issue #6).
   Add the small-angle Lie expansion fallback. Currently dormant but a
   landmine for any future code that makes global_orient or face joints
   differentiable in z.
5. **Fix the docstring** in `pose_pipeline_jax.py:236` ("trimesh-style
   volume centroid" -> "trimesh-style area-weighted surface centroid").
6. Optionally tighten the SI text on phone offset (z = +0.30 m for Munich
   vs the paragraph's +0.05 m for the parametric companion).

The pose pipeline itself (VPoser + SMPL-X LBS + world transform + native
Kirchhoff) is well-implemented and correct. Its critical dependency
(the Sionna body-path data) is not.
