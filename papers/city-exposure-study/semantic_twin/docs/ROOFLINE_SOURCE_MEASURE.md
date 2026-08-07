# Roofline source measure

## Purpose

The source model separates two questions that should not be conflated:

1. How many effective emitters belong to a site.
2. How those emitters are distributed along the represented roofline.

With fixed areal site density \(\rho_A\), the total source count is set by the
crop area \(A_{\mathrm{crop}}\):

\[
    N_{\mathrm{site}} = \rho_A A_{\mathrm{crop}}.
\]

This fixes the total source scaling. It does not, by itself, determine the
conditional placement of source mass along roof edges. That placement is the
source measure described here.

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

## Verified numerical indication

The sealed Korenmarkt result has

\[
    L_3 = 182.954\ \mathrm{m}.
\]

A non-sealed CPU indication for the same type of source construction found

\[
    L_3 = 179.335\ \mathrm{m},
    \qquad
    L_{xy} = 154.019\ \mathrm{m},
    \qquad
    L_{xy}/L_3 = 0.859.
\]

The indicated mean edge slope was \(19.9^\circ\), with 31.0% of 3D edge
length above \(30^\circ\). Reweighting the same edge set by the projected
measure changed the source-weight distribution by total variation distance
0.104 in that indication. These values are a sensitivity signal, not a
replacement for a sealed paired run.

The sealed Prague result has

\[
    L_3 = 654.605\ \mathrm{m}.
\]

An exact Prague projection is not available because the endpoint geometry was
not retained in the sealed artifact. It must not be reconstructed by guessing
from the scalar length.

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
