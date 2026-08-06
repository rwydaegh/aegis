# Command status

This page is the command map for `semantic_twin/`. It covers all 69 Python
files at the study root. A root file may remain for published notebooks and
old captures even when its implementation has moved into the package.

## Status definitions

| Status | Meaning |
|---|---|
| Production | Part of the normal path for current study results. |
| Supported wrapper | A published or useful command with a stable compatibility entry point. Its parser and `main` function live in `semantic_twin/cli/`. |
| Diagnostic | A scientific probe, convergence run, ablation, calibration, or comparison. It informs method choices or checks results. It does not write headline results by default. |
| Manual utility | An explicit preparation, inspection, rendering, plotting, or reporting tool. It is run when that artifact is needed. |
| Archive candidate | A historical entry point with a current replacement. Keep its history, but do not use it for new acquisition. |

## All root commands

| Root command | Status | Role |
|---|---|---|
| `analyse_material_vlm.py` | Diagnostic | Score material VLM evidence against the fixed prior. |
| `benchmark_walk_body.py` | Supported wrapper | Benchmark separate and batched body coupling. |
| `blind_facade_crops.py` | Manual utility | Blind facade crops before model review. |
| `bound_diffraction.py` | Diagnostic | Bound the possible diffraction contribution. |
| `build_dynamic_bodies.py` | Manual utility | Place SAM 3D Body reconstructions in scene coordinates. |
| `build_facade_crops.py` | Manual utility | Build matched facade crops from panorama and tile textures. |
| `build_fishnet_surface.py` | Manual utility | Build a visible fishnet semantic surface. |
| `build_inhouse_mesh.py` | Manual utility | Convert downloaded 3D Tiles to a local ENU mesh. |
| `build_propagation_blends.py` | Production | Build the propagation Blender bundles for study sites. |
| `build_site_config.py` | Manual utility | Write a screened-site scene configuration. |
| `build_site_fishnets.py` | Manual utility | Run fishnet projection over registered panoramas. |
| `build_site_semantics.py` | Production | Fuse registered panoramas into site semantic posteriors. |
| `build_surface_atlas.py` | Supported wrapper | Build the all-camera semantic and material atlas. |
| `build_texture_evidence.py` | Manual utility | Build and assess texture-based material evidence. |
| `build_walk_twin.py` | Manual utility | Build a panorama-walk twin and report its evidence. |
| `check_gpu_parity.py` | Supported wrapper | Compare CPU and CUDA SBR paths. |
| `compare_mesh_depth.py` | Supported wrapper | Compare monocular depth with support-mesh first hits. |
| `crop_fused_semantics.py` | Manual utility | Cut rectilinear maps from fused panorama semantics. |
| `download_inhouse_tiles.py` | Supported wrapper | Acquire and cache Google Photorealistic 3D Tiles. |
| `download_mapillary_panoramas.py` | Archive candidate | Older selected-panorama acquisition helper. The route-based fetch command supersedes it. |
| `export_propagation_payload.py` | Supported wrapper | Export a sealed propagation payload for Blender. |
| `fetch_site_panoramas.py` | Production | Fetch a spatially spread, registered site panorama set. |
| `infer_depth_anything.py` | Manual utility | Run Depth Anything V2 on panorama crops. |
| `infer_sam3_body.py` | Manual utility | Reconstruct people from panorama crops. |
| `infer_unidepth.py` | Manual utility | Run UniDepthV2 on perspective crops. |
| `make_city_sheet.py` | Manual utility | Compose the acquired-city comparison sheet. |
| `make_remesh_panel.py` | Manual utility | Compose the support-mesh remeshing panel. |
| `make_sensitivity_study.py` | Diagnostic | Run the illumination sensitivity study. |
| `make_vlm_batches.py` | Manual utility | Write material VLM batch inputs and prompts. |
| `measure_bounce_evidence.py` | Diagnostic | Measure image-evidence coverage by bounce budget. |
| `measure_city_metrics.py` | Manual utility | Measure sky fraction and skyline height for city comparisons. |
| `measure_near_clutter.py` | Diagnostic | Measure the near-clutter contribution. |
| `measure_skyline.py` | Diagnostic | Measure the recovered skyline function. |
| `measure_source_silhouette.py` | Diagnostic | Measure source-silhouette coverage. |
| `measure_surplus_spread.py` | Diagnostic | Measure next-event seed-to-seed surplus spread. |
| `plot_crop_convergence.py` | Manual utility | Plot crop-radius convergence outputs. |
| `plot_masonry_grating.py` | Manual utility | Plot masonry-grating study outputs. |
| `plot_material_vlm.py` | Manual utility | Plot material VLM evidence and ablations. |
| `plot_skyline_function.py` | Manual utility | Plot panorama, mesh, and ray-traced skyline functions. |
| `project_semantics.py` | Manual utility | Label one support mesh from one panorama and export a scene. |
| `propagation_blender.py` | Supported wrapper | Build a propagation walkthrough blend from a sealed payload. |
| `qa_propagation_blend.py` | Manual utility | Audit a propagation blend against source data. |
| `raycast_mesh_depth.py` | Manual utility | Render support-mesh first-hit ranges from a panorama camera. |
| `remesh_support_mesh.py` | Manual utility | Remesh and decimate a support mesh in Blender. |
| `render_blender_alignment.py` | Manual utility | Render photogrammetry from a recovered panorama camera. |
| `render_city_gallery.py` | Manual utility | Render comparable establishing views for acquired cities. |
| `render_showcase.py` | Manual utility | Render configured semantic-twin showcase views. |
| `reregister_site.py` | Manual utility | Re-run skyline registration for a site. |
| `run_angular_convergence.py` | Diagnostic | Run angular-cell convergence experiments. |
| `run_cdf_convergence.py` | Production | Run fixed-walk replicas and convergence stopping. |
| `run_crop_convergence.py` | Diagnostic | Run crop-radius convergence experiments. |
| `run_exposure.py` | Supported wrapper | Compatibility entry point for the exposure command. |
| `run_foliage_study.py` | Diagnostic | Compare foliage treatments. |
| `run_law_comparison.py` | Diagnostic | Compare illumination laws. |
| `run_law_ordering.py` | Diagnostic | Compare illumination-law ordering across cities. |
| `run_masonry_grating.py` | Diagnostic | Run the masonry grating study. |
| `run_masonry_spectrum.py` | Diagnostic | Run the rigorous masonry spectrum study. |
| `run_material_ablation.py` | Diagnostic | Trace a walk under alternative material models. |
| `run_monostatic.py` | Diagnostic | Run the co-located return study. |
| `run_next_event.py` | Supported wrapper | Compatibility entry point for the explicit next-event study. |
| `run_seed_replicas.py` | Diagnostic | Replicate fixed standpoints over independent ray seeds. |
| `run_station_calibration.py` | Diagnostic | Run station exposure and first-interaction calibration. |
| `run_substreet_ablation.py` | Diagnostic | Measure the sub-street geometry ablation. |
| `screen_cities.py` | Manual utility | Screen candidate sites before acquisition. |
| `showcase_blender.py` | Manual utility | Render a semantic-twin showcase payload in Blender. |
| `summarise_evidence_coverage.py` | Manual utility | Summarise image evidence by site. |
| `summarise_panorama_routes.py` | Manual utility | Summarise usable connected panorama routes. |
| `summarise_site_panoramas.py` | Manual utility | Summarise per-panorama registration results. |
| `summarise_station_calibration.py` | Manual utility | Summarise station-calibration reports. |

