% PREV: An unobstructed reference keeps network scale separate from scene visibility. The reference includes the inverse-square geometry of the complete source curve:
% PREV: \begin{equation}
% PREV: D_{\mathrm{ref}}(\mathbf{x})=
% PREV: \sum_i\frac{p_i}{r_i(\mathbf{x})^2},
% PREV: \qquad
% PREV: S_{\mathrm{ref}}(\mathbf{x})=
% PREV: \frac{A_{\mathrm{crop}}D_{\mathrm{ref}}(\mathbf{x})}{4\pi} .
% PREV: \label{eq:reference-scale}
% PREV: \end{equation}
% PREV: No visibility test enters $D_{\mathrm{ref}}$. The reported transfer and body
% PREV: endpoints are normalized per unit $\rho_A P_{\mathrm{EIRP}}$. Multiplication by
% PREV: $\rho_A P_{\mathrm{EIRP}}$ gives a physical scale only for a deployment that
% PREV: follows the same roofline transmitter model. The calculation omits transmitters
% PREV: and interactions outside the crop.
% NEXT: \begin{figure*}[!t]
% NEXT:   \centering
% NEXT:   \includegraphics[width=\textwidth]{figures/adjoint/adjoint.pdf}
% NEXT:   \caption{Forward and adjoint sampling for the first-diffuse term. (a) A forward calculation launches rays from every roofline segment toward the route point. (b) The adjoint calculation launches rays once from the route point. At the first blocking surface, next-event estimation tests connections to the roofline.}
% NEXT:   \label{fig:adjoint}
% NEXT: \end{figure*}
% claim: directional_component_representation
The directional transfer has direct, one-reflection specular, and
one-reflection diffuse parts. Let $\mathcal{D}$ contain the visible direct
paths, and let $\mathcal{S}_1$ contain the accepted one-reflection specular
paths. Their normalized powers are
$\alpha_a=m_a^{(\mathrm{d})}/D_{\mathrm{ref}}$ and
$\beta_b=m_b^{(\mathrm{s})}/D_{\mathrm{ref}}$. The diffuse estimate uses
normalized angular-cell powers
$\widehat{\gamma}_q=\widehat{m}_q^{(\mathrm{f})}/D_{\mathrm{ref}}$. With
$\delta_{\widehat{\mathbf{k}}}$ denoting a unit point mass in physical arrival
direction $\widehat{\mathbf{k}}$, the directional distribution is
\begin{equation}
\begin{aligned}
\mu_{\mathbf{x}}={}&
\sum_{a\in\mathcal{D}}\alpha_a\delta_{\widehat{\mathbf{k}}_a^{(\mathrm{d})}} \\
&+\sum_{b\in\mathcal{S}_1}\beta_b\delta_{\widehat{\mathbf{k}}_b^{(\mathrm{s})}} \\
&+\sum_{q=1}^{Q}\widehat{\gamma}_q\delta_{\widehat{\mathbf{k}}_q^{(\mathrm{f})}},
\qquad Q=4096 .
\end{aligned}
\label{eq:first-material-transfer}
\end{equation}
The first two sums retain the exact directions and powers of the direct and
specular paths. They are not projected onto the angular grid. Only diffuse
power is accumulated in the $Q$ Fibonacci cells. Rays start at the receiver and
travel outward to the first blocking surface, as shown in
Fig.~\ref{fig:adjoint}. Next-event estimation then tests
a connection from that surface to every roofline segment~\cite{veach}. The
material model combines unpolarized Fresnel power with a Rayleigh roughness
term. The remaining power enters a Lambertian diffuse term, and the components
add incoherently. The sampled path ends after this diffuse reflection, and the
calculation omits further specular reflections. Woody vegetation identified in
the material map does not block rays because the city mesh has no canopy
volume. The supplementary material gives the full laws and parameter values.

## reviews (paragraph)

_(empty, run /review to populate)_

## grinder notes

- Source: `docs/FIRST_MATERIAL_INTERACTION_TRANSPORT.md`, `docs/CURRENT_PRODUCTION_CONTRACT.md`, and `docs/SPINE.md`, M3.
- Guard: This is a first-material transport decomposition, not a complete multipath or three-bounce model.
- Notation: Exact direct and specular paths are atoms. Only first-diffuse power uses the Fibonacci output cells.
