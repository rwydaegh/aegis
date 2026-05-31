# HPC city-scale population exposure study

**Date:** 2026-05-31
**Status:** Draft

> **Addendum (2026-05-31, post-implementation):** the deterministic ray-tracing
> engine is **local Sionna RT** (Dr.Jit, runs on CPU and auto-uses a GPU when
> present), not DiffeRT. Reason: upstream DiffeRT 0.7.0 path finding is exhaustive
> image-method (O(N^K)), which does not scale to a city mesh; Sionna RT uses SBR
> and scales. DiffeRT is retained as a selectable second tracer for
> cross-validation (a two-tracer check strengthens the ground-truth claim). The
> "no Sionna/TF" rule still holds for the **stochastic 38.901 generator** (Plan 2);
> it never applied to the deterministic arm. Sionna RT 2.0 needs ITU radio
> materials, handled by a `radio_materials` mode on `to_sionna_xml`. Modal GPU
> offload is optional, not required.

## Problem

AEGIS can compute the absorbed power density on a single body from a single source, interactively, through the web viewer. It cannot run a population. There is no way to walk many people through a real city, expose them to a realistic deployment, and collect exposure statistics. The CLI (`aegis-run`) is single-shot and ignores its own `channel:` and `mimo:` config sections. The only existing time-stepped multi-body code is `JSAC/code/experiments/plaza_run/`, which is hardwired to one Brussels plaza and built entirely around an ECBF power-reduction comparison that is not relevant here.

We want a headless, batch research instrument that produces population exposure CDFs across several real cities, and that computes each person's exposure two ways, deterministic ray tracing and a stochastic 3GPP channel, so the two can be compared.

## Scientific framing

One paper, two payoffs that share the same machinery.

1. **Methods.** Deterministic ray tracing is the reference. The stochastic 3GPP TR 38.901 channel is the candidate shortcut. The question is when the cheap stochastic model reproduces ray-traced population exposure. The cities and mobility give this verdict statistical weight.
2. **Characterization.** The population exposure CDFs across cities of different morphology are a deliverable in their own right.

The reference frame is fixed: ray tracing through the actual city mesh is treated as ground truth, the stochastic channel is the thing under test. This is the capability the older `hybrid-QuaDRiGa-FDTD` pipeline never had, because that pipeline was always stochastic at the macro scale (QuaDRiGa) and deterministic only near the body (FDTD). AEGIS adds the deterministic macro channel (ray tracing the city), which is what makes the comparison possible.

All exposure is far below ICNIRP limits. There is no safety-constraint or power-reduction story.

## Non-goals (out of scope or parked)

- Power-reduction / ECBF / exposure-constrained beamforming. Dropped.
- Human-side hotspot optimization. Dropped.
- LLM-based dataset enrichment. Parked.
- Google 3D Tiles for geometry. Out. OSM only.
- Real per-site deployment data as the comparison substrate. The generative deployment recipe replaces it. A real-deployment descriptive arm is a possible later addition, not part of this spec.
- The deployment-fidelity 2x2 (real-vs-generated deployment crossed with det-vs-stoch channel) and counterfactual cities. Parked as extensions.
- Adaptive beam optimization (ECBF, QCQP, exposure-constrained precoders). Out. The study computes coherent dosimetry but with a fixed, non-adaptive precoder (see physics note).

## Architecture

A new module under `src/aegis`, provisionally `src/aegis/study/` (final name decided at implementation). It is headless, config-driven, and contains no Flask dependency. One run is one config file. It is written as one cohesive, high-quality codebase. The three precursor repos (`plaza_run`, `pedestrian_flow_ABM`, `hybrid-QuaDRiGa-FDTD`) are inspiration only, not imported and not copied, because their code quality does not meet the bar. We use production AEGIS physics directly and lean on its fast paths (JAX/GPU backend, vectorized kernels, automatic chunking, factored Fresnel) wherever they apply.

Production AEGIS pieces used directly:

