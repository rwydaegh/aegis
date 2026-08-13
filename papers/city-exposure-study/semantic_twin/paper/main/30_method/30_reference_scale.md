% PREV: The source model separates physical source scale from numerical placement. Let $\rho_A$ be the expected active-site density and let $A_{\mathrm{crop}}$ be the crop area. For a roofline element with endpoints $\mathbf{p}_i$ and $\mathbf{p}_{i+1}$, $\ell_i$ is its physical three-dimensional arc length. The expected site count and the conditional source weights are
% PREV: \begin{equation}
% PREV: N_{\mathrm{site}}=\rho_A A_{\mathrm{crop}},
% PREV: \qquad
% PREV: p_i=\frac{\ell_i}{\sum_j \ell_j},
% PREV: \qquad
% PREV: \ell_i=\left\lVert\mathbf{p}_{i+1}-\mathbf{p}_i\right\rVert_2 .
% PREV: \label{eq:source-measure}
% PREV: \end{equation}
% PREV: Thus, $N_{\mathrm{site}}$ sets the physical scale, whereas $p_i$ distributes that scale over the observed route-aligned roofline. The number of numerical elements is not a source count. Horizontal projected length is an explicit sensitivity option and is not used in the baseline.
% NEXT: The retained directional transfer has three nonoverlapping parts. Let $\mathcal{D}$ contain the visible direct paths, and let $\mathcal{S}_1$ contain the accepted order-1 all-specular paths. Their normalized masses are $\alpha_a=m_a^{(\mathrm{d})}/D_{\mathrm{ref}}$ and $\beta_b=m_b^{(\mathrm{s})}/D_{\mathrm{ref}}$. The first-diffuse estimate uses normalized cell masses $\widehat{\gamma}_q=\widehat{m}_q^{(\mathrm{f})}/D_{\mathrm{ref}}$. With $\delta_{\widehat{\mathbf{k}}}$ denoting a unit point mass in physical arrival direction $\widehat{\mathbf{k}}$, the directional measure is
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
% NEXT: The first two sums retain the exact directions and masses of the direct and order-1 specular paths. They are not projected onto the angular grid. Only first-diffuse power is accumulated in the $Q$ Fibonacci cells. This term uses next-event estimation at the first blocking material vertex~\cite{veach}. The material model combines unpolarized Fresnel power with a Rayleigh roughness factor. The remaining power enters a Lambertian diffuse term, and the components add incoherently. A sampled first-diffuse path stops at that interaction, and specular orders above one are absent. Nonblocking woody atlas cells pass rays without attenuation. The full laws and evaluated parameters are given in the supplementary material.
An unobstructed reference keeps network scale separate from scene visibility. The reference includes the inverse-square geometry of the complete source curve:
\begin{equation}
D_{\mathrm{ref}}(\mathbf{x})=
\sum_i\frac{p_i}{r_i(\mathbf{x})^2},
\qquad
S_{\mathrm{ref}}(\mathbf{x})=
\frac{A_{\mathrm{crop}}D_{\mathrm{ref}}(\mathbf{x})}{4\pi} .
\label{eq:reference-scale}
\end{equation}
No visibility test enters $D_{\mathrm{ref}}$. The reported transfer and body endpoints are normalized per unit $\rho_A P_{\mathrm{EIRP}}$. Multiplication by $\rho_A P_{\mathrm{EIRP}}$ gives a physical scale only for a deployment that follows the same conditional roofline source measure. Sources and interactions outside the crop are absent.

## reviews (paragraph)

_(empty, run /review to populate)_

## grinder notes

- Source: `docs/ROOFLINE_CAMPAIGN_OPERATIONS.md`, `docs/SPINE.md`, M2, and `docs/RESULTS_INVENTORY.md`.
- Guard: $D_{\mathrm{ref}}$ is intentionally unobstructed. It must not be described as visible direct transfer.
