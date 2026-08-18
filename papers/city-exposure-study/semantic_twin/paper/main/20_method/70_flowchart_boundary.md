% PREV: Two image-analysis models work in sequence. Mask2Former assigns a Vistas object
% PREV: class (building, road, vegetation, etc.) to every image
% PREV: pixel~\cite{mask2former,vistas}. SAM~3 then tests material and vegetation labels
% PREV: inside the compatible object regions~\cite{sam3}. Both sets of labels are
% PREV: projected onto the visible city mesh using the known camera position and viewing
% PREV: direction. Where multiple images cover the same triangle, the labels are
% PREV: combined into one material map, and every mapped triangle stays linked to its
% PREV: source image. A mesh triangle changes material only when the object and
% PREV: material labels agree and pass the acceptance tests. All other triangles keep
% PREV: their default material. The prompts, alignment tests, rejected labels, and
% PREV: mapping rules are given in the supplementary material.
% NEXT: \begin{figure*}[!t]
% NEXT:   \centering
% NEXT:   \includegraphics[width=\textwidth]{figures/flowchart/flowchart.pdf}
% NEXT:   \caption{Flowchart of the computation and input checks. Aligned 360-degree street images and the city mesh give the material map. The fixed route and visible roofline give observation and transmitter positions. Transport retains direct, first-order specular, and first-diffuse terms. A hash-verified file list pins every input to the five-site result.}
% NEXT:   \label{fig:flowchart}
% NEXT: \end{figure*}
Fig.~\ref{fig:flowchart} shows the computation and its input checks. A
hash-verified manifest lists every input file: aligned images, material map,
city mesh, route, roofline, body model, and transport settings. Only files whose
hashes match the manifest enter the ten-site data set. The transport
calculation keeps direct, specular, and diffuse contributions separate until
the field is applied to the body. The ten manifests contain 420 verified entries. Across the
resulting 10,432 directional body fields, the largest residual when the three
components are summed back to the stored total is
$1.214\times10^{-17}\,\mathrm{m}^{-2}$.
