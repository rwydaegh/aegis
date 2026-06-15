# Coherent Exposure Studio — review overview

This document orients a reviewing agent (or human) on the **Coherent Exposure
Studio**, the viewer module on branch `feature/coherent-exposure-studio`. It
explains what the studio is for, the physics it rests on, how the code is laid
out, what was built in the most recent sessions, and what to scrutinise.

> Scope note: the branch is **not** merged to master and should not be merged by
> the reviewer. It depends on gitignored precomputed packs in `data/studio/`
> (~2.8 GB) that live only on the dev box. The merge decision is the
> maintainer's (Robin's) call. Review the code, not the merge.

---

## 1. What we are trying to do

AEGIS computes **absorbed / deposited power density on human bodies** in wireless
environments. The Coherent Exposure Studio turns the static figures of the
coherent-hotspot study (internal "e11") into a **live, interactive 3D
instrument**: a base station fires a MIMO beam at a phantom, and the user can

- steer the beam focus (drag in 3D, slider, or click the body),
- switch beamformer (MRT, unfocused, decohered, decoy, worst case, ECBF),
- sweep the design space (phantom, LOS/NLOS, array size, frequency, seed),
- inspect the field on an orientable **slice plane**, as a **3D field volume**,
  and as a **per-triangle body map** of deposited Sab,

and see the exposure update in real time. It is a sibling to the existing
"Exposure Lab" module (which must never be deleted or disturbed).

The headline interaction is: **move the focus, watch the body's deposited-power
map recolour.**

---

## 2. The physics it rests on

Single source of truth for all equations is the monograph at `../monograph/`
(`monograph_v2.tex`, with `summary_paper.tex` as the condensed version). Read
before judging any physics.

- **Core dosimetry identity (incoherent levels 0-6):**
  `Sab(r) = Sinc * T0 * ReLU[n_hat(r) · (-k_hat)]`
  Absorbed surface power density = incident power density × a tissue power
  transmission coefficient `T0` × a clamped projection of the surface normal
  against the incoming ray. The ReLU enforces "back faces absorb nothing".
- **Coherent levels 7-8** use the complex field `psi` directly (not powers), so
  the beam's phase coherence is preserved through the dosimetry.
- **The studio's live body map** is the coherent deposited surface power:
  `S_ab(triangle) = sum_axis |G_tilde @ x|^2`
  where `G_tilde` (shape `(T, 3, M)`, complex) is the **precoder-free,
  tissue-weighted surface (exposure) channel** mapping the `M` antenna
  excitations to the 3 tissue-coupled surface-field components at each of `T`
  body triangles. These are the Fresnel-filtered, conductivity-scaled field
  components (the exposure branch of the formalism, `G_tilde = Psitil Phi J`),
  whose squared norm is absorbed power density, not the free-space field
  (`G = Psi Phi J`). `x` (length `M`) is the live precoder (beamforming
  vector). Because `x` is recomputed from the live focus/beam, the deposited map
  tracks steering exactly. This is the key equation the studio's interactivity
  depends on, and it matches the offline precompute.

The nine fidelity levels (0-8) range from O(1) analytic bounds to coherent MIMO
beamforming; the studio operates at the coherent end.

> Frequency-axis caveat: the ray pack (arrival directions `k_hat`, the path
> amplitudes `psi` which also carry the synthetic array's per-element steering
> phase, and the element dispatch) is traced once at 28 GHz. The frequency
> slider moves only the propagation wavenumber `k0` and the skin dielectric; the
> multipath geometry and the array's electrical aperture stay frozen at 28 GHz.
> So off-28-GHz frequencies are a tissue-and-wavelength reweighting on 28 GHz
> geometry, not a fully re-traced scenario (least valid at 10 GHz, exact at 28).
> The geometric part of ray tracing is frequency-independent, so reusing the
> arrival directions is defensible, but the array selectivity and the dispersive
> Fresnel amplitudes are not. A true sweep needs a per-frequency re-trace.

