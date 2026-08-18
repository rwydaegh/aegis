% PREV: The transport result contains exact direct transport, exact one-reflection
% PREV: specular transport, and one diffuse reflection. A sampled first-diffuse path
% PREV: stops at that reflection. The model omits a specular reflection after the
% PREV: diffuse event, further specular reflections, and all other multipath. The controlled open-square
% PREV: test validates the first-diffuse normalization, visibility, inverse-square loss,
% PREV: and cosine factors. The maximum adjoint-versus-Sionna difference is 0.0621 dB
% PREV: for the bounced term and 0.0344 dB for total transport in that test. The same
% PREV: three-way test has not been repeated for the full five-site calculation with its
% PREV: image-derived materials and exact specular term. The test validates this component. It
% PREV: does not provide external validation of every city result. The level-2 body
% PREV: coupling uses one-sided local incidence. It does not trace body self-occlusion.
% NEXT: Image-derived materials cover only surfaces that an accepted camera can see and
% NEXT: project onto the city mesh. Unlabeled material-map cells use the geometry-based
% NEXT: material. Transient pixels do not enter the static surface. Image labels can
% NEXT: preserve within-triangle material variation, but it cannot recover geometry
% NEXT: that is absent from the photogrammetric mesh. The two-site material control
% NEXT: tests how these assignments change the final result, but it supplies no image-label
% NEXT: ground truth. Coverage over the complete city mesh also differs from coverage
% NEXT: on the surfaces reached by propagation paths. The path audit reports where the
% NEXT: recorded image-derived and geometry-based materials act in one-reflection
% NEXT: specular and first-diffuse transport. It does not test whether the image labels
% NEXT: or geometry-based material are correct. The current claims therefore apply to
% NEXT: these recorded surfaces.
The ten routes are selected case studies. Their differences do not rank the
ten cities and do not estimate population exposure. Each result is normalized
per unit $\rho_A P_{\mathrm{EIRP}}$, so it is not an absolute prediction for an
operator deployment. The study uses one 15 GHz frequency, one body phantom,
one body orientation that faces along the walk, one roofline transmitter model, and ten
plaza routes. Additional frequencies, body models, headings, deployment laws,
street canyons, parks, and repeated route selections are outside this study.

## AI notes

- States external-validity limits in plain terms.
