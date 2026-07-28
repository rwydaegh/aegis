# City exposure study: what happened, and where to pick it up

Written 2026-07-27, reconstructed from the recovered session transcripts, the git
log, and the design docs. The study was built in a single stretch (2026-05-30
evening to 2026-06-01 08:42) and has not been touched since.

## The idea, in Robin's words

From the opening message of the design session (2026-05-30 21:17):

> ...we want to be able to have a human being (which later on will become multiple
> versions of humans) but for now let's keep it simple. We want to create this
> whole module and have several human beings walk around in some city with some
> amount of antennas radiating in the city onto the users. The idea is we're going
> to make a paper out of this where the paper really is only about a shit ton of
> results. Humans walk around a city, they get exposed, and we make a glorified
> CDF out of that.

And where the name came from:

> let's brand this whole idea as 10 cities. Don't brand it in the code like that
> but let's just call it that because this is how my promoter, very vaguely, told
> it to me: "Oh Rob, just take 10 cities and compute the exposure there." ... The
> kind of follow-up on that is what he said is he wanted to compare the
> deterministic channel model with the stochastic channel model.

## Timeline

### 30 May, 20:59 to 22:24. Framing

Brainstorming skill, high-level only. Robin threw in an LLM curveball at 21:46
(use an off-the-shelf model to "improve" the government antenna datasets so they
are "imagined to be realistic"), put it in the freezer three minutes later, and
killed it at 22:24: "let us drop LLM entirely but do think about how to generate
deployments effectively. in some way, it has to be realistic, in some way it has
to be future-looking. mmWave and (Ma)MIMO 6G kinda scenario". That is the
provenance of the "parked: LLM/generative dataset enrichment" line in the spec.

At this point the ABM was undefined beyond "how we walk from A to B".

### 31 May, 16:57 to 23:12. Design, then the whole build

The scope-down that set the tone (16:57): "let's come to the realization right now
that I kind of want to do something from a design perspective that is relatively
easy. I've decided that I want to be less ambitious and I want to be kind of more
normal. I still want everything."

The calls Robin made, and what each produced:

| When | What Robin said | What it produced |
|---|---|---|
| 17:10 | Handed a GitHub PAT for `pedestrian_flow_ABM` and `hybrid-QuaDRiGa-FDTD`, asked whether to use blosm or AEGIS's own OSM builder, "do think about it carefully" | AEGIS-native OSM builder kept, blosm rejected as a runtime dependency |
| 18:03 | "it WOULD be cool if we can do it per slot... the 'framerate' so to speak is a free knob we can play with" | Recompute cadence became a first-class config knob (`temporal.*`) |
| 18:27 | "coherent source incoherent body is making your life difficult... it would kinda fly in the face of the paper no? Think honestly and critically about this" | **The physics reversal.** Coherent dosimetry throughout with a fixed MRT precoder, not incoherent levels |
| 18:35 | "none of those sources has sufficient code quality so we will NOT do DRY"; don't mirror the prior IEEE Access papers for symmetry ("oh lets do 3.5 GHz too cuz thats the same as that paper... no"); LOS/NLOS for the stochastic arm is "lowkey necessary" | Clean re-implementation, 28 GHz only, P_LOS-blended stochastic arm |
| 19:41 | "start smaller in area and population and time"; asked what a K=1 realization is; raised sectoring ("not every antenna serves the entire city") | 180 m radius, 24 agents, 30 s window, K=1; 3 sectors/site, ±60° wedge, 150 m range |
| 19:47 | "go" | Spec written, then the plan via the writing-plans skill |
| 20:14 | "2 do everything then go on" | Autonomous execution of all 16 tasks, PR #825 |
| 20:51 | "why are we doing differt vs sionna? ... differt is tough for big scenes tbh" | Deterministic arm switched to local Sionna RT, PR #826 |
| 22:15 | "how did you configure the ray tracer?" | **Found a real bug.** The Sionna bridge never set `scene.frequency`, so everything had been tracing at Sionna's 3.5 GHz default instead of 28 GHz (`bc59c0cf`) |
| 22:43 | "samples_per_src = 1_000_000 how do we know this is good?" | **Found a second one.** Convergence sweep showed 1M finds only half the paths; raised to the 30M plateau (`b6bcf264`) |
| 22:58 | "we dont necessarily want things to run 'live'. it is okay for a lower frame rate. remember the goal here is big picture" | Stopped optimizing for latency |
| 23:12 | Handed RunPod/vast.ai credentials, "lets start with a simple gpu" | Cost spike on a real Ghent mesh; GPU chunking (`ec1fab91`); finding that the consumer card loses to CPU 19x on the fp64 gram |

