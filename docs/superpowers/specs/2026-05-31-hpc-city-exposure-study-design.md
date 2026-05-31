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
- `src/aegis/integration/differt.py` `paths_from_differt_scene` (full TE/TM tracking) is the deterministic arm. `src/aegis/viewer/raytracer.py` `compute_paths_differt` is the incoherent-only shortcut.
- `src/aegis/environment/__init__.py` `EnvironmentMesh.from_osm` builds the city mesh.
- `src/aegis/geometry/pose_stream.py` `PoseStream` and `src/aegis/geometry/parametric.py` `ParametricBody` pose the walking SMPL-X body.
- `src/aegis/coherent/translation.py` (`translation_phasor`, `q_translate`) provides the cheap per-frame field refresh between full re-poses. This is the production version of the trick `plaza_run` reimplements locally.
- `src/aegis/paths.py` `PropagationPaths.from_powers` is the common path container both channel arms produce.

Code borrowed (copied and adapted, not imported):

- The mobility model from `pedestrian_flow_ABM` (`pedestrian_ABM.py`): GHSL population sampling and Google Directions walking routes.
- The trajectory plus multi-body plus CDF-accumulation skeleton from `plaza_run/scenario.py`, `slot_loop.py`, `outputs.py`, with the ECBF content removed.
- OSM-to-mesh geometry logic from `hybrid-QuaDRiGa-FDTD/outdoor_environment.py` where it improves AEGIS's native builder.

Parallelism is over the independent axis (city, deployment realization, agent). The within-agent time loop is serial. No multi-node coordination is required, so a job array (one task per chunk of agents per realization per city) is sufficient.

## Pipeline, per city

1. **City mesh.** AEGIS-native OSM build to a materialed triangle mesh: building footprints, heights, tag-based materials, ground plane. One fixed bounding box of urban core per city, same nominal area across cities. Cached to disk so it is built once.
2. **Walks.** Sample home and destination positions weighted by GHSL population density. Route each with the Google Directions API in walking mode. Decode polylines to a lat/lon path. Project to the city local ENU frame using the same origin as the OSM mesh. Each agent walks at a sampled speed (default 1.4 m/s). The agent is an SMPL-X body posed walking, heading set to the path tangent.
3. **Deployment.** A repulsive point process (minimum-spacing, Ginibre-style) places base-station sites. Site density is anchored to the real site count for that city (read once from the base-station dataset, used only as a scalar density, not as per-site attributes). Sites are snapped to building rooftops. Each site is configured from one forward-looking equipment scenario (default 28 GHz mmWave MaMIMO: fixed array geometry, transmit power, height class). K independent realizations are sampled per city.
4. **Dual-channel exposure.** For each (deployment realization, agent, timestep), build the incident field two ways. Deterministic: ray trace the city mesh from the active sites to the body via `paths_from_differt_scene`. Stochastic: `generate_channel` with the matching 38.901 scenario per link, seeded for reproducibility. Both produce `PropagationPaths`. Both feed the same `DosimetryEngine.compute` at an incoherent level. Coherent is available but off.
5. **Exposure reduction.** Per-triangle $S_{\mathrm{ab}}$ reduces to a per-person exposure sample per timestep, then to a per-person summary over the walk.

The core absorption law is unchanged:

$$S_{\mathrm{ab}}(\mathbf{r}) = S_{\mathrm{inc}} \cdot T_0 \cdot [\hat{n}(\mathbf{r}) \cdot (-\hat{k})]_+$$

### Physics note: beamformed source, incoherent body

The deployment is MaMIMO and forms beams toward served users. Beamforming shapes the source radiation pattern (the beam points at served agents, bystanders get sidelobes and occasional main-lobe sweeps). The body-side absorption is still computed incoherently from the resulting incident field. This matches the prior IEEE Access work (precoding plus incoherent exposure) and keeps the default path on the well-tested incoherent kernels. The served-versus-bystander split comes from the ABM: a configurable fraction of agents are users (beam targets), the rest are non-users.

## Temporal model and the framerate knob

The time-stepped slot machinery from `plaza_run` is kept. The ECBF solve inside it is removed. What survives is the cadence structure plus the translation phasor.

Three cadences are independent, tunable parameters:

- `dt` (slot length). The sampling interval along each walk.
- `pose_period` (slots between full SMPL-X re-pose). Between re-poses, the body shape is frozen.
- `recompute_period` (slots between full channel and exposure recompute). Between recomputes, the body's bulk translation is applied analytically by the translation phasor (`coherent/translation.py`), which refreshes the incident-field response cheaply without re-tracing or re-posing.

This makes temporal resolution a free knob. The default is coarse and cheap. After we measure the cost on real hardware, the cadences can be dialed toward per-slot if the GPU and schedule allow. The cost discovery (wall-clock per slot for ray tracing vs stochastic, GPU memory) is an explicit early task, and the chosen defaults follow from it rather than being asserted now.

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
  bbox_area_km2: 1.0        # fixed urban-core box per city, same nominal size
mobility:
  n_agents: convergence     # grown until the CDF converges, order 1000
  walk_speed_mps: 1.4
  user_fraction: 0.5        # served (beam target) vs non-user
deployment:
  process: ginibre          # repulsive, minimum spacing
  density_source: dataset    # real site count for the city, scalar only
  realizations_K: 20        # 10-30, enough for a stable band
  scenario: mmwave_mamimo_28ghz   # array, power, height class
frequency_hz: 28.0e9        # primary; 3.5 GHz arm is a later add
temporal:
  dt_s: TBD                 # set after cost measurement
  pose_period: TBD
  recompute_period: TBD
dosimetry:
  coherent: false
  level: 3                  # incoherent spatial level, confirm at implementation
```

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
- **Stochastic per-link scenario assignment.** The stochastic arm needs the correct 38.901 scenario (LOS or NLOS, UMi-type parameters) per body-site link to be a fair comparison. The LOS or NLOS label can be derived from a cheap visibility test against the city mesh (the same trick `outdoor_environment.py` used to feed QuaDRiGa).
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
