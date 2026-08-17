% PREV: \subsection{Validation}
% PREV: \label{sec:validation}
% NEXT: % claim: controlled_depth1_validation
% NEXT: The direct and specular paths are computed from exact geometry, but the
% NEXT: first-diffuse estimate depends on random ray sampling. The controlled comparison
% NEXT: in Fig.~\ref{fig:controlled-validation} tests this stochastic component before
% NEXT: the city results. The open-square scene has 27 sources, 6 receivers, 8 triangles, and one diffuse
% NEXT: reflection. It has no specular reflection, refraction, or diffraction. Deterministic surface
% NEXT: quadrature uses 2,097,152 samples. The adjoint estimate uses 50,000 primary rays
% NEXT: for each of four seeds. An independent Sionna RT forward calculation uses
% NEXT: 50,000 samples per source for each of three seeds. The maximum difference
% NEXT: between the adjoint estimate and quadrature is 0.0616~dB for the reflected term.
% NEXT: A separate test of total transport gives a maximum adjoint-to-Sionna difference
% NEXT: of 0.0344~dB. Fig.~\ref{fig:controlled-validation} plots the one-reflection
% NEXT: transfer and its error relative to quadrature, not the total-transport test. The
% NEXT: comparison checks first-diffuse normalization, visibility, inverse-square loss,
% NEXT: and cosine terms in this one-reflection scene. It does not cover the
% NEXT: image-derived material map, exact specular transport, or their combination in a
% NEXT: city.
% claim: raw_component_closure
The calculation manifests list 42 files per site, and all 210 file hashes pass
verification. The direct, exact order-1 specular, and first-diffuse fields sum
to the stored total with a maximum absolute residual of
$1.735\times10^{-18}$~m$^{-2}$ across all 1,168 fields. The GPU body-coupling
result also agrees with the double-precision CPU reference to a maximum relative
difference of $6.64\times10^{-16}$ in the verified benchmark. These checks
confirm the input files, addition of components, and agreement between CPU and
GPU calculations. They do not externally validate the complete city model.
