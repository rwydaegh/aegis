% PREV: \begin{table*}[!t]
% PREV:   \caption{Configuration of the verified five-site result.}
% PREV:   \label{tab:si-configuration}
% PREV:   \centering
% PREV:   \begin{tabular}{p{0.24\textwidth}p{0.70\textwidth}}
% PREV:     \toprule
% PREV:     Item & Production value \\
% PREV:     \midrule
% PREV:     Sites and routes & Korenmarkt, Prague, Madrid, Mexico City, and Tokyo Hachiko. The fixed routes contain 10, 22, 14, 11, and 16 standpoints. \\
% PREV:     Geometry and frequency & Original photogrammetric support mesh within a 250 m horizontal radius at 15 GHz. The circular crop area is $196{,}349.54\,\mathrm{m^2}$. \\
% PREV:     Source measure & Observed route-aligned roofline. Areal density sets the expected source count. Physical three-dimensional roofline length sets the conditional source weights. \\
% PREV:     Exposure normalization & Per unit $\rho_A P_{\mathrm{EIRP}}$. Normalized whole-body SAR has unit $\mathrm{m^2\,kg^{-1}}$. \\
% PREV:     Transport & Exact direct term, exact order-1 all-specular term, and stochastic next-event estimation of the first diffuse interaction at the first blocking material vertex. \\
% PREV:     Surface model & Atlas material mode with measured finish roughness. The material posterior is evaluated at the exact hit texel. \\
% PREV:     Monte Carlo & 200,000 IID primary rays per standpoint and replica. Seeds 7 through 22 give 16 replicas. Stored convergence looks use 4, 8, 12, and 16 replicas. \\
% PREV:     Angular output & 4,096 passive cells collect only the first-diffuse estimate. Exact direct and order-1 all-specular paths remain directional atoms. The cells are not launch strata. \\
% PREV:     Body & Duke with 56,024 surface elements, area $1.87250\,\mathrm{m^2}$, mass 72.4 kg, $T_0=0.500140$, and fixed route-tangent yaw. Body coupling uses the level-2 surface-field model. \\
% PREV:     \bottomrule
% PREV:   \end{tabular}
% PREV: \end{table*}
% NEXT: For incidence cosine $c$, complex relative permittivity $\epsilon_r$, surface
% NEXT: root $q=\sqrt{\epsilon_r-(1-c^2)}$, and wavelength $\lambda$, the production
% NEXT: law is
% NEXT: \begin{align}
% NEXT:  R &= \tfrac12\left(\left|\frac{c-q}{c+q}\right|^2+
% NEXT:  \left|\frac{\epsilon_r c-q}{\epsilon_r c+q}\right|^2\right), \\
% NEXT:  \kappa &= \exp\!\left[-\left(\frac{4\pi s c}{\lambda}\right)^2\right].
% NEXT: \end{align}
% NEXT: Thus the reflected specular and diffuse shares are $R\kappa$ and
% NEXT: $R(1-\kappa)$. The surface-finish roughness $s$ excludes larger periodic relief.
% NEXT: Table~\ref{tab:si-materials} gives the evaluated 15 GHz material table. Metal
% NEXT: uses the finite-conductivity value in the same complex-permittivity convention.
% NEXT:
% NEXT: \begin{table*}[!t]
% NEXT:   \caption{Evaluated transport materials at 15 GHz. The roughness column is RMS height.}
% NEXT:   \label{tab:si-materials}
% NEXT:   \centering
% NEXT:   \begin{tabular}{lrrr@{\qquad}lrrr}
% NEXT:     \toprule
% NEXT:     Class & $\Re\epsilon_r$ & $-\Im\epsilon_r$ & $s$ ($\mu$m) & Class & $\Re\epsilon_r$ & $-\Im\epsilon_r$ & $s$ ($\mu$m) \\
% NEXT:     \midrule
% NEXT:     Asphalt concrete & 4.83 & 0.569 & 450 & Metal & 1.00 & $1.20\!\times\!10^7$ & 5 \\
% NEXT:     Brick & 3.91 & 0.044 & 30 & Plasterboard & 2.73 & 0.130 & 150 \\
% NEXT:     Ceramic & 7.07 & 0.081 & 280 & Plywood & 2.71 & 0.396 & 50 \\
% NEXT:     Chipboard & 2.58 & 0.215 & 50 & Polymer & 1.99 & 0.103 & 50 \\
% NEXT:     Concrete & 5.24 & 0.461 & 600 & Soil & 5.24 & 0.461 & 600 \\
% NEXT:     Fabric & 1.99 & 0.103 & 50 & Water & 5.24 & 0.461 & 600 \\
% NEXT:     Glass & 6.31 & 0.162 & 1 & Wood & 1.99 & 0.103 & 50 \\
% NEXT:     Marble & 7.07 & 0.081 & 280 & & & & \\
% NEXT:     \bottomrule
% NEXT:   \end{tabular}
% NEXT: \end{table*}
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

## AI notes

- Estimator statement follows the resident CUDA next-event kernel.
