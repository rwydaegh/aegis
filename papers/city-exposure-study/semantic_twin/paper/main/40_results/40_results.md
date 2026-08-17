<!-- AUTO_BEGIN: assembled -->
\section{Validation and Results}
\label{sec:results}

% claim: current_campaign_contract
Table~\ref{tab:routes} defines the five fixed routes and their 73 observation
points. Every site uses 15~GHz and a photogrammetric city mesh cropped to a
250~m radius. The Duke body model has 56,024 surface elements and a mass of
72.4~kg, and faces along the direction of travel. Each point has 16 independent
replicas with seeds 7 through 22. Each replica uses 200,000 primary rays and
4,096 fixed Fibonacci output cells for the first-diffuse term. The resulting 1,168 body fields contain 233.6 million primary rays.
Calculation time for a prepared site ranges from 29.79 to 69.02~s on one A6000
GPU. These times exclude image acquisition, alignment, depth estimation, and
material mapping because the full preparation time was not recorded.

% claim: raw_component_closure
The calculation manifests list 42 files per site, and all 210 file hashes pass
verification. The direct, exact order-1 specular, and first-diffuse fields sum
to the stored total with a maximum absolute residual of
$1.735\times10^{-18}$~m$^{-2}$ across all 1,168 fields. The GPU body-coupling
result also agrees with the double-precision CPU reference to a maximum relative
difference of $6.64\times10^{-16}$ in the verified benchmark. These checks
confirm the input files, addition of components, and agreement between CPU and
GPU calculations. They do not externally validate the complete city model.

% claim: controlled_depth1_validation
The direct and specular paths are computed from exact geometry, but the
first-diffuse estimate depends on random ray sampling. The controlled comparison
in Fig.~\ref{fig:controlled-validation} tests this stochastic component before
the city results. The open-square scene has 27 sources, 6 receivers, 8 triangles, and one diffuse
reflection. It has no specular reflection, refraction, or diffraction. Deterministic surface
quadrature uses 2,097,152 samples. The adjoint estimate uses 50,000 primary rays
for each of four seeds. An independent Sionna RT forward calculation uses
50,000 samples per source for each of three seeds. The maximum difference
between the adjoint estimate and quadrature is 0.0616~dB for the reflected term.
A separate test of total transport gives a maximum adjoint-to-Sionna difference
of 0.0344~dB. Fig.~\ref{fig:controlled-validation} plots the one-reflection
transfer and its error relative to quadrature, not the total-transport test. The
comparison checks first-diffuse normalization, visibility, inverse-square loss,
and cosine terms in this one-reflection scene. It does not cover the
image-derived material map, exact specular transport, or their combination in a
city.

\begin{figure*}[!t]
\centering
\includegraphics[width=\textwidth]{figures/validation/validation.pdf}
\caption{Controlled validation of the first-diffuse transfer. (a) Deterministic surface quadrature, the adjoint estimate, and the independent Sionna RT forward calculation at six receivers. (b) Signed error relative to quadrature. Error bars give the standard error across four adjoint seeds and three Sionna seeds.}
\label{fig:controlled-validation}
\end{figure*}

% claim: route_median_contrast_factor
Fig.~\ref{fig:route-distributions} shows the fixed-route empirical distributions
and route-mean component shares. Table~\ref{tab:route-results} gives the central
summaries and finite multipath surplus. Normalized whole-body SAR is reported in
m$^2$~kg$^{-1}$ per unit $\rho_A P_{\mathrm{EIRP}}$. A physical whole-body SAR value therefore requires multiplication by the
deployment's areal source density and EIRP.
Panel (a) includes all 73 observation points and marks the six with zero direct
and zero order-1 specular transfer. The largest route median is 13.34 times the
smallest. Mexico City and Tokyo Hachiko have the widest spread along a route
and the lowest tails.

