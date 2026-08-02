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

The least flattering figure and the most useful one. A single registered panorama
is a first hit on 3.3 percent of support triangles, 4.4 percent by area. 72.8
percent of faces take their material from tile texture and 23.9 percent carry no
image evidence at all.

Fusing twelve panoramas raises directly observed surface to 24.1 percent by area,
and it saturates there: 12 panoramas reach 77 percent of what the site can ever
offer and 26 reach 90, so the per site budget is 12 to 16. Quote area fractions
rather than face counts, because face counts move with ray density and area does
not.

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
either way: four repeats at one angle span a factor of 3.3 to 8.4 in amplitude
with standard deviations at or above the means, and the 60 degree points exceed
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
species in the standard's own tables, the medium spans a factor of five at 32
percent canopy.

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
and 12.5 dB under rooftop macro sites.

Read the rooftop and street curves as upper bounds, for the reason in figure 15.

## 15: has the crop radius converged

Nine crops at Korenmarkt from 60 to 340 m, with the observers held fixed inside
the smallest, so every radius scores the same 32 pedestrian standpoints and only
the surroundings change. The dotted line is the radius everything was acquired at.

Isotropic susceptibility and sky fraction converge by 100 m. **Rooftop sites need
250 m and street level small cells need 250 to 300.** At the acquired 130 m the
three errors are +0.05, +3.24 and **+9.93 dB**.

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

## 16: pedestrian exposure across ten squares

The study's central object. 80 walk locations per city at 15 GHz, one common crop
radius and one common material prior, so what varies between curves is urban form
and nothing else.

Left is the environment side, the susceptibility relative to free space. Middle is
sky fraction, which is converged at this radius and therefore the panel to trust
absolutely. Right is the body side, peak absorbed power density through the AEGIS
phantom.

The two outer panels are labelled as crop-limited upper bounds in their own titles
rather than in a footnote, because at 130 m a scene contains nothing that can
occlude a macro site at 250 m. Comparison between cities at a common radius is
unaffected, since the bias is a property of the radius.

The ordering runs from Brussels' enclosed Grand-Place at the left to Krakow's open
Rynek at the right, spanning 4.20 dB in median. The spread within a single square
reaches 6.48 dB, so which part of a square a person stands in matters as much as
which city the square is in.

## 17: does image evidence move exposure

The evidence ladder. Three runs on the same 120 locations with the same seed,
varying only how much of the scene carries material evidence from images: none at
all, one registered panorama at 3.13 percent of area, and eight fused stations at
10.57 percent.

The answer is a clean negative. Zero to a tenth of the scene shifts the median by
**0.29 dB** and moves exactly **one location out of 120** by more than a decibel.
A single panorama is worth 0.008 dB.

That is worth more than a positive would have been. It says the geometry sets the
exposure distribution, and the semantic layer has to justify itself on occlusion
handling, evidence confidence and cross capture validation rather than on moving
the number. The ladder spans 0 to 10.6 percent because that is as far as street
level capture reaches, and it says nothing about a fully evidence bound scene,
which cannot be built from the street.
