# Munich Sionna RT scene audit (JSAC2, paper v3)

Date: 2026-05-11
Scope: paper Sec II.A (lines 270-296), Sec V.E (lines 974-993, also referenced as VIII.C),
and the supporting Munich-scene plumbing in `JSAC2/code/scenes/`, `scene_smplx.py`,
`scene_nlos.py`, and `pose_pipeline_jax.py`. Trace data audited from
`JSAC2/code/outputs/munich/traces/scene_NN.npz` (May 10, 2026 build).

## TL;DR

The Munich RT setup is technically correct in every load-bearing physics aspect:
the body is excluded from the Sionna RT scene (so the `h = h_BS + h_body` Maxwell
split is clean), all 18 Rx are present with correct LOS/NLOS labels and span the
claimed bounding box, the `8x8` URA at lambda/2 spacing is correctly placed at
`(8.5, 21.7, 35) m`, the panel-normal vector matches the paper to two decimals,
the steering ramp is consistent across `munich_trace.py` and the JAX kirchhoff
pipeline, and the Sionna RT trace settings (depth 5, specular + refraction +
edge diffraction enabled, diffuse off, 1e7 samples, 2e5 max paths) match the
paper word for word. Sionna RT v2.0.1 is the installed version.

But there are **three substantive issues** that would be flagged in review:

1. **The "scene loss in dB" numbers in Sec VIII.D and the hero caption are
   computed from `20*log10(sum_m |h_scene[m]|)` (an L1-norm of the per-element
   complex channel), not the standard `10*log10(||h||^2)`.** They are off by
   approximately +18 dB everywhere ( = `10*log10(M=64)` for coherent paths).
   "Scene loss -109 dB" for hero scene 17 is actually `-127 dB` under the
   conventional channel-power definition. The SINR numbers are unaffected
   (they are computed correctly from `||h||^2`).
2. **Hero scene 17 has only 25% of body-incident energy from the front of the
   body.** The body is set to face the BS, but for the deep-NLOS scene 17,
   dominant arrivals come from buildings to the north and west, *not* the BS
   to the south-east. The body therefore presents its back/sides to most
   incident energy. This is a defensible modeling choice (user is presumed
   to be looking at phone, which faces BS), but it should be acknowledged
   because it reduces `||h_body||^2` versus a "face the dominant arrival"
   convention by an unquantified factor.
3. **NLOS path counts are 248 mean (range 122 to 413), not "~300" as claimed.**
   LOS path counts are 456 mean (range 348 to 526), not "~500". Off by about
   10-15% but no scene is starved.

The "exact split by Maxwell linearity" claim (Sec II.A line 296) holds because
the body is genuinely absent from the Sionna RT scene; only point-Tx and
point-Rx are added (`munich_trace.py` lines 88-93). All scene-side multipath
captured by `h_BS` is body-free.

Below, each numbered audit item from the prompt is addressed in turn.

---

## Item-by-item findings

### 1. BS placement consistency

**PASS.** `munich_bs.json` and `munich_setup.py` both store
`[8.5, 21.7, 35.0]`. `munich_rx.json` carries the same value. `munich_trace.py`
loads from `munich_rx.json` and uses it for `bs_xyz`. The trace NPZ files all
record `bs_pos = [8.5, 21.7, 35.0]`. The paper claim (line 927) matches.

### 2. Downtilt vector / steering ramp consistency

**PASS.** The code computes the panel normal as
`n = (target - bs) / ||target - bs||` with `target = (33, 91, 1.5)` and
`bs = (8.5, 21.7, 35)`, yielding
`n = (0.30330, 0.85791, -0.41472)`,
which rounds to the paper's `(0.30, 0.86, -0.41)` to two decimals.

The 64 element positions are placed in the plane orthogonal to `n` using
Gram-Schmidt against world `z`. Verification:
- max |(p_m - center) . n| < 4e-15 (perfectly in-plane, double-precision noise);
- spacing = 5.353 mm = lambda/2 at 28 GHz exactly;
- mean of element positions = panel center (no drift).

