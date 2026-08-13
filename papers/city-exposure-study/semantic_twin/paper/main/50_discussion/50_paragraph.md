% PREV: Several limits restrict the interpretation. The study covers five selected
% PREV: routes at 15~GHz, one body model, and one route-tangent body orientation. The
% PREV: reported scale is per unit areal source density and EIRP. Scaling to a specific
% PREV: deployment is valid only if its source positions follow the assumed conditional
% PREV: roofline measure. The transport model contains exact direct transport, exact
% PREV: order-1 specular transport, and one first-diffuse event. It stops at that
% PREV: diffuse event and omits all later interactions as well as higher-order specular
% PREV: paths. The controlled comparison validates the first-diffuse component in a
% PREV: depth-1 case. It does not validate the city calculations that also contain
% PREV: atlas materials and specular transport. The 16 replicas quantify estimator
% PREV: randomness. They do not propagate uncertainty in panorama registration,
% PREV: geometry, surface evidence, route choice, source placement, body shape, or body
% PREV: orientation. Finally, the repeated five-site computation takes less than
% PREV: 70~s per prepared site on the tested GPU, but scene acquisition and
% PREV: construction take longer and do not yet have one complete timing record.
The first priority is source calibration and validation of the city
calculation. Calibration should use a measured site source distribution.
Outdoor field measurements should then test the directional field before body
coupling. Second, higher specular orders and paths after a diffuse event
can be added through paired studies that report their change in the endpoints,
variance, and computation time. Third, several routes at the same site can
quantify route-selection variation before the site set is enlarged. Other
frequencies, body models, and orientations can then test the remaining range of
validity. Each extension should also report panorama evidence coverage on the
surfaces reached by the modeled paths.

## AI notes
- Orders future work by the present evidential gaps.
- Keeps the recommendations tied to the current method rather than adding new systems.

## Reviews
(empty)