Both of those bugs were caught by Robin asking a plain question about a number,
not by a test.

### 1 June, 00:38 to 03:11. The goal, and the first batch

Robin asked what a good `/goal` would be (00:38), then wrote the terms himself
(00:43):

> this is a good goal but no need to be submitabble. it can just be a latex report
> with good figures mostly. also add that the agent has to validate what it is
> doing... try to hit the figure "10 cities" at all costs and if other parameters
> (there is a myriad of options) need to be sacrificed for that, so be it. I need
> 10 cities and a nice CDF type plot for sure.

That became `docs/superpowers/goals/2026-06-01-hpc-study-end-goal.md`. Goal set at
00:47, "go" at 01:02. Then: batch driver and cost knobs (01:34), report scaffold
(01:37), CDF overlay regenerated (03:11). The session ends there.

### 1 June, 07:22 to 08:42. The stretch with no transcript

Nine more commits landed: real Google Directions walks, study scene export to the
replay viewer with Sionna bounce rays, city and sites rendered in the replay
scene, log x-axis on the overlay, `p_los(d)`, `generate_coherent_channel`, the
det-vs-stoch comparison primitives, `compare_city`, and the real city mesh in the
viewer.

No conversation record exists for any of it. The last backup of the old box ran
2026-06-01 03:31 and the next one ran 2026-06-09, with the box migration in
between, so anything written in that window was never backed up. The code is the
only record.

### Then it stopped

No user message about the study after 01:02 on 1 June. On 8 June Robin resumed the
*other* session (Paper C) with "hey im resuming this convo a week later", and by
14:05 that session had pivoted entirely to the coherent exposure operator paper.
The city study was never argued down or cancelled. It was orphaned by a context
switch, eight hours into its only build session.

## What exists now

**Code**: `src/aegis/study/`, 2,436 lines across 18 modules. City meshing from OSM,
rooftop-candidate thinning into 3-sector sites, GHSL + Google Directions mobility,
SMPL-X posing, Sionna-RT deterministic channel, MRT precoding, Q-phasor exposure,
CDF reduction, top-down viz, replay export. Plus `compare.py`, the full
deterministic-vs-stochastic arm.

**Tests**: `tests/study/`, 1,224 lines across 20 files. Two currently fail
(`test_run_cities.py::test_run_cities_overlays_all`, `::test_run_cities_skips_failures`),
deterministically, on a missing LaTeX font package. See resume step 0.

**Frontend**: the internal Replay tab shipped (`aegis-web/src/components/panels/ReplayPanel.tsx`,
`src/components/scene/replay/`).

**Results**: `results/cities/ghent/` complete; `results/cities/manhattan/` has the
Mitsuba scene but no summary, so the batch died there. No `cities_summary.json`,
which means `make_report.py` cannot rebuild the table as things stand.

**Report**: `report.tex` builds, with one figure covering three cities (Amsterdam,
Ghent, Tokyo) at 24 pedestrians each.

## Gap to the stated goal

| Goal doc says | Reality |
|---|---|
| 10 cities | 3 |
| Paired scale-invariant det-vs-stoch error | `compare.py` exists and is tested, never run into the report |
| Cross-city spread explained by covariates | No covariate code at all |
| Clean CDF figure | Exists, 24-point staircase per city |

Plus the knobs the report itself admits: K=1, 24 agents, one static pose, and the
per-triangle peak-Sab map off, so there is no ICNIRP-fraction context.

## Where to pick it up

0. **Unblock the figure path.** `sudo apt install cm-super dvipng`. scienceplots
   sets `text.usetex: True` and this box lacks `type1ec.sty`, which is why two
   study tests fail and why `make_report.py` would crash at `savefig`. The June
   figure was made on the old box, which had the fonts.
1. **Run the batch.** `python -m aegis.study.run_cities --config configs/study/ten_cities.yaml --out results/cities`.
   README estimates 1 to 2 h on CPU. Manhattan is where it previously stopped, so
   watch it. Then `make_report.py --results results/cities` and pdflatex.
2. **Run the comparison.** `python -m aegis.study.compare` on at least one city.
   This is the piece the goal doc calls the reason the report exists, and it has
   never been executed.
3. **Covariates.** Site density, footprint density, LOS fraction per city, to
   explain the cross-city spread instead of a grand mean. Nothing written yet.
4. **Then raise knobs** (crowd size, K, pose) only if 1 to 3 land.

Two smaller fixes while you are in there: `report.tex:86` references
`tools/make_report_table.py`, which does not exist (it is `make_report.py`), and
`ten_cities.yaml` carries `channel.stochastic: coherent_38901`, which `run_cities`
never reads (only `compare.py` does), so the config reads as if the batch were
stochastic when it is not.

