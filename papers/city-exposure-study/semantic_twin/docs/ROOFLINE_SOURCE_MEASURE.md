# Roofline source measure

> **Current-contract notice.** Production uses the physical three-dimensional
> edge-length measure for conditional source weights. Horizontal-projected
> roofline length is an explicit opt-in sensitivity, not a replacement. Current
> source artifacts retain exact endpoints and audit sidecars. The sealed
> Prague endpoint limitation described below is historical. See
> [CURRENT_PRODUCTION_CONTRACT.md](CURRENT_PRODUCTION_CONTRACT.md).

## Purpose

The source model separates two questions that should not be conflated:

1. How many effective emitters belong to a site.
2. How those emitters are distributed along the represented roofline.

With fixed areal site density \(\rho_A\), the expected active-source count is
set by the crop area \(A_{\mathrm{crop}}\):

\[
    N_{\mathrm{site}} = \rho_A A_{\mathrm{crop}}.
\]

This fixes the physical source scaling. It is not the number of numerical
source quadrature points. It does not, by itself, determine the conditional
placement of source mass along roof edges. That placement is the source measure
described here.

## Measures currently under consideration

The production baseline uses the exact three-dimensional length of each
retained roofline edge. For an edge from \(\mathbf p_i\) to \(\mathbf p_{i+1}\),
the baseline element is

\[
    ds_3 = \lVert d\mathbf p \rVert_2,
    \qquad
    L_3 = \sum_i \lVert\mathbf p_{i+1}-\mathbf p_i\rVert_2.
\]

An alternative for a plan-view urban deployment convention is horizontal
projected length:

\[
    ds_{xy} = \lVert d\mathbf p_{xy} \rVert_2,
    \qquad
    L_{xy} = \sum_i
       \lVert(\mathbf p_{i+1}-\mathbf p_i)_{xy}\rVert_2.
\]

The second quantity is more precise than the informal phrase “rooftop
length.” In a paper it should be called *plan-view roofline length* or
*horizontal projected roofline length*. It is the natural choice if the
deployment convention is density per map-plane opportunity. The three-
dimensional measure remains defensible if the intended interpretation is
physical placement along parapets, ridges, and other sloped structures.

For either measure \(m\in\{3,xy\}\), normalized source probabilities are

\[
    w_i^{(m)} = \frac{\ell_i^{(m)}}{L_m},
    \qquad
    \sum_i w_i^{(m)}=1.
\]

Thus changing the measure does not change \(N_{\mathrm{site}}\) or the total
site-level scaling. It changes the conditional distribution of source
locations. Consequently it can change direct, next-event-estimation,
specular, and body-coupled contributions even when the nominal total source
power is unchanged.

## Verified paired sensitivity

The exact Korenmarkt source artifact contains 506 segments with

\[
    L_3 = 182.953912\ \mathrm{m},
    \qquad
    L_{xy} = 160.509814\ \mathrm{m},
    \qquad
    L_{xy}/L_3 = 0.877324.
\]

A paired seed-7 A6000 run used identical 13 receiver positions, source-curve
hash, transport configuration, and point seeds. Only the normalized source
weights differed. Relative to the physical 3D baseline, horizontal-projected
weighting changed the mean pointwise raw transfer by:

- direct: -0.89%,
- one-reflection specular: -3.13%,
- diffuse: -1.17%,
- total: -1.41%.

For the total body field, mean pointwise peak \(S_{\mathrm{ab}}\) changed by
-1.23%, while mean \(S_{\mathrm{ab}}\), absorbed power, and whole-body SAR each
changed by -0.56%. This one-seed common-random-number result supports retaining
physical 3D length as the reproducibility baseline while treating projected
length as a modest, explicit sensitivity. It is not a convergence claim.

The sealed Prague result has

\[
    L_3 = 654.605\ \mathrm{m}.
\]

The historical sealed artifact did not retain endpoint geometry, so an exact
projection could not be reconstructed from that scalar length. Current source
artifacts retain exact endpoints and make the paired projection sensitivity
auditable. Its production decision still requires the paired run below.

## Recommended decision procedure

Preserve the 3D measure as the current reproducibility baseline. Before
adopting or rejecting the projected convention, make the source artifact
self-auditing by retaining, for every edge:

- both endpoints in the transport coordinate frame,
- \(\ell_i^{(3)}\) and \(\ell_i^{(xy)}\),
- the selected measure name,
- the total \(L_3\) and \(L_{xy}\),
- the normalized-weight hash and source-construction hash.

Then run a paired Korenmarkt and Prague sensitivity campaign with identical
geometry, seeds, route points, source identity, and transport settings. Use
common random numbers and compare total transfer, direct, NEE, specular,
body-absorbed power, and whole-body SAR. Report both the absolute change and
the uncertainty of the paired difference. The measure decision should be
made from that experiment and from the declared physical interpretation, not
from the scalar length ratio alone.

## Paper wording

The methods section can state that the study fixes total source density from
crop area and uses a normalized roofline measure for conditional placement.
The main paper need only name the selected convention and give its physical
interpretation. The endpoint records, alternative measure, hashes, and paired
sensitivity results belong in the supplementary material. This keeps the
parameterization reproducible without presenting an implementation detail as
an additional free physical parameter.