- `src/aegis/engine.py` `DosimetryEngine.compute` is the dosimetry core, run at a coherent level (7-8) with a fixed precoder. The coherent kernel is JAX/GPU-capable and uses factored Fresnel.
- `src/aegis/coherent/` builds the body-surface channel `G_tilde(r)`, the per-element field channel, and the exposure operator. `src/aegis/coherent/translation.py` (`translation_phasor`, `q_translate`) is the cheap per-slot Q refresh between full re-poses, which is exactly the framerate mechanism (see temporal model).
- `src/aegis/integration/differt.py` `paths_from_differt_scene(scene_path, tx_positions, rx_position, freq_hz, ...)` is the deterministic arm, with full TE/TM phase tracking (coherent). It loads a Sionna XML scene, so the city mesh is exported once per city via `EnvironmentMesh.to_sionna_xml(path)` and the cached path is passed in. Its returned `PropagationPaths` already carries per-element complex `psi` and `element_index` in `[0, M_ant)`, so it feeds the coherent body channel directly. Do not call `expand_paths_to_array` on top of it, that would double-apply the per-element phase. The viewer's `compute_paths_differt` is incoherent-only and is not used.
- `src/aegis/environment/__init__.py` `EnvironmentMesh.from_osm` and `parse_osm_xml` build the city mesh and expose building footprints and heights.
- `src/aegis/geometry/pose_stream.py` `PoseStream` and `src/aegis/geometry/parametric.py` `ParametricBody` pose the walking SMPL-X body.
- `src/aegis/mimo/` provides the UPA array, steering vectors, and the MRT precoder that forms the beam.

New physics to write (natively in AEGIS, JAX-friendly):

- A coherent 38.901 cluster channel, written as a new function `generate_coherent_channel(params, array, ...)` that supersedes `generate_channel` for coherent use. The existing `generate_channel` stays unchanged for the incoherent viewer path: it computes cluster angles, delays, and powers but returns `PropagationPaths.from_powers`, which collapses to one virtual element per path with arbitrary polarization and no phase. The new function reuses the cluster geometry but emits a full coherent `PropagationPaths` with per-element complex `psi` and `element_index` in `[0, M_ant)`: per-element steering phases via `mimo/array.py` `AntennaArray.steering_vector`, TE/TM polarization with 38.901 cross-polarization (XPR), assembled with the existing `expand_paths_to_array` helper. New signature, new return contract, new `array` argument. No QuaDRiGa, no TF/Sionna. This is the single largest new component.
- The 38.901 LOS probability $P_{\mathrm{LOS}}(d)$ (for example the UMi street-canyon form). Not present in the codebase, written fresh. It weights the LOS/NLOS blend in the stochastic arm.

Ideas taken (not code) from the precursor repos: the population-weighted origin-destination plus Directions routing pattern from `pedestrian_flow_ABM`, the time-stepped multi-body plus CDF-accumulation structure from `plaza_run` (minus its ECBF core), and the LOS/NLOS-aware stochastic-channel idea from `hybrid-QuaDRiGa-FDTD` (without QuaDRiGa). All re-implemented cleanly.

Parallelism is over the independent axis (city, deployment realization, agent). The within-agent time loop is serial. No multi-node coordination is required, so a job array (one task per chunk of agents per realization per city) is sufficient.

## Pipeline, per city