The steering ramp is:
- `munich_trace.py:189`: `element_phase = np.exp(-1j * k0 * (rel @ k_dod.T))`
   where `rel = bs_positions - bs_center`, used for the body-incident bundle;
- `munich_trace.py:216`: same formula, used for the phone `h_scene`;
- `pose_pipeline_jax.py:334`: `elem_phase = jnp.exp(-1j * k0 * (rel @ k_dod.T))`
   used by the Kirchhoff body render at gradient time.

All three use the same `(bs_pos[m] - bs_center) . k_dod` planewave convention
with consistent sign. Per-element delay variation is captured analytically
through this ramp; the per-element 1/r amplitude variation is dropped (justified
by far-field BS-to-phone distances, all >50 m vs panel diagonal 53 mm).

The `munich_trace.py` docstring claim "per-element delay variation across the
panel is sub-mm and ignored" (line 22) is **misleading**: the panel is 5
wavelengths across, so phase variation is 1784 deg max. What is actually
ignored is per-element *amplitude* variation (1/r differences). The phase
variation IS captured by the analytic ramp. This is a docstring nit, not a
physics bug.

### 3. 18 Rx positions

**PASS.** `munich_rx.json` contains exactly 18 entries: 9 labeled `LOS_NN`
and 9 labeled `NLOS_NN`. All have `z = 1.5 m`. The bounding box is:
- x in `[-69, 136]` (paper: `[-69, 136]`) - exact match
- y in `[-27, 159]` (paper: `[-27, 159]`) - exact match

The 18 trace NPZs (`scene_00.npz` through `scene_17.npz`) cover indices
0-8 = LOS, 9-17 = NLOS, with `los_flag` field consistent with the label.

`rx_grid_annotated.png` exists at the expected path. The paper figure caption
is consistent with `munich_rx.json`.

Note: the `munich_rx_grid.py` script that *generates* `rx_grid_annotated.png`
hard-codes a different list of 16 candidates ( = 8 LOS + 8 NLOS), which would
fight with `munich_rx.json` if rerun. This is benign because `munich_rx.json`
is the source of truth for `munich_trace.py` and the picker has not been
rerun. Worth a comment.

### 4. Body excluded from Sionna RT

**PASS - this is correct.** `munich_trace.py:trace_one` explicitly:
1. removes any pre-existing transmitters/receivers in the scene (lines 81-83);
2. adds a single point Tx at the BS position (lines 88-90);
3. adds a single point Rx at `target_xyz` (the body centroid for the body
   trace, the phone position for the phone trace) (lines 91-93);
4. runs the path solver with no body geometry in the scene.

There is no `scene.add(body_mesh)` or equivalent anywhere in `munich_trace.py`.
The Sionna RT scene contains only the canonical Munich buildings/ground
distributed with Sionna and the two synthetic point sources/receivers. The
`h_BS + h_body` decomposition is therefore exact in the limit that the point-Rx
at `body_centroid` correctly captures the field that would impinge on the
real body's bounding region. The Kirchhoff render (`pose_pipeline_jax.py`)
then uses this incident-bundle `(k_dod, k_doa, psi, amp)` to compute the
body-mediated channel, layered on top of `h_BS`.

The Maxwell-linearity claim in Sec II.A (line 296) is therefore consistent
with the implementation. The two channels can be added because they are
independent solutions of two different Maxwell problems (scene-only vs
body-only when illuminated by the scene field).

A subtle caveat that is NOT raised in the paper: the body is also absent at
the **uplink** trace level. If in deployment the BS observed UE pilots, the
body would also occlude/scatter the uplink and the BS-side `h_meas` would
have a mild body-mediated component. Because the paper only uses simulated
`h_BS + h_body` for the uplink as well (see calibration treatment in Sec V),
this is internally consistent. But "the BS observes the served user's actual
channel via uplink pilots" (line 373) glosses over the fact that the simulated
"actual" channel is not a real measurement.

### 5. Per-scene path count

