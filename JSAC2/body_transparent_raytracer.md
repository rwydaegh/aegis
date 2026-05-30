# Body-transparent ray tracer in JSAC2: audit and fix sketch

## The question

> The ray tracing in `JSAC2/code` assumes that the body doesn't actually exist.
> Is this a big problem? If so, how do we fix it (theory + code)?

## What the code actually does

The Sionna RT scene used in every JSAC2 trace is the Munich buildings-only `.glb`.
The SMPL-X body mesh is never inserted into that scene. It is built, but only
consumed by the on-device Kirchhoff/PO renderer downstream.

Evidence:

- `JSAC2/code/scenes/munich_trace.py:229,252-253` — `s = load_scene(sc.munich)`,
  then `trace_one(s, bs_xyz, body_centroid)` and `trace_one(s, bs_xyz, phone_xyz)`.
  Both receivers are point devices.
- `munich_trace.py:81-93` — the only `scene.add(...)` calls in the codebase add
  `Transmitter` and `Receiver` points. A repo-wide grep for `scene.add`,
  `SceneObject`, `RadioMaterial` confirms no mesh is ever inserted.
- `munich_trace.py:50` — `BODY_Z = 1.20` is a target coordinate, not a body
  representation.
- `JSAC2/code/scene_smplx.py` builds the SMPL-X mesh; it is handed to
  `kirchhoff.Body` (`JSAC2/code/kirchhoff.py:40-108`) which only uses a trimesh
  `RayMeshIntersector` for **self-occlusion** (back-face cull plus optional
  body-vs-body ray test, never against other geometry).
- `kirchhoff.py:162-301` (and the JAX twin `kirchhoff_jax.py`) compute
  `h_body` from `BSPathDict` (paths arriving at the body centroid as plane
  waves) plus the phone position via single-bounce Kirchhoff/PO. This is
  the only stage that "knows" about the body.

So the body's effects in the simulation are limited to: self-shadowing of
its own triangles from the phone, BS-side back-face cull
(`-k_hat . n_hat > 0`), and per-triangle Fresnel reflection into the phone.
The body **never** acts as an obstacle, scatterer, or diffractor in the
Sionna trace.

## What the paper claims

`JSAC2/paper/jsac2_v3.tex:289-296` decomposes the channel as
`h = h_BS + h_body` and states:

> "$h_{\text{BS}}$ collects every BS-to-phone propagation path that does
> not interact with the body... $h_{\text{body}}$ is the body-mediated
> coefficient... **The split is exact by Maxwell linearity.**"

(The paper uses `\hBS` / `\hbody` macros; reproduced here with explicit
subscripts so the markdown renders.)

That phrasing is technically true for a clean superposition, but only if
`h_BS` were the body-removed reference of a trace that *did* include the
body, with body-interaction paths subtracted. The code does not do this. It
traces in a body-free scene and adds an analytic `h_body` increment computed
in isolation.

The limitations paragraph (`jsac2_v3.tex:1336-1350`) covers single-user,
back-face cull, and sub-6 GHz Fabry-Perot. It does **not** mention that the
tracer is body-transparent.

## Is it a big problem?

**Yes for any LOS geometry where the body sits between BS and phone, and for
claims about body-induced multipath / self-shadowing of scene multipath.
Not fatal for the NLOS RIS-rescue headline, and front-side APD is fine.**

Three regimes:

1. **NLOS body-as-RIS rescue (the headline 100+ dB SINR result).** The LOS
   is already extinguished by buildings, so `h_BS` is dominated by building
   multipath. Whether the body would also have shadowed that multipath is a
   second-order perturbation. The qualitative pose-rescues-NLOS claim is
   probably safe.

2. **LOS with body as blocker (back pocket, body-behind-phone, BS-behind-back).**
   `h_BS` keeps the direct ray that should have been attenuated ~10-20 dB by
   the torso. `h_body` is then *added* on top, rather than substituting for
   the blocked direct ray. **Systematic double-counting.** The cascaded
   prediction will be biased optimistic in exactly the configurations the
   paper waves at as "interesting".

3. **Peak APD vs ICNIRP.** Front-of-torso triangles see full BS illumination
   from a body-free trace, which is approximately correct. Back-of-torso
   triangles see only paths that took the building-only route around the
   body, never short body-grazing diffraction. The "two orders below ICNIRP"
   margin understates exposure on body-shadowed sides — though if the
   reported peak APD lives on the front face, the headline number survives.

The deeper issue is honesty: "exact by Maxwell linearity" is the line a
reviewer will catch. The decomposition becomes exact only when `h_BS` is
the body-removed *reference* corresponding to a body-present trace, not when
both terms are computed in independent worlds.

## Fix sketch: theory

The intended decomposition is:

$$
h_{\text{meas}} \;=\; h_{\text{BS}} + h_{\text{body}}
$$

where $h_{\text{meas}}$ is the channel with the body in the scene and
$h_{\text{BS}}$ is the same scene with the body removed. By Maxwell
linearity this defines $h_{\text{body}}$ uniquely as a difference of two
full electromagnetic problems — not as an additive PO render computed from
body-free incident fields.

Two consistent routes:

