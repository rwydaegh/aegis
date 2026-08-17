# Manuscript spine

## Decision

This is a regular IEEE Access Research Article. It reports a ten-location
geometric screening and a fixed-route, five-site method and result at 15 GHz.
It does not make a population, city ranking, deployed-network, compliance,
complete-multipath, or material-accuracy claim.

## Title

Image-informed urban propagation and route-level body exposure across ten
cities at 15 GHz

## Thesis

Registered street imagery and city geometry define the material scene around a
fixed route. A common normalized roofline source model then gives stable central
route statistics while retaining large local changes at shadowed standpoints.
A broader geometric screening across ten locations shows a twofold span in
location-median whole-body SAR.

## Paragraph plan

### Front matter

1. A 200 to 250 word abstract states the problem, exact method scope, ten-city
   geometric screening, five detailed routes, controlled validation, main
   result, convergence, and limits.
2. Six alphabetical keywords span body dosimetry, image-informed propagation,
   ray tracing, street imagery, urban propagation, and whole-body SAR.

### I. Introduction

1. Urban propagation and body exposure vary along pedestrian routes.
2. Existing urban propagation and exposure methods provide geometry, transport,
   or body coupling, but their physical assumptions differ.
3. Image-informed wireless scene construction is established, but its use with
   a declared source measure and route-level body endpoint remains limited.
4. This study combines registered panorama evidence, a route-aligned roofline
   measure, a first-material transport decomposition, and body coupling across
   ten urban locations.
5. Three contributions state the scene, method, and ten-location plus
   five-route result without a broad first claim.

### II. Method

#### A. Study Configuration

1. Figure 1 introduces the panorama, support geometry, material atlas, route,
   source curve, and body.
2. Table I defines the five selected routes and shows that standpoints are fixed
   observations rather than a population sample.
3. Panorama registration and the two semantic sources define surface evidence.
4. Projection preserves evidence on the original support mesh and uses a
   declared fallback where evidence is absent or refused.
5. Figure 2 defines the full computation and the audit boundary.

#### B. Exposure Calculation

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

### III. Results

1. A preamble paragraph states frequency, mesh, body, rays, cells, replicas,
   seeds, and hardware timing boundary.

#### A. Validation

2. Hash verification, component closure, and GPU/CPU agreement confirm the
   stored calculation.
3. Figure 3 reports the controlled first-diffuse validation and its scope.

#### B. Route Exposure

4. Figure 4 reports route whole-body SAR distributions.
5. Table II gives route quantiles and the six zero-direct points.
6. Component shares show direct, order-1 specular, and first-diffuse splits
   and the path audit gives image-coverage fractions.

#### C. Replica Convergence

7. The nested 12-to-16 and 48-to-64 replica comparisons separate the stable
   route medians from the less stable Mexico City and Tokyo lower tails.

#### D. Material Sensitivity

8. The Madrid and Mexico City paired control bounds the effect of replacing the
   panorama atlas with the geometric fallback.

### IV. Discussion

1. The ten-location geometric screening shows a twofold span in location-median
   whole-body SAR. The route-median contrast across five detailed routes is
   interpreted as a conditional result, not a city ranking.
2. Direct transport sets most nonshadowed points while first-diffuse transport
   is essential at six shadowed points.
3. The material control shows small central total changes but different
   component balances and an unstable near-zero lower-tail ratio.
4. Limitations state the first-material topology, normalized source law,
   selected routes, controlled-component validation, and unpropagated input
   uncertainties.
5. Future work prioritizes source calibration, higher interaction orders, more
   routes beyond the current ten locations, other frequencies and bodies, and
   external field validation.

### V. Conclusion

1. A short conclusion restates the method, ten-location screening, five-route
   detailed result, controlled validation, shadowed-point finding, and
   conditional scope.

### End matter

1. Data and code availability identify the authenticated artifacts and pending
   public archive.
2. Acknowledgment contains a provisional venue-compliant AI-use disclosure.
3. Manual IEEE references contain only sources cited by the paper.
4. The author biography is provisional until Robin confirms the final author
   list and details.
