<!-- AUTO_BEGIN: assembled -->
\section*{Supplementary Information}
\label{sec:si}

This supplement gives the implementation details and sensitivity results that
are needed to reproduce the study but are not needed to follow the main paper.
It covers the semantic model roles, panorama admission, numerical settings,
provenance, convergence, the material-evidence control, timing boundaries, and
additional limitations. All numerical statements refer to the verified
five-site calculations under the first-material-interaction transport contract.

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

% claim: ray_reached_evidence_coverage
\subsection{Ray-reached evidence coverage}
\label{sec:si-ray-reached-coverage}

The audit replays all five sealed routes and 16 seeds with the production
geometry, source curve, atlas, body, 200,000 primary rays, and 4,096 output
cells. It classifies the exact reflection point of every retained order-1
specular path and the first blocking material vertex of every accepted
first-diffuse event. Category counts, transport contribution, body-coupled
fields, and the complete replay all close to the sealed arrays. Direct
transport is not assigned a category because it has no material interaction.

\begin{table}[!t]
  \caption{Share of pooled body-coupled whole-body SAR within each retained non-direct component. Other fallback combines insufficient structural mass, atlas-state refusal, and the residual fallback category.}
  \label{tab:si-ray-reached-coverage}
  \centering
  \resizebox{\columnwidth}{!}{%
  \begin{tabular}{lrrrr}
    \toprule
    Component & \shortstack{Panorama\\informed} & \shortstack{No panorama\\evidence} & \shortstack{Host\\incompatible} & \shortstack{Other\\fallback} \\
    \midrule
    Order-1 specular & 80.643\% & 8.774\% & 10.530\% & 0.052\% \\
    First diffuse & 13.337\% & 44.345\% & 42.314\% & 0.004\% \\
    Combined non-direct & 75.903\% & 11.280\% & 12.769\% & 0.049\% \\
    \bottomrule
  \end{tabular}
  }
\end{table}

Panorama evidence informs most of the pooled non-direct body contribution
because the exact specular term is both larger and more often atlas-bound. The
first-diffuse component has a different support pattern. Most of its
body-coupled contribution reaches geometry with no panorama evidence or with
evidence refused by the host-material compatibility gate. The nonblocking
woody category is zero for retained terminal interactions because a
nonblocking crossing cannot be the first blocking material vertex. This zero
does not imply that woody canopy evidence is absent from the routes.

\begin{figure*}[!t]
  \centering
  \includegraphics[width=\textwidth]{figures/ray_reached_evidence/ray_reached_evidence.pdf}
  \caption{Ray-reached semantic-evidence coverage. Panel (a) partitions the
  pooled non-direct body-coupled whole-body SAR contribution between
  panorama-informed interfaces and declared geometric fallback states. Panel
  (b) gives accepted retained interaction counts for all seven audit
  categories. Direct transport is not applicable because it has no material
  interaction.}
  \label{fig:si-ray-reached-coverage}
\end{figure*}

\section{Panorama registration and admission}
\label{sec:si-registration}

The registration matches the segmented sky boundary in a panorama to the
upper envelope of the support mesh. The stored residual is an angular skyline
error. An admitted pose has a residual no greater than $4^\circ$. The second
test casts the directions labeled as sky from the fitted camera into the mesh.
It records the fraction that hits geometry and the median range of those hits.
A camera is classified as inside the geometry when the hit fraction is greater
than 0.5 and the median range is less than 2 m. The paired condition matters
because a camera inside a wall can still obtain a small silhouette residual.
A large conflict at long range is retained as a distinct low-quality state.

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

\section{Numerical configuration and provenance}
\label{sec:si-configuration}

