# Semantic twin

A scene reconstruction for millimetre-wave exposure assessment, built from street
level panoramas and aerial photogrammetry. It feeds the ten-cities exposure study
in the parent directory.

The premise is that a panorama already carries, at centimetre scale, most of what
a ray tracer needs and a building footprint does not: which surface is brick and
which is glass, whether a facade is smooth or coursed, and where the parked cars
and street furniture that no map records actually stand. The pipeline extracts
that, registers it against photogrammetric geometry, and emits surface elements
carrying a material posterior rather than a single guessed label.

## What it produces

For each site, a set of surface elements cut along semantic island boundaries in
image space, each carrying a class, a material posterior over the ITU-R P.2040-4
table, a confidence, a normal, an area, a solid angle, a visible fraction and a
provenance record pointing back at the pixels that decided it. Alongside them, a
parallel table of rejected regions that keeps permanent clutter separate from
transient objects, and a body layer placing pedestrians as SMPL-X meshes.

Two sites are built: Korenmarkt in Ghent and Piazza del Duomo in Milan.

## The stages

Geometry comes first. `download_inhouse_tiles.py` pulls Photorealistic 3D Tiles
over a cylindrical region of interest and `build_inhouse_mesh.py` assembles them
into a support mesh in a local ENU frame. Tile placement is read in double
precision straight from the glTF node matrices, never through Blender's float32
object transforms, which quantise at half a metre out at Earth radius.

Registration follows. `download_mapillary_panoramas.py` selects and fetches
panoramas, and `align_skyline.py` fits the camera pose against the mesh skyline.
Every pose ships with a covariance from an independent seed study, not a single
residual, and camera altitude is measured against the mesh under that specific
camera rather than assumed from a scene constant.

Semantics run at native resolution. `project_semantics.py` and the concept
machinery in `semantic_twin/semantics.py` resolve dense classes and open
vocabulary concepts into a joint entity and material posterior, which
`semantic_twin/materials.py` binds to ITU-R P.2040-4 rows with an explicit
provenance grade. Depth from two independent models, compared in
`compare_mesh_depth.py`, decides whether a pixel that disagrees with the mesh is
clutter standing in front of it, a transient object, or a registration conflict.

`build_fishnet_surface.py` then cuts the surface elements, and
`build_texture_evidence.py` supplies coarse material evidence on the faces no
panorama sees, from the aerial tile textures, capped so it can never overturn a
panorama observation.

## Reading order

- `DECISIONS.md` is the running record of every call and the measurement behind
  it. Start here.
- `DESIGN.md` covers the pipeline architecture.
- `FISHNET.md` covers the geometry cutter that replaced the quadtree.
- `MONOSTATIC_SBR.md` is the propagation formulation the surface elements feed.
- `ROUGHNESS.md` and `config/surface_roughness.json` grade the roughness prior by
  provenance, since much of what the literature reports as a measured roughness
  is a radio fit wearing a metrology citation.
- `PRIOR_ART.md` is a hostile review of what the published work already owns.
- `METHOD.tex` is the explanatory writeup of the co-located transmitter argument
  and where it stops applying.

## Running it

Python 3.12, from the repository virtualenv. Tests and lint:

```bash
python -m pytest tests/ -q
python -m ruff check .
```

Tile downloads need a Google Maps Platform key in the environment. Panorama
selection needs a Mapillary token. Neither is committed.

## Status

The reconstruction stages are built and tested. The propagation engine designed
in `MONOSTATIC_SBR.md` is not, and no exposure number has been computed yet.
