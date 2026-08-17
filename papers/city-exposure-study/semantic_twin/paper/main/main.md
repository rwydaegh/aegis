<!-- AUTO_BEGIN: assembled -->
\documentclass{ieeeaccess}

\usepackage{cite}
\usepackage{amsmath,amssymb,amsfonts}
\usepackage{bm}
\usepackage{booktabs}
\usepackage{graphicx}
\usepackage{textcomp}
\usepackage{url}

\vol{16}
\year{2026}

\graphicspath{{../figures/}{figures/}}

\newcommand{\rhoA}{\rho_{\mathrm{A}}}
\newcommand{\Peirp}{P_{\mathrm{EIRP}}}
\newcommand{\wbsar}{\mathrm{SAR}_{\mathrm{wb}}}

\begin{document}

% PROVISIONAL AUTHOR METADATA: Robin-only draft pending final author confirmation.
% Publication history and DOI are supplied after acceptance.
% FUNDING: insert the confirmed sponsor statement with \tfootnote before submission.
\history{}
\doi{}

\title{Image-Informed Urban Propagation and Route-Level Body Exposure at 15 GHz}

\author{\uppercase{Robin Wydaeghe}\authorrefmark{1}}

\address[1]{WAVES Research Group, Department of Information Technology,
Ghent University--imec, Technologiepark-Zwijnaarde 126, 9052 Ghent, Belgium
(e-mail: robin.wydaeghe@ugent.be)}

\markboth
{R. Wydaeghe: Image-Informed Urban Propagation and Route-Level Body Exposure}
{R. Wydaeghe: Image-Informed Urban Propagation and Route-Level Body Exposure}

\corresp{Corresponding author: Robin Wydaeghe
(e-mail: robin.wydaeghe@ugent.be).}

\begin{abstract}
Street-level radiofrequency exposure varies along a pedestrian route because
buildings change the direct and reflected fields, surface materials affect how
much power returns to the street, and the human body absorbs differently
depending on the direction of arrival. This study projects 360-degree street
images onto a photogrammetric city mesh to identify surface materials along five
pedestrian routes at 15~GHz. Transmitters are placed along the visible
roofline in proportion to its physical length. All results are normalized per
unit product of areal source density and effective isotropic radiated power
(EIRP). The transport model treats direct
paths and one specular reflection exactly, estimates one diffuse reflection, and
stops. The arriving fields and their directions are then applied to a
56,024-element Duke body model. The five routes contain 73 fixed observation
points, each calculated with 16 independent replicas of 200,000 primary rays
and 4,096 angular output cells. In a controlled test scene, the adjoint estimate and deterministic quadrature
differ by at most 0.0616~dB for the reflected term. An independent forward
tracer gives a maximum difference of 0.0344~dB. Route-median
whole-body specific absorption rate differs by a factor of 13.34 across the
five routes. Direct paths carry the largest share at all 67 points with line of
sight, while the diffuse reflection is the only nonzero modeled contribution at
six fully shadowed points. The maximum change from 12 to 16 replicas is
0.0436~dB, though lower-tail estimates in Mexico City and Tokyo are less
stable. These results describe five selected routes under a fixed model and do
not estimate city-wide or deployed-network exposure.
\end{abstract}

\begin{keywords}
Body dosimetry, image-informed propagation, ray tracing, street imagery, urban
propagation, whole-body specific absorption rate.
\end{keywords}

\titlepgskip=-21pt
\maketitle

\section{Introduction}\label{sec:introduction}

\IEEEPARstart{A}{s} wireless networks expand into higher frequency bands,
the built environment plays a larger role in determining the radiofrequency
field that reaches a pedestrian~\cite{itu2040}. Along a city street, received
power can change over a few meters. A person walking past a row of buildings
can move from a clear view of a rooftop transmitter into a shadow where
buildings block the direct field and only reflected power reaches the
street. The facade materials then determine how much power returns to the
street~\cite{itu2040,vitucci}. This variation also matters after the field
arrives: whole-body absorption depends on the direction of arrival and on how
the body is oriented, so a single power value at a single point does not
describe exposure along a walking route. A route-level calculation must keep
the arrival direction until the field is applied to the
body~\cite{icnirp}.

