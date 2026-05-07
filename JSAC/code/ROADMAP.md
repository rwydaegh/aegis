# JSAC paper — what we have, what we don't

*Companion to `paper_v2.tex` and `ARCHEOLOGY.md` (both in `JSAC/planning/`). Last sync: 2026-05-04.*

The paper asks for a lot. The code already covers most of the **physics**, almost all of the **incoherent ladder**, and the **coherent operator** end-to-end including the ECBF QCQP solver. What's actually missing is **scenario assembly + scenario execution**: the Brussels plaza, the closed-loop runtime that ticks at the cadences `tab:cadence` advertises, and the hero figure that compares baselines vs. the proposed precoder under the Brussels RL cap.

This roadmap separates real gaps from theoretical ornament, picks which phantom track to **build the paper on** (SMPL‑X), explains the cost difference between incoherent and coherent kernels, names the viewer's role for the paper push, and sketches where new code should live so it doesn't sediment as one‑off scripts. **Nothing in the existing codebase gets removed.** The MakeHuman GLB pipeline, the Mixamo animation library, the Anny placeholder, the parametric build scripts, the glTF skeleton/LBS path, and the 4 IT'IS STL phantoms all stay in the repo. The paper just uses one canonical track (STL for validation, SMPL‑X for the hero scenario) and ignores the rest for the JSAC submission. We can revive the GLB / Anny work later when it's not in the paper's critical path.

---

## 0. The honest summary

| | Status | One-line |
|---|---|---|
| Physics + monograph theorems (1, 2, 3, Prop 1) | ✅ done | Levels 0–8 implemented; Cauchy / ReLU / Fresnel / polarisation / curvature / diffraction all wired. |
| Coherent operator `Q = Jᵀ M J` | ✅ done | `coherent/exposure_operator.py` builds Q, eigendecomposes, returns ρ. ECBF QCQP solver is real (`coherent/ecbf.py`). |
| Multi-user MIMO + closed-form precoder | 🟨 mostly | `mimo/precoders.py` has MRT/ZF/MMSE/zf-exposure. The multi-body **(Q_tot + νI)⁻¹ g_k** form (eq. closedform) needs a 1–2 d port — the building blocks are all there. |
| Rank-CDF figure (`fig:rank-cdf`) | ✅ done | `JSAC/code/experiments/rank_check/`, both plaza-specular and 3GPP UMa-LOS. |
| GPU benchmark (7.5 / 66 / 378 ms) | ✅ done | `JSAC/code/experiments/gpu_benchmark/` (RTX 3090, decim10 variant). |
| Hero figure (compliance vs sum-rate Pareto) | ❌ TODO | Paper has literal `\TODO` and X/Y/R3/R5 placeholders at line 1010. **Single biggest piece of missing work.** |
| Plaza scenario assembly | 🟨 partial | OSM + 3D Tiles + DiffeRT + 91 3GPP presets exist. Brussels Grand Place geometry not yet pinned down as a reusable scene. |
| AMASS walk-cycle pose stream | ❌ TODO | No mocap loader on disk. Need ~50 walk-cycle SMPL-X trajectories at 30 Hz. |
| Virtual IMU (ICM-20948 noise) + Madgwick/VQF | ❌ TODO | Pure citation in current paper; trivial sensor-fusion port (~200 LOC). Or skip and cite only — paper says "cite, don't invent." |
| Tier-C ISAC RCS detection | 🟨 sketched | Asserted as "available" in §VI; no link-budget evaluation. Either model it minimally or retreat to occupancy-envelope framing. |
| CSI per-path calibration (§V.B) | ❌ TODO | Described; not implemented; not evaluated. Likely one figure showing residual error vs SNR. |
| Theorem 2 tightness | ❌ TODO | Cauchy rank-one bound `xᴴ Q x ≤ T₀(A_ab/4) D_max |aᴴx|²` — no figure showing how loose it is. One sweep would close this. |
| Chronic-dose integral §VII.E | ❌ TODO | Pure narrative in paper. Trivial post-processing of any 5-min run. |
| Phantom track | 🟨 pick one | See §3. **SMPL-X is the JSAC "standard human"; IT'IS STLs stay as the Mie validation set; the GLB/MakeHuman/Mixamo/Anny tracks remain in the repo, just not used by paper experiments.** |
| Viewer for paper experiments | 🟨 wrong tool | See §5. **Hero scenario runs headless (JAX + Modal), not through Flask.** Viewer's job for the paper is debugging + screenshots + demos. |

