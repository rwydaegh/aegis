% PREV: The matrix form~\eqref{eq:mat-multi} is a single-hidden-layer
% NEXT: First, the network is differentiable in every input.
# Computational structure

<!-- AUTO_BEGIN: assembled -->
% NEXT: The matrix form~\eqref{eq:mat-multi} is a single-hidden-layer
\subsection{Computational structure}\label{subsec:disc-primitives}

% PREV: \subsection{Computational structure}\label{subsec:disc-primitives}
% NEXT: # Computational structure
The matrix form~\eqref{eq:mat-multi} is a single-hidden-layer
rectified-linear `network' whose weights are the path directions and
powers from a ray tracer~\cite{SionnaRT}. Three properties follow.

% PREV: # Computational structure
% NEXT: Second, the per-triangle absorbed-power map for $M \approx 10^4$
First, the network is differentiable in every input. Replacing the
hard $[\cdot]_+$ gate with the smooth \gls{GELU}
activation~\eqref{eq:gelu} preserves the chain rule. Gradients of
regulatory quantities propagate to antenna positions, antenna
orientations, beam codebooks, and reconfigurable-intelligent-surface
phases through standard backpropagation. End-to-end exposure
assessment in current practice carries a per-scenario FDTD
evaluation on the user phantom as the back-end
step~\cite{Wydaeghe2022access,Wydaeghe2026npj}. With the closed form
replacing that step, exposure-constrained network design becomes a
continuous optimization problem.

% PREV: First, the network is differentiable in every input.
% NEXT: Third, the whole-body identity~\eqref{eq:cauchy-exact} factorizes the
Second, the per-triangle absorbed-power map for $M \approx 10^4$
triangles and $N \approx 10^2$ paths is one matrix-vector multiply on
a modern GPU, evaluated in under $10$~ms. The cost is independent of
frequency. Against an FDTD reference whose cost scales as $f^4$, the
speed advantage grows by roughly $10^4$ from $6$ to $60$~GHz, exactly
the band where the Fresnel approximation is sharpest and the closed
form holds pointwise within $3\%$ of FDTD (\cref{tab:bands}). The
cosine gate is rectified shading. The visibility matrix $\mathbf{V}$
is ambient occlusion, one of the most optimized computations in
real-time rendering~\cite{AkenineMoller2018}.

% PREV: Second, the per-triangle absorbed-power map for $M \approx 10^4$
Third, the whole-body identity~\eqref{eq:cauchy-exact} factorizes the
body dependence into a single scalar $\Aab = \bar\eta\,A$. For a
given phantom and posture, $\bar\eta$ is computed once, in tens of
milliseconds, and cached. Population studies that previously
required one FDTD solve per body and per direction reduce to one
Fresnel quadrature shared across the population and one occlusion
pass per body.
<!-- AUTO_END: assembled -->





## section notes

_(AI-owned notes about this section as a whole)_
