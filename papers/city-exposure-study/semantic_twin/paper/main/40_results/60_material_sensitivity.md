% PREV: % claim: replica_convergence_12_to_16
% PREV: The nested 12-to-16-replica comparison separates the central route statistic from the lower tail. Every route-median whole-body SAR changes by at most $5.90\times10^{-5}$~dB. The largest lower-decile point changes are 0.032226~dB in Mexico City and 0.017636~dB in Tokyo Hachiko. The maximum pointwise total-transfer changes in Table~\ref{tab:route-results} reach 0.043625 and 0.019732~dB at these two sites. At 16 replicas, their 90th-percentile total-transfer standard errors are 0.1461 and 0.0310~dB, respectively. Central route statistics are stable under the retained estimator.
% PREV:
% PREV: % claim: replica_convergence_48_to_64
% PREV: A separate calculation retains the exact verified 16-replica
% PREV: prefix and continues every route through 64 replicas. Between 48 and 64
% PREV: replicas, the whole-body SAR $q_{10}$ changes by 0.00344~dB in Mexico City and
% PREV: 0.00491~dB in Tokyo Hachiko. The largest change among their six shadowed
% PREV: route points is 0.0125 and 0.0104~dB, respectively. Both lower tails satisfy the
% PREV: stated aggregate stability criteria through 64 replicas. Mexico City still
% PREV: shows rare-event first-diffuse behavior, with a maximum-to-median positive
% PREV: replica contribution ratio of 5738. This result remains
% PREV: specific to the fixed routes and excludes route-selection and
% PREV: city-sampling uncertainty. The complete nested comparison is provided in the
% PREV: supplementary material.
% claim: paired_material_evidence_control
A paired material-map control was completed for Madrid and Mexico City. The
control replaces all image-mapped materials with the geometry-based materials
while retaining the mesh, route, roofline transmitter model, body, seeds,
sampling budget, and transport steps. Each reported change is
$10\log_{10}(x_{\mathrm{image}}/x_{\mathrm{geometry}})$. The image-to-geometry
changes in normalized whole-body SAR at Madrid are $+0.233$, $+0.249$, and
$+0.269$~dB for $q_{10}$, $q_{50}$, and $q_{90}$. The corresponding changes at
Mexico City are $+24.84$, $-0.158$, and $+0.104$~dB. The large Mexico City
$q_{10}$ change comes from its three shadowed points, where both totals are near
zero and first diffuse is the only nonzero modeled contribution. The direct
term is identical in every pair. At Madrid, the image-derived map changes the
route-median specular component by $+1.89$~dB and the first-diffuse component by
$-12.43$~dB, although the total median changes by $+0.249$~dB. The control tests
the complete material map, including its material parameters and the treatment
of woody vegetation as nonblocking. It does not measure material accuracy or
isolate reflectance alone. The supplementary material gives pointwise and
component-level comparisons.
