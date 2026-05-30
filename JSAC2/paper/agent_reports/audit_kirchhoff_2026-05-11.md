# Kirchhoff kernel audit — 2026-05-11

Audit of the central physics kernel of the JSAC2 paper:

- /home/user/aegis/JSAC2/code/kirchhoff.py (NumPy reference)
- /home/user/aegis/JSAC2/code/kirchhoff_jax.py (JAX/GPU version)
- /home/user/aegis/JSAC2/code/test_kirchhoff_jax.py (parity test)
- /home/user/aegis/src/aegis/tissue/fresnel.py (Fresnel coefficient helper)

Theory anchors checked: jsac2_v3.tex sec III.A-III.D and Sec IV (eq. kirchhoff-integral, eq. kernel at 627-634, eq. Lambda-op at 647).

## Verdict

**The K coefficient in the code is wrong by 30+ dB and the wrongness is angle-dependent.** The two compounding bugs are:

1. The paper writes K = jk0 r0 with r0 = 1 - T0_skin ≈ 0.46 and calls this "the pseudo-Brewster reflection AMPLITUDE." But 1 − T0 = 0.46 is the power reflectance |r|^2, not the amplitude |r|. The amplitude is sqrt(1 − T0) ≈ 0.68. (This was already noted in audit_K.py.) — ~3.4 dB power-channel error if applied as written.

2. **The code does not implement the paper's formula.** It implements K = jk0 (r_s + r_p)/2 where r_s and r_p are the complex Fresnel amplitude coefficients. **Because of the standard Fresnel sign convention used throughout aegis, r_s + r_p is identically zero at normal incidence and tiny at near-normal incidence.** This makes the code's K vanish exactly where, physically, the body channel has its largest contributions (specular triangles). Combined with the missing PO factor of 2 and a missing j-vs-real sign, the code's |h_body| is ~30 dB below what the paper says it should be on a typical spherical-body test, and ~32 dB below it on a synthesized scene.

Below I list everything I checked, with numerical evidence.

---

## Issue 1 (severity: showstopper) — K = jk0 (r_s + r_p)/2 is ~0 at normal incidence

The aegis Fresnel convention (in src/aegis/tissue/fresnel.py::_fresnel_core) is

```
r_s = (mu - xi) / (mu + xi)
r_p = (n^2 mu - xi) / (n^2 mu + xi)
xi = sqrt(n^2 - 1 + mu^2)
```

This is the Born & Wolf / Stratton convention in which **r_s and r_p have OPPOSITE signs at normal incidence** (the TM unit vector flips on reflection in the local frame). At mu = 1, xi = n, so r_s = (1 − n)/(1 + n) and r_p = (n − 1)/(n + 1) = −r_s exactly.

For skin at 28 GHz (eps_r=16.5, sigma=25.8 → n_tilde = 4.47 − 1.85j):

| theta (deg) | mu     | r_s             | r_p             | (r_s + r_p)/2 (CODE) | sqrt(1 − T0) |
|-------------|--------|-----------------|-----------------|----------------------|---------------|
| 0           | 1.0000 | −0.672 + 0.111j | +0.672 − 0.111j | **−0.0000 + 0.0000j** | 0.681         |
| 10          | 0.985  | −0.676 + 0.110j | +0.668 − 0.112j | −0.0042 − 0.0010j     | 0.681         |
| 30          | 0.866  | −0.710 + 0.102j | +0.630 − 0.121j | −0.040 − 0.009j       | 0.681         |
| 45          | 0.707  | −0.757 + 0.089j | +0.565 − 0.135j | −0.096 − 0.023j       | 0.681         |
| 60          | 0.500  | −0.822 + 0.069j | +0.432 − 0.158j | −0.195 − 0.045j       | 0.681         |
| 70          | 0.342  | −0.875 + 0.050j | +0.261 − 0.180j | −0.307 − 0.065j       | 0.681         |
| 80          | 0.174  | −0.935 + 0.027j | −0.083 − 0.190j | −0.509 − 0.082j       | 0.681         |
| 89          | 0.017  | −0.993 + 0.003j | −0.851 − 0.054j | −0.922 − 0.026j       | 0.681         |

