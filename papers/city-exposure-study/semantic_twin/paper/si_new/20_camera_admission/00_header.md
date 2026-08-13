% NEXT: The registration matches the segmented sky boundary in a panorama to the
% NEXT: upper envelope of the support mesh. The stored residual is an angular skyline
% NEXT: error. An admitted pose has a residual no greater than $4^\circ$. The second
% NEXT: test casts the directions labeled as sky from the fitted camera into the mesh.
% NEXT: It records the fraction that hits geometry and the median range of those hits.
% NEXT: A camera is classified as inside the geometry when the hit fraction is greater
% NEXT: than 0.5 and the median range is less than 2 m. The paired condition matters
% NEXT: because a camera inside a wall can still obtain a small silhouette residual.
% NEXT: A large conflict at long range is retained as a distinct low-quality state.
\section{Panorama registration and admission}
\label{sec:si-registration}

## Reviews

_(empty)_
