# Paper spine

## Decision

This paper is a focused five-site methods-and-results paper. It explains one
image-informed urban exposure method, validates the part that can be validated
cleanly, applies it to five fixed pedestrian routes, and reports the result. It
does not wait for ten cities. It does not add agentic AI, masonry scattering,
RCWA, full multipath, or a second paper inside the first paper.

The numerical authority is the authenticated five-city export described in
[RESULTS_INVENTORY.md](RESULTS_INVENTORY.md). The method authority is
[CURRENT_PRODUCTION_CONTRACT.md](CURRENT_PRODUCTION_CONTRACT.md). If an older
document conflicts with either source, the older statement is not used.

## Preferred title

**Route-level body exposure from street imagery and city geometry at 15 GHz**

This title names the two input modalities, the human endpoint, and the carrier.
It does not claim a population study, a deployed network, or a real-time digital
twin.

Alternative if the title needs a stronger communications term:

**Image-informed urban propagation and route-level body exposure at 15 GHz**

## One-sentence thesis

Registered street imagery and city geometry define a material scene around a
fixed pedestrian route, and a common roofline source model then produces stable
central exposure statistics while preserving large local changes at shadowed
standpoints.

## The result in plain terms

The study contains five sites, 73 route standpoints, and 16 independent replicas
per standpoint. The routes are fixed observation-supported paths. Each result is
normalized per unit active-source density and per unit EIRP. Across the five
selected routes, the median normalized whole-body SAR differs by a factor of
13.34. The median finite multipath surplus is 0.721 to 1.534 dB. Six standpoints
have no direct or order-1 specular contribution. First-diffuse transport carries
the only nonzero modeled contribution at those points. Central route statistics are
stable at 16 replicas, but the lower tails in Mexico City and Tokyo remain less
stable.

## Exact scientific scope

- Frequency: 15 GHz
- Sites: Korenmarkt, Prague, Madrid, Mexico City, and Tokyo Hachiko
- Empirical unit: one standpoint on a fixed `provider_corridor_v1` route
- Total standpoints: 73
- Geometry: 250 m-radius photogrammetric support mesh
- Materials: panorama-derived atlas on the original support mesh
- Source support: observed route-aligned roofline
- Source scaling: per unit \(\rho_A P_{\mathrm{EIRP}}\)
- Source weights: physical three-dimensional roofline arc length
- Transport: exact direct, exact order-1 specular, and first-diffuse next-event
  estimation
- Sampling: 200,000 IID primary rays and 4,096 fixed first-diffuse output cells
- Replicas: seeds 7 through 22, with looks at 4, 8, 12, and 16
- Body: Duke, 56,024 surface elements, fixed route-tangent yaw
- Route statistic: empirical distribution over each fixed route

The paper does not estimate population exposure, citywide exposure, operator
deployment exposure, or regulatory compliance. It does not solve higher
specular orders or a diffuse-to-specular suffix. It does not propagate geometry,
material, route, source, or body uncertainty.

## IEEE Access fit

The paper is a regular IEEE Access Research Article. Its scope combines urban
wireless propagation, image-informed scene construction, and radio-frequency
dosimetry. Street imagery supplies material evidence, city geometry supplies the
transport surface, and the route calculation supplies body endpoints. This is a
multidisciplinary engineering method with a five-site application.

The paper does not contain agentic AI and does not need an AI theme. It also does
not claim a real-time or distributed digital twin. The manuscript uses the
official IEEE Access template. The abstract remains between 150 and 250 words,
and the working paper remains below the journal's recommended 20-page length.
A graphical abstract is prepared with the final files.

## Abstract plan

Target 200 to 230 words. Use one paragraph. Use no citations, equations, model
brands, or project names.

1. State the problem. Urban geometry and material surfaces vary along a
   pedestrian route, so one receiver position does not describe the route.
