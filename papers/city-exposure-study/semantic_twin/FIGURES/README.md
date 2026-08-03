# Figures

Collected here so they are in one place rather than scattered under `outputs/`.
Each is regenerable, and the script that made it is named in its own footer.

The two assembled scenes are `outputs/showcase_korenmarkt/korenmarkt.blend` and
`outputs/showcase_milan_duomo/milan_duomo.blend`. Both open on their establishing
shot and carry one named camera per figure below, so switching camera in Blender
reproduces the figure rather than approximating it.

## 01, 02: the twin at two sites

Korenmarkt in Ghent and Piazza del Duomo in Milan, assembled from the shipped
artifacts: Photorealistic 3D Tiles leaves placed in double precision, the
registered panorama camera with its pose covariance, and the pedestrians the
segmenter refused to paint onto the walls. Milan is 476,410 triangles from 342
leaf tiles at a 0.745 degree pose residual.

## 03: what one panorama actually sees

The least flattering figure and the most useful one. Over the full sphere a
single registered panorama is a first hit on 4.3 percent of support triangles and
6.9 percent by area. 72.8 percent of faces take their material from tile texture
and 23.9 percent carry no image evidence at all.

The 3.3 and 4.4 percent pair that appeared in earlier drafts of this caption was
the same capture scored inside the four 90 degree rectilinear crops the fishnet
cuts against, which is a different denominator and not comparable with the fused
number. **Neither of those two figures reproduces from anything shipped.** The
four `outputs/korenmarkt_fishnet_vistas/*_fishnet.npz` files touch 3,558 distinct
source triangles, 2.3 percent of the mesh and 3.2 percent by area. Quote the full
sphere pair above against the fused one and leave the crop band out of it.

Fusing twelve panoramas raises directly observed surface to 15.9 percent of
triangles and 24.1 percent by area, on that same full sphere denominator, and it
saturates there: 12 panoramas reach 77 percent of what the site can ever offer
and 26 reach 90, so the per site budget is 12 to 16. Quote area fractions rather
than face counts, because face counts move with ray density and area does not.

What binds after that is extent rather than count. Widening the observation radius
from 60 to 80 m lifts achievable coverage from 30.6 to 44.8 percent, more than
tripling the panorama count inside 60 m does. Beyond that nothing helps: the
remaining 55 percent is roofs, courtyards and rear elevations that no street level
capture ever sees.

## 04: the resolved facade against the photograph it came from

Left is the source crop, right is the entity class the cutter carried onto the
surface, same camera and same 90 degree field of view. Every colour in the render
is asserted to match its legend swatch to within a few counts out of 255, so the
figure cannot silently drift from its own key.

## 05: one patch of facade, four layers deep

Support geometry, entity class, radio material and RMS surface height, stacked
upward. The three upper sheets are the same triangles carrying three independent
posteriors, which is the thing that makes this a semantic twin rather than a
textured mesh.

## 06: what the cutter refused

Candidate surface elements the cutter rejected, kept in a parallel table rather
than discarded. A moving object leaves a hole in the static surface instead of
being painted onto the wall behind it, which is why the pedestrians appear as
separate bodies in figures 01 and 02 rather than as texture on a facade.

## 07: the mesh study

Nineteen candidates scored on one ray cast. Panel b is the finding: flatness and
first-hit range fidelity trade against each other monotonically, and no voxel size
beats the as-built mesh on both. Panel d retires the argument that a cleaner mesh
traces faster. Across a 75x span in triangle count, throughput stays between 6.5
and 12.4 Mray/s with as built in the middle, and the pass to pass spread on a
single mesh is wider than the effect.

## 08, 09: brickwork scattering, with no fitted parameter

The bistatic orders of standard brickwork computed from construction geometry
rather than fitted to measurements, which matters because no measurement will be
taken in this project.

Two things to read off 08. The rigorous coupled wave solve and the cheap Kirchhoff
phase screen agree near specular and in the forward orders, and diverge by close
to 20 dB in backscatter. Since this study has a monostatic branch, and backscatter
is what that branch consumes, the phase screen cannot be used there.

09 is the honest one. Predicted against measured with nothing fitted: 2.0 dB rms
against Landron 1996 at 4 GHz, and 8.2 dB rms against Dillard 2003 at 28 GHz with
every point under-predicted.

