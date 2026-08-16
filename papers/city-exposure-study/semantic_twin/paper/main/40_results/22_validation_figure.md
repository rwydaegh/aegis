% PREV: % claim: controlled_depth1_validation
% PREV: The controlled comparison in Fig.~\ref{fig:controlled-validation} tests the
% PREV: first-diffuse estimator before the city results. The open-square scene has 27
% PREV: sources, six receivers, eight triangles, and one diffuse reflection. It has no
% PREV: specular reflection, refraction, or diffraction. Deterministic surface
% PREV: quadrature uses 2,097,152 samples. The adjoint estimate uses 50,000 primary rays
% PREV: for each of four seeds. An independent Sionna RT forward calculation uses
% PREV: 50,000 samples per source for each of three seeds. The maximum difference
% PREV: between the adjoint estimate and quadrature is 0.0616~dB for the reflected term.
% PREV: A separate test of total transport gives a maximum adjoint-to-Sionna difference
% PREV: of 0.0344~dB. Fig.~\ref{fig:controlled-validation} plots the one-reflection
% PREV: transfer and its error relative to quadrature, not the total-transport test. The
% PREV: comparison checks first-diffuse normalization, visibility, inverse-square loss,
% PREV: and cosine terms in this one-reflection scene. It does not cover the
% PREV: image-derived material map, exact specular transport, or their combination in a
% PREV: city.
% NEXT: % claim: route_median_contrast_factor
% NEXT: Fig.~\ref{fig:route-distributions} shows the fixed-route empirical distributions
% NEXT: and route-mean component shares. Table~\ref{tab:route-results} gives the central
% NEXT: summaries and finite multipath surplus. Normalized whole-body SAR is reported in
% NEXT: m$^2$~kg$^{-1}$ per unit $\rho_A P_{\mathrm{EIRP}}$. A physical deployment
% NEXT: value therefore requires multiplication by its areal source density and EIRP.
% NEXT: Panel (a) includes all 73 route points and marks the six points with zero direct
% NEXT: and zero order-1 specular transfer. The largest route median is 13.34 times the
% NEXT: smallest. The selected routes do not define a city ranking. Mexico City and
% NEXT: Tokyo Hachiko have the widest ranges along a route and the lowest tails.
\begin{figure*}[!t]
\centering
\includegraphics[width=\textwidth]{figures/validation/validation.pdf}
\caption{Controlled validation of the first-diffuse transfer. (a) Deterministic surface quadrature, the adjoint estimate, and the independent Sionna RT forward calculation at six receivers. (b) Signed error relative to quadrature. Error bars give the standard error across four adjoint seeds and three Sionna seeds.}
\label{fig:controlled-validation}
\end{figure*}
