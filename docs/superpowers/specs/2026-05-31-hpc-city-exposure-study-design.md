# HPC city-scale population exposure study

**Date:** 2026-05-31
**Status:** Draft

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
- Coherent MIMO dosimetry (levels 7-8) as the default. Available, off by default. See physics note below.

## Architecture

A new module under `src/aegis`, provisionally `src/aegis/study/` (final name decided at implementation). It is headless, config-driven, and contains no Flask dependency. One run is one config file. The module reuses production AEGIS physics and borrows logic (not as a dependency) from two existing repos.

Reuse map:

- `src/aegis/engine.py` `DosimetryEngine.compute` is the dosimetry core, run at incoherent levels.
- `src/aegis/channel/generator.py` `generate_channel` and `src/aegis/channel/presets.py` `load_preset` are the stochastic arm.
- `src/aegis/integration/differt.py` `paths_from_differt_scene(scene_path, tx_positions, rx_position, freq_hz, ...)` is the deterministic arm. It loads a Sionna XML scene, so the city mesh is exported once per city via `EnvironmentMesh.to_sionna_xml(path)` and the cached path is passed in. `compute_paths_differt` in `src/aegis/viewer/raytracer.py` is the viewer's incoherent-only shortcut (`from_powers`, one element at a time) and is for reference only, not used here.
- `src/aegis/environment/__init__.py` `EnvironmentMesh.from_osm` builds the city mesh.
- `src/aegis/geometry/pose_stream.py` `PoseStream` and `src/aegis/geometry/parametric.py` `ParametricBody` pose the walking SMPL-X body.
- `src/aegis/coherent/translation.py` (`translation_phasor`, `q_translate`) refreshes the coherent exposure operator Q cheaply. It applies only in the optional coherent mode (Q is `(M_ant, M_ant)` and is absent from the incoherent path). The incoherent default uses a different cheap refresh, described under the temporal model.
- `src/aegis/paths.py` `PropagationPaths.from_powers` is the common path container both channel arms produce.

Code borrowed (copied and adapted, not imported):

- The mobility model from `pedestrian_flow_ABM` (`pedestrian_ABM.py`): GHSL population sampling and Google Directions walking routes.
- The trajectory plus multi-body plus CDF-accumulation skeleton from `plaza_run/scenario.py`, `slot_loop.py`, `outputs.py`, with the ECBF content removed.
- OSM-to-mesh geometry logic from `hybrid-QuaDRiGa-FDTD/outdoor_environment.py` where it improves AEGIS's native builder.

Parallelism is over the independent axis (city, deployment realization, agent). The within-agent time loop is serial. No multi-node coordination is required, so a job array (one task per chunk of agents per realization per city) is sufficient.

## Pipeline, per city

1. **City mesh.** AEGIS-native OSM build via `EnvironmentMesh.from_osm(lat, lon, radius_m)` to a materialed triangle mesh: building footprints, heights, tag-based materials, ground plane. The same `radius_m` is used for every city (the footprint is circular, not square), so the analysis area is fixed across cities. The mesh is cached to disk, exported once to a Sionna XML scene (`to_sionna_xml`) for the deterministic arm, and turned into a BVH (`geometry/occlusion.build_bvh`) for visibility tests.
2. **Walks.** Sample home and destination positions weighted by GHSL population density. Route each with the Google Directions API in walking mode. Decode polylines to a lat/lon path. Project to the city local ENU frame using the same origin as the OSM mesh. Each agent walks at a sampled speed (default 1.4 m/s). The agent is an SMPL-X body posed walking, heading set to the path tangent.
3. **Deployment.** Candidate rooftop points come from `parse_osm_xml`, which returns `Building` objects carrying `footprint` (N,2 local XY) and `height`. Each building yields a candidate site at its footprint centroid raised to its roof height. A repulsive point process (minimum-spacing, Ginibre-style) thins these candidates to the final site set, with target density anchored to the real site count for that city (read once from the base-station dataset as a scalar count, not per-site attributes). Each surviving site is configured from one equipment scenario, an AEGIS-side config block (not a 38.901 preset): array geometry, transmit power, height class, frequency. The default scenario is 28 GHz mmWave MaMIMO. K independent realizations are sampled per city.
4. **Dual-channel exposure.** For each (deployment realization, agent, timestep), build the incident field two ways. Deterministic: ray trace the cached Sionna scene from the active sites to the body via `paths_from_differt_scene`. Stochastic: `generate_channel(params, freq_ghz, antenna_pos, body_center, power_dbm, seed)` with `params` from `load_preset`, seeded for reproducibility. The preset per link is chosen by a line-of-sight test: cast a shadow ray from the site to the body center against the city BVH, then map `{LOS: 3GPP_38.901_UMi_LOS, NLOS: 3GPP_38.901_UMi_NLOS}` (UMi parameters cover 28 GHz). Both arms produce `PropagationPaths`, both feed the same `DosimetryEngine.compute` at an incoherent fidelity level. Coherent is available but off.
5. **Exposure reduction.** Per-triangle $S_{\mathrm{ab}}$ reduces to a per-person exposure sample per timestep, then to a per-person summary over the walk.