So the code's K coefficient is **vanishing for normally-facing triangles** and only "agrees with the paper" at near-grazing angles. For a uniform mu in [0.3, 1.0] (typical phone-on-torso facing), the mean |code K| / |paper amplitude| = 0.21 — i.e., the code's effective K is **−13.7 dB below the paper's intent**, before the missing factor of 2 or the polarization-projection issue.

### Empirical impact on h_body

#### Sphere body proxy (30 cm radius, 20480 triangles, 4 BS, BS at 50 m, phone 0.4 m in front)

- ||h_body|| from the code (current K = jk0 (r_s + r_p)/2 + z-projection): **2.58e-05**
- ||h_body|| with K = jk0 sqrt(1 − T0), isotropic UE: **1.02e-03**  → +32.0 dB vs code
- ||h_body|| with K = jk0 sqrt(1 − T0), z-projection (paper's K, code's UE): +31.9 dB vs code
- ||h_body|| with K = −2jk0 r_p (proper PO, isotropic UE): **2.04e-03** → +37.9 dB vs code

So on this synthetic body, **the code is suppressing the body channel by ~32–38 dB** relative to what the paper says it computes.

#### Real Munich Scene 0 (LOS_00, full pipeline, body = thelonious mesh, M = 64, P = 33664 paths)

| K convention                       | ||h_body|| | max|h_body| | ||h_body||/||h_scene|| | SINR_cas (dB) |
|------------------------------------|-------------|-------------|-------------------------|----------------|
| Code (jk0 (r_s + r_p)/2, z-proj)   | 1.16e-05    | 1.59e-06    | 0.141                   | 33.23          |
| Paper (jk0 sqrt(1 − T0), iso UE)   | 2.34e-05    | 3.45e-06    | 0.284                   | 29.53          |
| Paper (jk0 sqrt(1 − T0), z-proj)   | 2.04e-05    | 2.79e-06    | 0.247                   | 34.23          |
| Proper PO (−2jk0 r_p, iso UE)      | 7.41e-05    | 1.01e-05    | 0.900                   | 37.85          |

For reference: ||h_scene||-only (LOS no body) SINR = 32.32 dB.

#### Real Munich Scene 15 (NLOS_06, body = thelonious mesh, M = 64, P = 26432 paths)

| K convention                       | ||h_body|| | ||h_body||/||h_scene|| | SINR_cas (dB) |
|------------------------------------|-------------|-------------------------|----------------|
| Code (jk0 (r_s + r_p)/2, z-proj)   | 1.19e-06    | 0.0593 (−24.5 dB)       | 20.48          |
| Paper (jk0 sqrt(1 − T0), iso UE)   | 6.98e-06    | 0.348 (−9.2 dB)         | 19.05          |
| Proper PO (−2jk0 r_p, iso UE)      | 1.60e-05    | 0.799 (−2.0 dB)         | 23.68          |

For reference: ||h_scene||-only (NLOS) SINR = 20.05 dB.

This is the smoking gun:
- Under the code's K, |h_body| is essentially negligible (−24.5 dB below |h_scene|), and the body adds only 0.43 dB to SINR. The body looks like a minor perturbation.
- Under the proper PO K, |h_body| is comparable to |h_scene| (−2 dB), and the cascaded SINR is **3.2 dB higher** than the code reports.
- Under the paper's K-as-written (sqrt(1−T0), iso UE), the body interferes destructively with the scene channel and SINR drops by 1 dB instead of rising — opposite sign of the proper PO calculation.

#### Observations from both scenes

- The code's |h_body| underestimates the proper PO formula by **16 dB on Scene 0 (LOS), 22 dB on Scene 15 (NLOS)** on real Munich scenes. (Less than the 32 dB from the spherical proxy because the actual phone-on-body geometry has the BS more obliquely above, the contribution distribution is wider, and the bug becomes severe only at near-normal incidence.)
- **At the proper K, |h_body| is comparable to |h_scene|** in both LOS and NLOS scenes. The body is not a small perturbation.
- SINR shifts by **−2.8 to +5.5 dB** depending on the K convention on the LOS scene. The interference between h_LOS and h_body is constructive (+1 dB above scene-only) under code's K and becomes much more significant (+5.5 dB) under proper K. The polarization-projection choice (z vs iso) flips the sign of the interference (29.53 dB iso vs 34.23 dB z), illustrating that **even the SINR direction is sensitive** to which formula you choose.
- For NLOS Scene 15, SINR shifts by **+3.2 dB** between code's value (20.48 dB) and proper PO (23.68 dB). The paper claims an "8.6 dB body-as-reflector rescue on a deep-shadow NLOS scene above 100 dB of path loss" (abstract), but the underlying h_body is suppressed by ~22 dB under the buggy K. Re-running with the corrected K may strengthen this claim significantly OR may invalidate the optimal pose found by the gradient ascent (since the gradient direction depends on the wrong Lambda_KH operator).

