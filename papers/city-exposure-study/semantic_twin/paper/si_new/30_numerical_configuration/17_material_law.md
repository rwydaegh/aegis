% PREV: The receiver is $1.5\,$m above the support surface. Route points are placed at
% PREV: approximately $6\,$m arc-length intervals, with registered panorama positions
% PREV: retained as route anchors. The route-visible skyline extraction finds boundary
% PREV: and crease edges that separate the first visible mesh hit from sky. Duplicate
% PREV: mesh-edge contacts are combined. The resulting three-dimensional edge
% PREV: lengths are the quadrature weights. Each source site is shifted vertically by
% PREV: $0.5\,$m to avoid self-occlusion. Table~\ref{tab:si-source-quadrature} gives the
% PREV: retained counts.
% PREV:
% PREV: \begin{table}[!t]
% PREV:   \caption{Route and roofline quadrature sizes.}
% PREV:   \label{tab:si-source-quadrature}
% PREV:   \centering
% PREV:   \begin{tabular}{lrrr}
% PREV:     \toprule
% PREV:     Site & Route points & Quadrature sites & Length (m) \\
% PREV:     \midrule
% PREV:     Korenmarkt & 10 & 457 & 157.54 \\
% PREV:     Prague & 22 & 502 & 267.15 \\
% PREV:     Madrid & 14 & 207 & 79.40 \\
% PREV:     Mexico City & 11 & 164 & 63.69 \\
% PREV:     Tokyo Hachiko & 16 & 400 & 248.76 \\
% PREV:     \bottomrule
% PREV:   \end{tabular}
% PREV: \end{table}
% PREV:
% PREV: The first-diffuse term uses a reciprocal next-event estimator. For each
% PREV: primary direction $\mathbf u_n$ drawn uniformly over $4\pi$, the tracer keeps
% PREV: the first blocking material vertex. It then draws one roofline site from the
% PREV: arc-length weights and tests the connecting segment. If the connection is
% PREV: visible, its unscaled contribution is
% PREV: \begin{equation}
% PREV:   w_n = \frac{R_n(1-\kappa_n)}{\pi}
% PREV:   \frac{[\mathbf n_n\!\cdot\!\mathbf d_n]_+}{r_n^2}.
% PREV: \end{equation}
% PREV: Here $R_n$ is the unpolarized Fresnel power reflectance, $\kappa_n$ is the
% PREV: coherent specular share, $\mathbf d_n$ points from the vertex to the sampled
% PREV: source, and $r_n$ is the connecting distance. Occluded connections contribute
% PREV: zero. The estimate is $(4\pi/N)\sum_n w_n$. The launch direction determines the
% PREV: physical arrival direction by reciprocity. Only these sampled first-diffuse
% PREV: contributions are accumulated in the 4,096-cell Fibonacci grid. Direct sources
% PREV: and accepted order-1 specular paths are stored as exact directional atoms.
% NEXT: The deterministic order-1 search uses a conservative mirrored-receiver
% NEXT: triangle-cone broad phase when the candidate set reaches 20,000. Its CUDA
% NEXT: Float64 implementation leaves the host exact final test unchanged. The normal
% NEXT: adaptive candidate budget is 120 million. One Tokyo standpoint has zero
% NEXT: accepted order-1 paths, so a relative stopping rule cannot close around zero.
% NEXT: That case records and fully enumerates a 320 million candidate cap. Body
% NEXT: coupling uses fixed blocks of 512 directions. Candidate caps, broad-phase
% NEXT: thresholds, chunks, and block sizes control computation. They do not change the
% NEXT: declared physical model.
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

## AI notes

- Values are sealed in each calculation manifest. ITU rows and roughness provenance remain in that manifest.
