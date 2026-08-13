<!-- AUTO_BEGIN: assembled -->
\section{Validation and Results}
\label{sec:results}

Table~\ref{tab:routes} defines the five fixed registered routes and their 73 standpoints. Every site uses the same 15~GHz frequency, 250~m-radius photogrammetric support mesh, and Duke body model with 56,024 surface elements, 72.4~kg mass, and route-tangent yaw. Each standpoint has 16 independent replicas with seeds 7 through 22. Each replica uses 200,000 IID primary rays and 4,096 fixed output directions for the first-diffuse term. The resulting 1,168 standpoint-replica fields contain 233.6 million primary rays. Numerical calculation time after scene preparation ranges from 29.79 to 69.02~s on one A6000 GPU. These times exclude acquisition, registration, depth estimation, and material-surface construction because the cold-stage timing record is incomplete.

The campaign manifests bind 42 files per site, and all 210 recorded file hashes pass verification. The direct, exact order-1 specular, and first-diffuse fields sum to the stored total with a maximum absolute residual of $1.735\times10^{-18}$~m$^{-2}$ across all 1,168 fields. The GPU body-coupling result also agrees with the double-precision CPU reference to a maximum relative difference of $6.64\times10^{-16}$ in the verified benchmark. These checks establish artifact identity, additive closure, and numerical parity. They do not provide an external validation of the complete city model.

The controlled comparison in Fig.~\ref{fig:controlled-validation} isolates the first-diffuse estimator before the city results. The open-square scene has 27 sources, six receivers, eight triangles, and one diffuse reflection. Specular reflection, refraction, and diffraction are absent. Deterministic surface quadrature uses 2,097,152 samples. The adjoint estimate uses 50,000 primary rays for each of four seeds, and Sionna RT provides an independent forward calculation with 50,000 samples per source for each of three seeds. The maximum bounced-transfer difference between the adjoint estimate and quadrature is 0.0616~dB. A separate audit of total transport gives a maximum adjoint-to-Sionna difference of 0.0344~dB. This total-transport value is not plotted in Fig.~\ref{fig:controlled-validation}, which shows one-reflection transfer and its error relative to quadrature. The comparison checks first-diffuse normalization, visibility, inverse-square loss, and cosine factors in this depth-1 scene. It does not cover the panorama-derived material surface, the exact specular term, or their combination in a city.

\begin{figure*}[!t]
\centering
\includegraphics[width=\textwidth]{figures/validation/validation.pdf}
\caption{Controlled validation of the first-diffuse transfer. (a) Deterministic surface quadrature, the adjoint estimate, and the independent Sionna RT forward calculation at six receivers. (b) Signed error relative to quadrature. Error bars give the standard error across four adjoint seeds and three Sionna seeds.}
\label{fig:controlled-validation}
\end{figure*}

Figure~\ref{fig:route-distributions} contains the fixed-route empirical distributions and route-mean component shares, while Table~\ref{tab:route-results} gives the central summaries and finite multipath surplus. Normalized whole-body SAR is reported in m$^2$~kg$^{-1}$ per unit $\rho_A P_{\mathrm{EIRP}}$. A physical deployment value therefore requires multiplication by its areal source density and EIRP. Panel (a) includes all 73 standpoints and marks the six points with zero direct and zero order-1 specular transfer. Across the five selected routes, the ratio between the largest and smallest route medians is 13.34. This comparison is conditional on the selected routes and does not define a city ranking. Mexico City and Tokyo Hachiko have the widest within-route ranges and contain the deep lower tails.

\begin{figure*}[!t]
\centering
\includegraphics[width=\textwidth]{figures/route_results/route_results.pdf}
\caption{Normalized whole-body SAR on the five fixed routes. (a) Midpoint empirical CDFs include all 73 registered standpoints. Hollow triangles mark the six standpoints with zero direct and order-1 specular transfer. (b) Additive contributions to route-mean whole-body SAR. The routes are fixed case studies, not city or population samples.}
\label{fig:route-distributions}
\end{figure*}

