# Plaza run — JSAC §VII hero scenario

50 SMPL-X bodies on AMASS walk-cycles in Brussels Grand Place, 8x8 panel
at 26 GHz, five precoders compared per slot. NPZ outputs feed brief 09's
hero Pareto, chronic-dose CDF, and pose-info-gain ablation.

Source brief: `JSAC/code/prompts/08_plaza_run_assembly.md`. Plan in
`/home/user/.claude/plans/jsac-planning-paper-v2-tex-jsac-code-roa-bright-book.md`.

## Decisions made (per the plan + Robin's calls)

| Choice | Picked |
|---|---|
| RT engine | Sionna (Modal L4) — replaces brief's nominal DiffeRT |
| Path generators | `plaza_specular` (deterministic LOS + ground + 2 facades, image method) and `uma_los` (3GPP 38.901 stochastic) side by side; `sionna_dict` wired with graceful fallback |
| PHY | Shannon-rate proxy first; Sionna NR PHY pass deferred to follow-up |
| Pose ablation | `--ablate-pose-telemetry` flag downgrades tier-A/B to T-pose (Cauchy-style envelope) |
| Tier-C | `aegis.sensing.detection()` per slot; detected → T-pose Q (position only); undetected → excluded from solver (occupancy envelope handled regulator-side) |
| Solver fail | `min-absorption` returns flagged in NPZ; precoder kept rather than swapped to MRT |
| Scene | hand-placed BS panel (Brussels parquet has no mmWave sites — top freq 3.75 GHz). OSM scrape cached at `data/scenes/brussels_grand_place/` for preflight only |
| Tier split | 25 / 15 / 10 (A / B / C), static, seeded |
| Cadence | fake clock; pose every 30 frames (1 s), RT every 30 frames (1 s), Q + precoder every frame |
| Mesh | SMPL-X (20908 tri) decimated by stride 10 → ~2090 tri/body; areas rescaled |

## Layout

```
plaza_run/
  run.py             entrypoint; argparse + per-mode dispatch
  scenario.py        BS panel, body spawns, tier split, walk traces, AMASS picks
  scene_cache.py     Overpass scrape + cache (preflight only; not on critical path)
  paths.py           plaza_specular / uma_los / sionna_dict generators
  budgets.py         per-body L_RL, L_BR, active = min(...) per paper §IV.D
  tier_c.py          ISAC RCS detection wrapper (aegis.sensing)
  phy.py             Shannon-rate proxy (+ Sionna NR PHY hook)
  slot_loop.py       per-slot tick: pose / Q refresh / 5 precoders / p_abs / sumrate
  outputs.py         NPZ + run.json writer
  preflight.py       2-panel scatter: top-down + side view, written to outputs/
  outputs/           NPZs + cadence JSON + preflight.png
  README.md          this file
```

## Reproduction

```bash
# 0. Make sure SMPL-X is seeded (brief 01) and AMASS is ingested.
python scripts/ingest_amass.py \
  --input data/poses/amass_smplx_g/BMLrub \
  --output data/poses/plaza_run_walks \
  --filter walk --max-sequences 60

# 1. Visual preflight (no OSM scrape; the OSM cache is built lazily by scene_cache).
python -m JSAC.code.experiments.plaza_run.preflight --seed 42 --no-osm

# 2. Production: plaza_specular + 3GPP UMa-LOS comparator, pose-aware.
JAX_PLATFORMS=cpu AEGIS_ARRAY_BACKEND=jax \
python -m JSAC.code.experiments.plaza_run.run \
  --seed 42 --n-slots 600 --paths both --pose-period 30 --rt-period 30

# 3. Pose-info-gain ablation (proposed-ablated).
JAX_PLATFORMS=cpu AEGIS_ARRAY_BACKEND=jax \
python -m JSAC.code.experiments.plaza_run.run \
  --seed 42 --n-slots 600 --paths plaza_specular --ablate-pose-telemetry
```

JAX is forced to CPU because the per-body host dispatch overhead beats the
GPU on this slot loop (each body's translation phasor + q_translate is a
tiny einsum that a `vmap`-batched JAX path could lift onto the GPU; that is
left as a follow-up — see "Open follow-ups" below).

## NPZ schema

