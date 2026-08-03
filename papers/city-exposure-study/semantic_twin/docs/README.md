# The notes

Forty-one working notes plus one standalone writeup, moved here on 2026-08-03
from the top of `semantic_twin/`. No file was renamed, so every "see `SPINE.md`"
in the text still points at something you can find.

## Where to start

`SPINE.md` is the current source of truth for the argument and the numbers.
`OVERNIGHT.md` is the most recent dated status note and links the audit trail in
`../paper/`.

Two of the most-referenced notes are **not** current, despite what
`../README.md` says:

- `PAPER_METHODS.md` opens by saying "SPINE.md is now the source of truth". It is
  kept for the derivations it records.
- `REPORT.md` carries more than twenty internal "superseded" marks. Read it as
  history, not as a result.

`AGGREGATE_REBUILD.md` states that section 9.2 of `PAPER_METHODS.md` and parts of
`REPORT.md` still carry numbers the corrected pipeline replaced. Check before
quoting either.

## By kind

### The argument and the plan

| File | What it is |
| --- | --- |
| `SPINE.md` | The paper's argument, result by result, with an honesty ledger. The real source of truth. |
| `PROJECT_INTENT.md` | Why the project exists and what it is trying to show. |
| `DESIGN.md` | The pipeline design. Predates the 2026-08-02 illumination-law fix, which is outside its scope. |
| `ROADMAP.md` | Phase status. |
| `DECISIONS.md` | A running decision log. Marks its own old entries superseded. |
| `WHY_NOT.md` | Approaches considered and turned down. |

### Method

| File | What it is |
| --- | --- |
| `MONOSTATIC_SBR.md` | The foundational design document for the adjoint SBR estimator, and the largest file here. |
| `MONOSTATIC.md` | Builds the one module `MONOSTATIC_SBR.md` designed and declined to write, and answers its open question. |
| `DEPLOYMENT_GEOMETRY.md` | How the illumination models place sources. Its headline number is superseded twice inside the file; only the last value is good. |
| `FISHNET.md` | The standpoint sampling scheme. |
| `MASONRY.md` | Brickwork as a periodic scatterer. |
| `ROUGHNESS.md` | Surface roughness, and what the literature actually supports. |
| `FOLIAGE.md` | Vegetation attenuation. |
| `PAPER_METHODS.md` | Superseded by `SPINE.md`. Kept for the derivations. |
| `METHOD.tex` | A standalone eight-page writeup of the co-located transmitter argument, written for Robin. Builds with `latexmk -pdf METHOD.tex`. |

### Results

| File | What it is |
| --- | --- |
| `AGGREGATE_REBUILD.md` | What went wrong in the aggregate, and the rebuild. |
| `STATION_CALIBRATION.md` | Calibrating against measured station geometry. |
| `MATERIAL_REACH.md` | How far the material evidence reaches. Corrects a filename-parsing bug that had spoiled Prague's seed count. |
| `COVERAGE_LADDER.md` | The exposure shift each rung of evidence buys. |
| `BOUNCE_BUDGET.md` | How many bounces the estimator needs. Settles an earlier three-against-four disagreement. |
| `BEAMFORMING.md` | The beamforming arm. |
| `BYSTANDERS.md` | Other people in the square as absorbers and scatterers. |
| `SENSITIVITY.md` | Sensitivity study. Supersedes an older proxy in `DEPLOYMENT_GEOMETRY.md`. |
| `MATERIAL_VLM.md` | Reading facade materials with a vision model. |
| `SAM3_LADDER.md` | A segmentation ablation that came out null. |
| `CITIES.md` | Which squares were screened in and out. Ends in an open punch list. |
| `WALK.md` | The pedestrian walk. |
| `REPORT.md` | An overnight-run narrative. Heavily self-superseded, read as history. |

### Audits and reviews

| File | What it is |
| --- | --- |
| `CODE_AUDIT.md` | Code audit. Records a still-open crash in `steering_artefact` on an empty-surfaces scene. |
| `CROSS_VALIDATION.md` | Checked against Sionna RT. Note the 0.25 dB agreement excludes Sionna's specular branch, which the note finds wrong by a factor of 706 on tessellated surfaces. |
| `GROUND_DATUM.md` | A ground-height bug and its fix. Load-bearing, many notes depend on it. |
| `FLOW_REVIEW.md` | A review of `../paper/methods.tex`, pinned to one revision of it. |
| `RERUNS.md` | What was rerun and why. |
| `LIT_VERIFICATION.md` | Checking the literature claims. |
| `PRIOR_ART.md` | Prior-art review. Flags its own earlier numbers as not reproducible. |

### Running things

| File | What it is |
| --- | --- |
| `REMOTE_COMPUTE.md` | How the remote GPU work was driven. |
| `BLGPU_INVENTORY.md` | The record of the rented GPU box and its backup, now at `../../archive/blgpu_backup/`. |
| `PERFORMANCE.md` | Timings. |
| `PAYLOAD.md` | The exported propagation payload format. |
| `PROPAGATION_BLENDS.md` | The Blender walkthrough files. Rewrites earlier square summaries that were wrong. |
| `COVERAGE.md` | Panorama acquisition and registration status. `summarise_evidence_coverage.py` writes its table into this file. |

## Orphans

Nothing else in the tree links to `FOLIAGE.md`, `RERUNS.md`, `PROJECT_INTENT.md`,
`../paper/STYLE_PASS.md` or `../FIGURES/POLISH_NOTES.md`. They all look finished
and correct. They just never got linked.
