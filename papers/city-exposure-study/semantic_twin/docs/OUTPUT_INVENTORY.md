# What outputs/ and data/ hold, and what to do with each part

This is an inventory, not a cleanup. Nothing was moved or deleted while writing
it. It answers, for every top level thing under `outputs/` (3.6 GB, about 3700
files) and `data/` (4.7 GB): what wrote it, what reads it, whether it can be
rebuilt and at what cost, and which illumination law it belongs to. It ends
with three lists: KEEP, ARCHIVE, DELETE.

Read `TANGLE.md` first if you have not. It explains why five method changes in
four days left this many piles of files behind. `docs/2026-08-03_161712_LAW_CHANGE.md`
is the authority on which computed numbers are stale.

## The two things that decide almost everything below

**Cost to reacquire.** `data/panoramas`, `data/tiles` and `data/tiles250` came
from Google Street View, Google 3D Tiles and Mapillary. `docs/2026-08-03_161501_CITIES.md`
records the real numbers: a Street View day is capped at 15,000 tile requests,
one panorama costs 128 to 512 tiles depending on the capture rig, and the study
already hit that wall twice during acquisition. Nothing here should ever be
deleted to save disk space. Everything computed from this data (meshes,
fishnet cuts, traced exposure numbers) costs only CPU or GPU time to rebuild,
as long as the panoramas and tiles that fed it are still on disk. They are, for
every site in the study.

**Which law and which estimator.** The study changed its illumination law
twice and its estimator once. `LAW_CHANGE.md` has two tables: a list of
results that do not depend on the shape of the illumination weight `Q_S` and
survive untouched (geometry, coverage, materials, isotropic numbers), and a
list that does depend on it and is stale (every `chi_rooftop` and
`chi_street_small_cell` number, every figure built from them). A file being
"stale" does not mean delete it. It means the number in it should not be
quoted until it is recomputed, and the file itself is often the only evidence
behind a forensic doc that explains exactly how stale it is and by how much.

## data/ (4.7 GB)

| Folder | Size | Files | What it is | Verdict |
|---|---|---|---|---|
| `panoramas/` | 3.5 GB | 42,034 | Street View and Mapillary imagery, segmentation, alignment, for eleven sites plus the Korenmarkt walk | KEEP, always |
| `tiles/` | 275 MB | 2,720 | Google 3D Tiles, 130 m radius pull, thirteen sites (includes the dropped Istanbul and the 340 m Korenmarkt extension) | KEEP, always |
| `tiles250/` | 373 MB | 4,040 | Google 3D Tiles, 250 m radius pull, eight sites | KEEP, always |
| `geometry/` | 538 MB | 81 | Meshes built from the two tile pulls above, ten crop radii for Korenmarkt alone | KEEP, cheap to rebuild if lost |
| `street_routes/` | 36 KB | 8 | Google Routes walking paths, cached per site | KEEP, trivial to refetch |

**`tiles/` and `tiles250/` are not the same pull at two radii you can throw one
away and keep the other.** `docs/2026-08-03_161501_CITIES.md` says the
downloader has no cross run cache, so the 250 m pull re-fetched the inner
130 m annulus rather than reusing it. That means the 250 m tiles are a superset
by area but not a byte identical superset, and the two builds serve different
jobs: the 130 m mesh is the scattering and semantics geometry every fishnet
cut is made from, and the 250 m mesh is the occlusion shell the published
250 m exposure numbers trace against. Keep both. Do not try to derive one from
the other.

Meshes in `geometry/` are cheap: about 50 seconds of Blender per site per
`CITIES.md`. Twenty of the eighty-one files are already tracked in git,
because they are the small ones (60 to 340 m crops at Korenmarkt, the 130 m
crop everywhere else) and the large `_250m_f64` files are excluded by
`.gitignore` on purpose, with a comment explaining why. This is already
correct and needs no change.

`toulouse_capitole` and `krakow_rynek` have geometry but no panorama folder.
Both sites were dropped for now (`CITIES.md`): Toulouse's crop centre sits on
the Capitole roof, Krakow's on the Cloth Hall roof. Their tiles are paid for
and worth keeping in case the anchor gets fixed later.

## outputs/ (3.6 GB, about 3700 files)

### The published number: outputs/exposure_korenmarkt/ (177 MB, 1927 files)

The name is misleading. This one flat folder holds every exposure sweep run
in the whole study, for all eleven cities, under every law and estimator
version that ever existed. It is not a results folder, it is a lab notebook.

