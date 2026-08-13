% PREV: \section{Additional limitations}
% PREV: \label{sec:si-limitations}
% NEXT: The five routes are selected case studies. Their differences do not rank the
% NEXT: five cities and do not estimate population exposure. Each result is normalized
% NEXT: per unit $\rho_A P_{\mathrm{EIRP}}$, so it is not an absolute prediction for an
% NEXT: operator deployment. The study uses one 15 GHz frequency, one body phantom,
% NEXT: one fixed route-tangent body orientation, one roofline source law, and five
% NEXT: plaza routes. Additional frequencies, body models, headings, deployment laws,
% NEXT: street canyons, parks, and repeated route selections remain outside the present
% NEXT: evidence.
The transport result contains exact direct transport, exact single-reflection
all-specular transport, and the first diffuse interaction. A sampled
first-diffuse path stops at that diffuse event. The model has no diffuse-to-specular suffix, higher
specular order, or complete multipath expansion. The controlled open-square
test validates the first-diffuse normalization, visibility, inverse-square loss,
and cosine factors. The maximum adjoint-versus-Sionna difference is 0.0621 dB
for the bounced term and 0.0344 dB for total transport in that test. The same
three-way test has not been repeated for the full five-site stack with its atlas
materials and exact specular term. The test provides component validation. It
does not provide external validation of every city result. The level-2 body
coupling uses one-sided local incidence. It does not trace body self-occlusion.

## AI notes

- Uses the exact current validation comparator and states its scope.
