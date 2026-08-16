% PREV: % claim: directional_component_representation
% PREV: The directional transfer has direct, one-reflection specular, and
% PREV: one-reflection diffuse parts. Let $\mathcal{D}$ contain the visible direct
% PREV: paths, and let $\mathcal{S}_1$ contain the accepted one-reflection specular
% PREV: paths. Their normalized powers are
% PREV: $\alpha_a=m_a^{(\mathrm{d})}/D_{\mathrm{ref}}$ and
% PREV: $\beta_b=m_b^{(\mathrm{s})}/D_{\mathrm{ref}}$. The diffuse estimate uses
% PREV: normalized angular-cell powers
% PREV: $\widehat{\gamma}_q=\widehat{m}_q^{(\mathrm{f})}/D_{\mathrm{ref}}$. With
% PREV: $\delta_{\widehat{\mathbf{k}}}$ denoting a unit point mass in physical arrival
% PREV: direction $\widehat{\mathbf{k}}$, the directional distribution is
% PREV: \begin{equation}
% PREV: \begin{aligned}
% PREV: \mu_{\mathbf{x}}={}&
% PREV: \sum_{a\in\mathcal{D}}\alpha_a\delta_{\widehat{\mathbf{k}}_a^{(\mathrm{d})}} \\
% PREV: &+\sum_{b\in\mathcal{S}_1}\beta_b\delta_{\widehat{\mathbf{k}}_b^{(\mathrm{s})}} \\
% PREV: &+\sum_{q=1}^{Q}\widehat{\gamma}_q\delta_{\widehat{\mathbf{k}}_q^{(\mathrm{f})}},
% PREV: \qquad Q=4096 .
% PREV: \end{aligned}
% PREV: \label{eq:first-material-transfer}
% PREV: \end{equation}
% PREV: The first two sums retain the exact directions and powers of the direct and
% PREV: specular paths. They are not projected onto the angular grid. Only diffuse
% PREV: power is accumulated in the $Q$ Fibonacci cells. Rays start at the receiver and
% PREV: travel outward to the first blocking surface, as shown in
% PREV: Fig.~\ref{fig:adjoint}. Next-event estimation then tests
% PREV: a connection from that surface to every roofline segment~\cite{veach}. The
% PREV: material model combines unpolarized Fresnel power with a Rayleigh roughness
% PREV: term. The remaining power enters a Lambertian diffuse term, and the components
% PREV: add incoherently. The sampled path ends after this diffuse reflection, and the
% PREV: calculation omits further specular reflections. Woody vegetation identified in
% PREV: the material map does not block rays because the city mesh has no canopy
% PREV: volume. The supplementary material gives the full laws and parameter values.
% NEXT: Direction remains explicit until body coupling. For outward body-surface normal $\widehat{\mathbf{n}}(\mathbf{r})$, define $g(\mathbf{r},\widehat{\mathbf{k}})=[\widehat{\mathbf{n}}(\mathbf{r})\cdot(-\widehat{\mathbf{k}})]_+$. The normalized absorbed power density is
% NEXT: \begin{equation}
% NEXT: \begin{aligned}
% NEXT: \widetilde{S}_{\mathrm{ab}}(\mathbf{r},\mathbf{x})
% NEXT: &\equiv\frac{S_{\mathrm{ab}}(\mathbf{r},\mathbf{x})}
% NEXT: {\rho_A P_{\mathrm{EIRP}}}
% NEXT: \\
% NEXT: &=T_0S_{\mathrm{ref}}(\mathbf{x})\Bigg[
% NEXT: \sum_{a\in\mathcal{D}}\alpha_a g(\mathbf{r},\widehat{\mathbf{k}}_a^{(\mathrm{d})}) \\
% NEXT: &\hspace{5.8em}+\sum_{b\in\mathcal{S}_1}\beta_b g(\mathbf{r},\widehat{\mathbf{k}}_b^{(\mathrm{s})}) \\
% NEXT: &\hspace{5.8em}+\sum_{q=1}^{Q}\widehat{\gamma}_q g(\mathbf{r},\widehat{\mathbf{k}}_q^{(\mathrm{f})})
% NEXT: \Bigg] .
% NEXT: \end{aligned}
% NEXT: \label{eq:body-coupling}
% NEXT: \end{equation}
% NEXT: Here, $T_0$ is the normal-incidence power-transmission coefficient obtained from
% NEXT: the IT'IS tissue parameters at 15~GHz~\cite{itis}. The implementation applies
% NEXT: this one-sided local-incidence coupling to the Duke anatomical mesh with the
% NEXT: published level-2 dosimetry kernel~\cite{christ2010,aegis}. Thus,
% NEXT: $\widetilde{S}_{\mathrm{ab}}$ is dimensionless. For the area
% NEXT: $A_{\mathbf{r}}$ at position $\mathbf{r}$ and body mass
% NEXT: $m_{\mathrm{body}}$, the normalized integrated quantities are
% NEXT: \begin{equation}
% NEXT: \begin{aligned}
% NEXT: \widetilde{P}_{\mathrm{abs}}(\mathbf{x})
% NEXT: &\equiv\frac{P_{\mathrm{abs}}(\mathbf{x})}{\rho_A P_{\mathrm{EIRP}}}
% NEXT: \\
% NEXT: &=\sum_{\mathbf{r}}A_{\mathbf{r}}\widetilde{S}_{\mathrm{ab}}(\mathbf{r},\mathbf{x}), \\
% NEXT: \widetilde{\mathrm{SAR}}_{\mathrm{wb}}(\mathbf{x})
% NEXT: &\equiv\frac{\mathrm{SAR}_{\mathrm{wb}}(\mathbf{x})}{\rho_A P_{\mathrm{EIRP}}}
% NEXT: \\
% NEXT: &=\frac{\widetilde{P}_{\mathrm{abs}}(\mathbf{x})}{m_{\mathrm{body}}} .
% NEXT: \end{aligned}
% NEXT: \label{eq:body-endpoints}
% NEXT: \end{equation}
% NEXT: $\widetilde{P}_{\mathrm{abs}}$ has units m$^2$, and $\widetilde{\mathrm{SAR}}_{\mathrm{wb}}$ has units m$^2$~kg$^{-1}$.
\begin{figure*}[!t]
  \centering
  \includegraphics[width=\textwidth]{figures/adjoint/adjoint.pdf}
  \caption{Forward and adjoint sampling for the first-diffuse term. (a) A forward calculation launches rays from every roofline segment toward the route point. (b) The adjoint calculation launches rays once from the route point. At the first blocking surface, next-event estimation tests connections to the roofline.}
  \label{fig:adjoint}
\end{figure*}

## reviews (figure)

_(empty: run the figure review pass to populate)_
