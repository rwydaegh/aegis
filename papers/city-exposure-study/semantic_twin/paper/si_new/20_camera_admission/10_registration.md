% PREV: \section{Street-image alignment and acceptance}
% PREV: \label{sec:si-registration}
% NEXT: The current acceptance policy also requires complete sky checks and a best-fit
% NEXT: camera height inside the tested altitude interval. It rejects a
% NEXT: pose with a missing residual, a residual above $4^\circ$, missing sky
% NEXT: diagnostics, the near inside-geometry signature, or an optimum at the altitude
% NEXT: bound. Each material map stores the policy version that selected its cameras.
% NEXT: New builds use \texttt{registration-admission-v2}. The verified Korenmarkt map
% NEXT: uses its recorded version-1 policy. An accepted
% NEXT: camera can still be skipped if its dense and SAM label images are missing,
% NEXT: incomplete, malformed, or inconsistent with the fixed vocabulary. These
% NEXT: rejections prevent an image, pose, model, or mesh mismatch from entering the
% NEXT: combined material map.
The alignment matches the segmented sky boundary in a 360-degree street image
to the upper edge of the city mesh. The stored residual is the angular skyline
error. An accepted camera pose has a residual no greater than $4^\circ$. The second
test casts the directions labeled as sky from the fitted camera into the mesh.
It records the fraction that hits geometry and the median range of those hits.
A camera is classified as inside the geometry when the hit fraction is greater
than 0.5 and the median range is less than 2 m. The paired condition matters
because a camera inside a wall can still obtain a small silhouette residual.
A large conflict at long range is recorded as a separate low-quality state.

## AI notes

- Defines the two independent registration tests.
