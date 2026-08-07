# Model parameter inventory

[`config/model_parameters.yaml`](../config/model_parameters.yaml) is the
machine-readable inventory of configuration-like numbers found in the semantic
twin. It is an inventory only. It does not change current Python defaults.

Review date: 2026-08-07.

Each YAML entry records its current value, units, source symbol or CLI option,
scope, status, effect on published results, and known conflicts. The table below
is its review index. Explanatory notes live only in this Markdown table. They are
not YAML entry fields. The table groups values into transport, source
construction, walk, illumination, materials, geometry, QA, study profiles,
runtime, visualisation, site scenarios, and the semantic catalogue.

## Reading the statuses

- `canonical`: the present main owner for a production setting or source table.
- `default`: a module or CLI default that can change a result when it is used.
- `diagnostic`: used for validation, convergence, or a study figure.
- `legacy`: retained only for an older API or manifest.

## Scope and limitation

This is a targeted inventory assembled from earlier audits. The earlier audit
reported 214 Python files and 19 JSON configuration files, but this document
does not claim that every current source file has been manually reviewed. The
latest pass directly reviewed the two Sionna transport modules, four Sionna CLI
modules, five Sionna figure scripts, and the final sealed exposure manifest. The
YAML currently contains 80 parameter entries.
Generated manifests are evidence of a run. They do not become executable
defaults.

The inventory intentionally excludes generated numerical payloads. These
include mesh vertices, tile counts, byte counts, ray outputs, recorded site
measurements, and golden expected values. The inventory references those files
where they contain scenario provenance, but does not restate each generated
number as a parameter.

Four JSON tables are retained as authoritative numeric tables by reference:

- `config/itu_p2040_4.json` for dielectric and uncertainty values.
- `config/vegetation_p833.json` and `config/surface_roughness.json` for material
  evidence and priors.
- `config/masonry_scattering.json` for masonry geometry and band response.

`config/semantic_concepts.json` is also a parameter table. Its probabilities
are scientific priors for material binding, not display metadata.

The two angular convergence configurations are also covered. They point to the
sealed `pilot_korenmarkt_walk_drjit_atlas_v2` exposure target. That target is
present as output generation `9d5600364cae4a0b937e5c36e74e2b8b`, created at
`2026-08-05T15:46:57Z` from run digest `6020e8d74e9c`. Its manifest SHA-256 is
`15b06e1a5952de41c0ccb5dd33216bd9fec06eb682a3f63aa79a2f45d249f0ae`.
The recorded and measured hashes agree for the 24,159-byte locations file
(`59875937573fdd8b597be25760e67f7cea216bcb5c414be169e8bfe255527934`)
and the 58,658-byte spectra file
(`b9b611e179e2784620dab4a47db8ac5fddc56e063670659ae5aa006adcc81d88`).
The manifest also binds the atlas NPZ
(`c452c34e1d9422022d55fc758d228c22a39b80d9a770042e89e13f9110f43a76`),
its JSON sidecar
(`80d8f0bb448d6677fc29c9c51e81036e9b54913d52f1480030095ac16f08d783`),
and the support mesh
(`bfbdba0657a1dd4b8b819e7e611dbfd4eea919e5c08538078ff1948599957264`).
This reference contains 13 traced locations at 200000 rays and 512 angular
cells. It is the convergence input, not the sealed 4096-cell high-resolution
exposure. The repaired runner writes schema-v2 analysis into separate
`initial_seeds` and `extended_seeds` directories. Raw traces remain shared
under `runs`. The old root-level schema-v1 files remain historical.

The separately listed v1 exposure triple and the old Blender bundle predate the
integrity seals. They remain historical provenance. The current atlas hash is
bound by both the convergence reference and the high-resolution exposure
manifest.

Production semantic evidence enforces three exact SAM-side identities. The SAM
3 weights revision is
`3c879f39826c281e95690f02c7821c4de09afae7`. The installed SAM 3 source commit
is `96914d2425f90a64f45ca977c2b5165418099543`. The canonical semantic catalogue
digest is
`66d0dfefba87bde5081cfa82108ca60d47c79cf641df3ec44129ec20bb90453b`.
Production rejects another immutable weights/source pair. It also rejects a
catalogue edit that preserves the 60 prompts and 61 raster IDs.

