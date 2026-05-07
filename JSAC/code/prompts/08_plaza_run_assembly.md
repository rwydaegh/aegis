# 08 — Plaza run assembly

**Goal.** A runnable script — call it `plaza_run.py` — that simulates 5 minutes of the Brussels Grand Place plaza, with 50 SMPL-X bodies on AMASS walk traces, an 8×8 base-station panel mounted on a facade, ray-traced paths via DiffeRT, and the full §IV multi-body precoder solving every slot. Outputs go to NPZ files that brief 09 turns into figures.

This is **the paper's hero machine**. Everything else feeds into it; everything in §VII reads out of it.

## Blockers

- **01 (SMPL-X seeding)** — bodies must be loadable.
- **02 (AMASS pose ingest)** — bodies need walk traces.
- **03 (multi-body ECBF solver)** — the `(Q_tot + νI)⁻¹ g_k` precoder must exist.

Helpful but not strictly blocking:
- **04 (Q-refresh speedup)** — the cadence claim depends on this. If 04 isn't done when this brief runs, the script still runs, just slower than the paper claims. Report measured timings honestly.
- **07 (tier-C decision)** — affects how the script handles tier-C bodies. Either cooperating-style ISAC RCS, or worst-case Cauchy back-off. Decide which is wired before running.

## Why this matters

Paper §VII (`paper_v2.tex`, `paper_spine.md` §5) has a full setup paragraph but no actual results — the hero figure has X/Y/R3/R5 placeholders. This brief produces the data. Without it, §VII.D is unsupported, §VII.E (chronic dose) is narrative only, and the entire "Brussels RL binds under MRT/ZF at 26 GHz" claim is unanswered. ARCHEOLOGY's "still unsettled" list ranks this as the paper's primary empirical risk.

## What's already in place

The codebase has *every component this brief needs*. Nothing here is a from-scratch build:

- `src/aegis/environment/` (4 600 LOC) — OSM ingest, terrain, facades, roofs, materials, GeoJSON. Brussels Grand Place can be pulled from OSM directly.
- `src/aegis/integration/differt.py` — DiffeRT ray tracer bridge.
- `src/aegis/modal_rt/` — Modal-hosted T4 (DiffeRT) and L4 (Sionna) GPU offload. Already wired, tested in production.
- `src/aegis/basestation/` — antenna placement, MSI pattern parser, parquet IO, regional libraries. The Brussels parquet (`data/basestations/merged/brussels.parquet`) ships with the repo.
- `data/channel_presets/` — 91 3GPP TR 38.901 / 37.885 channel presets. UMa-LOS at 26 GHz is the paper's choice.
- `src/aegis/coherent/` — `Q`, `ρ`, ECBF (single-body); plus the multi-body solver from brief 03.
- `src/aegis/mimo/compute.py` (557 LOC) — `compute_mimo_scene_with_bodies()` is the orchestration entry point. May or may not be the right level of abstraction for this brief; investigate.
- `src/aegis/compliance/` (1 400 LOC) — ICNIRP 2020 limits, sweeps, link-budget evaluation. Useful for the "convert RL cap to per-body P_abs budget" step.
- `src/aegis/optim/` — has `placement.py`, `tilt_power.py`, `mimo_peak.py`, `loop.py`. Worth checking whether `loop.py` already has a closed-loop simulation skeleton.

The two existing JSAC experiments (`JSAC/code/experiments/rank_check/`, `gpu_benchmark/`) are the right reference for how a paper experiment is structured: README, run script, deterministic seed, NPZ outputs, hash-pinned scene assets.

## The scenario, restated

Paper §VII.A:
- **Scene:** Brussels Grand Place, OSM-derived. Approximately 100 × 100 m. Buildings to ~20 m, ground plane.
- **BS:** one 8×8 dual-pol panel on a facade overlooking the plaza, broadside facing into it. 26 GHz. 30 dBm total transmit power.
- **Bodies:** 50 SMPL-X, distributed roughly 25 / 15 / 10 across tiers A / B / C. AMASS walk-cycles at 30 Hz, 5 minutes wall-clock. Trajectories should keep them in the plaza, varying ranges 5–60 m.
- **Channel:** 3GPP 38.901 UMa-LOS, plus the deterministic plaza-specular geometry as a sanity comparison (both already used by `rank_check`).
- **Cadence (paper `tab:cadence`):** CSI 1 ms, precoder 1 ms, Φ(t) ~1 s, pose ~100 ms, RT ~ seconds, calibration seconds. The script doesn't need a real scheduler — fake the clock and tick at the right ratios.
- **Comparators:** MRT, ZF-to-served-users, worst-case power back-off, the proposed multi-body ECBF (brief 03), and a "pose-known oracle" that uses ground-truth pose for tier-C. Five precoders per slot.
- **Budgets:** Brussels RL at 14.57 V/m → per-body `L_RL` via the formula in §IV.D (and `tab:bind`). ICNIRP BR at 5.6 W WB-SAR → per-body `L_BR`. Active budget per body is `min(L_RL, L_BR)`.