2. State the method. Registered street imagery and a photogrammetric support
   mesh form a material surface. A roofline source measure and a declared
   first-material transport model produce directional fields for body coupling.
3. State the scale. Five sites, 73 standpoints, 16 replicas, 200,000 primary
   rays, 4,096 output directions, and 15 GHz.
4. State validation. In the controlled depth-1 case, the maximum total-transfer
   discrepancy against the independent forward solution is 0.0344 dB.
5. State results. Route-median normalized whole-body SAR differs by a factor of
   13.34. Median finite multipath surplus is 0.721 to 1.534 dB. Six shadowed
   standpoints have zero direct and zero order-1 specular transport.
6. State uncertainty and meaning. The maximum 12-to-16 total-transfer change is
   0.0437 dB, but the shadowed lower tails remain less stable. The result is a
   conditional fixed-route result, not a population distribution.

## Main argument

The paper uses six top-level sections.

## I. Introduction

### I1. Physical motivation

Urban wireless propagation changes over distances that are small compared with
a city. A pedestrian route can cross direct, reflected, and shadowed regions.
Body exposure therefore depends on local direction and position, not only on a
site-level incident-power scalar.

### I2. Existing approaches

Group prior work into three themes: urban ray tracing, exposure assessment, and
image-informed wireless scene construction. State what each theme provides.
Avoid a separate related-work section unless the final literature review exceeds
about 35 essential references.

### I3. Gap

Existing studies do not yet provide this exact combination: registered street
imagery, a material surface on city geometry, a declared roofline source
measure, component-resolved first-material transport, and body endpoints along
fixed routes. This claim requires a final literature check. Do not use “for the
first time” until that check passes.

### I4. Purpose and contributions

State the five-site and 73-standpoint scope. Then state three contributions.

1. A visual-geometric scene construction that binds panorama evidence to the
   transport mesh with explicit provenance.
2. A normalized roofline-source and first-material transport model that keeps
   direct, order-1 specular, and first-diffuse contributions separate before
   body coupling.
3. A five-site fixed-route result with controlled validation, component closure,
   convergence reporting, and explicit shadowed-point analysis.

If the literature audit supports novelty, use one precise sentence: “To the best
of the authors’ knowledge, this is the first route-level body-exposure study to
combine registered street imagery with a roofline source measure and an explicit
first-material transport decomposition.”

### I5. Introduction close

Close after the contributions. Do not add a paper-map paragraph. This follows
the author's recent BioEM-derived style while keeping the Introduction short.

## II. Configuration and evidence

### C1. Configuration

Introduce Fig. 1 in the first sentence: “The study configuration is shown in
Fig. 1.” Show the panorama, material surface, support geometry, fixed route,
roofline source curve, receiver, and body. State that panorama evidence supplies
materials. It does not create the support geometry.

### C2. Five fixed routes

Use Table I. List the five sites, route span, standpoint count, panorama evidence
status, and route contract. State that the standpoints are not a random or
population sample. Fixed route-tangent yaw defines body orientation.

### C3. Material surface

Explain the semantic pipeline in one substantial paragraph. A dense entity model
provides the closed object partition. A promptable model refines compatible
material and vegetation classes. Registration projects both forms of evidence
onto the support surface. Unseen or nondecisive regions retain the declared
geometric prior. Move prompts, class vocabularies, masks, refusal categories,
and atlas implementation details to the supplementary information.

### C4. Flowchart and audit boundary

Introduce Fig. 2 as the flowchart. State that the campaign identity binds route,
source, material, mesh, body, sampler, and transport inputs. The complete current
set has 210 verified source files and exact component closure at floating-point
roundoff. Keep hashes out of the body and put them in the data statement or SI.

## III. Method

Use four main equations. All computational thresholds, chunks, kernel choices,
and cache controls go to SI or the reproducibility package.

### M1. Source scale and roofline measure

Separate the expected physical source count from numerical quadrature:

