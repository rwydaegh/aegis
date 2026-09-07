# Manuscript spine

## Decision

This paper targets the IEEE OJ-COMS special issue on human-centric wireless
systems. It reports results for fixed routes in ten cities at 15 GHz. It does not make a population, city
ranking, deployed-network, compliance, complete-multipath, or
material-accuracy claim.

## Title

Human-Centric 6G RF-EMF Exposure with AI-Assisted Digital Twins in Ten Cities

## Thesis

Street imagery and city geometry form an AI-assisted digital twin around a
fixed route. SAM~3 Agent supplies the agentic AI stage for material and
vegetation labels. A normalized roofline source model and direction-aware body
model give stable route medians while retaining nonzero exposure at shadowed
points.

## Paragraph plan

### Front matter

1. A 200 to 250 word abstract states the problem, exact method scope, ten-city
   scale, controlled validation, main result, convergence, and limits.
2. Five alphabetical keywords cover AI-assisted digital twins, human-centric
   wireless systems, ray tracing, RF-EMF exposure, and whole-body SAR.

### I. Introduction

1. Urban propagation and body exposure vary along pedestrian routes.
2. Existing urban propagation and exposure methods provide geometry, propagation,
   or body coupling, but their physical assumptions differ.
3. Image-informed wireless scene construction is established, but its use with
   a declared source measure and route-level body endpoint remains limited.
4. This study combines aligned panorama evidence, a route-aligned roofline
   model, a single-reflection component split, and body coupling across
   ten urban locations.
5. Three contributions state the scene, method, and ten-route result without a
   broad first claim.

### II. Method

#### A. Study Configuration

1. Figure 1 introduces the panorama, support geometry, material atlas, route,
   source curve, and body.
2. Table I defines the ten selected routes and shows that standpoints are fixed
   observations rather than a population sample.
3. Image alignment, Mask2Former, and SAM~3 Agent define surface evidence. SAM~3
   Agent is the agentic AI stage for material and vegetation labels.
4. Projection preserves evidence on the original support mesh and uses a
   declared fallback where evidence is absent or refused.
5. Figure 2 shows the method from multimodal city data to whole-body SAR.

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
6. Independent runs and fixed-route empirical quantiles define the numerical and
   statistical outputs.

### III. Results

1. The final Methods paragraph states frequency, mesh, body, rays, cells, runs,
   seeds, and hardware timing boundary.

#### A. Validation

2. Component closure and GPU/CPU agreement confirm the stored calculation.
3. Figure 3 reports the controlled first-diffuse validation and its scope.

#### B. Route Exposure

4. Figure 4 reports route whole-body SAR distributions across ten routes.
5. Table II gives route quantiles and the six zero-direct points.
6. Component shares show direct, single-reflection specular, and
   single-reflection diffuse power.

#### C. Convergence across runs

7. The 48-to-64-run comparison shows stable route medians and larger
   lower-tail changes in Mexico City and Tokyo.

#### D. Material Sensitivity

8. The Madrid and Mexico City paired control bounds the effect of replacing the
   panorama atlas with the geometric fallback.

### IV. Discussion

1. Route-median whole-body SAR differs by a factor of 14.31 across the ten
   routes. The contrast is interpreted as a conditional result among selected
   routes, not a city ranking.
2. Direct power dominates most nonshadowed points while diffuse power
   is essential at six shadowed points.
3. The material control shows small central total changes but different
   component balances and an unstable near-zero lower-tail ratio.
4. Limitations state the first-material topology, normalized source law,
   selected routes, controlled-component validation, and unpropagated input
   uncertainties.
5. Future work prioritizes source calibration, higher interaction orders, more
   routes, other frequencies and bodies, and external field validation.

### V. Conclusion

1. A short conclusion restates the method, ten-route result, controlled
   validation, shadowed-point finding, and conditional scope.

### End matter

1. Data and code availability identify the authenticated artifacts and pending
   public archive.
2. Acknowledgment contains a provisional venue-compliant AI-use disclosure.
3. Manual IEEE references contain only sources cited by the paper.
4. The author biography is provisional until Robin confirms the final author
   list and details.