## The outputs the script needs to produce

Per-body, per-slot, per-precoder:
- `P_abs(t)` time series (5 min × 30 Hz = 9 000 frames × 50 bodies × 5 precoders = 2.25M samples — a few hundred MB at most as float32).
- Served sum-rate per slot (for users only, K varies by tier).
- Compliance flag (did this slot violate the body's `min(L_RL, L_BR)` budget?).
- Cadence wall-clock breakdown (Q-refresh time, precoder solve time, RT time) — populates `tab:cadence` honestly.

These go to NPZ files in `JSAC/code/experiments/plaza_run/outputs/` with a deterministic naming convention. Brief 09 reads them.

## Open questions for the dev

- **OSM scrape vs. cached scene.** Pull from Overpass at runtime, or cache a snapshot of Brussels Grand Place to `data/scenes/brussels_grand_place/`? Caching is cleaner for reproducibility.
- **BS placement details.** Which facade, what height, what tilt. Decide once you see the OSM scene; document the choice.
- **Walk trajectory generation.** AMASS gives pose; you also need root translation paths through the plaza. Either bake them into the corpus during brief 02, or generate them at run time here. Whichever, set seeds.
- **Tier assignment.** 25 / 15 / 10 is the paper's split. Consistent assignment across the 5-min run, or randomly resampled? The paper implies static.
- **Whether to actually do Sionna PHY.** Paper mentions "Sionna 3GPP-NR PHY, OFDM mu=2, MCS tables, BLER-driven" for the served sum-rate. That's a *lot* of overhead per slot. A cleaner first pass: link-adaptive Shannon-rate proxy, with Sionna left as a follow-up if reviewer demands it. Decide early; it changes the run-time budget by an order of magnitude.
- **How to fake the cadence.** Cleanest: each "slot" is one Python iteration; some quantities refresh every iteration, others every 100 / 1000 iterations. No real wall clock. The cadence breakdown comes from instrumenting the function calls.
- **GPU offload boundary.** Ray tracing → Modal (already wired). Q construction → JAX local? Mixing has overhead — keep both on the same machine if possible.
- **Failure handling.** What does the script do when the multi-body solver returns infeasible? Skip the slot? Use MRT fallback? Log and move on?
- **Where the script lives.** `JSAC/code/experiments/plaza_run/run.py` is the natural home. Outputs go to a sibling `outputs/` dir.
- **Scene pre-flight.** Use the viewer to load the assembled OSM + BS placement + 50 body initial positions and eyeball it before going headless. The viewer is great at this; ROADMAP §5 makes the case.

## What "done" looks like

- `python plaza_run.py --seed 42` runs end-to-end without errors and emits NPZ outputs.
- A README documenting the scenario settings, the precoders compared, the budget conversion, and the runtime budget actually achieved (per-slot wall clock, broken down).
- The five-precoder comparison data is in NPZ form, ready for brief 09.
- A scene visualisation (one screenshot of the loaded plaza with bodies + BS, captured via the viewer) lands in the experiment dir for sanity.
- The Mie golden test still passes — i.e. brief 03 / 04 didn't break the underlying physics.
- Modal-hosted RT is *optional* — if 50-body × 9000-frame paths fits on the workstation GPU within the run time budget, fine. Modal is the escape hatch when it doesn't.

## What this is NOT

- A real-time deployment. The script fakes the cadence; it doesn't run on a phone or against a real BS.
- A hyper-tuned scenario picked to make the paper look good. Use realistic settings, report what comes out. If MRT doesn't violate Brussels RL much, the chronic-dose narrative carries the paper — paper rewrite plan in `paper_spine.md` §8 already accommodates that.
- The figure-making step. NPZ outputs only; brief 09 turns them into PDFs.
- A regression test. This is one experimental run, not a unit test. Determinism (seed, frozen scene) is desirable but not enforced via pytest.