\[
N_{\mathrm{site}}=\rho_A A_{\mathrm{crop}}, \qquad
p_i=\frac{\ell_i}{\sum_j\ell_j}.
\]

Here \(\ell_i\) is the physical three-dimensional length represented by
roofline element \(i\). Plan-view length is a sensitivity option, not the
baseline.

### M2. Reference scale

Define the unobstructed geometric reference and the per-unit scale:

\[
D_{\mathrm{ref}}(\mathbf{x})=
\sum_i\frac{p_i}{r_i(\mathbf{x})^2}, \qquad
S_{\mathrm{ref}}(\mathbf{x})=
\frac{A_{\mathrm{crop}}D_{\mathrm{ref}}(\mathbf{x})}{4\pi}.
\]

No visibility test enters \(D_{\mathrm{ref}}\). A physical scenario multiplies
the normalized result by \(\rho_A P_{\mathrm{EIRP}}\).

### M3. First-material transport

Define the directional transfer measure:

\[
\mu_{\mathbf{x}}=
\frac{M_{\mathrm{direct}}+
M_{\mathrm{specular},1}+
\widehat M_{\mathrm{diffuse},1}}
{D_{\mathrm{ref}}(\mathbf{x})}.
\]

The direct and order-1 specular terms are exact. The diffuse term uses next-event
estimation at the first blocking diffuse material vertex. A sampled path stops
there. This is the central scope statement and must appear in the abstract,
method, and limitations.

### M4. Direction-aware body coupling

Define absorbed power density on body element \(r\):

\[
S_{ab}(r)=T_0\sum_q S_{\mathrm{ref}}\,\mu_q
\left[\widehat{\mathbf n}(r)\cdot
\left(-\widehat{\mathbf k}_q\right)\right]_+.
\]

State in prose that absorbed power is the area integral of \(S_{ab}\), whole-body
SAR is absorbed power divided by body mass, and the reported peak is the maximum
of the replica-mean body field. Direction remains explicit until body coupling.

### M5. Sampling and route statistics

State 200,000 IID primary rays, 4,096 fixed first-diffuse output cells, seeds 7 through
22, and looks at 4, 8, 12, and 16. Explain that the 4,096 cells are outputs, not
launch strata. Define each route curve as an empirical distribution over its
fixed standpoints with plotting positions \((\mathrm{rank}-0.5)/n\). Explain in
prose that surplus is undefined when direct transport is zero.

## IV. Results

### R1. Reproducibility setup

Open Results with Table I. State the data version, five sites, 73 standpoints,
15 GHz, 250 m geometry, route contract, body model, 16 seeds, ray count, output
directions, and A6000 hardware. Numerical campaign wall time is 29.79 to 69.02 s
after scene preparation. Do not call this cold end-to-end time.

### R2. Controlled validation

Introduce Fig. 3 before any city result. The controlled open-square case has 27
sources, six receivers, eight triangles, and one diffuse reflection. Compare
deterministic triangle quadrature, the adjoint estimate, and an independent
forward solver. Report maximum discrepancies of 0.0616 dB for bounced transfer
relative to quadrature and 0.0344 dB for total adjoint-versus-forward transfer.
State that the test validates the first-diffuse component, not the complete
atlas-material and specular city stack.

### R3. Fixed-route body distributions

Introduce Fig. 4. Report normalized whole-body SAR for all 73 standpoints and
finite multipath surplus for 67 standpoints. Use Table II for q10, q50, q90,
finite-surplus median, zero-direct count, and final convergence change. The text
should highlight only the factor-of-13.34 median contrast and the visibly larger
within-route spread at Mexico City and Tokyo.

### R4. Transport components

Use Fig. 4(b). Direct transport is largest at 67 nonshadowed points. Exact
order-1 specular is never the largest component. First diffuse carries the
only nonzero modeled contribution at all six shadowed points. Across all 73 points, the
pooled median whole-body-SAR shares are 77.662% direct, 21.391% order-1 specular, and 0.419%
first diffuse. State clearly that the diffuse median does not describe the six
shadowed points.

