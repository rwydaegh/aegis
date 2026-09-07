% PREV: % claim: ten_route_wbsar_route_quantiles
% PREV: \begin{table*}[!t]
% PREV: \caption{Fixed-route exposure summary. Whole-body SAR is normalized per unit $\rho_A P_{\mathrm{EIRP}}$. Excess above direct-path power is computed only at points with nonzero direct power.}
% PREV: \label{tab:route-results}
% PREV: \centering
% PREV: \begin{tabular}{lrrrrr}
% PREV: \toprule
% PREV: & \multicolumn{3}{c}{Normalized whole-body SAR [m$^2$~kg$^{-1}$]} & & \\
% PREV: \cmidrule(lr){2-4}
% PREV: City & $q_{10}$ & $q_{50}$ & $q_{90}$ & \shortstack{Median excess\\above direct [dB]} & \shortstack{Shadowed\\points} \\
% PREV: \midrule
% PREV: Brussels & 0.02502 & 0.03119 & 0.03371 & 1.43 & 0 \\
% PREV: Ghent & 0.05784 & 0.06205 & 0.06867 & 1.16 & 0 \\
% PREV: Krakow & 0.006717 & 0.02252 & 0.04927 & 0.92 & 0 \\
% PREV: London & 0.01175 & 0.01501 & 0.01744 & 0.90 & 0 \\
% PREV: Madrid & 0.02091 & 0.02238 & 0.02317 & 1.55 & 0 \\
% PREV: Mexico City & $9.92\times10^{-7}$ & 0.1291 & 0.2958 & 0.69 & 3 \\
% PREV: Milan & 0.008529 & 0.009016 & 0.009861 & 1.14 & 0 \\
% PREV: Prague & 0.01216 & 0.01307 & 0.01460 & 1.09 & 0 \\
% PREV: Tokyo Hachiko & $3.63\times10^{-5}$ & 0.009674 & 0.02520 & 0.84 & 3 \\
% PREV: Toulouse & 0.02431 & 0.03022 & 0.04292 & 0.84 & 0 \\
% PREV: \bottomrule
% PREV: \end{tabular}
% PREV: \end{table*}
% NEXT: \subsection{Convergence across runs}
% NEXT: \label{sec:convergence}
% claim: ten_route_component_dominance
% claim: ten_route_pooled_median_wbsar_component_shares
Fig.~\ref{fig:route-distributions}(b) shows the additive component shares. Of
the 157 points with line of sight, direct power is largest at 156. The
single-reflection specular component is largest at Brussels point 2. Mexico City
points 0, 1, and 3 and Tokyo Hachiko points 13, 14, and 15 have zero direct and
zero specular power. The single-reflection diffuse component is the only
nonzero contribution at these six points. Across all 163 points, the separate
component medians are 78\% direct, 20\% specular, and 0.5\% diffuse. These
medians do not sum to 100\% because each is computed separately. The small
pooled diffuse median does not represent the six shadowed points.