Traffic-light: ✅ done · 🟨 partial · ❌ todo.

---

## 1. The paper's demands, mapped to code

### §II — Body absorption physics

The Sab law, the Cauchy bound, posture insensitivity, and Theorem 2 are entirely covered by `kernels/level0_bound.py` … `level6_diffraction.py`, `geometry/directivity.py`, `tissue/`, and the monograph golden tests (`tests/golden/test_tables.py`). The 6.5% backflip number and SH-fit residual are lifted from the monograph; a regenerated paper-side figure would strengthen §II but isn't strictly needed.

**What's missing:** a one-page numerical sanity figure showing **Theorem 2 tightness** — the rank-1 bound LHS/RHS ratio under (a) random precoders, (b) ECBF outputs, on Thelonious. If the bound is loose by 6 dB on average, tier-C/D bystanders pay a 6 dB capacity tax, and that needs to be acknowledged honestly.

### §III — Coherent exposure operator

`Q = Jᵀ M J` lives in `coherent/exposure_operator.py`; `body_channel.py` already builds `G̃(r) ∈ ℂ^{M_tri × 3 × M_ant}` per Approximation 2 (depth coupling = 1, ≤0.44% at 28 GHz). The translation phasor identity `M(t) = Φ(t)ᴴ M(0) Φ(t)` is **not** yet implemented as a runtime caching shortcut — it's referenced as the trick that makes per-slot refresh cheap. Adding `Q.translate(Δt)` is one of the actual code asks (P1, §4 below).

### §IV — Multi-body exposure-constrained precoder

The level-8 single-body ECBF (`coherent/ecbf.py`) is the rank-one degenerate case of the multi-body form. The paper's `(Q_tot + νI)⁻¹ g_k` requires summing per-body Q operators with per-body Lagrangian multipliers and bisecting on ν over the joint feasibility set. This is the **actual algorithmic contribution of the paper** and **does not exist in the codebase yet**. Estimated effort: 1–2 days, including KKT bisection, soft-budget formulation, and warm-start from MRT.

Files to add/extend:
- `src/aegis/coherent/multibody_ecbf.py` *(new)* — the joint solver.
- `src/aegis/mimo/precoders.py` — add `multibody_ecbf()` constructor on `Precoder`.

### §V — Scene as ray-traced path dictionary

The path dictionary `D = {(k̂, k̂_T, ψ, α, j(n))}` is **functionally** what `PropagationPaths` already carries. What's missing is the **persistence + lookup-and-update** plumbing: a per-cell static dictionary, plus the per-slot CSI-to-α LS calibration described in §V.B.

Files to add:
- `src/aegis/twin/path_dictionary.py` *(new)* — load/save D, lookup by body position, calibration LS.

The DiffeRT bridge (`integration/differt.py`, plus `modal_rt/`) is what populates D in the first place. Modal-hosted T4 ray tracer is already wired.

### §VI — The closed loop

The cadence table `tab:cadence` (CSI 1 ms, precoder 1 ms, Φ(t) 1 s, pose 100 ms, RT seconds, calibration seconds) describes a **runtime loop that doesn't exist yet** — there's no scheduler in the codebase that ticks these refreshes at their native rates. For the paper we don't need a real scheduler; we need a 5-minute-of-wall-clock scripted run that *demonstrates* the cadence with mocked clock advancement.

The factored-Fresnel + vmap port that the paper claims gets 50 bodies under 100 ms is **also not yet done**. The benchmark shipped at 378 ms; the "with a 20-line port we hit 100 ms" claim is asserted, not measured. This is the second-most-load-bearing missing piece.

### §VII — Evaluation

The hero figure is the empty centre of the paper. Inputs: plaza geometry (OSM), 50 SMPL-X bodies on AMASS walk traces, 26 GHz 8×8 panel, 3GPP UMa-LOS channel preset, served sum-rate computed under MRT / ZF-to-users / WC back-off / proposed multi-body ECBF / oracle. Output: the compliance-violation × sum-rate Pareto.

The paper lays out the recipe; the codebase has every ingredient except the assembly. This is **the single experiment** the paper needs.

The chronic-dose §VII.E falls out of the same run for free — integrate `P_abs(t)` over the 5-minute trace per body, compare to GOLIAT thresholds.

