# JSAC paper — work briefs

These are client-style briefs for the work items called out in `../ROADMAP.md`. Each one says what we want, why we want it, what blocks it, and what's already in place to lean on. They deliberately avoid prescribing function signatures, file layouts, or algorithms — those are dev judgement calls.

Read `../ROADMAP.md` first for the big picture. Read `../../planning/paper_v2.tex`, `../../planning/paper_spine.md`, and `../../planning/ARCHEOLOGY.md` for paper-side context. The monograph (`/home/user/aegis/theory/monograph_v2.tex`) and `theory/system_formalism.tex` are the theory source-of-truth for everything coherent / Q / ECBF.

## The briefs

| # | File | One-line | Blocked on |
|---|---|---|---|
| 01 | `01_smplx_seeding.md` | Make the SMPL-X parametric body actually load on this machine | — |
| 02 | `02_amass_pose_ingest.md` | Bring in ~50 walk-cycle pose traces as a reusable corpus | 01 |
| 03 | `03_multibody_ecbf_solver.md` | The multi-body QCQP precoder from §IV (the algorithmic contribution) | — |
| 04 | `04_q_refresh_speedup.md` | Get 50-body Q refresh under 100 ms (factored Fresnel + translation phasor) | — |
| 05 | `05_theorem2_tightness_figure.md` | One figure on how loose the rank-1 Cauchy bound actually is | — |
| 06 | `06_csi_calibration_residual.md` | Implement and characterise §V.B path-dictionary calibration | — |
| 07 | `07_tier_c_decision.md` | Decide and possibly model tier-C ISAC RCS detection | — |
| 08 | `08_plaza_run_assembly.md` | The Brussels plaza closed-loop scenario (the paper's hero machine) | 01, 02, 03 |
| 09 | `09_paper_figures.md` | Hero Pareto + chronic-dose + pose-info-gain ablation from plaza outputs | 08 |

## Dependency graph

```
                   ┌────────────────────────────────────────────┐
                   │          PARALLEL WAVE 1 — no blockers     │
                   │                                            │
                   │  01 SMPL-X seeding                         │
                   │  03 multi-body ECBF solver                 │
                   │  04 Q-refresh speedup                      │
                   │  05 Theorem 2 tightness figure             │
                   │  06 CSI calibration residual               │
                   │  07 tier-C decision (and maybe code)       │
                   │                                            │
                   └─────────────┬─────────────────────┬────────┘
                                 │                     │
                                 ▼                     │
                   ┌─────────────────────────┐         │
                   │ PARALLEL WAVE 2          │        │
                   │                          │        │
                   │  02 AMASS pose ingest    │        │
                   │  (needs 01 to apply pose)│        │
                   │                          │        │
                   └─────────────┬────────────┘        │
                                 │                     │
                                 ▼                     ▼
                   ┌──────────────────────────────────────────┐
                   │ SEQUENTIAL — depends on 01, 02, 03       │
                   │                                          │
                   │  08 plaza_run assembly                   │
                   │                                          │
                   └─────────────┬────────────────────────────┘
                                 │
                                 ▼
                   ┌──────────────────────────┐
                   │ SEQUENTIAL — depends on 08│
                   │                           │
                   │  09 paper figures         │
                   │  (hero + chronic + pose)  │
                   │                           │
                   └──────────────────────────┘
```

## Parallelism notes

Wave 1 has six independent briefs. With one developer this is purely a serial schedule; with two or three it can compress significantly. 04 (Q-refresh speedup) is the longest single-dev item and the least urgent for paper acceptance — it validates the cadence claim but the paper can ship with honestly-reported 378 ms numbers if 04 slips. 05, 06, 07 are each <1 day and produce small targeted artefacts.

01 is the only true gate for 02 (you need the model to apply pose to it). 02 in turn gates 08 alongside 01 and 03. Once 08 is running, 09 is mostly figure-making and parameter sweeps.

## Cross-cutting conventions

- **Where one-off paper scripts go**: `JSAC/code/experiments/<name>/` next to the existing `rank_check/` and `gpu_benchmark/`. Each gets its own README, run script, and outputs.
- **Where reusable code goes**: `src/aegis/`, organised per the ROADMAP's §7 sketch (`coherent/`, `twin/`, `sensing/`, `mimo/`). The sketch is suggestion, not law — push back if a given brief wants a different shape.
- **What gets removed**: nothing. The MakeHuman / GLB / Mixamo / Anny / glTF-skeleton code stays in the repo throughout the JSAC push. The paper just doesn't use it.
- **What gets ignored for the paper but still tested**: the existing 154-test suite must keep passing. The Mie regression test is the canary — if it fails, the physics broke.
- **Who owns the paper-side prose**: not the dev. Once the figures land in `JSAC/code/experiments/<x>/figures/`, the paper rewrite is a separate pass — the dev's job ends at "figure exists, captions match the data, file paths committed."

## How to use these briefs

Each brief is self-contained. Pick one whose blockers are satisfied, read it end-to-end, then go look at the codebase pointers it lists. If something in the brief is wrong (incompatible with the code as it actually exists, or asks for the wrong thing given what you find), push back — these were written from a roadmap survey, not from a sit-down with the code.

Where a brief says "open question" or "for you to decide", that's deliberate. Make the call, write a one-line note in the experiment README explaining what you decided and why, and move on.
