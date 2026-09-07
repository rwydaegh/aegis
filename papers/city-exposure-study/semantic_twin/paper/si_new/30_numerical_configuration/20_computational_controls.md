% PREV: For incidence cosine $c$, complex relative permittivity $\epsilon_r$, surface
% PREV: root $q=\sqrt{\epsilon_r-(1-c^2)}$, and wavelength $\lambda$, the production
% PREV: law is
% PREV: \begin{align}
% PREV:  R &= \tfrac12\left(\left|\frac{c-q}{c+q}\right|^2+
% PREV:  \left|\frac{\epsilon_r c-q}{\epsilon_r c+q}\right|^2\right), \\
% PREV:  \kappa &= \exp\!\left[-\left(\frac{4\pi s c}{\lambda}\right)^2\right].
% PREV: \end{align}
% PREV: Thus the reflected specular and diffuse shares are $R\kappa$ and
% PREV: $R(1-\kappa)$. The surface-finish roughness $s$ excludes larger periodic relief.
% PREV: Table~\ref{tab:si-materials} gives the evaluated 15 GHz material table. Metal
% PREV: uses the finite-conductivity value in the same complex-permittivity convention.
% PREV:
% PREV: \begin{table*}[!t]
% PREV:   \caption{Evaluated transport materials at 15 GHz. The roughness column is RMS height.}
% PREV:   \label{tab:si-materials}
% PREV:   \centering
% PREV:   \begin{tabular}{lrrr@{\qquad}lrrr}
% PREV:     \toprule
% PREV:     Class & $\Re\epsilon_r$ & $-\Im\epsilon_r$ & $s$ ($\mu$m) & Class & $\Re\epsilon_r$ & $-\Im\epsilon_r$ & $s$ ($\mu$m) \\
% PREV:     \midrule
% PREV:     Asphalt concrete & 4.83 & 0.569 & 450 & Metal & 1.00 & $1.20\!\times\!10^7$ & 5 \\
% PREV:     Brick & 3.91 & 0.044 & 30 & Plasterboard & 2.73 & 0.130 & 150 \\
% PREV:     Ceramic & 7.07 & 0.081 & 280 & Plywood & 2.71 & 0.396 & 50 \\
% PREV:     Chipboard & 2.58 & 0.215 & 50 & Polymer & 1.99 & 0.103 & 50 \\
% PREV:     Concrete & 5.24 & 0.461 & 600 & Soil & 5.24 & 0.461 & 600 \\
% PREV:     Fabric & 1.99 & 0.103 & 50 & Water & 5.24 & 0.461 & 600 \\
% PREV:     Glass & 6.31 & 0.162 & 1 & Wood & 1.99 & 0.103 & 50 \\
% PREV:     Marble & 7.07 & 0.081 & 280 & & & & \\
% PREV:     \bottomrule
% PREV:   \end{tabular}
% PREV: \end{table*}
% NEXT: The result contains 163 route points, 10,432 point-replica fields, 640
% NEXT: site-replica runs, and 2.086 billion stochastic primary rays. Every campaign
% NEXT: manifest lists 42 files. All 420 recorded file hashes pass. The aggregate JSON,
% NEXT: CSV, PDF, and PNG also match their artifact manifest. Across the 10,432 fields,
% NEXT: the maximum raw residual between the saved total and the sum of direct,
% NEXT: all-specular, and first-diffuse components is
% NEXT: $1.214\times10^{-17}\,\mathrm{m^{-2}}$. The CUDA body result agrees with the
% NEXT: NumPy reference to a maximum relative error of $6.64\times10^{-16}$ in the
% NEXT: verified benchmark. The verified artifacts are stored under
% NEXT: the roofline campaign output package named
% NEXT: \texttt{ten\_city\_route\_\allowbreak{}production64\_v1}.
% NEXT: The Duke STL has SHA-256
% NEXT: \texttt{781e65ef3882f134\allowbreak{}7669e0ddca5dafa82\allowbreak{}cd6368dddd6b9e80\allowbreak{}1dc49613822fe3b}.
% NEXT: The verified body-area array has SHA-256
% NEXT: \texttt{5dd410b9512fdb02\allowbreak{}74dd1ac1fb8f7b70\allowbreak{}87564abfed998d57\allowbreak{}a25065e87ffebd6a}.
% NEXT: Each calculation manifest also verifies the city mesh, material map, roofline
% NEXT: segments, source weights, route arrays, material tables, and executable configuration.
The deterministic order-1 search uses a conservative mirrored-receiver
triangle-cone broad phase when the candidate set reaches 20,000. Its CUDA
Float64 implementation leaves the host exact final test unchanged. The normal
adaptive candidate budget is 120 million. One Tokyo route point has zero
accepted order-1 paths, so a relative stopping rule cannot close around zero.
That case records and fully enumerates a 320 million candidate cap. Body
coupling uses fixed blocks of 512 directions. Candidate caps, broad-phase
thresholds, chunks, and block sizes control computation. They do not change the
stated physical model.

## AI notes

- Separates model settings from implementation guards.
