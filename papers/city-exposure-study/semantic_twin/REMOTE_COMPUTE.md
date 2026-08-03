# Remote compute on blgpu

The local box is 4 vCPU and spends most of its life above load 30, so an exposure sweep there
runs at roughly half a core. `blgpu` is a rented 8 core Xeon with 31 GB and an RTX A6000, and it
sits idle. This document is how to move work onto it.

Nothing here needs the GPU. The adjoint SBR tracer is a Mitsuba `llvm_ad_rgb` and NumPy pipeline,
so what the box actually buys is eight uncontended cores. The A6000 is used by the segmentation
work another agent runs on the same machine, and both fit at once.

## The one thing to know

`tools/blgpu.sh` drives everything. The remote tree is mirrored at the **same absolute paths** as
the local one, `/home/user/aegis/...`, created with a `sudo mkdir /home/user` on the box. That is
deliberate: this study hard codes `/home/user/aegis/data/duke.stl` and
`/home/user/aegis/theory/scripts` in a dozen places, and mirroring the path means a command is
copy pasteable between the two machines with no rewriting and no environment variable.

```bash
cd papers/city-exposure-study/semantic_twin

tools/blgpu.sh sync                    # push code, config, meshes
JOB=$(tools/blgpu.sh run "python run_exposure.py --all-sites --locations 80")
tools/blgpu.sh status $JOB             # running, or the exit code
tools/blgpu.sh follow $JOB             # stream the log
tools/blgpu.sh wait   $JOB             # block, exit with the job's code
tools/blgpu.sh fetch  $JOB outputs/exposure_korenmarkt
```

`sync` first if you changed any code. It is a few seconds.

## Why a dropped connection does not matter

Each job gets a directory `/home/user/aegis/.blgpu_jobs/<id>/` on the box holding `cmd`, `pid`,
`log` and, once it is over, `rc`. The process is launched under `setsid nohup`, so it is detached
from the ssh session's process group: killing the client, losing the network, or the agent going
away leaves the job running. `status`, `log` and `fetch` are stateless reads of those files, so
you can come back to a job hours later from a different session.

`wait` polls for the `rc` file and treats a failed ssh probe as "not known yet" rather than as
"finished", so a network blip does not turn into a false completion.

## Commands

| Command | What it does |
| --- | --- |
| `sync` | rsync code, config, tests, meshes and the fused semantics to the box |
| `sync --all-meshes` | also push the six meshes the tracer refuses |
| `push PATH...` | push a heavier input the default sync leaves behind |
| `setup` | build the Python 3.12 venv and install both packages, idempotent |
| `doctor` | print the remote host, load, GPU and package versions |
| `run "CMD"` | start CMD detached, print the job id |
| `status [JOB]` | `running pid=N` or `finished rc=N`, defaults to the newest job |
| `log [JOB]` | tail the log, `BLGPU_TAIL=500` for more |
| `follow [JOB]` | stream the log until the job ends |
| `wait [JOB]` | block until it ends, exit with its code |
| `fetch [JOB] [SUBPATH ...]` | rsync results back, default `outputs/` |
| `jobs` | list jobs, newest first |
| `sh "CMD"` | one off foreground command in the remote venv |
| `verify [RAYS]` | prove the tracer still reproduces bit for bit |

`fetch` never passes `--delete`. The local `outputs/` tree is shared with about ten concurrent
agents and the box only ever holds the subset it produced itself.

## What gets copied, and what does not

| Copied | Size | Why |
| --- | --- | --- |
| `src/aegis` plus `pyproject.toml` | 50 MB | `propagation/exposure.py` and `propagation/bystanders.py` import `aegis.engine`, `aegis.geometry.mesh` and `aegis.tissue` |
| `data/duke.stl`, `data/itis_v5.db`, `data/phantoms.yaml` | 9.5 MB | the phantom and the IT'IS tissue database the body coupler opens |
| `theory/scripts/` | 1 MB | the shared matplotlib style the figure scripts import |
| the study's code, config and tests | 5 MB | |
| every mesh whose manifest declares `format_version >= 3`, and every mesh `.json` | 505 MB | the meshes `run_exposure.site_mesh` will accept |
| `data/panoramas/**/*.json` and `**/*.npz` | 309 MB | the fused semantics the material binding reads |
| `outputs/{walk_korenmarkt,site_semantics,material_vlm,cross_validation,antenna}`, data files only | 6 MB | inputs to the propagation stage that happen to live under `outputs/` |