That disagreement was chased rather than reported as an rms, and the answer is
symmetric. Inverting the two geometric parameters fits all six points to 1.40 dB
with construction plausible values, so the disagreement is in the parameters
rather than in the form of the model. But the measurement cannot adjudicate
either way: four repeats at one angle span a factor of 4.3 to 8.4 in amplitude on
brick at 5 to 30 degrees, with sample standard deviations 61 to 101 percent of
the means, and the 60 degree points exceed
the smooth surface Fresnel bound implied by the source's own permittivities, which
is impossible. So 1.40 dB is not a validation and 8.2 dB is not a refutation. The
model is validated at 4 GHz with nothing fitted and **unvalidated at FR2**, which
is now the top open item for that workstream.

## 10: what remeshing actually does

Three support meshes from the same camera. The flatness table says a 2 m voxel
grid improves median wall flatness from 10.1 to 6.1 degrees. The render says it
turns a Flemish market square into a glacier. Both are true, which is the point:
flatness improves in exact proportion to how much geometry the grid cannot hold.

## 11: eleven squares, one pipeline

Every acquired city, framed by its own geometry so a 26 m square in Toulouse and a
255 m canyon in New York are treated alike, with sky fraction and skyline height
measured from the mesh rather than quoted from the screening.

Sky fraction runs from 18 percent at Times Square to 46 percent at Krakow, which is
the geometric spread this study exists to turn into an exposure distribution.

The two labelled failures are on the sheet deliberately. Istanbul's flat green
plate is a more convincing argument for dropping it than its triangle count is, and
Toulouse's 7 percent sky is what an anchor sitting on a roofline looks like.

## 12: when the foliage treatment matters

Three ways of handling vegetation, swept against how much of the sphere the canopy
covers: delete it, treat it as an opaque surface, treat it as a participating
medium.

Panel b is the one to read. The surface and the null cross 0.5 dB at 2.1 percent
canopy solid angle, and Korenmarkt is 2.0 percent, so it sits on the line rather
than safely below it. Milan at 0.9 percent is genuinely safe. Between roughly 2
and 6 percent the surface is the outlier of the three, which means deleting
vegetation entirely would beat the wood mapping the pipeline currently uses.

Panel c shows why the answer is a band rather than a number: across the spread of
species in the standard's own tables, the medium spans a factor of 2.8 at 32
percent canopy and 8.9 over the full swept range.

## 13: brickwork convergence

Retained Floquet orders against the answer, with cost attached to every level,
for four cases. Across them the last truncation step moves specular by 0.1 to
0.8 percent and diffuse by 0.4 to 6.8, which is where the 1 percent and 7 percent
bars on every number in that work come from.

The 10 mm groove is visibly the slowest to converge, starting 40 percent low and
climbing, and it is the same waveguide physics that makes the phase screen fail
on it. That curve is also why an earlier claim about diffuse scattering had to be
corrected downward: it had been read off an under-converged rigorous result.

## 14: the first exposure distribution

Korenmarkt at 15 GHz over 120 walk locations. Left is the environment side, the
susceptibility relative to free space under three illumination models. Middle is
the body side, absorbed power density through the AEGIS phantom. Right is where
each location sits on the walk.

The spatial panel is the one that makes the point: the open square runs 10 to
15 dB hotter than the streets leaving it, and that is geometry rather than
material. Position within one square is worth 3.5 dB under isotropic illumination
and 8.2 dB under rooftop macro sites.

**This asset is stale.** Its two directional curves are the superseded
illumination law of `MONOSTATIC_SBR.md` section 2.7.1, which read 12.5 dB rooftop
and 18.0 dB street where the corrected law reads 8.2 and 16.6. The isotropic
curve and the spatial panel are unaffected. Rebuild from the `clean_semantic` run
before submission.

Read the rooftop and street curves as upper bounds, for the reason in figure 15.

## 15: has the crop radius converged

Nine crops at Korenmarkt from 60 to 340 m, with the observers held fixed inside
the smallest, so every radius scores the same 32 pedestrian standpoints and only
the surroundings change. The dotted line is the radius everything was acquired at.

Isotropic susceptibility and sky fraction converge by 100 m. **Rooftop sites need
250 m and street level small cells need 250 to 300.** At the acquired 130 m the
three errors are +0.05, +3.24 and **+9.93 dB**.

**The two directional curves are the superseded illumination law** and this sweep
has not been re-run. The requirement survives the correction and the sizes do
not: at Korenmarkt the 130 m to 250 m step falls from 4.58 to 1.09 dB rooftop and
from 11.37 to 8.21 dB street, so 250 m is now set by the street model alone.

