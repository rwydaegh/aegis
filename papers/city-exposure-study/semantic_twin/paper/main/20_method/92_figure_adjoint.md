% PREV: % claim: directional_component_representation
% PREV: The propagation result at each observation point has direct, one-reflection
% PREV: specular, and one-reflection diffuse parts. Let $\mathcal{D}$ contain visible direct
% PREV: paths and $\mathcal{S}_1$ contain accepted one-reflection specular
% PREV: paths. Their normalized powers are
% PREV: $\alpha_a=m_a^{(\mathrm{d})}/D_{\mathrm{ref}}$ and
% PREV: $\beta_b=m_b^{(\mathrm{s})}/D_{\mathrm{ref}}$. The diffuse estimate uses
% PREV: normalized angular-cell powers
% PREV: $\widehat{\gamma}_q=\widehat{m}_q^{(\mathrm{f})}/D_{\mathrm{ref}}$ in
% PREV: $Q=4096$ fixed angular cells. With $\delta_{\widehat{\mathbf{k}}}$ denoting a unit point
% PREV: mass in arrival direction $\widehat{\mathbf{k}}$, the directional distribution is
% PREV: \begin{equation}
% PREV: \begin{aligned}
% PREV: \mu_{\mathbf{x}}={}&
% PREV: \sum_{a\in\mathcal{D}}\alpha_a\delta_{\widehat{\mathbf{k}}_a^{(\mathrm{d})}}
% PREV: +\sum_{b\in\mathcal{S}_1}\beta_b\delta_{\widehat{\mathbf{k}}_b^{(\mathrm{s})}} \\
% PREV: &+\sum_{q=1}^{Q}\widehat{\gamma}_q\delta_{\widehat{\mathbf{k}}_q^{(\mathrm{f})}} .
% PREV: \end{aligned}
% PREV: \label{eq:first-material-transfer}
% PREV: \end{equation}
% PREV: The first two sums keep exact path directions and powers. Only diffuse power
% PREV: uses the angular cells. Fig.~\ref{fig:adjoint} contrasts the two sampling paths
% PREV: for this diffuse term. \emph{Adjoint ray tracing} launches rays from the
% PREV: observation point and tests visibility from each first surface hit to every
% PREV: roofline source~\cite{behlouli2014,cocheril2007}. This source connection is a next-event
% PREV: estimate~\cite{veach}. The surface law combines unpolarized Fresnel power with
% PREV: a Rayleigh roughness term. The surface law assigns the remaining reflected power to a
% PREV: Lambertian diffuse component, and all components add incoherently. Each sampled
% PREV: path ends after the diffuse reflection. Higher-order specular paths are also
% PREV: omitted. Woody vegetation identified by the images is transparent to rays
% PREV: because the city geometry has no canopy volume. The supplementary material gives the
% PREV: full laws and parameters.
% NEXT: The last two blocks in Fig.~\ref{fig:flowchart} make the propagation-to-body
% NEXT: handoff explicit. Accordingly, the calculation keeps each arrival direction
% NEXT: until body coupling. For outward
% NEXT: surface normal $\widehat{\mathbf{n}}(\mathbf{r})$, let
% NEXT: $g(\mathbf{r},\widehat{\mathbf{k}})=[\widehat{\mathbf{n}}(\mathbf{r})\cdot
% NEXT: (-\widehat{\mathbf{k}})]_+$. The normalized absorbed power density is
% NEXT: \begin{equation}
% NEXT: \widetilde{S}_{\mathrm{ab}}(\mathbf{r},\mathbf{x})
% NEXT: \equiv\frac{S_{\mathrm{ab}}(\mathbf{r},\mathbf{x})}{\rho_A P_{\mathrm{EIRP}}}
% NEXT: =T_0S_{\mathrm{ref}}(\mathbf{x})
% NEXT: \int_{\mathbb{S}^2}g(\mathbf{r},\widehat{\mathbf{k}})\,
% NEXT: \mathrm{d}\mu_{\mathbf{x}}(\widehat{\mathbf{k}}) .
% NEXT: \label{eq:body-coupling}
% NEXT: \end{equation}
% NEXT: The angular integral sums the direct, specular, and diffuse arrivals while
% NEXT: retaining their incoming directions.
% NEXT: Here, $T_0$ is the normal-incidence power-transmission coefficient from the
% NEXT: IT'IS tissue database at 15~GHz~\cite{itis}. It represents incoherent,
% NEXT: unpolarized illumination. The function $g$ gives zero absorption where the
% NEXT: surface faces away from the incoming direction. We apply this law to the
% NEXT: 56,024-element Duke anatomical mesh~\cite{christ2010}. With triangle area
% NEXT: $A_{\mathbf{r}}$ and body mass $m_{\mathrm{body}}$, the normalized endpoints are
% NEXT: \begin{equation}
% NEXT: \begin{aligned}
% NEXT: \widetilde{P}_{\mathrm{abs}}(\mathbf{x})
% NEXT: &=\sum_{\mathbf{r}}A_{\mathbf{r}}\widetilde{S}_{\mathrm{ab}}(\mathbf{r},\mathbf{x}), \\
% NEXT: \widetilde{\mathrm{SAR}}_{\mathrm{wb}}(\mathbf{x})
% NEXT: &=\frac{\widetilde{P}_{\mathrm{abs}}(\mathbf{x})}{m_{\mathrm{body}}} .
% NEXT: \end{aligned}
% NEXT: \label{eq:body-endpoints}
% NEXT: \end{equation}
% NEXT: $\widetilde{P}_{\mathrm{abs}}$ has units m$^2$, and
% NEXT: $\widetilde{\mathrm{SAR}}_{\mathrm{wb}}$ has units m$^2$~kg$^{-1}$ per unit
% NEXT: $\rho_A P_{\mathrm{EIRP}}$.
\begin{figure*}[!htb]
  \centering
  \includegraphics[width=\textwidth]{figures/adjoint/adjoint.pdf}
  \caption{Forward and adjoint sampling for the single-reflection diffuse component. (a) Forward sampling launches rays from every roofline segment. (b) Adjoint sampling launches one set of rays from the observation point and tests visible source connections at the first surface hit.}
  \label{fig:adjoint}
\end{figure*}

## reviews (figure)

_(empty: run the figure review pass to populate)_