| Skipped | Size | Why |
| --- | --- | --- |
| the rest of `outputs/` | 1.8 GB | the box produces these, it does not consume them |
| the rest of `data/panoramas/` | 2.7 GB | per view label rasters and source imagery, read only by the segmentation stage, which already ran |
| `data/tiles/`, `data/tiles250/` | 648 MB | Blender mesh building input, not propagation input |
| six meshes with `format_version < 3` | 34 MB | the tracer refuses them by manifest |
| `*.blend`, `*.png`, `*.pdf`, `*.zip`, `lit/` | ~250 MB | Blender scratch, renders and the literature stash |
| the rest of `/home/user/aegis/data` | 77 GB | unrelated studies |

The geometry filter deserves a note, because the obvious version of it is wrong. Filtering on the
`_f64` suffix looks like it selects the double precision meshes and it does not: New York and
Toulouse only ever got an unsuffixed build, and for every site except Korenmarkt and Milan that
unsuffixed build is already the good one. An `_f64` filter silently drops New York, and
`--all-sites` then reports `[skip] newyork_timessquare: no 250 m mesh` on the box but not locally.
`sync` therefore applies the same rule `site_mesh` does and reads `format_version` out of each
manifest. Six older Korenmarkt and Milan crops are all that is left behind, and those are exactly
the ones the tracer would refuse to open.

For heavier inputs that the default sync leaves behind, such as `outputs/bystander_study` at
24 MB or `outputs/substreet_ablation` at 47 MB, use `push`:

```bash
tools/blgpu.sh push outputs/bystander_study
```

## The environment

`setup` builds `/home/user/aegis/.venv` with uv on CPython 3.12.13, matching the local reference
environment exactly. The box's system Python is 3.10.12 and the repo declares `>=3.12`, so 3.10 is
not an option; uv supplies its own interpreter and nothing system wide is touched.

Versions are pinned rather than floated, because a bit level comparison against the local box is
only meaningful if the numeric stack is the same one:

```
python 3.12.13   numpy 2.4.6      scipy 1.17.1     mitsuba 3.8.0    drjit 1.3.1
trimesh 4.12.2   embreex 4.4.0    shapely 2.1.2    scikit-image 0.26.0
pillow 12.2.0    matplotlib 3.10.9
```

Two things that will bite anyone who bypasses `blgpu.sh` and sshes in by hand:

- **`/home/admin/semantic_twin` shadows the study package.** It is an unrelated 2 GB directory of
  UniDepth output from earlier work on the box. Because it sits in the home directory and carries
  no `__init__.py`, `import semantic_twin` from `~` picks it up as a namespace package and the
  real one never gets a look in. Every entry point in `blgpu.sh` exports
  `PYTHONPATH=/home/user/aegis/papers/city-exposure-study/semantic_twin` to make the import
  independent of the working directory.
- **`bash -lc` picks the wrong interpreter.** The login profile prepends `~/.local/bin`, which
  holds the uv managed `python3.12`, ahead of anything exported before it. The job wrapper uses
  plain `bash -c`.

The repo is synced without `.git`, so hatch-vcs cannot derive a version for the `aegis` package.
`setup` reads `aegis.__version__` out of the local venv and passes it through
`SETUPTOOLS_SCM_PRETEND_VERSION`, so `aegis.__version__` reads the same on both machines.
`SETUPTOOLS_SCM_PRETEND_VERSION_FOR_AEGIS`, which is what the build error message suggests, is
ignored by this build backend.

## Bit exact reproduction, checked

The tracer is claimed to be a pure function of its seed. That was tested rather than assumed, to
full float64 precision and not to a tolerance.

`tools/blgpu_reference.py` pins the mesh, the three observation points, the three illumination
models, the material and the seed, then prints every susceptibility as a C99 hexadecimal float
literal, which round trips exactly, and every angular power spectrum as a sha256 over its raw
bytes. Run it on both machines and diff. `tools/blgpu.sh verify` does exactly that.

