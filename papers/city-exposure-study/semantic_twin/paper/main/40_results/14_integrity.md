% PREV: \subsection{Validation}
% PREV: \label{sec:validation}
% NEXT: % claim: controlled_depth1_validation
% NEXT: Validation against deterministic quadrature and Sionna RT tests the
% NEXT: single-reflection diffuse estimate. Fig.~\ref{fig:controlled-validation} shows
% NEXT: the comparison in an open-square scene with 27 sources, 6 receivers, 8
% NEXT: triangles, and one diffuse reflection. The scene has no specular reflection,
% NEXT: refraction, or diffraction. Deterministic surface quadrature uses 2,097,152
% NEXT: samples. The adjoint calculation uses 50,000 primary rays for each of four
% NEXT: seeds. The independent Sionna RT forward calculation uses 50,000 samples per
% NEXT: source for each of three seeds. The maximum adjoint-to-quadrature difference is
% NEXT: 1.43\% for the reflected component. A separate comparison of total received
% NEXT: power gives a maximum adjoint-to-Sionna difference of 0.80\%. The figure shows
% NEXT: the reflected component and its signed percentage difference from quadrature. This test
% NEXT: covers diffuse normalization, visibility, inverse-square loss, and cosine terms
% NEXT: in a one-reflection scene. It does not validate the image-derived surface
% NEXT: materials, the specular component, or their combination in a city.
