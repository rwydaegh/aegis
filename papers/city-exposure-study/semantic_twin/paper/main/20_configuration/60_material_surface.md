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
The two image models have separate roles. Mask2Former assigns a Vistas object
class to every image pixel~\cite{mask2former,vistas}. These classes include
buildings, roads, people, vehicles, and vegetation. SAM 3 then tests relevant
material and vegetation labels inside compatible object regions~\cite{sam3}.
The known camera position and viewing direction project both sets of labels onto
the visible city mesh. Repeated observations are combined into one material
map, and every mapped triangle stays linked to its original image. A mesh
triangle changes material only when the object and material labels agree and
pass the acceptance tests. All other triangles keep their geometry-based
material. The prompts, image-alignment tests, rejected labels, and mapping rules
are given in the supplementary material.
