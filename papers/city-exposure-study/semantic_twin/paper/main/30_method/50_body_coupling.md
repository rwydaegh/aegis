% PREV: The retained directional transfer has three nonoverlapping parts. Let $\mathcal{D}$ contain the visible direct paths, and let $\mathcal{S}_1$ contain the accepted order-1 all-specular paths. Their normalized masses are $\alpha_a=m_a^{(\mathrm{d})}/D_{\mathrm{ref}}$ and $\beta_b=m_b^{(\mathrm{s})}/D_{\mathrm{ref}}$. The first-diffuse estimate uses normalized cell masses $\widehat{\gamma}_q=\widehat{m}_q^{(\mathrm{f})}/D_{\mathrm{ref}}$. With $\delta_{\widehat{\mathbf{k}}}$ denoting a unit point mass in physical arrival direction $\widehat{\mathbf{k}}$, the directional measure is
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
% PREV: The first two sums retain the exact directions and masses of the direct and order-1 specular paths. They are not projected onto the angular grid. Only first-diffuse power is accumulated in the $Q$ Fibonacci cells. This term uses next-event estimation at the first blocking material vertex~\cite{veach}. The material model combines unpolarized Fresnel power with a Rayleigh roughness factor. The remaining power enters a Lambertian diffuse term, and the components add incoherently. A sampled first-diffuse path stops at that interaction, and specular orders above one are absent. Nonblocking woody atlas cells pass rays without attenuation. The full laws and evaluated parameters are given in the supplementary material.
% NEXT: Each replica launches 200,000 independent and identically distributed primary rays per standpoint and accumulates first-diffuse power in 4,096 fixed Fibonacci output cells. The exact direct and specular atoms bypass this grid. The cells are not ray-launch strata. The calculations use 16 replicas with seeds 7 through 22 and retain cumulative looks after 4, 8, 12, and 16 replicas. Only the first-diffuse estimate varies between replicas. Scalar endpoints and body fields are averaged before route statistics are computed. Route quantiles use NumPy linear interpolation over equally weighted fixed standpoints. The plotted empirical distributions use positions $(\operatorname{rank}-0.5)/n$. These quantities describe a selected route and do not estimate a pedestrian population. Multipath surplus is computed only where direct transfer is positive. A zero-direct standpoint remains in the whole-body SAR distribution but has no finite surplus value.
Direction remains explicit until body coupling. For outward body-surface normal $\widehat{\mathbf{n}}(\mathbf{r})$, define $g(\mathbf{r},\widehat{\mathbf{k}})=[\widehat{\mathbf{n}}(\mathbf{r})\cdot(-\widehat{\mathbf{k}})]_+$. The normalized absorbed power density is
\begin{equation}
\begin{aligned}
\widetilde{S}_{\mathrm{ab}}(\mathbf{r},\mathbf{x})
&\equiv\frac{S_{\mathrm{ab}}(\mathbf{r},\mathbf{x})}
{\rho_A P_{\mathrm{EIRP}}}
\\
&=T_0S_{\mathrm{ref}}(\mathbf{x})\Bigg[
\sum_{a\in\mathcal{D}}\alpha_a g(\mathbf{r},\widehat{\mathbf{k}}_a^{(\mathrm{d})}) \\
&\hspace{5.8em}+\sum_{b\in\mathcal{S}_1}\beta_b g(\mathbf{r},\widehat{\mathbf{k}}_b^{(\mathrm{s})}) \\
&\hspace{5.8em}+\sum_{q=1}^{Q}\widehat{\gamma}_q g(\mathbf{r},\widehat{\mathbf{k}}_q^{(\mathrm{f})})
\Bigg] .
\end{aligned}
\label{eq:body-coupling}
\end{equation}
Here, $T_0$ is the normal-incidence power-transmission coefficient obtained from the IT'IS tissue parameters at 15~GHz~\cite{itis}. The AEGIS level-2 implementation applies this one-sided local-incidence coupling to the Duke anatomical mesh~\cite{christ2010,aegis}. Thus, $\widetilde{S}_{\mathrm{ab}}$ is dimensionless. For body-element area $A_{\mathbf{r}}$ and body mass $m_{\mathrm{body}}$, the normalized integrated endpoints are
\begin{equation}
\begin{aligned}
\widetilde{P}_{\mathrm{abs}}(\mathbf{x})
&\equiv\frac{P_{\mathrm{abs}}(\mathbf{x})}{\rho_A P_{\mathrm{EIRP}}}
\\
&=\sum_{\mathbf{r}}A_{\mathbf{r}}\widetilde{S}_{\mathrm{ab}}(\mathbf{r},\mathbf{x}), \\
\widetilde{\mathrm{SAR}}_{\mathrm{wb}}(\mathbf{x})
&\equiv\frac{\mathrm{SAR}_{\mathrm{wb}}(\mathbf{x})}{\rho_A P_{\mathrm{EIRP}}}
\\
&=\frac{\widetilde{P}_{\mathrm{abs}}(\mathbf{x})}{m_{\mathrm{body}}} .
\end{aligned}
\label{eq:body-endpoints}
\end{equation}
$\widetilde{P}_{\mathrm{abs}}$ has units m$^2$, and $\widetilde{\mathrm{SAR}}_{\mathrm{wb}}$ has units m$^2$~kg$^{-1}$.

## reviews (paragraph)

_(empty, run /review to populate)_

## grinder notes

- Source: `docs/SPINE.md`, M4, `docs/ROOFLINE_CAMPAIGN_OPERATIONS.md`, and the established AEGIS surface-field relation retained in `paper/body.tex`.
- Guard: Body coupling keeps direct and specular atoms separate from the first-diffuse grid. No scalar total is redistributed over the body.
