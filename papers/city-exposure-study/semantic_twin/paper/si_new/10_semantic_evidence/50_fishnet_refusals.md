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