**PARTIAL PASS, off by ~10-15%.** From `summary.json`:
- LOS body paths: mean 456, range [348, 526]. Paper claims "~500".
- NLOS body paths: mean 248, range [122, 413]. Paper claims "~300".

LOS is reasonably described as "~500" (mean 456 rounds up). NLOS is more like
"~250" than "~300"; the paper overstates by 17%. No scene is starved (the
minimum is 122 paths for NLOS_01), so the Kirchhoff body render has enough
incidence dictionary to populate per-triangle currents. This is a wording
issue, not a physics issue.

Per-scene breakdown (body / phone):
```
i  flag      label P_body P_phone
0  LOS    LOS_00    526    518
1  LOS    LOS_01    444    436
2  LOS    LOS_02    508    501
3  LOS    LOS_03    475    475
4  LOS    LOS_04    447    448
5  LOS    LOS_05    448    450
6  LOS    LOS_06    348    358
7  LOS    LOS_07    438    440
8  LOS    LOS_08    468    458
9  NLOS   NLOS_00   382    391
10 NLOS   NLOS_01   122    128
11 NLOS   NLOS_02   263    262
12 NLOS   NLOS_03   211    218
13 NLOS   NLOS_04   223    233
14 NLOS   NLOS_05   323    314
15 NLOS   NLOS_06   413    406
16 NLOS   NLOS_07   155    144
17 NLOS   NLOS_08   138    134  <- hero scene
```

### 6. Diffuse vs specular

**PASS.** `munich_trace.py:trace_one` calls
```
SOLVER(scene=scene, los=True, specular_reflection=True,
       diffuse_reflection=False, refraction=True,
       diffraction=True, edge_diffraction=True,
       max_depth=MAX_DEPTH, samples_per_src=10_000_000,
       max_num_paths_per_src=200_000)
```
which matches the paper's claim line by line. Diffuse OFF, edge diffraction ON.

### 7. Body centroid height

**SUBTLE - the cited "1.2 m centroid" is the trimesh area-weighted centroid,
not the volume centroid.** With this convention, the SMPL-X mesh in the
default phone-holding pose has:
- feet at z = 0.28 m (i.e. the body is "floating" 28 cm above ground if z=0
  is the Munich scene ground level);
- head at z = 1.99 m;
- center-of-mass at z = 1.27 m;
- standing height 1.71 m (correct adult height).

The phone at z=1.5 m sits at mid-chest of the floating body, which is the
desired geometric placement. The Kirchhoff render uses the actual mesh
triangles, so the body height interpretation matters only for which triangles
"see" the phone.

**Two consequences:**
- The paper's "1.2 m height" is ambiguous: a reader expecting "navel/center
  of mass at 1.2 m" would get a body whose feet are on the ground (head at
  ~2 m), but the code places the area-weighted centroid at 1.2 m, which lifts
  the feet by 28 cm. The `body.mesh.centroid` distinction matters; for the
  default SMPL-X pose with a slight forward lean and arms-out, the area
  centroid sits at navel/lower-rib, ~1.0 m above the feet.
- For the rays that end at `body_centroid` (z=1.2) in the Sionna trace, the
  receiver sits 28 cm above the actual chest level. This means the "body
  incident bundle" sampled by the trace is the bundle at the area-weighted
  centroid, not at the chest where the dominant body-mediated scattering
  happens. The bundle-vs-chest displacement is sub-wavelength scaled to
  the BS-distance, so the per-path angle of arrival is still correct, but
  the per-path phase reference is offset by ~28 cm vertically. The
  Kirchhoff render compensates via its per-triangle planewave evaluation
  (`exp(-j k0 k_doa . centroid)`), so this is benign for the field at any
  triangle, but the implicit "the bundle is sampled at the body" interpretation
  is loose by ~30 cm.

Net effect on numbers: small. The paper would benefit from saying "SMPL-X
mesh placed so that the trimesh-style area-weighted centroid lands at
z=1.2 m, which puts feet at z~=0.3 m and head at z~=2.0 m" to avoid this
ambiguity.

