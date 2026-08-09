# Multicity campaign readiness

> **Current-contract notice.** The earlier two-site readiness snapshot below is
> retained for provenance. For the current comparable-city v2 definition, use
> [CURRENT_PRODUCTION_CONTRACT.md](CURRENT_PRODUCTION_CONTRACT.md): the
> comparable-city v2 contract contains ten intended atlas-backed sites using
> exact cached registered-span pedestrian routes. Nine have panorama
> acquisitions, while Krakow remains pending Street View quota. Each site must
> independently pass input readiness before it is run. Times Square remains
> excluded for invalid geometry. This notice does not claim that all inputs or
> production campaigns are complete.

Everything below this notice is the earlier sealed-readiness snapshot. It is
retained as provenance and must not be read as the current cohort definition.

## Historical decision

Exactly two sites are sealed production-ready now: Korenmarkt and Prague. No
other site is sealed production-ready.

All 11 candidate sites have format-v3 250 m meshes. Mesh existence is therefore
not the main readiness blocker. A mesh does not prove that acquisition, semantic
evidence, route data, geometry, or the campaign contract is ready.

Ten-city results cannot honestly be generated tonight. Eight sites in the
sealed ten-site contract still have a stated gate, and Toulouse is outside that
contract. Never replace a missing material binding or route with a fallback
silently. Any fallback must be an explicit, separately named contract.

## Site gates

| Site or group | Current state | Blocker type | Exact next gate |
| --- | --- | --- | --- |
| Korenmarkt | Sealed production-ready | None | Preserve the sealed inputs and run the declared campaign preflight. |
| Prague | Sealed production-ready | None | Preserve the sealed inputs and run the declared campaign preflight. |
| Brussels, Madrid, Mexico Zocalo, Tokyo | Routes and 250 m meshes exist | Semantic rebuild | Complete hybrid SAM material inference and atlas fusion for each site, then seal the resulting material binding. |
| Krakow | Not ready for the sealed run | Acquisition and route, or contract | Complete the required acquisition and declared route, or explicitly adopt a geometry-grid contract. Record the chosen contract before any run. |
| London | Raw panoramas exist | Registration, semantic rebuild, and route | Register the panoramas, rebuild the semantic evidence, and create and seal the declared route. |
| Milan | Site identity and route need repair, with more coverage required | Acquisition and coverage, identity, and route | Repair the site identity and route, then acquire enough additional coverage for the declared campaign contract. |
| Times Square | Scientifically invalid mirror-glass and sub-street geometry | Geometry | Do not run. Replace or repair the geometry and pass a new scientific geometry review before reconsidering admission. |
| Toulouse | Outside the sealed ten-site contract | Contract | Take no campaign action under the current contract. Re-entry requires an explicit contract change and a separate readiness review. |

## Gate order by cohort

### Ready cohort

Korenmarkt and Prague are the only sites that may proceed to the sealed
production preflight now.

### Semantic completion cohort

Brussels, Madrid, Mexico Zocalo, and Tokyo already have routes and 250 m meshes.
Their remaining gate is the material evidence path: hybrid SAM material
inference followed by atlas fusion and a sealed material binding. Do not report
their routes or meshes as production readiness before that semantic gate closes.

### Recovery cohort

Krakow, London, and Milan require site-specific recovery before admission:

- Krakow needs acquisition and route completion, unless the study explicitly
  adopts a geometry-grid contract.
- London needs panorama registration, semantic rebuild, and route completion.
- Milan needs identity and route repair plus additional coverage.

Each site must have its chosen route and evidence contract recorded before it is
run.

### Excluded or hard-blocked sites

Times Square is hard-blocked on scientifically invalid geometry. It must not be
run while mirror-glass and sub-street geometry remain unresolved.

Toulouse is not a spare site for the ten-city contract. It remains outside the
contract until an explicit change admits it and its own gates are reviewed.

## No silent substitutions

The campaign identity must name the actual material evidence, route, geometry,
and contract used for every site. A geometric material prior, geometry grid, or
synthetic route may be used only when the campaign explicitly declares that
contract. It must never be introduced as an unrecorded substitute for missing
semantic evidence, acquisition, route data, or valid geometry.
