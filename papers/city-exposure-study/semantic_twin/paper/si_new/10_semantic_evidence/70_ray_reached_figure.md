% PREV: % claim: ray_reached_evidence_coverage
% PREV: \subsection{Ray-reached evidence coverage}
% PREV: \label{sec:si-ray-reached-coverage}
% PREV:
% PREV: The audit replays all five sealed routes and 16 seeds with the production
% PREV: geometry, source curve, atlas, body, 200,000 primary rays, and 4,096 output
% PREV: cells. It classifies the exact reflection point of every retained order-1
% PREV: specular path and the first blocking material vertex of every accepted
% PREV: first-diffuse event. Category counts, transport contribution, body-coupled
% PREV: fields, and the complete replay all close to the sealed arrays. Direct
% PREV: transport is not assigned a category because it has no material interaction.
% PREV:
% PREV: \begin{table}[!t]
% PREV:   \caption{Share of pooled body-coupled whole-body SAR within each retained non-direct component. Other fallback combines insufficient structural mass, atlas-state refusal, and the residual fallback category.}
% PREV:   \label{tab:si-ray-reached-coverage}
% PREV:   \centering
% PREV:   \resizebox{\columnwidth}{!}{%
% PREV:   \begin{tabular}{lrrrr}
% PREV:     \toprule
% PREV:     Component & \shortstack{Panorama\\informed} & \shortstack{No panorama\\evidence} & \shortstack{Host\\incompatible} & \shortstack{Other\\fallback} \\
% PREV:     \midrule
% PREV:     Order-1 specular & 80.643\% & 8.774\% & 10.530\% & 0.052\% \\
% PREV:     First diffuse & 13.337\% & 44.345\% & 42.314\% & 0.004\% \\
% PREV:     Combined non-direct & 75.903\% & 11.280\% & 12.769\% & 0.049\% \\
% PREV:     \bottomrule
% PREV:   \end{tabular}
% PREV:   }
% PREV: \end{table}
% PREV:
% PREV: Panorama evidence informs most of the pooled non-direct body contribution
% PREV: because the exact specular term is both larger and more often atlas-bound. The
% PREV: first-diffuse component has a different support pattern. Most of its
% PREV: body-coupled contribution reaches geometry with no panorama evidence or with
% PREV: evidence refused by the host-material compatibility gate. The nonblocking
% PREV: woody category is zero for retained terminal interactions because a
% PREV: nonblocking crossing cannot be the first blocking material vertex. This zero
% PREV: does not imply that woody canopy evidence is absent from the routes.
\begin{figure*}[!t]
  \centering
  \includegraphics[width=\textwidth]{figures/ray_reached_evidence/ray_reached_evidence.pdf}
  \caption{Ray-reached semantic-evidence coverage. Panel (a) partitions the
  pooled non-direct body-coupled whole-body SAR contribution between
  panorama-informed interfaces and declared geometric fallback states. Panel
  (b) gives accepted retained interaction counts for all seven audit
  categories. Direct transport is not applicable because it has no material
  interaction.}
  \label{fig:si-ray-reached-coverage}
\end{figure*}

## Reviews

_(empty)_
