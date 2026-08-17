% PREV: The study configuration is shown in Fig.~\ref{fig:configuration}. A
% PREV: 360-degree street image is aligned with a photogrammetric city mesh cropped to a
% PREV: 250\,m radius. Object and material labels from the image are projected onto the
% PREV: visible mesh triangles without changing their geometry. The roofline visible
% PREV: from the route gives the possible transmitter locations. Fixed points along the
% PREV: pedestrian route give the receiver locations, and the anatomical phantom faces
% PREV: along the direction of travel at each point.
% NEXT: Table~\ref{tab:routes} lists the five selected routes. The point counts and spans
% NEXT: come from the verified route files used for the five-site data set. Each route
% NEXT: follows a connected corridor covered by aligned 360-degree street images. The
% NEXT: calculation samples fixed points along that corridor, including interpolated
% NEXT: points between image locations. The image count and route-point count can
% NEXT: therefore differ. The 73 route points are fixed observations rather than a
% NEXT: random sample of pedestrians or places. The phantom faces along the walk, so a
% NEXT: different route would change both its position and orientation.
\begin{figure*}[!t]
  \centering
  \includegraphics[width=\textwidth]{figures/configuration/configuration.pdf}
  \caption{Study configuration at Prague Old Town Square. (a) A 360-degree street image is segmented, projected onto the city mesh, and converted to the material map used for ray tracing. (b) The 22 observation points and the visible roofline on a plan view. (c) Close-up of the route. The arrow shows the body model's direction of travel.}
  \label{fig:configuration}
\end{figure*}
