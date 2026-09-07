% PREV: \begin{figure*}[!htb]
% PREV:   \centering
% PREV:   \includegraphics[width=\textwidth]{figures/adjoint/adjoint.pdf}
% PREV:   \caption{Forward and adjoint sampling for the single-reflection diffuse component. (a) Forward sampling launches rays from every roofline segment. (b) Adjoint sampling launches one set of rays from the observation point and tests visible source connections at the first surface hit.}
% PREV:   \label{fig:adjoint}
% PREV: \end{figure*}
% NEXT: \subsection{Numerical settings and route statistics}
% NEXT: \label{sec:numerical-settings}
% NEXT:
% NEXT: For each independent run, the calculation launches 200,000 primary rays per
% NEXT: observation point and collects single-reflection diffuse power in 4,096 fixed
% NEXT: angular cells. Direct and specular paths are not binned on this grid, which does
% NEXT: not control the launch directions. The calculations use 64 runs with seeds 7
% NEXT: through 70 and keep cumulative results after 4, 8, 12, 16, 32, 48, and 64 runs.
% NEXT: Only the diffuse estimate varies between runs. Whole-body SAR values and body-surface fields
% NEXT: are averaged before route statistics are computed. The ten routes give 10,432
% NEXT: directional body fields from 2.086 billion primary rays. Route quantiles use
% NEXT: linear interpolation over equally weighted points, and empirical distribution
% NEXT: positions are $(\operatorname{rank}-0.5)/n$. Excess above direct-path power is
% NEXT: computed only where direct power is positive. Points with zero direct power
% NEXT: remain in the SAR distribution but have no finite excess value. Ray calculation
% NEXT: takes 5.95 to 73.77~s per city on one NVIDIA A6000 GPU. These times exclude
% NEXT: image acquisition, alignment, depth estimation, and surface-label assignment
% NEXT: because their full times were not recorded.
The last two blocks in Fig.~\ref{fig:flowchart} make the propagation-to-body
handoff explicit. Accordingly, the calculation keeps each arrival direction
until body coupling. For outward
surface normal $\widehat{\mathbf{n}}(\mathbf{r})$, let
$g(\mathbf{r},\widehat{\mathbf{k}})=[\widehat{\mathbf{n}}(\mathbf{r})\cdot
(-\widehat{\mathbf{k}})]_+$. The normalized absorbed power density is
\begin{equation}
\widetilde{S}_{\mathrm{ab}}(\mathbf{r},\mathbf{x})
\equiv\frac{S_{\mathrm{ab}}(\mathbf{r},\mathbf{x})}{\rho_A P_{\mathrm{EIRP}}}
=T_0S_{\mathrm{ref}}(\mathbf{x})
\int_{\mathbb{S}^2}g(\mathbf{r},\widehat{\mathbf{k}})\,
\mathrm{d}\mu_{\mathbf{x}}(\widehat{\mathbf{k}}) .
\label{eq:body-coupling}
\end{equation}
The angular integral sums the direct, specular, and diffuse arrivals while
retaining their incoming directions.
Here, $T_0$ is the normal-incidence power-transmission coefficient from the
IT'IS tissue database at 15~GHz~\cite{itis}. It represents incoherent,
unpolarized illumination. The function $g$ gives zero absorption where the
surface faces away from the incoming direction. We apply this law to the
56,024-element Duke anatomical mesh~\cite{christ2010}. With triangle area
$A_{\mathbf{r}}$ and body mass $m_{\mathrm{body}}$, the normalized endpoints are
\begin{equation}
\begin{aligned}
\widetilde{P}_{\mathrm{abs}}(\mathbf{x})
&=\sum_{\mathbf{r}}A_{\mathbf{r}}\widetilde{S}_{\mathrm{ab}}(\mathbf{r},\mathbf{x}), \\
\widetilde{\mathrm{SAR}}_{\mathrm{wb}}(\mathbf{x})
&=\frac{\widetilde{P}_{\mathrm{abs}}(\mathbf{x})}{m_{\mathrm{body}}} .
\end{aligned}
\label{eq:body-endpoints}
\end{equation}
$\widetilde{P}_{\mathrm{abs}}$ has units m$^2$, and
$\widetilde{\mathrm{SAR}}_{\mathrm{wb}}$ has units m$^2$~kg$^{-1}$ per unit
$\rho_A P_{\mathrm{EIRP}}$.

## reviews (paragraph)

_(empty, run /review to populate)_

## grinder notes

- Source: `docs/SPINE.md`, M4, `docs/ROOFLINE_CAMPAIGN_OPERATIONS.md`, and the established AEGIS surface-field relation retained in `paper/body.tex`.
- Guard: Body coupling keeps direct and specular atoms separate from the first-diffuse grid. No scalar total is redistributed over the body.