### 8. Body azimuth (face_az)

**MOSTLY PASS, with one significant caveat.** All 18 scenes have `face_az`
correctly computed as `arctan2(BS_y - phone_y, BS_x - phone_x)` so the body
nominally faces the BS in the xy plane. Verified to floating-point precision
across all scenes.

But the **modeling assumption "body faces BS"** doesn't capture where the
incident energy actually comes from in deep NLOS. For each scene I computed
the fraction of body-incident energy (sum of `|amp|^2 * ||psi||^2`) coming
from the front half-plane (cos(face, source) > 0) vs. the back half-plane:

```
Scene  flag   front-energy fraction
0      LOS    0.937   <- body sees BS direction strongly
8      LOS    0.958
9      NLOS   0.725
14     NLOS   0.839
17     NLOS   0.253   <- HERO: 75% of incident energy hits the BACK of the body
```

**Implication for the hero example.** Scene 17 is the centerpiece of Sec
VIII.D (paper line 1058). The body is set to face the BS (south-east of the
Rx), but the dominant body-incident paths arrive from the north-west buildings
(behind the user). The Kirchhoff render therefore evaluates the body's *back*
surface for most of the incident energy. Two things would be true if the
"face-the-dominant-source" convention were used instead:
- the body's chest/front would receive more energy, so `||h_body||^2` would
  be larger;
- the latent gradient would have different geometry (different visible
  triangles), so the +8.6 dB pose uplift could change.

This isn't a bug -- in real life, a user looking at a phone faces the phone,
which faces the BS, which is the modeling choice the code makes. But the
paper does not acknowledge that for scene 17 the body is back-on to the
dominant arrival. A one-sentence note is warranted.

### 9. Per-scene scaling - "scene loss -109 dB" for hero scene 17

**FAIL: the scene-loss number cited in the paper uses a non-standard L1
formula and is 18 dB off the standard MIMO channel-power definition.**

The summary.json field `h_scene_db` is computed in `munich_trace.py:282` as
```
"h_scene_db": float(20 * np.log10(np.abs(h_scene).sum() + 1e-30))
```
which is `20 log10(L1-norm of h)` rather than the standard MIMO channel
power `10 log10(||h||^2)`. The paper's "scene loss -109 dB" for scene 17
matches this code-defined value to 0.01 dB.

For scene 17, the comparison is:
```
A. 10 log10(||h||^2)   [MRT power-loss, conventional]:  -126.92 dB
B. 20 log10(sum |h|)   [code's L1 metric, used in paper]: -109.09 dB
C. 20 log10(|sum h|)   [coherent scalar amplitude]:      -126.78 dB
F. 10 log10(<|h|^2>)   [mean per-element |h|^2]:         -144.98 dB
```

The 18 dB offset is exactly `10 log10(M^2 / M) = 10 log10(M) = 18 dB` for
M=64 elements when paths are well-co-phased. It looks like the metric was
chosen by hand without realizing that for an MRT-precoder-with-isotropic-UE
system, the canonical per-element scaling cancels the M out and you get
`||h||^2` directly.

**Effect on the SINR numbers cited in the paper:** ZERO. The cascaded SINR
is computed as `P_tx * ||h||^2 / N0` in `pose_pipeline_jax.py:_sinr_db_from_h`,
which uses `||h||^2` directly. So the paper's quoted SINR values (10.9 dB
baseline, 19.5 dB best-of-100, 11 dB BS-only for scene 17) are correct.
Only the "scene loss in dB" numbers are off.

**Effect on the prose reading of the paper:** the regimes labelled
"~75 to 90 dB scene loss" (mild NLOS), "~90 to 100 dB" (strong NLOS),
"-109 dB" (deep NLOS) all need +18 dB if rephrased in standard MIMO
channel-power terms. A reader from the wireless community will read those
numbers and probably do the conversion implicitly when computing implied
SNR; given that the SINR numbers are also reported, the inconsistency is
self-correcting at the SINR level but confusing at the path-loss level.

