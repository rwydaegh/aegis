<!-- AUTO_BEGIN: assembled -->
\section{Conclusion}\label{sec:conclusion}

This study aligned 360-degree street images with a photogrammetric city mesh to
map surface materials around fixed pedestrian routes. A roofline transmitter model and a directional absorption step then produced
normalized whole-body SAR along each route, with all results per unit
$\rho_A P_{\mathrm{EIRP}}$. In a controlled one-reflection scene, the
first-diffuse estimate differed from deterministic quadrature by at most
0.0616\,dB and from an independent Sionna RT forward calculation by at most
0.0621\,dB. Across 73 observation points on five routes, route-median
whole-body SAR values differed by a factor of 13.34. Direct transport was
largest at all 67 points with line of sight, while first-diffuse transport was
the only nonzero contribution at the six fully shadowed points. The route
medians were stable at 16 replicas, but the fully shadowed lower tails had
larger estimator uncertainty. These results do not rank cities or predict
deployed-network exposure.

The image-to-mesh material mapping took effect mainly through the specular
component. A paired control at two sites showed route-median whole-body SAR
changes of $+0.249$ and $-0.158$~dB when the image-derived materials were
replaced by the geometry defaults. The method runs in under 70~s per prepared
site on one GPU. The main open items are outdoor field validation against the
full city model and a measured transmitter source distribution.
<!-- AUTO_END: assembled -->
