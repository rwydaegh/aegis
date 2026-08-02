# blgpu inventory and backup record

Audit of the rented GPU box (`ssh blgpu`, host `GPUcompute`, RTX A6000, Ubuntu 22.04) taken 2026-08-02.
Nothing was deleted or stopped. The box was read only.

Backup landed in `../blgpu_backup/` (sibling of this directory, outside the repo tree).
Total copied: **6,264,047,794 bytes (5.9 GiB) in 3,292 files**.
Local free space went from 26 GB to 20 GB, well clear of the 8 GB floor.

## Classification table

Sizes are as measured on the box. "Already local" means the same relative path exists under
`papers/city-exposure-study/semantic_twin/` with the same byte size, spot-checked by md5.

| Path on box | Size | Class | Verdict | Restore recipe if rebuildable |
| --- | --- | --- | --- | --- |
| `~/st` | 15 G | mixed | **partly backed up** to `blgpu_backup/st` (539 M) | 18,312 files (2.21 GB) are byte-identical to this repo. 12.0 GB of `data/panoramas/*/semantics/views/*.npy` skipped, see note below. Rest copied. |
| `~/.cache/uv` | 17 G | rebuildable | not copied | uv package cache. `uv` re-downloads on demand. |
| `~/.cache/huggingface` | 6.6 G | rebuildable | not copied, ids recorded | see model table below |
| `~/sam3` | 7.1 G | rebuildable | not copied | `git clone https://github.com/facebookresearch/sam3.git`, checkout `96914d2425f90a64f45ca977c2b5165418099543`. Size is mostly a nested `.venv/`. |
| `~/sam3-body-venv` | 4.4 G | rebuildable | not copied, freeze saved | `uv venv --python 3.11`, then install from `blgpu_backup/env/pipfreeze_sam3-body-venv.txt` |
| `~/st_work` | 3.9 G | unique | **partly backed up** (704 M) | fused results, configs, run scripts and logs copied. Per-view `.npy` intermediates copied for the two shipped runs only. |
| `~/sam3-venv` | 3.7 G | rebuildable | not copied, freeze saved | `uv venv --python 3.12`, then install from `blgpu_backup/env/pipfreeze_sam3-venv.txt` |
| `~/remeshqa` | 2.5 G | mixed | **backed up** (991 M) | meshes, remesh outputs, ray-cast reference depth, metrics and logs copied. Bundled Blender 4.5.3 (1.2 G) and `blender.tar.xz` (360 M) skipped as rebuildable. |
| `~/checkpoints` | 2.3 G | rebuildable | metadata only (84 K) | `hf download facebook/sam-3d-body-vith --local-dir ~/checkpoints/sam-3d-body-vith`, revision `f7f4ba4f67739e297f291639afb7c59041745367` |
| `~/semantic_twin` | 2.0 G | unique | **backed up** (2.0 G) | UniDepth and Depth-Anything raw inference output plus the two-view Mapillary refinement evidence |
| `~/blender-4.5` | 1.5 G | rebuildable | not copied | Blender 4.5.9 LTS, build commit dated 2026-04-20. Download from blender.org. |
| `~/altitude_probe` | 914 M | unique | **backed up** (914 M) | UniDepth depth and uncertainty fields for Korenmarkt and Milan at two camera altitudes |
| `~/showcase` | 803 M | mixed | **partly backed up** (131 M) | tiles, payloads, raw renders and code copied. The two `.blend` and `.blend1` files (703 M) skipped, see note. |
| `~/semantic_twin_bench.WFHv3m` | 512 M | unique | **backed up** (512 M) | timed benchmark of SAM 3 vs UniDepth vs Depth-Anything, with the repeat runs |
| `~/stenv` | 425 M | rebuildable | not copied, freeze saved | `python3.10 -m venv ~/stenv`, install from `blgpu_backup/env/pipfreeze_stenv.txt` (mitsuba 3.9.0, drjit 1.4.0, trimesh 5.0.0) |
| `~/st_body` | 121 M | unique | **backed up** (121 M) | SAM 3 body-layer segmentation and per-person meshes |
| `~/sam-3d-body` | 48 M | rebuildable | run outputs backed up (1.3 M) | `git clone https://github.com/facebookresearch/sam-3d-body.git`, checkout `b5c765a0d89d789985e186d396315e7590887b94`. Its untracked `outputs/` was copied. |
| `~/UniDepth` | 46 M | rebuildable | not copied | `git clone https://github.com/lpiccinelli-eth/UniDepth.git`, checkout `8d8cfe4c7ee15297099983607febf0d4f32eb3d6`. Working tree clean. |
| `~/meshviz` | 19 M | unique | **backed up** (19 M) | GPU orbit and mesh render scripts, camera basis, aligned pose, three case renders |
| `~/aegis-semantic-twin` | 10 M | unique | **backed up** (9.9 M) | earliest scratch checkout, holds a view set and three configs not in the repo |
| `~/stenv2` | 52 K | rebuildable | not copied | empty venv, zero packages installed. Dead. |
| loose `~/*.py`, `~/*.sh`, `~/*.log` | 84 K | unique | **backed up** (84 K) | six GPU cost probes, four report generators, the sweep and remote driver scripts, run logs |

