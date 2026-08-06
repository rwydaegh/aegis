# What is in this directory, and where it went

Written 2026-08-03 as part of a tidy-up. Nothing was deleted. Files that looked
finished or unused were moved into `archive/`, not removed.

This directory holds three separate pieces of work that grew side by side. They
share a subject (radio exposure in city squares) and almost nothing else. Telling
them apart is the main thing this file is for.

## The tree now

```
papers/city-exposure-study/
├── README.md            map of the three arms
├── INVENTORY.md         this file
├── CLAUDE.md
├── semantic_twin/       live: eleven squares at 15 GHz, the current paper
│   ├── README.md
│   ├── docs/            41 working notes plus METHOD.tex, with an index
│   ├── paper/           paper.tex, si.tex, body.tex, methods.tex, slides.tex
│   ├── FIGURES/         numbered figures and the scripts that make them
│   ├── semantic_twin/   the installable package
│   ├── tests/           1009 tests
│   ├── config/ data/ lit/ outputs/ tools/
│   └── *.py             63 run scripts, left at the top on purpose
├── report/              finished: ten cities at 28 GHz, June
│   ├── README.md  OVERVIEW.md  CONVERSATION_2026-06-01.md
│   ├── report.tex
│   ├── make_report.py  make_scenario_figures.py
│   ├── ghent_3d.py  see_ghent.py  tag_coverage.py
│   └── figures/
├── hybrid_twin/         sister project, left exactly where it was
└── archive/             nothing deleted, see archive/README.md
    ├── blgpu_backup/    5.9 GB mirror of a rented GPU box
    ├── propagation_previews/
    ├── loose_images/
    ├── semantic_twin_loose/
    ├── third_party/
    └── propagation_blends.zip
```

Before, the top level held nine loose Python and LaTeX files, five loose
screenshots, two zips totalling 448 MB, a `figures/` directory, four LaTeX build
artifacts, three markdown files and the 5.9 GB backup, all mixed together with
the three project directories.

## The three arms

| Arm | Directory | State | What it is |
| --- | --- | --- | --- |
| Semantic twin | `semantic_twin/` | live, the current paper | Eleven photogrammetric city squares, panorama-driven surface semantics, and an adjoint SBR estimator. Builds `semantic_twin/paper/paper.tex` (21 pages). |
| Ten-city report | `report/` | finished, not touched since June | The older deterministic arm. Runs `aegis.study.run_cities` from the main AEGIS package, walks agents through ten cities at 28 GHz, and writes a short LaTeX report. |
| Hybrid twin | `hybrid_twin/` | mostly finished, small recent additions | The sister project. Google/Inhouse 3D tiles plus OSM, assembled in headless Blender, focused on Graslei in Ghent. |

### Does the semantic twin reuse anything from the hybrid twin?

No.

Evidence:

- No file under `semantic_twin/` imports anything from `hybrid_twin/`. The
  hybrid twin's package is `hybrid_twin/twin/`, and `grep -rn "import twin\|from twin"`
  finds no hit outside `hybrid_twin/` itself.
- No file under `semantic_twin/` mentions `hybrid_twin` in any path string.
  The word "hybrid" does appear in `semantic_twin/build_site_semantics.py` and
  `build_walk_twin.py`, but it is the name of a segmentation backend, not the
  other project.
- No file under `semantic_twin/` mentions Graslei, which is the hybrid twin's
  only site.
- The two projects have separate `data/` trees, separate configs, separate
  tests, and separate packages. Every path inside `hybrid_twin` is built from
  its own `__file__`.

They do share ideas and some file names. `hybrid_twin/download_inhouse_tiles.py`
and `semantic_twin/download_inhouse_tiles.py` are different files with the same
name, both fetching 3D tiles, written independently. Same for `route_inhouse.py`
and the `mapillary` modules. That is duplication, not reuse.