## The normal production path

For a new city or a new result campaign, the normal path is:

1. `fetch_site_panoramas.py` acquires the spatially spread panorama set.
2. `build_site_semantics.py` fuses registered views into semantic evidence.
3. `run_cdf_convergence.py` traces the fixed walk and computes the result replicas.
4. `build_propagation_blends.py` makes Blender bundles when a visual audit is needed.

The fourth step is optional for numerical production. It belongs to the Blender
and audit track. The first three steps produce the data used for results.

## Supported command boundary

Eight root commands received explicit CLI extraction during the refactor:

`benchmark_walk_body.py`, `build_surface_atlas.py`, `compare_mesh_depth.py`,
`download_inhouse_tiles.py`, `export_propagation_payload.py`,
`propagation_blender.py`, `run_exposure.py`, and `run_next_event.py`.

Their reusable work lives in package modules. Their parser and `main` functions
live in `semantic_twin/cli/`. The root files remain compatibility wrappers for
published commands, notebooks, and old captures. `check_gpu_parity.py` was
already a package-side CLI and is listed as a supported wrapper for the same
reason.

## Archive decision

`download_mapillary_panoramas.py` is the one archive candidate in this matrix.
It selects individual panoramas through the older acquisition flow. The current
site workflow uses `fetch_site_panoramas.py`, which acquires a spatially spread
set and records the route and registration state together. Keep the old file's
history and provenance, but do not call it for a new site.

Every other root command has a current role: production, supported wrapper,
diagnostic, or manual utility. There is no unresolved command ownership.
