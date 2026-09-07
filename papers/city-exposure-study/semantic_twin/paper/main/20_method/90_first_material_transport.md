% PREV: An unobstructed reference separates source strength from scene geometry:
% PREV: \begin{equation}
% PREV: D_{\mathrm{ref}}(\mathbf{x})=
% PREV: \sum_i\frac{p_i}{r_i(\mathbf{x})^2},
% PREV: \qquad
% PREV: S_{\mathrm{ref}}(\mathbf{x})=
% PREV: \frac{A_{\mathrm{crop}}D_{\mathrm{ref}}(\mathbf{x})}{4\pi} \, .
% PREV: \label{eq:reference-scale}
% PREV: \end{equation}
% PREV: We apply no visibility test to $D_{\mathrm{ref}}$. All reported values are
% PREV: normalized per unit $\rho_A P_{\mathrm{EIRP}}$. Multiplication by
% PREV: $\rho_A P_{\mathrm{EIRP}}$ gives physical units, but only for a deployment
% PREV: that follows the same roofline transmitter model. The calculation omits
% PREV: transmitters and interactions outside the crop.
% NEXT: \begin{figure*}[!htb]
% NEXT:   \centering
% NEXT:   \includegraphics[width=\textwidth]{figures/adjoint/adjoint.pdf}
% NEXT:   \caption{Forward and adjoint sampling for the single-reflection diffuse component. (a) Forward sampling launches rays from every roofline segment. (b) Adjoint sampling launches one set of rays from the observation point and tests visible source connections at the first surface hit.}
% NEXT:   \label{fig:adjoint}
% NEXT: \end{figure*}
% claim: directional_component_representation
The propagation result at each observation point has direct, one-reflection
specular, and one-reflection diffuse parts. Let $\mathcal{D}$ contain visible direct
paths and $\mathcal{S}_1$ contain accepted one-reflection specular
paths. Their normalized powers are
$\alpha_a=m_a^{(\mathrm{d})}/D_{\mathrm{ref}}$ and
$\beta_b=m_b^{(\mathrm{s})}/D_{\mathrm{ref}}$. The diffuse estimate uses
normalized angular-cell powers
$\widehat{\gamma}_q=\widehat{m}_q^{(\mathrm{f})}/D_{\mathrm{ref}}$ in
$Q=4096$ fixed angular cells. With $\delta_{\widehat{\mathbf{k}}}$ denoting a unit point
mass in arrival direction $\widehat{\mathbf{k}}$, the directional distribution is
\begin{equation}
\begin{aligned}
\mu_{\mathbf{x}}={}&
\sum_{a\in\mathcal{D}}\alpha_a\delta_{\widehat{\mathbf{k}}_a^{(\mathrm{d})}}
+\sum_{b\in\mathcal{S}_1}\beta_b\delta_{\widehat{\mathbf{k}}_b^{(\mathrm{s})}} \\
&+\sum_{q=1}^{Q}\widehat{\gamma}_q\delta_{\widehat{\mathbf{k}}_q^{(\mathrm{f})}} .
\end{aligned}
\label{eq:first-material-transfer}
\end{equation}
The first two sums keep exact path directions and powers. Only diffuse power
uses the angular cells. Fig.~\ref{fig:adjoint} contrasts the two sampling paths
for this diffuse term. \emph{Adjoint ray tracing} launches rays from the
observation point and tests visibility from each first surface hit to every
roofline source~\cite{behlouli2014,cocheril2007}. This source connection is a next-event
estimate~\cite{veach}. The surface law combines unpolarized Fresnel power with
a Rayleigh roughness term. The surface law assigns the remaining reflected power to a
Lambertian diffuse component, and all components add incoherently. Each sampled
path ends after the diffuse reflection. Higher-order specular paths are also
omitted. Woody vegetation identified by the images is transparent to rays
because the city geometry has no canopy volume. The supplementary material gives the
full laws and parameters.

## reviews (paragraph)

_(empty, run /review to populate)_

## grinder notes

- Source: `docs/FIRST_MATERIAL_INTERACTION_TRANSPORT.md`, `docs/CURRENT_PRODUCTION_CONTRACT.md`, and `docs/SPINE.md`, M3.
- Guard: This is a first-material transport decomposition, not a complete multipath or three-bounce model.
- Notation: Exact direct and specular paths are atoms. Only first-diffuse power uses the Fibonacci output cells.