Ray tracing computes detailed propagation paths between transmitters and
receivers in a three-dimensional city model~\cite{sionna}. It has been used for
city-scale downlink exposure using published base-station
locations~\cite{leeman}, and to compute propagation and body exposure along an
outdoor pedestrian path~\cite{wydaeghe2026}. Stochastic geometry models
describe exposure when individual transmitter locations are not
known~\cite{wiame}, while precomputed body coefficients separate the incident
field from the absorption calculation~\cite{varsier}. Together, these studies
cover deterministic urban propagation, spatial source models, and the
directional absorption step that converts the arriving field into absorbed power
on the body. Because they use different source assumptions, their reported
exposure values are not directly comparable without a common source
normalization.

A photogrammetric city mesh gives accurate building geometry, but its triangles
carry no material information. Street-level images can fill that gap. The
Mapillary Vistas dataset provides a taxonomy for dense segmentation of street
scenes~\cite{vistas}. Kamari \emph{et al.} segment street-level images, project
the resulting material classes onto city geometry, and use that geometry in
millimeter-wave ray tracing~\cite{mmsv}. Xia \emph{et al.} use semantic
point-cloud classification and detailed scene reconstruction for outdoor ray
tracing at 2.8~GHz~\cite{xia2024}. Projecting image-derived materials onto
city geometry is therefore established. This study does not claim any of these
operations as new. It uses them to build a material map around fixed pedestrian
routes, keeping the default geometry-based material wherever the images give no
reliable label.

This study combines these established parts in one fixed model. Each 360-degree
street image is aligned with the same photogrammetric city mesh used for ray
tracing, and the image labels are projected onto that mesh to produce a material map. A common transmitter model distributes sources along the visible
roofline at every site. Rooflines are a natural choice: they are elevated, street-facing, and visible
from the route. Distributing transmitters in proportion to roofline length
avoids tying the result to any particular deployment. The ray tracer keeps the direct, specular, and diffuse components separate,
preserving their arrival directions, until the field is applied to the body. The transport model treats direct paths and one
specular reflection exactly, estimates one diffuse reflection, and stops there.
The route points are fixed case studies, not a population sample, and the
roofline transmitters are a model, not a measured deployment. To the best of the author's knowledge, prior work has not combined aligned
360-degree street images, a common roofline transmitter model, and separate
transport components with their arrival directions in a single route-level body
exposure calculation.

This study applies the method at 15~GHz to five selected routes containing 73
fixed observation points. Every result is normalized per unit active-source areal
density and per unit effective isotropic radiated power (EIRP). The route-median
whole-body SAR values differ by a factor of 13.34 across the five routes. These
results describe fixed routes under one source and transport model. They do not
estimate population exposure or deployed-network exposure.

This work makes the following three contributions.
\begin{enumerate}
  \item Aligned 360-degree street images supply traceable material labels to
  the same city mesh used for ray tracing. Surfaces without a reliable image
  label keep their geometry-based material.

  \item A roofline transmitter model and transport calculation keep direct,
  specular, and diffuse power separate, with arrival directions, until the
  field is applied to the body.

  \item A five-route application reports fixed-route exposure distributions,
  controlled first-diffuse validation, replica convergence, and the retained
  transport at the six observation points where buildings block all direct and
  specular paths.
\end{enumerate}

\section{Configuration and Surface Mapping}
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
    Korenmarkt & 10 & 49.04 & 29.79 \\
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

\section{Fixed-Route Exposure Method}
\label{sec:method}

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
the IT'IS tissue database at 15~GHz~\cite{itis}. The function $g$ sets the
absorbed fraction to zero where the surface faces away from the incoming
direction. The calculation applies this directional absorption to the Duke anatomical mesh
using the published surface-field method~\cite{christ2010,aegis}.
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

\section{Validation and Results}
\label{sec:results}