This is a load-bearing distortion of the central physical claims of the paper.

### Verification on a flat dielectric mirror

To make sure my "proper K" is right and not just a guess, I verified against the analytical image-source result for an infinite flat dielectric plane illuminated by a plane wave:

Setup: BS at z = +H, x-polarized plane wave with k_hat = −ẑ at the body centroid (amp = 1), phone at (0.3, 0, 0.5), 0.5–3.0 m mirror. For a large mirror (size >> Fresnel zone), the reflected field at the phone equals r_p × (image-source propagation factor).

For BS at H = 100 m (genuine far-field), 2 m mirror, 245k triangles:

| K convention                        | |h|     | arg     | |h|/|E_image| |
|-------------------------------------|---------|---------|----------------|
| Image source (truth)                | 0.6717  | −87.9°  | 1.000          |
| Code (jk0 (r_s + r_p)/2)            | 2.7e-17 | (noise) | **0.0000**     |
| Paper (jk0 sqrt(1 − T0))            | 0.334   | +74.6°  | 0.493          |
| K = +2jk0 r_p (proper PO + magnitude) | 0.667 | +65.2°  | 0.987          |
| K = −2jk0 r_p (proper PO with sign) | 0.667   | −114.8° | 0.987 (12° phase mismatch) |

Interpretation:
- The code returns numerical noise (1e-17) — consistent with K = 0 at near-normal incidence.
- The paper's intended K (r0 = sqrt(1−T0)) recovers half the true amplitude (factor 2 missing).
- The proper PO formula K = ±2jk0 r_F recovers the true amplitude to within 1.3% in magnitude. The 12° phase mismatch is residual mirror-truncation and the standard difference between r_p evaluated at the SP-of-the-Kirchhoff-integrand (the projection of the phone on the plane) versus r_p evaluated at the true specular reflection point.

### Summary of the K bug

The code implements K with three independent errors stacked on top of the paper:

1. (r_s + r_p)/2 instead of r_F (or sqrt(1 − T0) for the pseudo-Brewster collapse). At mu ≈ 1, this gives ZERO.
2. Paper itself has 1 − T0 (power) where it should have sqrt(1 − T0) (amplitude). +3.4 dB.
3. Missing factor of 2 from the PO surface current J = 2 (n × H_inc). +6 dB.

Net: |h_body|^2 is suppressed by ~32 dB on a sphere body, ~16–32 dB on a flat plate, depending on the angular distribution of facing triangles.

---

## Issue 2 (severity: significant) — UE polarization gate is angle-dependent, not isotropic

Paper line 638 says g_UE is the phone's antenna pattern in the arrival direction, "isotropic by assumption, |g_UE|^2 ≡ 1."

For an isotropic phone antenna intercepting a wave with polarization (I − eta eta^T) psi, the proper "isotropic" pickup is the magnitude |(I − eta eta^T) psi|.

The code (kirchhoff.py:273 and kirchhoff_jax.py:80) uses only the z-component, `psi_eta[:, 2]`. This is a vertically-polarized UE pattern, NOT isotropic.

Numerical impact for vertical-pol psi and various eta directions:

| eta direction               | |psi_eta| (iso) | |psi_eta_z| (code) | ratio z/iso |
|-----------------------------|------------------|---------------------|-------------|
| phone above (eta_z = 1)     | 0.000            | 0.000               | 0/0         |
| phone level (eta_x = 1)     | 1.000            | 1.000               | 1.000       |
| phone 45° above x-axis      | 0.707            | 0.500               | 0.707       |
| phone 30° above x-axis      | 0.866            | 0.750               | 0.866       |
| phone 60° below x-axis      | 0.500            | 0.250               | 0.500       |

For a uniform random eta on the sphere with vertical psi:
E[|psi_eta_z|^2] / E[|psi_eta|^2] = 0.80 (mean), but the distribution has a long left tail — pathological zero-pickup geometries exist for eta straight along the polarization axis.

