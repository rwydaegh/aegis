% PREV: This study aligned 360-degree street images with a photogrammetric city mesh to
% PREV: map surface materials around pedestrian routes at 15\,GHz. A roofline
% PREV: transmitter model and a directional absorption step then produced normalized
% PREV: whole-body SAR, with all results per unit $\rho_A P_{\mathrm{EIRP}}$. A
% PREV: geometric fixed-grid diagnostic at ten urban locations showed a twofold span in
% PREV: location-median whole-body SAR. Five of these locations were then studied with
% PREV: image-derived materials along fixed routes. In a controlled one-reflection
% PREV: scene, the first-diffuse estimate differed from deterministic quadrature by at
% PREV: most 0.0616\,dB, and the maximum total-transport difference from an independent
% PREV: Sionna RT forward calculation was 0.0344\,dB. Across 73 observation points on
% PREV: five routes, route-median whole-body SAR values differed by a factor of 13.34.
% PREV: Direct transport was largest at all 67 points with line of sight, while
% PREV: first-diffuse transport was the only nonzero contribution at the six fully
% PREV: shadowed points. The route medians were stable at 16 replicas, but the fully
% PREV: shadowed lower tails had larger estimator uncertainty. These results do not rank
% PREV: cities or predict deployed-network exposure.
The image-to-mesh material mapping took effect mainly through the specular
component. A paired control at two sites showed route-median whole-body SAR
changes of $+0.249$ and $-0.158$~dB when the image-derived materials were
replaced by the geometry defaults. Ray calculation time ranges from 5.95 to 73.77~s per site on one A6000 GPU. The main open items are outdoor field validation against the
full city model and a measured transmitter source distribution.

## reviews (paragraph)

_(empty -- run /review to populate)_

## AI notes

The paragraph fixes the interpretation to the selected routes and states the
convergence boundary without a future-work list.
