% PREV: Several limits restrict what the results can say. The geometric fixed-grid
% PREV: diagnostic covers ten locations with geometry-based materials and a fixed body
% PREV: orientation. The five detailed routes add image-derived materials and a body
% PREV: facing along the walk. Both tiers use the same frequency (15~GHz), source model,
% PREV: and transport model. Results are normalized per unit areal source density and
% PREV: EIRP. Scaling to a specific deployment is valid only if its transmitter
% PREV: positions follow the assumed roofline model. The transport model stops after one
% PREV: diffuse event and omits all later interactions and higher-order specular paths.
% PREV: The controlled comparison validates the first-diffuse component in a
% PREV: one-reflection scene. It does not validate the city calculations, which also
% PREV: use image-derived materials and exact specular transport. The 16 replicas
% PREV: quantify estimator randomness but not uncertainty in image-to-mesh alignment,
% PREV: geometry, material labels, route choice, transmitter placement, body shape, or
% PREV: body orientation. The five-site computation takes less than 70~s per prepared
% PREV: site on the tested GPU, but image acquisition and material mapping take longer
% PREV: and do not yet have a complete timing record.
The first priority is source calibration and end-to-end validation of the city
calculation against outdoor field measurements of the directional field before
body coupling. Second, higher specular orders and paths beyond the first diffuse
event can be added through paired studies that report their change in whole-body
SAR, variance, and computation time. Third, several routes at the same site can
quantify route-selection variation within a single city. Other
frequencies, body models, and orientations can then test the remaining range of
validity. Each extension should also report what fraction of the surfaces
reached by the modeled paths carries an image-derived material.

## AI notes
- Orders future work by the present evidential gaps.
- Keeps the recommendations tied to the current method rather than adding new systems.

## Reviews
(empty)
