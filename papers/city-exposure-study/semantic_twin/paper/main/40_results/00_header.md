% NEXT: % claim: current_campaign_contract
% NEXT: Table~\ref{tab:routes} defines the five fixed routes and their 73 calculation
% NEXT: points. Every site uses 15~GHz, a photogrammetric city mesh cropped to a
% NEXT: 250~m radius, and the Duke body model with 56,024 surface elements and a
% NEXT: 72.4~kg mass. The phantom faces along the walk. Each point has 16 independent
% NEXT: replicas with seeds 7 through 22, and each replica uses 200,000 IID primary rays
% NEXT: and 4,096 fixed output directions for the first-diffuse term. The resulting
% NEXT: 1,168 fields contain 233.6 million primary rays. Calculation time for a prepared
% NEXT: site ranges from 29.79 to 69.02~s on one A6000 GPU. These times exclude image
% NEXT: acquisition, image-to-mesh alignment, depth estimation, and material mapping
% NEXT: because the full preparation time was not recorded.
\section{Validation and Results}
\label{sec:results}
