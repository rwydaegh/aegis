% PREV: The paired material control tests the effect of image-derived materials on the
% PREV: body results. The direct term is identical in both cases, so all observed
% PREV: changes come from the materials used by the reflected and diffuse terms. In
% PREV: Madrid, the specular and first-diffuse component changes have opposite signs,
% PREV: while the route-median normalized whole-body SAR changes by only $0.249$~dB.
% PREV: The Mexico City route median changes by $-0.158$~dB. Its much larger lower-tail
% PREV: ratio comes from the three fully shadowed route points where both estimates are
% PREV: close to zero, not from a central effect. The paired cases differ in their
% PREV: assigned materials and in their treatment of woody canopy. The image-derived
% PREV: case treats identified canopy as transparent because the city mesh has no canopy
% PREV: volume. The comparison therefore measures sensitivity to both the material
% PREV: assignment and the vegetation rule together, and does not establish material
% PREV: accuracy on its own.
% NEXT: The first priority is source calibration and end-to-end validation of the city
% NEXT: calculation against outdoor field measurements of the directional field before
% NEXT: body coupling. Second, higher specular orders and paths beyond the first diffuse
% NEXT: event can be added through paired studies that report their change in whole-body
% NEXT: SAR, variance, and computation time. Third, several routes at the same site can
% NEXT: quantify route-selection variation beyond the current ten locations. Other
% NEXT: frequencies, body models, and orientations can then test the remaining range of
% NEXT: validity. Each extension should also report what fraction of the surfaces
% NEXT: reached by the modeled paths carries an image-derived material.
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

## AI notes
- States range, transport, validation, uncertainty, and computational limits.
- The runtime sentence uses only the recorded prepared-scene upper bound.

## Reviews
(empty)
