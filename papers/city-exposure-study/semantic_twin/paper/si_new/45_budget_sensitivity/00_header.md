% NEXT: % claim: roofline_budget_sensitivity
% NEXT: The budget test used paired seeds and common random numbers at the Madrid,
% NEXT: Mexico City, and Prague routes. Exact direct and all-specular components were
% NEXT: byte identical in every paired comparison, and the 200,000-ray, 4,096-cell
% NEXT: replay matched the verified baseline. The largest route-median whole-body-SAR
% NEXT: change among the five cheaper settings was 0.000797345~dB. The directional
% NEXT: first-diffuse fields did not pass the stated test. The largest site $q_{90}$
% NEXT: normalized-$L_{1}$ differences were 0.877498, 0.678942, and 0.400218 at 25,000,
% NEXT: 50,000, and 100,000 rays, respectively. At 1,024 and 2,048 cells, they were
% NEXT: 0.491265 and 0.455431. Each value exceeds the 0.1 limit. The largest absolute
% NEXT: whole-body-SAR changes at a shadowed Mexico City point were 0.707362, 0.563841,
% NEXT: and 0.217259~dB for the three ray settings. They were 0.00206975 and
% NEXT: 0.00088674~dB for the two cell settings.
% NEXT:
% NEXT: Ray cuts also do not give a defensible end-to-end speedup. At 25,000 rays, estimator-wall-time ratios relative to the baseline range from 0.991 to 1.064 across the three routes. Exact all-specular work takes 8.06 to 23.79~s in the baseline, whereas stochastic tracing takes 1.15 to 2.40~s. The $q_{90}$ variance-time ratios for every ray-reduced arm exceed one, with a minimum of 3.16. The reported timing therefore leaves the exact specular stage dominant while the reduced ray settings increase first-diffuse variance. Figure~\ref{fig:si-budget-sensitivity} retains the 200,000-ray, 4,096-cell setting as the production baseline.
\section{Primary-ray and angular-cell budgets}
\label{sec:si-budget-sensitivity}
