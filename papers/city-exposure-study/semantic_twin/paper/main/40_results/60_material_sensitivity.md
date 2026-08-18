% PREV: \subsection{Material Sensitivity}
% PREV: \label{sec:material-sensitivity}
% claim: paired_material_evidence_control
A paired control for Madrid and Mexico City replaces all image-mapped materials
with the default geometry-based materials while keeping the mesh, route,
roofline model, body, seeds, sampling budget, and transport steps identical.
Each reported change is
$10\log_{10}(x_{\mathrm{image}}/x_{\mathrm{geometry}})$. At Madrid the
image-to-geometry changes in normalized whole-body SAR are $+0.233$, $+0.249$,
and $+0.269$~dB for $q_{10}$, $q_{50}$, and $q_{90}$. At Mexico City the
corresponding changes are $+24.84$, $-0.158$, and $+0.104$~dB. The large
$q_{10}$ change comes from the three fully shadowed points, where both totals
are near zero and first-diffuse transport is the only nonzero contribution. The
direct term is identical in every pair. At Madrid, the image-derived map changes
the route-median specular component by $+1.89$~dB and the first-diffuse
component by $-12.43$~dB, but the total median changes by only $+0.249$~dB.
This control tests the complete material map, including its parameters and the
treatment of woody vegetation as nonblocking. It does not measure material
accuracy or isolate reflectance alone. The supplementary material gives
pointwise and component-level comparisons.
