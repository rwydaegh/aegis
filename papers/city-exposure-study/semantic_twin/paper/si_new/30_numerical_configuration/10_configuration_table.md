% PREV: \section{Numerical settings and file verification}
% PREV: \label{sec:si-configuration}
% NEXT: The receiver is $1.5\,$m above the city surface. Route points are placed at
% NEXT: approximately $6\,$m intervals along the route, with aligned street-image
% NEXT: positions retained as route anchors. The visible-roofline calculation finds boundary
% NEXT: and crease edges that separate the first visible mesh hit from sky. Duplicate
% NEXT: mesh-edge contacts are combined. The resulting three-dimensional edge
% NEXT: lengths are the numerical weights. Each possible transmitter position is shifted vertically by
% NEXT: $0.5\,$m to avoid self-occlusion. Table~\ref{tab:si-source-quadrature} gives the
% NEXT: retained counts.
% NEXT:
% NEXT: \begin{table}[!t]
% NEXT:   \caption{Number of route points and roofline segments.}
% NEXT:   \label{tab:si-source-quadrature}
% NEXT:   \centering
% NEXT:   \begin{tabular}{lrrr}
% NEXT:     \toprule
% NEXT:     Site & Route points & Roofline segments & Length (m) \\
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
% NEXT: the first blocking surface. It then draws one roofline segment from the
% NEXT: arc-length weights and tests the connecting segment. If the connection is
% NEXT: visible, its unscaled contribution is
% NEXT: \begin{equation}
% NEXT:   w_n = \frac{R_n(1-\kappa_n)}{\pi}
% NEXT:   \frac{[\mathbf n_n\!\cdot\!\mathbf d_n]_+}{r_n^2}.
% NEXT: \end{equation}
% NEXT: Here $R_n$ is the unpolarized Fresnel power reflectance, $\kappa_n$ is the
% NEXT: coherent specular share, $\mathbf d_n$ points from the surface to the sampled
% NEXT: transmitter position, and $r_n$ is the connecting distance. Occluded connections contribute
% NEXT: zero. The estimate is $(4\pi/N)\sum_n w_n$. The launch direction determines the
% NEXT: physical arrival direction by reciprocity. Only these sampled first-diffuse
% NEXT: contributions are accumulated in the 4,096-cell Fibonacci grid. Direct sources
% NEXT: and accepted one-reflection specular paths retain their exact arrival directions.
\begin{table*}[!t]
  \caption{Configuration of the verified ten-site result.}
  \label{tab:si-configuration}
  \centering
  \begin{tabular}{p{0.24\textwidth}p{0.70\textwidth}}
    \toprule
    Item & Production value \\
    \midrule
    Sites and routes & Brussels, Ghent, Krakow, London, Madrid, Mexico City, Milan, Prague, Tokyo Hachiko, and Toulouse. The fixed routes contain 14, 10, 16, 22, 14, 11, 23, 22, 16, and 15 route points (163 total). \\
    Geometry and frequency & Original photogrammetric city mesh within a 250 m horizontal radius at 15 GHz. The circular crop area is $196{,}349.54\,\mathrm{m^2}$. \\
    Transmitter model & Roofline visible from the route. Areal density sets the expected number of transmitters. Physical three-dimensional roofline length assigns their relative probability to each segment. \\
    Exposure normalization & Per unit $\rho_A P_{\mathrm{EIRP}}$. Normalized whole-body SAR has unit $\mathrm{m^2\,kg^{-1}}$. \\
    Transport & Exact direct term, exact one-reflection specular term, and stochastic next-event estimation of one diffuse reflection at the first blocking surface. \\
    Surface model & Image-derived material map with measured finish roughness. The material probabilities are evaluated at the exact hit point. \\
    Monte Carlo & 200,000 IID primary rays per route point and replica. Seeds 7 through 70 give 64 replicas. Stored convergence results use 16, 24, 32, 48, and 64 replicas. \\
    Angular output & 4,096 passive cells collect only the first-diffuse estimate. Exact direct and one-reflection specular paths retain their arrival directions. The cells do not control launch directions. \\
    Body & Duke with 56,024 surface elements, area $1.87250\,\mathrm{m^2}$, mass 72.4 kg, and $T_0=0.500140$. The phantom faces along the walk. Body coupling uses the level-2 surface-field model. \\
    \bottomrule
  \end{tabular}
\end{table*}

## AI notes

- Main reproducibility table. Computational controls are described separately.
