# Rebuilding blgpu from scratch

Everything here was read off the live box on 2026-08-03. Nothing on it was changed, stopped or
deleted. Where a fact could not be established it says so instead of guessing.

## What the box is for

`blgpu` is a rented Linux machine that exists because the local development box is 4 vCPU and
usually sits above load 30, so an exposure sweep there runs at roughly half a core. The box gives
this study eight uncontended Xeon cores and an RTX A6000, and the whole city-exposure pipeline is
driven onto it by one script, `tools/blgpu.sh`. Two kinds of work run there. The propagation stage
is CPU work: the adjoint SBR tracer is a Mitsuba `llvm_ad_rgb` and float64 NumPy pipeline and never
touches the GPU. The evidence stage is GPU work: panorama segmentation with Mask2Former and SAM 3,
and monocular depth with UniDepth and Depth-Anything, which is what the A6000 was rented for. Both
fit on the machine at the same time.

## Provider and instance

The provider is **Blue Lobster**, not TensorDock. The `IdentityFile` in the ssh config is called
`tensordock_ed25519`, which is a leftover name from the machine that Blue Lobster replaced around
2026-06-01, and it misleads. Two independent things confirm the provider: the login banner at
`/etc/update-motd.d/01-blue-lobster` prints "Welcome to Blue Lobster Infrastructure", and the Blue
Lobster API lists this exact IP as one of the account's instances.

The API lives at `https://api.bluelobster.ai/api/v1` and authenticates with an `X-API-Key` header.
The key is named `BLUELOBSTER_API_KEY` and is read from `/home/user/goliat/.env` on the local
development box. Its value is not recorded here and must not be.

Instance record as the API returns it:

| Field | Value |
| --- | --- |
| name | `GPUcompute` |
| uuid | `c57916d1-3daf-4cc7-87ab-b821f1027322` |
| instance type | `v1_gpu_1x_a6000` |
| template | `UBUNTU-22-04-NV` ("Ubuntu 22.04 + NVIDIA") |
| region | Wilmington (Delaware, USA), host id `wil-gpu-26` |
| price | 55 cents per hour, so 13.20 USD per day and about 400 USD per 30 days |
| cpu / memory / storage | 8 vCPU, 32 GB, 250 GB |
| gpu | 1x RTX A6000 |
| vm username | `admin` |
| public IP | 38.29.145.154 |
| created | 2026-08-01T10:26:30Z |

The local development box is on the same provider and the same physical host: name `devpc`,
`v1_cpu_medium`, 4 vCPU, 16 GB, 6 cents per hour, IP 38.29.145.161.

**Unknown:** whether this instance was launched through the API or through the web dashboard. The
only launch script in the repositories, `/home/user/goliat/cloud_setup/my_deploy_bluelobster.py`,
targets a Windows GPU box for a different project, so it records the request shape but not the
choices made for this one. The rebuild section below gives the request shape and marks the parts
that are inferred from the running instance rather than from a script.

## Access

The ssh alias, copied from `~/.ssh/config` on the local box:

```
Host blgpu
    HostName 38.29.145.154
    Port 22
    User admin
    IdentityFile ~/.ssh/tensordock_ed25519
    StrictHostKeyChecking accept-new
    ServerAliveInterval 60
    ServerAliveCountMax 3
```

The private key is `/home/user/.ssh/tensordock_ed25519`, mode 600, 419 bytes. There is no `.pub`
file next to it, so to get the public half for a new instance run
`ssh-keygen -y -f ~/.ssh/tensordock_ed25519`. On the box, `/home/admin/.ssh/authorized_keys` holds
exactly one `ssh-ed25519` line. `sudo` for `admin` is passwordless.

The IP is a real public address with no port translation, so port 22 is port 22.

## Hardware and operating system, as measured

- GPU: one NVIDIA RTX A6000, **46,068 MiB VRAM**, driver **580.126.20**, `nvidia-smi` reports CUDA
  version 13.0. Persistence mode on, idling at 16 W of a 300 W cap.
- No CUDA toolkit. `nvcc` is not installed, `/usr/local/cuda*` does not exist, and `ldconfig -p`
  finds no cuDNN. Everything runs on prebuilt wheels that carry their own CUDA runtime.
- CPU: two Intel Xeon Gold 6226 at 2.70 GHz, 4 cores per socket, 1 thread per core, so **8 vCPU**
  across 2 NUMA nodes. AVX-512 present. The local box is the same CPU model, which is why the
  bit-for-bit comparison between the two machines is meaningful.