Table~\ref{tab:routes} defines the five fixed routes and their 73 observation
points. Every site uses 15~GHz and a photogrammetric city mesh cropped to a
250~m radius. The Duke body model has 56,024 surface elements and a mass of
72.4~kg, and faces along the direction of travel. Each point has 16 independent
replicas with seeds 7 through 22. Each replica uses 200,000 primary rays and
4,096 fixed Fibonacci output cells for the first-diffuse term. The resulting 1,168 body fields contain 233.6 million primary rays.
Calculation time for a prepared site ranges from 29.79 to 69.02~s on one A6000
GPU. These times exclude image acquisition, alignment, depth estimation, and
material mapping because the full preparation time was not recorded.

The calculation manifests list 42 files per site, and all 210 file hashes pass
verification. The direct, exact order-1 specular, and first-diffuse fields sum
to the stored total with a maximum absolute residual of
$1.735\times10^{-18}$~m$^{-2}$ across all 1,168 fields. The GPU body-coupling
result also agrees with the double-precision CPU reference to a maximum relative
difference of $6.64\times10^{-16}$ in the verified benchmark. These checks
confirm the input files, addition of components, and agreement between CPU and
GPU calculations. They do not externally validate the complete city model.

The direct and specular paths are computed from exact geometry, but the
first-diffuse estimate depends on random ray sampling. The controlled comparison
in Fig.~\ref{fig:controlled-validation} tests this stochastic component before
the city results. The open-square scene has 27 sources, 6 receivers, 8 triangles, and one diffuse
reflection. It has no specular reflection, refraction, or diffraction. Deterministic surface
quadrature uses 2,097,152 samples. The adjoint estimate uses 50,000 primary rays
for each of four seeds. An independent Sionna RT forward calculation uses
50,000 samples per source for each of three seeds. The maximum difference
between the adjoint estimate and quadrature is 0.0616~dB for the reflected term.
A separate test of total transport gives a maximum adjoint-to-Sionna difference
of 0.0344~dB. Fig.~\ref{fig:controlled-validation} plots the one-reflection
transfer and its error relative to quadrature, not the total-transport test. The
comparison checks first-diffuse normalization, visibility, inverse-square loss,
and cosine terms in this one-reflection scene. It does not cover the
image-derived material map, exact specular transport, or their combination in a
city.

\begin{figure*}[!t]
\centering
\includegraphics[width=\textwidth]{figures/validation/validation.pdf}
\caption{Controlled validation of the first-diffuse transfer. (a) Deterministic surface quadrature, the adjoint estimate, and the independent Sionna RT forward calculation at six receivers. (b) Signed error relative to quadrature. Error bars give the standard error across four adjoint seeds and three Sionna seeds.}
\label{fig:controlled-validation}
\end{figure*}

Fig.~\ref{fig:route-distributions} shows the fixed-route empirical distributions
and route-mean component shares. Table~\ref{tab:route-results} gives the central
summaries and finite multipath surplus. Normalized whole-body SAR is reported in
m$^2$~kg$^{-1}$ per unit $\rho_A P_{\mathrm{EIRP}}$. A physical whole-body SAR value therefore requires multiplication by the
deployment's areal source density and EIRP.
Panel (a) includes all 73 observation points and marks the six with zero direct
and zero order-1 specular transfer. The largest route median is 13.34 times the
smallest. Mexico City and Tokyo Hachiko have the widest spread along a route
and the lowest tails.

\begin{figure*}[!t]
\centering
\includegraphics[width=\textwidth]{figures/route_results/route_results.pdf}
\caption{Normalized whole-body SAR on the five fixed routes. (a) Empirical CDFs of all 73 observation points. Hollow triangles mark the six points with zero direct and zero order-1 specular transfer. (b) Additive component shares of route-mean whole-body SAR. These routes are fixed case studies, not city or population samples.}
\label{fig:route-distributions}
\end{figure*}