**Result, 2026-08-03, at 200,000 rays on `inhouse_leaf_130m_f64.ply`:** all 77 lines identical.
Every `chi`, every `chi_direct`, every derived scalar, and the sha256 of every `rho` array. The
only line that differs is the host name.

The same check with the remote process pinned to a single core with `taskset -c 0` is also
identical, so the result does not depend on the core count either. Both machines are Xeon Gold
6226, which is worth writing down: an LLVM JIT target with different vector widths is the one
thing that could plausibly have broken this, and it was not tested against because no such host
was available.

A fingerprint on three points is weak evidence on its own, so the full sweep was compared too.
The same 24 location, 200,000 ray, 250 m Korenmarkt run was executed on both machines and the two
output sets compared field by field:

- **936 float64 comparisons** across 24 JSONL rows, in hex float form, **zero mismatches**. That
  covers the tracer scalars and the AEGIS body coupling: `peak_sab_w_m2`, `mean_sab_w_m2`,
  `absorbed_power_w` and `sar_wb_w_kg` for all three illumination models.
- **All four arrays** in the spectra `.npz`, including the 24 by 512 `rho_rooftop` block,
  sha256 identical.
- **All 316 leaf values** of `summary.json` identical.

That sweep used `--materials geometric`, which does not touch the semantic binding, so the
`--materials walk` path was checked separately at 4 locations: **156 float64 comparisons, zero
mismatches**, and the `surface_binding`, `semantic_binding`, `class_area_fractions` and
`ground_datum` blocks of the manifest hash identically. That is the end to end check that the
synced panorama semantics are byte for byte the local ones and that the binding reads them the
same way.

So the box can be used for published numbers, not just for exploration.

## Speedup, measured

Same command, same seed, run at the same time on both machines. Local load average was 33 with
about ten agents competing.

| Work | Local (4 vCPU, load 33) | blgpu (8 cores, idle) | Speedup |
| --- | --- | --- | --- |
| 24 locations, 200k rays, 250 m Korenmarkt mesh | 310 s wall, 50 % of one CPU | 47 s wall | **6.6x** |
| per location trace | 4.2 to 5.4 s | 0.8 s | 5 to 7x |
| 3 point fingerprint, 200k rays, 130 m mesh | 13.3 s | 3.0 s | 4.4x |

The command was

```bash
python run_exposure.py --locations 24 --materials geometric --crop-m 250 --tag blgpu_bench --seed 7
```

Two cores' worth of hardware advantage does not explain 6.6x. Most of it is contention: the local
run got 50 % of a single CPU across five minutes, so it was effectively running on half a core.
The speedup is therefore a property of tonight's local load and will shrink when the box is quiet,
but tonight's local load is the condition that matters.

It cuts both ways, and by 00:10 it already had. A second agent started an 80 location eleven site
sweep on the box out of its own tree, the box went from load 0.0 to load 29, and per location
trace time went from 0.8 s to between 3.6 and 4.7 s. Check `doctor` before assuming the box is
free. Eight cores are still eight cores, but they are not eight cores each.

An eleven site sweep at 6 locations per site and a 250 m crop took 9 minutes end to end, including
loading and ground datum measurement for every site mesh.

The link between the two machines carries about 120 MB/s, so a full `sync` of 350 MB is roughly
three seconds and fetching a sweep's results back is instant. There is no reason to batch work to
avoid transfers.

## Working alongside the other agent

The box already carries a SAM 3 setup, four other venvs, three model checkouts and about 23 GB of
caches, all inventoried in `BLGPU_INVENTORY.md`. None of it was touched. This work added only:

- `/home/user` and everything under it, a new tree
- `/home/user/aegis/.venv`, a new venv
- `/home/user/aegis/.blgpu_jobs/`, the job records

There is now also a `~/bounce3` tree with its own venv, built independently by another agent for
the same study. Two checkouts of the same code on one box is wasteful but harmless, and neither
should touch the other. Anything reached through `blgpu.sh` lives under `/home/user/aegis`.

Disk is 157 GB free, so there is room. If the GPU is busy with segmentation that does not matter
here, since the tracer is CPU only, but do check `tools/blgpu.sh doctor` for load before starting
something large.
