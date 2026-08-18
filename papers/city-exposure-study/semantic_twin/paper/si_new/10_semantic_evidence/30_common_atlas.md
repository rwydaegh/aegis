% PREV: The four rectilinear crops of each 360-degree street image face $0^\circ$,
% PREV: $90^\circ$, $180^\circ$, and $270^\circ$, zero pitch, a $90^\circ$ field of
% PREV: view, and $1536$ pixels per side. Mask2Former runs at $1536$ pixels. SAM~3 uses
% PREV: its trained $1008$-pixel input, a score threshold of 0.35, and prompt batches of
% PREV: 32. Production fixes the full model, source, and catalog identities listed in
% PREV: Table~\ref{tab:si-semantic-identity}. It refuses another model pair or a catalog
% PREV: change, even if the number of prompts remains the same.
% PREV:
% PREV: \begin{table*}[!t]
% PREV:   \caption{Fixed model identities used by the production material map.}
% PREV:   \label{tab:si-semantic-identity}
% PREV:   \centering
% PREV:   \scriptsize
% PREV:   \begin{tabular}{lp{0.72\textwidth}}
% PREV:     \toprule
% PREV:     Item & Immutable identifier \\
% PREV:     \midrule
% PREV:     Mask2Former weights & \texttt{4772b6bf101d91f2534c106dc524d906aeb3c68a} \\
% PREV:     SAM~3 weights & \texttt{3c879f39826c281e95690f02c7821c4de09afae7} \\
% PREV:     SAM~3 source & \texttt{96914d2425f90a64f45ca977c2b5165418099543} \\
% PREV:     Parsed concept catalog & \texttt{66d0dfefba87bde5081cfa82108ca60d47c79cf641df3ec44129ec20bb90453b} \\
% PREV:     \bottomrule
% PREV:   \end{tabular}
% PREV: \end{table*}
% NEXT: Material labels remain probabilistic when observations are combined. Vistas-backed pixels
% NEXT: use the declared full $p(\text{material}\mid\text{entity})$ table. Concept-backed
% NEXT: pixels use the full material distribution of the detected prompt. Transport
% NEXT: removes probability assigned to air, unknown material, people, vehicles, and
% NEXT: participating volumes. It assigns an image-derived structural material only when
% NEXT: the remaining compatible structural probability is strictly greater than 0.5.
% NEXT: An exact tie and any unsupported material-map cell use the geometric face material.
% NEXT: Reflected power uses the posterior-weighted material coefficients. The
% NEXT: specular sampling probability uses the posterior-weighted reflected specular
% NEXT: share. Grass keeps the geometric ground interface. Woody canopy labels are
% NEXT: nonblocking until a closed canopy volume can supply path lengths for
% NEXT: volume attenuation.
Rays from each 360-degree street image intersect the original city mesh. Each
observed mesh triangle has a common $8\times8$ barycentric material grid. Its
coordinates are fixed to the triangle and do not depend on the camera. Each
camera first reduces all of its rays in one grid cell to at most one
confidence-weighted contribution. Camera
means are then added across views. Range and raw pixel density give no extra
weight. Two images can therefore place a material boundary at different
positions on one large mesh triangle. Both observations are accumulated in
the same barycentric cells and remain a distribution. The transport lookup uses the
original triangle identifier and the barycentric coordinates of each ray hit.
The highly tessellated mesh shown for inspection is a display object and
is not the transport mesh.

## AI notes

- This is the direct answer to the perspective-dependent seam question.