- Memory: **31 GiB** usable, 3.9 GiB swap.
- Disk: `/dev/sda2` is **245 GB**, 86 GB used, **150 GB free**.
- OS: **Ubuntu 22.04.5 LTS** (jammy), kernel **5.15.0-171-generic**, hostname `GPUcompute`.
- Virtualisation: QEMU under Proxmox. DMI reports vendor QEMU, product "Standard PC (Q35 + ICH9,
  2009)", BIOS "Proxmox distribution of EDK II". cloud-init used `DataSourceNoCloud` seeded from
  `/dev/sr0`, so there is no cloud metadata service to query from inside.

Two user accounts have a home directory. `toddl` (uid 1000) is a provider default and was never
touched. `admin` (uid 1001, gid 1002) is the account everything runs as, and it is in `sudo`,
`video` and `docker`-adjacent groups.

## Where the repository lives, and why

The tree is mirrored at the **same absolute paths as the local machine**, `/home/user/aegis/...`.
This is not a symlink and not a bind mount. `/home/user` is a plain directory owned by `admin:admin`
created with `sudo mkdir /home/user && sudo chown admin:admin /home/user`. The reason is that this
study hard codes paths such as `/home/user/aegis/data/duke.stl` and `/home/user/aegis/theory/scripts`
in about a dozen places, so mirroring the path makes any command copy-pasteable between the two
machines with no rewriting and no environment variable.

The consequence to remember: `$HOME` on the box is `/home/admin`, **not** `/home/user`. So
`~/aegis` does not exist there. Anything that resolves through `~` resolves inside `/home/admin`.
That happens to be right for Blender, which every script reaches as `~/blender-4.5/blender` and
which really does live at `/home/admin/blender-4.5/blender`. It would be wrong for anything that
assumes `~` is the repository parent.

## The contract between the local tree and the box

`tools/blgpu.sh` is the whole interface. Read it before changing anything here, because these rules
are encoded in it rather than in configuration.

Fixed paths inside the script:

```
LOCAL_REPO   /home/user/aegis
REMOTE_REPO  /home/user/aegis
STUDY_REL    papers/city-exposure-study/semantic_twin
JOBS_DIR     /home/user/aegis/.blgpu_jobs
VENV         /home/user/aegis/.venv
```

The host alias comes from `BLGPU_HOST`, defaulting to `blgpu`. Every ssh call goes through a
ControlMaster socket under `$TMPDIR/blgpu-ssh-$(id -u)` with `ControlPersist=120`, so repeated
calls are cheap and a dropped TCP session reconnects without re-authenticating.

### What `sync` pushes

| Copied | Size | Why |
| --- | --- | --- |
| `src/` (the `aegis` package), with `--delete` | 50 MB | the propagation code imports `aegis.engine`, `aegis.geometry.mesh` and `aegis.tissue` |
| `pyproject.toml`, `README.md` | 24 KB | needed for the editable install |
| `data/duke.stl`, `data/itis_v5.db`, `data/phantoms.yaml` | 9.5 MB | the phantom mesh and the IT'IS tissue database |
| `theory/scripts/` | 1 MB | the shared matplotlib style the figure scripts import |
| the study's code, config and tests | about 5 MB | |
| meshes under `data/geometry/` whose manifest declares `format_version >= 3`, plus every mesh `.json` | 538 MB local, 518 MB on the box | exactly the meshes `run_exposure.site_mesh` will accept |
| `data/panoramas/**/*.json` and `**/*.npz` | 325 MB | the fused semantics the material binding reads |
| data files under `outputs/{walk_korenmarkt,site_semantics,material_vlm,cross_validation,antenna}` | about 6 MB | inputs to the propagation stage that happen to sit under `outputs/` |

### What `sync` deliberately leaves behind

| Skipped | Size | Why |
| --- | --- | --- |
| the rest of `outputs/` | 3.9 GB locally | the box produces these, it does not consume them |
| everything under `data/panoramas/` that is not `.json` or `.npz` | 3.2 GB | source imagery and per-view rasters, read only by the segmentation stage |
| `data/tiles/` and `data/tiles250/` | 275 MB and 373 MB | Blender mesh-building input, not propagation input |
| six meshes with `format_version < 3` | 34 MB | the tracer refuses them by manifest |
| `*.blend`, `*.blend1`, `*.png`, `*.pdf`, `*.zip`, `lit/` | about 250 MB | Blender scratch, renders and the literature stash |
| `__pycache__/`, `.pytest_cache/`, `.ruff_cache/`, `.hypothesis/`, `.coverage`, `.blgpu_jobs/` | | scratch |
| the rest of `/home/user/aegis/data` | 77 GB | unrelated studies |