`docs/2026-08-03_161442_DECISIONS.md` says this outright: **"Every earlier tag
is kept and none of them is the headline."** The folder is organised by a
prefix on the filename (the "tag"), not by subfolder. Reading through the
naming, the biggest groups are:

| Tag family | Size | Files | What it is | Status |
|---|---|---|---|---|
| `city250_L3_*` | 7.5 MB | 69 | The current headline: eleven sites, 80 standpoints each, three bounces, correct ground datum | Current, feeds `FIGURES/16_eleven_cities_exposure.png` |
| `city250_corrected_*` | 7.4 MB | 69 | The headline until 3 August. Proven to hold torn records (two sweeps wrote into it at once) and two sites standing on a rooftop instead of the pavement | Superseded by `city250_L3`, kept as the audited record of the bug |
| `city250_repair_*` | 2.6 MB | 24 | Two sites repaired from the torn files above, plus two controls | Evidence for `RERUNS.md`'s repair claim |
| `city250_datum_*` | 7.5 MB | 69 | Rerun used to verify the ground datum fix and the paper's Monte Carlo error numbers | Evidence for `RERUNS.md` |
| `city250_rebuildb3_*` | 6.2 MB | 56 | An intermediate rebuild attempt, referenced by `SENSITIVITY.md` | Kept as cited evidence |
| `city250` / `cities250` (plain) | 7.0 MB | 69 | An earlier 250 m sweep, before the `_corrected` tag existed | Superseded, kept as history |
| `city_` / `cities130` | 6.8 MB | 63 | The ten city sweep at 130 m, kept on purpose because comparing it to the 250 m run measures how much each city depends on geometry outside its own square | KEEP, cited by name in `EXPOSURE_NOTES.md` |
| `bandlaw_*` | 2.2 MB | 18 | Corrected law at Korenmarkt only, cited in four docs | KEEP |
| `ladder130_*` / `ladder250_*` | 99.6 MB | 984 | Four disjoint seed streams of the evidence ladder (figure 17's material null result), at both crop radii | KEEP, this is the uncertainty evidence behind a published +/- figure |
| `coverage_ladder_*` | 5.5 MB | 191 | An earlier generation of the same ladder sweep | KEEP, still read by `run_exposure.py` and a test |
| `sam3lad_*` | 8.3 MB | 54 | The SAM 3 fourth rung of the evidence ladder | KEEP, `SAM3_LADDER.md` |
| `clean_*` / `dirty_walk12` | 4.8 MB | 30 | Corrected-law counterparts of the single-site 120 location runs | KEEP, named individually in `DECISIONS.md` and `PAPER_METHODS.md` |
| `<site>_geometric` / `_semantic` / `_walk` | 7.3 MB | 54 | The original 130 m single-site runs those correct | KEEP |
| `golden_*` | 0.2 MB | 25 | Fixtures written by `pytest tests/golden`, declared in `tests/golden/cases.py` | KEEP, regenerates in about 3 minutes if lost |
| `blgpu_bench` / `nycheck` / `walkcheck` | 1.2 MB | 30 | GPU box smoke checks | Low value, see ARCHIVE list |
| `city250_blgpusmoke_*` | 2.2 MB | 63 | Another GPU box smoke check, no doc references it | Low value, see ARCHIVE list |
| `zz_probe*` / `zz_seed*` | 3.0 MB | 72 | No reference anywhere outside this folder | Low value, see ARCHIVE list |
| `pilot` | 0.1 MB | 3 | An early three-model pilot, referenced once in `REPORT.md` | KEEP |
| `exposure_*.json` singles | 12 KB | 5 | Validation, convergence, crop mechanism results named directly in `EXPOSURE_NOTES.md`'s own file table | KEEP |

The short version: almost everything in this folder is cited by name in at
least one doc, and several docs (`AGGREGATE_REBUILD.md`, `RERUNS.md`,
`DECISIONS.md`) are forensic write-ups that only make sense if the exact files
they quote line counts and byte offsets from are still there. Deleting the
`city250_corrected` files, for instance, would not free much space (7.4 MB)
and would break the audit trail that proves the current headline is right.
**Recommendation: keep the whole folder as is.** The only parts worth moving
out are the unreferenced smoke checks and probe runs, about 6.4 MB total,
covered in the ARCHIVE list below.

### City geometry and fishnet outputs (roughly 1.2 GB across eleven cities)

Every `<city>_fishnet_vistas` and `<city>_fishnet_vistas_250m` pair is written
by `build_site_fishnets.py`, which still exists and runs. These hold cut
geometry and a material class per face, not exposure numbers, so per
`LAW_CHANGE.md` they survive the law change entirely.

**The 250 m version does not replace the 130 m version.** They are read by
different things. `run_exposure.py`, the published driver, reads the
no-suffix 130 m version at every crop radius by design. `run_next_event.py`,
the new estimator, reads the 250 m version. Both are live. Keep both for
every city.

One exception: Tokyo Hachiko has three entries, and two of them are the same
8 KB failure record. `tokyo_hachiko_fishnet_vistas.stub_no_npz` is a duplicate
of `tokyo_hachiko_fishnet_vistas` (both record a 130 m build that admitted
zero panoramas). `PROPAGATION_BLENDS.md` explains the duplicate exists because
a copy was renamed out of the way on the GPU box. The code already treats it
as defused (`export_propagation_payload.py` skips it and says so). Delete the
`.stub_no_npz` copy, keep the other as the on-disk record that the 130 m
Hachiko build failed.

`outputs/fishnet_crop_validation/` (137 MB) is a three-way comparison of one
Korenmarkt panorama cut at different output widths. No script, doc, or figure
names it anywhere. It looks like a scratch comparison whose conclusion was
never written down. Because nothing points at it and I cannot rule out that
someone still wants that comparison, archive rather than delete.

### Korenmarkt materials, depth, and body outputs (roughly 330 MB)

This cluster (depth comparisons, SAM 3 projections, pixel projection sweeps,
mesh study, bystanders, antenna, material VLM) covers GPU inference results
from a rented A6000 box. A 5.9 GB backup of that box exists at
`../archive/blgpu_backup/`, and whether the box is still rented is not known
from this repo, so treat any GPU-only rerun as a real cost, not a free one.

Two clear pieces of noise:

- `korenmarkt_pixel_projection`, `_leaf60`, `_leaf100`, `_leaf120` (4.6 to
  4.7 MB each, 18.6 MB total). These are a crop-radius sweep of the
  now-superseded pixel projection path (fishnet cutting replaced it). Only
  `_leaf130` is cited anywhere, in `FISHNET.md`'s reduction table. The other
  four have zero references and the source meshes are still on disk for a
  cheap CPU rerun if ever needed again.
- `korenmarkt_texture_evidence_f32mesh` (7.5 MB), an alternate-precision twin
  of `korenmarkt_texture_evidence` with zero references anywhere, while the
  plain version is actively read by `render_showcase.py`.
- `bystander_study/scratch/crowd.ply` (48 MB) is an intermediate mesh,
  rebuildable in minutes from `korenmarkt_dynamic_bodies`, which stays.

Everything else in this cluster is either on the live published path
(`site_semantics`, read directly by `run_exposure.py`), tied to paper text
that still cites it (`antenna`, cited in `paper/PROVENANCE.md` four times),
or partly irreplaceable (`material_vlm`, whose raw model responses are 19 of
the 20 files tracked in git despite the folder being gitignored, because raw
API responses cannot be regenerated bit for bit even with a GPU). Keep those.

`korenmarkt_sam3_projection_inputs` and `korenmarkt_sam3_body_raw` have no
writer script left in this tree; they came off the GPU box directly. Archive
rather than delete, since a GPU rerun is a real but not free option, and
`korenmarkt_mesh` is the same case for the older projection path.

### The two showcase scenes and propagation_viz (1.7 GB)

This is where the real, uncontroversial waste is. **512 MB of it is Blender's
own `.blend1` auto-backup**, the save from one to twenty minutes before the
current one, sitting beside every `.blend` file:

- `showcase_korenmarkt/korenmarkt.blend1` and `showcase_milan_duomo/milan_duomo.blend1`: 341 MB combined.
- `propagation_viz/*.blend1` across the eleven sites: 171 MB combined.
- `propagation_viz/propagation_blends.zip`: 50 MB, a zip of two `.blend`
  files that already sit uncompressed in the same folder.

None of this is referenced anywhere. Delete all of it. The current `.blend`
files, `payload.npz`, and the rendered figure PNGs stay, and they are the
things `FIGURES/README.md` and `docs/BLGPU_INVENTORY.md` actually point at.

One caution before deleting the `propagation_viz` backups: three sites
(Krakow, Mexico City, Prague) have a `.blend1` that is newer and larger than
their `.blend`, which looks like an interrupted rebuild rather than a stale
save. Open those three before deleting, the other eight are safe.

`outputs/substreet_ablation/` keeps two small JSON results (its actual
finding, that spurious sub-street geometry moves the median by 0.026 dB and
nothing more) and two large culled mesh files (47 MB) that are one minute of
compute to rebuild and cited by nothing. Keep the JSON, delete the meshes.

`outputs/propagation_blends_rest/` is an empty folder, named nowhere. Delete.

### Small measurement directories (about 21 MB total)

`monostatic`, `cross_validation`, `diffraction_bound`, `mc_error`,
`station_calibration`, `masonry_grating`, `foliage_study`, `skyline`,
`skyline_function`. Every one of these is small, every one is cited by at
least one doc or one figure script (monostatic's visibility data feeds
figure 22, masonry feeds figures 8, 9, and 13, foliage feeds figure 12), and
several are the only surviving record of a measurement made under a law that
is being replaced. Keep all of them. There is nothing to gain by removing 21
MB and cutting a citation.

### Loose files and logs at the top of outputs/ (about 1.4 MB total)

The 18 `blgpu_*.log` files (962 KB combined, not 19, one of the paths in the
original count does not exist) are stdout captures pulled back from the
rented GPU box by `tools/blgpu.sh`, which still exists and still names its
logs this way. They are the only local record of which remote job produced
which output folder. Nothing reads them back programmatically. Same story for
the four other loose logs (`rerun_corrected_250.log`, `sensitivity_harvest.log`,
`build_site_fishnets.log`, `law_comparison.log`, 89 KB together).

None of these need to sit at the top of `outputs/`. Move all 22 into
`outputs/_logs/`. Nothing is lost, and the top level gets easier to read.

Everything else loose at the top (`evidence_coverage.json`,
`registration_sky_conflict.json` and `.csv`) is read live by
`run_exposure.py`, `export_propagation_payload.py`, or a test. Keep those
where they are.

### The 20 files tracked in git despite outputs/ being gitignored

`.gitignore` excludes `outputs/` entirely, but git only applies an ignore
rule to files that are not already tracked. These 20 were added to the
index (with `git add -f` or before the ignore rule existed) on purpose, and
git keeps tracking a file once it is tracked regardless of what the ignore
rule says later. That is standard git behaviour, not a bug, and needs no fix.

- 19 files under `outputs/material_vlm/`: the blind vision model prompts,
  batch plans, and raw JSONL responses behind `MATERIAL_VLM.md`. These are
  the one thing in this whole audit that truly cannot be regenerated, even
  with a GPU and the same crops, because they are recorded API responses.
- `outputs/next_event/escape_range_term.json`: the result of
  `archive/scripts/measure_escape_range_term.py`, the script that ruled out a missing range
  term as the reason the two estimators disagree. It is the only artefact of
  that specific negative result.

Both are correctly protected by being tracked. Leave them tracked.

## Does any output supersede another

Yes, and the clearest cases are all in the noise pile, not the science.

1. **Every `.blend1` file supersedes nothing, it is just an older save of the
   file next to it.** 512 MB across the two showcase scenes and
   `propagation_viz`. This is the single largest recoverable chunk in the
   whole audit.
2. **`propagation_blends.zip` duplicates two files that already exist
   unzipped in the same folder.** 50 MB.
3. **`city250_corrected_*` is provably superseded by `city250_L3_*`**, the
   current headline. `AGGREGATE_REBUILD.md` audited it line by line and found
   torn records from two sweeps writing into the same file at once, plus two
   sites standing on a rooftop instead of the pavement. This is the clearest
   science-level supersession in the repository. It is not deleted here,
   because the project's own decision record (`DECISIONS.md`) says explicitly
   that every earlier tag is kept on purpose, and two docs quote exact line
   numbers and byte fragments out of these exact files as forensic evidence.
   If disk space ever matters more than that audit trail, this is the file
   set to remove first, but that is a call for whoever owns the audit trail,
   not one to make in a disk-cleanup pass.
4. **`korenmarkt_pixel_projection` (plus its `_leaf60/100/120` siblings) is
   superseded by the fishnet cutting path.** `semantic_twin/fishnet.py`
   calls it "the previous projection path" in its own module docstring.
5. **`tokyo_hachiko_fishnet_vistas.stub_no_npz` duplicates
   `tokyo_hachiko_fishnet_vistas`**, both empty failure records of the same
   dead 130 m build.

What is not a supersession, despite looking like one: **figures 24 and 25
each have two files on disk** (`24_diffraction_bound.png` next to
`24_walk_route.png`, `25_bounce_budget.png` next to `25_walk_cities.png`).
`FIGURES/README.md` only documents the diffraction and bounce budget pair.
The walk pair comes from `docs/2026-08-04_103942_WALK.md`, dated a day after
the README was last touched, and describes genuinely different figures
(the capture-route walk drawings) that happen to have landed on the same
numbers. Both files in each pair are current and neither should be deleted.
This is a numbering collision that needs a rename, not a cleanup decision,
and it is flagged here rather than resolved because renaming touches the
paper's figure references too.

## KEEP

Everything not named in ARCHIVE or DELETE below. In practice that is nearly
all of `data/` (4.7 GB) and the great majority of `outputs/` (about 2.9 GB
once the two lists below are removed), including the entire
`outputs/exposure_korenmarkt/` lab notebook, every fishnet vistas pair, every
showcase and propagation_viz asset apart from its `.blend1`, and every small
measurement directory. Reasons are given inline above for each group; the
short version is that almost everything here is cited by name in a doc, a
figure script, a test, or `run_exposure.py` itself.

## ARCHIVE (move, do not delete)

| Item | Size | Why archive instead of keep in place or delete |
|---|---|---|
| `outputs/fishnet_crop_validation/` | 137 MB | Unreferenced anywhere, but looks like a real comparison whose finding was never written down |
| `outputs/korenmarkt_sam3_projection_inputs/` | 49 MB | No writer script left in this tree, came off the GPU box directly |
| `outputs/korenmarkt_sam3_body_raw/` | 6.6 MB | Same, GPU-only, checkpoint is a 2.3 GB download |
| `outputs/korenmarkt_mesh/` | 17 MB | Superseded projection path, cheap CPU rerun but still cited by two docs |
| `outputs/exposure_korenmarkt/` smoke and probe tags (`blgpu_bench*`, `blgpu_nycheck*`, `blgpu_walkcheck*`, `city250_blgpusmoke_*`, `cities250_blgpusmoke*`, `zz_probe*`, `zz_seed*`) | 6.4 MB | Zero references anywhere outside the folder itself, but small enough that deleting them saves nothing worth the risk of guessing wrong |
| 18 `blgpu_*.log` plus 4 loose top-level logs | 1.05 MB | Only local trace of which remote job produced which output, not read by anything programmatically, but worth keeping as provenance |

Total: about 217 MB moved, nothing lost.

## DELETE (regenerable and superseded, or pure noise)

| Item | Size | Why safe |
|---|---|---|
| `showcase_korenmarkt/korenmarkt.blend1`, `showcase_milan_duomo/milan_duomo.blend1` | 341 MB | Blender auto-backup, one save behind, referenced nowhere |
| `propagation_viz/*.blend1` (check Krakow, Mexico City, Prague first, see note above) | 171 MB | Same |
| `propagation_viz/propagation_blends.zip` | 50 MB | Exact duplicate of two files already unzipped in the same folder |
| `substreet_ablation/*_culled.ply` (two files) | 47 MB | Intermediate mesh, one minute to rebuild, the actual result JSON stays |
| `korenmarkt_pixel_projection/`, `_leaf60/`, `_leaf100/`, `_leaf120/` | 18.6 MB | Superseded projection path, zero references, source meshes still on disk |
| `korenmarkt_texture_evidence_f32mesh/` | 7.5 MB | Unreferenced twin of the file actually in use |
| `bystander_study/scratch/crowd.ply` | 48 MB | Intermediate, rebuildable in minutes from `korenmarkt_dynamic_bodies` |
| `tokyo_hachiko_fishnet_vistas.stub_no_npz/` | 8 KB | Duplicate of an already-defused failure record |
| `propagation_blends_rest/` | 4 KB | Empty, named nowhere |
| `cross_validation/tessellation/` | 0 | Empty subfolder |

Total: about 683 MB recovered, roughly a fifth of `outputs/`.

## Left unresolved on purpose

- **Whether `city250_corrected_*` should eventually be deleted.** It is
  provably wrong and provably superseded, but two docs use it as forensic
  evidence and the project's own decision record says to keep every tag.
  Flagged above, not decided.
- **The doubled figure 24 and figure 25.** Needs a rename across
  `FIGURES/README.md`, the two `make_*` scripts, and wherever the paper
  cites the figure numbers. Not a disk question.
- **`outputs/fishnet_crop_validation/`.** Placed in ARCHIVE rather than
  DELETE because nobody wrote down what it was for.