The legend carries the explanation. The three models order by how close to the
horizon they place their weight, full sphere then 3.1 to 60 degrees then 0.95 to
33, and that is also the order of how much crop each one needs. A ray leaving a
standing observer near the horizon travels a long way before rising far enough for
a building of ordinary height to intercept it, so the more grazing weight a model
carries the further out the occluders that matter live. Throughout, the small crop
is not missing scatterers that would add power, it is missing blockers that would
remove it.

A rule proposed before the third curve existed, that the crop must reach the
farthest source, is refuted by it: street small cells reach only 150 m yet
converge later than rooftop, which reaches 250.

The mechanism is measured rather than argued. Susceptibility splits with no
residual into a zero bounce part and a multi bounce part, and the split says
blocking accounts for 69 to 77 percent of the effect with redistribution of
multi bounce throughput the rest.

The grey line marks where the meshes change from single to double precision, which
is why the 130 m point steps the wrong way. The 250 m and wider crops come from a
second tile fetch, controlled against the first by rebuilding a 200 m crop from it
and getting 390,518 triangles, identical to the original.

## 16: pedestrian exposure across eleven squares

The study's central object. 80 walk locations per city at 15 GHz, at the converged
250 m crop radius, with one common material prior, so what varies between curves
is urban form and nothing else. Milan joins here because it has a 250 m build,
having been acquired before the others at a radius that made it incomparable at
130 m.

Left is the environment side, the susceptibility relative to free space. Middle is
sky fraction, which is converged at this radius and therefore the panel to trust
absolutely. Right is the body side, peak absorbed power density through the AEGIS
phantom.

The two outer panels are labelled as crop-limited upper bounds in their own titles
rather than in a footnote, because at 130 m a scene contains nothing that can
occlude a macro site at 250 m.

**This is the 250 m run, at the radius where the directional models converge.**
The 130 m version is `cities130_15ghz_cdf.png` and the difference between them is
not a constant offset: over the ten sites with a mesh at both radii the crop
correction ranges 0.05 to 4.80 dB rooftop, 0.16 to 11.39 street, and $-0.17$ to
0.96 even for isotropic, where the tall cities move most. So the 130 m version
distorted the sites relative to each other rather than shifting them together,
and a between-site comparison at the narrow radius is not safe either.

**This asset was rebuilt on 2026-08-03 from `city250_L3_*`.** The version shipped
before that date had been copied from an aggregate a concurrent run was still
writing, so its Brussels curve carried 3 locations where every per site record
carries 80, its legend read `brussels grandplace (3)`, and its rooftop panel was
the superseded illumination law. `AGGREGATE_REBUILD.md` is the audit of that
failure and lists every headline number that moved.
`make_eleven_cities_exposure.py` now refuses to draw unless all eleven sites are
present, every standpoint count is equal and no line failed to parse, and it
names the offending sites when it refuses. One cosmetic defect survives: the
susceptibility axis still uses the pre-overhaul symbol $\chi_S$.

The run behind it is a single writer sweep of 11 sites at 80 standpoints, 880 in
total, at a bounce budget of three on the ground datum measured per site.

**The medians span 3.71 dB isotropic, 4.93 dB rooftop and 9.58 dB street small
cell across the eleven. The largest spread within one square is 6.46 dB isotropic
at Madrid and 12.89 dB rooftop at Brussels.** So under isotropic illumination,
where in a square a person stands matters more than which of eleven cities on
three continents the square is in, by 2.75 dB.

The rooftop ordering runs from Brussels' enclosed Grand-Place and Tokyo's Hachiko
crossing at the left to Mexico City's Zocalo at the right, and it is not simply
built density. Times Square is lowest on isotropic and it is the one site the law
correction moves in the rooftop ranking, from third of eleven to ninth, because
its towers block the horizon while leaving the high elevations comparatively
open, so it gained least from a correction that moves weight up off the horizon.

Krakow no longer stands clear of the other ten. That feature of the earlier
figure was its ground datum sitting 18.19 m above the surrounding pavement, which
put the whole walk on the roof of the Cloth Hall, and Toulouse had the same
defect at 13.94 m on the Capitole. Coming down to the pavement costs Krakow
1.40 dB isotropic, 5.26 dB rooftop and 12.97 dB street. See `GROUND_DATUM.md`.

