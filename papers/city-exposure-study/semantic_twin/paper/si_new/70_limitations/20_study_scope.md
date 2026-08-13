% PREV: The transport result contains exact direct transport, exact single-reflection
% PREV: all-specular transport, and the first diffuse interaction. A sampled
% PREV: first-diffuse path stops at that diffuse event. The model has no diffuse-to-specular suffix, higher
% PREV: specular order, or complete multipath expansion. The controlled open-square
% PREV: test validates the first-diffuse normalization, visibility, inverse-square loss,
% PREV: and cosine factors. The maximum adjoint-versus-Sionna difference is 0.0621 dB
% PREV: for the bounced term and 0.0344 dB for total transport in that test. The same
% PREV: three-way test has not been repeated for the full five-site stack with its atlas
% PREV: materials and exact specular term. The test provides component validation. It
% PREV: does not provide external validation of every city result. The level-2 body
% PREV: coupling uses one-sided local incidence. It does not trace body self-occlusion.
% NEXT: Panorama evidence covers only surfaces that an admitted camera can see and cast
% NEXT: onto the support mesh. Unsupported atlas cells use the geometric material.
% NEXT: Transient pixels are withheld from the static surface. Image evidence can
% NEXT: preserve within-triangle material variation, but it cannot recover geometry
% NEXT: that is absent from the photogrammetric mesh. The two-site material control
% NEXT: tests downstream sensitivity and supplies no semantic ground truth. Coverage
% NEXT: on all support-mesh area also differs from coverage on the subset reached by
% NEXT: propagation paths. A ray-reached evidence-coverage report is therefore a useful
% NEXT: future diagnostic. The current claims are conditional on the recorded atlas
% NEXT: and fallback rule. The diagnostic would show where that rule acts in the
% NEXT: reported transport.
The five routes are selected case studies. Their differences do not rank the
five cities and do not estimate population exposure. Each result is normalized
per unit $\rho_A P_{\mathrm{EIRP}}$, so it is not an absolute prediction for an
operator deployment. The study uses one 15 GHz frequency, one body phantom,
one fixed route-tangent body orientation, one roofline source law, and five
plaza routes. Additional frequencies, body models, headings, deployment laws,
street canyons, parks, and repeated route selections remain outside the present
evidence.

## AI notes

- States external-validity limits in plain terms.
