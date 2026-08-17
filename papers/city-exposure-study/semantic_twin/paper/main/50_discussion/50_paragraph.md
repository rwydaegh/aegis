% PREV: Several limits restrict the interpretation. The study covers five selected
% PREV: routes at 15~GHz and one body model that faces along each walk. The
% PREV: reported scale is per unit areal source density and EIRP. Scaling to a specific
% PREV: deployment is valid only if its transmitter positions follow the assumed
% PREV: roofline model. The transport model contains exact direct transport, exact
% PREV: order-1 specular transport, and one first-diffuse event. It stops at that
% PREV: diffuse event and omits all later interactions as well as higher-order specular
% PREV: paths. The controlled comparison validates the first-diffuse component in a
% PREV: depth-1 case. It does not validate the city calculations that also contain
% PREV: image-derived materials and specular transport. The 16 replicas quantify
% PREV: estimator randomness. They do not include uncertainty in image-to-mesh
% PREV: alignment, geometry, material labels, route choice, transmitter placement, body
% PREV: shape, or body orientation. The repeated five-site computation takes less than
% PREV: 70~s per prepared site on the tested GPU, but image acquisition and material
% PREV: mapping take longer and do not yet have one complete timing record.
% PREV: A separate geometric fixed-grid diagnostic in the supplementary material
% PREV: provides a broader configuration check and remains separate from these
% PREV: fixed-route results.
The first priority is source calibration and end-to-end validation of the city
calculation against outdoor field measurements of the directional field before
body coupling. Second, higher specular orders and paths beyond the first diffuse
event can be added through paired studies that report their change in whole-body
SAR, variance, and computation time. Third, several routes at the same site can
quantify route-selection variation before the site set is enlarged. Other
frequencies, body models, and orientations can then test the remaining range of
validity. Each extension should also report what fraction of the surfaces
reached by the modeled paths carries an image-derived material.

## AI notes
- Orders future work by the present evidential gaps.
- Keeps the recommendations tied to the current method rather than adding new systems.

## Reviews
(empty)
