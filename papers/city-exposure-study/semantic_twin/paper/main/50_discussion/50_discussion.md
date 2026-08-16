<!-- AUTO_BEGIN: assembled -->
\section{Discussion}
\label{sec:discussion}

The factor of $13.34$ between the largest and smallest route medians shows that
body exposure differs among the selected routes after the same source-density
and EIRP normalization. This contrast includes the geometry, visible roofline,
mapped materials, and visibility conditions of each selected route. The
empirical distribution for each site therefore describes only that fixed route
and its calculation points. It does not estimate a city distribution or define
a ranking of the five cities. The analysis reports changes along each
pedestrian route while keeping the statistical unit clear.

The three modeled components explain the local changes within the route
distributions. A direct path is present at 67 route points. The exact order-1
specular term adds one surface reflection. The first-diffuse term connects the
receiver to a roofline transmitter through one blocking surface. After body
coupling, the first-diffuse contribution is small at most nonshadowed
route points. The six remaining points have zero direct and zero
order-1 specular contributions. The first-diffuse contribution is the only
nonzero modeled contribution at those points. Therefore, its small contribution
at most nonshadowed positions does not make it dispensable at shadowed positions.

The paired material control tests the effect of image-derived materials on the
body results. The direct term is identical between the image-derived and
geometry-based cases, so the observed changes arise from the materials used by the
reflected and diffuse terms. In Madrid, the specular and first-diffuse component
changes have opposite signs, while the route-median normalized
whole-body SAR changes by $0.249$~dB. The Mexico City route median changes by
$-0.158$~dB. Its much larger lower-tail ratio comes from three shadowed
route points where both estimates are close to zero, and it is not a stable
central effect. The paired cases differ in their assigned materials and in their
treatment of woody canopy. The image-derived case treats identified woody
canopy as pass-through without attenuation because the city mesh has no canopy
volume. The comparison therefore measures sensitivity to both choices and does
not establish the accuracy of the assigned materials.

Several limits restrict the interpretation. The study covers five selected
routes at 15~GHz and one body model that faces along each walk. The
reported scale is per unit areal source density and EIRP. Scaling to a specific
deployment is valid only if its transmitter positions follow the assumed
roofline model. The transport model contains exact direct transport, exact
order-1 specular transport, and one first-diffuse event. It stops at that
diffuse event and omits all later interactions as well as higher-order specular
paths. The controlled comparison validates the first-diffuse component in a
depth-1 case. It does not validate the city calculations that also contain
image-derived materials and specular transport. The 16 replicas quantify
estimator randomness. They do not include uncertainty in image-to-mesh
alignment, geometry, material labels, route choice, transmitter placement, body
shape, or body orientation. The repeated five-site computation takes less than
70~s per prepared site on the tested GPU, but image acquisition and material
mapping take longer and do not yet have one complete timing record.
A separate geometric fixed-grid diagnostic in the supplementary material
provides a broader configuration check and remains separate from these
fixed-route results.

The first priority is source calibration and validation of the city
calculation. Calibration should use a measured site source distribution.
Outdoor field measurements should then test the directional field before body
coupling. Second, higher specular orders and paths after a diffuse event
can be added through paired studies that report their change in whole-body SAR,
variance, and computation time. Third, several routes at the same site can
quantify route-selection variation before the site set is enlarged. Other
frequencies, body models, and orientations can then test the remaining range of
validity. Each extension should also report how much of the surface reached by
the modeled paths has an image-derived material.
<!-- AUTO_END: assembled -->

















## Aggregation notes (AI-owned)
