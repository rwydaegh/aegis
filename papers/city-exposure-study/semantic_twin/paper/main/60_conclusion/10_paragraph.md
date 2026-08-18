% PREV: \section{Conclusion}\label{sec:conclusion}
% NEXT: The image-to-mesh material mapping took effect mainly through the specular
% NEXT: component. A paired control at two sites showed route-median whole-body SAR
% NEXT: changes of $+0.249$ and $-0.158$~dB when the image-derived materials were
% NEXT: replaced by the geometry defaults. The method runs in under 70~s per prepared
% NEXT: site on one GPU. The main open items are outdoor field validation against the
% NEXT: full city model and a measured transmitter source distribution.
This study aligned 360-degree street images with a photogrammetric city mesh to
map surface materials around pedestrian routes at 15\,GHz. A roofline
transmitter model and a directional absorption step then produced normalized
whole-body SAR at ten urban locations, with all results per unit
$\rho_A P_{\mathrm{EIRP}}$. In a controlled one-reflection scene, the
first-diffuse estimate differed from deterministic quadrature by at most
0.0616\,dB, and the maximum total-transport difference from an independent
Sionna RT forward calculation was 0.0344\,dB. Across 163 observation points on
ten routes, route-median whole-body SAR differed by a factor of 14.31. Direct
transport was largest at 156 of the 157 points with line of sight, while
first-diffuse transport was the only nonzero contribution at the six fully
shadowed points.
The route medians were stable at 64 replicas, but the fully shadowed lower
tails had larger estimator uncertainty. These results do not rank cities or
predict deployed-network exposure.

## reviews (paragraph)

_(empty -- run /review to populate)_

## AI notes

The paragraph restates the method, validation scope, campaign size, and two
central route results without extending the production contract.
