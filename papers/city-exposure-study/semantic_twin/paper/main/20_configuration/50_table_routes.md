% PREV: Table~\ref{tab:routes} lists the five selected routes. The point counts and spans
% PREV: come from the verified route files used for the five-site data set. Each route
% PREV: follows a connected corridor covered by aligned 360-degree street images. The
% PREV: calculation samples fixed points along that corridor, including interpolated
% PREV: points between image locations. The image count and route-point count can
% PREV: therefore differ. The 73 route points are fixed observations rather than a
% PREV: random sample of pedestrians or places. The phantom faces along the walk, so a
% PREV: different route would change both its position and orientation.
% NEXT: The two image models have separate roles. Mask2Former assigns a Vistas object
% NEXT: class to every image pixel~\cite{mask2former,vistas}. These classes include
% NEXT: buildings, roads, people, vehicles, and vegetation. SAM 3 then tests relevant
% NEXT: material and vegetation labels inside compatible object regions~\cite{sam3}.
% NEXT: The known camera position and viewing direction project both sets of labels onto
% NEXT: the visible city mesh. Repeated observations are combined into one material
% NEXT: map, and every mapped triangle stays linked to its original image. A mesh
% NEXT: triangle changes material only when the object and material labels agree and
% NEXT: pass the acceptance tests. All other triangles keep their geometry-based
% NEXT: material. The prompts, image-alignment tests, rejected labels, and mapping rules
% NEXT: are given in the supplementary material.
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
