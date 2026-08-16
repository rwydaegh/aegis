% PREV: The exact positions of future transmitters are unknown, but elevated rooflines
% PREV: are plausible street-facing locations. The model therefore distributes the
% PREV: expected transmitters uniformly per unit physical length of the roofline visible
% PREV: from the route. Let $\rho_A$ be the expected active-site density and let
% PREV: $A_{\mathrm{crop}}$ be the crop area. For a roofline segment with endpoints
% PREV: $\mathbf{p}_i$ and $\mathbf{p}_{i+1}$, $\ell_i$ is its physical
% PREV: three-dimensional length. The expected number of transmitters and the fraction
% PREV: assigned to segment $i$ are
% PREV: \begin{equation}
% PREV: N_{\mathrm{site}}=\rho_A A_{\mathrm{crop}},
% PREV: \qquad
% PREV: p_i=\frac{\ell_i}{\sum_j \ell_j},
% PREV: \qquad
% PREV: \ell_i=\left\lVert\mathbf{p}_{i+1}-\mathbf{p}_i\right\rVert_2 .
% PREV: \label{eq:source-measure}
% PREV: \end{equation}
% PREV: Thus, $N_{\mathrm{site}}$ sets the number of transmitters and $p_i$ assigns a
% PREV: fraction of that number to segment $i$. Dividing by the total roofline length
% PREV: ensures that splitting one segment into smaller numerical pieces does not add
% PREV: transmitters. The baseline uses three-dimensional length rather than horizontal
% PREV: projected length.
% NEXT: % claim: directional_component_representation
% NEXT: The directional transfer has direct, one-reflection specular, and
% NEXT: one-reflection diffuse parts. Let $\mathcal{D}$ contain the visible direct
% NEXT: paths, and let $\mathcal{S}_1$ contain the accepted one-reflection specular
% NEXT: paths. Their normalized powers are
% NEXT: $\alpha_a=m_a^{(\mathrm{d})}/D_{\mathrm{ref}}$ and
% NEXT: $\beta_b=m_b^{(\mathrm{s})}/D_{\mathrm{ref}}$. The diffuse estimate uses
% NEXT: normalized angular-cell powers
% NEXT: $\widehat{\gamma}_q=\widehat{m}_q^{(\mathrm{f})}/D_{\mathrm{ref}}$. With
% NEXT: $\delta_{\widehat{\mathbf{k}}}$ denoting a unit point mass in physical arrival
% NEXT: direction $\widehat{\mathbf{k}}$, the directional distribution is
% NEXT: \begin{equation}
% NEXT: \begin{aligned}
% NEXT: \mu_{\mathbf{x}}={}&
% NEXT: \sum_{a\in\mathcal{D}}\alpha_a\delta_{\widehat{\mathbf{k}}_a^{(\mathrm{d})}} \\
% NEXT: &+\sum_{b\in\mathcal{S}_1}\beta_b\delta_{\widehat{\mathbf{k}}_b^{(\mathrm{s})}} \\
% NEXT: &+\sum_{q=1}^{Q}\widehat{\gamma}_q\delta_{\widehat{\mathbf{k}}_q^{(\mathrm{f})}},
% NEXT: \qquad Q=4096 .
% NEXT: \end{aligned}
% NEXT: \label{eq:first-material-transfer}
% NEXT: \end{equation}
% NEXT: The first two sums retain the exact directions and powers of the direct and
% NEXT: specular paths. They are not projected onto the angular grid. Only diffuse
% NEXT: power is accumulated in the $Q$ Fibonacci cells. Rays start at the receiver and
% NEXT: travel outward to the first blocking surface, as shown in
% NEXT: Fig.~\ref{fig:adjoint}. Next-event estimation then tests
% NEXT: a connection from that surface to every roofline segment~\cite{veach}. The
% NEXT: material model combines unpolarized Fresnel power with a Rayleigh roughness
% NEXT: term. The remaining power enters a Lambertian diffuse term, and the components
% NEXT: add incoherently. The sampled path ends after this diffuse reflection, and the
% NEXT: calculation omits further specular reflections. Woody vegetation identified in
% NEXT: the material map does not block rays because the city mesh has no canopy
% NEXT: volume. The supplementary material gives the full laws and parameter values.
An unobstructed reference keeps network scale separate from scene visibility. The reference includes the inverse-square geometry of the complete source curve:
\begin{equation}
D_{\mathrm{ref}}(\mathbf{x})=
\sum_i\frac{p_i}{r_i(\mathbf{x})^2},
\qquad
S_{\mathrm{ref}}(\mathbf{x})=
\frac{A_{\mathrm{crop}}D_{\mathrm{ref}}(\mathbf{x})}{4\pi} .
\label{eq:reference-scale}
\end{equation}
No visibility test enters $D_{\mathrm{ref}}$. The reported transfer and body
endpoints are normalized per unit $\rho_A P_{\mathrm{EIRP}}$. Multiplication by
$\rho_A P_{\mathrm{EIRP}}$ gives a physical scale only for a deployment that
follows the same roofline transmitter model. The calculation omits transmitters
and interactions outside the crop.

## reviews (paragraph)

_(empty, run /review to populate)_

## grinder notes

- Source: `docs/ROOFLINE_CAMPAIGN_OPERATIONS.md`, `docs/SPINE.md`, M2, and `docs/RESULTS_INVENTORY.md`.
- Guard: $D_{\mathrm{ref}}$ is intentionally unobstructed. It must not be described as visible direct transfer.
