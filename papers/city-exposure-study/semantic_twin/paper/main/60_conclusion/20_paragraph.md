% PREV: This study aligned 360-degree street images with a photogrammetric city mesh to
% PREV: map surface materials around fixed pedestrian routes. A common roofline
% PREV: transmitter model and direction-aware body coupling then gave normalized
% PREV: whole-body SAR along each route. Each result was normalized by
% PREV: $\rho_A P_{\mathrm{EIRP}}$. The transport model retained exact direct paths,
% PREV: exact order-1 specular paths, and the first diffuse reflection. In a
% PREV: controlled depth-1 case, the adjoint first-diffuse estimate had maximum
% PREV: bounced-transport errors of 0.0616\,dB against deterministic surface quadrature
% PREV: and 0.0621\,dB against Sionna RT forward tracing. The five scenes contained 73
% PREV: route points. Their route-median values differed by a factor of 13.34. Direct
% PREV: transport was largest at 67 nonshadowed points, while first-diffuse transport
% PREV: was the only nonzero modeled contribution at all six shadowed points.
The image-to-mesh material mapping took effect mainly through the specular
component. A paired control at two sites showed route-median whole-body SAR
changes of $+0.249$ and $-0.158$~dB when the image-derived materials were
replaced by the geometry defaults. The method runs in under 70~s per prepared
site on one GPU. The main open items are outdoor field validation against the
full city model and a measured transmitter source distribution.

## reviews (paragraph)

_(empty -- run /review to populate)_

## AI notes

The paragraph fixes the interpretation to the selected routes and states the
convergence boundary without a future-work list.
