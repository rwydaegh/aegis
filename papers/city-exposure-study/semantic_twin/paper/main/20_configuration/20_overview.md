% PREV: \section{Configuration and Surface Mapping}
% PREV: \label{sec:configuration}
% NEXT: \begin{figure*}[!t]
% NEXT:   \centering
% NEXT:   \includegraphics[width=\textwidth]{figures/configuration/configuration.pdf}
% NEXT:   \caption{Study configuration at Prague Old Town Square. Panel (a) follows a 360-degree street image through object segmentation, projection onto the city mesh, and conversion to the material map used by the tracer. Panel (b) shows the 22 route points and the visible roofline on a plan view of the city. Panel (c) enlarges the route. The arrow gives the phantom's direction along the walk.}
% NEXT:   \label{fig:configuration}
% NEXT: \end{figure*}
The study configuration is shown in Fig.~\ref{fig:configuration}. A
360-degree street image is aligned with a photogrammetric city mesh cropped to a
250\,m radius. Object and material labels from the image are projected onto the
visible mesh triangles without changing their geometry. The roofline visible
from the route gives the possible transmitter locations. Fixed points along the
pedestrian route give the receiver locations, and the anatomical phantom faces
along the direction of travel at each point.
