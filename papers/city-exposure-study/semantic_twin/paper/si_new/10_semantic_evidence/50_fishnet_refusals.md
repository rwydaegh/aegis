% PREV: Material evidence remains probabilistic through fusion. Vistas-backed pixels
% PREV: use the declared full $p(\text{material}\mid\text{entity})$ table. Concept-backed
% PREV: pixels use the full material distribution of the detected prompt. Transport
% PREV: removes probability assigned to air, unknown material, people, vehicles, and
% PREV: participating volumes. It binds an image-derived structural interface only when
% PREV: the remaining compatible structural mass is strictly greater than 0.5. An
% PREV: exact tie and any unsupported atlas cell use the geometric face material.
% PREV: Reflected power uses the posterior-weighted material coefficients. The
% PREV: specular sampling probability uses the posterior-weighted reflected specular
% PREV: share. Grass keeps the geometric ground interface. Woody canopy evidence is
% PREV: nonblocking until registered closed canopy geometry can supply path chords for
% PREV: volume attenuation.
% NEXT: % claim: ray_reached_evidence_coverage
% NEXT: \subsection{Ray-reached evidence coverage}
% NEXT: \label{sec:si-ray-reached-coverage}
% NEXT:
% NEXT: The audit replays all five sealed routes and 16 seeds with the production
% NEXT: geometry, source curve, atlas, body, 200,000 primary rays, and 4,096 output
% NEXT: cells. It classifies the exact reflection point of every retained order-1
% NEXT: specular path and the first blocking material vertex of every accepted
% NEXT: first-diffuse event. Category counts, transport contribution, body-coupled
% NEXT: fields, and the complete replay all close to the sealed arrays. Direct
% NEXT: transport is not assigned a category because it has no material interaction.
% NEXT:
% NEXT: \begin{table}[!t]
% NEXT:   \caption{Share of pooled body-coupled whole-body SAR within each retained non-direct component. Other fallback combines insufficient structural mass, atlas-state refusal, and the residual fallback category.}
% NEXT:   \label{tab:si-ray-reached-coverage}
% NEXT:   \centering
% NEXT:   \resizebox{\columnwidth}{!}{%
% NEXT:   \begin{tabular}{lrrrr}
% NEXT:     \toprule
% NEXT:     Component & \shortstack{Panorama\\informed} & \shortstack{No panorama\\evidence} & \shortstack{Host\\incompatible} & \shortstack{Other\\fallback} \\
% NEXT:     \midrule
% NEXT:     Order-1 specular & 80.643\% & 8.774\% & 10.530\% & 0.052\% \\
% NEXT:     First diffuse & 13.337\% & 44.345\% & 42.314\% & 0.004\% \\
% NEXT:     Combined non-direct & 75.903\% & 11.280\% & 12.769\% & 0.049\% \\
% NEXT:     \bottomrule
% NEXT:   \end{tabular}
% NEXT:   }
% NEXT: \end{table}
% NEXT:
% NEXT: Panorama evidence informs most of the pooled non-direct body contribution
% NEXT: because the exact specular term is both larger and more often atlas-bound. The
% NEXT: first-diffuse component has a different support pattern. Most of its
% NEXT: body-coupled contribution reaches geometry with no panorama evidence or with
% NEXT: evidence refused by the host-material compatibility gate. The nonblocking
% NEXT: woody category is zero for retained terminal interactions because a
% NEXT: nonblocking crossing cannot be the first blocking material vertex. This zero
% NEXT: does not imply that woody canopy evidence is absent from the routes.
The per-view fishnet is a separate audit product. It cuts visible support
triangles at semantic boundaries for inspection and stores each accepted piece
with its source triangle, image support, confidence, area, and visible
fraction. A parallel table keeps rejected candidate geometry when a reliable
inverse projection exists. Reason codes include a degenerate or subpixel
triangle, clipping outside the crop, occlusion by the support mesh, clutter in
front, a transient object, missing semantic support, area below the retained
minimum, a grazing plane, a pixel that is not owned by the support surface, and
a mesh or pose conflict. A rejected piece can lie on the support mesh because
the code describes why that image-space piece was not accepted as observed
semantic evidence. Rejected pieces do not replace or remove the original
transport geometry.

## AI notes

- Clarifies that refused fishnet faces are evidence QA, not deleted transport faces.
