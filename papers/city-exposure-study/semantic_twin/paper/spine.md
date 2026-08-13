# Manuscript spine

## Decision

This is a regular IEEE Access Research Article. It reports a fixed-route,
five-site method and result at 15 GHz. It does not make a population, city
ranking, deployed-network, compliance, complete-multipath, or material-accuracy
claim.

## Title

Image-informed urban propagation and route-level body exposure at 15 GHz

## Thesis

Registered street imagery and city geometry define the material scene around a
fixed route. A common normalized roofline source model then gives stable central
route statistics while retaining large local changes at shadowed standpoints.

## Paragraph plan

### Front matter

1. A 200 to 250 word abstract states the problem, exact method scope, five-site
   scale, controlled validation, main result, convergence, and limits.
2. Six alphabetical keywords span body dosimetry, image-informed propagation,
   ray tracing, street imagery, urban propagation, and whole-body SAR.

### I. Introduction

1. Urban propagation and body exposure vary along pedestrian routes.
2. Existing urban propagation and exposure methods provide geometry, transport,
   or body coupling, but their physical assumptions differ.
3. Image-informed wireless scene construction is established, but its use with
   a declared source measure and route-level body endpoint remains limited.
4. This study combines registered panorama evidence, a route-aligned roofline
   measure, a first-material transport decomposition, and body coupling.
5. Three contributions state the scene, method, and five-route result without a
   broad first claim.

### II. Configuration and scene evidence

1. Figure 1 introduces the panorama, support geometry, material atlas, route,
   source curve, and body.
2. Table I defines the five selected routes and shows that standpoints are fixed
   observations rather than a population sample.
3. Panorama registration and the two semantic sources define surface evidence.
4. Projection preserves evidence on the original support mesh and uses a
   declared fallback where evidence is absent or refused.
5. Figure 2 defines the full computation and the audit boundary.

### III. Route-conditioned exposure method

1. A compact notation passage states the fixed assumptions.
2. The areal density sets source count while physical roofline arc length sets
   conditional source weights.
3. The unobstructed reference preserves inverse-square geometry and defines the
   normalized physical scale.
4. Direct, exact order-1 specular, and first-diffuse next-event terms define the
   retained directional field.
5. Direction remains explicit through body coupling to absorbed power density,
   absorbed power, and whole-body SAR.
6. IID replicas and fixed-route empirical quantiles define the numerical and
   statistical outputs.

### IV. Validation and results

1. A reproducibility paragraph states frequency, mesh, body, rays, cells,
   replicas, seeds, and hardware timing boundary.
2. Figure 3 reports the controlled first-diffuse validation and its scope.
3. Figure 4 reports route wbSAR and finite surplus distributions.
4. Table II gives route quantiles and the six zero-direct points.
5. Figure 4(b) shows direct, order-1 specular, and first-diffuse component shares.
6. Table II and the supplementary convergence figure report 4, 8, 12, and
   16-replica convergence and preserve the less stable Mexico City and Tokyo
   lower tails.
7. The Madrid and Mexico City paired control bounds the effect of replacing the
   panorama atlas with the geometric fallback.

### V. Discussion

1. The route-median contrast is interpreted as a conditional result among five
   selected routes, not a city ranking.
2. Direct transport sets most nonshadowed points while first-diffuse transport
   is essential at six shadowed points.
3. The material control shows small central total changes but different
   component balances and an unstable near-zero lower-tail ratio.
4. Limitations state the first-material topology, normalized source law,
   selected routes, controlled-component validation, and unpropagated input
   uncertainties.
5. Future work prioritizes source calibration, higher interaction orders, more
   routes, other frequencies and bodies, and external field validation.

### VI. Conclusion

1. A short conclusion restates the method, five-site result, controlled
   validation, shadowed-point finding, and conditional scope.

### End matter

1. Data and code availability identify the authenticated artifacts and pending
   public archive.
2. Acknowledgment contains a provisional venue-compliant AI-use disclosure.
3. Manual IEEE references contain only sources cited by the paper.
4. The author biography is provisional until Robin confirms the final author
   list and details.
