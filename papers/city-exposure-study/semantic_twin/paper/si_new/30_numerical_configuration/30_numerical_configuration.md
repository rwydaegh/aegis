<!-- AUTO_BEGIN: assembled -->
\section{Numerical settings and file verification}
\label{sec:si-configuration}

\begin{table*}[!t]
  \caption{Configuration of the verified five-site result.}
  \label{tab:si-configuration}
  \centering
  \begin{tabular}{p{0.24\textwidth}p{0.70\textwidth}}
    \toprule
    Item & Production value \\
    \midrule
    Sites and routes & Korenmarkt, Prague, Madrid, Mexico City, and Tokyo Hachiko. The fixed routes contain 10, 22, 14, 11, and 16 route points. \\
    Geometry and frequency & Original photogrammetric city mesh within a 250 m horizontal radius at 15 GHz. The circular crop area is $196{,}349.54\,\mathrm{m^2}$. \\
    Transmitter model & Roofline visible from the route. Areal density sets the expected number of transmitters. Physical three-dimensional roofline length assigns their relative probability to each segment. \\
    Exposure normalization & Per unit $\rho_A P_{\mathrm{EIRP}}$. Normalized whole-body SAR has unit $\mathrm{m^2\,kg^{-1}}$. \\
    Transport & Exact direct term, exact one-reflection specular term, and stochastic next-event estimation of one diffuse reflection at the first blocking surface. \\
    Surface model & Image-derived material map with measured finish roughness. The material probabilities are evaluated at the exact hit point. \\
    Monte Carlo & 200,000 IID primary rays per route point and replica. Seeds 7 through 22 give 16 replicas. Stored convergence results use 4, 8, 12, and 16 replicas. \\
    Angular output & 4,096 passive cells collect only the first-diffuse estimate. Exact direct and one-reflection specular paths retain their arrival directions. The cells do not control launch directions. \\
    Body & Duke with 56,024 surface elements, area $1.87250\,\mathrm{m^2}$, mass 72.4 kg, and $T_0=0.500140$. The phantom faces along the walk. Body coupling uses the level-2 surface-field model. \\
    \bottomrule
  \end{tabular}
\end{table*}

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
adaptive candidate budget is 120 million. One Tokyo route point has zero
accepted order-1 paths, so a relative stopping rule cannot close around zero.
That case records and fully enumerates a 320 million candidate cap. Body
coupling uses fixed blocks of 512 directions. Candidate caps, broad-phase
thresholds, chunks, and block sizes control computation. They do not change the
stated physical model.

The result contains 73 route points, 1,168 point-replica fields, 80
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
The verified body-area array has SHA-256
\texttt{5dd410b9512fdb02\allowbreak{}74dd1ac1fb8f7b70\allowbreak{}87564abfed998d57\allowbreak{}a25065e87ffebd6a}.
Each calculation manifest also verifies the city mesh, material map, roofline
segments, source weights, route arrays, material tables, and executable configuration.
<!-- AUTO_END: assembled -->




























## Aggregation notes (AI-owned)