One caveat, and it is the reason `hybrid_twin/` was **not** moved into `archive/`:
it is not dead. Three of its files are new (2026-08-03) and are about Korenmarkt,
which is the semantic twin's main site:

- `hybrid_twin/trace_korenmarkt_sbr.py` (Sionna SBR trace of co-located dipoles at 3.5 GHz)
- `hybrid_twin/build_korenmarkt_sbr_blend.py` (bakes that into a Blender file)
- `hybrid_twin/data/korenmarkt_colocated_sbr.json`

These are self-contained inside `hybrid_twin/`. They read `hybrid_twin/scene_hybrid.blend`
and write `hybrid_twin/korenmarkt_colocated_dipole_sbr.blend`. So the hybrid twin
is being used as a picture-making workshop for the live study, even though no code
crosses between them.

Two further reasons to leave it alone are given under "What was deliberately left
alone" below.

## Top level, before and after

| Was | Is now | Why |
| --- | --- | --- |
| `README.md` | `report/README.md`, plus a new `README.md` | The old one described only the ten-city report arm. The new one maps all three arms. |
| `OVERVIEW.md` | `report/OVERVIEW.md` | A history of the ten-city arm. |
| `CONVERSATION_2026-06-01.md` | `report/CONVERSATION_2026-06-01.md` | Salvaged transcript of the same session. |
| `report.tex` | `report/report.tex` | The ten-city report. Moves with its `figures/`, so its relative paths still work. |
| `make_report.py` | `report/make_report.py` | Writes `figures/cities_cdf.pdf` and `figures/cities_table.tex`. Uses `Path(__file__).parent / "figures"`, so it moves with them. |
| `make_scenario_figures.py` | `report/make_scenario_figures.py` | Same pattern. |
| `ghent_3d.py` | `report/ghent_3d.py` | 3D render of the Ghent scene from `/home/user/aegis/results/cities/`. All its paths are absolute, so the move is free. |
| `see_ghent.py` | `report/see_ghent.py` | Same. |
| `tag_coverage.py` | `report/tag_coverage.py` | Asks Overpass how many buildings in each study city carry a real height tag. Imports `aegis.study.run_cities` by absolute path. |
| `figures/` | `report/figures/` | Generated output of the two `make_*` scripts, read by `report.tex`. Still ignored by git: the `figures/` pattern in `.gitignore` matches at any depth. |
| `a.png`, `aa.png`, `abc.png`, `network.png`, `Screenshot 2026-08-02 222854.png` | `archive/loose_images/` | Five screenshots and plots. Nothing in the tree references any of them by name. Described one by one in `archive/README.md`. |
| `propagation_blends.zip` (189 MB) | `archive/propagation_blends.zip` | Byte-identical duplicate (same md5) of `semantic_twin/propagation_blends.zip`, which is the copy the documents point at. |
| `The_City_Generator_2.6 1.zip` (259 MB) | `archive/third_party/` | A third-party Blender add-on. Not our output, not referenced anywhere. |
| `blgpu_backup/` (5.9 GB) | `archive/blgpu_backup/` | A read-only mirror of the rented GPU box, taken 2026-08-02. Contents untouched. Only the directory was renamed. See below. |
| `propagation_previews/` (31 MB) | `archive/propagation_previews/` | 28 preview frames for 4 of the 11 squares, rendered by `semantic_twin/propagation_blender.py`. Nothing reads the directory. Its `README.md` is a stray copy of the text that belongs inside `propagation_blends.zip`. |
| `CLAUDE.md`, `.gitignore`, `.claude/` | unchanged | Apply to the whole directory. |

### On `blgpu_backup/`

`semantic_twin/docs/BLGPU_INVENTORY.md` is the record of it: a 5.9 GB, 3,292 file copy
of a rented RTX A6000 box, taken before the box was given up. Nothing on the box
was deleted. Nothing in the tree reads a path inside the backup. The only two
files that mention it are `BLGPU_INVENTORY.md` itself and `semantic_twin/docs/CODE_AUDIT.md`,
which flags it as a working artefact sitting loose at the top level.

