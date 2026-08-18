% PREV: \section{Results}
% PREV: \label{sec:results}
% NEXT: \subsection{Validation}
% NEXT: \label{sec:validation}
% claim: current_campaign_contract
Table~\ref{tab:routes} defines the ten fixed routes and their 163 observation
points. Every site uses 15~GHz and a photogrammetric city mesh cropped to a
250~m radius. The Duke body model has 56,024 surface elements and a mass of
72.4~kg, and faces along the direction of travel. Each point has 64 independent
replicas with seeds 7 through 70. Each replica uses 200,000 primary rays and
4,096 fixed Fibonacci output cells for the first-diffuse term. The resulting
10,432 body fields contain 2.086 billion primary rays.
Calculation time for a prepared site ranges from 5.95 to 73.77~s on one A6000
GPU. These times exclude image acquisition, alignment, depth estimation, and
material mapping because the full preparation time was not recorded.
