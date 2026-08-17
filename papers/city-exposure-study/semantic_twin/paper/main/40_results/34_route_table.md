% PREV: \begin{figure*}[!t]
% PREV: \centering
% PREV: \includegraphics[width=\textwidth]{figures/route_results/route_results.pdf}
% PREV: \caption{Normalized whole-body SAR on the five fixed routes. (a) Midpoint empirical CDFs include all 73 route points. Hollow triangles mark the six points with zero direct and order-1 specular transfer. (b) Additive contributions to route-mean whole-body SAR. The routes are fixed case studies rather than city or population samples.}
% PREV: \label{fig:route-distributions}
% PREV: \end{figure*}
% NEXT: % claim: six_shadowed_standpoints
% NEXT: % claim: pooled_median_wbsar_component_shares
% NEXT: The component shares in Fig.~\ref{fig:route-distributions}(b) are additive
% NEXT: shares of route-mean whole-body SAR. Direct transport is the largest body
% NEXT: contribution at all 67 nonshadowed points. Exact order-1 specular transport is
% NEXT: never the largest. Mexico City points 0, 1, and 3 and Tokyo Hachiko points 13,
% NEXT: 14, and 15 have zero direct and zero order-1 specular transport. First-diffuse
% NEXT: transport is the only nonzero modeled contribution at these six points. Across
% NEXT: all 73 points, the pooled component medians are 77.662\% direct, 21.391\% exact
% NEXT: order-1 specular, and 0.419\% first diffuse. They do not sum to 100\% because
% NEXT: each component has a separate median over the 73 route points. The small
% NEXT: first-diffuse median therefore does not describe the six shadowed points.
% NEXT:
% NEXT: % claim: ray_reached_evidence_coverage
% NEXT: The path audit assigns each retained material interaction to an image-mapped or
% NEXT: geometry-based material. Pooled over the five routes and 16 seeds,
% NEXT: image-mapped surfaces account for 75.903\% of the non-direct
% NEXT: body-coupled whole-body SAR contribution. The corresponding shares are
% NEXT: 80.643\% for exact order-1 specular transport and 13.337\% for first-diffuse
% NEXT: transport. The supplementary material gives the complete split by material source.
% claim: five_city_wbsar_route_quantiles
\begin{table*}[!t]
\caption{Fixed-route exposure summary. Whole-body SAR quantiles are normalized per unit $\rho_A P_{\mathrm{EIRP}}$ and have units m$^2$~kg$^{-1}$. Surplus is computed only at points with nonzero direct transfer. The last column is the maximum pointwise total-transfer change from 12 to 16 replicas.}
\label{tab:route-results}
\centering
\begin{tabular}{lrrrrrr}
\toprule
Site & $q_{10}$ & $q_{50}$ & $q_{90}$ & Median surplus [dB] & \shortstack{Zero direct and\\order-1 specular} & \shortstack{Max total-transfer\\change [dB]} \\
\midrule
Ghent & 0.057833 & 0.062045 & 0.068672 & 1.108 & 0 & 0.0000819 \\
Prague & 0.012157 & 0.013073 & 0.014594 & 1.061 & 0 & 0.0001559 \\
Madrid & 0.020913 & 0.022381 & 0.023171 & 1.534 & 0 & 0.0004083 \\
Mexico City & $9.92\times10^{-7}$ & 0.129062 & 0.295798 & 0.721 & 3 & 0.043625 \\
Tokyo Hachiko & $3.66\times10^{-5}$ & 0.009674 & 0.025200 & 0.828 & 3 & 0.019732 \\
\bottomrule
\end{tabular}
\end{table*}