### The image evidence gap

**`sync` never pushes a single JPEG or PNG.** Step 4 of `cmd_sync` filters `data/panoramas/` down
to `--include '*.json' --include '*.npz' --exclude '*'`, and `sync_excludes` drops `*.png`
everywhere else. That is correct for the propagation stage, which only reads the fused
`semantics.json` and `panorama_semantics.npz`, but it means **2.77 GB of source panorama JPEGs in
40,972 files stay on the local machine**. Any stage that needs the picture rather than the fused
label array (re-segmentation, re-registration, a new alignment pass, a figure made from raw
imagery) will not find its input on the box.

There is no subcommand for this. Push it explicitly:

```bash
cd /home/user/aegis/papers/city-exposure-study/semantic_twin
rsync -a --info=stats1 \
  --include '*/' --include '*.jpg' --include '*.jpeg' --include '*.png' --exclude '*' \
  data/panoramas/ blgpu:/home/user/aegis/papers/city-exposure-study/semantic_twin/data/panoramas/
```

At the measured 120 MB/s link that is about 25 seconds of transfer for the whole set. For one city,
put the city directory in the source path.

`tools/blgpu.sh push PATH` exists for the other heavy inputs, such as `outputs/bystander_study`
(24 MB) or `outputs/substreet_ablation` (47 MB), but `push` on `data/panoramas` copies everything
including the tile pyramids, so the filtered rsync above is the better tool for imagery.

### How jobs run

`run "CMD"` writes a job directory at `/home/user/aegis/.blgpu_jobs/<id>/` holding `cmd`, `pid`,
`wrapper.sh`, `log` and, once the job ends, `rc`. The id is
`YYYYmmddTHHMMSS-xxxx` where the four hex digits stop two jobs launched in the same second from
overwriting each other. The command travels base64 encoded, because ssh flattens its argument list
and the remote shell splits it again. The wrapper is started with `setsid nohup`, so the job is
detached from the ssh session's process group and survives the connection dropping, the client
being killed and the agent going away. `status`, `log`, `follow`, `wait` and `fetch` are all
stateless reads of those files, so a job can be picked up hours later from a different session.
`wait` treats a failed ssh probe as "not known yet" rather than as "finished", so a network blip
cannot be read as a false completion.

The wrapper pins four things before running the command:

```
cd /home/user/aegis/papers/city-exposure-study/semantic_twin
PATH=/home/user/aegis/.venv/bin:$PATH
VIRTUAL_ENV=/home/user/aegis/.venv
PYTHONUNBUFFERED=1
PYTHONPATH=/home/user/aegis/papers/city-exposure-study/semantic_twin
```

There were 50 job directories on the box at the time of this audit and none of them were running.

`fetch` pulls `outputs/` back by default and **never passes `--delete`**, because the local
`outputs/` tree is shared with other work and the box only ever holds the subset it produced. If a
job id is given, its log lands at `outputs/blgpu_<job>.log`.

## Rebuild procedure

Follow these in order. Every command is the real one.

### 1. Provision the instance

Launch a `v1_gpu_1x_a6000` in region Wilmington from the `UBUNTU-22-04-NV` template with username
`admin` and the public half of `~/.ssh/tensordock_ed25519`. The request shape, taken from the one
launch script in the repositories:

```bash
cd /home/user/goliat
KEY=$(grep '^BLUELOBSTER_API_KEY=' .env | cut -d= -f2-)
PUB=$(ssh-keygen -y -f ~/.ssh/tensordock_ed25519)
curl -s -X POST https://api.bluelobster.ai/api/v1/instances/launch-instance \
  -H "X-API-Key: $KEY" -H 'Content-Type: application/json' \
  -d "$(python3 -c '
import json, os, sys
print(json.dumps({
  "region": "Wilmington",
  "instance_type": "v1_gpu_1x_a6000",
  "template_name": "UBUNTU-22-04-NV",
  "username": "admin",
  "ssh_key": sys.argv[1],
  "name": "GPUcompute",
}))' "$PUB")"
```

Two honest gaps. First, the field values for `region` and `template_name` are what the running
instance reports back, and the launch endpoint may want a short code instead. The Windows script
for a different project used `"region": "igl"` for the same Wilmington site, so if `"Wilmington"`
is rejected, try `"igl"`. Second, that script also passed a `password`, which the Windows template
needs for RDP. Whether the Ubuntu template needs one is unknown. If the call fails, use the web
dashboard and pick the same instance type, region, template and username, which is a supported path
and produces the same result.

