# Figure polish pass for the two-column journal format

Presentation only. No figure shows anything different from what it showed before,
and no number behind any panel was touched. Every figure was regenerated from its
generator, rendered to PNG at the width it is actually placed at in `paper/paper.tex`
(7.16 in for a `figure*`, 3.5 in for a `figure`), and read at that size.

Conventions settled during the pass, applied to every figure that needed them:

* Units in square brackets, `[dB]`, `[m]`, `[deg]`, `[%]`. Two of the twelve used
  parentheses and two used a trailing comma.
* The exposure ratio is `$\chi$`, the name the body uses. Three axis labels called
  it susceptibility, a word the paper never uses, and one wrote it `$\chi_S$`.
* Lower case `a`, `b`, `c` panel labels at the left of the panel title.
* No figure title and no paragraph of provenance under the axes. Those repeated
  the LaTeX caption and were set between 5.4 and 6.4 pt, which no printed page
  carries. Every number they held is now printed to the terminal by the generator
  that used to draw them.
* Where a colour carries a distinction, a marker or a dash pattern carries it too.

## Per figure

**11 eleven cities.** Reset. The sheet was on a near-black background with the
title at 9 pt, the standfirst at 4.6 pt and the tile labels at 4.3 to 5.1 pt.
Text sizes are now derived from the printed resolution of the sheet, 269 ppi at
`\textwidth`, so the tile names print at 8.5 pt and the numbers under them at
7.2 pt. Labels wider than their tile shrink to fit, which fixes "Plaza de la
Constitucion, Mexico City" running into the Milan tile and the Istanbul rejection
note running off the right edge. The background is now white, because every other
figure in the paper is on white and a full page of solid black is a poor
neighbour to them. The headline and three of the four standfirst lines were
dropped, since the caption says the same thing. The two sentences that survive
are the key to the numbers under each tile.

**14 exposure CDF Korenmarkt.** Not currently included by the body. Notation fixed
to the exposure ratio, panel labels added, the three illumination models given
markers, peak and mean absorbed density separated by dash pattern as well as by
tint, figure title and the 6.2 pt footer paragraph removed.

**15 crop convergence.** The worst case in the set. It was drawn 6.95 in wide and
placed at `\columnwidth`, so everything printed at half the size it was set at,
and it carried an eleven line footer paragraph at 6.2 pt. Redrawn at 3.5 in.
Legend moved out from under the curves to two columns below the axes. Series
labels shortened. Each series now has a marker and a dash pattern, since red
against purple is the pair a red-green colourblind reader loses first and none of
the four hues separates in greyscale. The two vertical rules are labelled without
crossing any curve. Converged radii are printed to the terminal rather than drawn.

**16 eleven cities exposure.** Second worst. It was drawn 12.2 in wide and shrunk
to 7.16 on the page, an 0.59 scale that put the axis labels near 6 pt and the
eleven-entry legend near 3.7 pt, and the legend sat on top of the curves in the
left panel. Redrawn at 7.16 in with the legend in four columns under the axes.
The turbo colour ramp was replaced with plasma: eleven curves sorted by their own
median is a sequential encoding, and plasma keeps its lightness order in greyscale
and through a red-green filter where turbo does not. The legend is in the same
order as the curves. `$\chi_S$` corrected to `$\chi$`, standpoint counts dropped
from the eleven legend entries since the caption states them once, panel labels
added, absorbed density reference moved from the axis label into the panel title.

**17 evidence ladder.** Not currently included by the body. Same treatment as 14:
notation, panel labels, markers on the three models, title and footer paragraph
removed.

**18 elevation geometry, 19 deployment box, 20 adjoint idea, 21 one ray.** These
four were each saved with a tight bounding box, which cropped them to four
different widths between 4.53 and 5.97 in, and LaTeX then stretched each back to
`\textwidth` by a different factor between 1.20 and 1.58. Four figures set at the
same point sizes printed at four different sizes, and 21 printed its annotations
larger than the body text. The shared `save` now fits the drawing to the placed
width before writing, so a point size in these generators is the point size that
prints, and annotation type was raised to 8.5 pt across all four. Panel labels
added to 19 and 20. Units moved to brackets in 18 and 19. In 19 the corner
annotation was moved clear of the constant-elevation labels. In 20 the blocked
rays were lightened so the escaped-against-blocked split survives greyscale, and
the sentence describing it now says dark against pale rather than blue against
grey. In 21 the drawing window was trimmed to what is actually drawn, which was
leaving about a third of the panel empty.

**22 evidence reach.** Already close. Annotation type raised from 6.2 to 6.9 pt up
to 7.0 to 7.4 pt. The three interaction depths in panel b were three tints of one
blue, all with the same marker, so each depth now has its own marker shape. The
6.0 pt provenance line under the axes was removed.

**24 diffraction bound.** Already close. Units to brackets on five axes and the
colorbar, including `azimuth, degrees` against `elevation, deg` in the same panel.
The four in-panel annotations were set at 5.9 to 6.8 pt and are now 6.9 to 7.2 pt.
Colorbar label and ticks raised to 7.5 pt.

**25 bounce budget.** Base type raised from 7.0 to 7.6 pt and the in-panel
annotations from 5.4 to 6.4 pt up to 6.6 to 6.9 pt, with the figure aspect opened
from 0.60 to 0.64 to absorb it. Three collisions that the larger type introduced
were resolved: the depth labels in panel a now sit on a white plate, panel c has
room under the isotropic row for its note, and the worst-standpoint line in panels
d, e and f moved to the left above the half decibel rule, where it does not cross
the street model's worst-standpoint curve. The 5.4 pt stamp under the axes was
removed. `shift against 8 interactions, dB` to brackets.

## Content I did not touch, and one thing worth a look

Nothing in the twelve looked wrong or misleading, so nothing was changed on those
grounds. Two things a reader may want to know about, neither of which is a
presentation matter:

* Figure 16 panels a and c clip the x axis to the pooled 1st and 99.5th
  percentiles. The generator explains why, a couple of deep-shadow standpoints
  otherwise squash all eleven curves against the right edge, but the consequence
  is that the curves start above zero at the left edge and the extreme tail is off
  the page. Figure 14 panel a clips the same way at the 2nd percentile. Worth a
  caption sentence if a reviewer asks where the missing fraction went.
* Figure 25 panel a plots the share of launched power arriving at each depth, and
  those bars are not a partition: a ray that reached depth three was counted at
  depths one and two as well. The generator docstring says so and the axis label
  is accurate, but the panel invites reading the bars as a decomposition.

## Rebuild

`pdflatex` twice, clean, 19 pages. The page count did not move.
