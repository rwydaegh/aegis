% PREV: The per-image inspection mesh is a separate audit product. It cuts visible
% PREV: city-mesh triangles at object boundaries and stores each accepted piece with
% PREV: its source triangle, source image, confidence, area, and visible fraction. A
% PREV: parallel table keeps rejected pieces when a reliable
% PREV: inverse projection exists. Reason codes include a degenerate or subpixel
% PREV: triangle, clipping outside the crop, occlusion by the city mesh, clutter in
% PREV: front, a transient object, missing object labels, area below the retained
% PREV: minimum, a grazing plane, a pixel that does not belong to the city mesh, and
% PREV: a mesh or camera-pose conflict. A rejected piece can lie on the city mesh
% PREV: because the code describes why that image-space piece did not receive an
% PREV: accepted object or material label. Rejected pieces do not replace or remove the original
% PREV: transport geometry.
% NEXT: \begin{figure*}[!t]
% NEXT:   \centering
% NEXT:   \includegraphics[width=\textwidth]{figures/ray_reached_evidence/ray_reached_evidence.pdf}
% NEXT:   \caption{Material labels on surfaces reached by modeled paths. Panel (a) partitions the
% NEXT:   pooled non-direct body-coupled whole-body SAR contribution between
% NEXT:   image-mapped and geometry-based materials. Panel
% NEXT:   (b) gives accepted retained interaction counts for all seven audit
% NEXT:   categories. Direct transport is not applicable because it has no material
% NEXT:   interaction.}
% NEXT:   \label{fig:si-ray-reached-coverage}
% NEXT: \end{figure*}
% claim: ray_reached_evidence_coverage
\subsection{Material labels on reached surfaces}
\label{sec:si-ray-reached-coverage}

The audit replays all ten verified routes and 64 seeds with the production
geometry, source curve, material map, body, 200,000 primary rays, and 4,096 output
cells. It classifies the exact reflection point of every retained order-1
specular path and the first blocking surface of every accepted
first-diffuse event. Category counts, transport contribution, body-coupled
fields, and the complete replay all match the verified arrays. Direct
transport is not assigned a category because it has no material interaction.

\begin{table}[!t]
  \caption{Share of pooled body-coupled whole-body SAR within each retained non-direct component. Other fallback combines insufficient structural probability, a rejected image label, and the remaining geometry-based category.}
  \label{tab:si-ray-reached-coverage}
  \centering
  \resizebox{\columnwidth}{!}{%
  \begin{tabular}{lrrrr}
    \toprule
    Component & \shortstack{Image\\mapped} & \shortstack{No image\\label} & \shortstack{Object-material\\mismatch} & \shortstack{Other geometry\\fallback} \\
    \midrule
    Order-1 specular & 80.643\% & 8.774\% & 10.530\% & 0.052\% \\
    First diffuse & 13.337\% & 44.345\% & 42.314\% & 0.004\% \\
    Combined non-direct & 75.903\% & 11.280\% & 12.769\% & 0.049\% \\
    \bottomrule
  \end{tabular}
  }
\end{table}

Image-derived materials inform most of the pooled non-direct body contribution
because the exact specular term is both larger and more often image-mapped. The
first-diffuse component reaches different surfaces. Most of its body-coupled
contribution reaches geometry with no image label or with a label rejected by
the object-material compatibility test. The nonblocking
woody category is zero for retained terminal interactions because a
nonblocking crossing cannot be the first blocking surface. This zero
does not imply that woody canopy evidence is absent from the routes.

## AI notes

- Reports the exact body-coupled denominator rather than support-mesh area.
