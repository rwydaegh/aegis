% PREV: \section{Validation and Results}
% PREV: \label{sec:results}
% NEXT: % claim: raw_component_closure
% NEXT: The calculation manifests list 42 files per site, and all 210 file hashes pass
% NEXT: verification. The direct, exact order-1 specular, and first-diffuse fields sum
% NEXT: to the stored total with a maximum absolute residual of
% NEXT: $1.735\times10^{-18}$~m$^{-2}$ across all 1,168 fields. The GPU body-coupling
% NEXT: result also agrees with the double-precision CPU reference to a maximum relative
% NEXT: difference of $6.64\times10^{-16}$ in the verified benchmark. These checks
% NEXT: confirm the input files, addition of components, and agreement between CPU and
% NEXT: GPU calculations. They do not externally validate the complete city model.
% claim: current_campaign_contract
Table~\ref{tab:routes} defines the five fixed routes and their 73 observation
points. Every site uses 15~GHz and a photogrammetric city mesh cropped to a
250~m radius. The Duke body model has 56,024 surface elements and a mass of
72.4~kg, and faces along the direction of travel. Each point has 16 independent
replicas with seeds 7 through 22. Each replica uses 200,000 primary rays and
4,096 fixed Fibonacci output cells for the first-diffuse term. The resulting 1,168 body fields contain 233.6 million primary rays.
Calculation time for a prepared site ranges from 29.79 to 69.02~s on one A6000
GPU. These times exclude image acquisition, alignment, depth estimation, and
material mapping because the full preparation time was not recorded.
