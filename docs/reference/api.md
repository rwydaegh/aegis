# API reference

Auto-generated from source code. See the [user guide](../user_guide/overview.md) for usage examples.

## Core

### DosimetryEngine

::: aegis.engine.DosimetryEngine
    options:
      show_root_heading: true
      show_source: true
      members_order: source

### DosimetryResult

::: aegis.result.DosimetryResult
    options:
      show_root_heading: true
      show_source: true
      members_order: source

### PropagationPaths

::: aegis.paths.PropagationPaths
    options:
      show_root_heading: true
      show_source: true
      members_order: source

### Precoder

::: aegis.precoder.Precoder
    options:
      show_root_heading: true
      show_source: true
      members_order: source

## Tissue

### TissueModel

::: aegis.tissue.dielectric.TissueModel
    options:
      show_root_heading: true
      show_source: true
      members_order: source

### Fresnel coefficients

::: aegis.tissue.fresnel
    options:
      show_root_heading: true
      show_source: true
      members_order: source
      filters:
        - '!^_'

### Cole-Cole model

::: aegis.tissue.cole_cole
    options:
      show_root_heading: true
      show_source: true
      members_order: source
      filters:
        - '!^_'

### IT'IS database

::: aegis.tissue.database
    options:
      show_root_heading: true
      show_source: true
      members_order: source
      filters:
        - '!^_'

## Geometry

### BodyMesh

::: aegis.geometry.mesh.BodyMesh
    options:
      show_root_heading: true
      show_source: true
      members_order: source

### Mesh utilities

::: aegis.geometry.mesh.load_stl_binary
    options:
      show_root_heading: true
      show_source: true

::: aegis.geometry.mesh.triangle_areas
    options:
      show_root_heading: true
      show_source: true

### Projected area

::: aegis.geometry.projected_area
    options:
      show_root_heading: true
      show_source: true
      members_order: source
      filters:
        - '!^_'

### Directivity and spherical harmonics

::: aegis.geometry.directivity
    options:
      show_root_heading: true
      show_source: true
      members_order: source
      filters:
        - '!^_'

### Ambient occlusion

::: aegis.geometry.occlusion
    options:
      show_root_heading: true
      show_source: true
      members_order: source
      filters:
        - '!^_'

### Spatial averaging

::: aegis.geometry.averaging
    options:
      show_root_heading: true
      show_source: true
      members_order: source
      filters:
        - '!^_'

### Cauchy formula

::: aegis.geometry.cauchy
    options:
      show_root_heading: true
      show_source: true
      members_order: source
      filters:
        - '!^_'

## Kernels

### Level 0: worst-case bound

::: aegis.kernels.level0_bound
    options:
      show_root_heading: true
      show_source: true
      members_order: source
      filters:
        - '!^_'

### Level 1: aggregate

::: aegis.kernels.level1_aggregate
    options:
      show_root_heading: true
      show_source: true
      members_order: source
      filters:
        - '!^_'

### Level 2: geometric

::: aegis.kernels.level2_geometric
    options:
      show_root_heading: true
      show_source: true
      members_order: source
      filters:
        - '!^_'

### Level 3: Fresnel

::: aegis.kernels.level3_fresnel
    options:
      show_root_heading: true
      show_source: true
      members_order: source
      filters:
        - '!^_'

### Level 4: polarisation

::: aegis.kernels.level4_polarisation
    options:
      show_root_heading: true
      show_source: true
      members_order: source
      filters:
        - '!^_'

### Level 5: curvature

::: aegis.kernels.level5_curvature
    options:
      show_root_heading: true
      show_source: true
      members_order: source
      filters:
        - '!^_'

### Level 6: diffraction

::: aegis.kernels.level6_diffraction
    options:
      show_root_heading: true
      show_source: true
      members_order: source
      filters:
        - '!^_'

### Level 7: coherent

::: aegis.kernels.level7_coherent
    options:
      show_root_heading: true
      show_source: true
      members_order: source
      filters:
        - '!^_'

### Level 8: ECBF

::: aegis.kernels.level8_ecbf
    options:
      show_root_heading: true
      show_source: true
      members_order: source
      filters:
        - '!^_'

## Coherent module

### Fresnel operator

::: aegis.coherent.fresnel_operator
    options:
      show_root_heading: true
      show_source: true
      members_order: source
      filters:
        - '!^_'

### Field channel

::: aegis.coherent.field_channel
    options:
      show_root_heading: true
      show_source: true
      members_order: source
      filters:
        - '!^_'

### Body channel

::: aegis.coherent.body_channel
    options:
      show_root_heading: true
      show_source: true
      members_order: source
      filters:
        - '!^_'

### Exposure operator

::: aegis.coherent.exposure_operator
    options:
      show_root_heading: true
      show_source: true
      members_order: source
      filters:
        - '!^_'

### ECBF solver

::: aegis.coherent.ecbf
    options:
      show_root_heading: true
      show_source: true
      members_order: source
      filters:
        - '!^_'

## Optimization

### Loss functions

::: aegis.optim
    options:
      show_root_heading: true
      show_source: true
      members_order: source
      filters:
        - '!^_'

## Constants

::: aegis.constants
    options:
      show_root_heading: true
      show_source: true

## Compliance

::: aegis.compliance
    options:
      show_root_heading: true
      show_source: true
      members_order: source
      filters:
        - '!^_'

## Integration

### DiffeRT bridge

::: aegis.integration.differt
    options:
      show_root_heading: true
      show_source: true
      members_order: source
      filters:
        - '!^_'

### Sionna RT bridge

::: aegis.integration.sionna
    options:
      show_root_heading: true
      show_source: true
      members_order: source
      filters:
        - '!^_'