\begin{table*}[!t]
\caption{Fixed-route exposure summary. Whole-body SAR quantiles are normalized per unit $\rho_A P_{\mathrm{EIRP}}$ and have units m$^2$~kg$^{-1}$. Surplus is computed only at points with nonzero direct transfer. The last column is the maximum pointwise total-transfer change from 12 to 16 replicas.}
\label{tab:route-results}
\centering
\begin{tabular}{lrrrrrr}
\toprule
Site & $q_{10}$ & $q_{50}$ & $q_{90}$ & Median surplus [dB] & \shortstack{Zero direct and\\order-1 specular} & \shortstack{Max total-transfer\\change [dB]} \\
\midrule
Korenmarkt & 0.057833 & 0.062045 & 0.068672 & 1.108 & 0 & 0.0000819 \\
Prague & 0.012157 & 0.013073 & 0.014594 & 1.061 & 0 & 0.0001559 \\
Madrid & 0.020913 & 0.022381 & 0.023171 & 1.534 & 0 & 0.0004083 \\
Mexico City & $9.92\times10^{-7}$ & 0.129062 & 0.295798 & 0.721 & 3 & 0.043625 \\
Tokyo Hachiko & $3.66\times10^{-5}$ & 0.009674 & 0.025200 & 0.828 & 3 & 0.019732 \\
\bottomrule
\end{tabular}
\end{table*}

The component shares in Fig.~\ref{fig:route-distributions}(b) are additive
shares of route-mean whole-body SAR. Direct transport is the largest
contribution at all 67 points with line of sight. Exact order-1 specular
transport is never the largest. Mexico City points 0, 1, and 3 and Tokyo
Hachiko points 13, 14, and 15 have zero direct and zero order-1 specular
transport. First-diffuse transport is the only nonzero contribution at these six
points. Across all 73 points, the pooled component medians are 77.662\% direct,
21.391\% exact order-1 specular, and 0.419\% first diffuse. They do not sum to
100\% because each component has a separate median over the 73 route points. The
small first-diffuse median therefore does not describe the six fully shadowed
points.

The path audit assigns each retained material interaction to an image-mapped or
geometry-based surface. Pooled over the five routes and 16 seeds, image-mapped
surfaces account for 75.903\% of the reflected SAR. The
corresponding shares are 80.643\% for exact order-1 specular transport and
13.337\% for first-diffuse transport. The supplementary material gives the
complete split by material source.

The nested 12-to-16-replica comparison separates the route median from the
lower tail. Every route-median whole-body SAR changes by at most
$5.90\times10^{-5}$~dB. The largest lower-decile changes are 0.032226~dB in
Mexico City and 0.017636~dB in Tokyo Hachiko. The maximum pointwise
total-transfer changes in Table~\ref{tab:route-results} reach 0.043625 and
0.019732~dB at these two sites. At 16 replicas, the 90th-percentile total-transfer standard errors are
0.1461~dB in Mexico City and 0.0310~dB in Tokyo Hachiko. The route medians are
stable at 16 replicas.

A separate calculation reuses the first 16 replicas and extends every route
through 64 replicas. Between 48 and 64 replicas, the whole-body SAR
$q_{10}$ changes by 0.00344~dB in Mexico City and 0.00491~dB in Tokyo Hachiko.
The largest change among their six fully shadowed route points is 0.0125 and
0.0104~dB. Both lower tails remain stable through 64 replicas.
In Mexico City, the single strongest diffuse replica at one shadowed point
carries 5738 times the median replica contribution.
This result is specific to the fixed routes and excludes route-selection and
city-sampling uncertainty. The complete nested comparison is given in the
supplementary material.