List instances to find the new IP:

```bash
curl -s -H "X-API-Key: $KEY" https://api.bluelobster.ai/api/v1/instances
```

The per-instance cloud firewall on the current box is enabled with `policy_in` and `policy_out`
both `ACCEPT` and zero rules, which is the default and means nothing is blocked at the provider.
Check it on the new instance with
`curl -s -H "X-API-Key: $KEY" https://api.bluelobster.ai/api/v1/instances/<uuid>/firewall` and open
tcp/22 there if the default has changed.

### 2. Add the ssh alias locally

Append to `~/.ssh/config` on the local box, with the new IP:

```
Host blgpu
    HostName <new IP>
    Port 22
    User admin
    IdentityFile ~/.ssh/tensordock_ed25519
    StrictHostKeyChecking accept-new
    ServerAliveInterval 60
    ServerAliveCountMax 3
```

Then `ssh blgpu true` to confirm it works.

### 3. Confirm the driver, and skip the toolkit

The template ships the driver, so there is nothing to install:

```bash
ssh blgpu nvidia-smi
```

Expect driver 580.126.20 or newer and one RTX A6000 with 46,068 MiB. If it is missing, the manually
installed apt packages on the current box are `nvidia-driver-580-open` and `cuda-keyring`, so
`sudo apt install -y nvidia-driver-580-open` and a reboot is the path.

Do **not** install a CUDA toolkit. The current box has none and every GPU package used here ships
its own runtime inside the wheel. Add one only if something new needs to compile CUDA source.

### 4. Operating system packages

The current box carries the stock `ubuntu-server` set plus `build-essential`, `curl`,
`ca-certificates`, `openssh-server`, `qemu-guest-agent`, `nvidia-driver-580-open`, `cuda-keyring`,
`docker-ce` with `containerd.io` and `nvidia-container-toolkit`. All of that comes from the
template. The only thing to make sure of by hand:

```bash
ssh blgpu 'sudo apt-get update && sudo apt-get install -y build-essential curl ca-certificates rsync'
```

Nothing else is needed for the propagation stage. There is no system embree, no OpenEXR and no
ffmpeg on the box, and none is required: the `mitsuba` wheel bundles its own
`libembree3.so` (29,953,296 bytes) and `embreex` is a pip wheel. `gcc` is 11.4.0 and Docker is
29.3.0, neither of which the pipeline uses.

### 5. Create the mirrored path

```bash
ssh blgpu 'sudo mkdir -p /home/user && sudo chown admin:admin /home/user'
```

This is the whole trick. Everything below writes under `/home/user/aegis`.

### 6. Push the tree and build the environment

From the local machine:

```bash
cd /home/user/aegis/papers/city-exposure-study/semantic_twin
tools/blgpu.sh sync
tools/blgpu.sh setup
```

`setup` installs `uv` from `https://astral.sh/uv/install.sh` if it is missing, asks it for CPython
3.12, creates `/home/user/aegis/.venv`, then installs this pinned set:

```
numpy==2.4.6      scipy==1.17.1     mpmath==1.3.0      PyYAML==6.0.3
mitsuba==3.8.0    drjit==1.3.1      trimesh==4.12.2    embreex==4.4.0
shapely==2.1.2    mapbox-earcut     pillow==12.2.0     scikit-image==0.26.0
matplotlib==3.10.9                  pytest==9.0.3
```

then installs `aegis` and `aegis-semantic-twin` editable with `--no-deps`. The versions are pinned
rather than floated because the bit-for-bit comparison against the local machine is only meaningful
if both sides run the same numeric stack.

The environment that came out of this on the current box, read back from its `dist-info`
directories, is 32 distributions:

```
aegis==0.38.1.dev11+g5e2fc2ca3   aegis-semantic-twin==0.1.0   contourpy==1.3.3
cycler==0.12.1                   drjit==1.3.1                 embreex==4.4.0
fonttools==4.63.0                ImageIO==2.37.4              iniconfig==2.3.0
kiwisolver==1.5.0                lazy-loader==0.5             mapbox_earcut==2.0.0
matplotlib==3.10.9               mitsuba==3.8.0               mpmath==1.3.0
networkx==3.6.1                  numpy==2.4.6                 packaging==26.2
pillow==12.2.0                   pluggy==1.6.0                Pygments==2.20.0
pyparsing==3.3.2                 pytest==9.0.3                python-dateutil==2.9.0.post0
PyYAML==6.0.3                    rtree==1.4.1                 scikit-image==0.26.0
scipy==1.17.1                    shapely==2.1.2               six==1.17.0
tifffile==2026.7.31              trimesh==4.12.2
```

