% PREV: Direction remains explicit until body coupling. For outward body-surface normal $\widehat{\mathbf{n}}(\mathbf{r})$, define $g(\mathbf{r},\widehat{\mathbf{k}})=[\widehat{\mathbf{n}}(\mathbf{r})\cdot(-\widehat{\mathbf{k}})]_+$. The normalized absorbed power density is
% PREV: \begin{equation}
% PREV: \begin{aligned}
% PREV: \widetilde{S}_{\mathrm{ab}}(\mathbf{r},\mathbf{x})
% PREV: &\equiv\frac{S_{\mathrm{ab}}(\mathbf{r},\mathbf{x})}
% PREV: {\rho_A P_{\mathrm{EIRP}}}
% PREV: \\
% PREV: &=T_0S_{\mathrm{ref}}(\mathbf{x})\Bigg[
% PREV: \sum_{a\in\mathcal{D}}\alpha_a g(\mathbf{r},\widehat{\mathbf{k}}_a^{(\mathrm{d})}) \\
% PREV: &\hspace{5.8em}+\sum_{b\in\mathcal{S}_1}\beta_b g(\mathbf{r},\widehat{\mathbf{k}}_b^{(\mathrm{s})}) \\
% PREV: &\hspace{5.8em}+\sum_{q=1}^{Q}\widehat{\gamma}_q g(\mathbf{r},\widehat{\mathbf{k}}_q^{(\mathrm{f})})
% PREV: \Bigg] .
% PREV: \end{aligned}
% PREV: \label{eq:body-coupling}
% PREV: \end{equation}
% PREV: Here, $T_0$ is the normal-incidence power-transmission coefficient obtained from
% PREV: the IT'IS tissue parameters at 15~GHz~\cite{itis}. The implementation applies
% PREV: this one-sided local-incidence coupling to the Duke anatomical mesh with the
% PREV: published level-2 dosimetry kernel~\cite{christ2010,aegis}. Thus,
% PREV: $\widetilde{S}_{\mathrm{ab}}$ is dimensionless. For the area
% PREV: $A_{\mathbf{r}}$ at position $\mathbf{r}$ and body mass
% PREV: $m_{\mathrm{body}}$, the normalized integrated quantities are
% PREV: \begin{equation}
% PREV: \begin{aligned}
% PREV: \widetilde{P}_{\mathrm{abs}}(\mathbf{x})
% PREV: &\equiv\frac{P_{\mathrm{abs}}(\mathbf{x})}{\rho_A P_{\mathrm{EIRP}}}
% PREV: \\
% PREV: &=\sum_{\mathbf{r}}A_{\mathbf{r}}\widetilde{S}_{\mathrm{ab}}(\mathbf{r},\mathbf{x}), \\
% PREV: \widetilde{\mathrm{SAR}}_{\mathrm{wb}}(\mathbf{x})
% PREV: &\equiv\frac{\mathrm{SAR}_{\mathrm{wb}}(\mathbf{x})}{\rho_A P_{\mathrm{EIRP}}}
% PREV: \\
% PREV: &=\frac{\widetilde{P}_{\mathrm{abs}}(\mathbf{x})}{m_{\mathrm{body}}} .
% PREV: \end{aligned}
% PREV: \label{eq:body-endpoints}
% PREV: \end{equation}
% PREV: $\widetilde{P}_{\mathrm{abs}}$ has units m$^2$, and $\widetilde{\mathrm{SAR}}_{\mathrm{wb}}$ has units m$^2$~kg$^{-1}$.
Each replica launches 200,000 independent and identically distributed primary
rays per route point and accumulates first-diffuse power in 4,096 fixed
Fibonacci output cells. Exact direct and specular paths bypass this grid. The output cells do not control the launch directions.
The calculations use 16 replicas with seeds 7 through 22 and retain cumulative
results after 4, 8, 12, and 16 replicas. Only the first-diffuse estimate varies
between replicas. Scalar quantities and body fields are averaged across replicas
before route statistics are computed. Route quantiles use linear interpolation
over equally weighted route points, and the plotted empirical distributions use
positions $(\operatorname{rank}-0.5)/n$. Multipath surplus is computed
only where direct transfer is positive. A route point with zero direct transfer
remains in the whole-body SAR distribution but has no finite surplus value.

## reviews (paragraph)

_(empty, run /review to populate)_

## grinder notes

- Source: `docs/CURRENT_PRODUCTION_CONTRACT.md`, `docs/RESULTS_INVENTORY.md`, and `docs/SPINE.md`, M5.
- Guard: The 4,096 Fibonacci cells contain only first-diffuse output. IID sampling is the production launch baseline, while rotated Fibonacci launch is diagnostic only.