A paired control for Madrid and Mexico City replaces all image-mapped materials
with the default geometry-based materials while keeping the mesh, route,
roofline model, body, seeds, sampling budget, and transport steps identical.
Each reported change is
$10\log_{10}(x_{\mathrm{image}}/x_{\mathrm{geometry}})$. At Madrid the
image-to-geometry changes in normalized whole-body SAR are $+0.233$, $+0.249$,
and $+0.269$~dB for $q_{10}$, $q_{50}$, and $q_{90}$. At Mexico City the
corresponding changes are $+24.84$, $-0.158$, and $+0.104$~dB. The large
$q_{10}$ change comes from the three fully shadowed points, where both totals
are near zero and first-diffuse transport is the only nonzero contribution. The
direct term is identical in every pair. At Madrid, the image-derived map changes
the route-median specular component by $+1.89$~dB and the first-diffuse
component by $-12.43$~dB, but the total median changes by only $+0.249$~dB.
This control tests the complete material map, including its parameters and the
treatment of woody vegetation as nonblocking. It does not measure material
accuracy or isolate reflectance alone. The supplementary material gives
pointwise and component-level comparisons.

\section{Discussion}
\label{sec:discussion}

The factor of 13.34 between the largest and smallest route medians shows that
body exposure differs substantially among the five routes, even after the same
source-density and EIRP normalization. This contrast reflects the geometry,
visible roofline, mapped materials, and visibility conditions of each route.
Each empirical distribution therefore describes only that fixed route and its
observation points.

The first-diffuse component is small at most points (0.419\% pooled median),
but it is the only nonzero contribution at the six fully shadowed points. Its
small share where line of sight exists does not make it dispensable where
buildings block all direct and specular paths. A transport model that omits the
diffuse term would assign zero exposure to those six positions.

The paired material control tests the effect of image-derived materials on the
body results. The direct term is identical in both cases, so all observed
changes come from the materials used by the reflected and diffuse terms. In
Madrid, the specular and first-diffuse component changes have opposite signs,
while the route-median normalized whole-body SAR changes by only $0.249$~dB.
The Mexico City route median changes by $-0.158$~dB. Its much larger lower-tail
ratio comes from the three fully shadowed route points where both estimates are
close to zero, not from a central effect. The paired cases differ in their
assigned materials and in their treatment of woody canopy. The image-derived
case treats identified canopy as transparent because the city mesh has no canopy
volume. The comparison therefore measures sensitivity to both the material
assignment and the vegetation rule together, and does not establish material
accuracy on its own.

Several limits restrict what the results can say. The study covers five
selected routes at 15~GHz and one body model that faces along each walk.
Results are normalized per unit areal source density and EIRP. Scaling to a
specific deployment is valid only if its transmitter positions follow the
assumed roofline model. The transport model stops after one diffuse event and
omits all later interactions and higher-order specular paths. The controlled
comparison validates the first-diffuse component in a one-reflection scene. It
does not validate the city calculations, which also use image-derived materials
and exact specular transport. The 16 replicas quantify estimator randomness but
not uncertainty in image-to-mesh alignment, geometry, material labels, route
choice, transmitter placement, body shape, or body orientation. The five-site
computation takes less than 70~s per prepared site on the tested GPU, but image
acquisition and material mapping take longer and do not yet have a complete
timing record. A ten-location geometric fixed-grid diagnostic in the supplementary material
checks coverage and orientation sensitivity over a wider set of
configurations.

The first priority is source calibration and end-to-end validation of the city
calculation against outdoor field measurements of the directional field before
body coupling. Second, higher specular orders and paths beyond the first diffuse
event can be added through paired studies that report their change in whole-body
SAR, variance, and computation time. Third, several routes at the same site can
quantify route-selection variation before the site set is enlarged. Other
frequencies, body models, and orientations can then test the remaining range of
validity. Each extension should also report what fraction of the surfaces
reached by the modeled paths carries an image-derived material.

\section{Conclusion}\label{sec:conclusion}

This study aligned 360-degree street images with a photogrammetric city mesh to
map surface materials around fixed pedestrian routes. A roofline transmitter model and a directional absorption step then produced
normalized whole-body SAR along each route, with all results per unit
$\rho_A P_{\mathrm{EIRP}}$. In a controlled one-reflection scene, the
first-diffuse estimate differed from deterministic quadrature by at most
0.0616\,dB and from an independent Sionna RT forward calculation by at most
0.0621\,dB. Across 73 observation points on five routes, route-median
whole-body SAR values differed by a factor of 13.34. Direct transport was
largest at all 67 points with line of sight, while first-diffuse transport was
the only nonzero contribution at the six fully shadowed points. The route
medians were stable at 16 replicas, but the fully shadowed lower tails had
larger estimator uncertainty. These results do not rank cities or predict
deployed-network exposure.