### R5. Convergence and negative case

Central route statistics are stable at look 16. The maximum 12-to-16 change in
total transfer is 0.0000819 to 0.043625 dB across sites. However, the look-16
p90 standard error is 0.1461 dB in Mexico City and 0.0310 dB in Tokyo. Place the
full convergence figure in SI. This is the explicit negative result. Do not say
that every point has converged.

### R6. Material-evidence ablation

The paired current-contract control is complete for Madrid and Mexico City. It
replaces the panorama-derived atlas with the declared geometric fallback while
holding geometry, route, source, seeds, transport, and body model fixed. This is
an evidence-layer sensitivity test. It is not a material-accuracy test or a
reflectance-only test.

For Madrid, the atlas changes the route-median normalized whole-body SAR by
+0.249 dB. Its q10 and q90 changes are +0.233 and +0.269 dB. For Mexico City,
the corresponding changes are -0.158, +24.84, and +0.104 dB. The very large
Mexico City q10 change comes from the three shadowed points, where first-diffuse
transport is the only nonzero modeled contribution and both alternatives are near zero.
The direct term is identical in every paired run. The component split changes
much more than the central total. In Madrid, the route-median specular term is
1.89 dB higher and the first-diffuse term is 12.43 dB lower with the atlas.

The main paper should report the central endpoint changes and the shadowed
stratum separately. The complete component and pointwise comparison belongs in
the supplementary material. The result shows that the atlas changes the
transport partition while its effect on the route median is below 0.25 dB in
both selected sites. It does not show that either material assignment is more
accurate.

## V. Discussion

### D1. Main interpretation

A route median summarizes the center but can omit deep local shadow. This result
is strongest at Mexico City and Tokyo, where six points have no retained direct
or order-1 specular path. Do not convert this observation into a universal city
ranking.

### D2. Value of direction and components

The component split shows whether a route change comes from visibility,
first-order reflection, or the first diffuse event. Direction-aware body
coupling then converts the same arriving power from different directions into
different surface fields. Keep the interpretation tied to the retained three
components.

### D3. Value and limit of image evidence

Registered panoramas provide material information where map geometry does not.
The paired control shows modest route-median endpoint changes and larger changes
in the specular and diffuse components. The shadowed Mexico City stratum remains
sensitive because its retained result contains first-diffuse transport only.
Coverage outside observed regions remains prior based. This is visual-geometric
evidence fusion, not RF measurement and not a live digital twin.

### D4. Limits

List the limits in one substantial paragraph: five selected routes, one
frequency, one source law, one body, fixed yaw, first-material transport, 16
replicas, no population sampling, and no propagated scene uncertainty. State
that convergence intervals cover estimator randomness only.

### D5. Next step

Additional routes quantify route-selection uncertainty. Additional frequencies
test spectral transfer. Higher interactions test the transport boundary. Body
and orientation ensembles test human variability. Keep this paragraph short.

## VI. Conclusion

Use two paragraphs. The first states what was computed and the two central
numbers. The second states the conditional meaning. Add no new result, equation,
technology, or broad promise.

## Main figures

1. **Configuration.** Registered panorama and material surface above the current
   Prague route, roofline source curve, receiver, and body. The caption must use
   the word “configuration.”
2. **Flowchart.** Plain black TikZ boxes. Registered panorama and support mesh,
   fused material surface, source curve and route, first-material transport,
   body coupling, fixed-route distributions.
3. **Validation.** Deterministic quadrature, independent forward tracing, and the
   adjoint first-diffuse estimate in the controlled depth-1 case.
4. **Five-site results.** Fixed-route empirical distributions of normalized
   whole-body SAR and finite multipath surplus.
5. **Transport components.** Direct, exact order-1 specular, and first-diffuse
   shares at all 73 standpoints, with the six zero-direct points marked.