The high-resolution Blender input exposure is present as generation
`2a77cecc897f4177b1c5938866a26264`, created at `2026-08-05T16:03:35Z` from run
digest `af8b9fc7cf3e`. Its manifest SHA-256 is
`e87bd8e5db0308cfa9ad445c179a8464b19a7aaa8eaf2242fb1492c0eee75a9d`.
The recorded and measured hashes agree for the 24,176-byte locations file
(`66b4e5c70494dc653a8d99ab33d4551fac99d70029114995ef9523d831e34534`)
and the 457,258-byte spectra file
(`1186e952d4edc65046e69940a54c1024cb29c1fee6e6ae72acbe95b76f59b90b`).
The run has 13 locations, 1600000 rays per standpoint, 4096 angular cells, a
400000-ray batch, seed 7, and the CUDA DrJit transport kernel. It binds the same
atlas and support-mesh hashes as the convergence reference. Its stored spectrum
is available as the high-resolution Blender input. The exporter still requires
this production stem or the three exact paths, so the exposure artifacts alone
do not prove that a Blender bundle has been rebuilt from them. The 512-cell,
200000-ray convergence reference remains a separate sealed generation.

## Highest-priority consolidation work

The current code has deliberate study variants, but they are easy to confuse
with production defaults. The main conflicts are crop radius, ray count, bounce
budget, seed, source angular resolution, and semantic confidence gates. The
inventory lists each current value without resolving it. A later refactor should
add named profiles and separate acquisition, support-mesh, trace, semantic, and
display radii.

## Review index

The values below are compact groups. Each row points to exact owners in the
YAML. "Science" means a change can alter a reported physical result. "Conditional"
means it changes results only when that mode or study is selected.