`G_tilde` is produced by `aegis.coherent.compute_body_channel`. The studio's
field-reconstruction primitives (free-space synthesis around the focus, 4 cm^2
spatial averaging, worst-case search, internal/layered-skin SAR) were ported
from the paper fork into a new main subpackage `src/aegis/hotspot/`, with the
`paper_aegis.*` imports rewired to `aegis.*`. An `@slow` oracle test reproduces
the paper's ~52x focusing-ratio ground truth.

---

## 3. Architecture

Data flow: **offline precompute → gitignored packs → fork-free Flask routes →
React/Three.js frontend.** Nothing at runtime imports the paper fork, sionna,
mitsuba, or TensorFlow; only the offline precompute script may.

### Backend (`src/aegis/viewer/routes/studio/`, fork-free Flask blueprint)
- `__init__.py` — endpoints: `/api/studio/{manifest, rays, slice (POST),
  bodymap (GET), bodymap-live (POST), volume (POST), phantom}`. `_beam_field()`
  centralises beam → precoder/field-source resolution (MRT/unfocused/decoy/
  worstcase build a precoder `x`; decohered returns a field source; ECBF loads
  the precomputed exposure operator `Q` and solves, else raises).
- `_channel.py` — loads the persisted `G_tilde` pack and applies the live `x`
  for the live body map (`compute_live_bodymap`, `deposited_sab`).
- `_bodymap.py` — static (focus-frozen) body-map packs + ensemble mean/p95.
- `_slice.py`, `_volume.py` — field slice and 3D field volume reconstruction.
- `_precoders.py` — beamformers (all matched to power `||x||^2 = P`).
- `_phantom.py` — phantom geometry + at-skin focus snapping (`known_meshes`,
  `snap_focus_to_skin`).
- `_presets.py` — design-space axes + `default_scene` + manifest.
- `_config.py` — `data/studio/` pack discovery (`available_packs`,
  `studio_data_dir`).

### Frontend (`aegis-web/src/modules/coherentStudio/`, React + R3F + Zustand)
- `store.ts` — Zustand store. **Critical invariant:** the derived
  `sliceFetchKey` / `bodyMapFetchKey` / `volumeFetchKey` selectors include only
  params that require a network refetch; render-only state (colormap, scale
  knobs, camera) must never appear in them.
- `scene/` — `StudioScene` (assembly), `StudioSlicePlane` (shader-coloured
  quad), `StudioVolume` (instanced voxel cloud), `StudioRays`, `studioHelpers`
  (pure colour/geometry helpers), `colorScale.ts` (the colour-scale core — see
  below).
- `panels/` — `StudioPanel` (control surface), `StudioQuantityPicker`,
  `controls.ts` (pack-gating predicates: `channelHasPack`, `phantomHasPack`,
  `arraySizeHasRayPack`, `beamAvailability`, `ensembleHasPack`, ...).
- `useStudio*.ts` — debounced, race-safe fetch hooks per result type;
  `useStudioScales.ts` (resolves colour scales for all surfaces at once).
- `StudioHud.tsx` — provenance card, computing pill, legend colour bar.

### Coordinate frames (a recurring source of bugs)
- Python/AEGIS is **Z-up**; three.js is **Y-up**.
- Conversion: `toScene: (x,y,z) -> (x,z,-y)`, `toServer: (x,y,z) -> (x,-z,y)`.
- The phantom geometry is baked into the Y-up scene with `geometry.rotateX(-pi/2)`.

---

## 4. The precompute (`scripts/studio_precompute.py`)

Offline-only tool (may import the fork for exact e11 geometry). Produces
`data/studio/` (gitignored):

- `rays/` — arrival rays per (condition, array size, seed); body-independent, so
  bare stems `bs{n}_{cond}_seed{s}`.
- `phantom/{mesh}.npz` — placed full-resolution triangle soup + centroids /
  normals / areas, e11 world frame (Z-up).
