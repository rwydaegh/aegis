% PREV: \begin{figure*}[!htb]
% PREV: \centering
% PREV: \includegraphics[width=\textwidth,height=0.76\textheight,keepaspectratio]{figures/route_results/route_results.pdf}
% PREV: \caption{Normalized whole-body SAR on the ten fixed routes. (a)~Empirical CDFs include all 163 observation points. Hollow triangles mark the six points with zero direct and zero single-reflection specular power. (b)~Route-mean component shares. The routes are case studies and support no city or population inference.}
% PREV: \label{fig:route-distributions}
% PREV: \end{figure*}
% NEXT: % claim: ten_route_component_dominance
% NEXT: % claim: ten_route_pooled_median_wbsar_component_shares
% NEXT: Fig.~\ref{fig:route-distributions}(b) shows the additive component shares. Of
% NEXT: the 157 points with line of sight, direct power is largest at 156. The
% NEXT: single-reflection specular component is largest at Brussels point 2. Mexico City
% NEXT: points 0, 1, and 3 and Tokyo Hachiko points 13, 14, and 15 have zero direct and
% NEXT: zero specular power. The single-reflection diffuse component is the only
% NEXT: nonzero contribution at these six points. Across all 163 points, the separate
% NEXT: component medians are 78\% direct, 20\% specular, and 0.5\% diffuse. These
% NEXT: medians do not sum to 100\% because each is computed separately. The small
% NEXT: pooled diffuse median does not represent the six shadowed points.
% claim: ten_route_wbsar_route_quantiles
\begin{table*}[!t]
\caption{Fixed-route exposure summary. Whole-body SAR is normalized per unit $\rho_A P_{\mathrm{EIRP}}$. Excess above direct-path power is computed only at points with nonzero direct power.}
\label{tab:route-results}
\centering
\begin{tabular}{lrrrrr}
\toprule
& \multicolumn{3}{c}{Normalized whole-body SAR [m$^2$~kg$^{-1}$]} & & \\
\cmidrule(lr){2-4}
City & $q_{10}$ & $q_{50}$ & $q_{90}$ & \shortstack{Median excess\\above direct [dB]} & \shortstack{Shadowed\\points} \\
\midrule
Brussels & 0.02502 & 0.03119 & 0.03371 & 1.43 & 0 \\
Ghent & 0.05784 & 0.06205 & 0.06867 & 1.16 & 0 \\
Krakow & 0.006717 & 0.02252 & 0.04927 & 0.92 & 0 \\
London & 0.01175 & 0.01501 & 0.01744 & 0.90 & 0 \\
Madrid & 0.02091 & 0.02238 & 0.02317 & 1.55 & 0 \\
Mexico City & $1.01\times10^{-6}$ & 0.1291 & 0.2958 & 0.69 & 3 \\
Milan & 0.008529 & 0.009016 & 0.009861 & 1.14 & 0 \\
Prague & 0.01216 & 0.01307 & 0.01460 & 1.09 & 0 \\
Tokyo Hachiko & $3.63\times10^{-5}$ & 0.009674 & 0.02520 & 0.84 & 3 \\
Toulouse & 0.02431 & 0.03022 & 0.04292 & 0.84 & 0 \\
\bottomrule
\end{tabular}
\end{table*}