## 17: does image evidence move exposure

The evidence ladder. Three runs on the same 120 locations with the same seed,
varying only how much of the scene carries material evidence from images: none at
all, one registered panorama at 3.13 percent of area, and eight fused stations at
10.57 percent.

The answer is a clean negative. Zero to a tenth of the scene shifts the median by
**0.29 dB** and moves exactly **one location out of 120** by more than a decibel.
A single panorama is worth 0.008 dB.

**This asset is stale in two ways.** A fourth rung exists, at 11.02 percent of
area, from gating on the sky conflict test rather than on the skyline residual,
and it readmits one station rather than removing any. And the shipped curves are
the superseded illumination law. Under the corrected law the same three rungs
read 0.2165, 0.2239 and 0.2354 with a 0.36 dB shift, and the count of standpoints
moving over a decibel rises from 1 to 8 of 120. The median result survives, the
per standpoint one is weaker than the caption says, and it is weakest under
isotropic illumination, where 17 of 120 move over a decibel.

That is worth more than a positive would have been. It says the geometry sets the
exposure distribution, and the semantic layer has to justify itself on occlusion
handling, evidence confidence and cross capture validation rather than on moving
the number. The ladder spans 0 to 10.6 percent because that is as far as street
level capture reaches, and it says nothing about a fully evidence bound scene,
which cannot be built from the street.

## 18 to 21: the explainer figures

Made by `make_explainer_figures.py` rather than by a pipeline run, so they carry
no data and cannot go stale against a rerun. They exist because
`PAPER_METHODS.md` was opening on an integral, and a reader has to picture the
situation before the integral means anything. They are figures 1, 2, 3 and 6 of
that document, in reading order.

**18, elevation is a ratio.** Three sources on the boundary of the rooftop
deployment model, drawn to kill the most common misreading of the elevation
bands: a 60 degree arrival is not something above a roofline, it is a mast 43.5 m
up at 25 m away. Elevation is measured from the pedestrian's own horizon
throughout this study, so a steep arrival means a **near** source.

**19, the deployment box and the density it induces.** Left, the models are
rectangles in the (range, height) plane and constant elevation is a ray through
the origin, so the quoted support is contributed by two opposite corners. Right,
the density those rectangles actually induce, from the production
`elevation_band_measure`. 45 percent of the rooftop band's solid angle sits above
30 degrees and carries 3.3 percent of the power, which is why binary colouring by
band membership is nearly uninformative and why section 4.2 had to be corrected.

**20, why the tracer runs backwards.** Forward against adjoint, with real
occlusion in both panels so the sky wedge is the one that cross section actually
has. Forward wastes essentially every ray on a point observer, adjoint wastes
none, and the escape direction is exactly the argument the illumination density
wants.

**21, one ray from launch to deposit.** A single sample, with line thickness as
throughput. The reflections are specular off vertical walls rather than drawn by
eye, so the geometry in the figure is the geometry in the loop.

## 22: how far the photographic evidence reaches

The method figure for the thread the whole paper hangs on. Transmitter and
receiver sit at the same point, so a photograph taken from that point sees the
surfaces the early bounces hit, material is measured rather than assumed, and how
far that measurement reaches is what sets the bounce budget. Until this figure
that thread was carried entirely by prose and tables.

Two panels because there are two different meanings of observed and they must not
be differenced against each other. Panel a is geometric, observed means visible
from the standpoint on a mask built by first hit probing 2e6 directions from the
standpoint itself. Panel b is evidential, observed means a registered panorama
landed transient free rays on the triangle and the class it collected carries a
material. Each panel says which one it is under its own title.

**a, the guarantee, on real photogrammetric geometry.** Share of power whose whole
interaction chain lands on visible surfaces, median over 42 standpoints on the
four meshes that have a visibility probe, Korenmarkt, Brussels Grand-Place, Milan
Duomo and Tokyo Hachiko. A path that returns to the standpoint reads 1.000000,
0.999972 and 0.980 at the first three interactions. The outward path the adjoint
estimator actually traces reads 0.999, 0.912 and 0.714. Both ends of a returning
path are unoccluded from the standpoint so both carry evidence by construction,
and an outward path has only its first interaction there. The grey wedge is the
size of that difference, which is the price of the efficiency. The whiskers are
the interquartile range over the 42, and the closed loop dips at the third
interaction because the guarantee is over the two ends of a loop and not over its
middle.