The convergence figure belongs in SI unless the final page layout has room.

## Main tables

### Table I. Configuration and campaign inventory

Site, route span, standpoints, admitted evidence count, replicas, primary rays,
output directions, and numerical campaign wall time.

### Table II. Headline route statistics

Site, normalized whole-body SAR q10, q50, q90, median finite surplus,
zero-direct count, and maximum 12-to-16 total-transfer change.

## Supplementary information

- panorama selection and registration gates
- semantic vocabularies, prompts, and fusion rules
- atlas coverage, refusal categories, and geometric fallbacks
- route construction, station identifiers, distances, and hashes
- complete source-curve construction and plan-view sensitivity
- full model-parameter table
- complete component closure and manifest audit
- body endpoint definitions and CUDA parity
- per-site route profiles
- convergence at looks 4, 8, 12, and 16
- Mexico City and Tokyo lower-tail diagnostics
- historical topology sensitivity, clearly labeled as historical
- scene-construction and numerical timing ledger
- optional Blender and panorama audit views

Do not place agentic AI, Gemini, masonry scattering, RCWA, the rejected mixed
suffix estimator, or obsolete eleven-city results in the SI. Archival material
is not supplementary evidence.

## Claims that are allowed

- The method combines registered street imagery and city geometry.
- The five campaigns use one sealed first-material transport contract.
- The route statistics are normalized and conditional on fixed routes.
- Direct, order-1 specular, and first-diffuse components are separated before
  body coupling.
- Central route statistics are stable at 16 replicas.
- Six retained standpoints have zero direct and zero order-1 specular transport.
- The controlled depth-1 first-diffuse case agrees with independent references
  within the reported numerical differences.

## Claims that are not allowed

- representative cities or pedestrians
- population, citywide, or operator-deployment exposure
- absolute W/m² or W/kg without a declared \(\rho_A P_{\mathrm{EIRP}}\)
- full multipath, complete ray tracing, or three-bounce production
- complete convergence at every standpoint
- full-stack external validation
- measured material properties or complete panorama coverage
- a real-time, distributed, or operational digital twin
- agentic AI as a scientific contribution
- exposure danger, risk, or safety conclusions
- improved material accuracy from the paired evidence-layer control

## Writing controls

- Use American English.
- Use simple subject-verb-object sentences.
- Prefer “is,” “has,” “uses,” “computes,” and “shows.”
- Use no em dashes and no semicolons.
- Use no anthropomorphism.
- Use no internal project names in the abstract, body, captions, or legends.
- Use “exposure,” “absorbed power,” and “whole-body SAR.” Avoid danger framing.
- Introduce every figure before it appears.
- Keep captions near 50 to 60 words.
- Use nonbreaking spaces before numbers, units, and citations in LaTeX.
- Use no theorem, proposition, lemma, remark, or definition environment.
- Use no equation in the abstract, introduction, or conclusion.
- Put exact values in tables. Use prose for the two or three important findings.
- Do not use fake or illustrative numerical data in a scientific result figure.

## Submission gates

### Green now

- five authenticated current-contract campaigns
- 73 fixed-route standpoints
- exact direct and exact order-1 specular components
- controlled three-way first-diffuse validation
- body-backend parity
- component closure and manifest verification
- main results, component, flowchart, and convergence figure sources
- paired Madrid and Mexico City material-evidence controls

### Yellow

- full-stack external validation is not available
- Mexico City and Tokyo lower tails remain less stable
- cold end-to-end timing is incomplete
- the novelty sentence needs a final literature audit
- figure captions and the manuscript paragraph tree remain to be written

### Red if claimed

- ten-city completion
- population or citywide inference
- complete multipath
- deployment-absolute exposure
- real-time digital twin operation
- agentic AI
- fully measured materials

The paper is ready to draft from this spine. No additional numerical campaign
should displace writing time unless a result or reviewer comment directly
requires it.