The binding-distance table `tab:bind` is closed-form and already done.

### §VIII — Regulatory framing

ICNIRP 2020 is fully implemented in `compliance/`. Brussels arrêté + Italian DL are policy citations, not code. One agent-2 TODO (line 1218) on the Brussels 2024 update.

---

## 2. Coherent vs incoherent — what the paper actually needs each for

Robin's intuition that "coherent might only be worth it for hotspots" is **paper-supported by `tab:bind`**: at K = 25 served users, the Brussels RL stops binding past r* ≈ 2.7 m. Outside the close-range, low-load corner of the operating envelope, the chronic-dose narrative carries the value proposition, and the **chronic-dose narrative is fully incoherent**: it integrates ACS-only, ReLU-gated, Cauchy-bounded P_abs over time. Levels 0, 1, 2 alone deliver it.

The coherent regime earns its place in three places, and only three:

1. **Hero figure**: the compliance × sum-rate Pareto. Needs the multi-body ECBF (§IV) on Q operators, by definition coherent.
2. **Rank-3-4 claim**: needs the eigendecomposition of Q. Done.
3. **Translation phasor cheap refresh**: the "1-second dictionary, 100 ms phasor diagonal, 1 ms precoder solve" cadence story collapses without it.

Everything else — Cauchy bound, posture insensitivity, ACS evaluation, sub-6 GHz extension, ICNIRP averaging, psSAR-10g surface kernel — is incoherent. **The paper could plausibly demote coherent to one section if the hero figure shows the gap is small.** It doesn't have to, but it could.

For the codebase this means: keep the incoherent ladder pristine (it already is). The new code we write for the paper bolts on top of it — never replaces it.

---

## 3. Kernel speed: incoherent vs coherent

Short answer: **going coherent is strictly more expensive**, not faster. There is no algorithmic short-cut where adding phase awareness makes the kernel cheaper. Coherent's payoff is qualitative — it unlocks the class of problems (precoder design, hotspot prediction, exposure nulling) that incoherent kernels simply cannot express.

Concretely, per body:

| | Inputs per path | Per-triangle work | Per-body work | Order of magnitude on Thelonious (25 k tri) |
|---|---|---|---|---|
| **L0 bound** | 1 scalar `S_total` | none | O(1) | μs |
| **L1 aggregate** | `D(k̂_i)` per path | none (precomputed SH coeffs) | O(N_paths × L_SH²) | sub-ms |
| **L2 geometric** | `power, k̂` | `T₀ · ReLU(n·k̂) · s` | O(N_paths × N_tri) | a few ms |
| **L3–L6 spatial+** | + θ, q, H, σ | adds Fresnel/Stokes/curvature/GELU per tri | O(N_paths × N_tri) with bigger constant | ~10 ms |
| **L7 coherent** | full complex `ψ` ∈ ℂ^{M_ant} per path | builds `G̃ ∈ ℂ^{N_tri × 3 × M_ant}`, computes `‖G̃ x‖²` | O(N_paths × N_tri × M_ant) for Sab; O(N_tri × M_ant²) for Q | **66 ms/body** at M_ant=64, GPU benchmark |
| **L8 ECBF** | as L7 | as L7, plus eigendecompose Q (O(M_ant³)) and bisect Lagrangian | adds tens of ms for solve | ~80–100 ms/body |

The 7.5 ms/body number cited in the paper is L7/L8 on **decimated SMPL-X** (~2.4 k tri, 10× fewer triangles). At full Thelonious mesh you pay 66 ms/body. The coherent kernel scales with `M_ant` (per-element complex amplitudes per path × per-element entries in Q), whereas incoherent kernels scale only in `N_tri` and `N_paths`.

Where the wins actually come from inside the coherent stack:

- **Approximation 1 (cross-term drop, ≤4% error)** — keeps the Fresnel operator block-diagonal per path. Without it, off-diagonal `M_{nn'}` terms scale O(N_paths²).
- **Approximation 2 (depth coupling = 1, ≤0.44% at 28 GHz)** — eliminates the depth-attenuation integral. This is what makes `G̃` cheap to assemble.
- **Translation phasor identity** — once `M(0)` is computed, `M(t)` for a moved body is one diagonal phase multiplication, not a re-evaluation. This is the runtime cadence trick. **Not yet implemented.**
- **Factored Fresnel + vmap** — the asserted 50-body 100 ms claim. **Not yet measured.**