\begin{figure*}[!t]
\centering
\includegraphics[width=\textwidth]{figures/route_results/route_results.pdf}
\caption{Normalized whole-body SAR on the five fixed routes. (a) Empirical CDFs of all 73 observation points. Hollow triangles mark the six points with zero direct and zero order-1 specular transfer. (b) Additive component shares of route-mean whole-body SAR. These routes are fixed case studies, not city or population samples.}
\label{fig:route-distributions}
\end{figure*}

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

% claim: six_shadowed_standpoints
% claim: pooled_median_wbsar_component_shares
The component shares in Fig.~\ref{fig:route-distributions}(b) are additive
shares of route-mean whole-body SAR. Direct transport is the largest
contribution at all 67 points with line of sight. Exact order-1 specular
transport is never the largest. Mexico City points 0, 1, and 3 and Tokyo
Hachiko points 13, 14, and 15 have zero direct and zero order-1 specular
transport. First-diffuse transport is the only nonzero contribution at these six
points. Across all 73 points, the pooled component medians are 77.662\% direct,
21.391\% exact order-1 specular, and 0.419\% first diffuse. They do not sum to
100\% because each component has a separate median over the 73 route points. The
small first-diffuse median therefore does not describe the six fully shadowed
points.

% claim: ray_reached_evidence_coverage
The path audit assigns each retained material interaction to an image-mapped or
geometry-based surface. Pooled over the five routes and 16 seeds, image-mapped
surfaces account for 75.903\% of the reflected SAR. The
corresponding shares are 80.643\% for exact order-1 specular transport and
13.337\% for first-diffuse transport. The supplementary material gives the
complete split by material source.

% claim: replica_convergence_12_to_16
The nested 12-to-16-replica comparison separates the route median from the
lower tail. Every route-median whole-body SAR changes by at most
$5.90\times10^{-5}$~dB. The largest lower-decile changes are 0.032226~dB in
Mexico City and 0.017636~dB in Tokyo Hachiko. The maximum pointwise
total-transfer changes in Table~\ref{tab:route-results} reach 0.043625 and
0.019732~dB at these two sites. At 16 replicas, the 90th-percentile total-transfer standard errors are
0.1461~dB in Mexico City and 0.0310~dB in Tokyo Hachiko. The route medians are
stable at 16 replicas.

% claim: replica_convergence_48_to_64
A separate calculation reuses the first 16 replicas and extends every route
through 64 replicas. Between 48 and 64 replicas, the whole-body SAR
$q_{10}$ changes by 0.00344~dB in Mexico City and 0.00491~dB in Tokyo Hachiko.
The largest change among their six fully shadowed route points is 0.0125 and
0.0104~dB. Both lower tails remain stable through 64 replicas.
In Mexico City, the single strongest diffuse replica at one shadowed point
carries 5738 times the median replica contribution.
This result is specific to the fixed routes and excludes route-selection and
city-sampling uncertainty. The complete nested comparison is given in the
supplementary material.

% claim: paired_material_evidence_control
A paired control for Madrid and Mexico City replaces all image-mapped materials
with the default geometry-based materials while keeping the mesh, route,
roofline model, body, seeds, sampling budget, and transport steps identical.
Each reported change is
$10\log_{10}(x_{\mathrm{image}}/x_{\mathrm{geometry}})$. At Madrid the
image-to-geometry changes in normalized whole-body SAR are $+0.233$, $+0.249$,
and $+0.269$~dB for $q_{10}$, $q_{50}$, and $q_{90}$. At Mexico City the
corresponding changes are $+24.84$, $-0.158$, and $+0.104$~dB. The large
$q_{10}$ change comes from the three fully shadowed points, where both totals
are near zero and first-diffuse transport is the only nonzero contribution. The
direct term is identical in every pair. At Madrid, the image-derived map changes
the route-median specular component by $+1.89$~dB and the first-diffuse
component by $-12.43$~dB, but the total median changes by only $+0.249$~dB.
This control tests the complete material map, including its parameters and the
treatment of woody vegetation as nonblocking. It does not measure material
accuracy or isolate reflectance alone. The supplementary material gives
pointwise and component-level comparisons.
<!-- AUTO_END: assembled -->