- `bodymaps/` — static per-triangle floor/mrt/worstcase/amp maps.
- `ensemble/` — mean / p95 over the LOS seed ensemble.
- `qop/` — exposure operator `Q = J^H M J` (M_ant x M_ant) per scenario.
- `channel/` — the `G_tilde` field-channel packs (largest artifact, ~150 MB ea).

Pack stems are **mesh-prefixed** for body-derived artifacts:
`{mesh}_{cond}_bs{n}_{qty}_{freq}` (bodymap), `{mesh}_{cond}_bs{n}_{freq}` (qop),
`{mesh}_{cond}_bs{n}_{freq}_seed{s}` (channel). `freq` uses python `%g`.

`G_tilde` is built in 128-triangle chunks (a full build OOMs at ~26 GB). The
build is backend-agnostic (`aegis._array_backend`): `AEGIS_ARRAY_BACKEND=jax` +
`jax[cuda12]` runs the kernel on GPU with machine-epsilon parity vs NumPy
(~12x at bs16, ~7x at bs8). Built on an ephemeral 2x-A5000 box; packs rsync'd
back. Phantoms available: thelonious (6 yo), duke (34 yo M), eartha (8 yo F),
ella (26 yo F). Array sizes: bs8 (8x8 = 64 elements), bs16 (16x16 = 256).

---

## 5. Recent work (what is freshest and most worth reviewing)

The last three commits are the newest and least battle-tested:

### `8311666b` / earlier — live focus-tracking body map
Added the `/api/studio/bodymap-live` path and the `deposited` quantity.

### `546c4539` — "Open the studio on the live focus-tracking body map"
**Bug:** the body map "did not respond to the focus." End-to-end QA proved the
live path was correct (backend recomputes `x` from the live focus; the live
fetch key includes focus; the hook refetches). The real cause was the **default
`bodyMapQuantity` being the static, focus-frozen `mrt` pack** in both the store
and the backend `default_scene`. Fix: default to `deposited`. A **second-order
bug** surfaced and was fixed: the quantity picker's "live-unavailable fallback"
effect fired on first mount before the manifest loaded (empty packs ->
`liveAvailable` spuriously false) and clobbered the new default back to `mrt`;
gated it on `manifest &&`. Regression guard added in `store.test.ts`.

### `1a4fc184` — "Rebuild the studio colour and scale system" (largest recent change)
Previously the slice, body map, and volume shared only a colormap, never a
normalisation. Each autoscaled independently (equal colours != equal values),
the single colorbar described only the slice, "Fixed" was a dead control
(identical to Auto), and log used inconsistent conventions per surface.

New subsystem (all client-side, display-only, **no fetch-key impact**):
- `scene/colorScale.ts` — one **pure** resolver `resolveScale()` plus
  `scaleNormalise()`, `percentileRange()`, `minMax()`, `unionRange()`,
  `rangeOf()`, `logFloor()`. This is the heart of the change and the most
  important file to review for correctness. 20 unit tests in
  `__tests__/colorScale.test.ts`.
- **Shared scope** — unions the surfaces' ranges so a colour means the same
  W/m^2 across slice/body/volume; one legend then describes all three.
- **Real Fixed** — editable vmin/vmax + "lock to current view", seeded from the
  live auto range so the view never jumps.
- **Consistent log** — one dB-window formula across slice (GLSL shader), body
  (dB path in `BodyMeshInstance`), and volume, driven by a 10-60 dB
  dynamic-range slider (was hardcoded 30).
- **Robust autoscale** — clip to p0.5..p99.5 so one hot triangle/voxel cannot
  wash out the map.
- **Perceptually-uniform colormaps** — plasma/inferno/magma/cividis/turbo added
  to `src/lib/colormap.ts` (viridis default, jet kept as legacy, coolwarm auto
  for signed ReE components).
- **Honest legend** — ticks follow the resolved scale (dB decades in log), fall
  back to the body scale when no slice, footer states scope / robust / range.

`useStudioScales.ts` computes all three surfaces' resolved scales in one place
(data ranges memoised on result identity + robust flag, since `percentileRange`
sorts and must not run per frame).