The core absorption law is unchanged:

$$S_{\mathrm{ab}}(\mathbf{r}) = S_{\mathrm{inc}} \cdot T_0 \cdot [\hat{n}(\mathbf{r}) \cdot (-\hat{k})]_+$$

### Physics note: beamformed source, incoherent body

The deployment is MaMIMO and forms beams toward served users. Beamforming shapes the source radiation pattern (the beam points at served agents, bystanders get sidelobes and occasional main-lobe sweeps). The body-side absorption is still computed incoherently from the resulting incident field. This matches the prior IEEE Access work (precoding plus incoherent exposure) and keeps the default path on the well-tested incoherent kernels. The served-versus-bystander split comes from the ABM: a configurable fraction of agents are users (beam targets), the rest are non-users.

## Temporal model and the framerate knob

The time-stepped slot machinery from `plaza_run` is kept. The ECBF solve inside it is removed. What survives is the cadence structure plus the translation phasor.

Three cadences are independent, tunable parameters:

- `dt` (slot length). The sampling interval along each walk.
- `pose_period` (slots between full SMPL-X re-pose). Between re-poses, the body articulation is frozen.
- `recompute_period` (slots between full channel recompute). For the deterministic arm this is the ray-trace cadence, the dominant cost. Between recomputes the last path set is reused with a free-space correction for the body's small translation (update each path's propagation distance and phase from the new body position, and optionally re-test paths whose visibility could have changed). This is the incoherent analog of the coherent Q translation phasor, applied to scalar path power and direction rather than to the Gram operator. In the optional coherent mode, `coherent/translation.py` supplies the exact Q-phasor refresh instead.

This makes temporal resolution a free knob. The default is coarse and cheap. After we measure the cost on real hardware, the cadences can be dialed toward per-slot if the GPU and schedule allow. Cost discovery (wall-clock per slot for ray tracing versus the stochastic draw, and GPU memory) is an explicit early task, and the chosen defaults follow from it. The stochastic draw is cheap NumPy, so the knob matters mainly for the deterministic arm.

## Exposure metric and normalization

The headline random variable is **per-person time-averaged exposure** over the walk, expressed as a fraction of the ICNIRP limit. The per-timestep instantaneous distribution is also retained.

Normalization is the part that makes cross-city results meaningful.

- **Marginalize over deployment realizations.** For each city, the K realizations give a distribution of exposure CDFs. Report the expected CDF with an uncertainty band. A single unlucky close-site layout is one draw, not a skew.
- **No grand cross-city mean.** Report per-city CDFs. Explain the spread across cities with covariates: site density, building-footprint density, line-of-sight fraction. The result is a relationship, not an average.
- **Paired, scale-invariant agreement.** The det-vs-stoch comparison is paired within scenario: the same body at the same instant under the same deployment, computed both ways. Report the agreement as a scale-invariant error (log-ratio or dB error) and as a distance between the two CDFs. Magnitude divides out, so high-exposure cities do not dominate, and the disagreements are the finding.

## Visualization

Two surfaces.

- **Analytics.** matplotlib with scienceplots (the style already used in `pedestrian_flow_ABM` and AEGIS figures): CDFs, agreement plots, per-city comparisons, footprint heatmaps.
- **Internal HPC tab.** A new tab in the AEGIS React/R3F frontend, client-invisible, low polish. It loads a completed run and lets the user scrub it: city mesh, base-station markers, the crowd walking, exposure coloring on bodies. It reuses the existing scene components (city, phantom, antenna, heatmap) and a new results-loading store slice. Built for follow-along, validation, and debugging, not for clients.

## Configuration and defaults

Parameters and their proposed defaults. Defaults marked TBD-after-measurement are set by the cost-discovery task.

```yaml
cities:
  count: 10                 # spanning dense-historic, grid, sprawl morphologies
  radius_m: 565             # circular footprint, same for every city (~1 km2)
mobility:
  n_agents: convergence     # grown until the CDF converges, order 1000
  walk_speed_mps: 1.4
  user_fraction: 0.5        # served (beam target) vs non-user
deployment:
  process: ginibre          # repulsive thinning of rooftop candidates
  density_source: dataset    # real site count for the city, scalar only
  realizations_K: 20        # 10-30, enough for a stable band
  equipment:                # AEGIS-side scenario, not a 38.901 preset
    name: mmwave_mamimo_28ghz
    array: [8, 8]           # UPA elements
    tx_power_dbm: 30
    height_class: rooftop
    freq_hz: 28.0e9
channel:
  stochastic_preset_family: 3GPP_38.901_UMi   # _LOS / _NLOS chosen per link
  seed: 42
dosimetry:
  coherent: false
  level: 3                  # Fresnel-corrected incoherent Sab (angle-dependent)
temporal:
  dt_s: TBD                 # set after cost measurement
  pose_period: TBD
  recompute_period: TBD
```

