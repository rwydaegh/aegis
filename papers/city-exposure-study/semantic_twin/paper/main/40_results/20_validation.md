% NEXT: \begin{figure*}[!htb]
% NEXT: \centering
% NEXT: \includegraphics[width=\textwidth]{figures/validation/validation.pdf}
% NEXT: \caption{Controlled validation of the single-reflection diffuse component. (a) Deterministic surface quadrature, the adjoint estimate, and the independent Sionna RT forward calculation at six receivers. (b) Signed percentage difference from quadrature. Error bars give the standard error across four adjoint seeds and three Sionna seeds.}
% NEXT: \label{fig:controlled-validation}
% NEXT: \end{figure*}
% claim: controlled_depth1_validation
Before applying the model to the ten city routes, validation against
deterministic quadrature and Sionna RT tests the
single-reflection diffuse estimate. Fig.~\ref{fig:controlled-validation} shows
the comparison in an open-square scene with 27 sources, 6 receivers, 8
triangles, and one diffuse reflection. The scene has no specular reflection,
refraction, or diffraction. Deterministic surface quadrature uses 2,097,152
samples. The adjoint calculation uses 50,000 primary rays for each of four
seeds. The independent Sionna RT forward calculation uses 50,000 samples per
source for each of three seeds. The maximum adjoint-to-quadrature difference is
1.43\% for the reflected component. A separate comparison of total received
power gives a maximum adjoint-to-Sionna difference of 0.80\%. Fig.~\ref{fig:controlled-validation}
also shows the reflected component and its signed percentage difference from quadrature. This test
covers diffuse normalization, visibility, inverse-square loss, and cosine terms
in a one-reflection scene.