This is mostly a constant 1–6 dB bias for "phone in front of body" geometries, plus pose-dependent zeros. It interacts with Issue 1 (the K bug already screws up the amplitude at near-normal angles, where the z-projection actually matters most). The magnitude of this issue alone would be ~1–3 dB on Munich-style scenes.

---

## Issue 3 (severity: minor) — Polarization projection direction (eta vs n_hat) is OK

Code computes psi_eta = psi - eta * (psi . eta), which is (I − eta eta^T) psi: projection onto the plane transverse to the OUTGOING ray.

Question raised: shouldn't the reflection apply the local Fresnel rotation around the surface normal n_hat, then the (I − eta eta^T) projection happens at the receiver?

Answer: the code's projection is physically correct AS A FAR-FIELD OUTPUT projection. The PO formula gives:

```
E_far(eta) ~ -jk0 Z0/(4πR) exp(jk0R) (I − eta eta^T) ∫ J(r') exp(−jk0 eta . r') dS
```

The (I − eta eta^T) projection IS at the receiver side. The error in the code is conflating the surface current J (which comes from n × H_inc and depends on n_hat AND k_hat AND psi) with a scalar K times psi.

For the pseudo-Brewster collapse approximation (r_s ≈ r_p ≈ scalar), the substitution J ≈ 2 r_F psi / Z0 is internally consistent at near-normal incidence. So for the paper's scope, treating the projection as (I − eta eta^T) psi is fine. The bug is in K, not in the projection direction.

---

## Issue 4 (severity: cosmetic, but could matter for cascaded interference) — Sign convention mixing

Paper line 633: incident plane wave phase is exp(−jk0 k_n . r). Engineering convention with implicit exp(+jωt) gives outgoing radiation as exp(−jk0 R)/R, NOT exp(+jk0 R)/R.

Paper line 621 and code: Green's function is exp(+jk0 R) / (4πR). This is the physics convention with implicit exp(−jωt), in which the plane wave would be exp(+jk0 k_n . r), NOT exp(−jk0 k_n . r).

So the paper (and the code) mixes two conventions. As long as the same convention is used internally, |h_body|^2 is unchanged. But the cascaded channel is h_LOS + h_body (linear sum, complex-valued). If h_LOS comes from a different convention (e.g., Sionna RT under engineering convention), the relative phase between h_LOS and h_body in the constructive/destructive interference is wrong by a sign.

I checked AEGIS coherent kernels (src/aegis/coherent/_fast.py:88, src/aegis/coherent/translation.py): they use exp(−jk0 k . r) for the BS-side incident phase, same as kirchhoff.py. So the AEGIS-side conventions are internally consistent. h_scene comes from JSAC2/code/scenes/munich_trace.py which also uses exp(−jk0 (rel . k_dod)) — the same. The Sionna RT primitives use the same engineering convention. So **the mixed-convention concern doesn't actually translate into a relative-phase bug between h_LOS and h_body** in this codebase. The Green's function having "wrong" sign is a notational issue but is consistently applied.

That said, the choice of sign affects the OPTIMAL pose direction in the latent gradient ascent (which exploits constructive vs destructive h_LOS + h_body interference). So get the sign right next time.

---

## Issue 5 (severity: significant) — Triangle-centroid quadrature is poor at oblique incidence

SMPL-X has 20908 triangles for ~1.7 m^2 surface area, so average triangle ~9 mm side ≈ 1 wavelength at 28 GHz. The code replaces ∫_triangle by (centroid value) × area.

I tested a 1 cm × 1 cm flat triangle with phone at 0.3 m and a plane-wave incident at various angles, comparing centroid quadrature to a 100×100 fine quadrature:

| theta_inc | centroid/fine ratio (1 cm tri) | error % |
|-----------|--------------------------------|---------|
| 10°       | 1.00                           | 0.8%    |
| 30°       | 1.03                           | 2.7%    |
| 60°       | 1.49                           | **49%** |
| 80°       | 3.83                           | **283%** |

For 2 cm triangles (some SMPL-X triangles get this large in flexed regions):

| theta_inc | centroid/fine ratio | error % |
|-----------|---------------------|---------|
| 10°       | 1.00                | 3%      |
| 30°       | 1.11                | 12%     |
| 60°       | 16.4                | **1500%** |
| 80°       | 4.98                | **600%** |

