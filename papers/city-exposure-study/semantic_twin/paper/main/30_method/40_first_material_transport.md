% PREV: An unobstructed reference keeps network scale separate from scene visibility. The reference includes the inverse-square geometry of the complete source curve:
% PREV: \begin{equation}
% PREV: D_{\mathrm{ref}}(\mathbf{x})=
% PREV: \sum_i\frac{p_i}{r_i(\mathbf{x})^2},
% PREV: \qquad
% PREV: S_{\mathrm{ref}}(\mathbf{x})=
% PREV: \frac{A_{\mathrm{crop}}D_{\mathrm{ref}}(\mathbf{x})}{4\pi} .
% PREV: \label{eq:reference-scale}
% PREV: \end{equation}
% PREV: No visibility test enters $D_{\mathrm{ref}}$. The reported transfer and body endpoints are normalized per unit $\rho_A P_{\mathrm{EIRP}}$. Multiplication by $\rho_A P_{\mathrm{EIRP}}$ gives a physical scale only for a deployment that follows the same conditional roofline source measure. Sources and interactions outside the crop are absent.
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
% NEXT: Here, $T_0$ is the normal-incidence power-transmission coefficient obtained from the IT'IS tissue parameters at 15~GHz~\cite{itis}. The AEGIS level-2 implementation applies this one-sided local-incidence coupling to the Duke anatomical mesh~\cite{christ2010,aegis}. Thus, $\widetilde{S}_{\mathrm{ab}}$ is dimensionless. For body-element area $A_{\mathbf{r}}$ and body mass $m_{\mathrm{body}}$, the normalized integrated endpoints are
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
% claim: directional_component_representation
The retained directional transfer has three nonoverlapping parts. Let $\mathcal{D}$ contain the visible direct paths, and let $\mathcal{S}_1$ contain the accepted order-1 all-specular paths. Their normalized masses are $\alpha_a=m_a^{(\mathrm{d})}/D_{\mathrm{ref}}$ and $\beta_b=m_b^{(\mathrm{s})}/D_{\mathrm{ref}}$. The first-diffuse estimate uses normalized cell masses $\widehat{\gamma}_q=\widehat{m}_q^{(\mathrm{f})}/D_{\mathrm{ref}}$. With $\delta_{\widehat{\mathbf{k}}}$ denoting a unit point mass in physical arrival direction $\widehat{\mathbf{k}}$, the directional measure is
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
The first two sums retain the exact directions and masses of the direct and order-1 specular paths. They are not projected onto the angular grid. Only first-diffuse power is accumulated in the $Q$ Fibonacci cells. This term uses next-event estimation at the first blocking material vertex~\cite{veach}. The material model combines unpolarized Fresnel power with a Rayleigh roughness factor. The remaining power enters a Lambertian diffuse term, and the components add incoherently. A sampled first-diffuse path stops at that interaction, and specular orders above one are absent. Nonblocking woody atlas cells pass rays without attenuation. The full laws and evaluated parameters are given in the supplementary material.

## reviews (paragraph)

_(empty, run /review to populate)_

## grinder notes

- Source: `docs/FIRST_MATERIAL_INTERACTION_TRANSPORT.md`, `docs/CURRENT_PRODUCTION_CONTRACT.md`, and `docs/SPINE.md`, M3.
- Guard: This is a first-material transport decomposition, not a complete multipath or three-bounce model.
- Notation: Exact direct and specular paths are atoms. Only first-diffuse power uses the Fibonacci output cells.