**Recommended fix.** Change the `h_scene_db` formula in `munich_trace.py:282`
to `10 * np.log10((np.abs(h_scene)**2).sum() + 1e-60)`, regenerate
`summary.json`, and update every "scene loss" cited in the paper by adding
~18 dB. Concretely, the hero "-109 dB" becomes "-127 dB", the LOS scenes go
from "-63 to -65 dB" to "-81 to -83 dB", and so on. The story doesn't
change, but the numbers become unambiguous.

### 10. Sionna RT version

**PASS.** Installed: `sionna-rt 2.0.1` (verified via `pip show sionna-rt`
in `/home/user/aegis/.venv`). Matches paper claim of "v2.0.1" (line 960).

Note: there is no top-level `sionna` package in this venv; only `sionna-rt`,
which is the standalone RT package introduced in Sionna 2.x. The
`sionna.rt.PathSolver`, `sionna.rt.scene.munich`, etc. import paths used in
the code are stable on 2.0.1. The `paths.cir()` return shape
`(2, 1, 1, 1, 1, P, 1)` documented in `munich_trace.py:104` matches Sionna
2.0 conventions.

### Steering ramp / per-element phase verification (item 2 follow-up)

I verified by direct Python execution that the `BSArray` constructor:
- places 64 elements in a plane perpendicular to `n = (0.303, 0.858, -0.415)`,
- with lambda/2 spacing exactly,
- with mean position equal to the BS center (no drift),
- using a Gram-Schmidt basis (`up=z` projected onto the normal-perp plane,
  `e2 = n cross e1`).

The steering ramp `exp(-j k0 (bs_pos[m] - bs_center) . k_dod)` is
identical between (a) `munich_trace.py:fanout_to_elements` (line 189), (b)
the phone trace `per_element_h_at_phone` (line 216), and (c) the JAX kernel
`kirchhoff_h_body_native` (line 334). All use the same convention with
`k_dod` defined as the unit vector from the BS in the direction of departure.

This means the per-element phases for the body-incident bundle (used inside
the kirchhoff render) are exactly consistent with the per-element phases
for `h_scene` at the phone. There is no accidental relative phase shift
between `h_BS` and `h_body`.

---

## Items not directly addressed in the prompt but worth flagging

### Selection bias in NLOS picks

Looking at the actual NLOS path counts vs the paper's coarse "~300" claim:
the NLOS pool has very-low-path scenes (NLOS_01 with 122 paths, NLOS_07 with
155 paths) and high-path scenes (NLOS_06 with 413 paths), spanning a 3x range.
This is consistent with "deep shadow" vs "mild shadow" labelling but the bin
is broad. Paper Sec VIII.D's "three regimes" classification (mild/strong/deep
NLOS) is an empirical finding from inspecting the per-scene SINRs, not from
any pre-defined geometry. That's fine but should be acknowledged as
post-hoc.

### Missing height context in the figure

`fig_munich_perscene.pdf` (the per-scene SINR bars) and the hero figure
`fig_hero_munich.pdf` are not in the audit scope, but if "scene loss" appears
on the figure as an x-axis label or annotation, it inherits the same +18 dB
offset issue.

### `iso` polarization at Tx and Rx

The Sionna trace uses `pattern="iso", polarization="V"` for both Tx and Rx
arrays (single element each, so the array gain is 1). This is a deliberately
neutral choice that lets the post-trace per-element steering ramp do all the
beamforming work analytically. It is consistent with the paper's per-element
representation and is the right setup for a `h_BS + h_body` decomposition
where the body Kirchhoff term will be added downstream.

### `wavelength / 4 pi` factor in `los_path_dict`

In `scene_nlos.py:los_path_dict` (used elsewhere, not by the Munich trace
directly), the LOS path amplitude is
```
amp = (lambda / (4 pi)) * exp(j k0 r) / r
```
which encodes the standard Friis-style per-element link budget. The Munich
trace uses Sionna's `paths.cir()` which already includes the spreading
factor in `psi`, so the `amp_path` is set to 1.0+0j and the Friis factor is
implicitly inside `psi`. These two representations are mutually consistent
under their respective conventions. No drift.

