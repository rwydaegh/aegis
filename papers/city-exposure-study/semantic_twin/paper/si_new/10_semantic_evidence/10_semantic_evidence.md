<!-- AUTO_BEGIN: assembled -->
\section{Semantic evidence and surface fusion}
\label{sec:si-semantics}

The semantic pass uses two models with separate roles. Mask2Former with the
65-class Mapillary Vistas vocabulary assigns one street-scene entity to every pixel. It
therefore supplies the complete entity layer and identifies small objects such
as poles, signs, curbs, and bicycle racks. One Vistas building label can contain
brick, stone, render, glass, and metal. SAM~3 supplies the open-vocabulary
material evidence needed inside such broad entity classes. The production
catalog contains 60 text prompts and 61 raster identifiers including the
unlabeled identifier. Examples include ``brick facade'', ``glass window'',
``metal cladding panel'', and separate ground, grass, shrub,
tree, and forest concepts. The prompts are also gated by the Vistas classes. A class
must occupy at least 256 pixels in a $1536\times1536$ crop before its related
prompts are sent to SAM~3. The gate reduces work and removes prompts that have no
entity support in the view. The complete prompt list and its entity, material,
attribute, and vegetation mappings are stored in
\texttt{config/semantic\_concepts.json}.

The four rectilinear crops of each panorama use yaw angles of $0^\circ$,
$90^\circ$, $180^\circ$, and $270^\circ$, zero pitch, a $90^\circ$ field of
view, and $1536$ pixels per side. Mask2Former runs at $1536$ pixels. SAM~3 uses
its trained $1008$-pixel input, a score threshold of 0.35, and prompt batches of
32. Production fixes the full model, source, and catalog identities listed in
Table~\ref{tab:si-semantic-identity}. It refuses another model pair or a catalog
change, even if the number of prompts remains the same.

\begin{table*}[!t]
  \caption{Immutable semantic identities used by the production atlas.}
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

Panorama rays intersect the original support mesh. A common $8\times8$
barycentric atlas is defined on each observed support triangle. Its coordinate
system is fixed to the triangle and is independent of the camera. Each camera
first reduces all of its rays in one atlas cell to at most one
confidence-weighted contribution. Camera
means are then added across views. Range and raw pixel density give no extra
weight. Therefore, two panoramas can place a material boundary at different
positions on one large support triangle. Both observations are accumulated in
the same barycentric cells and remain a distribution. The transport lookup uses the
original triangle identifier and the barycentric coordinates of each ray hit.
The highly tessellated mesh shown for atlas inspection is a display object and
is not the transport mesh.

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
<!-- AUTO_END: assembled -->















## Aggregation notes (AI-owned)
