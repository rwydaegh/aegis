<!-- AUTO_BEGIN: assembled -->
\section{Method}
\label{sec:method}

\subsection{Study Configuration}
\label{sec:configuration}

Fig.~\ref{fig:configuration} shows the study configuration. A 360-degree street
image is aligned with a photogrammetric city mesh cropped to a 250~m radius
around the route. Object and material labels from the image are projected onto
the visible mesh triangles without changing their geometry. The roofline visible
from the route gives the possible transmitter locations. Fixed points along the
pedestrian route give the observation positions, and the anatomical body model
faces along the direction of travel at each point.

\begin{figure*}[!t]
  \centering
  \includegraphics[width=\textwidth]{figures/configuration/configuration.pdf}
  \caption{Study configuration at Prague Old Town Square. (a) A 360-degree street image is segmented, projected onto the city mesh, and converted to the material map used for ray tracing. (b) The 22 observation points and the visible roofline on a plan view. (c) Close-up of the route. The arrow shows the body model's direction of travel.}
  \label{fig:configuration}
\end{figure*}

Table~\ref{tab:routes} lists the five selected routes. Each route follows a
connected street corridor covered by aligned 360-degree street images. The
calculation places fixed observation points along that corridor, including
interpolated positions between image locations, so the number of images and
the number of observation points can differ. The 73 route points are fixed
observations, not a random sample of pedestrians or places. The body model
faces along the direction of travel, so a different route would change both
position and orientation.

\begin{table}[!t]
  \caption{Five fixed routes with observation-point counts, route spans, and computation times}
  \label{tab:routes}
  \centering
  \begin{tabular}{lrrr}
    \toprule
    Site & Route points & Route span (m) & Wall time (s) \\
    \midrule
    Ghent & 10 & 49.04 & 29.79 \\
    Prague & 22 & 119.39 & 69.02 \\
    Madrid & 14 & 73.47 & 40.70 \\
    Mexico City & 11 & 60.79 & 30.92 \\
    Tokyo Hachiko & 16 & 87.38 & 50.11 \\
    \midrule
    Total & 73 & 390.07 & 220.54 \\
    \bottomrule
  \end{tabular}
\end{table}

Two image-analysis models work in sequence. Mask2Former assigns a Vistas object
class (building, road, vegetation, etc.) to every image
pixel~\cite{mask2former,vistas}. SAM~3 then tests material and vegetation labels
inside the compatible object regions~\cite{sam3}. Both sets of labels are
projected onto the visible city mesh using the known camera position and viewing
direction. Where multiple images cover the same triangle, the labels are
combined into one material map, and every mapped triangle stays linked to its
source image. A mesh triangle changes material only when the object and
material labels agree and pass the acceptance tests. All other triangles keep
their default material. The prompts, alignment tests, rejected labels, and
mapping rules are given in the supplementary material.

Fig.~\ref{fig:flowchart} shows the computation and its input checks. A
hash-verified manifest lists every input file: aligned images, material map,
city mesh, route, roofline, body model, and transport settings. Only files whose
hashes match the manifest enter the five-site data set. The transport
calculation keeps direct, specular, and diffuse contributions separate until
the field is applied to the body. The five manifests contain 210 verified entries. Across the
resulting 1,168 directional body fields, the largest residual when the three
components are summed back to the stored total is
$1.735\times10^{-18}\,\mathrm{m}^{-2}$.

\begin{figure*}[!t]
  \centering
  \includegraphics[width=\textwidth]{figures/flowchart/flowchart.pdf}
  \caption{Flowchart of the computation and input checks. Aligned 360-degree street images and the city mesh give the material map. The fixed route and visible roofline give observation and transmitter positions. Transport retains direct, first-order specular, and first-diffuse terms. A hash-verified file list pins every input to the five-site result.}
  \label{fig:flowchart}
\end{figure*}

\subsection{Exposure Calculation}
\label{sec:exposure-calc}

The calculation uses a fixed route, city mesh, material map, and roofline
transmitter model. Every route point uses 15~GHz and a crop with radius
$R_{\mathrm{crop}}=250$~m, which gives
$A_{\mathrm{crop}}=\pi R_{\mathrm{crop}}^2=196{,}349.54$~m$^2$. The receiver
position $\mathbf{x}$ is the ray origin and body reference point. The body model faces along the local direction of travel. Index $i$
denotes a roofline segment, $r_i(\mathbf{x})$ is its range to the receiver,
and $\mathbf{r}$ is a position on the body surface. These assumptions are fixed
across replicas and sites.

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
\ell_i=\left\lVert\mathbf{p}_{i+1}-\mathbf{p}_i\right\rVert_2 \, .
\label{eq:source-measure}
\end{equation}
Thus, $N_{\mathrm{site}}$ sets the number of transmitters and $p_i$ assigns a
fraction of that number to segment $i$. Dividing by the total roofline length
ensures that splitting one segment into smaller numerical pieces does not add
transmitters. The baseline uses three-dimensional length rather than horizontal
projected length.

An unobstructed reference separates the source density from the scene geometry. The reference sums the inverse-square contribution of every roofline segment:
\begin{equation}
D_{\mathrm{ref}}(\mathbf{x})=
\sum_i\frac{p_i}{r_i(\mathbf{x})^2},
\qquad
S_{\mathrm{ref}}(\mathbf{x})=
\frac{A_{\mathrm{crop}}D_{\mathrm{ref}}(\mathbf{x})}{4\pi} \, .
\label{eq:reference-scale}
\end{equation}
No visibility test enters $D_{\mathrm{ref}}$. All reported quantities are
normalized per unit $\rho_A P_{\mathrm{EIRP}}$. Multiplication by
$\rho_A P_{\mathrm{EIRP}}$ recovers physical units, but only for a deployment
that follows the same roofline transmitter model. The calculation omits
transmitters and interactions outside the crop.

% claim: directional_component_representation
The propagation result at each observation point has direct, one-reflection
specular, and one-reflection diffuse parts. Let $\mathcal{D}$ contain the visible direct
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
\qquad Q=4096 \, .
\end{aligned}
\label{eq:first-material-transfer}
\end{equation}
The first two sums retain the exact directions and powers of the direct and
specular paths. They are not projected onto the angular grid. Only diffuse
power is accumulated in the $Q$ Fibonacci cells. Rays start at the receiver and
travel outward to the first blocking surface, as shown in
Fig.~\ref{fig:adjoint}. Next-event estimation then tests visibility from that surface to every roofline
segment~\cite{veach}. The
material model combines unpolarized Fresnel power with a Rayleigh roughness
term. The remaining power enters a Lambertian diffuse term, and the components
add incoherently. The sampled path ends after this diffuse reflection, and the
calculation omits further specular reflections. Woody vegetation identified in
the material map does not block rays because the city mesh has no canopy
volume. The supplementary material gives the full laws and parameter values.

\begin{figure*}[!t]
  \centering
  \includegraphics[width=\textwidth]{figures/adjoint/adjoint.pdf}
  \caption{Forward and adjoint sampling for the first-diffuse term. (a) A forward calculation launches rays from every roofline segment toward the observation point. (b) The adjoint calculation launches rays once from the observation point. At the first blocking surface, connections to every visible roofline segment are tested.}
  \label{fig:adjoint}
\end{figure*}

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
<!-- AUTO_END: assembled -->