**b, and it is a radius rather than a property of a square.** Korenmarkt at the
130 m crop, 200k rays per standpoint, against distance from the standpoint to the
nearest admitted station. The nearest bin of the underlying report holds exactly
the eight station positions and no walk standpoint, which is why the first
category is drawn as the cameras themselves. Seven of the eight sit between 0.978
and 0.999 at the first interaction, so where a camera stood the geometric and the
evidential readings coincide. The eighth reads 0.362 and is a registration
failure that the skyline residual gate passed, plotted hollow and excluded. Within
20 m the second interaction still lands on photographed material 93 to 96 percent
of the time. Past 40 m all three interactions are under 0.20.

The dashed line is the number the study has to own. Pooled over the published 90 m
walk the first interaction coverage is 0.479, so rather less than half of the
power at the first interaction lands on a triangle any panorama saw. That is the
walk radius and not the bounce budget. The eleven city results run with
`--materials geometric` and use no image evidence at all, so none of them depend
on it, but the Korenmarkt evidence ladder does.

Panel counts are on the sheet: 8 stations, then 4, 5, 7 and 24 walk standpoints in
the four distance bins.

## 24: the diffraction hole, bounded on the geometry that was traced

The tracer is rectilinear and has no diffraction term, which is the largest known
hole in the method. The defence is not an argument from the literature, it is a
computation on the same 250 m meshes and the same standpoints as the eleven city
run, and this figure is that computation. Made by
`make_diffraction_bound_figure.py` from `outputs/diffraction_bound/*.json` and
the production location records.

**a, the construction.** The most enclosed Korenmarkt standpoint, 720 azimuths by
600 logarithmic elevation bands, 8.7 percent sky by solid angle. Every blocked
direction carries the Fresnel-Kirchhoff parameter of ITU-R P.526-16 equation (27)
and is shaded by the knife edge gain of equation (31). The bright rim just inside
the skyline is where the bound lives, and the dashed line at 5 degrees is where
88.0 percent of the street small cell illumination measure sits, in the darkest
part of the map.

**b, the validation, and it matters as much as the bound.** The same mask
integrated over the *visible* directions has to reproduce the direct term the
production tracer got from 200 000 Monte Carlo rays. Independent code path,
independent quadrature, independent ray budget. Median disagreement 0.19 percent
isotropic, 1.14 percent rooftop, 3.70 percent street, worst case 1.29, 6.44 and
23.05. This is the first external check any part of this tracer has had. The
panel also shows why the street row is the weak one: the disagreement grows as
the direct term shrinks, and the street model's direct term is four decades
smaller than the isotropic one.

**c, the bound, over the full distribution rather than three medians.** Pooled
over the 60 standpoints, the uplift a single edge diffraction term could add is
0.06 / 0.15 / 0.42 dB at the median and 0.13 / 0.37 / 1.26 dB at the 90th
percentile, isotropic / rooftop / street. Every assumption in the construction
errs upward, so it is a bound and not an estimate. The grey band is what the
study's own answer already varies by inside a single square, 2.49 to 10.35 dB
over the three sites and three models, so under the isotropic and rooftop models
the omission is one to two orders of magnitude below the effect being measured.
The dashed curves are the identical calculation at 2 GHz, a factor of 3.1 to 5.0
larger in linear terms. That reproduces the frequency argument on this geometry
rather than borrowing it from a canyon measurement campaign.

**d, the concession, which is on the sheet rather than in a footnote.** Under the
street small cell model the bound is not small: one Grand-Place standpoint reaches
12.64 dB. The panel says why it should not be read as a correction of that size.
The bound scales inversely with the exposure, so the large uplifts belong to
standpoints whose absolute susceptibility is of order 1e-5, the smallest in the
study. The four stars are the standpoints where the model's entire elevation
support is occluded, so the direct term is exactly zero, every watt in the traced
answer arrives by reflection and the uplift is undefined. Those four are also why
the street curves in panel c stop at 56 of 60 instead of reaching one.

**One number in `WHY_NOT.md` section 2.6 does not reproduce from the shipped
JSON.** The pooled street small cell 90th percentile is tabulated there as
1.84 dB. Over the 56 standpoints with a defined uplift it is 1.26 dB, and if the
four undefined ones are ranked at the top of the sample it is 4.80 dB. Neither is
1.84. Every other entry in that table reproduces to the last digit, so this looks
like a single transcription slip rather than a bug in `bound_diffraction.py`.
