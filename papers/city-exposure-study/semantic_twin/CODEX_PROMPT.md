# Paste this to Codex

You are taking over a large refactor in mid-flight. The previous session ran out
of account budget. Everything below is what the orchestrator knew and could not
finish writing into the code.

---

## What you are walking into

`/home/user/aegis/papers/city-exposure-study/semantic_twin` computes RF exposure
on pedestrians in city squares at 15 GHz using adjoint shoot-and-bounce ray
tracing. Rays leave a pedestrian's head, bounce up to three times off buildings,
and are credited on escape by an assumed angular base-station density. It is one
arm of a PhD paper by Robin, who is the only author.

The code grew for months under changing requirements and became tangled. A
refactor was run by an orchestrator directing nine subagents in parallel. Seven
finished. Three were stopped mid-flight when the budget ran out.

Nothing is committed. All of it is uncommitted work in the working tree.

**Read `HANDOFF.md` in that directory first. It is the authoritative status.**
Then `TANGLE.md` for history, `REFACTOR_PLAN.md` for the target shape,
`docs/BUGS.md` for the fourteen numbered defects.

Use `/home/user/aegis/.venv/bin/python` by absolute path. The shell has no
virtualenv on its path.

## Three rules that are not negotiable

**1. The golden lock.** `tests/golden/` pins 10,249 traced numbers at a relative
tolerance of 1e-12, captured before any code moved. The refactor must reproduce
them exactly. Do not change a float literal, an operation order, or a random draw
order. The tracer draws twice per ray plus once per bounce from a single stream,
so any reordering changes every number in the study. Never edit anything under
`tests/golden/`.

**2. Structure now, fixes later.** Do not fix any defect in `docs/BUGS.md`, even
one sitting in a file you are moving. Move it faithfully, bug intact. Each fix
lands afterwards as its own commit with its own before and after numbers, so its
effect on the paper stays legible instead of being buried in a rename.

**3. The checkout is shared.** Other sessions have run in this same tree. One
swept 49 renames into its own commit. One deleted a file from the worktree while
the git index held an older copy. Before any commit, run `git status` and
`git diff --cached`, and re-stage from the working tree rather than trusting the
index. Stage specific paths, never `git add -A`.

## Who owned what, and what state it is in

Nine agents. Each owned a disjoint set of files so they could not collide.

**Finished and verified.** Do not redo these.

| Area | Package | How it was proven |
|---|---|---|
| Spine: sites, paths, run identity | `sites.py` `paths.py` `runconfig.py` | 155 tests; run digests pinned to literal hex strings |
| Imagery acquisition | `acquire/` | 84 tests |
| Aggregation | `report/` | golden aggregation cases pass |
| Figures and Blender | `viz/` | golden fast case passes |
| Illumination laws | `illumination/` | bit-exact against `git show HEAD:` reconstructions |
| Walks | `walk/` | bit-exact, 80 cases across four functions |
| Image evidence | `vision/` | 288 tests |
| Physics invariant tests | `tests/test_invariant_*.py` | verified against 20 mutation trees |

**Stopped mid-flight.** Each was told to leave the tree importable and write its
own handoff. Read these before touching anything they owned:

- `docs/HANDOFF_MATERIALS.md` — owned `propagation/semantic_binding.py`,
  `propagation/scene.py`, `foliage.py`, and the masonry stack (`rcwa.py`,
  `kirchhoff.py`, `masonry.py`, `floquet.py`, `materials.py`).
- `docs/HANDOFF_SCENE.md` — owned `fishnet.py`, `support_mesh.py`,
  `semantic_twin/scene.py`, `geo.py`, `pano_geometry.py`, `mmwave.py`.
- `docs/HANDOFF_TRANSPORT.md` — owned `propagation/tracer.py`,
  `propagation/exposure.py`, `propagation/monostatic.py`,
  `propagation/sionna_check.py`.

**Check the transport handoff first and carefully.** That agent owned the tracer,
which draws the random numbers for the whole study. It was instructed that if it
could not prove bit-exactness it should revert rather than leave the move in
place. Confirm what it actually did before trusting any traced number. If its
handoff file does not exist, assume the move is unverified and check the tracer
against `git show HEAD:semantic_twin/propagation/tracer.py` yourself.

## Do this first

Find out where you actually are. Do not trust any document over a test run.