1. **City mesh.** AEGIS-native OSM build via `EnvironmentMesh.from_osm(lat, lon, radius_m)` to a materialed triangle mesh: building footprints, heights, tag-based materials, ground plane. The same `radius_m` is used for every city (the footprint is circular, not square), so the analysis area is fixed across cities. The mesh is cached to disk, exported once to a Sionna XML scene (`to_sionna_xml`) for the deterministic arm, and turned into a BVH (`geometry/occlusion.build_bvh`) for visibility tests.
2. **Walks.** Sample home and destination positions weighted by GHSL population density. Route each with the Google Directions API in walking mode. Decode polylines to a lat/lon path. Project to the city local ENU frame using the same origin as the OSM mesh. Each agent walks at a sampled speed (default 1.4 m/s). The agent is an SMPL-X body posed walking, heading set to the path tangent. The population is a synchronized crowd over a window `window_s` (agents enter staggered, walk, exit), not a bag of independent walks, because beam scheduling needs a shared clock to know which users a sector serves at each slot.
3. **Deployment.** Candidate rooftop points come from `parse_osm_xml`, which returns `Building` objects carrying `footprint` (N,2 local XY) and `height`. Each building yields a candidate site at its footprint centroid raised to its roof height. A repulsive point process (minimum-spacing, Ginibre-style) thins these candidates to the final site set, with target density anchored to the real site count for that city (read once from the base-station dataset as a scalar count, not per-site attributes). Each surviving site is configured from one equipment scenario, an AEGIS-side config block (not a 38.901 preset): array geometry, transmit power, height class, frequency. The default scenario is 28 GHz mmWave MaMIMO. Each site carries S sector panels (default 3, 120 degrees apart), each an 8x8 UPA covering a +/-60 degree azimuth wedge with a finite useful range (default 150 m at mmWave). A body is illuminated only by sectors whose wedge and range it falls inside, which adds realism and limits per-body cost because each body interacts with a few nearby panels rather than every site. Each sector serves the active users within its wedge and range with a fixed MRT precoder toward the served-user channel (no adaptive optimization). K independent realizations (random site layouts) are sampled per city.
4. **Dual-channel exposure.** For each (deployment realization, agent, timestep), build the per-element coherent channel two ways. Deterministic: ray trace the cached Sionna scene with TE/TM phase tracking via `paths_from_differt_scene`, giving the complex paths the body-surface channel is built from. Stochastic: the AEGIS-native coherent 38.901 cluster channel, seeded for reproducibility, geometry-blind by design (it never sees the actual buildings). Rather than a hard LOS/NLOS switch from a shadow ray, the stochastic exposure is the $P_{\mathrm{LOS}}(d)$-weighted blend of the LOS and NLOS channel statistics, with $P_{\mathrm{LOS}}(d)$ the standard 38.901 distance-based probability. This keeps the stochastic arm purely statistical, so the comparison against ray tracing (which gets real occlusion for free) is honest. Both arms feed the same coherent dosimetry path with the same fixed precoder.
5. **Exposure reduction.** The coherent per-triangle $S_{\mathrm{ab}} = \lVert \tilde{G}(\mathbf{r})\,\mathbf{x} \rVert^2$ (body-surface channel times precoder) reduces to a per-person exposure sample per timestep, then to a per-person summary over the walk. Distinct sites are uncorrelated transmitters and sum in power.

The core absorption law is unchanged:

$$S_{\mathrm{ab}}(\mathbf{r}) = S_{\mathrm{inc}} \cdot T_0 \cdot [\hat{n}(\mathbf{r}) \cdot (-\hat{k})]_+$$

### Physics note: coherent dosimetry with a fixed beam

