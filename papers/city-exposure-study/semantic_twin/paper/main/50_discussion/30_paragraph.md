% PREV: The three modeled components explain the local changes within the route
% PREV: distributions. A direct path is present at 67 standpoints. The exact order-1
% PREV: specular term adds one surface reflection. The first-diffuse term connects the
% PREV: receiver to a source at the first blocking diffuse interaction. After body
% PREV: coupling, the first-diffuse contribution is small at most nonshadowed
% PREV: standpoints. However, the six remaining standpoints have zero direct and zero
% PREV: order-1 specular contributions. The first-diffuse contribution is the only
% PREV: nonzero modeled contribution at those points. Therefore, its small contribution
% PREV: at most nonshadowed positions does not make it dispensable at shadowed positions.
% NEXT: Several limits restrict the interpretation. The study covers five selected
% NEXT: routes at 15~GHz, one body model, and one route-tangent body orientation. The
% NEXT: reported scale is per unit areal source density and EIRP. Scaling to a specific
% NEXT: deployment is valid only if its source positions follow the assumed conditional
% NEXT: roofline measure. The transport model contains exact direct transport, exact
% NEXT: order-1 specular transport, and one first-diffuse event. It stops at that
% NEXT: diffuse event and omits all later interactions as well as higher-order specular
% NEXT: paths. The controlled comparison validates the first-diffuse component in a
% NEXT: depth-1 case. It does not validate the city calculations that also contain
% NEXT: atlas materials and specular transport. The 16 replicas quantify estimator
% NEXT: randomness. They do not propagate uncertainty in panorama registration,
% NEXT: geometry, surface evidence, route choice, source placement, body shape, or body
% NEXT: orientation. Finally, the repeated five-site computation takes less than
% NEXT: 70~s per prepared site on the tested GPU, but scene acquisition and
% NEXT: construction take longer and do not yet have one complete timing record.
The paired material control tests the effect of panorama evidence on the body
results. The direct term is identical between the atlas and geometric
cases, so the observed changes arise from the surface state used by the
reflected and diffuse terms. In Madrid, the specular and first-diffuse component
changes have opposite signs, while the route-median normalized
whole-body SAR changes by $0.249$~dB. The Mexico City route median changes by
$-0.158$~dB. Its much larger lower-tail ratio comes from three shadowed
standpoints where both estimates are close to zero, and it is not a stable
central effect. The paired cases differ in their material binding and in their
treatment of woody canopy. The atlas case treats identified woody canopy as
pass-through without attenuation because the scene has no registered canopy
volumes. The comparison therefore measures sensitivity to both choices and does
not establish the accuracy of the assigned materials.

## AI notes
- Uses only the current Madrid and Mexico City paired controls.
- Avoids describing the control as reflectance-only or as material validation.

## Reviews
(empty)