Interpreter details on the current box:

- `/home/user/aegis/.venv/bin/python` is Python **3.12.13**.
- It resolves to
  `/home/admin/.local/share/uv/python/cpython-3.12.13-linux-x86_64-gnu/bin/python3.12`.
- `uv` is 0.12.1 at `/home/admin/.local/bin/uv` and manages CPython 3.11.15 and 3.12.13.
- The system Python is 3.10.12, which the repository's `>=3.12` requirement rules out. Nothing
  system-wide is modified.
- **This is the exact interpreter path `tools/blgpu.sh` invokes**, both through the job wrapper's
  `PATH=/home/user/aegis/.venv/bin:$PATH` and through `doctor`, which calls
  `/home/user/aegis/.venv/bin/python` directly.

### 7. Restore the data the sync does not carry

If a stage needs source imagery, run the filtered rsync from the image evidence section above.

If a stage needs the meshes the tracer refuses, `tools/blgpu.sh sync --all-meshes`.

If a stage needs Blender, install it under the box's home, since every caller resolves it through
`~`:

```bash
ssh blgpu 'cd ~ && curl -LO https://download.blender.org/release/Blender4.5/blender-4.5.9-linux-x64.tar.xz \
  && tar xf blender-4.5.9-linux-x64.tar.xz && mv blender-4.5.9-linux-x64 blender-4.5 \
  && ~/blender-4.5/blender --version'
```

The current box has Blender 4.5.9 LTS, build date 2026-04-21, at `/home/admin/blender-4.5/blender`.

The GPU evidence stage (segmentation, depth) needs a separate environment that this document does
not rebuild. Its package lists, git commits and pinned HuggingFace model revisions are recorded in
`BLGPU_INVENTORY.md` and captured verbatim under
`papers/city-exposure-study/archive/blgpu_backup/env/`.

### 8. Environment variables and secrets

The propagation stage needs **no secret at all**. There is no `.env` file anywhere under
`/home/user/aegis` on the box, and none is required.

Names the study code reads from the environment, and where the value lives:

| Name | Read by | Source of the value |
| --- | --- | --- |
| `AEGIS_DATA_DIR` | `run_exposure.py`, for the phantom | defaults to `/home/user/aegis/data`, so unset is correct |
| `GOOGLE_API_KEY` | `semantic_twin/scene.py` | `/home/user/aegis/.env` on the local box |
| `GOOGLE_MAPS_API_KEY` | `download_inhouse_tiles.py`, falls back to `GOOGLE_API_KEY` | `/home/user/aegis/.env` on the local box |
| `MAPILLARY_TOKEN` | `semantic_twin/mapillary.py` | `/home/user/aegis/.env` on the local box |
| `BLUELOBSTER_API_KEY` | provisioning only, not the pipeline | `/home/user/goliat/.env` on the local box |

There is also a HuggingFace token file on the box at `/home/admin/.cache/huggingface/token`, 37
bytes, used by the segmentation work. Its contents were not read and are not recorded anywhere.

If a tile download or a panorama fetch has to run on the box, copy the specific variable across for
that one command rather than shipping the whole `.env`. Do not commit any of these values.

## Verification

### `tools/blgpu.sh doctor`

Prints hostname, load average, core count, memory, GPU name and VRAM and utilisation, free disk,
then the Python version and path, the versions of numpy, scipy, mitsuba, drjit, trimesh, shapely
and matplotlib, the resolved `aegis.__file__`, the resolved study package path, and finally
confirms that `from semantic_twin.propagation import SbrTracer` imports. A `MISSING` line for any
package, or an `aegis` path outside `/home/user/aegis/src`, means the environment is wrong.

Reference output from the current box:

```
host      GPUcompute
load      0.01 0.01 0.00
cores     8
mem       31 GiB total, 30 GiB available
gpu       NVIDIA RTX A6000, 46068 MiB, 0 %
disk      150G free
python    3.12.13  /home/user/aegis/.venv/bin/python
numpy     2.4.6
scipy     1.17.1
mitsuba   3.8.0
drjit     1.3.1
trimesh   4.12.2
shapely   2.1.2
matplotlib3.10.9
aegis     /home/user/aegis/src/aegis/__init__.py
study     ['/home/user/aegis/papers/city-exposure-study/semantic_twin/semantic_twin']
tracer    import ok
```

### `tools/blgpu.sh verify [RAYS]`

