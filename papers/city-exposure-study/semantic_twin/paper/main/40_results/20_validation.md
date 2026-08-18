% PREV: % claim: raw_component_closure
% PREV: The calculation manifests list 42 files per site, and all 210 file hashes pass
% PREV: verification. The direct, exact order-1 specular, and first-diffuse fields sum
% PREV: to the stored total with a maximum absolute residual of
% PREV: $1.735\times10^{-18}$~m$^{-2}$ across all 1,168 fields. The GPU body-coupling
% PREV: result also agrees with the double-precision CPU reference to a maximum relative
% PREV: difference of $6.64\times10^{-16}$ in the verified benchmark. These checks
% PREV: confirm the input files, addition of components, and agreement between CPU and
% PREV: GPU calculations. They do not externally validate the complete city model.
% NEXT: \begin{figure*}[!t]
% NEXT: \centering
% NEXT: \includegraphics[width=\textwidth]{figures/validation/validation.pdf}
% NEXT: \caption{Controlled validation of the first-diffuse transfer. (a) Deterministic surface quadrature, the adjoint estimate, and the independent Sionna RT forward calculation at six receivers. (b) Signed error relative to quadrature. Error bars give the standard error across four adjoint seeds and three Sionna seeds.}
% NEXT: \label{fig:controlled-validation}
% NEXT: \end{figure*}
% claim: controlled_depth1_validation
The direct and specular paths are computed from exact geometry, but the
first-diffuse estimate depends on random ray sampling. The controlled comparison
in Fig.~\ref{fig:controlled-validation} tests this stochastic component before
the city results. The open-square scene has 27 sources, 6 receivers, 8 triangles, and one diffuse
reflection. It has no specular reflection, refraction, or diffraction. Deterministic surface
quadrature uses 2,097,152 samples. The adjoint estimate uses 50,000 primary rays
for each of four seeds. An independent Sionna RT forward calculation uses
50,000 samples per source for each of three seeds. The maximum difference
between the adjoint estimate and quadrature is 0.0616~dB for the reflected term.
A separate test of total transport gives a maximum adjoint-to-Sionna difference
of 0.0344~dB. Fig.~\ref{fig:controlled-validation} plots the one-reflection
transfer and its error relative to quadrature, not the total-transport test. The
comparison checks first-diffuse normalization, visibility, inverse-square loss,
and cosine terms in this one-reflection scene. It does not cover the
image-derived material map, exact specular transport, or their combination in a
city.