Where the incoherent stack wins on speed:

- **L1 aggregate** is ~10⁴× faster than L2/L7 (monograph §7.2) because it never touches per-triangle data. If you only need P_abs (not the surface heatmap), L1 is the tool.
- **L0/L1 are the right kernels for chronic-dose**, where you want millions of body-position combinations per region. The hero figure can use coherent; the 24-h chronic-dose CDF should use L1.

So if you have N_bodies bodies, M_ant antennas, N_tri triangles, and N_paths paths:

- Incoherent (L2): **O(N_bodies · N_tri · N_paths)**
- Coherent (L7): **O(N_bodies · N_tri · N_paths · M_ant)**
- ECBF (L8): **+ N_bodies · M_ant³ for eigendecomp + per-iteration solve**

There's a factor of `M_ant` between coherent and incoherent. At M_ant = 64, that's nearly two orders of magnitude. The 66 ms/body benchmark at full Thelonious is **slow enough** that the paper's 100 ms/50-body cadence claim depends on the factored-Fresnel + vmap port + translation phasor — both of which are still on the TODO list.

**Practical rule for the paper experiments:**
- Coherent only where the precoder design lives: §IV solver, §VII hero, §III rank claim.
- Incoherent everywhere else: §II Cauchy, §VII.E chronic-dose, §VII back-of-envelope sweeps, all the regression / golden tests.

---

## 4. The phantom question

Robin: *"the code alludes to there being more than 4 phantoms, and it looks quite good in code, but it is currently a messy buggy mess … I think just SMPL is fine, nothing more. The standard human for now."*

### What was actually attempted (the full ambition)

Reconstructed from the codebase:

1. **Two-track phantom system** — IT'IS STL (Thelonious / Duke / Eartha / Ella) **and** MakeHuman GLB (adult_male / adult_female / boy_6y / girl_8y). Both wired through the viewer with separate loaders.
2. **Animation library** — five named clips (idle, walking, phone left/right ear, sitting), driven from Mixamo FBX, retargeted onto MakeHuman base meshes. UI dropdown lets the user pick the clip.
3. **MakeHuman/MPFB2 parametric build pipeline** — `scripts/build_phantoms.py` drives Blender headlessly with macro sliders (gender, age, muscle, weight, height, race) to generate the 4 GLBs.
4. **Pure-procedural fallback** — `scripts/generate_phantoms.py` (828 LOC) builds capsule/sphere figures from ICRP reference dimensions. The on-disk GLBs are all suspiciously identical 3.69 MB, suggesting this is the path that actually ran.
5. **Live-posed dosimetry on glTF** — `geometry/skeleton.py` does FK + LBS to triangle soup; `AnimatedBody.tsx` POSTs the deformed mesh to `/api/compute` on every animation pause. Heatmaps re-render per-frame.
6. **SMPL-X parametric body** — `geometry/parametric.py` + `POST /api/parametric-body`. Plumbed but un-seeded (no model files at `~/.aegis/models/smplx/`).
7. **Anny (Naver Labs pediatric)** — explicit `NotImplementedError` placeholder. Documented as the planned under-18 complement.
8. **Limb / head-trunk segmentation** — `scripts/classify_limbs.py` produces per-face is_limb masks for ICNIRP region-specific averaging. Cached `.npz`.

### Current state

- IT'IS STL × 4 — works, used by Mie golden test and Thelonious validation.
- MakeHuman GLB × 4 — buggy. Sentry issues #389, #394, #444, #653 ("Body 'boy_6y' not found"), #381 (degenerate triangles), #482, #655. The fix at #656 hid the broken phantoms in the dropdown rather than fixing the pipeline.
- Animations — fragile; recompute fires on every pause toggle.
- SMPL-X — works on paper, no model files seeded, tests skip.
- Anny — `NotImplementedError`.

### Decision: pick SMPL-X for the paper, leave everything else where it sits

For the JSAC paper we use:
- **IT'IS STLs** — Mie golden test plus the rank-CDF and Thelonious validation experiments.
- **SMPL-X** — the 50-body plaza scenario. Ten-beta shape, AMASS walk-cycle pose stream.

