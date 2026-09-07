% PREV: % claim: controlled_depth1_validation
% PREV: Validation against deterministic quadrature and Sionna RT tests the
% PREV: single-reflection diffuse estimate. Fig.~\ref{fig:controlled-validation} shows
% PREV: the comparison in an open-square scene with 27 sources, 6 receivers, 8
% PREV: triangles, and one diffuse reflection. The scene has no specular reflection,
% PREV: refraction, or diffraction. Deterministic surface quadrature uses 2,097,152
% PREV: samples. The adjoint calculation uses 50,000 primary rays for each of four
% PREV: seeds. The independent Sionna RT forward calculation uses 50,000 samples per
% PREV: source for each of three seeds. The maximum adjoint-to-quadrature difference is
% PREV: 1.43\% for the reflected component. A separate comparison of total received
% PREV: power gives a maximum adjoint-to-Sionna difference of 0.80\%. The figure shows
% PREV: the reflected component and its signed percentage difference from quadrature. This test
% PREV: covers diffuse normalization, visibility, inverse-square loss, and cosine terms
% PREV: in a one-reflection scene. It does not validate the image-derived surface
% PREV: materials, the specular component, or their combination in a city.
% NEXT: \subsection{Route exposure}
% NEXT: \label{sec:route-exposure}
\begin{figure*}[!htb]
\centering
\includegraphics[width=\textwidth]{figures/validation/validation.pdf}
\caption{Controlled validation of the single-reflection diffuse component. (a) Deterministic surface quadrature, the adjoint estimate, and the independent Sionna RT forward calculation at six receivers. (b) Signed percentage difference from quadrature. Error bars give the standard error across four adjoint seeds and three Sionna seeds.}
\label{fig:controlled-validation}
\end{figure*}
