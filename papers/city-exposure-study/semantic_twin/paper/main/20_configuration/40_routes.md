% PREV: \begin{figure*}[!t]
% PREV:   \centering
% PREV:   \includegraphics[width=\textwidth]{figures/configuration/configuration.pdf}
% PREV:   \caption{Study configuration at Prague Old Town Square. Panel (a) follows a 360-degree street image through object segmentation, projection onto the city mesh, and conversion to the material map used by the tracer. Panel (b) shows the 22 route points and the visible roofline on a plan view of the city. Panel (c) enlarges the route. The arrow gives the phantom's direction along the walk.}
% PREV:   \label{fig:configuration}
% PREV: \end{figure*}
% NEXT: \begin{table}[!t]
% NEXT:   \caption{Five fixed routes and prepared-scene numerical campaign times}
% NEXT:   \label{tab:routes}
% NEXT:   \centering
% NEXT:   \begin{tabular}{lrrr}
% NEXT:     \hline
% NEXT:     Site & Route points & Route span (m) & Wall time (s) \\
% NEXT:     \hline
% NEXT:     Korenmarkt & 10 & 49.04 & 29.79 \\
% NEXT:     Prague & 22 & 119.39 & 69.02 \\
% NEXT:     Madrid & 14 & 73.47 & 40.70 \\
% NEXT:     Mexico City & 11 & 60.79 & 30.92 \\
% NEXT:     Tokyo Hachiko & 16 & 87.38 & 50.11 \\
% NEXT:     \hline
% NEXT:     Total & 73 & 390.07 & 220.54 \\
% NEXT:     \hline
% NEXT:   \end{tabular}
% NEXT: \end{table}
Table~\ref{tab:routes} lists the five selected routes. The point counts and spans
come from the verified route files used for the five-site data set. Each route
follows a connected corridor covered by aligned 360-degree street images. The
calculation samples fixed points along that corridor, including interpolated
points between image locations. The image count and route-point count can
therefore differ. The 73 route points are fixed observations rather than a
random sample of pedestrians or places. The phantom faces along the walk, so a
different route would change both its position and orientation.
