# Phantom build pipeline

AEGIS ships four parametric human phantoms as GLB files in `data/phantoms/`. These are generated from MakeHuman body meshes with Mixamo skeletal animations baked in, all driven by a single Blender script.

The pipeline: MakeHuman (via MPFB2) generates the mesh, Mixamo provides animation clips, and Blender joins everything into a GLB with embedded skeleton and NLA tracks.

## Prerequisites

- **Blender 3.6+** (runs headless via `--background`)
- **MPFB2** (MakeHuman Plugin for Blender 2.0), the Blender addon that generates parametric human meshes
- **Mixamo FBX clips** for the animations (requires an Adobe account)

## Installing MPFB2

Download `mpfb-2.0-b1.zip` from [makehuman.org](http://static.makehumancommunity.org/mpfb/releases/release_20b1.html). Two ways to install:

1. Through Blender: Edit > Preferences > Add-ons > Install, select the zip. This registers the addon globally.
2. Manual: unzip to `tools/mpfb2/` in the repo root. The script imports directly from `mpfb.services`.

The zip is ~40 MB and gitignored. Do not commit it.

## Mixamo animations

The script expects four FBX files in `data/phantoms/`:

| FBX file | Action name | Description |
|---|---|---|
| `Idle.fbx` | `idle` | Standing idle, default pose |
| `Walking.fbx` | `walking` | Walking cycle |
| `Talking On Phone.fbx` | `phone_ear_r` | Phone held to right ear |
| `Sitting Idle.fbx` | `sitting` | Seated idle |

Download these from [mixamo.com](https://www.mixamo.com/). Export settings: FBX Binary, no skin (the script uses its own mesh). The `phone_ear_r` action is automatically mirrored to create `phone_ear_l`.

FBX files are gitignored (`data/phantoms/*.fbx`).

## Running the script

```bash
blender --background --python scripts/build_phantoms.py
```

Blender must have MPFB2 installed (either via addon preferences or on the Python path). The script runs entirely headless. No GPU required.

For each character, the script:

1. Generates a MakeHuman mesh via MPFB2's `HumanService`
2. Adds a Mixamo-compatible skeleton via `HumanService.add_builtin_rig`
3. Bakes shape keys into clean geometry
4. Scales to the target height
5. Triangulates and recalculates outward normals
6. Imports each Mixamo FBX, retargets bone prefixes, and pushes actions to NLA tracks
7. Exports as GLB with animations, skeleton, and a PBR skin material

## Character definitions

Four characters are defined in `scripts/build_phantoms.py`:

| Character | Height | Mass | Gender | Age | Notes |
|---|---|---|---|---|---|
| `adult_male` | 1.76 m | 73 kg | Male | Young adult | Reference adult male |
| `adult_female` | 1.63 m | 60 kg | Female | Young adult | Reference adult female |
| `boy_6y` | 1.15 m | 19 kg | Male | Child (~6 y) | Pediatric phantom |
| `girl_8y` | 1.36 m | 30 kg | Female | Child (~8 y) | Pediatric phantom |

Each character is controlled by MPFB2 macro sliders (gender, age, muscle, weight, height, proportions) with values in the 0.0-1.0 range. See the `CHARACTERS` list in the script for exact values.

## Output

The script writes four files to `data/phantoms/`:

```
data/phantoms/
    adult_male.glb
    adult_female.glb
    boy_6y.glb
    girl_8y.glb
```

Each GLB contains a triangulated mesh, an armature with Mixamo-compatible bone names, a PBR skin material, and five animation actions (idle, walking, phone_ear_r, phone_ear_l, sitting). The viewer loads these directly via Three.js and can switch between animations at runtime.

## Adding a character

Append a dict to the `CHARACTERS` list in `scripts/build_phantoms.py`:

```python
{
    "name": "elderly_male",
    "target_height_m": 1.70,
    "target_mass_kg": 75,
    "macro": {
        "gender": 0.0,
        "age": 0.9,
        "muscle": 0.3,
        "weight": 0.55,
        "proportions": 0.5,
        "height": 0.6,
        "cupsize": 0.5,
        "firmness": 0.3,
        "race": {"african": 0.0, "asian": 0.0, "caucasian": 1.0},
    },
    "skin_color": (0.70, 0.52, 0.40, 1.0),
}
```

The `macro` dict maps directly to MPFB2's parametric sliders. The `target_height_m` value is used to scale the generated mesh after creation. Run the script again to regenerate all phantoms.

## SMPL-X bootstrap

The SMPL-X parametric body lives behind `ParametricBody.load("smplx")` (`src/aegis/geometry/parametric.py`) and the `POST /api/parametric-body` viewer route. The Python plumbing comes from the `[body]` extra: `pip install -e ".[body]"` (pulls `smplx`, `torch`, `pygltflib`).

The model files are license-gated. Register at [smpl-x.is.tue.mpg.de](https://smpl-x.is.tue.mpg.de/), accept the EULA, and download `models_smplx_v1_1.zip` (~200 MB, three NEUTRAL/MALE/FEMALE NPZs plus pkl variants). Then place them with:

```bash
python scripts/fetch_smplx.py /path/to/models_smplx_v1_1.zip
```

The script copies `SMPLX_NEUTRAL.npz`, `SMPLX_MALE.npz`, and `SMPLX_FEMALE.npz` into `~/.aegis/models/smplx/` (override with `--dest` or `AEGIS_MODELS_DIR`). It accepts either the official zip or an already-extracted directory and is idempotent. Once those three files exist, `tests/test_parametric.py` and `tests/test_viewer_parametric.py` un-skip and `ParametricBody.load("smplx").generate(np.zeros(10))` returns a real triangle-soup `BodyMesh`.

For CI / cloud runners, mirror the unzipped files into the same path or set `AEGIS_MODELS_DIR` to a host-side cache. The files cannot be redistributed in this repository.
