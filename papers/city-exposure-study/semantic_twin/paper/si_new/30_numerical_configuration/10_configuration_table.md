% PREV: \section{Numerical configuration and provenance}
% PREV: \label{sec:si-configuration}
% NEXT: The receiver is $1.5\,$m above the support surface. Route points are placed at
% NEXT: approximately $6\,$m arc-length intervals, with registered panorama positions
% NEXT: retained as route anchors. The route-visible skyline extraction finds boundary
% NEXT: and crease edges that separate the first visible mesh hit from sky. Duplicate
% NEXT: mesh-edge contacts are combined. The resulting three-dimensional edge
% NEXT: lengths are the quadrature weights. Each source site is shifted vertically by
% NEXT: $0.5\,$m to avoid self-occlusion. Table~\ref{tab:si-source-quadrature} gives the
% NEXT: retained counts.
% NEXT:
% NEXT: \begin{table}[!t]
% NEXT:   \caption{Route and roofline quadrature sizes.}
% NEXT:   \label{tab:si-source-quadrature}
% NEXT:   \centering
% NEXT:   \begin{tabular}{lrrr}
% NEXT:     \toprule
% NEXT:     Site & Route points & Quadrature sites & Length (m) \\
% NEXT:     \midrule
% NEXT:     Korenmarkt & 10 & 457 & 157.54 \\
% NEXT:     Prague & 22 & 502 & 267.15 \\
% NEXT:     Madrid & 14 & 207 & 79.40 \\
% NEXT:     Mexico City & 11 & 164 & 63.69 \\
% NEXT:     Tokyo Hachiko & 16 & 400 & 248.76 \\
% NEXT:     \bottomrule
% NEXT:   \end{tabular}
% NEXT: \end{table}
% NEXT:
% NEXT: The first-diffuse term uses a reciprocal next-event estimator. For each
% NEXT: primary direction $\mathbf u_n$ drawn uniformly over $4\pi$, the tracer keeps
% NEXT: the first blocking material vertex. It then draws one roofline site from the
% NEXT: arc-length weights and tests the connecting segment. If the connection is
% NEXT: visible, its unscaled contribution is
% NEXT: \begin{equation}
% NEXT:   w_n = \frac{R_n(1-\kappa_n)}{\pi}
% NEXT:   \frac{[\mathbf n_n\!\cdot\!\mathbf d_n]_+}{r_n^2}.
% NEXT: \end{equation}
% NEXT: Here $R_n$ is the unpolarized Fresnel power reflectance, $\kappa_n$ is the
% NEXT: coherent specular share, $\mathbf d_n$ points from the vertex to the sampled
% NEXT: source, and $r_n$ is the connecting distance. Occluded connections contribute
% NEXT: zero. The estimate is $(4\pi/N)\sum_n w_n$. The launch direction determines the
% NEXT: physical arrival direction by reciprocity. Only these sampled first-diffuse
% NEXT: contributions are accumulated in the 4,096-cell Fibonacci grid. Direct sources
% NEXT: and accepted order-1 specular paths are stored as exact directional atoms.
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

## AI notes

- Main reproducibility table. Computational controls are described separately.
