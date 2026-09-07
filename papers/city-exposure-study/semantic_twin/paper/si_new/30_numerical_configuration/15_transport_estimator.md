% PREV: \begin{table*}[!t]
% PREV:   \caption{Configuration of the verified ten-site result.}
% PREV:   \label{tab:si-configuration}
% PREV:   \centering
% PREV:   \begin{tabular}{p{0.24\textwidth}p{0.70\textwidth}}
% PREV:     \toprule
% PREV:     Item & Production value \\
% PREV:     \midrule
% PREV:     Sites and routes & Brussels, Ghent, Krakow, London, Madrid, Mexico City, Milan, Prague, Tokyo Hachiko, and Toulouse. The fixed routes contain 14, 10, 16, 22, 14, 11, 23, 22, 16, and 15 route points (163 total). \\
% PREV:     Geometry and frequency & Original photogrammetric city mesh within a 250 m horizontal radius at 15 GHz. The circular crop area is $196{,}349.54\,\mathrm{m^2}$. \\
% PREV:     Transmitter model & Roofline visible from the route. Areal density sets the expected number of transmitters. Physical three-dimensional roofline length assigns their relative probability to each segment. \\
% PREV:     Exposure normalization & Per unit $\rho_A P_{\mathrm{EIRP}}$. Normalized whole-body SAR has unit $\mathrm{m^2\,kg^{-1}}$. \\
% PREV:     Transport & Exact direct term, exact one-reflection specular term, and stochastic next-event estimation of one diffuse reflection at the first blocking surface. \\
% PREV:     Surface model & Image-derived material map with measured finish roughness. The material probabilities are evaluated at the exact hit point. \\
% PREV:     Monte Carlo & 200,000 IID primary rays per route point and replica. Seeds 7 through 70 give 64 replicas. Stored convergence results use 16, 24, 32, 48, and 64 replicas. \\
% PREV:     Angular output & 4,096 passive cells collect only the first-diffuse estimate. Exact direct and one-reflection specular paths retain their arrival directions. The cells do not control launch directions. \\
% PREV:     Body & Duke with 56,024 surface elements, area $1.87250\,\mathrm{m^2}$, mass 72.4 kg, and $T_0=0.500140$. The phantom faces along the walk. Body coupling uses the level-2 surface-field model. \\
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
The receiver is $1.5\,$m above the city surface. Route points are placed at
approximately $6\,$m intervals along the route, with aligned street-image
positions retained as route anchors. The visible-roofline calculation finds boundary
and crease edges that separate the first visible mesh hit from sky. Duplicate
mesh-edge contacts are combined. The resulting three-dimensional edge
lengths are the numerical weights. Each possible transmitter position is shifted vertically by
$0.5\,$m to avoid self-occlusion. Table~\ref{tab:si-source-quadrature} gives the
retained counts.

\begin{table}[!t]
  \caption{Number of route points and roofline segments.}
  \label{tab:si-source-quadrature}
  \centering
  \begin{tabular}{lrrr}
    \toprule
    Site & Route points & Roofline segments & Length (m) \\
    \midrule
    Brussels & 14 & 450 & 158.53 \\
    Ghent & 10 & 457 & 157.54 \\
    Krakow & 16 & 320 & 94.97 \\
    London & 22 & 635 & 296.67 \\
    Madrid & 14 & 207 & 79.40 \\
    Mexico City & 11 & 164 & 63.69 \\
    Milan & 23 & 502 & 437.63 \\
    Prague & 22 & 502 & 267.15 \\
    Tokyo Hachiko & 16 & 400 & 248.76 \\
    Toulouse & 15 & 283 & 72.10 \\
    \bottomrule
  \end{tabular}
\end{table}

The first-diffuse term uses a reciprocal next-event estimator. For each
primary direction $\mathbf u_n$ drawn uniformly over $4\pi$, the tracer keeps
the first blocking surface. It then draws one roofline segment from the
arc-length weights and tests the connecting segment. If the connection is
visible, its unscaled contribution is
\begin{equation}
  w_n = \frac{R_n(1-\kappa_n)}{\pi}
  \frac{[\mathbf n_n\!\cdot\!\mathbf d_n]_+}{r_n^2}.
\end{equation}
Here $R_n$ is the unpolarized Fresnel power reflectance, $\kappa_n$ is the
coherent specular share, $\mathbf d_n$ points from the surface to the sampled
transmitter position, and $r_n$ is the connecting distance. Occluded connections contribute
zero. The estimate is $(4\pi/N)\sum_n w_n$. The launch direction determines the
physical arrival direction by reciprocity. Only these sampled first-diffuse
contributions are accumulated in the 4,096-cell Fibonacci grid. Direct sources
and accepted one-reflection specular paths retain their exact arrival directions.

## AI notes

- Estimator statement follows the resident CUDA next-event kernel.