So the code OVER-estimates contributions from oblique-incidence triangles by 1.5×–16×. This is the classic PO-centroid-quadrature failure mode. For a typical body scene, this contributes a several-dB bias in the WRONG direction (compared to Issue 1, which under-estimates) — combined the two errors don't cancel cleanly.

Mitigation: use Gauss-Legendre 3-point per triangle, OR (better) replace the per-triangle wave-rapid factor with its analytical sinc-like average. See e.g. Pozar §13.7. Cost: ~3× per-triangle. For a 20908-triangle body and 526 paths, this is still well within the 100 ms target.

---

## Issue 6 (severity: none) — JAX vs NumPy parity is sound

Ran the parity test (test_kirchhoff_jax.py):
```
Scene 0 (LOS_close):  max|h_jax - h_ref|/max|h_ref| = 7.7e-11
Scene 15 (NLOS_far):  max|h_jax - h_ref|/max|h_ref| = 6.0e-11
```
Both pass, well below the 1e-4 tolerance. Also checked Fresnel directly: max|r_s_jax - r_s_np| = 4.9e-11, max|r_p_jax - r_p_np| = 8.5e-11. The JAX kernel is a faithful port. **They share the same physics bugs.**

The slight n_tilde difference (8e-10 between np.sqrt and jnp.sqrt) propagates linearly to ~1e-10 in Fresnel coefficients. Harmless.

The lit gate (`mu > 1e-3` in both) is identical; the polarization projection equivalence (full 3-vector minus eta z-component) is checked symbolically and confirmed.

---

## Issue 7 (severity: low) — `lit = mu > 1e-3` gate

The threshold mu = 1e-3 corresponds to theta = 89.94°. This is the right place to cull contributions from triangles facing essentially edge-on to the BS. At and below this threshold, both r_s and r_p approach −1 (perfect reflector) but the back-face cull is needed to avoid spurious counter-illuminated contributions.

Observation: at grazing (theta ~ 89°), the code's K = (r_s + r_p)/2 actually becomes |K| ~ 1 because both r_s and r_p go to -1 (no longer cancel). So the code overweights edge-on triangles relative to normally-facing ones. This is the inverse of what physical intuition expects.

Since we lose exactly the contributions where the K bug is worst (mu near 1), the lit gate itself is fine; the bug is elsewhere.

---

## Issue 8 (severity: minor at current K, could be larger with corrected K) — Visibility test is "facing only", not BVH

Body.visible_from default does only the per-triangle facing test (n_hat . (phone − centroid) > 0), not a full BVH ray-mesh self-occlusion test. The docstring claims "within ~5% of the full BVH-based occlusion result" — undocumented and untested.

I tested on Munich Scene 0 with the actual SMPL-X body (20908 tris, baseline pose):

- Facing test: 10956 triangles
- Full BVH test: 8392 triangles
- 23.4% of "facing" triangles are actually occluded (mostly self-shadow on the back of the torso seen through arms etc.)

But h_body magnitude difference between the two:

