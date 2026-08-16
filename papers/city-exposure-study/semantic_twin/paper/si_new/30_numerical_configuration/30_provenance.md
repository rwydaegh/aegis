% PREV: The deterministic order-1 search uses a conservative mirrored-receiver
% PREV: triangle-cone broad phase when the candidate set reaches 20,000. Its CUDA
% PREV: Float64 implementation leaves the host exact final test unchanged. The normal
% PREV: adaptive candidate budget is 120 million. One Tokyo route point has zero
% PREV: accepted order-1 paths, so a relative stopping rule cannot close around zero.
% PREV: That case records and fully enumerates a 320 million candidate cap. Body
% PREV: coupling uses fixed blocks of 512 directions. Candidate caps, broad-phase
% PREV: thresholds, chunks, and block sizes control computation. They do not change the
% PREV: stated physical model.
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

## AI notes

- Gives result size and integrity checks from the current inventory.
