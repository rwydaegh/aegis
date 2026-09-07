% PREV: Route-median normalized whole-body SAR differs by a factor of 14.31 across the
% PREV: ten selected routes. Street width, building height, roofline visibility,
% PREV: surface materials, and canopy all differ between these routes. The study does
% PREV: not separate their individual effects. Each distribution applies only to its
% PREV: route and observation points, so the result is not a city ranking.
% NEXT: The paired control shows how image-derived surface information changes the body
% NEXT: result. Direct power is identical in both cases. In Madrid, the specular and
% NEXT: diffuse changes have opposite signs, while the total route median increases by
% NEXT: only 5.9\%. The Mexico City median decreases by 3.6\%. Its large lower-tail
% NEXT: ratio comes from three shadowed points where both estimates are near zero. The
% NEXT: image-derived case also treats identified canopy as
% NEXT: nonblocking because the city geometry has no canopy volume. The control tests
% NEXT: both the surface parameters and vegetation rule. It does not establish material
% NEXT: accuracy.
The single-reflection diffuse component is small at most points, with a pooled
median of 0.5\%, but it is the only nonzero contribution at the six fully
shadowed points. A propagation model without this component would assign zero
exposure to those positions. Therefore, the diffuse component is necessary to
retain nonzero exposure at these positions.

## AI notes
- Interprets the direct, order-1 specular, and first-diffuse roles.
- The six shadowed points are Mexico City 0, 1, and 3 and Tokyo Hachiko 13, 14, and 15.

## Reviews
(empty)
