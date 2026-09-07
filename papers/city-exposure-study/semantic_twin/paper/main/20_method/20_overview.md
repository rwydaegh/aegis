% PREV: \section{Methods}
% PREV: \label{sec:method}
% PREV:
% PREV: \subsection{Study configuration}
% PREV: \label{sec:configuration}
% NEXT: \begin{figure*}[!htb]
% NEXT:   \centering
% NEXT:   \includegraphics[width=\textwidth]{figures/configuration/configuration.pdf}
% NEXT:   \caption{Configuration at Prague Old Town Square. (a) Object and material labels from a 360-degree street image are assigned to the city geometry. (b) Plan view of the 22 observation points and visible roofline. (c) Close-up of the route. The arrow gives the body model's direction of travel.}
% NEXT:   \label{fig:configuration}
% NEXT: \end{figure*}
Fig.~\ref{fig:configuration} shows how the inputs come together at Prague Old
Town Square. A 360-degree street image is aligned with a photogrammetric city
mesh cropped to a 250~m radius around the route. Image labels are assigned to
the visible mesh triangles without changing their geometry. Possible
transmitters lie along visible rooflines. Fixed points set the observation
positions, and the anatomical body model faces the direction of travel at each
point.
