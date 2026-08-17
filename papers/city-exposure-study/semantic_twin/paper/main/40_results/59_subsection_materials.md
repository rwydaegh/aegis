% PREV: % claim: replica_convergence_12_to_16
% PREV: The nested 12-to-16-replica comparison separates the route median from the
% PREV: lower tail. Every route-median whole-body SAR changes by at most
% PREV: $5.90\times10^{-5}$~dB. The largest lower-decile changes are 0.032226~dB in
% PREV: Mexico City and 0.017636~dB in Tokyo Hachiko. The maximum pointwise
% PREV: total-transfer changes in Table~\ref{tab:route-results} reach 0.043625 and
% PREV: 0.019732~dB at these two sites. At 16 replicas, the 90th-percentile total-transfer standard errors are
% PREV: 0.1461~dB in Mexico City and 0.0310~dB in Tokyo Hachiko. The route medians are
% PREV: stable at 16 replicas.
% PREV:
% PREV: % claim: replica_convergence_48_to_64
% PREV: A separate calculation reuses the first 16 replicas and extends every route
% PREV: through 64 replicas. Between 48 and 64 replicas, the whole-body SAR
% PREV: $q_{10}$ changes by 0.00344~dB in Mexico City and 0.00491~dB in Tokyo Hachiko.
% PREV: The largest change among their six fully shadowed route points is 0.0125 and
% PREV: 0.0104~dB. Both lower tails remain stable through 64 replicas.
% PREV: In Mexico City, the single strongest diffuse replica at one shadowed point
% PREV: carries 5738 times the median replica contribution.
% PREV: This result is specific to the fixed routes and excludes route-selection and
% PREV: city-sampling uncertainty. The complete nested comparison is given in the
% PREV: supplementary material.
% NEXT: % claim: paired_material_evidence_control
% NEXT: A paired control for Madrid and Mexico City replaces all image-mapped materials
% NEXT: with the default geometry-based materials while keeping the mesh, route,
% NEXT: roofline model, body, seeds, sampling budget, and transport steps identical.
% NEXT: Each reported change is
% NEXT: $10\log_{10}(x_{\mathrm{image}}/x_{\mathrm{geometry}})$. At Madrid the
% NEXT: image-to-geometry changes in normalized whole-body SAR are $+0.233$, $+0.249$,
% NEXT: and $+0.269$~dB for $q_{10}$, $q_{50}$, and $q_{90}$. At Mexico City the
% NEXT: corresponding changes are $+24.84$, $-0.158$, and $+0.104$~dB. The large
% NEXT: $q_{10}$ change comes from the three fully shadowed points, where both totals
% NEXT: are near zero and first-diffuse transport is the only nonzero contribution. The
% NEXT: direct term is identical in every pair. At Madrid, the image-derived map changes
% NEXT: the route-median specular component by $+1.89$~dB and the first-diffuse
% NEXT: component by $-12.43$~dB, but the total median changes by only $+0.249$~dB.
% NEXT: This control tests the complete material map, including its parameters and the
% NEXT: treatment of woody vegetation as nonblocking. It does not measure material
% NEXT: accuracy or isolate reflectance alone. The supplementary material gives
% NEXT: pointwise and component-level comparisons.
\subsection{Material Sensitivity}
\label{sec:material-sensitivity}
