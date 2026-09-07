% PREV: The single-reflection diffuse component is small at most points, with a pooled
% PREV: median of 0.5\%, but it is the only nonzero contribution at the six fully
% PREV: shadowed points. A propagation model without this component would assign zero
% PREV: exposure to those positions. Therefore, the diffuse component is necessary to
% PREV: retain nonzero exposure at these positions.
% NEXT: The study has several limitations. It uses one frequency, one body model, ten
% NEXT: selected routes, one roofline source model, and one set of image-derived surface
% NEXT: labels. The normalized values can be scaled to a specific deployment only when
% NEXT: its transmitter distribution matches the source model. The propagation model
% NEXT: includes direct paths and one specular or diffuse reflection only. The
% NEXT: controlled comparison validates the diffuse component in a one-reflection
% NEXT: scene. The complete city calculation remains unvalidated. Variation across 64 runs measures
% NEXT: random ray-sampling error but not uncertainty in geometry, image alignment,
% NEXT: surface labels, route choice, transmitter placement, body shape, or body
% NEXT: orientation. The recorded GPU times cover only ray and body calculations.
The paired control shows how image-derived surface information changes the body
result. Direct power is identical in both cases. In Madrid, the specular and
diffuse changes have opposite signs, while the total route median increases by
only 5.9\%. The Mexico City median decreases by 3.6\%. Its large lower-tail
ratio comes from three shadowed points where both estimates are near zero. The
image-derived case also treats identified canopy as
nonblocking because the city geometry has no canopy volume. The control tests
both the surface parameters and vegetation rule. Independent surface
measurements are required for a material-accuracy assessment.

## AI notes
- Uses only the current Madrid and Mexico City paired controls.
- Avoids describing the control as reflectance-only or as material validation.

## Reviews
(empty)
