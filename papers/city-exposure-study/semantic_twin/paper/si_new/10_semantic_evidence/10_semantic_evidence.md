<!-- AUTO_BEGIN: assembled -->
\section{Image labels and material mapping}
\label{sec:si-semantics}

The image-labeling pass uses two models with separate roles. Mask2Former with the
65-class Mapillary Vistas vocabulary assigns one street-scene object class to every pixel. It
therefore supplies the complete object map and identifies small objects such
as poles, signs, curbs, and bicycle racks. One Vistas building label can contain
brick, stone, render, glass, and metal. SAM~3 supplies the open-vocabulary
material labels needed inside such broad object classes. The production
catalog contains 60 text prompts and 61 raster identifiers including the
unlabeled identifier. Examples include ``brick facade'', ``glass window'',
``metal cladding panel'', and separate ground, grass, shrub,
tree, and forest concepts. The prompts are also gated by the Vistas classes. A class
must occupy at least 256 pixels in a $1536\times1536$ crop before its related
prompts are sent to SAM~3. The gate reduces work and removes prompts that have no
matching object in the view. The complete prompt list and its object, material,
attribute, and vegetation mappings are stored in
\texttt{config/semantic\_concepts.json}.

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

The per-image inspection mesh is a separate audit product. It cuts visible
city-mesh triangles at object boundaries and stores each accepted piece with
its source triangle, source image, confidence, area, and visible fraction. A
parallel table keeps rejected pieces when a reliable
inverse projection exists. Reason codes include a degenerate or subpixel
triangle, clipping outside the crop, occlusion by the city mesh, clutter in
front, a transient object, missing object labels, area below the retained
minimum, a grazing plane, a pixel that does not belong to the city mesh, and
a mesh or camera-pose conflict. A rejected piece can lie on the city mesh
because the code describes why that image-space piece did not receive an
accepted object or material label. Rejected pieces do not replace or remove the original
transport geometry.

% claim: ray_reached_evidence_coverage
\subsection{Material labels on reached surfaces}
\label{sec:si-ray-reached-coverage}

The audit replays all five verified routes and 16 seeds with the production
geometry, source curve, material map, body, 200,000 primary rays, and 4,096 output
cells. It classifies the exact reflection point of every retained order-1
specular path and the first blocking surface of every accepted
first-diffuse event. Category counts, transport contribution, body-coupled
fields, and the complete replay all match the verified arrays. Direct
transport is not assigned a category because it has no material interaction.

\begin{table}[!t]
  \caption{Share of pooled body-coupled whole-body SAR within each retained non-direct component. Other fallback combines insufficient structural probability, a rejected image label, and the remaining geometry-based category.}
  \label{tab:si-ray-reached-coverage}
  \centering
  \resizebox{\columnwidth}{!}{%
  \begin{tabular}{lrrrr}
    \toprule
    Component & \shortstack{Image\\mapped} & \shortstack{No image\\label} & \shortstack{Object-material\\mismatch} & \shortstack{Other geometry\\fallback} \\
    \midrule
    Order-1 specular & 80.643\% & 8.774\% & 10.530\% & 0.052\% \\
    First diffuse & 13.337\% & 44.345\% & 42.314\% & 0.004\% \\
    Combined non-direct & 75.903\% & 11.280\% & 12.769\% & 0.049\% \\
    \bottomrule
  \end{tabular}
  }
\end{table}

Image-derived materials inform most of the pooled non-direct body contribution
because the exact specular term is both larger and more often image-mapped. The
first-diffuse component reaches different surfaces. Most of its body-coupled
contribution reaches geometry with no image label or with a label rejected by
the object-material compatibility test. The nonblocking
woody category is zero for retained terminal interactions because a
nonblocking crossing cannot be the first blocking surface. This zero
does not imply that woody canopy evidence is absent from the routes.

\begin{figure*}[!t]
  \centering
  \includegraphics[width=\textwidth]{figures/ray_reached_evidence/ray_reached_evidence.pdf}
  \caption{Material labels on surfaces reached by modeled paths. Panel (a) partitions the
  pooled non-direct body-coupled whole-body SAR contribution between
  image-mapped and geometry-based materials. Panel
  (b) gives accepted retained interaction counts for all seven audit
  categories. Direct transport is not applicable because it has no material
  interaction.}
  \label{fig:si-ray-reached-coverage}
\end{figure*}
<!-- AUTO_END: assembled -->




























## Aggregation notes (AI-owned)
