<!-- AUTO_BEGIN: assembled -->
\section{Configuration and Surface Mapping}
\label{sec:configuration}

The study configuration is shown in Fig.~\ref{fig:configuration}. A
360-degree street image is aligned with a photogrammetric city mesh cropped to a
250\,m radius. Object and material labels from the image are projected onto the
visible mesh triangles without changing their geometry. The roofline visible
from the route gives the possible transmitter locations. Fixed points along the
pedestrian route give the receiver locations, and the anatomical phantom faces
along the direction of travel at each point.

\begin{figure*}[!t]
  \centering
  \includegraphics[width=\textwidth]{figures/configuration/configuration.pdf}
  \caption{Study configuration at Prague Old Town Square. Panel (a) follows a 360-degree street image through object segmentation, projection onto the city mesh, and conversion to the material map used by the tracer. Panel (b) shows the 22 route points and the visible roofline on a plan view of the city. Panel (c) enlarges the route. The arrow gives the phantom's direction along the walk.}
  \label{fig:configuration}
\end{figure*}

Table~\ref{tab:routes} lists the five selected routes. The point counts and spans
come from the verified route files used for the five-site data set. Each route
follows a connected corridor covered by aligned 360-degree street images. The
calculation samples fixed points along that corridor, including interpolated
points between image locations. The image count and route-point count can
therefore differ. The 73 route points are fixed observations rather than a
random sample of pedestrians or places. The phantom faces along the walk, so a
different route would change both its position and orientation.

\begin{table}[!t]
  \caption{Five fixed routes and prepared-scene numerical campaign times}
  \label{tab:routes}
  \centering
  \begin{tabular}{lrrr}
    \hline
    Site & Route points & Route span (m) & Wall time (s) \\
    \hline
    Korenmarkt & 10 & 49.04 & 29.79 \\
    Prague & 22 & 119.39 & 69.02 \\
    Madrid & 14 & 73.47 & 40.70 \\
    Mexico City & 11 & 60.79 & 30.92 \\
    Tokyo Hachiko & 16 & 87.38 & 50.11 \\
    \hline
    Total & 73 & 390.07 & 220.54 \\
    \hline
  \end{tabular}
\end{table}

The two image models have separate roles. Mask2Former assigns a Vistas object
class to every image pixel~\cite{mask2former,vistas}. These classes include
buildings, roads, people, vehicles, and vegetation. SAM 3 then tests relevant
material and vegetation labels inside compatible object regions~\cite{sam3}.
The known camera position and viewing direction project both sets of labels onto
the visible city mesh. Repeated observations are combined into one material
map, and every mapped triangle stays linked to its original image. A mesh
triangle changes material only when the object and material labels agree and
pass the acceptance tests. All other triangles keep their geometry-based
material. The prompts, image-alignment tests, rejected labels, and mapping rules
are given in the supplementary material.

Fig.~\ref{fig:flowchart} shows the computation and the files checked before it
runs. A hash-verified manifest lists the aligned images, material map, city
mesh, route, roofline, body, sampler, and transport settings. Only files that
match this list enter the five-site data set. The transport calculation keeps
direct, first-order specular, and first-diffuse contributions separate until
body coupling. The five manifests contain 210 verified entries. Across the
resulting 1,168 directional body fields, the largest additive-closure residual
is $1.735\times10^{-18}\,\mathrm{m}^{-2}$.

\begin{figure*}[!t]
  \centering
  \includegraphics[width=\textwidth]{figures/flowchart/flowchart.pdf}
  \caption{Flowchart of the computation and input checks. Aligned 360-degree street images and the city mesh give the material map. The fixed route and visible roofline give receiver and possible transmitter positions. Transport retains direct, first-order specular, and first-diffuse terms. A hash-verified file list fixes every input to the five-site result.}
  \label{fig:flowchart}
\end{figure*}
<!-- AUTO_END: assembled -->















## Aggregation notes (AI-owned)
