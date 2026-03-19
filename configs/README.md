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

Run: `py -3.12 -m aegis.viewer --config configs/default.json --scenario my_site`.

`--location` / `--voxel-dir` on the CLI still win over the scenario after merge.

## Automated E2E lab

`configs/e2e_lab.json` drives a **small tracked STL** under `tests/fixtures/e2e_lab/` (no voxels, deterministic multipath jitter). Use it for Playwright and `test_viewer_e2e.py` without Thelonious or voxel data.

```bash
py -3.12 -m aegis.viewer --config configs/e2e_lab.json --no-open
py -3.12 test_viewer_e2e.py --base http://127.0.0.1:5070 --profile lab
```

Run the viewer from the **repository root** so `tests/fixtures/e2e_lab` resolves. See `tests/fixtures/e2e_lab/README.md` to regenerate the STL after changing `make_icosahedron()`.