The image-to-mesh material mapping took effect mainly through the specular
component. A paired control at two sites showed route-median whole-body SAR
changes of $+0.249$ and $-0.158$~dB when the image-derived materials were
replaced by the geometry defaults. The method runs in under 70~s per prepared
site on one GPU. The main open items are outdoor field validation against the
full city model and a measured transmitter source distribution.

\section*{Data and Code Availability}

The verified five-site data, manifests, analysis scripts, and figure scripts
are kept in the study repository. A stable public archive with a versioned
digital object identifier will be deposited before publication. The 360-degree
street images and commercial photogrammetric tiles are governed by their
providers' terms and are not redistributed. Their identifiers and the alignment
manifests are kept so the inputs can be reacquired where the licenses allow it.

\section*{Acknowledgment}

OpenAI Codex~\cite{openai_codex} was used to draft and edit text in all
manuscript sections and to assist with plotting code and manuscript checks. The author reviewed the
generated text and code and verified the scientific claims, numerical values,
references, and final text.

\begin{thebibliography}{99}

\bibitem{itu2040}
International Telecommunication Union, ``Effects of building materials and
structures on radio-wave propagation in the range of 1 MHz to 450 GHz,''
Recommendation ITU-R P.2040-4, 2025.

\bibitem{vitucci}
E.~M.~Vitucci, V.~Degli-Esposti, F.~Mani \emph{et al.}, ``Tuning ray tracing for
mm-wave coverage prediction in outdoor urban scenarios,'' \emph{Radio Sci.},
vol. 54, no. 11, pp. 1112--1128, 2019,
doi: 10.1029/2019RS006869.

\bibitem{icnirp}
International Commission on Non-Ionizing Radiation Protection, ``Guidelines for
limiting exposure to electromagnetic fields (100 kHz to 300 GHz),'' \emph{Health
Phys.}, vol. 118, no. 5, pp. 483--524, 2020,
doi: 10.1097/HP.0000000000001210.

\bibitem{sionna}
J.~Hoydis, F.~A\"it~Aoudia, S.~Cammerer, M.~Nimier-David, N.~Binder,
G.~Marcus, and A.~Keller, ``Sionna RT: Differentiable ray tracing for radio
propagation modeling,'' in \emph{Proc. IEEE Globecom Workshops}, 2023,
pp. 317--321, doi: 10.1109/GCWkshps58843.2023.10465179.

\bibitem{leeman}
M.~Leeman, R.~Wydaeghe, J.~Van~der~Straeten, S.~Goegebeur, G.~Vermeeren, and
W.~Joseph, ``City-scale spatio-temporal modeling of 5G downlink exposure of
users and non-users by ray-tracing in a real urban environment,'' \emph{IEEE
Access}, vol. 13, pp. 30894--30906, 2025,
doi: 10.1109/ACCESS.2025.3541352.

\bibitem{wydaeghe2026}
R.~Wydaeghe, S.~Shikhantsov, G.~Vermeeren, L.~Martens, E.~Tanghe, and W.~Joseph,
``Hybrid ray-tracing-QuaDRiGa/FDTD method for realistic 28 GHz exposure with 6G
CF-MaMIMO in 3D outdoor environments,'' \emph{npj Wireless Technol.}, vol. 2,
no. 1, Art. no. 13, 2026, doi: 10.1038/s44459-026-00031-4.

\bibitem{wiame}
C.~Wiame, S.~Demey, L.~Vandendorpe, P.~De~Doncker, and C.~Oestges, ``Joint data
rate and EMF exposure analysis in Manhattan environments: Stochastic geometry
and ray tracing approaches,'' \emph{IEEE Trans. Veh. Technol.}, vol. 73, no. 1,
pp. 894--908, 2024, doi: 10.1109/TVT.2023.3307226.