| Entry | Value and units | Exact owner | Scope | Status | Science | Conflict or duplicate | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Transport crop | 250 m | `RunConfig.crop_m` | production trace | canonical | yes | 130, 140, 200, 250 m roles | Trace crop, not acquisition radius. |
| Transport frequency | 15e9 Hz | `RunConfig.frequency_hz` | propagation | canonical | yes | none | Main study band. |
| Comparable-city v2 transport | 250 m, 15 GHz, 200000 IID rays, 4096 passive output cells, exact direct, stochastic diffuse/mixed next-event, adaptive order-1 all-specular plus sampled mixed suffix, 120000000 logical candidates, 262144 chunk, 0.02 tolerance, one suffix sample with offset 2000, finish-only roughness, physical 3D edge-length baseline, level-2 body | `parameters.study_transport.comparable_city_v2_production` | comparable production transport and coupling | canonical | yes | horizontal projected edge length is a sensitivity; 4096 cells are not launch bins | Current contract aggregate. |
| Bounce budget | 3 interactions | `RunConfig.max_bounces`, `DEFAULT_MAX_BOUNCES` | propagation | canonical | yes | studies use 4 and order 8 | Evidence-led hard cap. |
| Roulette and ray lift | 0.05 probability, 0.001 m | `RunConfig.roulette_floor`, `.ray_epsilon_m` | transport | canonical | conditional/yes | tracer defaults match | Roulette is inactive at shipped cap. |
| Sampling | 200000 rays, 400000 batch, 512 cells, 18 bands, seed 7 | `RunConfig.{rays,batch,local_cells,exit_bands,seed}` | production Monte Carlo | canonical/default | yes | generic 512-cell grid is a default. The roofline pilot uses 4096 cells. Direct tracer uses 400000 and seed 0 | Batch changes seeded draws above one batch. |
| Atlas interface decision | strict posterior greater than 0.5 | `atlas_binding.py:MIN_INTERFACE_POSTERIOR` | atlas material transport | canonical | yes | an exact 0.5 tie uses geometric fallback | Prevents a small residual material mass from becoming certain after excluded channels are removed. |
| Direct tracer defaults | 15e9 Hz, 400000 rays, 512 cells, 18 bands, 3 bounces, seed 0 | `TraceConfig` | direct API | default | yes | differs from RunConfig | Retained callable API profile. |
| Next-event gather | 0.5 m, 1 sample, order 8, 0.001/0.01 m, offset 1000 | `next_event.py` gather constants | source connection | default | yes | order exceeds trace cap | Connection estimator settings. |
| Monostatic | order 8, 2/600/400 m, gain 1, 0.002 m, 20001 samples | `monostatic.py` | monostatic study | default | yes | distinct diagnostic model | Not main exposure transport. |
| Source construction default | 128+16 views, 1440x600, 1 m, 3D, 0.5 m, one connection | `NextEventConfig` | source construction | default | yes | the roofline pilot locks builders and held-out to 1 and uses every declared route point. Skyline and diffraction grids differ | Held-out views prevent self-scoring in this default profile. |
| Source diagnostics | skyline 720x400, diffraction 720x600, silhouette 360/720/1440x600 | relevant CLI flags | source studies | default/diagnostic | conditional | intentional grid variants | Resolution studies, not one shared default. |
| Walk and recorder | 90 m, 3 m, 6 m, 1.5 m, recorder 2000 paths and 400 m sky | `RunConfig`, `PathRecorder` | observers | canonical/diagnostic | yes/no | exports use 60 m | Recorder is visual evidence only. |
| Illumination bands | roof 13.5-43.5 m at 25-250 m, street 2.5-6.5 m at 10-150 m | `catalogue.py` | source law | canonical | yes | none | Physical deployment prior. |
| Illumination numerics | 200001 quadrature samples, -90 to 90 deg | `model.py` | normalisation | default | yes | none | Numerical integral resolution. |
| Roofline model | 0.05-85 deg, 0.05/2/3/0.5 m | `roofline.py` | roofline sources | default | yes | none | Geometry gates and offsets. |
| Antenna | 65 deg beams, 30 dB limits, 8 dBi, 8x8 at half wavelength | `antenna.py` | antenna gain | canonical | yes | scenario tilts vary | 3GPP-style element and array. |
| Antenna numerical and scenarios | interpolation 1201x361, chunks, tilts 102/96 deg and sweeps | `antenna.py` | antenna studies | default | yes | none | Integration and study choices. |
| Material tables | ITU P.2040, P.833, roughness, masonry tables | four `config/*.json` tables | RF material model | canonical | yes | extrapolation noted per table | Whole numeric tables retained by reference. |
| Vegetation routing | strict posterior greater than 0.5, grass keeps geometric ground, woody canopy is nonblocking until closed volume geometry exists | `atlas_binding.py`, `vegetation_transport.py` | atlas transport | canonical | yes | no validated grass layer or current canopy chords | Vegetation evidence never becomes wood, vacuum, or an opaque support triangle. |
| P.833 path chords | 30 MHz-100 GHz recommendation, 1.3-61.5 GHz RET tables, 64-character geometry hash, watertight positive chords, extrapolation off | `vegetation_transport.py` | volume transport | canonical | yes | current atlas has no chord geometry | Entry and exit points determine length. Every complete species row remains separate. |
| Foliage and bodies | 0.0002 m leaf, body spacing/radii, 600-face quadric remesh with fast-simplification 0.1.13 | `foliage.py`, `bystander_geometry.py`, `pyproject.toml` | material/bystander | canonical/default | yes | none | Includes body-placement geometry and the exact decimator used by the production run. |
| Screening and acquisition | Earth radius 6371008.8 m, 60 m screen, tile limits | `screening.py`, `tiles.py`, `mapillary.py` | site and geometry | default | yes/conditional | none | Admission and acquisition limits. |
| Support mesh | 2 m match, 0.3 m solidify, 1 deg planar gate | `inhouse_mesh_build.py`, `support_remesh.py` | geometry | default | yes | 2 m repeated in showcase | Changes reflected geometry. |
| Camera, fishnet, facade, texture | 90 deg, 1536 px, confidence 0.35, 384 px crops, 140 m texture | named CLI/module settings | evidence | default | yes | 0.35 has two meanings | Separate image stages. |
| Registration and depth | seeds, 1024 bins, 4 deg gate, depth sigma/gates | `register.py`, depth modules, CLI | evidence QA | default | yes | 4 deg repeated | Determines which evidence is accepted. |
| Production semantic identity | 60 prompts, 61 raster IDs including ID 0, exact SAM 3 weights, source, and catalogue digests above, Mask2Former commit `4772b6bf101d91f2534c106dc524d906aeb3c68a` | `semantic_concepts.json`, `vocabulary.py`, `prompted.py`, `dense.py`, `build_surface_atlas.py` | semantic evidence | canonical | yes | another immutable SAM pair or same-count catalogue edit is refused | Mask2Former verifies the reviewed snapshot, then loads processor and weights from that local snapshot only. Production uses an explicitly selected versioned panorama directory. |
| Semantic session parity | A6000 live parity, independent p00 116.981 s, shared p00+p01 199.228 s, scientific arrays exact | `parameters.registration_and_depth_qa.semantic_session_parity` | semantic session reuse validation | diagnostic | no | measured validation anchor, not a universal timing claim | Exact fields include scientific panorama arrays, concept-cache arrays, prompt gate, and normalized metadata. |
| Main and next-event CLIs | 250 m, 200000 rays, 15 GHz, seed 7 and source inputs | `run_exposure.py`, `run_next_event.py` | study launch | default | yes | mirrors RunConfig | CLI front doors. |
| Roofline sampled-specular pilots and paired campaign | Pilot code `0844eadde0308ff8dfeda7142ec3903165f5a053`. Korenmarkt and Prague, 250 m crop, atlas, full panorama-link route, route-tangent yaw, 200000 rays, 400000 batch, 4096 cells, 15 GHz, seed 7, curve 1e-4 m, top-edge tolerance 0.25 m, specular order exactly 1, candidate budget 120000000, chunk 262144, relative tolerance 0.02, sampled suffix one sample per eligible diffuse vertex with offset 2000. Paired config commit `b985ab58` uses IID and Fibonacci modes, seeds 7-22, and looks 4, 8, 12, and 16 | `config/roofline_campaign_*_pilot_cuda_sampled_specular.json`, `config/roofline_campaign_*_convergence_cuda_{iid,rotated_fibonacci}.json`, `semantic_twin/exposure/roofline_setup.py`, `semantic_twin/walk/orientation.py` | committed roofline body-exposure pilots and paired sampling campaign | diagnostic | yes | max_bounces=3 is a transport interaction cap, not three specular reflections. Higher specular orders are absent | Korenmarkt and Prague one-seed CUDA pilots passed independent audits. Korenmarkt and Prague paired campaigns passed full audit. Prague has 49 hash-valid manifest entries per mode, seeds 7-22, 68x56024 body arrays, and no orphan files. Fibonacci is not adopted. See [roofline campaign results](ROOFLINE_CAMPAIGN_RESULTS.md). |
| Diagnostic CLIs | crop, bounce, monostatic, substreet, foliage profiles | named scripts | diagnostics | diagnostic | conditional | ray and seed variants | Must not replace production profile. |
| Angular convergence | schema v2, sealed reference generation `9d5600364cae4a0b937e5c36e74e2b8b`, production 512-4096 cells, 200000-1600000 rays, seeds 7-10 or 7-14, quick 32-64 cells, 1000-2000 rays, seeds 7-8 | convergence JSON and `angular_convergence.py` | atlas-bound convergence | diagnostic | conditional | the sealed reference is 512 cells and 200000 rays, root-level schema-v1 files are historical | Initial and extended seed results have separate directories and share raw runs. |
| Matched Sionna transport | PEC-like material, diffuse share 1, depth 3, 200000 forward samples per source, 200000 adjoint rays, 4 seed helper ensembles | `sionna_forward.py` and `PEC_PERMITTIVITY` | forward-versus-adjoint validation | diagnostic | conditional | CLI seed counts, chunks, and path buffers differ | Both solvers disable the unmatched path mechanisms. |
| Sionna open square | 200 m ground half-width, walls at 40 m, 20 m high, 27 facade-tip sources, 6 fixed receivers | `sionna_forward.py:open_square_environment` | controlled geometry | diagnostic | conditional | city mode uses real geometry, 32 sources, and 4 receivers | Exact receiver coordinates remain in the YAML. |
| Forward Sionna CLI | open square default, city defaults at Korenmarkt 250 m, depth 3, 200000 samples or rays, 8 adjoint and 4 Sionna seeds | `cli/sionna_forward.py` | validation command | diagnostic | conditional | source chunk 8 overrides helper default 16 | City selection and seed offsets are recorded separately from the helper defaults. |
| Sionna source scaling | 3-729 sources, 6 receivers, 50000 adjoint rays, 8/6 seeds, fixed 20000 per source or 1350000 total samples | `cli/sionna_scaling.py` | scaling diagnostic | diagnostic | conditional | fixed-total samples floor at 256, path buffer is 1000000 | The first timed seed is excluded from warmed timing. |
| Adjoint ray budget | 2187 sources, 6 receivers, 5000-100000 rays, 8 seeds, one connection, depth 3 | `cli/adjoint_budget.py` | ray-budget diagnostic | diagnostic | conditional | forward validation defaults to 200000 rays | This is a controlled production-like source ratio. |
| Deterministic first bounce | 64 kernel subdivisions, CLI sweep 16-128, 27 sources, 6 receivers, 15 GHz, 1 mm ray lift and 1 cm connection lift | `deterministic_reference.py`, `cli/deterministic_first_bounce.py` | independent one-bounce reference | diagnostic | conditional | one interaction only, CLI overrides subdivision count | Generated quadrature answers are excluded from the inventory. |
| Sionna figure selection | 50k/100k controlled budgets, depths 1-3, 200k city budget, 1 mm-10 cm lift sweep, 3k/6k full-city budgets, 0.1 dB rules | five `make_sionna_*.py` scripts | figure input and runtime reduction | diagnostic | no | values select generated experiments, they are not solver defaults | Runtime plots drop one seed and use warmed time times median variance. |
| Blender input exposure | sealed generation `2a77cecc897f4177b1c5938866a26264`, 4096 cells, 1600000 rays, 400000 batch, seed 7, CUDA DrJit | high-resolution exposure manifest and Blender input validator | high-resolution exposure and available Blender input | canonical | yes | convergence reference remains 512 cells and 200000 rays | The exposure triple is verified. A rebuilt Blender bundle is not asserted here. |
| Sealed exposure output | format 1, 32-character generation ID, hashed locations and spectra, manifest committed last | `execution.py`, `reuse.py`, `angular_convergence.py`, Blender `exporter.py` | output publication | canonical | no | old or mixed triples have no valid seal | Reuse, angular convergence, and Blender export require the same sealed locations, spectra, and manifest generation. |
| Comparable runtime anchors | Korenmarkt cold one-seed 155.73 s, warm two-seed total 147.79 s for 13 points; Prague dry 47.96 s for 68 points, full cold 2063.05 s with 1584.75 s deterministic all-specular, 308.66 s stochastic transport, and 119.95 s body coupling | `parameters.runtime_and_visualisation.comparable_runtime_anchors` | measured implementation timing | diagnostic | no | measured stage anchors, not free runtime parameters | Values are hardware-specific observations. |
| GPU and runtime | parity 200000 rays, fixed seed, tolerances, network and solver budgets | `gpu_parity.py`, acquisition and masonry CLIs | QA/runtime | diagnostic/default | no/conditional | local cells 256 in parity | Parity checks implementation. |
| Visualisation | Blender radii, 64/96 samples, image dimensions | render CLIs | presentation | default | no | display radii differ | No physical result change. |
| Blender bundle identity | bundle schema v1, 64-character shared identity, payload plus manifest | `viz/blender/payload.py`, `exporter.py` | artifact publication | canonical | no | old unstamped pairs are historical | Crossed or partially replaced pairs are rejected. |
| Blender evidence family | check 250 m v2, fused, then unversioned, require one mesh, pose, view set, and image shape | `viz/blender/exporter.py` | evidence display | canonical | no | an incomplete first existing family stops selection | The selected fishnet names its matching mesh-depth directory. Incompatible optional layers are excluded. |
| Comparable-city v2 contract | Ten intended sites, nine panorama acquisitions, Krakow quota-pending, all primary materials atlas, registered-span street v1 route, 90 m radius and 6 m stride, Times Square excluded | `parameters.study_transport.comparable_city_v2_contract` | cohort membership and route contract | canonical | yes | does not duplicate per-site scenario JSON | Readiness remains an independent gate before execution. |
| Site scenarios | all location, crop, frequency, geometry, screening leaves | 11 site JSON files | site provenance | canonical | yes | several radius meanings | Keep per-site records distinct. |
| Semantic catalogue | material priors and attributes | `semantic_concepts.json` | material binding | canonical | yes | priors are not confidence scores | Image labels map to RF materials. |
| Historical atlas production provenance | 250 m, 15 GHz, 200000 rays, 512 cells, seed 7, 13 traced locations, 8x8 atlas | old `joint_atlas_250m_r8` and `pilot_korenmarkt_walk_drjit_atlas_v1_15ghz` files | pre-repair record | legacy | conditional | atlas lacks pinned versioned semantics, exposure lacks `output_generation` | Kept for provenance. Rebuild before current convergence or Blender work. |
| Golden fast provenance | 130 m, 50000 rays, 512 cells, seed 7 | `tests/golden/MANIFEST.json` | regression record | legacy | conditional | differs from production | Retained as a fast regression case. |

## Coverage check

Run the following from this directory. It parses the YAML and checks that every
machine-readable parameter entry has all required fields. The final `80` is the
current entry count.

```bash
python3 - <<'PY'
import yaml

data = yaml.safe_load(open("config/model_parameters.yaml"))
required = set(data["inventory"]["fields"])
assert required == {
    "value",
    "units",
    "source",
    "scope",
    "status",
    "affects_published_results",
    "conflicts",
}
entry_without_conflicts = required - {"conflicts"}
allowed = {"canonical", "default", "diagnostic", "legacy"}
entries = []

def walk(value):
    if isinstance(value, dict):
        if entry_without_conflicts <= value.keys():
            assert required <= value.keys(), value
            entries.append(value)
        else:
            for child in value.values():
                walk(child)

walk(data["parameters"])
assert entries and all(required <= entry.keys() for entry in entries)
assert {entry["status"] for entry in entries} <= allowed
assert len(entries) == 80
print(f"YAML parsed, {len(entries)} parameter entries covered")
PY
```
