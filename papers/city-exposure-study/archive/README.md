# Archive

Nothing here was deleted. This is where things went that are finished, or that
nothing in the study reads any more. Everything is on disk exactly as it was;
only the directory names changed.

If you are looking for the map of the whole study directory, read
`../INVENTORY.md`.

## `blgpu_backup/` (5.9 GB, 3,292 files)

A read-only copy of a rented GPU box (RTX A6000, host `GPUcompute`, reached as
`ssh blgpu`), taken 2026-08-02 before the box was given up. Nothing on the box was
deleted to make it.

The full record of what was copied, what was skipped, and how to rebuild the
skipped parts is `../semantic_twin/docs/BLGPU_INVENTORY.md`. In short: raw
inference output, benchmark runs, remesh QA and the segmentation ablation were
copied; package caches, model checkpoints, virtual environments and Blender
itself were not, because each has a one-line recipe to fetch again.

No script or document reads a path inside this directory. It is a safety copy.

## `propagation_previews/` (31 MB, 28 PNG)

Preview frames rendered by `../semantic_twin/propagation_blender.py`, seven views
each for four of the eleven squares (Korenmarkt, Krakow, Times Square, Grand
Place). The full set of eleven lives in `../semantic_twin/propagation_blends.zip`
as Blender files.

Note that the `README.md` inside this directory does not describe these PNGs. It
is a copy of the index text that `build_propagation_blends.py` writes into the
zip, and it describes the Blender files. It was left as found.

## `propagation_blends.zip` (189 MB)

Byte for byte the same file as `../semantic_twin/propagation_blends.zip` (md5
`7e4932375c29a95925cb24b577af9e0d`). The copy inside `semantic_twin/` is the one
the documents point at, so this one is the spare.

## `loose_images/`

Five pictures that were sitting at the top of the study directory. Nothing
references any of them by name.

| File | What it shows |
| --- | --- |
| `a.png` | A plot of the official Stad Gent LOD2 building data within 150 m of Korenmarkt: roof vertices from above, coloured by height, and a cross-section. Roofs are there, facades are not. |
| `aa.png` | A three-panel plot arguing that voxel remeshing closes the support mesh and is still the wrong move: facade cross-section, normal-error CDF, and face count against error. |
| `abc.png` | A Blender screenshot, close in: rays converging from a source onto the low-poly city mesh. |
| `network.png` | A Blender screenshot, further out: the same mesh with the `support_mesh` collection selected and the source markers scattered around. |
| `Screenshot 2026-08-02 222854.png` | A Blender screenshot: an orange ray fan spreading up from one standpoint over a city skyline. |

## `semantic_twin_loose/`

Two files that were loose at the top of `semantic_twin/`.

| File | Why it is here |
| --- | --- |
| `korenmarkt_remesh_comparison.blend1` (119 MB) | A Blender autosave. The `.blend` it backs up no longer exists, and nothing references it. |
| `texput.log` | The log pdfTeX writes under its fallback job name when it cannot find the file it was asked to build. Left over from an aborted run on `methods.tex`. |

## `third_party/`

`The_City_Generator_2.6 1.zip` (259 MB) is a Blender add-on written by someone
else, holding a 565 MB `City_Generator2.0.blend`. It is not study output and
nothing in the tree refers to it.
