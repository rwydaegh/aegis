% PREV: Table~\ref{tab:routes} lists the five selected routes. Each route follows a
% PREV: connected street corridor covered by aligned 360-degree street images. The
% PREV: calculation places fixed observation points along that corridor, including
% PREV: interpolated positions between image locations, so the number of images and
% PREV: the number of observation points can differ. The 73 route points are fixed
% PREV: observations, not a random sample of pedestrians or places. The body model
% PREV: faces along the direction of travel, so a different route would change both
% PREV: position and orientation.
% NEXT: Two image-analysis models work in sequence. Mask2Former assigns a Vistas object
% NEXT: class (building, road, vegetation, etc.) to every image
% NEXT: pixel~\cite{mask2former,vistas}. SAM~3 then tests material and vegetation labels
% NEXT: inside the compatible object regions~\cite{sam3}. Both sets of labels are
% NEXT: projected onto the visible city mesh using the known camera position and viewing
% NEXT: direction. Where multiple images cover the same triangle, the labels are
% NEXT: combined into one material map, and every mapped triangle stays linked to its
% NEXT: source image. A mesh triangle changes material only when the object and
% NEXT: material labels agree and pass the acceptance tests. All other triangles keep
% NEXT: their default material. The prompts, alignment tests, rejected labels, and
% NEXT: mapping rules are given in the supplementary material.
\begin{table}[!t]
  \caption{Ten fixed routes with observation-point counts, route spans, and computation times}
  \label{tab:routes}
  \centering
  \begin{tabular}{lrrr}
    \toprule
    Site & Route points & Route span (m) & Wall time (s) \\
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
