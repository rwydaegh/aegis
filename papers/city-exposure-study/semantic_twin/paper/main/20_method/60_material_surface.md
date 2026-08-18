% PREV: \begin{table}[!t]
% PREV:   \caption{Five fixed routes with observation-point counts, route spans, and computation times}
% PREV:   \label{tab:routes}
% PREV:   \centering
% PREV:   \begin{tabular}{lrrr}
% PREV:     \toprule
% PREV:     Site & Route points & Route span (m) & Wall time (s) \\
% PREV:     \midrule
% PREV:     Ghent & 10 & 49.04 & 29.79 \\
% PREV:     Prague & 22 & 119.39 & 69.02 \\
% PREV:     Madrid & 14 & 73.47 & 40.70 \\
% PREV:     Mexico City & 11 & 60.79 & 30.92 \\
% PREV:     Tokyo Hachiko & 16 & 87.38 & 50.11 \\
% PREV:     \midrule
% PREV:     Total & 73 & 390.07 & 220.54 \\
% PREV:     \bottomrule
% PREV:   \end{tabular}
% PREV: \end{table}
% NEXT: Fig.~\ref{fig:flowchart} shows the computation and its input checks. A
% NEXT: hash-verified manifest lists every input file: aligned images, material map,
% NEXT: city mesh, route, roofline, body model, and transport settings. Only files whose
% NEXT: hashes match the manifest enter the five-site data set. The transport
% NEXT: calculation keeps direct, specular, and diffuse contributions separate until
% NEXT: the field is applied to the body. The five manifests contain 210 verified entries. Across the
% NEXT: resulting 1,168 directional body fields, the largest residual when the three
% NEXT: components are summed back to the stored total is
% NEXT: $1.735\times10^{-18}\,\mathrm{m}^{-2}$.
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
