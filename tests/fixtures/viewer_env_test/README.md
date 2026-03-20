# Viewer environment UI stub

Minimal voxel JSON (flat 2×2 slab) for manually checking **Environment view** (cubes vs hull vs tiles) in `py -3.12 -m aegis.viewer --voxel-json tests/fixtures/viewer_env_test/voxels.json`.

Use with a small body, for example:

```bash
py -3.12 -m aegis.viewer --no-open --port 5091 ^
  --data-dir tests/fixtures/e2e_lab --body e2e_icosahedron ^
  --voxel-json tests/fixtures/viewer_env_test/voxels.json
```

DiffeRT (`pip install aegis[rt]`) is required for the **Ray-tracing hull mesh** option.