Moving it was a rename on the same filesystem. No bytes were read, written or
copied. The one line in `BLGPU_INVENTORY.md` that gave its old location was
updated. `semantic_twin/tools/blgpu.sh` and `tools/blgpu_reference.py` are the
tools that drove the box, not the backup, and they were not touched.

## Inside `semantic_twin/`

This is the live arm and the biggest pile: 63 Python files, 42 markdown notes,
plus configs, data, tests and a 3.0 GB `outputs/`.

### What moved

The 41 markdown notes other than `README.md` went into `semantic_twin/docs/`,
along with `METHOD.tex` and its build artifacts. `semantic_twin/docs/README.md`
is a new index that says what each note is and which ones are current.

Almost every reference between these notes is a bare file name in running text
("see `MONOSTATIC_SBR.md`"), which keeps working after a move. Exactly one place
in code held a real path, and it was updated:

- `summarise_evidence_coverage.py`, the `--into` default, was `SCRIPT_DIR / "COVERAGE.md"`
  and is now `SCRIPT_DIR / "docs" / "COVERAGE.md"`.

`semantic_twin/README.md` had its reading order repointed at `docs/`, and now
starts the reader at `SPINE.md` rather than at the superseded `PAPER_METHODS.md`.
No `.md` file was renamed, and no `.md` file anywhere in the tree used a relative
link of the form `[text](FILE.md)`, so nothing else needed touching.

Three loose files were archived:

| File | Where | Why |
| --- | --- | --- |
| `korenmarkt_remesh_comparison.blend1` (119 MB) | `archive/semantic_twin_loose/` | A Blender autosave with no matching `.blend`. Nothing references it. |
| `texput.log` | `archive/semantic_twin_loose/` | The log pdfTeX writes when it cannot find its input. From an aborted build. |
| `3570361.3613291.pdf` (16 MB) | `semantic_twin/lit/` | A cited MobiCom paper. `lit/` is where the other 67 downloaded papers live. `paper/CITATIONS.md` and `docs/PRIOR_ART.md` were updated to say where it now sits. |

### What did not move, and why

**The 63 Python files at `semantic_twin/`'s top level stay put.** This looks
untidy and it is, but moving them would break things in a quiet way:

1. The test suite imports twelve of them as plain modules
   (`from compare_mesh_depth import ...`, `import run_exposure`, and so on). That
   works because the suite is run with `python -m pytest` from `semantic_twin/`,
   which puts that directory on the import path. Move the scripts and all twelve
   imports break.
2. About 35 of them set `ROOT = Path(__file__).resolve().parent` or
   `SCRIPT_DIR = ...` and then build data paths from it: `ROOT / "outputs" / ...`,
   `ROOT / "config" / ...`, `ROOT / "data" / ...`. There are over a hundred such
   uses. Move the scripts one level down and every one of them points at a
   directory that does not exist, or worse, silently at the wrong one.
3. The same variable is also used for `sys.path.insert(0, SCRIPT_DIR)` so the
   script can `import semantic_twin`. That would need `parent.parent` instead.

That is well past "a handful of path strings", and a miss would show up as a
script writing results into the wrong place rather than as an error. Left alone
on purpose.

**`outputs/` (3.0 GB) stays put.** It is gitignored, and roughly 250 path strings
across the notes and scripts point into it.

**`data/` (4.2 GB) stays put.** Same reason. `data/panoramas/`, `data/tiles/`
and `data/tiles250/` are gitignored. `data/geometry/` is partly tracked.

**`FIGURES/` stays put.** `paper/paper.tex`, `paper/methods.tex` and `paper/body.tex`
all carry `\graphicspath{{../FIGURES/}}`, so it has to remain a sibling of `paper/`.

**`paper/`, `config/`, `tests/`, `tools/`, `lit/` stay put.** Already tidy.

**`semantic_twin/semantic_twin/` (the installable package) stays put.** Named by
`pyproject.toml`, imported by everything.