---

## 6. What the end result should be / acceptance

- Opening the studio shows the phantom **standing upright**, painted with the
  **live deposited** map, recolouring as the focus moves.
- Every (phantom x condition x array x freq x seed x beam x focus-mode x
  quantity x field-quantity x plane orientation) combination either returns a
  200 with a sensible map/slice or degrades gracefully (409 "not precomputed"
  greys nothing it shouldn't; 400 for an under-specified free plane).
- The colour scale is **honest**: with Shared scope, equal colours mean equal
  values across all three surfaces and the one legend is correct; Fixed locks a
  user range; Log shows a dB window with correct decade ticks; Robust clips
  outliers.
- No console errors; physics sign/positivity invariants hold (Sab >= 0).

---

## 7. Known constraints and gotchas (do not "fix" these)

- **Fork isolation:** runtime studio code imports only `aegis.*` + numpy. Never
  pull the fork / sionna / mitsuba / TF into a runtime path. Only
  `scripts/studio_precompute.py` may import the fork.
- **Exposure Lab** must never be deleted or altered beyond the planned
  behaviour-preserving HUD extraction.
- **Never weaken test assertions** to make tests pass. The Mie regression test
  is the CI canary.
- `data/studio/` is gitignored. `src/aegis/viewer/static/` is gitignored except
  the force-added `index.html` (the built bundle entry); the hashed JS/CSS
  chunks are regenerated by `npm run build:copy` and intentionally not committed.
- Style: no em dashes, no semicolons in code; type annotations on public API.
- Geometry gotcha (already fixed, but illustrative): never feed a shared/store
  vertex buffer straight into a `THREE.BufferGeometry` you then `rotateX` in
  place — clone it first, or React StrictMode's double-invoke rotates it twice
  and the body tips onto the floor.

---

## 8. How to run, build, and test

```bash
# Backend (serves the built bundle from static/) on :5000
python -m aegis.viewer                 # or the studio is at /studio

# Frontend dev server on :5173 (proxies /api to :5000)
cd aegis-web && npm run dev

# Rebuild the production bundle into the Flask static dir
cd aegis-web && npm run build:copy

# Frontend tests / lint / typecheck
cd aegis-web && npx vitest run         # 275 tests (incl. 20 colorScale)
cd aegis-web && npx tsc --noEmit
cd aegis-web && npx eslint src/modules/coherentStudio --max-warnings=0

# Backend studio tests (need data/studio packs for the @needs_packs ones)
python -m pytest tests/viewer/test_studio_routes.py tests/test_hotspot.py -m "not slow" -n 0
```

Browser QA: headless chromium via the `playwright` library, with the script
placed **inside `aegis-web/`** so `playwright` resolves. Capture screenshots to
`test_screenshots/` and read them back.

---

## 9. Suggested review focus, in priority order

1. **`scene/colorScale.ts`** — the pure resolver and `scaleNormalise`. Check the
   signed-vs-non-signed precedence, the vmin=0 pin for non-negative quantities,
   the shared-union exclusion of a signed slice, the dB-window math, and that the
   GLSL shader (`StudioSlicePlane`), the body dB path (`BodyMeshInstance` via
   `StudioScene`), and the volume (`StudioVolume`) all normalise identically.
2. **`useStudioScales.ts`** — memoisation correctness (no percentile sort per
   frame) and the auto-range snapshot used by Fixed mode.
3. **`StudioQuantityPicker` default + fallback** — the `manifest &&` gate that
   keeps the live default from being clobbered on first mount.
4. **`store.ts` fetch keys** — confirm none of the new colour/scale fields leak
   into a fetch key (they are render-only).
5. **`src/lib/colormap.ts`** — the new colormap stops and the `sampleNamedStops`
   fallback to viridis for unknown names.
6. Backend `_channel.py` / `__init__.py bodymap-live` — that the live precoder is
   genuinely rebuilt from the request focus.