## Files

| Path | What |
|---|---|
| `docs/superpowers/specs/2026-05-31-hpc-city-exposure-study-design.md` | The design, 216 lines. Locked decisions, normalization, defaults |
| `docs/superpowers/plans/2026-05-31-hpc-study-deterministic-spine.md` | Plan 1 of 5, 992 lines. Plans 2 to 5 were never written |
| `docs/superpowers/goals/2026-06-01-hpc-study-end-goal.md` | The goal in Robin's terms, 113 lines. Non-negotiables and guardrails |
| `configs/study/ten_cities.yaml` | The headline config. Cities come from `run_cities.DEFAULT_CITIES` |
| `src/aegis/study/run_cities.py` | Batch driver, `DEFAULT_CITIES` list |
| `src/aegis/study/compare.py` | Det-vs-stoch arm, unrun |
| `papers/city-exposure-study/report.tex` | The report |
| `papers/city-exposure-study/make_report.py` | Figure + table assembly from `cities_summary.json` |

## Session 4 (2026-07-28, overnight): audit, physics fixes, restart

An 8-auditor adversarial workflow over `src/aegis/study/` plus targeted
experiments found and fixed, in order of gravity (commits `6a753927..ff7aba4c`
on `feature/coherent-exposure-studio`):

- **Coherent bridge phase reference (foundational, beyond the study).** Sionna's
  `cir()` default bakes only first-arrival-relative phase into `a`, and psi was
  left referenced at the receiver while every coherent kernel phases at absolute
  world coordinates: a body far from the origin had its inter-path interference
  scrambled. Fixed with `normalize_delays=False` plus origin re-referencing (and
  the same re-reference in the DiffeRT bridge); two regression tests in
  `tests/test_sionna.py` pin the convention against analytic geometry. Every
  June coherent number predates this fix.
- **Array physics.** Steering and element patterns now act on the departure
  direction (`PropagationPaths.k_hat_tx`), not the arrival direction at the
  body, which was wrong for every bounced path. The patch element pattern was an
  unnormalized amplitude (peak 0 dBi): now energy-normalized to 9.0 dBi, so
  absolute exposure with patch panels was ~9 dB low.
- **Floating base stations (the sighting that started this).** Vertex-mean site
  XY landed outside 12/232 concave Ghent footprints (one June seed-42 site
  hovered over a street) at raw OSM tag heights (Belfort 95 m eligible). Sites
  now take an interior roof point snapped to the traced mesh, inside a
  realistic 8-45 m roof band, with a 2 m mount, 10 deg downtilt, and per-site
  azimuth offsets.
- **City meshes.** The OSM `height` tag is total height, but roofs were stacked
  on top of it (the Belfry traced at 190 m); relation/part tags were stripped by
  the Overpass query so Manhattan towers collapsed to 8 m defaults (verified
  fixed live: 94 parts, peaks at 227 m); there was no ground surface off the
  road ribbons (the 28 GHz street ground bounce simply did not exist), and
  pedestrian squares meshed as perimeter ribbons. All fixed in the builder.
- **Batch hardening.** Per-city OSM snapshot caching with mesh-hash-guarded
  scene exports, `--city` on the job-array entry, wired `user_fraction`,
  per-city seeds, failure recording + nonzero exit, unknown-config-key
  warnings, data paths independent of the cwd, a silent-sector guard for
  zero-channel users, and a rebuilt stochastic comparison arm (per-hypothesis
  MRT beams, capped grams: the uncapped NLOS gram was 5 GB and got SIGKILLed).

The June results were moved to `results/cities-june-prephysics`. Everything
after this point is computed with the corrected physics: cadences 5 s/5 s,
20 s windows, 3M samples, 10-path cap, real street routing.

## Conversation record

| Session | Span | What it is |
|---|---|---|
| `74aa577a-7617-498f-b90e-89180257845a` | 05-30 20:59 to 06-01 03:11 | **The study session.** Design, spec, plan, build, GPU spike, goal. 41 user messages, 15 subagents |
| `7339b93e-11e4-44ea-b892-4e257107a5c8` | 05-30 21:35 to 06-18 18:16 | Paper C, running concurrently. Contains the replay-tab work and the moment it noticed the study session editing the same tree |
| (none) | 06-01 07:22 to 08:42 | Lost with the old box, see above |

Resume the first with `claude --resume 74aa577a-7617-498f-b90e-89180257845a` from
`/home/user/aegis`. It was recovered from the Google Drive backup on 2026-07-27;
it had been absent from this box since the migration.
