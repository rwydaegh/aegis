% PREV: The two image models have separate roles. Mask2Former assigns a Vistas object
% PREV: class to every image pixel~\cite{mask2former,vistas}. These classes include
% PREV: buildings, roads, people, vehicles, and vegetation. SAM 3 then tests relevant
% PREV: material and vegetation labels inside compatible object regions~\cite{sam3}.
% PREV: The known camera position and viewing direction project both sets of labels onto
% PREV: the visible city mesh. Repeated observations are combined into one material
% PREV: map, and every mapped triangle stays linked to its original image. A mesh
% PREV: triangle changes material only when the object and material labels agree and
% PREV: pass the acceptance tests. All other triangles keep their geometry-based
% PREV: material. The prompts, image-alignment tests, rejected labels, and mapping rules
% PREV: are given in the supplementary material.
% NEXT: \begin{figure*}[!t]
% NEXT:   \centering
% NEXT:   \includegraphics[width=\textwidth]{figures/flowchart/flowchart.pdf}
% NEXT:   \caption{Flowchart of the computation and input checks. Aligned 360-degree street images and the city mesh give the material map. The fixed route and visible roofline give receiver and possible transmitter positions. Transport retains direct, first-order specular, and first-diffuse terms. A hash-verified file list fixes every input to the five-site result.}
% NEXT:   \label{fig:flowchart}
% NEXT: \end{figure*}
Fig.~\ref{fig:flowchart} shows the computation and its input checks. A
hash-verified manifest lists every input file: aligned images, material map,
city mesh, route, roofline, body model, and transport settings. Only files whose
hashes match the manifest enter the five-site data set. The transport
calculation keeps direct, specular, and diffuse contributions separate until
the field is applied to the body. The five manifests contain 210 verified entries. Across the
resulting 1,168 directional body fields, the largest residual when the three
components are summed back to the stored total is
$1.735\times10^{-18}\,\mathrm{m}^{-2}$.