Each site forms a beam toward its served users with a fixed MRT precoder `x`. The precoder is built from the served user's channel `h`: in the deterministic arm `h` is the ray-traced user channel, in the geometry-blind stochastic arm `h` comes from the coherent 38.901 generator evaluated at the served user's position (not the bystander's). The body absorption is computed coherently: the per-element body-surface channel `G_tilde(r)` carries phase and polarization, and the per-triangle exposure is `||G_tilde(r) x||^2`. This uses AEGIS's coherent Sab kernel, the engine's differentiator, rather than collapsing to summed path powers. What is dropped from the JSAC line is only the adaptive part: the precoder is fixed (MRT), with no exposure-constrained or power-reduced optimization. The served-versus-bystander split comes from the ABM: served users are beam targets, non-users catch the resulting sidelobes and main-lobe sweeps. Elements within a site combine coherently, distinct sites are uncorrelated and add in power.

## Temporal model and the framerate knob

The time-stepped slot machinery from `plaza_run` is kept. The ECBF solve inside it is removed. What survives is the cadence structure plus the translation phasor.

Three cadences are independent, tunable parameters:

- `dt` (slot length). The sampling interval along each walk.
- `pose_period` (slots between full SMPL-X re-pose). Between re-poses, the body articulation is frozen.
- `recompute_period` (slots between full channel recompute). For the deterministic arm this is the ray-trace cadence, the dominant cost. Between recomputes, the body's bulk translation is applied analytically by the coherent Q translation phasor (`coherent/translation.py` `q_translate`): the pose-frozen per-path Gram is refreshed by `exp(-j k0 (k_hat . delta))` without re-tracing or re-posing. This is the production version of the trick `plaza_run` used for per-slot speed, and it is why coherent dosimetry does not blow up the time loop. The phasor refreshes the exposure operator Q, so it gives the per-person scalar exposure ($\mathbf{x}^H Q \mathbf{x}$) at slot cadence, which is exactly the headline metric. The full per-triangle $S_{\mathrm{ab}}$ map is recomputed only at `recompute_period` (and for the visualization tab), not every slot.

This makes temporal resolution a free knob. The default is coarse and cheap. After we measure the cost on real hardware, the cadences can be dialed toward per-slot if the GPU and schedule allow. Cost discovery (wall-clock per slot for ray tracing versus the stochastic draw, and GPU memory) is an explicit early task, and the chosen defaults follow from it. The stochastic draw is cheap, so the knob matters mainly for the deterministic arm.

## Exposure metric and normalization

The headline random variable is **per-person time-averaged exposure** over the walk, expressed as a fraction of the ICNIRP limit. The per-timestep instantaneous distribution is also retained.

Normalization is the part that makes cross-city results meaningful.

- **Marginalize over deployment realizations.** A realization is one random draw of the Ginibre site layout. For each city, the K realizations give a distribution of exposure CDFs. Report the expected CDF with an uncertainty band. A single unlucky close-site layout is one draw, not a skew. v1 runs K=1, marginalization comes once a single realization works.
- **No grand cross-city mean.** Report per-city CDFs. Explain the spread across cities with covariates: site density, building-footprint density, line-of-sight fraction. The result is a relationship, not an average.
- **Paired, scale-invariant agreement.** The det-vs-stoch comparison is paired within scenario: the same body at the same instant under the same deployment, computed both ways. Report the agreement as a scale-invariant error (log-ratio or dB error) and as a distance between the two CDFs. Magnitude divides out, so high-exposure cities do not dominate, and the disagreements are the finding.

## Visualization

Two surfaces.

- **Analytics.** matplotlib with scienceplots (the style already used in `pedestrian_flow_ABM` and AEGIS figures): CDFs, agreement plots, per-city comparisons, footprint heatmaps.
- **Internal HPC tab.** A new tab in the AEGIS React/R3F frontend, client-invisible, low polish. It loads a completed run and lets the user scrub it: city mesh, base-station markers, the crowd walking, exposure coloring on bodies. It reuses the existing scene components (city, phantom, antenna, heatmap) and a new results-loading store slice. Built for follow-along, validation, and debugging, not for clients.

## Configuration and defaults

Parameters and their proposed defaults. Defaults marked TBD-after-measurement are set by the cost-discovery task.

v1 starts deliberately small (one city, a few blocks, a small crowd, a short window). Every size is a grow-later knob.

```yaml
cities:
  count: 1                  # start with one, code for many
  radius_m: 200             # small dense core to start (~0.13 km2), grow later
mobility:
  n_agents: 50              # start small; grow until the CDF converges (~1000)
  window_s: 60              # synchronized crowd window, grow later
  walk_speed_mps: 1.4
  user_fraction: 0.5        # active (schedulable) vs bystander
deployment:
  process: ginibre          # repulsive thinning of rooftop candidates
  density_source: dataset    # real macro-site count in the footprint, scalar
  densification: 1.0        # optional 6G overlay multiplier on site count
  realizations_K: 1         # one random site layout to start; raise to ~20 to marginalize
  sectoring:
    sectors: 3              # panels per site, 120 deg apart
    az_coverage_deg: 120    # each panel's azimuth wedge (+/- 60 deg)
    max_range_m: 150        # mmWave useful range; bodies beyond are not lit or served
  equipment:                # AEGIS-side scenario, not a 38.901 preset
    name: mmwave_mamimo_28ghz
    array: [8, 8]           # UPA elements per panel
    tx_power_dbm: 30
    height_class: rooftop
    freq_hz: 28.0e9
  precoder: mrt             # fixed beam toward served users, no optimization
channel:
  stochastic: coherent_38901   # AEGIS-native coherent cluster channel (UMi)
  los_blend: p_los          # P_LOS(d)-weighted LOS/NLOS, geometry-blind
  seed: 42
dosimetry:
  level: 7                  # coherent MIMO Sab = ||G_tilde x||^2 (>=7 implies coherent)
temporal:
  dt_s: TBD                 # set after cost measurement
  pose_period: TBD
  recompute_period: TBD
```

## Dependencies and setup

The body model and ray tracer pull heavy optional dependencies that must be provisioned on every compute node.

- SMPL-X posing needs `smplx` and `torch` (the `aegis[body]` extra). Model weights are a manual download from the MPI-IS site, placed at `~/.aegis/models/smplx/SMPLX_{GENDER}.npz`. `plaza_run` already relies on these, so the lab has them.
- Walking motion needs AMASS clips in AEGIS `.npz` pose format (`PoseStream.load`). A small set of walking clips (for example CMU or ACCAD) is pre-ingested and staged on the cluster. AMASS itself requires a separate licence and download.
- The deterministic arm needs DiffeRT (the `aegis[rt]` extra), which runs on CPU via JAX and uses GPU when present.
- Mobility needs a Google Directions API key. Routes are cached aggressively (the ABM already caches agents) because the API is billed per call.

For the cost-discovery spike, a static STL phantom (for example `duke`) translated and yaw-rotated along the path is a cheap stand-in for the SMPL-X twin. It drops the `smplx`/`torch`/AMASS dependency and isolates the ray-tracing cost. The SMPL-X twin is the production path, the static phantom is the fallback if posing dominates the budget.

## Execution and hardware

One job is one (city, deployment realization, agent-chunk) task, dispatched as a scheduler job array (PBS or Slurm). There is no cross-task communication. The per-task resource assumption (CPU cores, GPU, memory) is fixed by the cost-discovery spike. The deterministic arm runs DiffeRT locally on the node when a GPU is present, with `src/aegis/modal_rt` GPU offload as the fallback when nodes are CPU-only. The coherent dosimetry kernel and the coherent 38.901 channel are JAX, so they use the GPU when present and fall back to CPU.

## Data flow

```
GHSL raster ---> population-weighted OD sampling ---> Google Directions ---> lat/lon walks
                                                                                  |
OSM ---> AEGIS mesh (cached) ---> local ENU frame <-------------------------------+
                |                          |
                |                          v
                |                  SMPL-X walking bodies (PoseStream + ParametricBody)
                v                          |
 Ginibre deployment (K realizations) ------+
                |                          |
                +----> deterministic: ray trace, TE/TM coherent       --\
                |                                                         >--> coherent Sab = ||G_tilde x||^2
                +----> stochastic:   coherent 38.901, P_LOS-weighted   --/
                                                                                  |
                                                              per-person exposure samples
                                                                                  |
                                            marginalize over K, per-city CDFs, paired agreement
                                                                                  |
                                                       matplotlib analytics + R3F HPC tab
```

## Open questions and risks

- **Ray-tracing cost.** Ray tracing the full city mesh per body per timestep across cities and realizations is the dominant cost and the schedule risk. The framerate knob and the cost-discovery task exist to bound it. Modal GPU offload is the fallback if local CPU is too slow.
- **Stochastic channel realism.** The stochastic arm is a $P_{\mathrm{LOS}}(d)$-weighted blend of UMi LOS/NLOS statistics, geometry-blind by design. Open: whether UMi is the right family for every city, and whether the coherent 38.901 reimplementation (steering phases plus XPR) matches a reference closely enough. Validate the new generator against Sionna's 38.901 on a fixed link before trusting it.
- **Precoder and user assignment.** Open: how ABM users are assigned to sites (nearest, or strongest-channel), and whether one beam per served user per site suffices. MRT is the fixed default, alternatives are a sensitivity knob.
- **Fairness of total power.** The deterministic and stochastic arms must agree on total radiated and incident power before their spatial $S_{\mathrm{ab}}$ maps are compared. Normalize and check `paths.total_power` per arm.
- **Native mesh fidelity.** AEGIS's OSM-to-mesh has known imperfections. The plan is to validate empirically that geometry fidelity does not move the exposure CDF (a one-city check), not to assume it.
- **Google Directions cost and caching.** Routing is billed per call. Cache aggressively (the ABM already caches agents). Order 1000 agents per city is affordable, larger runs need care.

## Testing

- Unit: deployment point process respects minimum spacing and target density. ENU projection round-trips. Walk interpolation produces the right number of slots for a given `dt`.
- Physics: deterministic and stochastic arms produce comparable total power for a trivial single-site, single-body, free-space case. The coherent 38.901 generator reproduces a reference (Sionna) channel's statistics on a fixed link. $S_{\mathrm{ab}}$ is non-negative (existing property tests cover the engine).
- Integration: a tiny end-to-end run (one small city, few agents, one realization, both channels) completes and writes a CDF.
- The Mie regression test remains the canary for the engine itself.

## Suggested build order

1. Cost-discovery spike: measure ray-tracing and coherent-dosimetry wall-clock per slot on a real city mesh, set the temporal cadences.
2. Headless run on one small Ghent core (radius 200 m, ~50 agents, 60 s window, a handful of sectored sites, K=1), deterministic-only, coherent Sab with the fixed MRT beam, writing per-person exposure.
3. Write the coherent 38.901 stochastic channel (steering phases plus XPR), validate it against a reference on a fixed link.
4. Add the stochastic arm with the P_LOS-weighted blend and the paired comparison.
5. Add the deployment generator and K-realization marginalization.
6. Multi-city orchestration and the covariate analysis.
7. The internal R3F HPC tab.