## What was deliberately not copied, and why

Three skips account for almost all the bytes left behind. Each was checked rather than assumed.

**Panorama per-view `.npy` (12.0 GB in `~/st/data/panoramas`).** These are per-view Mask2Former
label and confidence rasters for Prague, Mexico City, Madrid and the Korenmarkt walk. They are
strictly upstream of the fused `semantics/panorama_semantics.npz` plus `semantics.json` plus the
three preview PNGs, and a per-city file-level diff confirmed every one of those fused products is
already in this repo byte for byte. What was genuinely missing was 32 MB of non-view files, mostly
`alignment250/` skyline-alignment output and `pose_aligned.json` for a 250 m alignment pass the
local tree never received. That 32 MB was copied.

**Per-view `.npy` for 13 of the 15 `st_work` ablation runs (3.4 GB).** Same argument. The
`panorama_semantics.npz` for all 15 runs was copied (157 MB total) and none of them existed
locally. To keep re-fusion possible without a GPU, the raw per-view arrays were also copied for
`korenmarkt_ship` and `milan_duomo_ship`, the two runs the scripts mark as shipped.

**Showcase `.blend` files (703 MB).** `outputs/showcase_korenmarkt/korenmarkt.blend` and
`outputs/showcase_milan_duomo/milan_duomo.blend` already exist locally at 152,600,139 and
204,393,933 bytes against 152,323,793 and 203,924,278 on the box, so the local copies are a later
build of the same scene. `payload.npz` is byte-identical on both sides, and the payload is the
scientific content. The scene rebuilds from payload plus tiles.

The two mesh QA PLY sets were kept even though they are technically derived, because regenerating
them means a Blender voxel remesh at 5 cm on a 40 m scene: `~/st/mesh_study` (524 MB, 29 PLYs) and
`~/remeshqa/out` (880 MB, 4 PLYs). Their generating commands are preserved in
`blgpu_backup/home_loose/blgpu_sweep.sh` and `blgpu_backup/remeshqa/fine.sh` if they ever need to
be reproduced instead.

## What the box was used for

Reading the driver scripts and run logs, the box did five jobs, all of which need a GPU.

1. **Panorama semantic segmentation at scale.** `remote_seg.sh` runs
   `semantic_twin.semantics --backend mask2former --device cuda --inference-size 1536
   --output-width 4096` over the 12 Korenmarkt walk panoramas, roughly 50 to 79 s each. The same
   module in `--backend hybrid` mode fuses Mask2Former with SAM 3 concept grounding. This is the
   single most GPU-bound stage in the pipeline.
2. **A 15-run segmentation ablation** in `~/st_work`, scripted as `run_v2.sh` through `run_v5.sh`
   plus `run_final.sh`, comparing dense Mask2Former against the hybrid backend across cache
   settings for Korenmarkt and Milan. `report.py`, `report2.py`, `report3.py` and `report_ship.py`
   turn each run into an ITU-R P.2040 material table.
3. **Monocular metric depth inference.** UniDepth V2 ViT-L/14 and Depth-Anything V2 Metric Outdoor
   Large over 26-view crop sets, in `~/semantic_twin`, `~/altitude_probe` and the timed benchmark
   `~/semantic_twin_bench.WFHv3m`. Measured cost: UniDepth 13.71 s for one crop and 37.40 s for 26,
   Depth-Anything 7.62 s and 28.37 s, SAM 3 24.01 s and 111.23 s.
4. **GPU cost characterisation.** The six `probe_*.py` scripts in the home directory measure SAM 3
   grounding cost against prompt count, where the 17.8 ms per prompt is spent across fusion encoder,
   decoder and mask head, whether batched grounding is possible, and, in
   `probe_unidepth_field.py`, a causal test of whether UniDepth's `confidence` output is really a
   confidence or a log error. `verify_backend.py` checks chunked batched grounding reproduces the
   one-prompt-at-a-time reference. These probes are the evidence behind the batching design and
   they are not reconstructible from the outputs alone.
5. **Mesh remesh QA.** `blgpu_sweep.sh` and `remeshqa/fine.sh` sweep Blender voxel remesh
   parameters over the in-house Korenmarkt mesh, then ray-cast the results against reference depth
   and score normal agreement and topology. This part is CPU-bound Blender work and does not need
   the A6000, only time and 5.4 GB of RSS.

Skyline alignment (`remote_align.sh`, 12 walk panoramas at 7-way parallelism, all rc=0) is CPU work
that happened to run there.

## Environment capture

Saved verbatim under `blgpu_backup/env/`:

- `_raw_capture.txt` holds `nvidia-smi` and `nvidia-smi -q`, `/etc/os-release`, `uname -a`, `lscpu`,
  `free -h`, Blender versions, git remotes and HEAD for every clone, cache layout, checkpoint file
  listing.
