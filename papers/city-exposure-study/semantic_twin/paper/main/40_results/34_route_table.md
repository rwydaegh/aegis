% PREV: \begin{figure*}[!t]
% PREV: \centering
% PREV: \includegraphics[width=\textwidth]{figures/route_results/route_results.pdf}
% PREV: \caption{Normalized whole-body SAR on the ten fixed routes. (a)~Empirical CDFs include all 163 route points. Hollow triangles mark the six points with zero direct and zero order-1 specular transfer. (b)~Route-mean component shares of whole-body SAR. The routes are fixed case studies, not city or population samples.}
% PREV: \label{fig:route-distributions}
% PREV: \end{figure*}
% NEXT: % claim: six_shadowed_standpoints
% NEXT: % claim: pooled_median_wbsar_component_shares
% NEXT: The additive component shares of route-mean whole-body SAR are shown in the
% NEXT: supplementary material. Direct transport is the largest
% NEXT: contribution at all 67 points with line of sight. Exact order-1 specular
% NEXT: transport is never the largest. Mexico City points 0, 1, and 3 and Tokyo
% NEXT: Hachiko points 13, 14, and 15 have zero direct and zero order-1 specular
% NEXT: transport. First-diffuse transport is the only nonzero contribution at these six
% NEXT: points. Across all 73 points, the pooled component medians are 77.662\% direct,
% NEXT: 21.391\% exact order-1 specular, and 0.419\% first diffuse. They do not sum to
% NEXT: 100\% because each component has a separate median over the 73 route points. The
% NEXT: small first-diffuse median therefore does not describe the six fully shadowed
% NEXT: points.
% NEXT:
% NEXT: % claim: ray_reached_evidence_coverage
% NEXT: The path audit assigns each retained material interaction to an image-mapped or
% NEXT: geometry-based surface. Pooled over the five routes and 16 seeds, image-mapped
% NEXT: surfaces account for 75.903\% of the reflected SAR. The
% NEXT: corresponding shares are 80.643\% for exact order-1 specular transport and
% NEXT: 13.337\% for first-diffuse transport. The supplementary material gives the
% NEXT: complete split by material source.
% claim: ten_city_wbsar_route_quantiles
\begin{table*}[!t]
\caption{Fixed-route exposure summary. Whole-body SAR quantiles are normalized per unit $\rho_A P_{\mathrm{EIRP}}$ and have units m$^2$~kg$^{-1}$. Surplus is computed only at points with nonzero direct transfer. The last column is the maximum pointwise total-transfer change from 48 to 64 replicas.}
\label{tab:route-results}
\centering
\begin{tabular}{lrrrrrr}
\toprule
Site & $q_{10}$ & $q_{50}$ & $q_{90}$ & Median surplus [dB] & \shortstack{Zero direct and\\order-1 specular} & \shortstack{Max total-transfer\\change [dB]} \\
\midrule
Brussels & 0.025022 & 0.031187 & 0.033714 & 1.431 & 0 & 0.0003047 \\
Ghent & 0.057835 & 0.062047 & 0.068668 & 1.155 & 0 & 0.0001115 \\
Krakow & 0.006717 & 0.022520 & 0.049268 & 0.917 & 0 & 0.0002922 \\
London & 0.011746 & 0.015008 & 0.017444 & 0.901 & 0 & 0.0008481 \\
Madrid & 0.020913 & 0.022381 & 0.023170 & 1.552 & 0 & 0.0001015 \\
Mexico City & $9.92\times10^{-7}$ & 0.129061 & 0.295766 & 0.686 & 3 & 0.0138811 \\
Milan & 0.008529 & 0.009016 & 0.009861 & 1.136 & 0 & 0.0001842 \\
Prague & 0.012157 & 0.013074 & 0.014595 & 1.091 & 0 & 0.0001223 \\
Tokyo Hachiko & $3.66\times10^{-5}$ & 0.009674 & 0.025200 & 0.839 & 3 & 0.0055850 \\
Toulouse & 0.024312 & 0.030217 & 0.042915 & 0.835 & 0 & 0.0000651 \\
\bottomrule
\end{tabular}
\end{table*}
