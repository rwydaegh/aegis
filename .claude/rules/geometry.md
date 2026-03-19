---
paths: ["src/aegis/geometry/**"]
description: Body geometry conventions and data paths
---

# Geometry rules

## Mesh conventions

- Triangle normals point outward from the body surface
- Areas are in m^2
- Centroids are in meters (world coordinates)
- BodyMesh stores: vertices, triangles, normals, areas, centroids

## Data paths

- Mesh files (STL, ~5MB) live in `../data/`
- Set `AEGIS_DATA_DIR` env var or the default `../../data` is used
- Tests needing mesh data are marked `@pytest.mark.slow` and skipped if data is absent

## Spatial averaging

- ICNIRP 2020 requires 4 cm^2 averaging area
- Implementation in `averaging.py` uses geodesic neighbor search
- The averaged result must still satisfy Sab >= 0