Runs `tools/blgpu_reference.py` three times: locally, on the box, and on the box under
`taskset -c 0`. That script pins the mesh (`data/geometry/korenmarkt/inhouse_leaf_130m_f64.ply`),
three observation points, three illumination models, the material and the seed, then prints every
susceptibility as a C99 hexadecimal float literal, which round-trips exactly, and a sha256 over the
raw bytes of every angular power spectrum. The three outputs are diffed with the `# host` line
removed, so one differing character is a real numerical difference and not a formatting artefact.

The last recorded run, 2026-08-03 at 200,000 rays, was identical on all 77 lines, including under
`taskset`. `python -m pytest tests/test_propagation.py -q` also passed on the box, 41 of 41.

Default ray count is 200,000. Use fewer for a quicker check:

```bash
tools/blgpu.sh verify 50000
```

### GPU smoke test

`doctor` and `verify` both exercise the CPU path only, because `llvm_ad_rgb` is the default variant
in every entry point in this study. To prove the GPU actually works, load a real mesh under
`cuda_ad_rgb` and trace through it. This was run during the audit and these are the real numbers:

```bash
tools/blgpu.sh sh 'python - <<PY
import time, pathlib, numpy as np, mitsuba as mi
mi.set_variant("cuda_ad_rgb")
from semantic_twin.propagation.geometry import MitsubaGeometry
p = pathlib.Path("data/geometry/korenmarkt/inhouse_leaf_130m_f64.ply")
g = MitsubaGeometry(p, variant="cuda_ad_rgb")
print("faces", g.face_count, "variant", g.variant)
rng = np.random.default_rng(0)
d = rng.normal(size=(200_000, 3)); d /= np.linalg.norm(d, axis=1, keepdims=True)
o = np.zeros((200_000, 3)); o[:, 2] = 2.0
t0 = time.time(); hit, *_ = g.intersect(o, d)
print("%.3f s, hit fraction %.4f" % (time.time() - t0, float(np.mean(hit))))
PY'
```

Expected: `mitsuba.variants()` lists five `cuda_ad_*` variants, the mesh loads in 0.15 s with
157,862 faces, and 200,000 rays intersect in 0.06 s, which is 3.1 million rays per second, with a
hit fraction of 0.3153.

One honest note on that number. The same 200,000 rays under `llvm_ad_rgb` on the 8 cores take
0.024 s, which is 8.3 million rays per second. At this batch size the CPU is nearly three times
faster than the GPU, because the kernel launch dominates. The GPU is worth using for the
segmentation and depth models, not for this tracer, and that is why every script in the study
defaults to `llvm_ad_rgb`.

For an end-to-end run that writes one small JSON and nothing else:

```bash
JOB=$(tools/blgpu.sh run "python run_next_event.py --sites korenmarkt --rays 20000 --builders 16 --held-out 4 --tag rebuild_smoke")
tools/blgpu.sh follow $JOB
```

It writes `outputs/next_event/rebuild_smoke_250m.json`. `run_next_event.py` takes `--variant`, so
`--variant cuda_ad_rgb` puts the whole estimator on the GPU, but the CPU default is the one that
reproduces published numbers.

## What is precious

**Nothing on the box is irreplaceable.** That is the short answer and it is worth stating plainly,
because it changes the risk of destroying the machine from high to low. The detail matters though,
because "nothing precious" was true only after a deliberate backup, and some material has landed
since.

### Under `/home/user/aegis`, the tree the helper script manages

Compared file by file against the local tree on 2026-08-03. Excluding `.venv`, `.blgpu_jobs` and
`__pycache__`, the box holds 4,299 files. Of those:

- **123 files, 2.7 MB total, have no local counterpart.** They break down as 39 stale `.md` files
  sitting at the study root that were later moved into `docs/` locally and exist there, 65 files
  under `.perfbench/before/` which is a snapshot of the package taken before a performance change,
  and about 19 loose scratch scripts and LaTeX build products (`bench.py`, `bench2.py`,
  `bench_variant.py`, `profile_trace.py`, `METHOD.tex` and its `.aux`/`.log`/`.out`, `blend_all.sh`,
  `evid.sh`, `evid2.sh`, `trace_all.sh`, `peek.py`, egg-info). `METHOD.tex` on the box is 29,541
  bytes against 30,094 locally at `archive/METHOD.tex`, so it is an older copy.
- **6 files differ in size**, and in every case the local copy is the newer and larger one
  (`download_inhouse_tiles.py`, `fetch_site_panoramas.py`, `tests/test_download_inhouse_tiles.py`,
  a Madrid `walk_manifest.json`, and two `.pytest_cache` bookkeeping files).
