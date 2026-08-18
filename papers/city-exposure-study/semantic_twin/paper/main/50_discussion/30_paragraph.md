% PREV: The first-diffuse component is small at most points (0.419\% pooled median),
% PREV: but it is the only nonzero contribution at the six fully shadowed points. Its
% PREV: small share where line of sight exists does not make it dispensable where
% PREV: buildings block all direct and specular paths. A transport model that omits the
% PREV: diffuse term would assign zero exposure to those six positions.
% NEXT: Several limits restrict what the results can say. The geometric fixed-grid
% NEXT: diagnostic covers ten locations with geometry-based materials and a fixed body
% NEXT: orientation. The five detailed routes add image-derived materials and a body
% NEXT: facing along the walk. Both tiers use the same frequency (15~GHz), source model,
% NEXT: and transport model. Results are normalized per unit areal source density and
% NEXT: EIRP. Scaling to a specific deployment is valid only if its transmitter
% NEXT: positions follow the assumed roofline model. The transport model stops after one
% NEXT: diffuse event and omits all later interactions and higher-order specular paths.
% NEXT: The controlled comparison validates the first-diffuse component in a
% NEXT: one-reflection scene. It does not validate the city calculations, which also
% NEXT: use image-derived materials and exact specular transport. The 16 replicas
% NEXT: quantify estimator randomness but not uncertainty in image-to-mesh alignment,
% NEXT: geometry, material labels, route choice, transmitter placement, body shape, or
% NEXT: body orientation. The five-site computation takes less than 70~s per prepared
% NEXT: site on the tested GPU, but image acquisition and material mapping take longer
% NEXT: and do not yet have a complete timing record.
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

## AI notes
- Uses only the current Madrid and Mexico City paired controls.
- Avoids describing the control as reflectance-only or as material validation.

## Reviews
(empty)
