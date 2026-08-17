<!-- AUTO_BEGIN: assembled -->
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
<!-- AUTO_END: assembled -->