```
cd /home/user/aegis/papers/city-exposure-study/semantic_twin
/home/user/aegis/.venv/bin/python -m pytest tests/ -m "not slow" -q -p no:randomly
find tests/golden -type f | sort | xargs sha256sum   # 17 files, must be untouched
```

Expect roughly 27 xfail markers. They are deliberate: each pins one numbered
defect and is `strict=True`. **An unexpected pass is a warning, not a success.**
It means either someone fixed that defect or something moved that should not
have.

## Then, in this order

1. **Rewire the two drivers and delete the 31 shims.** This is the critical path.
   Because agents could not edit the same driver simultaneously, each left its old
   module path importable as a temporary re-export shim. Find them with
   `grep -rln "staging shim" --include="*.py" semantic_twin/`. `HANDOFF.md` has
   the exact driver line numbers and two decisions this pass must settle.

2. **Run the full golden suite.** It has not run since the agents started
   changing things, because they were fenced off it to stop them clobbering each
   other's output files. Until it passes, the refactor is unverified. This is the
   moment of truth.

3. **Commit.** Nothing has been committed yet.

4. Everything else is listed in `HANDOFF.md`.

## What the orchestrator would have done next

In this order, and the reasoning matters more than the list:

The driver rewiring first, because 31 shims are the only thing holding the tree
together and every further move gets harder while they exist. Then the full
golden run, because the entire refactor is unverified until it passes and finding
out late would be expensive. Then a commit, because five hours of work sitting
uncommitted in a shared checkout is the single largest risk right now.

Only after that, the remaining orphans: `propagation/bystanders.py` at 1,534
lines and `propagation/antenna.py` at 1,292. The standing instruction from Robin
is that the default for an orphan is to wire it back in, and to leave it out only
with a stated reason. `antenna.py` needs a conversation about invariance first.

The bug fixes come last, deliberately, and finding 2 must be settled before
finding 1 is re-measured because the two are coupled.

## Judgment calls already made, so you do not relitigate them

- The package keeps the name `semantic_twin`. Robin's decision.
- The 49 existing timestamped notes in `docs/` stay untouched as a historical
  record. A new lean docs set gets written separately. Robin's decision.
- `source_mesh` in the config files is acquisition provenance, not a mesh
  resolver. Every config names the unsuffixed build, which at Korenmarkt and
  Milan is the old-format mesh the version gate exists to refuse.
  `paths.site_mesh` is the single resolver.
- The fifth illumination law, `uniform_sites_pathloss`, was deleted rather than
  implemented. It had no instance anywhere and its formula spreads power in
  horizontal range instead of slant range, wrong by a factor of four at sixty
  degrees. An abandoned idea, not a missing feature.
- The atlas modules are kept, not archived. The plan had guessed the fishnet
  superseded them. It does not: the fishnet cuts geometry so a triangle carries
  one class, the atlas paints inside a triangle and leaves the mesh alone. They
  are alternatives.
- `tag` is out of the run identity. Three parameters that genuinely change the
  physics went in: `ray_epsilon_m`, `roulette_floor`, and `batch`.
- Every `inhouse` identifier in code is now `google`. The 80 mesh files on disk
  keep the old name for now because the golden fixtures pin runs that read them.

## How Robin wants to be worked with

- Full autonomy. He does not want to be asked for permission at each step. He
  wants the ambitious result, not the fast one.
- If you hit a tooling blocker (a missing API key, a site you cannot reach, a
  download you cannot do), stop and ask him rather than quietly taking a worse
  route. He can provide keys, run browser steps, install things.
- Writing style: short sentences, plain words, no invented jargon. He has said so
  explicitly and given examples of what he hates. Do not coin umbrella phrases.
  Replace vague references with hard numbers.
- Tests must be real. He would rather have no test than one asserting that a
  setter sets.
- Do not be a yes-man, and do not overcorrect into being a no-man. When you
  disagree, verify first and then say so plainly with evidence.

## The single most important scientific fact in this handoff

Finding 1 in `docs/BUGS.md` changes the paper's story, not just a number.

Next-event estimation discards 54 percent of the power reflected at the first
bounce and 73 percent at the second. It treats that power as specular and never
routes it anywhere. Crediting it closes 39 to 62 percent of the gap between the
study's two estimators. `NEXT_EVENT.md` currently attributes that entire gap to a
different cause, so about half of the written explanation is wrong.

Do not rewrite that explanation without talking to Robin. Fix the code, measure
the before and after, and put the numbers in front of him.
