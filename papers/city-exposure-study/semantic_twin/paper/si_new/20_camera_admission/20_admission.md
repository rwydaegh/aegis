% PREV: The registration matches the segmented sky boundary in a panorama to the
% PREV: upper envelope of the support mesh. The stored residual is an angular skyline
% PREV: error. An admitted pose has a residual no greater than $4^\circ$. The second
% PREV: test casts the directions labeled as sky from the fitted camera into the mesh.
% PREV: It records the fraction that hits geometry and the median range of those hits.
% PREV: A camera is classified as inside the geometry when the hit fraction is greater
% PREV: than 0.5 and the median range is less than 2 m. The paired condition matters
% PREV: because a camera inside a wall can still obtain a small silhouette residual.
% PREV: A large conflict at long range is retained as a distinct low-quality state.
The current admission policy also requires complete sky diagnostics and a
vertical registration optimum inside the altitude search interval. It refuses a
pose with a missing residual, a residual above $4^\circ$, missing sky
diagnostics, the near inside-geometry signature, or an optimum at the altitude
bound. Each atlas stores the exact policy version that selected its cameras.
New builds use \texttt{registration-admission-v2}. The sealed Korenmarkt atlas
uses its recorded version-1 policy and is not silently restamped. An admitted
camera can still be skipped if its dense and SAM semantic rasters are missing,
incomplete, malformed, or inconsistent with the fixed vocabulary. These
refusals prevent an image, pose, model, or mesh mismatch from entering fusion.

## AI notes

- Keeps gate version provenance explicit without using stale camera counts.
