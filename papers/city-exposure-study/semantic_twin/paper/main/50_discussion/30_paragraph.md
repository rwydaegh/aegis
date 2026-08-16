% PREV: The three modeled components explain the local changes within the route
% PREV: distributions. A direct path is present at 67 route points. The exact order-1
% PREV: specular term adds one surface reflection. The first-diffuse term connects the
% PREV: receiver to a roofline transmitter through one blocking surface. After body
% PREV: coupling, the first-diffuse contribution is small at most nonshadowed
% PREV: route points. The six remaining points have zero direct and zero
% PREV: order-1 specular contributions. The first-diffuse contribution is the only
% PREV: nonzero modeled contribution at those points. Therefore, its small contribution
% PREV: at most nonshadowed positions does not make it dispensable at shadowed positions.
% NEXT: Several limits restrict the interpretation. The study covers five selected
% NEXT: routes at 15~GHz and one body model that faces along each walk. The
% NEXT: reported scale is per unit areal source density and EIRP. Scaling to a specific
% NEXT: deployment is valid only if its transmitter positions follow the assumed
% NEXT: roofline model. The transport model contains exact direct transport, exact
% NEXT: order-1 specular transport, and one first-diffuse event. It stops at that
% NEXT: diffuse event and omits all later interactions as well as higher-order specular
% NEXT: paths. The controlled comparison validates the first-diffuse component in a
% NEXT: depth-1 case. It does not validate the city calculations that also contain
% NEXT: image-derived materials and specular transport. The 16 replicas quantify
% NEXT: estimator randomness. They do not include uncertainty in image-to-mesh
% NEXT: alignment, geometry, material labels, route choice, transmitter placement, body
% NEXT: shape, or body orientation. The repeated five-site computation takes less than
% NEXT: 70~s per prepared site on the tested GPU, but image acquisition and material
% NEXT: mapping take longer and do not yet have one complete timing record.
% NEXT: A separate geometric fixed-grid diagnostic in the supplementary material
% NEXT: provides a broader configuration check and remains separate from these
% NEXT: fixed-route results.
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

## AI notes
- Uses only the current Madrid and Mexico City paired controls.
- Avoids describing the control as reflectance-only or as material validation.

## Reviews
(empty)
