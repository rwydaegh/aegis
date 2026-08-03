# Semantic twin

A scene reconstruction for millimetre-wave exposure assessment, built from street
level panoramas and aerial photogrammetry, plus the adjoint SBR estimator that
consumes it. It feeds the city exposure study in the parent directory, which is
now eleven squares rather than the ten the older documents name.

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

Two sites carry the full material stack: Korenmarkt in Ghent and Piazza del Duomo
in Milan. Six further squares carry panoramas with dense entity segmentation and
no material axis, and three carry no panoramas at all. See the status section for
what that means for the published numbers.

## The stages

Geometry comes first. `download_inhouse_tiles.py` pulls Photorealistic 3D Tiles
over a cylindrical region of interest and `build_inhouse_mesh.py` assembles them
into a support mesh in a local ENU frame. Tile placement is read in double
precision straight from the glTF node matrices, never through Blender's float32
object transforms, which quantise at half a metre out at Earth radius.

Registration follows. `download_mapillary_panoramas.py` selects and fetches
panoramas, and `semantic_twin/align_skyline.py` fits the camera pose against the
mesh skyline. Every pose ships with a covariance from an independent seed study,
not a single residual, and camera altitude is measured against the mesh under
that specific camera rather than assumed from a scene constant.

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

Propagation is last. `semantic_twin/propagation/` holds the adjoint shoot and
bounce estimator: rays leave the standpoint, bounce until they escape the crop,
and deposit throughput into a bin indexed by departure direction, which
reciprocity makes the local arrival direction. `run_exposure.py` drives it and
writes a summary, a CDF and a manifest per run under
`outputs/exposure_korenmarkt/`. The illumination laws that weight the exit
directions live in `semantic_twin/propagation/directions.py`, and the corrected
band law of 2026-08-02 is the one the current results use.

## Reading order

- `PAPER_METHODS.md` is the method and results writeup, and it is where the
  eleven site table and its caveats live. Start here if you want the numbers.
- `DECISIONS.md` is the running record of every call and the measurement behind
  it. Start here if you want to know why anything is the way it is. It is a log,
  so it carries superseded numbers on purpose, labelled where they are
  superseded.
- `ROADMAP.md` is the phase plan with current status against it.
- `DESIGN.md` covers the pipeline architecture.
- `FISHNET.md` covers the geometry cutter that replaced the quadtree.
- `MONOSTATIC_SBR.md` is the propagation formulation the surface elements feed.
- `ROUGHNESS.md` and `config/surface_roughness.json` grade the roughness prior by
  provenance, since much of what the literature reports as a measured roughness
  is a radio fit wearing a metrology citation.
- `PRIOR_ART.md` is a hostile review of what the published work already owns.
- `METHOD.tex` is the explanatory writeup of the co-located transmitter argument
  and where it stops applying.
- `FIGURES/README.md` says what each numbered figure shows and which script
  regenerates it.

## Running it

Python 3.12, from the repository virtualenv. Tests and lint:

```bash
python -m pytest tests/ -q
python -m ruff check .
```

One exposure run, which is what every published number is made of:

```bash
python run_exposure.py --site korenmarkt --crop-m 250 --locations 80 \
  --rays 200000 --max-bounces 3 --seed 7 --tag city250_L3_korenmarkt
```

That run takes minutes on a quiet machine and much longer on a busy one. To send
it to the rented 8 core box instead, see `REMOTE_COMPUTE.md`:

```bash
JOB=$(tools/blgpu.sh run --sync "python run_exposure.py --all-sites --locations 80")
tools/blgpu.sh wait $JOB && tools/blgpu.sh fetch $JOB outputs/exposure_korenmarkt
```

The tracer reproduces bit for bit there, checked to full float64 precision
rather than to a tolerance, so results from the box are publishable.

Tile downloads need a Google Maps Platform key in the environment. Panorama
selection needs a Mapillary token. Neither is committed. `outputs/` and
`data/panoramas/` are not tracked, so a fresh clone has the code and none of the
artifacts.

## Status

The reconstruction stages are built and tested. The propagation estimator is
built, validated against closed forms and run: eleven squares at a 250 m crop,
80 standpoints each, at 15 GHz, three surface interactions, tagged
`city250_L3_*`. Earlier tags for the same eleven squares are kept beside it and
are not the headline. `city250_corrected_*` is the same sweep at four bounces on
a ground datum that put the Krakow and Toulouse walks on a roof, and
`AGGREGATE_REBUILD.md` audits the difference.

Three things about those numbers should be read before the numbers themselves.

**The eleven site result uses no image evidence.** Every one of the eleven
manifests carries `semantic_binding.materials = "geometric"`, with
`covered_fraction_by_face` and `covered_fraction_by_area` both exactly 0.0. The
surface class is decided by the face normal and the material comes from a prior,
so nothing in this README's first three stages reaches the headline table. The
semantic ablation is a separate Korenmarkt-only run at the 130 m crop, which the
crop study says is not converged for either directional model.

**The material axis ran at two sites.** SAM 3 produced concepts for 2 of the 96
panoramas that carry semantics. The other 94 have the dense Vistas entity
partition and no material posterior.

**Most registrations feed nothing.** Of the 83 poses in
`outputs/registration_sky_conflict.csv`, 14 are consumed downstream. The
remaining 69, every pose at Brussels, Mexico, New York, Prague, Madrid and Tokyo,
exist and are used by no result.

One correction dominates how older numbers read. On 2026-08-02 the directional
illumination law was replaced, because the `1/sin^3(alpha)` weight was derived
for sources at one fixed height and was then being used over the support of a
height band. Anything computed before that date under the rooftop or street small
cell models is superseded. The old pair is kept as `ROOFTOP_FIXED_HEIGHT` and
`STREET_SMALL_CELL_FIXED_HEIGHT` so those numbers stay reproducible. The
correction is site dependent, 1.06 dB at Krakow to 6.33 dB at Madrid on the
rooftop median, so it cannot be undone with a constant offset and it reorders the
squares.

A second correction lands on 2026-08-03 and is independent of the first. The
ground datum estimator took the median downward first hit at the crop centre,
which at Krakow and Toulouse is a building, so those two walks ran 18.19 and
13.94 m up on the Cloth Hall and the Capitole. `GROUND_DATUM.md` carries the
replacement and `AGGREGATE_REBUILD.md` the requalified sweep. Anything quoting
Krakow or Toulouse from before that date is a roof.