\begin{table*}[!t]
\caption{Fixed-route exposure summary. Whole-body SAR quantiles are normalized per unit $\rho_A P_{\mathrm{EIRP}}$ and have units m$^2$~kg$^{-1}$. Surplus uses finite-direct points only. The last column is the maximum pointwise total-transfer change from 12 to 16 replicas.}
\label{tab:route-results}
\centering
\begin{tabular}{lrrrrrr}
\toprule
Site & $q_{10}$ & $q_{50}$ & $q_{90}$ & Median surplus [dB] & \shortstack{Zero direct and\\order-1 specular} & \shortstack{Max total-transfer\\change [dB]} \\
\midrule
Korenmarkt & 0.057833 & 0.062045 & 0.068672 & 1.108 & 0 & 0.0000819 \\
Prague & 0.012157 & 0.013073 & 0.014594 & 1.061 & 0 & 0.0001559 \\
Madrid & 0.020913 & 0.022381 & 0.023171 & 1.534 & 0 & 0.0004083 \\
Mexico City & $9.92\times10^{-7}$ & 0.129062 & 0.295798 & 0.721 & 3 & 0.043625 \\
Tokyo Hachiko & $3.66\times10^{-5}$ & 0.009674 & 0.025200 & 0.828 & 3 & 0.019732 \\
\bottomrule
\end{tabular}
\end{table*}

The component shares in Fig.~\ref{fig:route-distributions}(b) are additive shares of route-mean whole-body SAR. Direct transport is the largest body contribution at all 67 nonshadowed points. Exact order-1 specular transport is never the largest body contribution. Mexico City points 0, 1, and 3 and Tokyo Hachiko points 13, 14, and 15 have zero direct and zero order-1 specular transport. First-diffuse transport is the only nonzero modeled contribution at these six points. Across all 73 points, the componentwise pooled median whole-body SAR shares are 77.662\% direct, 21.391\% exact order-1 specular, and 0.419\% first diffuse. The three medians need not sum to 100\% because each is taken separately over the pooled standpoint set. The small first-diffuse median therefore does not describe the six shadowed points.

The nested 12-to-16-replica comparison separates the central route statistic from the lower tail. Every route-median whole-body SAR changes by at most $5.90\times10^{-5}$~dB. The largest lower-decile point changes are 0.032226~dB in Mexico City and 0.017636~dB in Tokyo Hachiko. The maximum pointwise total-transfer changes in Table~\ref{tab:route-results} reach 0.043625 and 0.019732~dB at these two sites. At 16 replicas, their 90th-percentile total-transfer standard errors are 0.1461 and 0.0310~dB, respectively. Central route statistics are stable under the retained estimator. Individual lower-tail points in these two routes have greater relative uncertainty, so convergence is not established for every standpoint or for the complete lower tail. The complete convergence figure is provided in the supplementary material.

A paired material-evidence control was completed for Madrid and Mexico City. The control replaces the panorama-derived atlas with the declared geometric fallback while retaining the mesh, route, roofline source measure, body, seeds, sampling budget, and transport topology. Each reported change is $10\log_{10}(x_{\mathrm{atlas}}/x_{\mathrm{fallback}})$. The atlas-to-fallback changes in normalized whole-body SAR at Madrid are $+0.233$, $+0.249$, and $+0.269$~dB for $q_{10}$, $q_{50}$, and $q_{90}$. The corresponding changes at Mexico City are $+24.84$, $-0.158$, and $+0.104$~dB. The large Mexico City $q_{10}$ change is set by its three shadowed points, where both paired totals are near zero and first diffuse is the only nonzero modeled contribution. The direct term is identical in every pair. At Madrid, the atlas changes the route-median specular component by $+1.89$~dB and the first-diffuse component by $-12.43$~dB, while the total median changes by only $+0.249$~dB. The control therefore measures sensitivity to the complete evidence layer, including its material parameters and nonblocking semantic state. It does not measure material accuracy or isolate reflectance alone. Pointwise and component-level comparisons are provided in the supplementary material.
<!-- AUTO_END: assembled -->








## Aggregation notes (AI-owned)