### Two `BSArray.__post_init__` defaults

`BSArray.center = [0, 0, 8]` and `normal = [1, 0, 0]` defaults exist for
backwards compatibility with the legacy S2/S3 PoC scenes (`scene_nlos.py`).
The Munich trace explicitly overrides both, so the defaults are not in play
here. No bug, but if a future caller forgets to pass them they get a 8m-tall
SISO-x-pointing BS at origin instead of an error - mildly footgun-y.

---

## Summary of changes the paper would benefit from

| Severity | Item | Recommendation |
|---|---|---|
| MEDIUM | Item 9: scene loss formula | Change to `10*log10(||h||^2)` everywhere; regenerate summary.json; update all "scene loss" numbers in paper text by +18 dB. The hero "-109 dB" becomes "-127 dB". SINR numbers stay the same. |
| MEDIUM | Item 8: hero body orientation | Add one sentence acknowledging that for scene 17, 75% of body-incident energy arrives from behind the body (since dominant NLOS paths come from buildings to the NW, not the BS). The "face the BS" convention is defensible (user is looking at phone) but the asymmetry should be noted. |
| LOW | Item 5: NLOS path count | Change "~300" to "~250" or "200 to 400 across NLOS scenes". Cosmetic. |
| LOW | Item 7: body centroid definition | Disambiguate "body centroid 1.2 m": the SMPL-X area-weighted centroid is at z=1.2, putting feet at z=0.28 and head at z=1.99. A reader expecting "feet on the ground" would set centroid at ~0.95 m. |
| NIT | Steering doctring | "per-element delay variation across the panel is sub-mm" should say "per-element 1/r amplitude variation is sub-percent and ignored; per-element phase variation IS captured by the planewave ramp". |
| NIT | Item 3 / `munich_rx_grid.py` | The picker hard-codes 16 candidates, but `munich_rx.json` has 18 entries (from a later picker run). Add a comment noting which script generated the current `munich_rx.json`. |

No issue identified rises to "fundamentally wrong scene setup" or "all
per-scene numbers are wrong". The pipeline is sound; the SINR numbers and
the hero example are reproducible from the code; the body-RT exclusion is
clean; and the panel geometry is precise. The most consequential issue is
the L1-vs-L2 scene-loss naming convention, which is a presentation issue
rather than a physics issue.

---

## Files inspected

Absolute paths:
- `/home/user/aegis/JSAC2/code/scenes/munich_setup.py`
- `/home/user/aegis/JSAC2/code/scenes/munich_trace.py`
- `/home/user/aegis/JSAC2/code/scenes/munich_bs.json`
- `/home/user/aegis/JSAC2/code/scenes/munich_rx.json`
- `/home/user/aegis/JSAC2/code/scenes/munich_rx_seed.json`
- `/home/user/aegis/JSAC2/code/scenes/munich_rx_v2.py`
- `/home/user/aegis/JSAC2/code/scenes/munich_rx_v3.py`
- `/home/user/aegis/JSAC2/code/scenes/munich_rx_grid.py`
- `/home/user/aegis/JSAC2/code/scenes/munich_los_scan.py`
- `/home/user/aegis/JSAC2/code/scenes/munich_dual_scan.py`
- `/home/user/aegis/JSAC2/code/scene_nlos.py`
- `/home/user/aegis/JSAC2/code/scene_smplx.py`
- `/home/user/aegis/JSAC2/code/pose_pipeline_jax.py` (lines 270-380)
- `/home/user/aegis/JSAC2/code/outputs/munich/traces/scene_*.npz` (all 18)
- `/home/user/aegis/JSAC2/code/outputs/munich/traces/summary.json`
- `/home/user/aegis/JSAC2/paper/jsac2_v3.tex` (lines 270-296, 925-1075)