- **Every one of the 32 `outputs/` subdirectories on the box has a local counterpart of equal or
  larger size.** `exposure_korenmarkt` is 128 MB on the box against 173 MB locally,
  `propagation_viz` 754 MB against 1,034 MB, `material_vlm` 1 MB against 13 MB, and the rest match
  exactly.

So the tree `blgpu.sh` drives holds nothing that is not already local. `tools/blgpu.sh fetch` has
been keeping up.

### Under `/home/admin`, other work on the same box

This is the part `blgpu.sh` never touches and `fetch` never sees. A full audit and backup was done
on 2026-08-02 and is recorded in `BLGPU_INVENTORY.md`. It copied **5.9 GiB in 3,292 files** to
`papers/city-exposure-study/archive/blgpu_backup/`, which is present locally and is not committed to
git. That backup covers everything unique as of that date, including the 20 mesh-QA PLYs in
`~/st/mesh_study` (501 MB in the backup).

About **13.2 GB of files landed after that backup**. Checked directory by directory:

| Path on box | Size | New since backup | Verdict |
| --- | --- | --- | --- |
| `~/st` | 27.8 GB | 4,463 files | 25.9 GB has no local counterpart, and 23.07 GB of that is 4,888 per-view `.npy` label and confidence rasters under `data/panoramas/<city>/<pano>/semantics/views/`. **Regenerable.** They are strictly upstream of the fused `panorama_semantics.npz` plus `semantics.json`, and those fused files are local. |
| `~/st` panorama JPEGs | 2.08 GB | | **Already local.** They looked missing only because of a naming difference: the box calls a Tokyo panorama directory `pano_06_uNkIV8NcS80E4kMD` and the local tree calls it `indoor_2018-05_06_uNkIV8NcS80E4kMD`. Sampled, `panorama_z5.jpg` is the same 16 MB file on both sides. |
| `~/pviz` | 426 MB | 143 files | **Superseded.** Four sites and 70 figures, last written 2026-08-03 01:10. The local `outputs/propagation_viz` is newer (2026-08-03 05:40), covers 11 sites and holds 155 figures. |
| `~/bounce3` | 1.1 GB | 7,029 files | Almost all of it is a nested `venv/`. The 2.2 MB of package source is a second checkout of code that is in git. |
| `~/timing_probe` | 257 MB | 83 files | 23.5 MB of segmentation view arrays from a timing probe. Regenerable. |
| `~/perf` | 20 MB | 63 files | 0.2 MB of package source, the same snapshot as `.perfbench/before`. |
| `~/aegis-semantic-twin` | 622 MB | 3,458 files | Grew from 10 MB to 622 MB, entirely by gaining a `.venv/`. The 9.9 MB of real content was backed up. |
| `~/tracenv`, `~/sam3-venv`, `~/sam3-body-venv`, `~/stenv` | 600 MB, 8.5 GB, 7.5 GB, 427 MB | | Virtual environments. Package lists saved in the backup under `env/`. |
| `~/.cache/uv`, `~/.cache/huggingface`, `~/.drjit` | 18 GB, 6.6 GB, 1.6 GB | | Caches. Model revisions are pinned and recorded in `BLGPU_INVENTORY.md`. |
| `~/checkpoints`, `~/sam3`, `~/sam-3d-body`, `~/UniDepth`, `~/blender-4.5` | 2.3 GB, 7.2 GB, 48 MB, 46 MB, 1.5 GB | | Downloads and clones at pinned revisions. |

### What to pull off before destroying the box

If the box is destroyed today, the only real loss is **time, not information**: roughly 23 GB of
per-view Mask2Former rasters across seven cities. Every one of them has already been reduced to a
fused `panorama_semantics.npz` that lives locally. They matter only if someone later wants to
re-fuse those exact panoramas under different fusion parameters without re-segmenting. Re-segmenting
is 50 to 80 seconds per panorama on an A6000, so the whole set is a few hours of rental at 55 cents
per hour, and the driver commands are preserved at
`archive/blgpu_backup/home_loose/remote_seg.sh`.

Before destroying, do three things:

```bash
cd /home/user/aegis/papers/city-exposure-study/semantic_twin
tools/blgpu.sh jobs                 # 1. confirm nothing is still running
tools/blgpu.sh fetch outputs        # 2. pull the propagation results back
ssh blgpu 'du -sh ~/* | sort -h'    # 3. look for a home directory newer than this document
```

