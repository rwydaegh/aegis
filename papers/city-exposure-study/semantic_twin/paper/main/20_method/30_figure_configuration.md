% PREV: Fig.~\ref{fig:configuration} shows the study configuration. A 360-degree street
% PREV: image is aligned with a photogrammetric city mesh cropped to a 250~m radius
% PREV: around the route. Object and material labels from the image are projected onto
% PREV: the visible mesh triangles without changing their geometry. The roofline visible
% PREV: from the route gives the possible transmitter locations. Fixed points along the
% PREV: pedestrian route give the observation positions, and the anatomical body model
% PREV: faces along the direction of travel at each point.
% NEXT: Table~\ref{tab:routes} lists the five selected routes. Each route follows a
% NEXT: connected street corridor covered by aligned 360-degree street images. The
% NEXT: calculation places fixed observation points along that corridor, including
% NEXT: interpolated positions between image locations, so the number of images and
% NEXT: the number of observation points can differ. The 73 route points are fixed
% NEXT: observations, not a random sample of pedestrians or places. The body model
% NEXT: faces along the direction of travel, so a different route would change both
% NEXT: position and orientation.
\begin{figure*}[!t]
  \centering
  \includegraphics[width=\textwidth]{figures/configuration/configuration.pdf}
  \caption{Study configuration at Prague Old Town Square. (a) A 360-degree street image is segmented, projected onto the city mesh, and converted to the material map used for ray tracing. (b) The 22 observation points and the visible roofline on a plan view. (c) Close-up of the route. The arrow shows the body model's direction of travel.}
  \label{fig:configuration}
\end{figure*}