## What was deliberately left alone

- **`hybrid_twin/` was not moved into `archive/`.** Three reasons. It is not dead
  (see above). Its working tree has an unfinished rename in progress: two tracked
  files, `download_google_tiles.py` and `route_google.py`, are deleted on disk and
  two untracked replacements, `download_inhouse_tiles.py` and `route_inhouse.py`,
  sit beside them. Moving the directory in git would force a decision about those
  deletions that is not mine to make. And `hybrid_twin/data/twin/streetview_graslei.json`
  stores 96 absolute paths of the form
  `/home/user/aegis/papers/city-exposure-study/hybrid_twin/renders/...`, all of
  which would go stale. The directory is already self-contained and clearly named,
  so the gain would have been small.
- **The uncommitted changes across the tree were left uncommitted.** At the time
  of this tidy-up there were about 40 modified files and 15 untracked ones from
  other work in flight. Only files this tidy-up actually moved were staged.
- **`semantic_twin/.coverage`** and the `mesh_*.png` / `orbit_*.png` renders at the
  top of `semantic_twin/`. The orbit renders are read by `make_remesh_panel.py`,
  which uses a hard-coded absolute path, so moving them would need a code change
  for very little gain.

## Things that look wrong, found while looking

These were noticed during the survey. The first was fixed because it was one
character and it blocked a build. The rest were left as they are.

1. **`report.tex` did not build.** `make_report.py` wrote its table caption with
   one closing brace too many (`\caption{...}}`), so `pdflatex` stopped with
   "Extra }, or forgotten \endgroup" every time. Fixed in `make_report.py` and the
   generated `figures/cities_table.tex` was rebuilt by hand to match. `report.tex`
   now builds to 2 pages with no errors.
2. **`semantic_twin/bench_intersect.py` fails ruff** with `F401`, an unused
   `import drjit`. It is an untracked benchmark from work in progress, so it was
   left for its author. It is the only lint error in the directory.
3. **`docs/BLGPU_INVENTORY.md` said the backup was "outside the repo tree".** It was
   not. It sat inside `papers/city-exposure-study/`, merely untracked. The line was
   corrected along with the path.
4. **`propagation_previews/README.md` describes the wrong thing.** Its text is the
   index that `build_propagation_blends.py` writes into `propagation_blends.zip`,
   describing Blender files. The directory holds PNG frames. It was copied in.
   Left as found, now in `archive/`.
5. **The reading order in `semantic_twin/README.md` points at superseded notes.**
   `README.md` used to send the reader to `PAPER_METHODS.md`, whose own first lines say
   "SPINE.md is now the source of truth". `REPORT.md` carries more than twenty
   internal "superseded" marks. The current entry points are `SPINE.md` for the
   argument and `OVERNIGHT.md` for status. `docs/README.md` says so.
6. **`docs/AGGREGATE_REBUILD.md` states that `PAPER_METHODS.md` section 9.2 and
   `REPORT.md` still carry numbers the corrected pipeline replaced.** Not checked
   here, but worth checking before quoting either.
7. **Two duplicate 189 MB zips.** `propagation_blends.zip` existed at both the top
   level and inside `semantic_twin/`, byte for byte the same. The top-level copy is
   now in `archive/`.

## How to check nothing broke

```bash
cd /home/user/aegis/papers/city-exposure-study/semantic_twin
/home/user/aegis/.venv/bin/python -m pytest tests/ -q -p no:randomly    # 1009 passed, 2 skipped
/home/user/aegis/.venv/bin/ruff check .                                 # 1 pre-existing error, see above

cd paper && latexmk -pdf -interaction=nonstopmode paper.tex             # 21 pages, no undefined references

cd ../../report && latexmk -pdf -interaction=nonstopmode report.tex     # 2 pages
```

All four were run after every batch of moves. The counts above are what they gave
on 2026-08-03, and they match what they gave before any file was touched.