\begin{table*}[!t]
  \caption{Configuration of the verified five-site result.}
  \label{tab:si-configuration}
  \centering
  \begin{tabular}{p{0.24\textwidth}p{0.70\textwidth}}
    \toprule
    Item & Production value \\
    \midrule
    Sites and routes & Korenmarkt, Prague, Madrid, Mexico City, and Tokyo Hachiko. The fixed routes contain 10, 22, 14, 11, and 16 standpoints. \\
    Geometry and frequency & Original photogrammetric support mesh within a 250 m horizontal radius at 15 GHz. The circular crop area is $196{,}349.54\,\mathrm{m^2}$. \\
    Source measure & Observed route-aligned roofline. Areal density sets the expected source count. Physical three-dimensional roofline length sets the conditional source weights. \\
    Exposure normalization & Per unit $\rho_A P_{\mathrm{EIRP}}$. Normalized whole-body SAR has unit $\mathrm{m^2\,kg^{-1}}$. \\
    Transport & Exact direct term, exact order-1 all-specular term, and stochastic next-event estimation of the first diffuse interaction at the first blocking material vertex. \\
    Surface model & Atlas material mode with measured finish roughness. The material posterior is evaluated at the exact hit texel. \\
    Monte Carlo & 200,000 IID primary rays per standpoint and replica. Seeds 7 through 22 give 16 replicas. Stored convergence looks use 4, 8, 12, and 16 replicas. \\
    Angular output & 4,096 passive cells collect only the first-diffuse estimate. Exact direct and order-1 all-specular paths remain directional atoms. The cells are not launch strata. \\
    Body & Duke with 56,024 surface elements, area $1.87250\,\mathrm{m^2}$, mass 72.4 kg, $T_0=0.500140$, and fixed route-tangent yaw. Body coupling uses the level-2 surface-field model. \\
    \bottomrule
  \end{tabular}
\end{table*}

The receiver is $1.5\,$m above the support surface. Route points are placed at
approximately $6\,$m arc-length intervals, with registered panorama positions
retained as route anchors. The route-visible skyline extraction finds boundary
and crease edges that separate the first visible mesh hit from sky. Duplicate
mesh-edge contacts are combined. The resulting three-dimensional edge
lengths are the quadrature weights. Each source site is shifted vertically by
$0.5\,$m to avoid self-occlusion. Table~\ref{tab:si-source-quadrature} gives the
retained counts.

\begin{table}[!t]
  \caption{Route and roofline quadrature sizes.}
  \label{tab:si-source-quadrature}
  \centering
  \begin{tabular}{lrrr}
    \toprule
    Site & Route points & Quadrature sites & Length (m) \\
    \midrule
    Korenmarkt & 10 & 457 & 157.54 \\
    Prague & 22 & 502 & 267.15 \\
    Madrid & 14 & 207 & 79.40 \\
    Mexico City & 11 & 164 & 63.69 \\
    Tokyo Hachiko & 16 & 400 & 248.76 \\
    \bottomrule
  \end{tabular}
\end{table}

The first-diffuse term uses a reciprocal next-event estimator. For each
primary direction $\mathbf u_n$ drawn uniformly over $4\pi$, the tracer keeps
the first blocking material vertex. It then draws one roofline site from the
arc-length weights and tests the connecting segment. If the connection is
visible, its unscaled contribution is
\begin{equation}
  w_n = \frac{R_n(1-\kappa_n)}{\pi}
  \frac{[\mathbf n_n\!\cdot\!\mathbf d_n]_+}{r_n^2}.
\end{equation}
Here $R_n$ is the unpolarized Fresnel power reflectance, $\kappa_n$ is the
coherent specular share, $\mathbf d_n$ points from the vertex to the sampled
source, and $r_n$ is the connecting distance. Occluded connections contribute
zero. The estimate is $(4\pi/N)\sum_n w_n$. The launch direction determines the
physical arrival direction by reciprocity. Only these sampled first-diffuse
contributions are accumulated in the 4,096-cell Fibonacci grid. Direct sources
and accepted order-1 specular paths are stored as exact directional atoms.

For incidence cosine $c$, complex relative permittivity $\epsilon_r$, surface
root $q=\sqrt{\epsilon_r-(1-c^2)}$, and wavelength $\lambda$, the production
law is
\begin{align}
 R &= \tfrac12\left(\left|\frac{c-q}{c+q}\right|^2+
 \left|\frac{\epsilon_r c-q}{\epsilon_r c+q}\right|^2\right), \\
 \kappa &= \exp\!\left[-\left(\frac{4\pi s c}{\lambda}\right)^2\right].
\end{align}
Thus the reflected specular and diffuse shares are $R\kappa$ and
$R(1-\kappa)$. The surface-finish roughness $s$ excludes larger periodic relief.
Table~\ref{tab:si-materials} gives the evaluated 15 GHz material table. Metal
uses the finite-conductivity value in the same complex-permittivity convention.