\bibitem{varsier}
N.~Varsier, D.~Plets, Y.~Corre, G.~Vermeeren, W.~Joseph, S.~Aerts, L.~Martens,
and J.~Wiart, ``A novel method to assess human population exposure induced by a
wireless cellular network,'' \emph{Bioelectromagnetics}, vol. 36, no. 6,
pp. 451--463, 2015, doi: 10.1002/bem.21928.

\bibitem{vistas}
G.~Neuhold, T.~Ollmann, S.~Rota~Bul\`o, and P.~Kontschieder,
``The Mapillary Vistas dataset for semantic understanding of street scenes,''
in \emph{Proc. IEEE Int. Conf. Comput. Vis.}, 2017, pp. 5000--5009,
doi: 10.1109/ICCV.2017.534.

\bibitem{mmsv}
A.~Kamari, Y.~Chae, and P.~Pathak, ``mmSV: mmWave vehicular networking using
Street View imagery in urban environments,'' in \emph{Proc. 29th Annu. Int.
Conf. Mobile Comput. Netw.}, 2023, pp. 1--16,
doi: 10.1145/3570361.3613291.

\bibitem{xia2024}
G.~Xia, C.~Zhou, F.~Zhang, Z.~Cui, C.~Liu, H.~Ji, X.~Zhang, Z.~Zhao, and
Y.~Xiao, ``Path loss prediction in urban environments with Sionna-RT based on
accurate propagation scene models at 2.8 GHz,'' \emph{IEEE Trans. Antennas
Propag.}, vol. 72, no. 10, pp. 7986--7997, 2024,
doi: 10.1109/TAP.2024.3451214.

\bibitem{mask2former}
B.~Cheng, I.~Misra, A.~G.~Schwing, A.~Kirillov, and R.~Girdhar,
``Masked-attention mask transformer for universal image segmentation,'' in
\emph{Proc. IEEE/CVF Conf. Comput. Vis. Pattern Recognit.}, 2022,
pp. 1290--1299.

\bibitem{sam3}
N.~Carion \emph{et al.}, ``SAM 3: Segment anything with concepts,''
arXiv:2511.16719, 2025, doi: 10.48550/arXiv.2511.16719.

\bibitem{veach}
E.~Veach, \emph{Robust Monte Carlo Methods for Light Transport Simulation}.
Stanford, CA, USA: Stanford Univ., Ph.D. dissertation, 1997.

\bibitem{itis}
P.~A.~Hasgall \emph{et al.}, ``IT'IS database for thermal and electromagnetic
parameters of biological tissues,'' Version 4.2, 2024,
doi: 10.13099/VIP21000-04-2.

\bibitem{christ2010}
A.~Christ \emph{et al.}, ``The Virtual Family: Development of surface-based
anatomical models of two adults and two children for dosimetric simulations,''
\emph{Phys. Med. Biol.}, vol. 55, no. 2, pp. N23--N38, 2010,
doi: 10.1088/0031-9155/55/2/N01.

\bibitem{aegis}
R.~Wydaeghe, ``AEGIS: Absorbed power density on human bodies in wireless
environments,'' Version 0.39.1, software, 2026.

\bibitem{openai_codex}
OpenAI, ``Codex CLI,'' \emph{OpenAI Documentation}, 2026. [Online]. Available:
\url{https://learn.chatgpt.com/docs/codex/cli}. Accessed: Aug. 13, 2026.

\end{thebibliography}

% PROVISIONAL BIOGRAPHY: replace or extend after the final author list is set.
\begin{IEEEbiographynophoto}{Robin Wydaeghe}
received the B.Sc. and M.Sc. degrees in engineering physics from Ghent
University, Ghent, Belgium, in 2019 and 2021, respectively. He is currently
pursuing the Ph.D. degree in engineering physics with Ghent University. His
research interests include computational electromagnetics, numerical assessment
of human radiofrequency electromagnetic-field exposure, and propagation
modeling for next-generation wireless networks.
\end{IEEEbiographynophoto}

\EOD

\end{document}
<!-- AUTO_END: assembled -->
