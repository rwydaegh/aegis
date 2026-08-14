% PREV: The per-view fishnet is a separate audit product. It cuts visible support
% PREV: triangles at semantic boundaries for inspection and stores each accepted piece
% PREV: with its source triangle, image support, confidence, area, and visible
% PREV: fraction. A parallel table keeps rejected candidate geometry when a reliable
% PREV: inverse projection exists. Reason codes include a degenerate or subpixel
% PREV: triangle, clipping outside the crop, occlusion by the support mesh, clutter in
% PREV: front, a transient object, missing semantic support, area below the retained
% PREV: minimum, a grazing plane, a pixel that is not owned by the support surface, and
% PREV: a mesh or pose conflict. A rejected piece can lie on the support mesh because
% PREV: the code describes why that image-space piece was not accepted as observed
% PREV: semantic evidence. Rejected pieces do not replace or remove the original
% PREV: transport geometry.
% NEXT: \begin{figure*}[!t]
% NEXT:   \centering
% NEXT:   \includegraphics[width=\textwidth]{figures/ray_reached_evidence/ray_reached_evidence.pdf}
% NEXT:   \caption{Ray-reached semantic-evidence coverage. Panel (a) partitions the
% NEXT:   pooled non-direct body-coupled whole-body SAR contribution between
% NEXT:   panorama-informed interfaces and declared geometric fallback states. Panel
% NEXT:   (b) gives accepted retained interaction counts for all seven audit
% NEXT:   categories. Direct transport is not applicable because it has no material
% NEXT:   interaction.}
% NEXT:   \label{fig:si-ray-reached-coverage}
% NEXT: \end{figure*}
% claim: ray_reached_evidence_coverage
\subsection{Ray-reached evidence coverage}
\label{sec:si-ray-reached-coverage}

The audit replays all five sealed routes and 16 seeds with the production
geometry, source curve, atlas, body, 200,000 primary rays, and 4,096 output
cells. It classifies the exact reflection point of every retained order-1
specular path and the first blocking material vertex of every accepted
first-diffuse event. Category counts, transport contribution, body-coupled
fields, and the complete replay all close to the sealed arrays. Direct
transport is not assigned a category because it has no material interaction.

\begin{table}[!t]
  \caption{Share of pooled body-coupled whole-body SAR within each retained non-direct component. Other fallback combines insufficient structural mass, atlas-state refusal, and the residual fallback category.}
  \label{tab:si-ray-reached-coverage}
  \centering
  \resizebox{\columnwidth}{!}{%
  \begin{tabular}{lrrrr}
    \toprule
    Component & \shortstack{Panorama\\informed} & \shortstack{No panorama\\evidence} & \shortstack{Host\\incompatible} & \shortstack{Other\\fallback} \\
    \midrule
    Order-1 specular & 80.643\% & 8.774\% & 10.530\% & 0.052\% \\
    First diffuse & 13.337\% & 44.345\% & 42.314\% & 0.004\% \\
    Combined non-direct & 75.903\% & 11.280\% & 12.769\% & 0.049\% \\
    \bottomrule
  \end{tabular}
  }
\end{table}

Panorama evidence informs most of the pooled non-direct body contribution
because the exact specular term is both larger and more often atlas-bound. The
first-diffuse component has a different support pattern. Most of its
body-coupled contribution reaches geometry with no panorama evidence or with
evidence refused by the host-material compatibility gate. The nonblocking
woody category is zero for retained terminal interactions because a
nonblocking crossing cannot be the first blocking material vertex. This zero
does not imply that woody canopy evidence is absent from the routes.

## AI notes

- Reports the exact body-coupled denominator rather than support-mesh area.