\begin{table*}[!t]
  \caption{Evaluated transport materials at 15 GHz. The roughness column is RMS height.}
  \label{tab:si-materials}
  \centering
  \begin{tabular}{lrrr@{\qquad}lrrr}
    \toprule
    Class & $\Re\epsilon_r$ & $-\Im\epsilon_r$ & $s$ ($\mu$m) & Class & $\Re\epsilon_r$ & $-\Im\epsilon_r$ & $s$ ($\mu$m) \\
    \midrule
    Asphalt concrete & 4.83 & 0.569 & 450 & Metal & 1.00 & $1.20\!\times\!10^7$ & 5 \\
    Brick & 3.91 & 0.044 & 30 & Plasterboard & 2.73 & 0.130 & 150 \\
    Ceramic & 7.07 & 0.081 & 280 & Plywood & 2.71 & 0.396 & 50 \\
    Chipboard & 2.58 & 0.215 & 50 & Polymer & 1.99 & 0.103 & 50 \\
    Concrete & 5.24 & 0.461 & 600 & Soil & 5.24 & 0.461 & 600 \\
    Fabric & 1.99 & 0.103 & 50 & Water & 5.24 & 0.461 & 600 \\
    Glass & 6.31 & 0.162 & 1 & Wood & 1.99 & 0.103 & 50 \\
    Marble & 7.07 & 0.081 & 280 & & & & \\
    \bottomrule
  \end{tabular}
\end{table*}

The deterministic order-1 search uses a conservative mirrored-receiver
triangle-cone broad phase when the candidate set reaches 20,000. Its CUDA
Float64 implementation leaves the host exact final test unchanged. The normal
adaptive candidate budget is 120 million. One Tokyo standpoint has zero
accepted order-1 paths, so a relative stopping rule cannot close around zero.
That case records and fully enumerates a 320 million candidate cap. Body
coupling uses fixed blocks of 512 directions. Candidate caps, broad-phase
thresholds, chunks, and block sizes control computation. They do not change the
declared physical model.

The result contains 73 standpoints, 1,168 standpoint-replica fields, 80
site-replica runs, and 233.6 million stochastic primary rays. Every campaign
manifest lists 42 files. All 210 recorded file hashes pass. The aggregate JSON,
CSV, PDF, and PNG also match their artifact manifest. Across the 1,168 fields,
the maximum raw residual between the saved total and the sum of direct,
all-specular, and first-diffuse components is
$1.735\times10^{-18}\,\mathrm{m^{-2}}$. The CUDA body result agrees with the
NumPy reference to a maximum relative error of $6.64\times10^{-16}$ in the
verified benchmark. The verified artifacts are stored under
the roofline campaign output package named
\texttt{current\_five\_city\_\allowbreak{}first\_material\_interaction}.
The Duke STL has SHA-256
\texttt{781e65ef3882f134\allowbreak{}7669e0ddca5dafa82\allowbreak{}cd6368dddd6b9e80\allowbreak{}1dc49613822fe3b}.
The sealed body-area array has SHA-256
\texttt{5dd410b9512fdb02\allowbreak{}74dd1ac1fb8f7b70\allowbreak{}87564abfed998d57\allowbreak{}a25065e87ffebd6a}.
Each calculation manifest also seals the support mesh, atlas, source sites,
source weights, route arrays, material tables, and executable configuration.

\section{Replica convergence and lower tails}
\label{sec:si-convergence}

% claim: replica_convergence_48_to_64
\begin{table}[!t]
  \caption{Current-contract convergence from 48 to 64 replicas. Bootstrap width is the 95\% interval width for route $q_{10}$ whole-body SAR. Shadow change is the largest stepwise change among the six declared shadowed standpoints.}
  \label{tab:si-convergence}
  \centering
  \begin{tabular}{lrrr}
    \toprule
    Site & \shortstack{$q_{10}$ change\\(dB)} & \shortstack{Bootstrap width\\(dB)} & \shortstack{Shadow change\\(dB)} \\
    \midrule
    Korenmarkt & 0.0000723 & 0.000222 & -- \\
    Prague & 0.0000203 & 0.000218 & -- \\
    Madrid & 0.00000615 & 0.000378 & -- \\
    Mexico City & 0.00344 & 0.364 & 0.0125 \\
    Tokyo Hachiko & 0.00491 & 0.0538 & 0.0104 \\
    \bottomrule
  \end{tabular}
\end{table}

The 64-replica extension uses seeds 7 through 70 and nested looks of 16, 24,
32, 48, and 64. Its first 16 replicas are exactly equal to the sealed campaign
arrays after timing fields are removed. Mexico City standpoints 0, 1, and 3
and Tokyo Hachiko standpoints 13, 14, and 15 remain the explicit shadowed
stratum. The first-diffuse estimate is their only nonzero modeled contribution.
From 48 to 64 replicas, their largest pointwise whole-body SAR changes are
0.0125 and 0.0104~dB. The route $q_{10}$ changes are 0.00344 and 0.00491~dB,
and their whole-replica bootstrap widths are 0.364 and 0.0538~dB.

