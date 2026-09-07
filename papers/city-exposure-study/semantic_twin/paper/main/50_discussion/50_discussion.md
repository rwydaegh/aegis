<!-- AUTO_BEGIN: assembled -->
\section{Discussion}
\label{sec:discussion}

Route-median normalized whole-body SAR differs by a factor of 14.31 across the
ten selected routes. Street width, building height, roofline visibility,
surface materials, and canopy all differ between these routes. The study does
not separate their individual effects. Each distribution applies only to its
route and observation points, so the result is not a city ranking.

The single-reflection diffuse component is small at most points, with a pooled
median of 0.5\%, but it is the only nonzero contribution at the six fully
shadowed points. A propagation model without this component would assign zero
exposure to those positions. Therefore, the diffuse component is necessary to
retain nonzero exposure at these positions.

The paired control shows how image-derived surface information changes the body
result. Direct power is identical in both cases. In Madrid, the specular and
diffuse changes have opposite signs, while the total route median increases by
only 5.9\%. The Mexico City median decreases by 3.6\%. Its large lower-tail
ratio comes from three shadowed points where both estimates are near zero. The
image-derived case also treats identified canopy as
nonblocking because the city geometry has no canopy volume. The control tests
both the surface parameters and vegetation rule. It does not establish material
accuracy.

The study has several limitations. It uses one frequency, one body model, ten
selected routes, one roofline source model, and one set of image-derived surface
labels. The normalized values can be scaled to a specific deployment only when
its transmitter distribution matches the source model. The propagation model
includes direct paths and one specular or diffuse reflection only. The
controlled comparison validates the diffuse component in a one-reflection
scene. The complete city calculation remains unvalidated. Variation across 64 runs measures
random ray-sampling error but not uncertainty in geometry, image alignment,
surface labels, route choice, transmitter placement, body shape, or body
orientation. The recorded GPU times cover only ray and body calculations.
<!-- AUTO_END: assembled -->