- `pipfreeze_stenv.txt`, `pipfreeze_stenv2.txt`, `pipfreeze_sam3-venv.txt`,
  `pipfreeze_sam3-body-venv.txt` hold the Python version, `pyvenv.cfg`, and every installed distribution
  as `name==version`. The venvs are uv-created and carry no `pip`, so the lists were read from
  `*.dist-info` directories, which gives the same information.
- `hf_models.txt` holds the HuggingFace snapshot ids and revision hashes.

Key facts for a future Dockerfile:

- Driver 580.126.20, CUDA 13.0, one RTX A6000 with 46,068 MiB. No `nvcc` installed, so everything
  ran on prebuilt wheels.
- Ubuntu 22.04.5, kernel 5.15.0-171-generic, 2 x Xeon Gold 6226 (8 vCPU), 31 GiB RAM, 3.9 GiB swap.
- System Python 3.10.12. uv 0.12.1 manages CPython 3.11.15 and 3.12.13.
- `stenv` Python 3.10.12 with mitsuba 3.9.0, drjit 1.4.0, trimesh 5.0.0, numpy 2.2.6.
- `sam3-venv` Python 3.12.13 with torch 2.10.0+cu128, transformers 4.57.6, numpy 2.5.1.
- `sam3-body-venv` Python 3.11.15 with torch 2.11.0+cu128, numpy 2.4.4.
- `stenv2` is empty and can be ignored.

Model revisions, all pinned:

| Model id | Revision | Cache size |
| --- | --- | --- |
| `facebook/sam3` | `3c879f39826c281e95690f02c7821c4de09afae7` | 3.3 G |
| `lpiccinelli/unidepth-v2-vitl14` | `52b349b514bd8b47642f67ac78cb7b5dc5c51dd9` | 1.4 G |
| `depth-anything/Depth-Anything-V2-Metric-Outdoor-Large-hf` | `4eab4cf1983c2801c515804005214de56a4b67cc` | 1.3 G |
| `facebook/mask2former-swin-large-mapillary-vistas-semantic` | `4772b6bf101d91f2534c106dc524d906aeb3c68a` | 826 M |
| `facebook/sam-3d-body-vith` | `f7f4ba4f67739e297f291639afb7c59041745367` | 2.3 G in `~/checkpoints` |

A HuggingFace token file exists at `~/.cache/huggingface/token` on the box. Its value was not read
and is not recorded anywhere. No other credential or `.env` file was found.

## Backup layout

| Directory in `../blgpu_backup/` | Size | Source |
| --- | --- | --- |
| `semantic_twin_box/` | 2.0 G | `~/semantic_twin` |
| `remeshqa/` | 991 M | `~/remeshqa` minus bundled Blender |
| `altitude_probe/` | 914 M | `~/altitude_probe` |
| `st_work/` | 704 M | `~/st_work` minus 13 runs of view intermediates |
| `st/` | 539 M | `~/st`, only what was absent locally |
| `semantic_twin_bench/` | 512 M | `~/semantic_twin_bench.WFHv3m` |
| `showcase/` | 131 M | `~/showcase` minus `.blend` |
| `st_body/` | 121 M | `~/st_body` |
| `meshviz/` | 19 M | `~/meshviz` |
| `aegis-semantic-twin/` | 9.9 M | `~/aegis-semantic-twin` |
| `manifests/` | 4.8 M | full remote and local file manifests used for the diff |
| `sam-3d-body_outputs/` | 1.3 M | untracked `outputs/` in the clone |
| `home_loose/` | 84 K | loose scripts, logs and shell rc files |
| `checkpoints_meta/` | 84 K | checkpoint config, README, licence |
| `env/` | 36 K | environment capture |

Integrity was checked by md5 on a ten-file sample spanning every backed-up directory and every
file type. All ten matched.

## Safe to delete

If the box is destroyed today, and only the backup survives, here is what is actually lost.

Nothing that carries a result. Every fused semantic map, depth field, mesh, metric table, figure and
log now exists either in this repo or in `../blgpu_backup/`. The environment is reconstructible
from pinned commits, pinned model revisions and per-venv package lists, and none of the four venvs,
three clones, two Blender installs or 23 GB of caches hold anything that is not re-downloadable.

What is lost is time, not information: about 12 GB of per-view Mask2Former label rasters for four
cities and 13 of the 15 ablation runs. Every one of those was already reduced to a fused
`panorama_semantics.npz` that has been kept, so they matter only if someone later wants to re-fuse
those specific panoramas under different fusion parameters without re-segmenting. Re-segmenting is
roughly 50 to 80 s per panorama on an A6000, so the whole set is a few hours of GPU rental to
regenerate, and the exact commands are preserved in `blgpu_backup/home_loose/remote_seg.sh`. The
only other loss is the two showcase `.blend` scenes, and those are superseded by newer copies
already sitting in `outputs/showcase_korenmarkt/` and `outputs/showcase_milan_duomo/`.

Delete when ready.