The bootstrap resamples complete replicas jointly over all standpoints, so it
preserves spatial dependence within one replica. Its 2,000 draws use PCG64 with
the authenticated analysis seed 20260814. All five identities, manifests,
component closures, and common inputs pass, and both lower tails meet the
declared 48-to-64 aggregate criteria. Mexico City nevertheless retains
rare-event first-diffuse behavior: its maximum positive replica contribution
is 5738 times its positive-replica median, compared with 2.38 for Tokyo
Hachiko. These intervals remain conditional on each fixed registered route.
They do not include route-selection or city-sampling uncertainty.

\begin{figure*}[!t]
  \centering
  \includegraphics[width=\textwidth]{figures/convergence64/convergence64.pdf}
  \caption{Current-contract convergence through 64 replicas. Panel (a) shows
  route $q_{10}$ whole-body SAR changes from the sealed 16-replica value. Panel
  (b) shows the largest stepwise change among the three shadowed standpoints in
  each of Mexico City and Tokyo Hachiko. The final 48-to-64 changes satisfy the
  declared aggregate lower-tail criteria. Mexico City retains rare-event
  first-diffuse behavior.}
  \label{fig:si-convergence}
\end{figure*}

\section{Primary-ray and angular-cell budgets}
\label{sec:si-budget-sensitivity}

% claim: roofline_budget_sensitivity
The budget diagnostic used paired seeds and common random numbers at the Madrid, Mexico City, and Prague routes. Exact direct and all-specular components were byte identical in every paired comparison, and the 200,000-ray, 4,096-cell replay matched the sealed baseline. The route-median normalized whole-body-SAR changes were small, with a maximum absolute $q_{50}$ difference of 0.000797345~dB among the five cheaper settings. Directional first-diffuse fields did not meet the stated gate. The largest site $q_{90}$ normalized-$L_{1}$ differences were 0.877498, 0.678942, and 0.400218 at 25,000, 50,000, and 100,000 rays, respectively. At 1,024 and 2,048 cells, they were 0.491265 and 0.455431. Each value exceeds the 0.1 gate. Mexico City shadowed-point maximum absolute whole-body-SAR changes were 0.707362, 0.563841, and 0.217259~dB for the three ray settings, compared with 0.00206975 and 0.00088674~dB for the two cell settings.

Ray cuts also do not give a defensible end-to-end speedup. At 25,000 rays, estimator-wall-time ratios relative to the baseline range from 0.991 to 1.064 across the three routes. Exact all-specular work takes 8.06 to 23.79~s in the baseline, whereas stochastic tracing takes 1.15 to 2.40~s. The $q_{90}$ variance-time ratios for every ray-reduced arm exceed one, with a minimum of 3.16. The reported timing therefore leaves the exact specular stage dominant while the reduced ray settings increase first-diffuse variance. Figure~\ref{fig:si-budget-sensitivity} retains the 200,000-ray, 4,096-cell setting as the production baseline.

\begin{figure*}[!t]
  \centering
  \includegraphics[width=\textwidth]{figures/budget_sensitivity/budget_sensitivity.pdf}
  \caption{Primary-ray and angular-cell budget sensitivity under the current first-material transport contract. All five cheaper settings leave route-median whole-body SAR nearly unchanged, but each exceeds the directional first-diffuse gate. Exact direct and order-1 specular components remain invariant. The diagnostic retains 200,000 rays and 4,096 cells.}
  \label{fig:si-budget-sensitivity}
\end{figure*}

\section{Paired material-evidence control}
\label{sec:si-material-control}

The control replaces the panorama-derived atlas layer with the geometric
fallback in Madrid and Mexico City. Each pair keeps the support mesh, route,
source curve, source weights, body, frequency, transport topology, ray count,
output cells, and 16 seeds fixed. A strict compatibility check permits changes
only in the material mode, the material arrays and hashes, the run
configuration, and the presence of the atlas files. Both paired manifests pass
all 42 file hashes. The comparison therefore measures sensitivity to the atlas
evidence layer under the current model. It does not isolate reflectance because
the atlas also changes roughness, specular share, and the nonblocking state of
woody vegetation. It does not measure semantic or material accuracy.

