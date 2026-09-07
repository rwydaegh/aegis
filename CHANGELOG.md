# Changelog

Curated highlights per release. Full detail lives in `git log` — this file
exists so a human can understand a release in two minutes.

## v0.41.0 - 2026-09-07

### Features

- Control password access to the viewer and documentation together with
  `AEGIS_PUBLIC_ACCESS`. Set it to `true` to allow access without a password
  while retaining the configured passwords for switching back (#952).

### Fixes

- Correct Sionna synthetic-array expansion for arbitrary element layouts by
  tracing at the array centroid and applying each path's departure-direction
  phase (`db5b36d9`).
- Validate Sionna coefficient, delay, angle, and validity-mask shapes before
  conversion. Handle empty JAX path sets and single-element non-synthetic
  traces explicitly (`0abb95bb`).
- Restore the mpmath constraint required by the optional body stack so the
  combined installation resolves correctly (#952).
- Remove stale documentation files during deployment (#952).

### Maintenance

- Limit source packages to application code, tests, configuration, and
  documentation (#952).
- Refresh viewer, visualization, documentation, and development dependencies
  and the dependency lockfile (#935-#951).
- Refresh viewer visual-regression baselines and verify the production SSH
  host key during disaster-recovery backups (`573e615f`, `35180a3e`).
- Synchronize citation version, release date, and test-count metadata.

## v0.40.0 — 2026-08-09

The consolidation release: 539 commits across three parallel lines (June 8 to
August 9), brought onto one master with full history preserved. See
`papers/city-exposure-study/agent_docs/CONSOLIDATION_20260809.md` for how the
merge was done and proven safe.

### Coherent Exposure Studio (new viewer module)

- Full 3D studio for coherent MIMO exposure: field slices with shader
  colouring, ray rendering, phantom body maps, HUD, grouped control panel.
- Physics controls: GEP precoder, ICNIRP compliance scalars, absolute-limit
  two-restriction ECBF, transmit-power slider to 100 dBm (ECBF flattens where
  MRT diverges), patch element factor, spectral-efficiency and S_ab peak rows.
- Analysis panels ported from the hybridizer: A/B beam comparison, radial
  falloff, line probe, array-pattern cut, exposure distribution.
- Data layer: precomputed exposure-operator Q packs (fast ECBF), ensemble
  mean/p95 body maps, live focus-tracking deposited body map, UE-aware
  per-position channel packs, float16 packs halving a 127 GB tree.
- Performance: JIT-fused GPU body-channel assembler (13x), frequency-invariant
  geometry hoisting, `AEGIS_JAX_X64` toggle.
- Phantom/array selection, child/adult ratio sheets, figure capture tooling.

### Semantic twin: city exposure study (new package)

- Panorama-driven multi-view scene reconstruction to body exposure, end to
  end: acquisition, registration, semantic segmentation, facade materials,
  transport, dosimetry.
- Eleven-city screening and acquisition; crop-radius convergence settled at
  250 m (set by the farthest source); corrected illumination law and what it
  reorders; evidence ladder with an honest negative on image-based materials
  (SAM 3 ran on 2 of 96 panoramas — disclosed, then closed).
- Full paper draft with SI, provenance audits tracing every number to source,
  errata records (including a factor-2 monograph depth-identity slip).
- Walk/CDF campaigns with sequential stopping, Blender evidence views with
  production identity stamped into scenes.

### Roofline production pipeline (PRs #906–#925)

- Production transport contract `first_material_interaction_v1`: exact direct
  plus exact order-1 all-specular plus stochastic next-event at the first
  blocking material vertex; enforced partition at run time.
- Sealed campaign infrastructure: identity hashing, atomic replica shards,
  preflight refusals, persistent transport cache, strict registration
  admission, portable meshes and visualization across machines.
- Five completed city campaigns (Korenmarkt, Prague, Madrid, Mexico City,
  Tokyo); the export is archived in-repo as the durable copy. A sixth city
  (Brussels Grand-Place) traced during consolidation and awaits review.
- Physics corrections: body surface mean weighting (#920), exact direct
  arrival directions (#922), exact uniform-yaw body averaging (#923),
  deterministic RCWA mode selection (#908).

### Report integrity (#932)

- Persistent cache identity now reads live algorithm constants (was restating
  literals, which would have served stale entries after a constant change).
- Multicity report binds campaigns to their sealed site and refuses
  duplicate-site or mixed-contract pooling; route CDFs carry support counts;
  topology sensitivity gains properly paired per-standpoint dB quantiles.

### Viewer production and Exposure Lab (#847–#855)

- SMPL-X model and posed-body caching (2 s to 26 ms same-pose), deferred and
  accelerated 4 cm² averaging, Lab HUD, numba kernel warm-up at worker boot,
  production disaster-recovery automation, Sentry noise fixes.

### Core and studies

- New `aegis.hotspot` module with e11 ground-truth oracle.
- New `aegis.study` city-scale package (OSM city meshing, GHSL mobility,
  covariates, deterministic-vs-stochastic comparison arms). Windows-safe
  UTF-8 file IO fixed in this release.
- Eartha phantom reprocessed from a double-walled shell to a solid single
  skin; corrected mass and biometrics.
- Directional source-aware self-shadow for the single-source viewer.

### Housekeeping

- One worktree, one branch: seven merged branches and five worktrees retired
  with per-branch proofs; retired report and hybrid twin moved to `archive/`.
- CPU-first dependency split: `all` now bundles the CPU body stack, `gpu` is
  an explicit opt-in, torch pinned to the CPU index on this machine.
- Business/spin-off notes (patent claims v1, outreach dossiers, IOF
  materials, market de-risk studies) tracked under `spinoff/`; the Custorix
  dossier moved out of the repo.
- Routine dependency bumps throughout (dependabot).