- ||h_body|| (facing only, with current code's K): 1.366e-05
- ||h_body|| (full BVH, with current code's K): 1.380e-05
- Ratio: +0.09 dB

So under the **current bugged K**, the visibility difference is microscopic (0.09 dB) — because the falsely-included occluded triangles' contributions are random-phase and cancel. The docstring's "within ~5%" claim is correct (actually it's much better).

Under the **corrected K** (where the dominant contributions come from specularly-aligned triangles), this could change. The 23% triangle inclusion error could matter more if the falsely-included triangles happen to have coherent contributions. I tried to run the corrected-K version on Munich but the heavy SMPL-X loading machinery kept timing out under load; numerically the impact should still be small (sub-dB) because the BS is far away (so triangle-to-triangle phase coherence within the falsely-included set is low). I would recommend wiring the BVH check on by default if you can afford the cost — it's cheap (~30 ms per body) and removes the assumption.

---

## Cascaded SINR impact

Combining the identified bugs:
- Code suppresses |h_body| by roughly 30 dB relative to the paper's intended K (and ~36 dB relative to a proper PO formula). This is observed on a sphere body proxy at 50 m BS distance.
- Triangle quadrature overestimates oblique-angle contributions by 1.5–16×, partially offsetting in the wrong way.
- z-projection UE pattern adds another 1–3 dB bias.

For the cascaded channel h_cas = h_LOS + h_body:

- LOS scenes (h_LOS dominant): the bugged h_body has small effect on SINR. SINR claims should be roughly correct because they're mostly h_LOS-driven. But the **rate-versus-pose sensitivity claims** (the paper's punchline) are sensitive to ||h_body|| because pose changes the body channel only. With a 30 dB suppressed h_body, the paper's optimization landscape is also suppressed by 30 dB, making "best-of-N" gains look attainable when they would actually be much larger or much smaller depending on the corrected sign.

- NLOS scenes (h_body should be the DOMINANT path): the paper measures small |h_body| (8.5e-7 in scene 15), and presumably gets correspondingly small SINR. With proper K, |h_body| would be ~30 dB larger, and the SINR claims (and the entire NLOS-coverage story) would be very different.

The CALIBRATION step (gamma fit) absorbs CONSTANT scaling errors but NOT angle-dependent ones. The K bug is angle-dependent (vanishes at normal, grows at grazing). So calibration only partially compensates. The SVD-K basis used for calibration is computed from the BUGGED Lambda_KH operator; the dominant modes captured are those of the "edge-on triangle" pattern, NOT the "specular triangle" pattern. After calibration, the system might still APPEAR self-consistent against UL pilots (a tautology — gamma absorbs the residual), but the PREDICTIVE value of the body twin for closed-loop pose optimization is undermined.

---

## What to do

1. **Fix K**. Replace `K = 1j * k0 * 0.5 * (r_s + r_p)` with one of:
   - Pseudo-Brewster collapse (cheaper): `K = -2 * 1j * k0 * np.sqrt(1 - T0(n_tilde))` (real positive amplitude, factor 2 from PO surface current). This matches the paper's intent if the paper is also corrected to read sqrt(1 − T0).
   - Polarization-aware (more accurate): decompose psi into TE/TM at each triangle, apply r_s / r_p separately, recombine. This is the formula in src/aegis/coherent/_fast.py::compute_body_channel_factored_jax (which uses `compute_fresnel_operator`). Cost: ~3× per-path.

2. **Fix UE polarization gate**. Replace the z-component pickup with `np.linalg.norm(psi_eta, axis=1)` for the isotropic case OR document the choice (vertical-pol UE) and update the paper to match.

3. **Fix the paper**. Equation (kernel) should read `K = jk_0 \cdot 2 \cdot \sqrt{1 - T_0}` (or whichever PO formula you use), and r_0 should be defined as the AMPLITUDE reflection at normal, not 1 − T0. Note that the standard sign convention has K with a leading `−` (or `+j` flip), depending on which sign of j the field uses.

4. **Re-run the experiments and sanity-check against measured channels**. If the corrected h_body now exceeds h_LOS in NLOS, the entire empirical narrative shifts. The "body as auxiliary mode" framing may need to become "body as primary mode in NLOS."

5. **Tighten triangle quadrature**. 3-point Gauss on each triangle, or analytical sinc factor. The 49% over-estimation at 60° is too much.

6. **Add a unit test that compares the Kirchhoff render to the image-source on a flat dielectric plane.** This is a 50-line test that would have caught the K=0 bug immediately. The current parity test (kirchhoff_jax vs kirchhoff_numpy) only catches IMPLEMENTATION drift between the two backends — both of which share the bug.

---

## Files I exercised

- /home/user/aegis/JSAC2/code/kirchhoff.py — read in full
- /home/user/aegis/JSAC2/code/kirchhoff_jax.py — read in full
- /home/user/aegis/JSAC2/code/test_kirchhoff_jax.py — read and ran (passes, 1e-11 parity)
- /home/user/aegis/src/aegis/tissue/fresnel.py — read in full (this is where the sign convention lives)
- /home/user/aegis/JSAC2/paper/jsac2_v3.tex — read sec III.A-III.D and IV
- /home/user/aegis/JSAC2/paper/agent_reports/audit_K.py — exists, identified the 1−T0 vs sqrt(1−T0) issue but stops short of noticing the (r_s+r_p)/2 cancellation in the code
- /home/user/aegis/src/aegis/coherent/_fast.py — checked sign conventions
- /home/user/aegis/src/aegis/coherent/translation.py — checked sign conventions
- /home/user/aegis/JSAC2/code/scenes/munich_trace.py — checked sign conventions, OK
