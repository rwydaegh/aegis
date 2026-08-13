% PREV: Panorama rays intersect the original support mesh. A common $8\times8$
% PREV: barycentric atlas is defined on each observed support triangle. Its coordinate
% PREV: system is fixed to the triangle and is independent of the camera. Each camera
% PREV: first reduces all of its rays in one atlas cell to at most one
% PREV: confidence-weighted contribution. Camera
% PREV: means are then added across views. Range and raw pixel density give no extra
% PREV: weight. Therefore, two panoramas can place a material boundary at different
% PREV: positions on one large support triangle. Both observations are accumulated in
% PREV: the same barycentric cells and remain a distribution. The transport lookup uses the
% PREV: original triangle identifier and the barycentric coordinates of each ray hit.
% PREV: The highly tessellated mesh shown for atlas inspection is a display object and
% PREV: is not the transport mesh.
% NEXT: The per-view fishnet is a separate audit product. It cuts visible support
% NEXT: triangles at semantic boundaries for inspection and stores each accepted piece
% NEXT: with its source triangle, image support, confidence, area, and visible
% NEXT: fraction. A parallel table keeps rejected candidate geometry when a reliable
% NEXT: inverse projection exists. Reason codes include a degenerate or subpixel
% NEXT: triangle, clipping outside the crop, occlusion by the support mesh, clutter in
% NEXT: front, a transient object, missing semantic support, area below the retained
% NEXT: minimum, a grazing plane, a pixel that is not owned by the support surface, and
% NEXT: a mesh or pose conflict. A rejected piece can lie on the support mesh because
% NEXT: the code describes why that image-space piece was not accepted as observed
% NEXT: semantic evidence. Rejected pieces do not replace or remove the original
% NEXT: transport geometry.
Material evidence remains probabilistic through fusion. Vistas-backed pixels
use the declared full $p(\text{material}\mid\text{entity})$ table. Concept-backed
pixels use the full material distribution of the detected prompt. Transport
removes probability assigned to air, unknown material, people, vehicles, and
participating volumes. It binds an image-derived structural interface only when
the remaining compatible structural mass is strictly greater than 0.5. An
exact tie and any unsupported atlas cell use the geometric face material.
Reflected power uses the posterior-weighted material coefficients. The
specular sampling probability uses the posterior-weighted reflected specular
share. Grass keeps the geometric ground interface. Woody canopy evidence is
nonblocking until registered closed canopy geometry can supply path chords for
volume attenuation.

## AI notes

- Describes the strict transport gate and the current vegetation rule.
