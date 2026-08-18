% PREV: The image-labeling pass uses two models with separate roles. Mask2Former with the
% PREV: 65-class Mapillary Vistas vocabulary assigns one street-scene object class to every pixel. It
% PREV: therefore supplies the complete object map and identifies small objects such
% PREV: as poles, signs, curbs, and bicycle racks. One Vistas building label can contain
% PREV: brick, stone, render, glass, and metal. SAM~3 supplies the open-vocabulary
% PREV: material labels needed inside such broad object classes. The production
% PREV: catalog contains 60 text prompts and 61 raster identifiers including the
% PREV: unlabeled identifier. Examples include ``brick facade'', ``glass window'',
% PREV: ``metal cladding panel'', and separate ground, grass, shrub,
% PREV: tree, and forest concepts. The prompts are also gated by the Vistas classes. A class
% PREV: must occupy at least 256 pixels in a $1536\times1536$ crop before its related
% PREV: prompts are sent to SAM~3. The gate reduces work and removes prompts that have no
% PREV: matching object in the view. The complete prompt list and its object, material,
% PREV: attribute, and vegetation mappings are stored in
% PREV: \texttt{config/semantic\_concepts.json}.
% NEXT: Rays from each 360-degree street image intersect the original city mesh. Each
% NEXT: observed mesh triangle has a common $8\times8$ barycentric material grid. Its
% NEXT: coordinates are fixed to the triangle and do not depend on the camera. Each
% NEXT: camera first reduces all of its rays in one grid cell to at most one
% NEXT: confidence-weighted contribution. Camera
% NEXT: means are then added across views. Range and raw pixel density give no extra
% NEXT: weight. Two images can therefore place a material boundary at different
% NEXT: positions on one large mesh triangle. Both observations are accumulated in
% NEXT: the same barycentric cells and remain a distribution. The transport lookup uses the
% NEXT: original triangle identifier and the barycentric coordinates of each ray hit.
% NEXT: The highly tessellated mesh shown for inspection is a display object and
% NEXT: is not the transport mesh.
The four rectilinear crops of each 360-degree street image face $0^\circ$,
$90^\circ$, $180^\circ$, and $270^\circ$, zero pitch, a $90^\circ$ field of
view, and $1536$ pixels per side. Mask2Former runs at $1536$ pixels. SAM~3 uses
its trained $1008$-pixel input, a score threshold of 0.35, and prompt batches of
32. Production fixes the full model, source, and catalog identities listed in
Table~\ref{tab:si-semantic-identity}. It refuses another model pair or a catalog
change, even if the number of prompts remains the same.

\begin{table*}[!t]
  \caption{Fixed model identities used by the production material map.}
  \label{tab:si-semantic-identity}
  \centering
  \scriptsize
  \begin{tabular}{lp{0.72\textwidth}}
    \toprule
    Item & Immutable identifier \\
    \midrule
    Mask2Former weights & \texttt{4772b6bf101d91f2534c106dc524d906aeb3c68a} \\
    SAM~3 weights & \texttt{3c879f39826c281e95690f02c7821c4de09afae7} \\
    SAM~3 source & \texttt{96914d2425f90a64f45ca977c2b5165418099543} \\
    Parsed concept catalog & \texttt{66d0dfefba87bde5081cfa82108ca60d47c79cf641df3ec44129ec20bb90453b} \\
    \bottomrule
  \end{tabular}
\end{table*}

## AI notes

- Exact model and catalog identities are reproducibility data.