The MakeHuman GLB pipeline, the procedural fallback, the Mixamo FBX assets, the Anny stub, the glTF FK/LBS path, and the live-posed `AnimatedBody` flow **all stay in place**. They're just not on the paper's critical path. The viewer dropdown keeps showing what works (per #656); the underlying pipelines remain in the repo to be revisited later. None of this is deleted.

What needs to happen to get SMPL-X actually usable:
- `pip install aegis[body]` (already declared in `pyproject.toml` extras: `smplx`, `torch`, `pygltflib`).
- Download SMPL-X model files (~200 MB, license-gated at smpl-x.is.tue.mpg.de) into `~/.aegis/models/smplx/`.
- `tests/test_parametric.py` should then unskip; `POST /api/parametric-body` should return real meshes.
- For the paper: write a tiny `ParametricBody.from_amass(npz_path)` adapter that consumes AMASS pose sequences.

Effort: half a day to seed + verify. The plumbing is already there.

---

## 5. The viewer's role for the paper push

The viewer is a phenomenal **debugging and figure-making** tool and a poor **batch-experiment** tool. For the JSAC paper, this means using each side for what it's good at.

### What the viewer is good for

- **Pre-flighting the plaza scene** visually — does the OSM Brussels Grand Place import look right? Are the buildings the right height, is the BS panel where I want it, do the bodies stand on the ground rather than float? Catching this in 3D for ten seconds saves an hour of debugging a headless run.
- **Sanity-checking heatmaps** on Thelonious or SMPL-X for representative single-body cases — the sort of figure that ends up as a teaser image or supplementary visualisation.
- **Capturing screenshots** for §III/§VII teasers, for the architecture diagram, for the appendix. The frontend already has html2canvas plumbing.
- **Demonstrating to non-experts** (Carolina, VLAIO, IDF reviewers) what the system actually does.
- **QA over feature flips** — does enabling polarisation correction change the heatmap visibly? Is the rank-CDF data actually loading?
- **Building intuition** for the paper while we're writing it — point at a body, see Q's eigenvalues update, see how `ρ` shifts when we change panel orientation.

### What the viewer is bad for

- **The hero scenario.** 50 bodies × 30 Hz pose × 5 minutes = ~9 000 frames × 50 bodies = 450 000 Q-refreshes. Per-request Flask round-trips, single-process JS↔Python hot loop, browser-side state — this is exactly the workload that wants a headless batch runner, not a UI.
- **Sweeps and sensitivity studies.** Pose-info-gain ablation, channel-preset sweeps, Theorem 2 tightness over 10 k random precoders — none of these belong behind a Flask endpoint.
- **HPC / GPU offload.** The Flask server runs the engine in-process; pushing computation onto Modal or onto a workstation GPU cleanly is awkward through the viewer. The codebase already has `modal_rt/` for the right way: detached jobs, explicit GPU types (T4 for DiffeRT, L4 for Sionna), result NPZ pulled back to the workstation.
- **Reproducibility.** A figure generated from a UI session is hard to regenerate. A figure generated from `python plaza_run.py --seed 42 --config plaza.toml` is trivially re-runnable.

### The split, concretely

```
JSAC paper experiments  →  headless scripts in JSAC/code/experiments/
                           ↓
                           call src/aegis/ engine + coherent + mimo directly
                           ↓
                           JAX backend, vmap across bodies
                           ↓
                           Modal-hosted GPU for ray tracing + heavy Q construction
                           ↓
                           save NPZ outputs
                           ↓
                           plot offline with matplotlib → PDF for paper

Viewer (Flask + React)  →  pre-flight scene visually
                           ↓
                           single-body heatmaps for figures
                           ↓
                           demos / screenshots / sanity checks
```

`JSAC/code/experiments/rank_check/` and `gpu_benchmark/` already follow this pattern. `plaza_run/` should too.

A useful side benefit: the viewer + headless workflows share the same `engine.compute()` and `coherent/` modules. Whatever optimisations land for the paper (factored-Fresnel + vmap, translation phasor caching) automatically improve the viewer's response time.

---

## 6. What's missing for the paper, in priority order

### P0 — paper cannot land without these
1. **Multi-body ECBF solver** (`coherent/multibody_ecbf.py`). The closed-form `(Q_tot + νI)⁻¹ g_k` with KKT bisection. 1–2 days.
2. **Plaza hero scenario assembled** as a runnable script (`JSAC/code/experiments/plaza_run/`). Brussels Grand Place from OSM, 8×8 panel on a facade, 50 SMPL-X bodies (25/15/10 across tiers), AMASS walk-cycles at 30 Hz, 5 minutes wall-clock, DiffeRT path tracing for D. ~2–3 days.
3. **Hero figure produced** — compliance violation rate × sum-rate Pareto under MRT / ZF / WC back-off / proposed / oracle. Falls out of (1) + (2). 1 day for figure-making.
4. **SMPL-X seeding** — install `aegis[body]` extra, download model files, verify `tests/test_parametric.py` passes. ~0.5 day. Blocks (2).
5. **AMASS walk-cycle ingest** — script that downloads ~50 walk traces, converts to SMPL-X pose sequences at 30 Hz, exports as `.npz`. ~1 day.

### P1 — the paper is honest with these in
6. **Theorem 2 tightness figure** — rank-1 Cauchy bound LHS/RHS ratio sweep on Thelonious. ~1 day.
7. **Chronic-dose integral plot** §VII.E. Falls out of (2). 0.5 day for figure-making.
8. **Translation phasor caching** — `Q.translate(Δt)` so per-slot refresh is one phase diagonal, not a re-eval. ~1 day. Validates the "real-time-in-silico" cadence claim.
9. **Factored-Fresnel + vmap port** — claimed <100 ms for 50 bodies. Currently 378 ms. Needs measuring. ~1 day.
10. **CSI per-path calibration LS + residual figure**. Described in §V.B; should have one residual-vs-SNR figure. ~1 day.

### P2 — could be deferred or replaced with citation
11. **ISAC RCS detection model for tier C** — currently asserted with no link-budget. Either model it (~1 day) or retreat to "occupancy-envelope" framing in §VI. The latter is cheaper.
12. **Virtual IMU + Madgwick/VQF** — paper says "cite, don't invent." Stay with the citation. No code needed.
13. **Pose-information gain** — needs running (1) twice, with and without tier-A/B pose telemetry. 0.5 day on top of (2).
14. **Brussels averaging-window verification** — the 6-min assumption (line 1059 TODO). Read the arrêté. 0.5 day, no code.

### P3 — deferred to follow-up paper
- Pose-differentiable Q (round-1 hero, archived).
- Löwner SDP (obsoleted by Cauchy).
- Pose-NN surrogate (killed in spine).
- Multi-operator Shapley.
- RIS-EMF compliance buyback.
- Closed-loop pose-SLAM / public pose privacy beacon.
- ISAC vital signs (downgraded to RCS-only in round 3).
- Skeleton-in-formalism (LBS-diff).
- GLB / MakeHuman / Anny phantom revival (the parts left dormant in §4).

**Total P0+P1 effort: ~12–14 working days**, single-thread. With the current code as base, the paper's 13-page hero is reachable in two focused weeks.

---

## 7. Long-term codebase structure

The current package layout is good. Don't refactor it for the paper. But the new paper-driven code shouldn't all sediment into top-level scripts either. Anticipating where things will eventually settle:

```
src/aegis/
  ├─ kernels/                 # ✅ exists — fidelity ladder, don't touch
  ├─ coherent/                # ✅ exists — Q, ECBF, body channel
  │   ├─ multibody_ecbf.py    # 🆕 add — joint multi-body QCQP
  │   ├─ translation.py       # 🆕 add — Φ(t) caching for cheap refresh
  │   └─ _fast.py             # 🆕 add — factored-Fresnel + vmap path
  ├─ twin/                    # 🆕 new subpackage — body twin abstraction
  │   ├─ body_twin.py         # one body's pose + Q + refresh-rate metadata
  │   ├─ path_dictionary.py   # static D (load/save/lookup), CSI calibration
  │   └─ scheduler.py         # cadence ticker for 5-min closed-loop runs
  ├─ sensing/                 # 🆕 new subpackage — ISAC tier-C detection (P2)
  │   └─ rcs.py               # monostatic link-budget + occupancy envelope
  ├─ mimo/                    # ✅ exists — extend precoders.py with multi-body
  ├─ geometry/                # ✅ exists — skeleton.py, parametric.py stay; add AMASS adapter
  ├─ basestation/             # ✅ exists
  ├─ environment/             # ✅ exists
  ├─ compliance/              # ✅ exists
  ├─ viewer/                  # ✅ exists — keep all existing routes incl GLB
  └─ ...

JSAC/code/experiments/    # one-off paper scripts, hash-pinned
  ├─ rank_check/              # ✅ done
  ├─ gpu_benchmark/           # ✅ done
  ├─ plaza_run/               # 🆕 the hero scenario
  ├─ cauchy_tightness/        # 🆕 Theorem 2 figure
  └─ csi_calibration/         # 🆕 §V.B residual figure

data/
  ├─ phantoms.yaml            # untouched — keeps all 8
  ├─ scenes/
  │   └─ brussels_grand_place/   # 🆕 OSM-derived plaza scene
  └─ poses/                   # 🆕 AMASS walk-cycles as SMPL-X .npz
```

**Three new subpackages, all additive**: `twin/` (load-bearing — owns body-side state: pose, Q, refresh metadata, calibration), `sensing/` (small, optional, may not survive if tier-C uses an envelope only), and `coherent/_fast.py` (private, an optimisation path).

Hack-script vs codebase rule of thumb: anything that sweeps a parameter once for one figure goes in `JSAC/code/experiments/`. Anything that other code might call goes in `src/aegis/`. Don't put plaza-specific constants in `src/aegis/`.

### Things to sunset later (NOT during the JSAC push)

The GLB phantom track, Mixamo animations, procedural fallback, and Anny stub will eventually want either a proper revival or a deliberate retirement — but **after the paper ships**, not before. Touching them now risks regressions in production (the viewer is live at `waves-ugent.be`) for no paper-side benefit.

---

## 8. Open theoretical risks the paper still carries

Quoted from `ARCHEOLOGY.md`'s "still unsettled" list, with code-side actionability:

| Risk | Code can speak to it? |
|---|---|
| Does Brussels RL bind under MRT/ZF at 26 GHz on this geometry? | **Yes — the hero figure answers this directly.** If MRT violates ≥ 10 % the paper writes itself; if < 1 % we lean on chronic-dose. |
| Pose-information gain — 0.5 dB or 3–5 dB? | Yes — run hero twice (tier A/B with vs without pose telemetry). |
| ISAC RCS at plaza range | No, link budget is back-of-envelope. Decide: model it (~1 day) or retreat to envelope. |
| `q_complement` 5% eigenvector locking on Thelonious | Yes — one Q + Q_re computation, eigenvector overlap. ~0.5 day. Optional. |
| Brussels averaging window | No, regulatory text reading. |
| Italian 15 V/m current status | No, regulatory text reading. |

The paper's value hinges almost entirely on the first row.

---

## 9. Suggested working order

1. **SMPL-X seeding** (0.5 d) — install `aegis[body]`, download model files, verify the existing parametric route returns real meshes.
2. **Multi-body ECBF solver** (1–2 d) — the algorithmic contribution of §IV must exist before §VII can be evaluated.
3. **AMASS pose ingest** (1 d) — gives plaza_run real walk traces.
4. **Plaza hero scenario assembled** (2–3 d) — Brussels OSM + DiffeRT + 50 SMPL-X bodies + AMASS walks + Sionna PHY-light. Use the viewer to visually pre-flight the scene before going headless.
5. **Run hero + chronic-dose** (1 d) — the two paper figures + numbers for `tab:cadence`.
6. **Theorem 2 tightness, CSI calibration residual, pose-info-gain ablation** (~2 d together).
7. **Factored-Fresnel + vmap measurement** (1 d) — close the cadence loop honestly.
8. **Translation phasor caching** (1 d) — only if step 7 shows we need it for 100 ms target.
9. **Paper rewrite** — fill in the four `\TODO`s, rewrite §VII.D around real numbers, decide whether coherent stays load-bearing or gets demoted to one section depending on what the hero shows.

Stretch / decide later: ISAC RCS model. If hero shows tier-C bystanders rarely matter (binding distance < 5 m at K ≥ 10), retreat to envelope and skip the model.

---

## 10. What this roadmap is NOT

- A spec for the multi-body solver — that lives in §IV of the paper and should be re-derived from the monograph + `system_formalism.tex` when we sit down to write `multibody_ecbf.py`.
- A re-architecture of AEGIS — the code is in good shape (21 k LOC, zero TODOs, 154 tests, levels 0–8 all real, ECBF QCQP fully worked).
- A schedule with dates — durations are best-effort estimates assuming single-threaded effort and no plaza-OSM-import yak shaves.
- A removal plan — nothing is deleted. The GLB / Mixamo / Anny / glTF-skeleton tracks all stay; the JSAC paper just doesn't use them.
