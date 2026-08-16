<!-- AUTO_BEGIN: assembled -->
\balance
\section{Additional limitations}
\label{sec:si-limitations}

The transport result contains exact direct transport, exact one-reflection
specular transport, and one diffuse reflection. A sampled first-diffuse path
stops at that reflection. The model omits a specular reflection after the
diffuse event, further specular reflections, and all other multipath. The controlled open-square
test validates the first-diffuse normalization, visibility, inverse-square loss,
and cosine factors. The maximum adjoint-versus-Sionna difference is 0.0621 dB
for the bounced term and 0.0344 dB for total transport in that test. The same
three-way test has not been repeated for the full five-site calculation with its
image-derived materials and exact specular term. The test validates this component. It
does not provide external validation of every city result. The level-2 body
coupling uses one-sided local incidence. It does not trace body self-occlusion.

The five routes are selected case studies. Their differences do not rank the
five cities and do not estimate population exposure. Each result is normalized
per unit $\rho_A P_{\mathrm{EIRP}}$, so it is not an absolute prediction for an
operator deployment. The study uses one 15 GHz frequency, one body phantom,
one body orientation that faces along the walk, one roofline transmitter model, and five
plaza routes. Additional frequencies, body models, headings, deployment laws,
street canyons, parks, and repeated route selections are outside this study.

Image-derived materials cover only surfaces that an accepted camera can see and
project onto the city mesh. Unlabeled material-map cells use the geometry-based
material. Transient pixels do not enter the static surface. Image labels can
preserve within-triangle material variation, but it cannot recover geometry
that is absent from the photogrammetric mesh. The two-site material control
tests how these assignments change the final result, but it supplies no image-label
ground truth. Coverage over the complete city mesh also differs from coverage
on the surfaces reached by propagation paths. The path audit reports where the
recorded image-derived and geometry-based materials act in one-reflection
specular and first-diffuse transport. It does not test whether the image labels
or geometry-based material are correct. The current claims therefore apply to
these recorded surfaces.
<!-- AUTO_END: assembled -->


























## Aggregation notes (AI-owned)
