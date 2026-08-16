% PREV: The alignment matches the segmented sky boundary in a 360-degree street image
% PREV: to the upper edge of the city mesh. The stored residual is the angular skyline
% PREV: error. An accepted camera pose has a residual no greater than $4^\circ$. The second
% PREV: test casts the directions labeled as sky from the fitted camera into the mesh.
% PREV: It records the fraction that hits geometry and the median range of those hits.
% PREV: A camera is classified as inside the geometry when the hit fraction is greater
% PREV: than 0.5 and the median range is less than 2 m. The paired condition matters
% PREV: because a camera inside a wall can still obtain a small silhouette residual.
% PREV: A large conflict at long range is recorded as a separate low-quality state.
The current acceptance policy also requires complete sky checks and a best-fit
camera height inside the tested altitude interval. It rejects a
pose with a missing residual, a residual above $4^\circ$, missing sky
diagnostics, the near inside-geometry signature, or an optimum at the altitude
bound. Each material map stores the policy version that selected its cameras.
New builds use \texttt{registration-admission-v2}. The verified Korenmarkt map
uses its recorded version-1 policy. An accepted
camera can still be skipped if its dense and SAM label images are missing,
incomplete, malformed, or inconsistent with the fixed vocabulary. These
rejections prevent an image, pose, model, or mesh mismatch from entering the
combined material map.

## AI notes

- Keeps gate version provenance explicit without using stale camera counts.
