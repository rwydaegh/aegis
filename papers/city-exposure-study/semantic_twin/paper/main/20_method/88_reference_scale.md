% PREV: The possible roofline transmitters in Fig.~\ref{fig:flowchart} represent a
% PREV: future distributed massive MIMO (DMaMIMO) architecture only to
% PREV: define possible access-point locations~\cite{wydaeghe2026,ngo2017}. Therefore,
% PREV: the model uses visible rooflines as possible transmitter locations. The
% PREV: calculation treats the possible sites as independent power sources and
% PREV: distributes expected transmitters uniformly per
% PREV: unit physical length of the roofline visible from the route. The active-site density $\rho_A$ gives an
% PREV: expected count $N_{\mathrm{site}}=\rho_A A_{\mathrm{crop}}$. For a segment with
% PREV: endpoints $\mathbf{p}_i$ and $\mathbf{p}_{i+1}$, its source fraction is
% PREV: \begin{equation}
% PREV: p_i=\frac{\ell_i}{\sum_j \ell_j},\qquad
% PREV: \ell_i=\lVert\mathbf{p}_{i+1}-\mathbf{p}_i\rVert_2 .
% PREV: \label{eq:source-measure}
% PREV: \end{equation}
% PREV: The denominator prevents a numerical split of one segment from adding source
% PREV: power. The calculation uses three-dimensional length rather than horizontal
% PREV: length.
% NEXT: % claim: directional_component_representation
% NEXT: The propagation result at each observation point has direct, one-reflection
% NEXT: specular, and one-reflection diffuse parts. Let $\mathcal{D}$ contain visible direct
% NEXT: paths and $\mathcal{S}_1$ contain accepted one-reflection specular
% NEXT: paths. Their normalized powers are
% NEXT: $\alpha_a=m_a^{(\mathrm{d})}/D_{\mathrm{ref}}$ and
% NEXT: $\beta_b=m_b^{(\mathrm{s})}/D_{\mathrm{ref}}$. The diffuse estimate uses
% NEXT: normalized angular-cell powers
% NEXT: $\widehat{\gamma}_q=\widehat{m}_q^{(\mathrm{f})}/D_{\mathrm{ref}}$ in
% NEXT: $Q=4096$ fixed angular cells. With $\delta_{\widehat{\mathbf{k}}}$ denoting a unit point
% NEXT: mass in arrival direction $\widehat{\mathbf{k}}$, the directional distribution is
% NEXT: \begin{equation}
% NEXT: \begin{aligned}
% NEXT: \mu_{\mathbf{x}}={}&
% NEXT: \sum_{a\in\mathcal{D}}\alpha_a\delta_{\widehat{\mathbf{k}}_a^{(\mathrm{d})}}
% NEXT: +\sum_{b\in\mathcal{S}_1}\beta_b\delta_{\widehat{\mathbf{k}}_b^{(\mathrm{s})}} \\
% NEXT: &+\sum_{q=1}^{Q}\widehat{\gamma}_q\delta_{\widehat{\mathbf{k}}_q^{(\mathrm{f})}} .
% NEXT: \end{aligned}
% NEXT: \label{eq:first-material-transfer}
% NEXT: \end{equation}
% NEXT: The first two sums keep exact path directions and powers. Only diffuse power
% NEXT: uses the angular cells. Fig.~\ref{fig:adjoint} contrasts the two sampling paths
% NEXT: for this diffuse term. \emph{Adjoint ray tracing} launches rays from the
% NEXT: observation point and tests visibility from each first surface hit to every
% NEXT: roofline source~\cite{behlouli2014,cocheril2007}. This source connection is a next-event
% NEXT: estimate~\cite{veach}. The surface law combines unpolarized Fresnel power with
% NEXT: a Rayleigh roughness term. The surface law assigns the remaining reflected power to a
% NEXT: Lambertian diffuse component, and all components add incoherently. Each sampled
% NEXT: path ends after the diffuse reflection. Higher-order specular paths are also
% NEXT: omitted. Woody vegetation identified by the images is transparent to rays
% NEXT: because the city geometry has no canopy volume. The supplementary material gives the
% NEXT: full laws and parameters.
An unobstructed reference separates source strength from scene geometry:
\begin{equation}
D_{\mathrm{ref}}(\mathbf{x})=
\sum_i\frac{p_i}{r_i(\mathbf{x})^2},
\qquad
S_{\mathrm{ref}}(\mathbf{x})=
\frac{A_{\mathrm{crop}}D_{\mathrm{ref}}(\mathbf{x})}{4\pi} \, .
\label{eq:reference-scale}
\end{equation}
We apply no visibility test to $D_{\mathrm{ref}}$. All reported values are
normalized per unit $\rho_A P_{\mathrm{EIRP}}$. Multiplication by
$\rho_A P_{\mathrm{EIRP}}$ gives physical units, but only for a deployment
that follows the same roofline transmitter model. The calculation omits
transmitters and interactions outside the crop.

## reviews (paragraph)

_(empty, run /review to populate)_

## grinder notes

- Source: `docs/ROOFLINE_CAMPAIGN_OPERATIONS.md`, `docs/SPINE.md`, M2, and `docs/RESULTS_INVENTORY.md`.
- Guard: $D_{\mathrm{ref}}$ is intentionally unobstructed. It must not be described as visible direct transfer.
