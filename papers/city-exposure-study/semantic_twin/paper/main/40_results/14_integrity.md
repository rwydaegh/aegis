% PREV: % claim: current_campaign_contract
% PREV: Table~\ref{tab:routes} defines the five fixed routes and their 73 calculation
% PREV: points. Every site uses 15~GHz, a photogrammetric city mesh cropped to a
% PREV: 250~m radius, and the Duke body model with 56,024 surface elements and a
% PREV: 72.4~kg mass. The phantom faces along the walk. Each point has 16 independent
% PREV: replicas with seeds 7 through 22, and each replica uses 200,000 IID primary rays
% PREV: and 4,096 fixed output directions for the first-diffuse term. The resulting
% PREV: 1,168 fields contain 233.6 million primary rays. Calculation time for a prepared
% PREV: site ranges from 29.79 to 69.02~s on one A6000 GPU. These times exclude image
% PREV: acquisition, image-to-mesh alignment, depth estimation, and material mapping
% PREV: because the full preparation time was not recorded.
% NEXT: % claim: controlled_depth1_validation
% NEXT: The controlled comparison in Fig.~\ref{fig:controlled-validation} tests the
% NEXT: first-diffuse estimator before the city results. The open-square scene has 27
% NEXT: sources, six receivers, eight triangles, and one diffuse reflection. It has no
% NEXT: specular reflection, refraction, or diffraction. Deterministic surface
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
