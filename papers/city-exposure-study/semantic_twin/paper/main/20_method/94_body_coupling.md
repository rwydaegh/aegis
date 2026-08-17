% PREV: \begin{figure*}[!t]
% PREV:   \centering
% PREV:   \includegraphics[width=\textwidth]{figures/adjoint/adjoint.pdf}
% PREV:   \caption{Forward and adjoint sampling for the first-diffuse term. (a) A forward calculation launches rays from every roofline segment toward the observation point. (b) The adjoint calculation launches rays once from the observation point. At the first blocking surface, connections to every visible roofline segment are tested.}
% PREV:   \label{fig:adjoint}
% PREV: \end{figure*}
% NEXT: Each replica launches 200,000 independent and identically distributed primary
% NEXT: rays per route point and accumulates first-diffuse power in 4,096 fixed
% NEXT: Fibonacci output cells. Exact direct and specular paths bypass this grid. The output cells do not control the launch directions.
% NEXT: The calculations use 16 replicas with seeds 7 through 22 and retain cumulative
% NEXT: results after 4, 8, 12, and 16 replicas. Only the first-diffuse estimate varies
% NEXT: between replicas. Scalar quantities and body fields are averaged across replicas
% NEXT: before route statistics are computed. Route quantiles use linear interpolation
% NEXT: over equally weighted route points, and the plotted empirical distributions use
% NEXT: positions $(\operatorname{rank}-0.5)/n$. Multipath surplus is computed
% NEXT: only where direct transfer is positive. A route point with zero direct transfer
% NEXT: remains in the whole-body SAR distribution but has no finite surplus value.
The arrival directions are carried through to the body. For outward body-surface normal $\widehat{\mathbf{n}}(\mathbf{r})$, define $g(\mathbf{r},\widehat{\mathbf{k}})=[\widehat{\mathbf{n}}(\mathbf{r})\cdot(-\widehat{\mathbf{k}})]_+$. The normalized absorbed power density is
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
\Bigg] \, .
\end{aligned}
\label{eq:body-coupling}
\end{equation}
Here, $T_0$ is the normal-incidence power-transmission coefficient from
the IT'IS tissue database at 15~GHz~\cite{itis}. It approximates the
absorption cross section for incoherent, unpolarized illumination. The
function $g$ sets the absorbed fraction to zero where the surface faces away
from the incoming direction. The calculation applies this directional
absorption to the 56,024-element Duke anatomical mesh~\cite{christ2010}.
Because all quantities are normalized by $\rho_A P_{\mathrm{EIRP}}$,
$\widetilde{S}_{\mathrm{ab}}$ is dimensionless. For the triangle area
$A_{\mathbf{r}}$ at position $\mathbf{r}$ and body mass
$m_{\mathrm{body}}$, the normalized integrated quantities are
\begin{equation}
\begin{aligned}
\widetilde{P}_{\mathrm{abs}}(\mathbf{x})
&\equiv\frac{P_{\mathrm{abs}}(\mathbf{x})}{\rho_A P_{\mathrm{EIRP}}}
\\
&=\sum_{\mathbf{r}}A_{\mathbf{r}}\widetilde{S}_{\mathrm{ab}}(\mathbf{r},\mathbf{x}), \\
\widetilde{\mathrm{SAR}}_{\mathrm{wb}}(\mathbf{x})
&\equiv\frac{\mathrm{SAR}_{\mathrm{wb}}(\mathbf{x})}{\rho_A P_{\mathrm{EIRP}}}
\\
&=\frac{\widetilde{P}_{\mathrm{abs}}(\mathbf{x})}{m_{\mathrm{body}}} \, .
\end{aligned}
\label{eq:body-endpoints}
\end{equation}
$\widetilde{P}_{\mathrm{abs}}$ has units m$^2$, and $\widetilde{\mathrm{SAR}}_{\mathrm{wb}}$ has units m$^2$~kg$^{-1}$.

## reviews (paragraph)

_(empty, run /review to populate)_

## grinder notes

- Source: `docs/SPINE.md`, M4, `docs/ROOFLINE_CAMPAIGN_OPERATIONS.md`, and the established AEGIS surface-field relation retained in `paper/body.tex`.
- Guard: Body coupling keeps direct and specular atoms separate from the first-diffuse grid. No scalar total is redistributed over the body.