A 3.5 GHz arm is a clean later addition (swap `equipment.freq_hz` and the preset family). Your prior work covered both bands.

## Dependencies and setup

The body model and ray tracer pull heavy optional dependencies that must be provisioned on every compute node.

- SMPL-X posing needs `smplx` and `torch` (the `aegis[body]` extra). Model weights are a manual download from the MPI-IS site, placed at `~/.aegis/models/smplx/SMPLX_{GENDER}.npz`. `plaza_run` already relies on these, so the lab has them.
- Walking motion needs AMASS clips in AEGIS `.npz` pose format (`PoseStream.load`). A small set of walking clips (for example CMU or ACCAD) is pre-ingested and staged on the cluster. AMASS itself requires a separate licence and download.
- The deterministic arm needs DiffeRT (the `aegis[rt]` extra), which runs on CPU via JAX and uses GPU when present.
- Mobility needs a Google Directions API key. Routes are cached aggressively (the ABM already caches agents) because the API is billed per call.

For the cost-discovery spike, a static STL phantom (for example `duke`) translated and yaw-rotated along the path is a cheap stand-in for the SMPL-X twin. It drops the `smplx`/`torch`/AMASS dependency and isolates the ray-tracing cost. The SMPL-X twin is the production path, the static phantom is the fallback if posing dominates the budget.

## Execution and hardware

One job is one (city, deployment realization, agent-chunk) task, dispatched as a scheduler job array (PBS or Slurm). There is no cross-task communication. The per-task resource assumption (CPU cores, GPU, memory) is fixed by the cost-discovery spike. The deterministic arm runs DiffeRT locally on the node when a GPU is present, with `src/aegis/modal_rt` GPU offload as the fallback when nodes are CPU-only. The stochastic arm and the dosimetry kernel are CPU and NumPy.

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
                +----> deterministic: paths_from_differt_scene  --\
                |                                                   >--> DosimetryEngine.compute --> S_ab
                +----> stochastic:   generate_channel (38.901)   --/         (incoherent)
                                                                                  |
                                                              per-person exposure samples
                                                                                  |
                                            marginalize over K, per-city CDFs, paired agreement
                                                                                  |
                                                       matplotlib analytics + R3F HPC tab
```

## Open questions and risks

- **Ray-tracing cost.** Ray tracing the full city mesh per body per timestep across cities and realizations is the dominant cost and the schedule risk. The framerate knob and the cost-discovery task exist to bound it. Modal GPU offload is the fallback if local CPU is too slow.
- **Stochastic scenario family.** Step 4 assigns LOS/NLOS by a deterministic shadow-ray test and maps to UMi presets. Open: whether UMi is the right family for every city, and whether a hard LOS/NLOS split (versus the 38.901 probabilistic LOS model) biases the comparison. Resolve with a sensitivity check.
- **Fairness of total power.** The deterministic and stochastic arms must agree on total radiated and incident power before their spatial $S_{\mathrm{ab}}$ maps are compared. Normalize and check `paths.total_power` per arm.
- **Native mesh fidelity.** AEGIS's OSM-to-mesh has known imperfections. The plan is to validate empirically that geometry fidelity does not move the exposure CDF (a one-city check), not to assume it.
- **Google Directions cost and caching.** Routing is billed per call. Cache aggressively (the ABM already caches agents). Order 1000 agents per city is affordable, larger runs need care.

## Testing

- Unit: deployment point process respects minimum spacing and target density. ENU projection round-trips. Walk interpolation produces the right number of slots for a given `dt`.
- Physics: deterministic and stochastic arms produce comparable total power for a trivial single-site, single-body, free-space case. Incoherent $S_{\mathrm{ab}}$ is non-negative and obeys the ReLU bound (existing property tests cover the engine).
- Integration: a tiny end-to-end run (one small city, few agents, one realization, both channels) completes and writes a CDF.
- The Mie regression test remains the canary for the engine itself.

## Suggested build order

1. Cost-discovery spike: measure ray-tracing and stochastic wall-clock per slot on a real city mesh, set the temporal defaults.
2. Headless single-city, single-channel run end to end (deterministic), writing per-person exposure.
3. Add the stochastic arm and the paired comparison.
4. Add the deployment generator and K-realization marginalization.
5. Multi-city orchestration and the covariate analysis.
6. The internal R3F HPC tab.
