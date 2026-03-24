# Viewer configuration

`default.json` is merged on top of `src/aegis/viewer/config.py` defaults (deep merge). You can copy it to a new file and pass `--config path/to/yours.json`.

## Scenarios

Named scenarios bundle launch parameters so runs are easy to repeat and document.

- **`default_scenario`** (optional): applied when you omit `--scenario`. Set to `null` to disable.
- **`scenarios`**: map of scenario id → `{ "description": "...", "launch": { ... } }`.

Supported **`launch`** keys (all optional; CLI flags override):

| Key           | Meaning                                              |
|---------------|------------------------------------------------------|
| `voxel_dir`   | Directory of voxel JSON files, or `null` for none  |
| `voxel_json`  | Single voxel JSON path, or `null`                  |
| `body`        | STL stem under the data directory                    |
| `bbox`        | Scene box size in meters (same as `--bbox`)          |
| `data_dir`    | Override STL data directory                          |

Built-in default scenarios live in `config.py` (e.g. `open_ground`: body + ground, no voxels). Add more in your JSON:

```json
"scenarios": {
  "my_site": {
    "description": "Local capture",
    "launch": {
      "voxel_dir": "C:/data/my_tile",
      "bbox": 40
    }
  }
}
```

Run: `python -m aegis.viewer --config configs/default.json --scenario my_site`.

`--location` / `--voxel-dir` on the CLI still win over the scenario after merge.

## Antenna radiation pattern (viewer)

The 3D viewer can draw a **jet-colored** radiation lobe around the hub (`antenna.radiation_pattern`). By default it shows a vertical **short dipole** donut in scene space (Y is up in Three.js). That is **illustrative**: synthetic dosimetry and the bundled ray tracer still use **isotropic** equivalent power toward the body. Set `match_physics` to `true` for a uniform sphere that matches that isotropic assumption.

For future **MIMO / arrays**, use `elements`: each entry has `offset` [m], complex `weight` `[Re, Im]`, and dipole `axis` in scene coordinates. With more than one element, small markers appear at each offset; gain is an **incoherent sum** of element powers (not a phased array beam yet).

## E2E lab fixture

`configs/e2e_lab.json` drives a **small tracked STL** under `tests/fixtures/e2e_lab/` (no voxels, deterministic multipath jitter). Use it for manual browser QA or Playwright without Thelonious or voxel data.

```bash
python -m aegis.viewer --config configs/e2e_lab.json --no-open
```

Run the viewer from the **repository root** so `tests/fixtures/e2e_lab` resolves. See `tests/fixtures/e2e_lab/README.md` to regenerate the STL after changing `make_icosahedron()`.
