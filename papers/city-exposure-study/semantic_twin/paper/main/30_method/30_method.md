# Route-conditioned exposure method

<!-- AUTO_BEGIN: assembled -->
\section{Route-Conditioned Exposure Method}
\label{sec:method}

The calculation is conditioned on a fixed route, support mesh, material surface, and roofline source curve. Every standpoint uses 15~GHz and a crop with radius $R_{\mathrm{crop}}=250$~m, which gives $A_{\mathrm{crop}}=\pi R_{\mathrm{crop}}^2=196{,}349.54$~m$^2$. The receiver position $\mathbf{x}$ is also the reciprocal ray origin and body reference point. The body yaw follows the local route tangent. Index $i$ denotes a numerical roofline element, $r_i(\mathbf{x})$ is its range to the receiver, and $\mathbf{r}$ denotes a body surface element. These assumptions remain fixed across replicas and sites.

The source model separates physical source scale from numerical placement. Let $\rho_A$ be the expected active-site density and let $A_{\mathrm{crop}}$ be the crop area. For a roofline element with endpoints $\mathbf{p}_i$ and $\mathbf{p}_{i+1}$, $\ell_i$ is its physical three-dimensional arc length. The expected site count and the conditional source weights are
\begin{equation}
N_{\mathrm{site}}=\rho_A A_{\mathrm{crop}},
\qquad
p_i=\frac{\ell_i}{\sum_j \ell_j},
\qquad
\ell_i=\left\lVert\mathbf{p}_{i+1}-\mathbf{p}_i\right\rVert_2 .
\label{eq:source-measure}
\end{equation}
Thus, $N_{\mathrm{site}}$ sets the physical scale, whereas $p_i$ distributes that scale over the observed route-aligned roofline. The number of numerical elements is not a source count. Horizontal projected length is an explicit sensitivity option and is not used in the baseline.

An unobstructed reference keeps network scale separate from scene visibility. The reference includes the inverse-square geometry of the complete source curve:
\begin{equation}
D_{\mathrm{ref}}(\mathbf{x})=
\sum_i\frac{p_i}{r_i(\mathbf{x})^2},
\qquad
S_{\mathrm{ref}}(\mathbf{x})=
\frac{A_{\mathrm{crop}}D_{\mathrm{ref}}(\mathbf{x})}{4\pi} .
\label{eq:reference-scale}
\end{equation}
No visibility test enters $D_{\mathrm{ref}}$. The reported transfer and body endpoints are normalized per unit $\rho_A P_{\mathrm{EIRP}}$. Multiplication by $\rho_A P_{\mathrm{EIRP}}$ gives a physical scale only for a deployment that follows the same conditional roofline source measure. Sources and interactions outside the crop are absent.

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

Each replica launches 200,000 independent and identically distributed primary rays per standpoint and accumulates first-diffuse power in 4,096 fixed Fibonacci output cells. The exact direct and specular atoms bypass this grid. The cells are not ray-launch strata. The calculations use 16 replicas with seeds 7 through 22 and retain cumulative looks after 4, 8, 12, and 16 replicas. Only the first-diffuse estimate varies between replicas. Scalar endpoints and body fields are averaged before route statistics are computed. Route quantiles use NumPy linear interpolation over equally weighted fixed standpoints. The plotted empirical distributions use positions $(\operatorname{rank}-0.5)/n$. These quantities describe a selected route and do not estimate a pedestrian population. Multipath surplus is computed only where direct transfer is positive. A zero-direct standpoint remains in the whole-body SAR distribution but has no finite surplus value.
<!-- AUTO_END: assembled -->














## section notes

- Five equation environments define the source measure, reference scale, retained transport, surface coupling, and integrated endpoints.
- Computational thresholds, chunks, cache controls, and backend details belong to the supplementary information.
