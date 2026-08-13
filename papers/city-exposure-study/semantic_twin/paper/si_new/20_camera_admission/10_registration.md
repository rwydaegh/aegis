% PREV: \section{Panorama registration and admission}
% PREV: \label{sec:si-registration}
% NEXT: The current admission policy also requires complete sky diagnostics and a
% NEXT: vertical registration optimum inside the altitude search interval. It refuses a
% NEXT: pose with a missing residual, a residual above $4^\circ$, missing sky
% NEXT: diagnostics, the near inside-geometry signature, or an optimum at the altitude
% NEXT: bound. Each atlas stores the exact policy version that selected its cameras.
% NEXT: New builds use \texttt{registration-admission-v2}. The sealed Korenmarkt atlas
% NEXT: uses its recorded version-1 policy and is not silently restamped. An admitted
% NEXT: camera can still be skipped if its dense and SAM semantic rasters are missing,
% NEXT: incomplete, malformed, or inconsistent with the fixed vocabulary. These
% NEXT: refusals prevent an image, pose, model, or mesh mismatch from entering fusion.
The registration matches the segmented sky boundary in a panorama to the
upper envelope of the support mesh. The stored residual is an angular skyline
error. An admitted pose has a residual no greater than $4^\circ$. The second
test casts the directions labeled as sky from the fitted camera into the mesh.
It records the fraction that hits geometry and the median range of those hits.
A camera is classified as inside the geometry when the hit fraction is greater
than 0.5 and the median range is less than 2 m. The paired condition matters
because a camera inside a wall can still obtain a small silhouette residual.
A large conflict at long range is retained as a distinct low-quality state.

## AI notes

- Defines the two independent registration tests.