| Key | Shape | dtype | Notes |
|---|---|---|---|
| `p_abs` | `(T, B, P)` | float32 | absorbed power per body per precoder per slot, W |
| `sumrate` | `(T, P)` | float32 | served-user sum-rate per slot, bps |
| `violation` | `(T, B, P)` | bool | per-body RL/BR breach flag |
| `infeasible` | `(T, P)` | bool | min-absorption fallback fired (multibody_ecbf / oracle only) |
| `tier` | `(B,)` | uint8 | 0=A, 1=B, 2=C |
| `body_positions` | `(T, B, 3)` | float32 | walk traces, plaza-frame [m] |
| `cadence_ms` | `(T, 4)` | float32 | per-stage wall-clock per slot: q_refresh, precoder, rt, phy |
| `precoder_names` | `(P,)` | U16 | mrt, zf, wc_backoff, multibody_ecbf, oracle |
| `body_budgets_w` | `(B,)` | float32 | active per-body L = min(L_RL, L_BR), W |
| scalars | — | — | seed, freq_hz, tx_power_dbm, n_bodies, n_slots, dt_s, scene_hash, phy_mode, pose_mode, paths_mode |

Filename pattern: `plaza_run_seed{N}_phy{shannon|sionna}_pose{aware|ablate}_paths{dict|uma}.npz`.
Run metadata + cadence-table breakdown lives in the sibling `.json`.

## Empirical observation worth flagging to brief 09

At 30 dBm, K=25 served users, and bodies in 5-55 m: **the Brussels RL is
not binding for any precoder.** P_abs / budget median is ~10⁻⁴; MRT itself
satisfies every budget by ~four orders of magnitude. This matches paper
`tab:bind` (binding distance `r* ≈ 2.7 m` at K=25) and the §VII.D
contingency in `paper_spine.md` §8: when MRT doesn't violate, the
chronic-dose narrative carries the value proposition. All five precoders
collapse to MRT in this regime.

For brief 09 to produce a hero figure with precoder separation, plaza_run
should be re-run in a binding regime: any of (a) close-range bodies (1-5
m), (b) low served-user count (K=1-5), (c) higher TX power (55 dBm EIRP
per operator). Brief 09 owns that figure choice; this brief produces the
NPZ at the paper's nominal macro-op spec.

The chronic-dose CDF (§VII.E) is unaffected — it integrates p_abs over
the trace regardless of binding. That figure can be produced from these
NPZs as-is.

## Open follow-ups

- Sionna pre-baked dictionary (the planned RT path): `paths.py::SionnaDictionary` is wired to `aegis.modal_rt.sionna_tracer.SionnaTracer.trace_bundled`, but defaults to a fallback because the bundled "etoile" scene differs materially from Brussels Grand Place. Replacing with a real Brussels Mitsuba scene or an OSM-derived voxel scene through `trace_voxel` is a clean follow-up and keeps the §V "scene as path dictionary" narrative honest.
- Sionna NR PHY pass for served sum-rate: `phy.py` exposes the hook; brief 08 stayed with the Shannon proxy because the Sionna L4 round-trip per slot is non-trivial wall-clock.
- JAX vmap batching across bodies for `compute_static_path_gram`: unlocks the GPU. Brief 04 already shipped `compute_q_batch_vmap`; wiring plaza_run's pose-cadence rebuild through it would drop pose-tick wall-clock by ~10x on a workstation GPU.
- Warm-start λ in `solve_multibody_ecbf` from previous slot. Brief 03's done-doc flagged this; under the current (non-binding) regime it doesn't matter, but for low-K runs the ECBF solve dominates the budget.
- 9000-slot full 5-min run. The current 600-slot pass exercises the pipeline at a tractable wall-clock; brief 09 can extend `--n-slots 9000` on a workstation GPU once the vmap path lands.

## Cadence achieved

`cadence_ms` in each NPZ is per-slot wall-clock for the four stages
(`q_refresh, precoder, rt, phy`). The companion `run.json` has p10 / p50 /
p90 across the run. With JAX-CPU + numpy-batched p_abs on a workstation
CPU these typically come in around:

| Stage | p50 (ms) | what it covers |
|---|---|---|
| `q_refresh` | ~60 | numpy `q_translate` + numpy `translation_phasor` × 50 bodies × 2 (posed + tposed); JAX `compute_static_path_gram` only fires at pose cadence |
| `precoder` | ~30 | mrt + zf + wc_backoff + multibody_ecbf (proposed) + multibody_ecbf (oracle) |
| `rt` | <1 | plaza_specular path eval × 50 bodies, only at RT cadence |
| `phy` | ~110 | five Shannon sum-rate evals + five batched per-body p_abs |

Per-slot total ~200 ms on CPU. The paper's `tab:cadence` claim (1 ms
slot, 100 ms pose) is not achieved here without the JAX-vmap follow-up;
the values reported faithfully reflect what the unbatched path delivers
on this hardware.
