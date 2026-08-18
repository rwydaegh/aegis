% PREV: Material labels remain probabilistic when observations are combined. Vistas-backed pixels
% PREV: use the declared full $p(\text{material}\mid\text{entity})$ table. Concept-backed
% PREV: pixels use the full material distribution of the detected prompt. Transport
% PREV: removes probability assigned to air, unknown material, people, vehicles, and
% PREV: participating volumes. It assigns an image-derived structural material only when
% PREV: the remaining compatible structural probability is strictly greater than 0.5.
% PREV: An exact tie and any unsupported material-map cell use the geometric face material.
% PREV: Reflected power uses the posterior-weighted material coefficients. The
% PREV: specular sampling probability uses the posterior-weighted reflected specular
% PREV: share. Grass keeps the geometric ground interface. Woody canopy labels are
% PREV: nonblocking until a closed canopy volume can supply path lengths for
% PREV: volume attenuation.
% NEXT: % claim: ray_reached_evidence_coverage
% NEXT: \subsection{Material labels on reached surfaces}
% NEXT: \label{sec:si-ray-reached-coverage}
% NEXT:
% NEXT: The audit replays all five verified routes and 16 seeds with the production
% NEXT: geometry, source curve, material map, body, 200,000 primary rays, and 4,096 output
% NEXT: cells. It classifies the exact reflection point of every retained order-1
% NEXT: specular path and the first blocking surface of every accepted
% NEXT: first-diffuse event. Category counts, transport contribution, body-coupled
% NEXT: fields, and the complete replay all match the verified arrays. Direct
% NEXT: transport is not assigned a category because it has no material interaction.
% NEXT:
% NEXT: \begin{table}[!t]
% NEXT:   \caption{Share of pooled body-coupled whole-body SAR within each retained non-direct component. Other fallback combines insufficient structural probability, a rejected image label, and the remaining geometry-based category.}
% NEXT:   \label{tab:si-ray-reached-coverage}
% NEXT:   \centering
% NEXT:   \resizebox{\columnwidth}{!}{%
% NEXT:   \begin{tabular}{lrrrr}
% NEXT:     \toprule
% NEXT:     Component & \shortstack{Image\\mapped} & \shortstack{No image\\label} & \shortstack{Object-material\\mismatch} & \shortstack{Other geometry\\fallback} \\
% NEXT:     \midrule
% NEXT:     Order-1 specular & 80.643\% & 8.774\% & 10.530\% & 0.052\% \\
% NEXT:     First diffuse & 13.337\% & 44.345\% & 42.314\% & 0.004\% \\
% NEXT:     Combined non-direct & 75.903\% & 11.280\% & 12.769\% & 0.049\% \\
% NEXT:     \bottomrule
% NEXT:   \end{tabular}
% NEXT:   }
% NEXT: \end{table}
% NEXT:
% NEXT: Image-derived materials inform most of the pooled non-direct body contribution
% NEXT: because the exact specular term is both larger and more often image-mapped. The
% NEXT: first-diffuse component reaches different surfaces. Most of its body-coupled
% NEXT: contribution reaches geometry with no image label or with a label rejected by
% NEXT: the object-material compatibility test. The nonblocking
% NEXT: woody category is zero for retained terminal interactions because a
% NEXT: nonblocking crossing cannot be the first blocking surface. This zero
% NEXT: does not imply that woody canopy evidence is absent from the routes.
The per-image inspection mesh is a separate audit product. It cuts visible
city-mesh triangles at object boundaries and stores each accepted piece with
its source triangle, source image, confidence, area, and visible fraction. A
parallel table keeps rejected pieces when a reliable
inverse projection exists. Reason codes include a degenerate or subpixel
triangle, clipping outside the crop, occlusion by the city mesh, clutter in
front, a transient object, missing object labels, area below the retained
minimum, a grazing plane, a pixel that does not belong to the city mesh, and
a mesh or camera-pose conflict. A rejected piece can lie on the city mesh
because the code describes why that image-space piece did not receive an
accepted object or material label. Rejected pieces do not replace or remove the original
transport geometry.

## AI notes

- Clarifies that refused fishnet faces are evidence QA, not deleted transport faces.
