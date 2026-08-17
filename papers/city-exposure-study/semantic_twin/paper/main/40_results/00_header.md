% NEXT: % claim: current_campaign_contract
% NEXT: Table~\ref{tab:routes} defines the five fixed routes and their 73 observation
% NEXT: points. Every site uses 15~GHz and a photogrammetric city mesh cropped to a
% NEXT: 250~m radius. The Duke body model has 56,024 surface elements and a mass of
% NEXT: 72.4~kg, and faces along the direction of travel. Each point has 16 independent
% NEXT: replicas with seeds 7 through 22. Each replica uses 200,000 primary rays and
% NEXT: 4,096 fixed Fibonacci output cells for the first-diffuse term. The resulting 1,168 body fields contain 233.6 million primary rays.
% NEXT: Calculation time for a prepared site ranges from 29.79 to 69.02~s on one A6000
% NEXT: GPU. These times exclude image acquisition, alignment, depth estimation, and
% NEXT: material mapping because the full preparation time was not recorded.
\section{Results}
\label{sec:results}