\begin{table}[!t]
  \caption{Atlas-to-geometric change in route quantiles of normalized
  whole-body SAR. Positive values mean that the atlas result is larger.}
  \label{tab:si-material-control}
  \centering
  \begin{tabular}{lrrr}
    \toprule
    Site & q10 (dB) & q50 (dB) & q90 (dB) \\
    \midrule
    Madrid & 0.233 & 0.249 & 0.269 \\
    Mexico City & 24.84 & -0.158 & 0.104 \\
    \bottomrule
  \end{tabular}
\end{table}

The direct component is identical within each pair. In Madrid, the atlas raises
the route-median all-specular whole-body SAR by 1.89 dB and lowers the
first-diffuse component by 12.43 dB. Their combined effect changes the total
route median by 0.249 dB. Mexico City's 24.84 dB q10 change is set by three
shadowed standpoints where both alternatives are near zero and first-diffuse
transport is the only nonzero modeled contribution. The Mexico City median and q90
changes are $-0.158$ and 0.104 dB. The two sites show that component changes can
be much larger than the change in total normalized whole-body SAR. The result
supports a model-layer sensitivity statement for these routes only.

\section{Timing boundary}
\label{sec:si-timing}

The repeated numerical campaigns start from a ready city scene. Their wall
times on one A6000 are 29.79 s for Korenmarkt, 69.02 s for Prague, 40.70 s for
Madrid, 30.92 s for Mexico City, and 50.11 s for Tokyo Hachiko. These times
include the 16 transport replicas and body coupling for the complete fixed
route. They exclude image and mesh acquisition, panorama registration,
semantic inference, depth processing, and atlas construction. Persistent
transport caches and exact conservative broad-phase screening reduce repeated
work with no change to the saved scientific arrays.

The cold scene path has no complete common timing ledger. Available 14-panorama
records give 21.3 to 26.6 min for the hybrid semantic pass and 5.3 to 13.6 min
for atlas construction. Acquisition, registration, depth, and fusion were not
all timed separately. One live A6000 parity check took 116.981 s for one
panorama with independent model sessions. A shared session processed two
panoramas in 199.228 s and reproduced every scientific panorama array, concept
cache array, prompt gate, and normalized metadata field exactly. These values
are implementation anchors. They do not define a universal time per panorama.
A single cold end-to-end time is therefore not reported.

\section{Additional limitations}
\label{sec:si-limitations}

The transport result contains exact direct transport, exact single-reflection
all-specular transport, and the first diffuse interaction. A sampled
first-diffuse path stops at that diffuse event. The model has no diffuse-to-specular suffix, higher
specular order, or complete multipath expansion. The controlled open-square
test validates the first-diffuse normalization, visibility, inverse-square loss,
and cosine factors. The maximum adjoint-versus-Sionna difference is 0.0621 dB
for the bounced term and 0.0344 dB for total transport in that test. The same
three-way test has not been repeated for the full five-site stack with its atlas
materials and exact specular term. The test provides component validation. It
does not provide external validation of every city result. The level-2 body
coupling uses one-sided local incidence. It does not trace body self-occlusion.

The five routes are selected case studies. Their differences do not rank the
five cities and do not estimate population exposure. Each result is normalized
per unit $\rho_A P_{\mathrm{EIRP}}$, so it is not an absolute prediction for an
operator deployment. The study uses one 15 GHz frequency, one body phantom,
one fixed route-tangent body orientation, one roofline source law, and five
plaza routes. Additional frequencies, body models, headings, deployment laws,
street canyons, parks, and repeated route selections remain outside the present
evidence.

Panorama evidence covers only surfaces that an admitted camera can see and cast
onto the support mesh. Unsupported atlas cells use the geometric material.
Transient pixels are withheld from the static surface. Image evidence can
preserve within-triangle material variation, but it cannot recover geometry
that is absent from the photogrammetric mesh. The two-site material control
tests downstream sensitivity and supplies no semantic ground truth. Coverage
on all support-mesh area also differs from coverage on the subset reached by
propagation paths. The ray-reached audit now reports where the recorded atlas
and fallback rule act in retained order-1 specular and first-diffuse transport.
It does not test whether the panorama labels or fallback material are correct.
The current claims therefore remain conditional on those recorded surfaces.

\clearpage

% End of supplementary-information body.
<!-- AUTO_END: assembled -->


















## Aggregation notes (AI-owned)
