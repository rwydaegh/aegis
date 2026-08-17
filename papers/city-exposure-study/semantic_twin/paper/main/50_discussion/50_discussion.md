<!-- AUTO_BEGIN: assembled -->
\section{Discussion}
\label{sec:discussion}

The ten-location geometric screening shows a twofold span in location-median
whole-body SAR across locations that differ in street width, building height,
and roofline visibility. The factor of 13.34 between the largest and smallest
route medians on the five detailed routes is much larger, reflecting the
additional variation from image-derived materials, canopy, and route-specific
visibility conditions. Each empirical distribution therefore describes only
that fixed route and its observation points.

The first-diffuse component is small at most points (0.419\% pooled median),
but it is the only nonzero contribution at the six fully shadowed points. Its
small share where line of sight exists does not make it dispensable where
buildings block all direct and specular paths. A transport model that omits the
diffuse term would assign zero exposure to those six positions.

The paired material control tests the effect of image-derived materials on the
body results. The direct term is identical in both cases, so all observed
changes come from the materials used by the reflected and diffuse terms. In
Madrid, the specular and first-diffuse component changes have opposite signs,
while the route-median normalized whole-body SAR changes by only $0.249$~dB.
The Mexico City route median changes by $-0.158$~dB. Its much larger lower-tail
ratio comes from the three fully shadowed route points where both estimates are
close to zero, not from a central effect. The paired cases differ in their
assigned materials and in their treatment of woody canopy. The image-derived
case treats identified canopy as transparent because the city mesh has no canopy
volume. The comparison therefore measures sensitivity to both the material
assignment and the vegetation rule together, and does not establish material
accuracy on its own.

Several limits restrict what the results can say. The geometric fixed-grid
diagnostic covers ten locations with geometry-based materials and a fixed body
orientation. The five detailed routes add image-derived materials and a body
facing along the walk. Both tiers use the same frequency (15~GHz), source model,
and transport model. Results are normalized per unit areal source density and
EIRP. Scaling to a specific deployment is valid only if its transmitter
positions follow the assumed roofline model. The transport model stops after one
diffuse event and omits all later interactions and higher-order specular paths.
The controlled comparison validates the first-diffuse component in a
one-reflection scene. It does not validate the city calculations, which also
use image-derived materials and exact specular transport. The 16 replicas
quantify estimator randomness but not uncertainty in image-to-mesh alignment,
geometry, material labels, route choice, transmitter placement, body shape, or
body orientation. The five-site computation takes less than 70~s per prepared
site on the tested GPU, but image acquisition and material mapping take longer
and do not yet have a complete timing record.

The first priority is source calibration and end-to-end validation of the city
calculation against outdoor field measurements of the directional field before
body coupling. Second, higher specular orders and paths beyond the first diffuse
event can be added through paired studies that report their change in whole-body
SAR, variance, and computation time. Third, several routes at the same site can
quantify route-selection variation beyond the current ten locations. Other
frequencies, body models, and orientations can then test the remaining range of
validity. Each extension should also report what fraction of the surfaces
reached by the modeled paths carries an image-derived material.
<!-- AUTO_END: assembled -->
