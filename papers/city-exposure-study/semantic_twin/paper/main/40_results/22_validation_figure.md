% PREV: % claim: controlled_depth1_validation
% PREV: The direct and specular paths are computed from exact geometry, but the
% PREV: first-diffuse estimate depends on random ray sampling. The controlled comparison
% PREV: in Fig.~\ref{fig:controlled-validation} tests this stochastic component before
% PREV: the city results. The open-square scene has 27 sources, 6 receivers, 8 triangles, and one diffuse
% PREV: reflection. It has no specular reflection, refraction, or diffraction. Deterministic surface
% PREV: quadrature uses 2,097,152 samples. The adjoint estimate uses 50,000 primary rays
% PREV: for each of four seeds. An independent Sionna RT forward calculation uses
% PREV: 50,000 samples per source for each of three seeds. The maximum difference
% PREV: between the adjoint estimate and quadrature is 0.0616~dB for the reflected term.
% PREV: A separate test of total transport gives a maximum adjoint-to-Sionna difference
% PREV: of 0.0344~dB. Fig.~\ref{fig:controlled-validation} plots the one-reflection
% PREV: transfer and its error relative to quadrature, not the total-transport test. The
% PREV: comparison checks first-diffuse normalization, visibility, inverse-square loss,
% PREV: and cosine terms in this one-reflection scene. It does not cover the
% PREV: image-derived material map, exact specular transport, or their combination in a
% PREV: city.
% NEXT: \subsection{Route Exposure}
% NEXT: \label{sec:route-exposure}
\begin{figure*}[!t]
\centering
\includegraphics[width=\textwidth]{figures/validation/validation.pdf}
\caption{Controlled validation of the first-diffuse transfer. (a) Deterministic surface quadrature, the adjoint estimate, and the independent Sionna RT forward calculation at six receivers. (b) Signed error relative to quadrature. Error bars give the standard error across four adjoint seeds and three Sionna seeds.}
\label{fig:controlled-validation}
\end{figure*}
