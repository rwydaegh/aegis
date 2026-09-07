% PREV: Third, the whole-body identity~\eqref{eq:cauchy-exact} factorizes the
% PREV: body dependence into a single scalar $\Aab = \bar\eta\,A$. For a
% PREV: given phantom and posture, $\bar\eta$ is computed once, in tens of
% PREV: milliseconds, and cached. Population studies that previously
% PREV: required one FDTD solve per body and per direction reduce to one
% PREV: Fresnel quadrature shared across the population and one occlusion
% PREV: pass per body.
We highlight three potential applications. First, dosimetry can be
computed in real time, because each evaluation takes about $10$~ms,
well below the timescale on which the body pose and environment
change, given an accurate digital twin of both. Second, exposure
metrics can be optimized under design constraints, because the method
is differentiable end to end. Third, large-scale dosimetric assessment
across diverse populations is possible and useful at the city scale,
e.g., for epidemiological studies such as the GOLIAT
project~\cite{Goliat}.

## reviews (paragraph)

_(empty — run /review to populate)_
