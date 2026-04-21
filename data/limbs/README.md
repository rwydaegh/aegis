# Limb / head+trunk classification

Per-face boolean masks splitting each phantom mesh into two ICNIRP 2020 dosimetry regions:

- `is_limb == True`  → arms (incl. shoulder caps), legs, hands, feet
- `is_limb == False` → head, neck, trunk

## Files

| File                     | Contents                                                           |
|--------------------------|--------------------------------------------------------------------|
| `<name>_limbs.npz`       | `is_limb` (bool, shape `(F,)`), `groin_z`, `armpit_z`              |
| `<name>_limbs.png`       | Three-view render (front / side / top), red = limb                 |
| `<name>_slices.png`      | Debug plot of slice-component count vs z with groin/armpit lines   |

Indexing matches `mesh.faces` of `data/<name>.stl` loaded with `trimesh`.

## Script

`scripts/classify_limbs.py <phantom_name>` regenerates everything (currently
`duke`, `ella`, `eartha`, `thelonious`).

## How it works

Purely slice-based, no SDF, no thresholds, no phantom-specific numbers:

1. Slice the mesh at 220 horizontal z-levels via `mesh.section_multiplane`.
2. `groin_z` = lowest z where any slice polygon straddles the body's vertical axis
   (the two legs have merged into a pelvis that crosses `x = x₀`).
3. `armpit_z` = highest z with slice count ≥ 3 (trunk + two arms cleanly separated);
   fall back to ≥ 2 if arms are asymmetric.
4. Face classification:
   - `z < groin_z` → **limb** (leg + foot).
   - `groin_z ≤ z ≤ armpit_z` and (x,y) outside the largest polygon at that slice
     (1 cm buffer) → **limb** (arm).
   - `z > armpit_z` and x outside the armpit-trunk x-range → **limb** (shoulder cap).
     Only the x axis is tested, so the chin/nose/forehead extending forward in y
     stay classified as head/trunk.
   - Otherwise → **head/trunk**.
5. One neighbor-majority smoothing pass + removal of connected components smaller
   than 80 faces to clean speckles.

Dependencies: `trimesh`, `shapely`, `networkx`, `rtree`, `scipy`, `matplotlib`.
