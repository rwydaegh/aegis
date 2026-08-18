% PREV: Rays from each 360-degree street image intersect the original city mesh. Each
% PREV: observed mesh triangle has a common $8\times8$ barycentric material grid. Its
% PREV: coordinates are fixed to the triangle and do not depend on the camera. Each
% PREV: camera first reduces all of its rays in one grid cell to at most one
% PREV: confidence-weighted contribution. Camera
% PREV: means are then added across views. Range and raw pixel density give no extra
% PREV: weight. Two images can therefore place a material boundary at different
% PREV: positions on one large mesh triangle. Both observations are accumulated in
% PREV: the same barycentric cells and remain a distribution. The transport lookup uses the
% PREV: original triangle identifier and the barycentric coordinates of each ray hit.
% PREV: The highly tessellated mesh shown for inspection is a display object and
% PREV: is not the transport mesh.
% NEXT: The per-image inspection mesh is a separate audit product. It cuts visible
% NEXT: city-mesh triangles at object boundaries and stores each accepted piece with
% NEXT: its source triangle, source image, confidence, area, and visible fraction. A
% NEXT: parallel table keeps rejected pieces when a reliable
% NEXT: inverse projection exists. Reason codes include a degenerate or subpixel
% NEXT: triangle, clipping outside the crop, occlusion by the city mesh, clutter in
% NEXT: front, a transient object, missing object labels, area below the retained
% NEXT: minimum, a grazing plane, a pixel that does not belong to the city mesh, and
% NEXT: a mesh or camera-pose conflict. A rejected piece can lie on the city mesh
% NEXT: because the code describes why that image-space piece did not receive an
% NEXT: accepted object or material label. Rejected pieces do not replace or remove the original
% NEXT: transport geometry.
Material labels remain probabilistic when observations are combined. Vistas-backed pixels
use the declared full $p(\text{material}\mid\text{entity})$ table. Concept-backed
pixels use the full material distribution of the detected prompt. Transport
removes probability assigned to air, unknown material, people, vehicles, and
participating volumes. It assigns an image-derived structural material only when
the remaining compatible structural probability is strictly greater than 0.5.
An exact tie and any unsupported material-map cell use the geometric face material.
Reflected power uses the posterior-weighted material coefficients. The
specular sampling probability uses the posterior-weighted reflected specular
share. Grass keeps the geometric ground interface. Woody canopy labels are
nonblocking until a closed canopy volume can supply path lengths for
volume attenuation.

## AI notes

- Describes the strict transport gate and the current vegetation rule.
