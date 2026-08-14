<!-- AUTO_BEGIN: assembled -->
\section{Discussion}
\label{sec:discussion}

The factor of $13.34$ between the largest and smallest route medians shows that
body exposure differs among the selected routes after the same source-density
and EIRP normalization. This contrast includes the geometry, roofline support,
surface evidence, and visibility conditions of each selected route. The empirical
distribution for each site therefore describes only that fixed route and its
declared standpoints. It does not estimate a city distribution or define a
ranking of the five cities. This conditional analysis reports changes at
pedestrian scale while keeping the statistical unit clear.

The three modeled components explain the local changes within the route
distributions. A direct path is present at 67 standpoints. The exact order-1
specular term adds one surface reflection. The first-diffuse term connects the
receiver to a source at the first blocking diffuse interaction. After body
coupling, the first-diffuse contribution is small at most nonshadowed
standpoints. However, the six remaining standpoints have zero direct and zero
order-1 specular contributions. The first-diffuse contribution is the only
nonzero modeled contribution at those points. Therefore, its small contribution
at most nonshadowed positions does not make it dispensable at shadowed positions.

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

Several limits restrict the interpretation. The study covers five selected
routes at 15~GHz, one body model, and one route-tangent body orientation. The
reported scale is per unit areal source density and EIRP. Scaling to a specific
deployment is valid only if its source positions follow the assumed conditional
roofline measure. The transport model contains exact direct transport, exact
order-1 specular transport, and one first-diffuse event. It stops at that
diffuse event and omits all later interactions as well as higher-order specular
paths. The controlled comparison validates the first-diffuse component in a
depth-1 case. It does not validate the city calculations that also contain
atlas materials and specular transport. The 16 replicas quantify estimator
randomness. They do not propagate uncertainty in panorama registration,
geometry, surface evidence, route choice, source placement, body shape, or body
orientation. Finally, the repeated five-site computation takes less than
70~s per prepared site on the tested GPU, but scene acquisition and
construction take longer and do not yet have one complete timing record.

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
<!-- AUTO_END: assembled -->










## Aggregation notes (AI-owned)
