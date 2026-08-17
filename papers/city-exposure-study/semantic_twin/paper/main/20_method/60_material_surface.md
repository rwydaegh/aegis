% PREV: \begin{table}[!t]
% PREV:   \caption{Five fixed routes and prepared-scene numerical campaign times}
% PREV:   \label{tab:routes}
% PREV:   \centering
% PREV:   \begin{tabular}{lrrr}
% PREV:     \hline
% PREV:     Site & Route points & Route span (m) & Wall time (s) \\
% PREV:     \hline
% PREV:     Korenmarkt & 10 & 49.04 & 29.79 \\
% PREV:     Prague & 22 & 119.39 & 69.02 \\
% PREV:     Madrid & 14 & 73.47 & 40.70 \\
% PREV:     Mexico City & 11 & 60.79 & 30.92 \\
% PREV:     Tokyo Hachiko & 16 & 87.38 & 50.11 \\
% PREV:     \hline
% PREV:     Total & 73 & 390.07 & 220.54 \\
% PREV:     \hline
% PREV:   \end{tabular}
% PREV: \end{table}
% NEXT: Fig.~\ref{fig:flowchart} shows the computation and the files checked before it
% NEXT: runs. A hash-verified manifest lists the aligned images, material map, city
% NEXT: mesh, route, roofline, body, sampler, and transport settings. Only files that
% NEXT: match this list enter the five-site data set. The transport calculation keeps
% NEXT: direct, first-order specular, and first-diffuse contributions separate until
% NEXT: body coupling. The five manifests contain 210 verified entries. Across the
% NEXT: resulting 1,168 directional body fields, the largest additive-closure residual
% NEXT: is $1.735\times10^{-18}\,\mathrm{m}^{-2}$.
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
