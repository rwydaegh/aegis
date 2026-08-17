% PREV: The paired material control tests the effect of image-derived materials on the
% PREV: body results. The direct term is identical between the image-derived and
% PREV: geometry-based cases, so the observed changes arise from the materials used by the
% PREV: reflected and diffuse terms. In Madrid, the specular and first-diffuse component
% PREV: changes have opposite signs, while the route-median normalized
% PREV: whole-body SAR changes by $0.249$~dB. The Mexico City route median changes by
% PREV: $-0.158$~dB. Its much larger lower-tail ratio comes from three shadowed
% PREV: route points where both estimates are close to zero, and it is not a stable
% PREV: central effect. The paired cases differ in their assigned materials and in their
% PREV: treatment of woody canopy. The image-derived case treats identified woody
% PREV: canopy as pass-through without attenuation because the city mesh has no canopy
% PREV: volume. The comparison therefore measures sensitivity to both choices and does
% PREV: not establish the accuracy of the assigned materials.
% NEXT: The first priority is source calibration and validation of the city
% NEXT: calculation. Calibration should use a measured site source distribution.
% NEXT: Outdoor field measurements should then test the directional field before body
% NEXT: coupling. Second, higher specular orders and paths after a diffuse event
% NEXT: can be added through paired studies that report their change in whole-body SAR,
% NEXT: variance, and computation time. Third, several routes at the same site can
% NEXT: quantify route-selection variation before the site set is enlarged. Other
% NEXT: frequencies, body models, and orientations can then test the remaining range of
% NEXT: validity. Each extension should also report how much of the surface reached by
% NEXT: the modeled paths has an image-derived material.
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
