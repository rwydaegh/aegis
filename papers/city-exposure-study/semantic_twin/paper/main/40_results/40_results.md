<!-- AUTO_BEGIN: assembled -->
\section{Results}
\label{sec:results}

\subsection{Validation}
\label{sec:validation}

% claim: controlled_depth1_validation
Validation against deterministic quadrature and Sionna RT tests the
single-reflection diffuse estimate. Fig.~\ref{fig:controlled-validation} shows
the comparison in an open-square scene with 27 sources, 6 receivers, 8
triangles, and one diffuse reflection. The scene has no specular reflection,
refraction, or diffraction. Deterministic surface quadrature uses 2,097,152
samples. The adjoint calculation uses 50,000 primary rays for each of four
seeds. The independent Sionna RT forward calculation uses 50,000 samples per
source for each of three seeds. The maximum adjoint-to-quadrature difference is
1.43\% for the reflected component. A separate comparison of total received
power gives a maximum adjoint-to-Sionna difference of 0.80\%. The figure shows
the reflected component and its signed percentage difference from quadrature. This test
covers diffuse normalization, visibility, inverse-square loss, and cosine terms
in a one-reflection scene. It does not validate the image-derived surface
materials, the specular component, or their combination in a city.

\begin{figure*}[!htb]
\centering
\includegraphics[width=\textwidth]{figures/validation/validation.pdf}
\caption{Controlled validation of the single-reflection diffuse component. (a) Deterministic surface quadrature, the adjoint estimate, and the independent Sionna RT forward calculation at six receivers. (b) Signed percentage difference from quadrature. Error bars give the standard error across four adjoint seeds and three Sionna seeds.}
\label{fig:controlled-validation}
\end{figure*}

\subsection{Route exposure}
\label{sec:route-exposure}

% claim: ten_route_median_contrast_factor
Fig.~\ref{fig:route-distributions} shows the fixed-route empirical distributions.
Table~\ref{tab:route-results} gives the route quantiles and excess above
direct-path power. Normalized whole-body SAR is reported in m$^2$~kg$^{-1}$ per
unit $\rho_A P_{\mathrm{EIRP}}$. A physical value requires multiplication by a
deployment's areal source density and EIRP. The figure includes all 163
observation points and marks the six with zero direct and zero
single-reflection specular power. The largest selected-route median (Mexico City,
0.1291~m$^2$~kg$^{-1}$) is 14.31 times the smallest (Milan,
0.009016~m$^2$~kg$^{-1}$). Mexico City and Tokyo Hachiko have the widest spread
along a route and the lowest tails.

\begin{figure*}[!htb]
\centering
\includegraphics[width=\textwidth,height=0.76\textheight,keepaspectratio]{figures/route_results/route_results.pdf}
\caption{Normalized whole-body SAR on the ten fixed routes. (a)~Empirical CDFs include all 163 observation points. Hollow triangles mark the six points with zero direct and zero single-reflection specular power. (b)~Route-mean component shares. The routes are case studies and support no city or population inference.}
\label{fig:route-distributions}
\end{figure*}

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
Mexico City & $9.92\times10^{-7}$ & 0.1291 & 0.2958 & 0.69 & 3 \\
Milan & 0.008529 & 0.009016 & 0.009861 & 1.14 & 0 \\
Prague & 0.01216 & 0.01307 & 0.01460 & 1.09 & 0 \\
Tokyo Hachiko & $3.63\times10^{-5}$ & 0.009674 & 0.02520 & 0.84 & 3 \\
Toulouse & 0.02431 & 0.03022 & 0.04292 & 0.84 & 0 \\
\bottomrule
\end{tabular}
\end{table*}

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

\subsection{Convergence across runs}
\label{sec:convergence}

% claim: ten_route_replica_convergence_48_to_64
Between 48 and 64 runs, the largest pointwise change in total received power is
0.32\% at a shadowed point in Mexico City. The next largest change is 0.13\% in
Tokyo Hachiko. The maximum is below 0.023\% on each of the other eight routes,
and every route-median whole-body SAR is stable. At one shadowed point in Mexico
City, the largest single-run diffuse estimate is 5,738 times the median run estimate. This
concentration explains the larger lower-tail variation. It does not measure
city-sampling or route-selection uncertainty. The supplementary material gives
the complete 48-to-64-run comparison.

\subsection{Material sensitivity}
\label{sec:material-sensitivity}

% claim: paired_material_evidence_control
A paired control for Madrid and Mexico City replaces all image-derived
materials with geometry-based defaults. The geometry, route, rooflines, body,
seeds, number of rays, and propagation steps remain unchanged. In Madrid, the
image-derived case increases normalized whole-body SAR by 5.5\%, 5.9\%, and
6.4\% at $q_{10}$, $q_{50}$, and $q_{90}$. In Mexico City, the image-derived case gives a roughly
305-fold larger $q_{10}$, a 3.6\% smaller median, and a 2.4\% larger $q_{90}$.
The large lower-tail ratio occurs at three shadowed points where both values are
near zero and only diffuse power is nonzero. Direct power is identical in every
pair. In Madrid, image-derived materials increase the median specular component
by 54\% and reduce the median diffuse component by 94\%, but increase the total
median by only 5.9\%. The control includes both surface parameters and the
treatment of woody vegetation as nonblocking. It does not measure material
accuracy or isolate reflectance alone. The supplementary material gives
pointwise and component results.
<!-- AUTO_END: assembled -->
