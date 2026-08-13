% PREV: \section{Configuration and Scene Evidence}
% PREV: \label{sec:configuration}
% NEXT: \begin{figure*}[!t]
% NEXT:   \centering
% NEXT:   \includegraphics[width=\textwidth]{figures/configuration/configuration.pdf}
% NEXT:   \caption{Study configuration at Prague Old Town Square. The registered panorama in (a) is aligned with the traced support in (b). Panel (c) shows the surface classes supplied to transport: atlas interfaces, nonblocking woody vegetation, and the geometric fallback. In (d), orange marks roofline source support, filled squares mark registered panorama endpoints, and the arrow gives one route-tangent yaw. The calculation uses a 250\,m-radius support mesh, 502 roofline source elements, and 22 fixed standpoints. Panel (e) shows the anatomical body in neutral gray.}
% NEXT:   \label{fig:configuration}
% NEXT: \end{figure*}
The study configuration is shown in Fig.~\ref{fig:configuration}. Registered street panoramas supply surface evidence to a photogrammetric support mesh cropped to a 250\,m radius. They do not create or alter its geometry. The original mesh remains the transport surface, while the image evidence supplies the surface classes queried on that mesh. A route-visible roofline defines the source support. Fixed positions along a pedestrian route define the receiver locations. At each position, the anatomical body has a horizontal orientation set by the local route tangent.