**(A) Reference-subtraction.** Run the Sionna trace twice per scene: once
with the SMPL-X mesh inserted (`h_meas`) and once without (`h_BS`). Define
`h_body := h_meas - h_BS`. The analytic Kirchhoff render becomes the
*on-device prediction* of $h_{\text{body}}$, and the calibration residual
absorbs the gap between the prediction and the tracer's body interaction.
This is the cleanest interpretation and matches the cascaded structure
already in the paper. Cost: 2x trace time, plus a tissue `RadioMaterial`
spec.

**(B) Body-as-scene-object end-to-end.** Trace BS->phone once with the
SMPL-X mesh in the scene; skip the analytic PO render and read $h$ off the
tracer. This is more physical but loses pose differentiability, which is
the paper's contribution. So (B) is not viable as a replacement, only as a
ground truth.

**(C) Honest hybrid.** Insert a *coarse body proxy* (capsule / cylinder
torso) into the Sionna trace so that `h_BS` includes correct shadowing of
building multipath by a generic torso. Then add the analytic per-pose
$h_{\text{body}}$ as a *delta correction* relative to that proxy. Cheaper
than (A), still autodiff-friendly. Cost: pick a proxy, accept a residual
mismatch between proxy and SMPL-X.

I would recommend (A) for the calibration / ground-truth campaign and (C)
for production trace runs that need pose gradients.

## Fix sketch: code

Minimal change set to make (A) work:

1. **New helper** in `JSAC2/code/scenes/munich_trace.py`:
   ```python
   def _add_body_to_scene(scene, mesh: trimesh.Trimesh, freq_hz: float):
       mat = RadioMaterial(
           name="tissue_avg",
           relative_permittivity=eps_r_tissue(freq_hz),
           conductivity=sigma_tissue(freq_hz),
       )
       obj = SceneObject.from_trimesh(mesh, radio_material=mat)
       scene.add(obj)
       return obj
   ```
   `eps_r_tissue`, `sigma_tissue` should be averaged Cole-Cole values; the
   existing `src/aegis/tissue/` module already provides them.

2. **Trace twice per scene.** Modify `trace_one` (or wrap it) so each
   scene index produces two NPZs:
   ```
   outputs/munich/traces/scene_NN_meas.npz   # body in scene
   outputs/munich/traces/scene_NN_bsref.npz  # body removed
   ```
   `h_BS` is then `h_bsref` directly (current `scene_NN.npz`), and the
   "true" residual `h_body_meas = h_meas - h_bsref` becomes the calibration
   target for the analytic Kirchhoff render. Cost: ~2x trace time per scene.

3. **Calibration update** in `JSAC2/code/calibration.py` /
   `calibration_run.py`: change the fitting target from `h_body_PO` alone
   to the difference `h_meas - h_bsref`. The current calibration is
   implicitly fitting to "whatever the PO render says is body
   contribution", which is unfalsifiable. Refitting against tracer-derived
   ground truth gives a real residual and a real error bar.

4. **SVD / pose-sensitivity scripts** (`svd_spectrum.py`, `pose_sweep.py`,
   `latent_sweep_munich.py`, `fig_hero_*`): no change to the
   pose-differentiable forward model. The only switch is which `h_BS`
   they consume — point them at `scene_NN_bsref.npz`.

5. **Paper text** (`JSAC2/paper/jsac2_v3.tex`):
   - Section II.B (`:289-296`): drop "exact by Maxwell linearity" or
     qualify it: "exact by Maxwell linearity when $h_{\text{BS}}$ is the
     body-removed reference of the same scene." Explain the two-trace
     protocol.
   - Limitations (`:1336-1350`): add a bullet noting that the on-device
     prediction is the analytic PO render and that the tracer-derived
     ground truth is from option (A) above. State the gap as a measured
     calibration residual rather than as an assumption.

## Estimated effort

- Code: ~1 day for the two-trace pipeline, ~0.5 day to retrain calibration,
  ~1 day to re-run the 18 Munich scenes. Sionna scenes with a single body
  object are cheap; the dominant cost is re-running everything downstream.
- Theory write-up: a few paragraphs in Section II.B + one bullet in
  limitations. The decomposition is unchanged; only the interpretation of
  `h_BS` shifts.
- Risk: the calibration residual will probably grow, especially in
  body-as-blocker LOS scenes. That is a feature, not a bug — it is what
  honest reporting looks like.

## Relevant files

- `JSAC2/code/scenes/munich_trace.py` — main ray-trace driver, body absent
- `JSAC2/code/scenes/munich_setup.py` — scene loader, buildings only
- `JSAC2/code/scene_smplx.py` — SMPL-X mesh built only for Kirchhoff `Body`
- `JSAC2/code/scene_nlos.py:64-103` — analytic LOS paths, no occlusion check
- `JSAC2/code/kirchhoff.py:40-108, 162-301` — `Body` self-shadow + PO render
- `JSAC2/code/kirchhoff_jax.py` — same logic, JAX
- `JSAC2/paper/jsac2_v3.tex:289-296` — the "exact by Maxwell linearity" claim
- `JSAC2/paper/jsac2_v3.tex:1336-1350` — limitations, missing this caveat