Step 3 is the one that matters. Other agents create new directories under `/home/admin` without
telling anyone, and `~/bounce3`, `~/pviz`, `~/perf` and `~/timing_probe` all appeared in the 26
hours after the 2026-08-02 backup was written. Anything there that a local path does not already
hold has to be rsynced off by hand.

## Known gotchas

**`sync` does not push images.** Covered above. The propagation stage does not need them, so this
is easy to forget until a re-segmentation or a raw-imagery figure fails on the box with a missing
file.

**`/home/admin/semantic_twin` shadows the study package.** It is a 2.0 GB directory of UniDepth
output from earlier work. It sits in the home directory and carries no `__init__.py`, so
`import semantic_twin` from `~` picks it up as a namespace package and the real one never gets a
look in. Every entry point in `blgpu.sh` exports
`PYTHONPATH=/home/user/aegis/papers/city-exposure-study/semantic_twin` for exactly this reason. If
you ssh in by hand, export it yourself.

**`bash -lc` picks the wrong interpreter.** The login profile prepends `~/.local/bin`, which holds
the uv-managed `python3.12`, ahead of anything exported before it. The job wrapper uses plain
`bash -c` on purpose. Note that `uv` itself is at `~/.local/bin/uv` and is therefore **not** on the
non-login PATH, so `ssh blgpu uv --version` fails while `ssh blgpu 'bash -lc "uv --version"'` works.

**`$HOME` is `/home/admin`, not `/home/user`.** So `~/aegis` does not exist on the box even though
`/home/user/aegis` does. This is fine for Blender, which lives at `~/blender-4.5/blender` on both
machines, and wrong for anything that reaches the repository through `~`.

**Version pinning needs `SETUPTOOLS_SCM_PRETEND_VERSION`.** The repository is synced without `.git`,
so hatch-vcs cannot derive a version for `aegis`. `setup` reads `aegis.__version__` out of the local
venv and passes it through that variable, which keeps the version identical on both machines. The
`SETUPTOOLS_SCM_PRETEND_VERSION_FOR_AEGIS` form that the build error message suggests is ignored by
this backend.

**The geometry filter is on `format_version`, not on the `_f64` suffix.** Filtering on the suffix
looks equivalent and is not. New York and Toulouse only ever got an unsuffixed build, and that build
is already double precision. A suffix filter silently drops New York, and `--all-sites` then reports
`[skip] newyork_timessquare: no 250 m mesh` on the box but not locally. `sync` reads
`format_version` out of each mesh manifest, which is the same rule `run_exposure.site_mesh` applies.
Six older Korenmarkt and Milan crops, 34 MB, are the only meshes left behind.

**rsync exit 24 is forgiven on purpose.** About ten agents write into this tree at once, so a file
vanishing between rsync's scan and its transfer is routine. Only exit 24 is forgiven, nothing else.

**A stale sync looks exactly like a machine disagreement.** A test suite once failed on the box and
passed locally, which looks like the numerical difference this whole setup exists to rule out. It
was not. The test file had been rewritten locally after the last `sync`, so the box was running a
newer tracer against an older test. Anything that looks like a machine disagreement is a stale sync
until `md5sum` on both sides says otherwise. `run --sync` exists so the question does not come up.

**The box is not yours alone.** Check `doctor` for load before starting something large. A second
agent once took the box from load 0.0 to load 29 and per-location trace time went from 0.8 s to
between 3.6 and 4.7 s. Eight cores are still eight cores, but they are not eight cores each.

**The identity file name lies.** `~/.ssh/tensordock_ed25519` is a Blue Lobster key. The name is a
leftover from the provider that Blue Lobster replaced. There is no `.pub` next to it, so derive the
public half with `ssh-keygen -y`.

**No firewall anywhere.** `ufw` is inactive on the box, the provider firewall accepts everything in
both directions with zero rules, and only sshd listens on a public address. Do not casually bind a
development server to `0.0.0.0` here.

**No `nvcc`.** Anything that needs to compile CUDA source will fail. Install a toolkit only if that
day comes.

**Nothing is scheduled.** `admin` has no crontab, `/etc/cron.d` holds only the distribution's
`e2scrub_all`, and there are no custom systemd units. The running services are all stock Ubuntu plus
`docker`, `containerd`, `nvidia-persistenced` and `qemu-guest-agent`. So nothing on the box restarts
work by itself, and a rebuilt box needs no scheduling to be set up.

**Billing does not stop when the box is idle.** At 55 cents per hour the machine costs about 13 USD
per day whether or not a job is running. There is no idle-stopper installed here, unlike the
TensorDock arrangement, because on this provider a stopped instance still bills.
