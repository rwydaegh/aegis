% PREV: The last two blocks in Fig.~\ref{fig:flowchart} make the propagation-to-body
% PREV: handoff explicit. Accordingly, the calculation keeps each arrival direction
% PREV: until body coupling. For outward
% PREV: surface normal $\widehat{\mathbf{n}}(\mathbf{r})$, let
% PREV: $g(\mathbf{r},\widehat{\mathbf{k}})=[\widehat{\mathbf{n}}(\mathbf{r})\cdot
% PREV: (-\widehat{\mathbf{k}})]_+$. The normalized absorbed power density is
% PREV: \begin{equation}
% PREV: \widetilde{S}_{\mathrm{ab}}(\mathbf{r},\mathbf{x})
% PREV: \equiv\frac{S_{\mathrm{ab}}(\mathbf{r},\mathbf{x})}{\rho_A P_{\mathrm{EIRP}}}
% PREV: =T_0S_{\mathrm{ref}}(\mathbf{x})
% PREV: \int_{\mathbb{S}^2}g(\mathbf{r},\widehat{\mathbf{k}})\,
% PREV: \mathrm{d}\mu_{\mathbf{x}}(\widehat{\mathbf{k}}) .
% PREV: \label{eq:body-coupling}
% PREV: \end{equation}
% PREV: The angular integral sums the direct, specular, and diffuse arrivals while
% PREV: retaining their incoming directions.
% PREV: Here, $T_0$ is the normal-incidence power-transmission coefficient from the
% PREV: IT'IS tissue database at 15~GHz~\cite{itis}. It represents incoherent,
% PREV: unpolarized illumination. The function $g$ gives zero absorption where the
% PREV: surface faces away from the incoming direction. We apply this law to the
% PREV: 56,024-element Duke anatomical mesh~\cite{christ2010}. With triangle area
% PREV: $A_{\mathbf{r}}$ and body mass $m_{\mathrm{body}}$, the normalized endpoints are
% PREV: \begin{equation}
% PREV: \begin{aligned}
% PREV: \widetilde{P}_{\mathrm{abs}}(\mathbf{x})
% PREV: &=\sum_{\mathbf{r}}A_{\mathbf{r}}\widetilde{S}_{\mathrm{ab}}(\mathbf{r},\mathbf{x}), \\
% PREV: \widetilde{\mathrm{SAR}}_{\mathrm{wb}}(\mathbf{x})
% PREV: &=\frac{\widetilde{P}_{\mathrm{abs}}(\mathbf{x})}{m_{\mathrm{body}}} .
% PREV: \end{aligned}
% PREV: \label{eq:body-endpoints}
% PREV: \end{equation}
% PREV: $\widetilde{P}_{\mathrm{abs}}$ has units m$^2$, and
% PREV: $\widetilde{\mathrm{SAR}}_{\mathrm{wb}}$ has units m$^2$~kg$^{-1}$ per unit
% PREV: $\rho_A P_{\mathrm{EIRP}}$.
\subsection{Numerical settings and route statistics}
\label{sec:numerical-settings}

For each independent run, the calculation launches 200,000 primary rays per
observation point and collects single-reflection diffuse power in 4,096 fixed
angular cells. Direct and specular paths are not binned on this grid, which does
not control the launch directions. The calculations use 64 runs with seeds 7
through 70 and keep cumulative results after 4, 8, 12, 16, 32, 48, and 64 runs.
Only the diffuse estimate varies between runs. Whole-body SAR values and body-surface fields
are averaged before route statistics are computed. The ten routes give 10,432
directional body fields from 2.086 billion primary rays. Route quantiles use
linear interpolation over equally weighted points, and empirical distribution
positions are $(\operatorname{rank}-0.5)/n$. Excess above direct-path power is
computed only where direct power is positive. Points with zero direct power
remain in the SAR distribution but have no finite excess value. Ray calculation
takes 5.95 to 73.77~s per city on one NVIDIA A6000 GPU. These times exclude
image acquisition, alignment, depth estimation, and surface-label assignment
because their full times were not recorded.

## reviews (paragraph)

_(empty, run /review to populate)_

## grinder notes

- Source: `docs/CURRENT_PRODUCTION_CONTRACT.md`, `docs/RESULTS_INVENTORY.md`, and `docs/SPINE.md`, M5.
- Guard: The 4,096 Fibonacci cells contain only first-diffuse output. IID sampling is the production launch baseline, while rotated Fibonacci launch is diagnostic only.
