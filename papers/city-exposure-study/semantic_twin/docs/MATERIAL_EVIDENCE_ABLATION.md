# Material evidence ablation

## Question

The current ablation is **atlas evidence layer versus geometric fallback**. It
tests the effect of the panorama-derived material layer within the current
first-material-interaction contract. It is not a reflectance-only test. It does
not measure material accuracy.

Madrid and Mexico City provide the pair. Each site uses one completed atlas
campaign and one geometric control. The pair keeps the support mesh, route,
source curve, source weights, seeds, ray count, output cells, body, frequency,
and transport topology fixed.

## Campaigns

The geometric controls are defined by:

- `config/roofline_campaign_madrid_plazamayor_provider_corridor_v1_first_material_interaction_v1_convergence_cuda_iid_geometric_control.json`

- `config/roofline_campaign_mexico_zocalo_provider_corridor_v1_first_material_interaction_v1_convergence_cuda_iid_geometric_control.json`

Run them from the `semantic_twin` package root:

```bash
python -m semantic_twin.cli.roofline_campaign \
  --config config/roofline_campaign_madrid_plazamayor_provider_corridor_v1_first_material_interaction_v1_convergence_cuda_iid_geometric_control.json \
  --persistent-transport-cache outputs/roofline_campaign/_persistent_transport_cache/madrid_plazamayor

python -m semantic_twin.cli.roofline_campaign \
  --config config/roofline_campaign_mexico_zocalo_provider_corridor_v1_first_material_interaction_v1_convergence_cuda_iid_geometric_control.json \
  --persistent-transport-cache outputs/roofline_campaign/_persistent_transport_cache/mexico_zocalo
```

The persistent cache is an optional runtime optimization. It is not part of
the campaign identity.

## Closed pair identity

The reporter authenticates the campaign manifests and every committed shard.
It then requires exact route rows, seeds, component schema, topology, and all
identity values outside this allowlist:

- `/configuration/material_mode`

- `/materials`

- `/transport/tracer/atlas_material`

- `/transport/tracer/face_class_sha256`

- `/transport/tracer/permittivity_sha256`

- `/transport/tracer/rms_height_sha256`

- `/transport/estimator/configuration/specular_transport/material_class_sha256`

- `/inputs/bytes`

- `/inputs/file_count`

- `/inputs/files[run_config]`

- `/inputs/files[atlas_npz]`

- `/inputs/files[atlas_json]`

The input file exceptions are also closed. The reporter accepts one site and
mode-specific roofline config in each campaign. It accepts one joint atlas JSON
and one joint atlas NPZ only in the atlas campaign. Any other identity drift is
a refusal.

This rule keeps the mesh hashes, route position and yaw hashes, provider
selection, source curve, body, point-seed algorithm, frequency, ray count,
batch size, output cells, device kernel, topology, component names, and
convergence looks exact.

## Report

After both controls complete, write one report per site:

```bash
python -m semantic_twin.cli.material_evidence_ablation \
  outputs/roofline_campaign/madrid_plazamayor_provider_corridor_v1_first_material_interaction_v1_convergence_cuda_iid \
  outputs/roofline_campaign/madrid_plazamayor_provider_corridor_v1_first_material_interaction_v1_convergence_cuda_iid_geometric_control \
  --output outputs/roofline_campaign/material_evidence_ablation/madrid_plazamayor

python -m semantic_twin.cli.material_evidence_ablation \
  outputs/roofline_campaign/mexico_zocalo_provider_corridor_v1_first_material_interaction_v1_convergence_cuda_iid \
  outputs/roofline_campaign/mexico_zocalo_provider_corridor_v1_first_material_interaction_v1_convergence_cuda_iid_geometric_control \
  --output outputs/roofline_campaign/material_evidence_ablation/mexico_zocalo
```

Each report contains:

- pointwise and route q10, q50, and q90 changes for total transfer and
  normalized whole-body SAR

- direct, all-specular, first-diffuse, and total component changes

- direct-visible, zero-direct, and discordant direct-visibility strata

- paired seed uncertainty from complete route shards

- observed estimator and body-coupling time

- JSON, CSV, PDF, PNG, and a SHA-256 artifact manifest

The dB change is $10\log_{10}(x_{\mathrm{atlas}} / x_{\mathrm{geometric}})$.
It is undefined when either paired value is zero. The JSON records those cases
separately instead of replacing them with a floor.

## Paper claim

This experiment supports a sensitivity statement only. A small change would
show that the reported route endpoints are insensitive to replacing the atlas
evidence layer with the geometric fallback under this source and interaction
model. A large change would show that the evidence layer matters for those
endpoints. Neither outcome validates the assigned materials against ground
truth.
