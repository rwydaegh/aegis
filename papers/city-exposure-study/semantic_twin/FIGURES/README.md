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

Fusing twelve panoramas raises directly observed surface to 24.8 percent by area,
and the coverage curve has not saturated. Quote area fractions rather than face
counts: face counts move with ray density, area does not.

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

Retained Floquet orders against the answer, with cost attached to every level.
Specular settles within 0.6 percent from 1,393 orders upward. Diffuse oscillates
without a monotone trend, which is why every diffuse number in this project
carries a 6 percent bar rather than a digit count.

## 15: has the crop radius converged

Six crops at Korenmarkt with the observers held fixed inside the smallest, so
every radius scores the same 32 pedestrian standpoints and only the surroundings
change.

The lower panel is the reading. Isotropic susceptibility and sky fraction fall an
order of magnitude below the half decibel criterion from 120 m onward, so they are
converged. **Rooftop illumination never gets under it**, falling 3.1 dB between the
130 m the study uses and 200 m and still moving at the end of the sweep.

The mechanism is in the illumination model rather than the geometry. Macro sites
sit at horizontal ranges out to 250 m, and a 130 m crop holds nothing that can
occlude one of them, so rays escape to a sky a real building would have blocked.
The small crop is not missing scatterers that would add power, it is missing
blockers that would remove it.

The vertical line marks where the meshes change from single to double precision
builds, which is why the 130 m point steps the wrong way. Every step above it is
like for like.
