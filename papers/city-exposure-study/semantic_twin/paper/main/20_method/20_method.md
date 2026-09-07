<!-- AUTO_BEGIN: assembled -->
\section{Methods}
\label{sec:method}

\subsection{Study configuration}
\label{sec:configuration}

Fig.~\ref{fig:configuration} shows how the inputs come together at Prague Old
Town Square. A 360-degree street image is aligned with a photogrammetric city
mesh cropped to a 250~m radius around the route. Image labels are assigned to
the visible mesh triangles without changing their geometry. Possible
transmitters lie along visible rooflines. Fixed points set the observation
positions, and the anatomical body model faces the direction of travel at each
point.

\begin{figure*}[!htb]
  \centering
  \includegraphics[width=\textwidth]{figures/configuration/configuration.pdf}
  \caption{Configuration at Prague Old Town Square. (a) Object and material labels from a 360-degree street image are assigned to the city geometry. (b) Plan view of the 22 observation points and visible roofline. (c) Close-up of the route. The arrow gives the body model's direction of travel.}
  \label{fig:configuration}
\end{figure*}

With this configuration fixed, Table~\ref{tab:routes} summarizes the study
route in each of the ten cities. Each
route follows a connected street corridor covered by aligned 360-degree street
images. Fixed observation points include positions between image locations, so
the number of images and points can differ. The 163 points are fixed case-study
observations that describe the selected routes. A different route would change
both position and body orientation.

\begin{table}[!t]
  \caption{Study route in each city, with observation-point counts, route spans, and ray calculation times}
  \label{tab:routes}
  \centering
  \begin{tabular}{lrrr}
    \toprule
    City & Points & Span (m) & Time (s) \\
    \midrule
    Brussels & 14 & 87.00 & 32.16 \\
    Ghent & 10 & 49.04 & 6.59 \\
    Krakow & 16 & 116.10 & 31.76 \\
    London & 22 & 121.10 & 73.77 \\
    Madrid & 14 & 73.47 & 8.06 \\
    Mexico City & 11 & 60.79 & 5.95 \\
    Milan & 23 & 128.43 & 69.02 \\
    Prague & 22 & 119.39 & 39.00 \\
    Tokyo Hachiko & 16 & 87.38 & 10.02 \\
    Toulouse & 15 & 82.47 & 37.87 \\
    \midrule
    Total & 163 & 925.17 & 314.20 \\
    \bottomrule
  \end{tabular}
\end{table}

\subsection{AI-assisted digital twin}
\label{sec:digital-twin}

Two image models are applied in sequence. First, Mask2Former assigns a Vistas object
class such as building, road, or vegetation to every pixel~\cite{mask2former,vistas}.
Next, SAM~3 Agent performs the agentic AI step by assigning material and vegetation
labels inside compatible object regions~\cite{sam3}. Its prompt-guided concepts
extend the fixed object classes with material evidence. The camera position and
viewing direction locate these labels on visible triangles in the city geometry. When several images cover one
triangle, their accepted labels are combined. A triangle changes material only
when its object and material labels are compatible and meet the selection
criteria. All other triangles keep their geometry-based material. The
supplementary material gives the prompts, alignment tests, rejected labels, and
assignment rules.

Fig.~\ref{fig:flowchart} connects the scene-building and exposure stages. The
image and geometry branches first form the human-centric digital twin.
Pedestrian locations, body orientations, and possible roofline transmitters
complete its route-specific inputs. The final stages compute directional radio
arrivals and apply them to the body.

\begin{figure*}[!htb]
  \centering
  \includegraphics[width=\textwidth]{figures/flowchart/flowchart.pdf}
  \caption{Flowchart from multimodal city data to whole-body specific absorption rate (SAR). Mask2Former assigns object labels, and SAM~3 Agent assigns material labels. These labels, 3-D city geometry, pedestrian locations and body orientations, and possible roofline transmitters form a human-centric digital twin. The propagation and body calculations then give whole-body SAR.}
  \label{fig:flowchart}
\end{figure*}

\subsection{Exposure calculation}
\label{sec:exposure-calc}

Following the central path in Fig.~\ref{fig:flowchart}, every route point uses
15~GHz and a circular scene crop with radius
$R_{\mathrm{crop}}=250$~m and area
$A_{\mathrm{crop}}=196{,}349.54$~m$^2$. The receiver position $\mathbf{x}$ is
the ray origin and body reference point. The body faces the local direction of
travel. Index $i$ denotes a roofline segment, $r_i(\mathbf{x})$ is its range to
the receiver, and $\mathbf{r}$ is a point on the body surface.

The possible roofline transmitters in Fig.~\ref{fig:flowchart} represent a
future distributed massive MIMO (DMaMIMO) architecture only to
define possible access-point locations~\cite{wydaeghe2026,ngo2017}. Therefore,
the model uses visible rooflines as possible transmitter locations. The
calculation treats the possible sites as independent power sources and
distributes expected transmitters uniformly per
unit physical length of the roofline visible from the route. The active-site density $\rho_A$ gives an
expected count $N_{\mathrm{site}}=\rho_A A_{\mathrm{crop}}$. For a segment with
endpoints $\mathbf{p}_i$ and $\mathbf{p}_{i+1}$, its source fraction is
\begin{equation}
p_i=\frac{\ell_i}{\sum_j \ell_j},\qquad
\ell_i=\lVert\mathbf{p}_{i+1}-\mathbf{p}_i\rVert_2 .
\label{eq:source-measure}
\end{equation}
The denominator prevents a numerical split of one segment from adding source
power. The calculation uses three-dimensional length rather than horizontal
length.

An unobstructed reference separates source strength from scene geometry:
\begin{equation}
D_{\mathrm{ref}}(\mathbf{x})=
\sum_i\frac{p_i}{r_i(\mathbf{x})^2},
\qquad
S_{\mathrm{ref}}(\mathbf{x})=
\frac{A_{\mathrm{crop}}D_{\mathrm{ref}}(\mathbf{x})}{4\pi} \, .
\label{eq:reference-scale}
\end{equation}
We apply no visibility test to $D_{\mathrm{ref}}$. All reported values are
normalized per unit $\rho_A P_{\mathrm{EIRP}}$. Multiplication by
$\rho_A P_{\mathrm{EIRP}}$ gives physical units, but only for a deployment
that follows the same roofline transmitter model. The calculation omits
transmitters and interactions outside the crop.

% claim: directional_component_representation
The propagation result at each observation point has direct, one-reflection
specular, and one-reflection diffuse parts. Let $\mathcal{D}$ contain visible direct
paths and $\mathcal{S}_1$ contain accepted one-reflection specular
paths. Their normalized powers are
$\alpha_a=m_a^{(\mathrm{d})}/D_{\mathrm{ref}}$ and
$\beta_b=m_b^{(\mathrm{s})}/D_{\mathrm{ref}}$. The diffuse estimate uses
normalized angular-cell powers
$\widehat{\gamma}_q=\widehat{m}_q^{(\mathrm{f})}/D_{\mathrm{ref}}$ in
$Q=4096$ fixed angular cells. With $\delta_{\widehat{\mathbf{k}}}$ denoting a unit point
mass in arrival direction $\widehat{\mathbf{k}}$, the directional distribution is
\begin{equation}
\begin{aligned}
\mu_{\mathbf{x}}={}&
\sum_{a\in\mathcal{D}}\alpha_a\delta_{\widehat{\mathbf{k}}_a^{(\mathrm{d})}}
+\sum_{b\in\mathcal{S}_1}\beta_b\delta_{\widehat{\mathbf{k}}_b^{(\mathrm{s})}} \\
&+\sum_{q=1}^{Q}\widehat{\gamma}_q\delta_{\widehat{\mathbf{k}}_q^{(\mathrm{f})}} .
\end{aligned}
\label{eq:first-material-transfer}
\end{equation}
The first two sums keep exact path directions and powers. Only diffuse power
uses the angular cells. Fig.~\ref{fig:adjoint} contrasts the two sampling paths
for this diffuse term. \emph{Adjoint ray tracing} launches rays from the
observation point and tests visibility from each first surface hit to every
roofline source~\cite{behlouli2014,cocheril2007}. This source connection is a next-event
estimate~\cite{veach}. The surface law combines unpolarized Fresnel power with
a Rayleigh roughness term. The surface law assigns the remaining reflected power to a
Lambertian diffuse component, and all components add incoherently. Each sampled
path ends after the diffuse reflection. Higher-order specular paths are also
omitted. Woody vegetation identified by the images is transparent to rays
because the city geometry has no canopy volume. The supplementary material gives the
full laws and parameters.

\begin{figure*}[!htb]
  \centering
  \includegraphics[width=\textwidth]{figures/adjoint/adjoint.pdf}
  \caption{Forward and adjoint sampling for the single-reflection diffuse component. (a) Forward sampling launches rays from every roofline segment. (b) Adjoint sampling launches one set of rays from the observation point and tests visible source connections at the first surface hit.}
  \label{fig:adjoint}
\end{figure*}

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
<!-- AUTO_END: assembled -->
