# Route-conditioned exposure method

<!-- AUTO_BEGIN: assembled -->
\section{Fixed-Route Exposure Method}
\label{sec:method}

The calculation uses a fixed route, city mesh, material map, and roofline source
curve. Every route point uses 15~GHz and a crop with radius
$R_{\mathrm{crop}}=250$~m, which gives
$A_{\mathrm{crop}}=\pi R_{\mathrm{crop}}^2=196{,}349.54$~m$^2$. The receiver
position $\mathbf{x}$ is also the reciprocal ray origin and body reference
point. The phantom faces along the local direction of travel. Index $i$ denotes
a roofline segment, $r_i(\mathbf{x})$ is its range to the receiver, and
$\mathbf{r}$ is the position of a body surface element. These assumptions stay
fixed across replicas and sites.

The exact positions of future transmitters are unknown, but elevated rooflines
are plausible street-facing locations. The model therefore distributes the
expected transmitters uniformly per unit physical length of the roofline visible
from the route. Let $\rho_A$ be the expected active-site density and let
$A_{\mathrm{crop}}$ be the crop area. For a roofline segment with endpoints
$\mathbf{p}_i$ and $\mathbf{p}_{i+1}$, $\ell_i$ is its physical
three-dimensional length. The expected number of transmitters and the fraction
assigned to segment $i$ are
\begin{equation}
N_{\mathrm{site}}=\rho_A A_{\mathrm{crop}},
\qquad
p_i=\frac{\ell_i}{\sum_j \ell_j},
\qquad
\ell_i=\left\lVert\mathbf{p}_{i+1}-\mathbf{p}_i\right\rVert_2 .
\label{eq:source-measure}
\end{equation}
Thus, $N_{\mathrm{site}}$ sets the number of transmitters and $p_i$ assigns a
fraction of that number to segment $i$. Dividing by the total roofline length
ensures that splitting one segment into smaller numerical pieces does not add
transmitters. The baseline uses three-dimensional length rather than horizontal
projected length.

An unobstructed reference keeps network scale separate from scene visibility. The reference includes the inverse-square geometry of the complete source curve:
\begin{equation}
D_{\mathrm{ref}}(\mathbf{x})=
\sum_i\frac{p_i}{r_i(\mathbf{x})^2},
\qquad
S_{\mathrm{ref}}(\mathbf{x})=
\frac{A_{\mathrm{crop}}D_{\mathrm{ref}}(\mathbf{x})}{4\pi} .
\label{eq:reference-scale}
\end{equation}
No visibility test enters $D_{\mathrm{ref}}$. The reported transfer and body
endpoints are normalized per unit $\rho_A P_{\mathrm{EIRP}}$. Multiplication by
$\rho_A P_{\mathrm{EIRP}}$ gives a physical scale only for a deployment that
follows the same roofline transmitter model. The calculation omits transmitters
and interactions outside the crop.

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

\begin{figure*}[!t]
  \centering
  \includegraphics[width=\textwidth]{figures/adjoint/adjoint.pdf}
  \caption{Forward and adjoint sampling for the first-diffuse term. (a) A forward calculation launches rays from every roofline segment toward the route point. (b) The adjoint calculation launches rays once from the route point. At the first blocking surface, next-event estimation tests connections to the roofline.}
  \label{fig:adjoint}
\end{figure*}

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
Here, $T_0$ is the normal-incidence power-transmission coefficient obtained from
the IT'IS tissue parameters at 15~GHz~\cite{itis}. The implementation applies
this one-sided local-incidence coupling to the Duke anatomical mesh with the
published level-2 dosimetry kernel~\cite{christ2010,aegis}. Thus,
$\widetilde{S}_{\mathrm{ab}}$ is dimensionless. For the area
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
&=\frac{\widetilde{P}_{\mathrm{abs}}(\mathbf{x})}{m_{\mathrm{body}}} .
\end{aligned}
\label{eq:body-endpoints}
\end{equation}
$\widetilde{P}_{\mathrm{abs}}$ has units m$^2$, and $\widetilde{\mathrm{SAR}}_{\mathrm{wb}}$ has units m$^2$~kg$^{-1}$.

Each replica launches 200,000 independent and identically distributed primary
rays per route point and accumulates first-diffuse power in 4,096 fixed
Fibonacci output cells. Exact direct and specular paths bypass this grid. The
output cells do not control the launch directions. The calculations use 16
replicas with seeds 7 through 22 and retain cumulative results after 4, 8, 12,
and 16 replicas. Only the first-diffuse estimate varies between replicas.
Scalar quantities and body fields are averaged before route statistics are
computed. Route quantiles use NumPy linear interpolation over equally weighted
route points. The plotted empirical distributions use positions
$(\operatorname{rank}-0.5)/n$. These quantities describe a selected route and
do not estimate a pedestrian population. Multipath surplus is computed only
where direct transfer is positive. A zero-direct route point remains in the
whole-body SAR distribution but has no finite surplus value.
<!-- AUTO_END: assembled -->





















## section notes

- Five equation environments define the source measure, reference scale, retained transport, surface coupling, and integrated endpoints.
- Computational thresholds, chunks, cache controls, and backend details belong to the supplementary information.
