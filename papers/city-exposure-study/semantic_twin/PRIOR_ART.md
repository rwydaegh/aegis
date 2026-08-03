# Prior art and positioning

Hostile review, run 2026-08-01. The brief was to find what kills or weakens the
novelty claim, not to confirm it. Companion to `METHOD.tex` (what the method is),
`MONOSTATIC_SBR.md` (the formulation) and `DESIGN.md` (reconstruction).

Papers marked "full PDF read" were downloaded and grepped. Everything else is
marked abstract-only, and abstract-only claims must not be repeated as
established. Every DOI carrying a verdict below was checked against Crossref.

Method: Semantic Scholar Graph API with citation-graph walking, OpenAlex,
Crossref, Unpaywall, the arXiv API, GitHub raw source, vendor documentation and
direct PDF fetches. The session WebSearch budget was exhausted at 200 calls early
on, so there was no Google Scholar or IEEE Xplore full-text pass anywhere in this
exercise. Negative findings therefore rest on title and abstract indexing. They
are strong rather than airtight. No patent search was run.

## Verdict

**Every individual ingredient is published. Only the combination is new.** That
is the honest answer and it should be written in those words.

Photogrammetric city twin with semantically classified materials, ray traced at
28 GHz, absorbed power density on a phantom, ICNIRP framing, multiple cities: in
print, by this author, `10.1038/s44459-026-00031-4`. Street-view imagery
segmented per pixel into materials, projected onto city geometry, cut into
per-material faces and ray traced: ACM MobiCom 2023, mmSV. The microfacet BRDF
for radio propagation: ISNCC 2020. The observation that the Degli-Esposti
directive model is non-reciprocal: published by Degli-Esposti's own group, who
also already built the repaired version. Tracing outward from the point of
interest, tallying escaping rays and invoking reciprocity to get a
source-independent angular operator: adjoint neutron transport in the 1950s,
daylight coefficients in 1983, Veach in 1997, precomputed radiance transfer in
2002, polarisation added in 2016 and 2024, and receiver-hardware substitution as
a headline feature in virtual acoustics in 2020. Ten-city population exposure
comparison: Environment International 2025. Exposure factorised as a precomputed
body coefficient times a swappable deployment term: the LEXNET exposure index,
2015.

What is left, stated as narrowly as it deserves: **a delay-resolved,
polarisation-complete, second-moment reciprocal transfer operator, published per
location as a reusable object, for RF exposure, at FR2 and FR3.** Nobody in radio
propagation has built that, and the search for it was deliberate and hard.

Is the combination enough for the venue? Yes for a good IEEE journal, on one
condition: the paper concedes each component explicitly, with citations, and
claims only the composition. No if the paper leads with "digital twin",
"street-view materials", "transmitter-agnostic" or "first to consider incidence
angle", because a well-read referee owns a counter-citation for each.

The single largest risk is not an external paper. It is a weak self-citation of
the npj paper. The failure mode is not that a referee misses it, it is that a
referee reads this paper as that paper with more cities.

---

# Question 1: image-driven RF material assignment

## The decisive item, now fully resolved

**mmSV, Kamari, Chae, Pathak (George Mason), ACM MobiCom 2023,
`10.1145/3570361.3613291`. Full PDF read**, from `lit/3570361.3613291.pdf` already
sitting on disk. It was flagged as the highest-value unreachable item
in this review and it turned out to be on disk. It occupies more of section 1
than any summary suggests, so here is what it actually does:

- 13 outdoor material categories (brick, stucco, vinyl, stone, polished stone,
  glass, metal, wood, tile, ceramic, asphalt, foliage, sky). Their own SVM
  dataset, 1200 Street View images, 132,423 hand-labelled 256x256 patches,
  augmented from MINC-2500.
- A patch classifier that, given a pixel, returns **the probability that the
  pixel belongs to a material category**, then superpixel over-segmentation to
  clean up boundaries, then **dynamic object removal** for cars and people.
- **The same projection this study uses.** A ray is cast from the panorama origin
  through each pixel of the spherical Street View image and intersected with the
  3D building surface, and the intersection inherits the pixel's material. That
  is the free first hit, three years early, against OpenStreetMap prisms rather
  than photogrammetry.
- **A fishnet, by another name.** RANSAC plane fit to the material point cloud,
  each plane split into 10 cm by 10 cm faces, each face assigned the most
  commonly predicted material among its points, then neighbouring same-material
  faces merged into surfaces.
- Shooting and bouncing rays at 60 GHz, with reflection loss from a
  (material, incidence angle) lookup table derived from complex permittivity and
  validated on their own testbed. 90.62 percent patch accuracy, 86.7 percent full
  scene.
- They name the dominant error source themselves: inaccuracy in the OSM 3D
  building models.

**What this means.** Per-pixel material segmentation of street-level imagery,
projected by ray casting onto city geometry, cut into per-material surface
elements and ray traced at millimetre wave, is published at a top venue. Do not
claim it. What remains genuinely different here: photogrammetric geometry instead
of OSM prisms, cuts that follow the semantic island boundary exactly instead of a
10 cm grid with a majority vote, a retained posterior instead of the majority
vote, ITU-R P.2040 permittivity **plus a separately sourced roughness prior**
feeding a Rayleigh specular-diffuse split instead of a scalar reflection-loss
lookup, polarisation, clutter promoted to geometry, and the exposure observable.
That is a real list. It is a much shorter list than the method's framing assumes.

Two corrections to that sentence, both from `ROUGHNESS.md`, which read the
in-force Recommendation rather than trusting the usual restatement.

**P.2040 does not supply roughness and never did.** Its section 3 Table 3 gives
`eps' = a f^b` and `sigma = c f^d` and nothing else: no roughness column, no RMS
height, no scattering coefficient. The layered-slab model in section 2.2.2 that
Table 3 feeds assumes smooth, planar, parallel interfaces, so its reflection and
transmission coefficients are smooth-surface coefficients by construction. The
only RMS height anywhere in P.2040-4 is in equation 48, a per-metre waveguide
attenuation for corridors and tunnels, and the only place it models scattering
from a building surface at all is section 2.3, where the rough surface is defined
as "a round convexity array formed by locating circular cylinders periodically"
and solved with lattice sums and a T-matrix. P.2040-3 is the same, and P.1411-13
has no facade roughness either. So the roughness half of the sentence above is
this repository's own contribution (`config/surface_roughness.json`, sixteen
classes with evidence grades), not an ITU inheritance. Writing "ITU-R P.2040
permittivity and roughness" in a paper hands a referee a free correction.

**The Rayleigh split covers the random-roughness classes only.** See section 4.6.

## Tier 1, the rest of what can sink section 1

**VisRFTwin**, An, Shangguan, Kaewell, Pietraski (InterDigital), Senic, Gentile,
Golmie (NIST), Jamieson (Princeton). arXiv:2603.13383, 11 Mar 2026. **Full PDF
read.** Reproduces nearly the whole spine: roughly 100 panoramic images per scene
to frozen CLIP and DINOv2 per-pixel semantic embeddings, lifted into 3D through a
NeRF. GPT-4o proposes candidate material types, CLIP cosine similarity picks the
label, and a database initialised following ITU standard material definitions
supplies permittivity and conductivity. **Roughness is inferred visually** by VLM
discrete-level classification mapped through a roughness-to-scattering-coefficient
table with a Lambertian lobe. Sionna RT 0.19.2, 60.5 GHz, gradient calibration on
sparse soundings. For the outdoor scenario they take virtual photographs in
Google Earth Studio over Google's photorealistic 3D geometry.

Gaps: argmax cosine similarity with no posterior, roughness as a discrete bucket
rather than a height and correlation length into a Rayleigh split, materials
attached to patches of existing surfaces rather than to re-meshed image-space
semantic islands, no attribute vector, 60 GHz only, no clutter recovery, no
exposure. **Critically it needs real channel measurements to close the loop**,
which kills its eleven-city scalability. That is this study's best differentiator
against it.

**Cazzella, Linsalata, Badini (Huawei Technologies Italia), Matteucci, Magarini,
Spagnolini**, "High-Fidelity RF Mapping: Assessing Environmental Modeling in 6G
Network Digital Twins", arXiv:2507.19173 and Computer Networks 2025. **Full PDF
read.** Their motivation is this study's, verbatim: with only untextured building
meshes available, they retrieved 616 camera images of building facades across
Milan over 550 by 670 m, applied homographic perspective correction, stitching
and texture projection onto facade faces in Blender, then **manually segmented
window mesh components** using the textures as reference, ITU glass against ITU
concrete, Sionna RT at 28 GHz. They also place 505 parked-vehicle meshes from
satellite imagery.

Gaps: the segmentation is manual, an MSc thesis per the acknowledgements. Two
classes only, OSM stacked prisms rather than photogrammetry, no roughness, no
specular and diffuse split, no posterior, one site. Their actual contribution is
the Hausdorff-RT and Chamfer-RT metric, not the material method. But it is
sub-facade material heterogeneity for RF, published, at 28 GHz, with an
industrial co-author.

## Tier 2, automated semantics to EM materials, coarser granularity

- **HoRAMA**, Ying, Qian, Wang, Ma, Shakya, Rappaport (NYU WIRELESS),
  arXiv:2602.12942, ICC 2026, `10.1109/ICC59461.2026.11587422`. **Full PDF read.**
  RGB video to MASt3R-SLAM point cloud, PTv3 instance segmentation, Qwen3-VL
  material classification, mapped to ITU-R P.2040 with majority voting across
  frames, per-face material in Mitsuba XML, NYURay. Two months of work reduced to
  16 hours, 2.28 dB RMSE against 2.18 dB hand-built. **Validated at 6.75 and
  16.95 GHz, which is the FR3 band this study wants to claim.** Their planar-merge
  tolerance is 0.1 m, twenty times tighter than this study's 2 m mesh error. Gaps:
  indoor 700 square metre factory, four or five classes, granularity is the object
  instance so a wall is one material, majority voting explicitly discards the
  distribution, no roughness or diffuse scattering. They name outdoor urban as
  future work.
- **Xia, Zhou, Zhang, Cui, Liu, Ji, Zhang, Zhao, Xiao** (Wuhan University), "Path
  Loss Prediction in Urban Environments With Sionna-RT Based on Accurate
  Propagation Scene Models at 2.8 GHz", IEEE TAP 72(10):7986-7997, Oct 2024,
  `10.1109/TAP.2024.3451214`. **Full PDF read**, from
  `lit/Path_Loss_Prediction_in_Urban_Environments_With_Sionna-RT_...pdf` in this
  directory. Code public at
  `github.com/GuozhenXia/Accurate-propagation-scene-modeling-method`. This entry
  was marked abstract-only in an earlier revision and the details below change
  two verdicts, so it is written out at length in section 4.7. Summary:
  their own DJI Matrice 30 oblique drone survey of a 900 by 800 m green suburban
  district near Qingdao with 55 buildings, RandLA-Net segmentation, ball-pivoting
  reconstruction of vegetation, fences and street furniture, cars **deleted**,
  one ITU material per class over five classes, Sionna-RT at 2.8 GHz with both
  ends at 2.2 to 2.5 m. Gaps: no street-level imagery anywhere, no posterior, no
  sub-facade variation, no glass class at all, best RMSE about 6 dB.
- **Zhang, Zhou, Brennan, Wang, Li**, IEEE TAP Mar 2024,
  `10.1109/TAP.2024.3355502`. **Abstract-only.** Deep-learning semantic
  segmentation on a point cloud to electrical parameters, surface reconstruction,
  then GO and UTD ray tracing, validated against measurements. Outdoor urban, and
  two years ahead of the 2026 VLM wave.
- **Kang, Lim, Gu, Ko, Quek, Park**, "VLM-Guided Differentiable Ray Tracing for
  Multi-Material RF Parameter Estimation", arXiv:2601.18242. A VLM parses scene
  images to infer material categories and maps them to priors via an ITU-R
  material table. Indoor, priors are gradient initialisations rather than a
  posterior.
- **RFDT-Channel**, arXiv:2606.01261. COLMAP with 3DGS and SuGaR mesh,
  LiDAR-regularised, then OpenScene segmentation to concrete, glass, wood, metal,
  Sionna RT at 28 GHz. Runs an all-concrete against multi-material ablation and
  reports that **material binding cuts effective paths from 742 to 52 while
  leaving the dominant path amplitude nearly unchanged.** That number needs
  engaging with: it argues material detail lives in the weak-path tail.
- **Li, He, Yang, Qi, Zhang, Zhang, Han, Ai, Zhong**, "Point Cloud-Based
  Environmental Material Classification for Wireless Channel Ray-Tracing
  Simulations", IEEE TCCN 2026, `10.1109/TCCN.2026.3659825`. **Abstract-only.**
  Frames the problem exactly as this study does, and analyses how material
  recognition accuracy propagates into path loss and delay spread. Outdoor.
- **Suga, Yoshida, Gozono, Maeda, Sato**, IEEE WCL Jun 2025,
  `10.1109/LWC.2025.3557794`. RGB-D plus material classification for radio map
  estimation, 2.14 dB NLoS gain. The cleanest published demonstration that vision
  to material to ray tracing pays. Indoor Wi-Fi.
- **Vaara, Sangi, Bordallo Lopez, Heikkila (Oulu)**, arXiv:2507.04021, IEEE AWPL,
  `10.1109/LAWP.2026.3670638`. **Full PDF read.** Learns permittivity,
  conductivity and scattering coefficients per material label by differentiable
  ray tracing. **Their introduction proposes this study's idea as future work**,
  suggesting semantic segmentation models to automatically label points by
  material and learn their properties by differentiable RT.
- **Zhao, Zhang, Zhang, Sun, Zhang (BUPT)**, "Accurate mmWave Path Loss Prediction
  via Digital Twin Environment With Material Semantics", IEEE AWPL Feb 2026,
  `10.1109/LAWP.2025.3639276`. Owns the phrase "material semantics" in the mmWave
  digital twin context, but feeds a learned regressor rather than a tracer.
- Others in the family: arXiv:2602.13340 and `10.1109/TIM.2026.3660422` (indoor,
  ITU-R parameters), arXiv:2401.01288, and "Material-informed Gaussian Splatting
  for 3D World Reconstruction in a Digital Twin" (arXiv:2511.20348, IEEE IV 2026),
  which is optical and automotive but structurally identical.

## Aerial and satellite leg

Land-cover classification driving propagation is old, but it operates at one
clutter category per raster cell driving an empirical correction, never a
per-surface EM material: the ITU-R P.2108 lineage (`10.1049/cp.2018.0724`),
`10.1109/tvt.2014.2310777`, the P.452 and P.1812 clutter extensions, and 1997-era
high-resolution clutter databases (`10.1049/CP:19970365`). Contrast case:
"Prediction of Wireless Channel Statistics With Ray Tracing and Uncalibrated
Digital Twin", arXiv:2411.13360, `10.1109/LWC.2025.3577135`, where the twin comes
from satellite images and is uncalibrated.

That tradition sits at 10 to 100 m polygons against roughly 4 cm here. Stating it
as a resolution jump of three to four orders of magnitude survives scrutiny.

## One facade into several materials: occupied

Do not claim it. Cazzella et al. cut windows out of facades by hand, ITU glass
against ITU concrete, at 28 GHz in Sionna, and measured the channel impact. mmSV
does it automatically at 10 cm face resolution over 13 classes at 60 GHz.
VisRFTwin achieves sub-facade granularity automatically by attaching per-point
CLIP-derived materials to a NeRF surface.

Not occupied: doing it automatically, at many classes, with roughness priors,
retaining a posterior, on third-party photogrammetric geometry, at city scale,
with cuts that follow the semantic boundary rather than a fixed grid. Claim
automation, class count, physics and scale. Use Cazzella as evidence that the
effect is worth resolving, not as a competitor beaten on concept.

## OSM-to-Sionna pipelines: every one hard-codes one material per class

Verified in raw source, not from abstracts.

| Pipeline | Material assignment | Source |
|---|---|---|
| OpenGERT (arXiv:2501.06945, DySPAN 2025, `10.1109/DySPAN64764.2025.11115956`) | `roof_material_name="itu_metal"`, `wall_material_name="itu_marble"`, `terrain_material_name="itu_concrete"`, `default_material_name="itu_brick"`, four globals swapped by whole-object slot | `serhatadik/OpenGERT`, `extract_geometry.py` |
| Geo2SigMap (arXiv:2312.14303) | three globals for ground, rooftop and wall into the Mitsuba XML | `functions-lab/geo2sigmap`, `scene_generation/core.py` |
| Sionna reference scenes | `munich.xml` has 1152 `itu_marble` and 1144 `itu_metal` references, exactly two materials per building. `etoile` has four scene-wide | Sionna repo |
| Blosm / blender-osm | no electromagnetic information at all, which is why every downstream tool invents globals | importer |
| BostonTwin (MMSys 2024, `10.1145/3625468.3652190`) | "the materials are assigned based on the type of model reported in the Model Catalog (ITU brick for 'Wall', ITU concrete for 'Building', ITU medium-dry ground for the ground)" | paper, verbatim |
| Sionna RT API | per scene-object `obj.radio_material = 'itu-brick'`, ITU-R P.2040-3 coefficients, scattering coefficient, XPD, Lambertian, Directive and Backscattering patterns. No texture or imagery-based assignment anywhere | nvlabs.github.io/sionna |

None ingests imagery to pick materials.

Quotable for the introduction, verified verbatim in the Sionna RT paper
(arXiv:2303.11103): there is no straightforward process to obtain the material
properties, so it is important to develop techniques that automatically assign
material properties, such as permittivity, conductivity, permeability, roughness
and scattering functions, to all objects in a scene. Excellent motivation, and an
equal non-obviousness risk, because NVIDIA posed exactly this problem, roughness
included, in 2023.

Synthetic counterparts owning the RGB-to-EM co-registration idea: UR-MAT
(`10.1145/3746027.3758314`), OSM-derived Unreal scenes with PBR materials
annotated with electromagnetic properties plus material segmentation masks,
explicitly for mmWave. Great-X (arXiv:2507.08716). DeepTelecom
(arXiv:2508.14507), which imports Google 3D Tiles through Blosm, states this
study's motivation for it by noting the imported models are coarse with uneven
surfaces and merged components, and responds by hand-rebuilding LoD3 in SketchUp
with per-surface EM annotation. Same geometry source, manual answer.

## Learned material classification and inverse calibration

- Hoydis, Aït Aoudia, Cammerer, Nimier-David, ten Brink, Keller, "Learning Radio
  Environments by Differentiable Ray Tracing", arXiv:2311.18558, IEEE TMLCN 2024,
  `10.1109/TMLCN.2024.3474639`. The reference point for inverse calibration.
- RadioTwin, DySPAN 2025, `10.1109/DySPAN64764.2025.11115919`, materials from RF
  rather than imagery, the direct precursor to VisRFTwin.
- RFCanvas, SenSys 2024, `10.1145/3666025.3699351`, fuses visual priors and RF
  measurements with tensorial fields and signed distance fields.
- WiSegRT, arXiv:2312.11245, `10.1109/ICNC59896.2024.10556262`.
- On-site permittivity estimation at 60 GHz from point clouds, IEEE TAP 2018,
  `10.1109/TAP.2018.2829798`.
- NEMF, arXiv:2603.02582. **Full PDF read.** Inverts a continuous spatially-varying
  permittivity and conductivity field from images plus ambient RF. Synthetic-only,
  indoor, inverted from physics rather than read off semantics.
- arXiv:2312.12625, arXiv:2605.22361.

Uncertainty-in-materials prior art, relevant to the posterior claim:
polynomial-chaos UQ of ray tracing, `10.1109/EUCAP.2014.6902136`, and "Effects of
inaccuracy of material permittivities on ray tracing results",
`10.1109/APWC.2013.6624930`.

## NeRF and 3DGS for wireless: almost no material semantics

No material semantics, purely implicit fields: NeRF-squared
(`10.1145/3570361.3592527`), WiNeRT (ICLR 2023), NeWRF (arXiv:2403.03241), WRF-GS
(INFOCOM 2025), RF-3DGS (arXiv:2411.19420), GSRF (arXiv:2502.01826), PropSplat.

Exceptions to flag: NEMF above. Vaara et al., arXiv:2605.07781, the direct
competitor to reconstructed-mesh-as-RT-geometry, no semantic segmentation.
CORF-GS (arXiv:2607.25569). "Neural Reflectance Fields for Radio-Frequency Ray
Tracing" (arXiv:2501.02458), which already states this study's motivating
sentence, that there still lacks scalable approaches to estimate material
reflectivity in real-world environments. Also **RF inverse rendering**,
arXiv:2604.07086 (April 2026), which "explicitly decouples RF emission, geometry,
and material electromagnetic properties" through an RF-aware BSDF in a Gaussian
splatting framework. Source-environment decoupling as a selling point is four
months old in wireless.

Sensor-reconstructed geometry for ray tracing is a decade old: Järveläinen and
Haneda, IEEE TAP 2016, `10.1109/TAP.2016.2598200`.

## Commercial 6G twins

No shipping commercial product resolves material below one material per building
or per CityGML surface class. That finding is solid, though the capability often
exists and is simply unpopulated.

**NVIDIA Aerial Omniverse Digital Twin.** Materials per building or per CityGML
semantic surface class (Building, Building Installation, Wall Surface, Roof
Surface, Ground Surface). The physics is real and already there: ITU-R P.2040
four-parameter permittivity plus scattering XPD, RMS roughness, scattering
coefficient under the effective roughness model, and forward and backward lobe
exponents. Geometry ingestion is OpenStreetMap and CityGML only, no
photogrammetry, no 3D Tiles, no imagery-derived materials anywhere in the docs.
So the honest framing is not "they cannot do this". It is that the roughness and
scattering machinery is shipping and there is nothing to populate it with.

**Ansys Perceive EM and RF Channel Modeler.** The best framing sentence
available, and Ansys already ingests exactly this geometry class. From the
26 Jun 2024 Ansys webinar "Enabling 6G Technologies" (Shawn Carpenter, Program
Director), transcript at `spinoff/webinar_ansys/transcript.md` in this repo: a
5 cm Aerometrex photogrammetric model of downtown Denver, about 4.5 by 4.5 km and
about 10 million facets, plus Cesium 3D Tiles streaming. The texture is explicitly
decoration: the photogrammetry overlay is described as pretty, but underneath are
structural facets, and it is a structural model with a visual overlay introduced
as a texture, while the solver consumes a list of mesh triangles with associated
material properties assigned separately in a USD layer.

**The incumbent has the photograph registered to the geometry and uses it as
wallpaper.** That is the paper in one sentence, sourced to the vendor's own
program director.

**Remcom Wireless InSite.** Per-facet in principle: all CAD features are composed
of planar facets and the material assigned to each facet determines its
electromagnetic behaviour. Material types include dielectric half-space, layered
dielectric, PEC-backed, constant-coefficient, **Monte Carlo for parameter
uncertainty**, and user-defined measured-coefficient files. City workflow is DXF
and SHP import with materials assigned after import. No imagery-driven assignment
documented, and no roughness or diffuse parameters exposed on the materials page.

**Altair WinProp and Feko, Keysight, Rohde and Schwarz, Nokia Bell Labs,
Ericsson, Huawei.** Searched, nothing found, pages 404 or 403 from this sandbox.
Not disproven, just undocumented. Do not write that these vendors do not do it.
Write that it is not publicly documented.

**Residual commercial risk: Siradel and Luxcarta.** Telecom geodata vendors who
classify clutter from imagery for RF planning and publish no methodology.
Siradel's page lists inputs as satellite imaging, aerial photography, IoT sensors,
GIS technology and open data, and stops. Closing this needs a sales conversation,
not a literature search.

## Two attacks to pre-empt in section 1

**The motivation attack.** OpenGERT reports that minor perturbations in
permittivity and conductivity do not significantly alter channel statistics,
while variations in building height and position significantly alter all
statistics even at 1 m in height and 0.4 m in position. This study's geometry is
3D Tiles at roughly 2 m error, worse than the geometric perturbation they say
dominates. Checked, and the claim is narrower than the sentence sounds: 3.5 GHz,
and the perturbation is a standard deviation of 10 percent of the initial value,
on Sionna's default Munich and Etoile scenes. That says a 10 percent wobble
around a correct value does not matter. It says nothing about glass against metal
against vegetation, nothing about transmission through thin panes, and nothing
about the specular-diffuse partition that dominates at 28 and 60 GHz, where
material error is a category error rather than a perturbation. Their own escape
hatch is quotable in this study's favour: if the initial material parameters are
largely unknown or mischaracterised, the resulting variability would likely be
much greater. Make that argument with numbers, or it will be made against you.
See also section 4.5 below, where the geometry threat is treated as real.

**The obviousness attack.** Two published papers assemble most of the method
between them. Texture2LoD3 (arXiv:2504.05249, TUM) ortho-rectifies street-level
panoramas against a low-LoD building prior and segments facades into semantic
surfaces, with the ReLoD3 dataset released and zero RF, stated applications being
solar potential and driving simulation. Combine with Cazzella et al. and the
method is largely assembled. Siblings: Scan2LoD3 (arXiv:2305.06314), MLS2LoD3
(arXiv:2402.06288), TUM2TWIN (arXiv:2505.07396), ZAHA
(`10.1109/wacv61041.2025.00743`).

The vision half is a mature non-RF task. **OpenFACADES**, Liang, Xie, Zhao,
Stouffs, Biljecki (NUS), ISPRS J. Photogramm. Remote Sens. 230:918, 2025,
`10.1016/j.isprsjprs.2025.10.014`, links Mapillary street-level imagery to OSM
building geometry through isovist analysis and predicts attributes for 31,180
buildings across seven attributes including surface material. Flagship
photogrammetry journal, open, city scale, no RF. Its sub-literature includes Raghu
et al. 2023 on multi-city facade material categories from geotagged street-level
imagery. Further: material classification from Google Street View with Vision
Transformers for building energy models (`10.1016/j.enbuild.2025.115457`), facade
material classification (arXiv:2404.08557), cladding detection
(`10.1016/j.jobe.2024.110466`), and window-to-wall ratio from street view at urban
scale (`10.1007/s12273-025-1301-3`), which already splits one facade into window
against wall at city scale with different physics attached.

**The acoustic twin, five years early.** Colombo, Dolhasz, Harvey, "A Texture
Superpixel Approach to Semantic Material Classification for Acoustic Geometry
Tagging", CHI EA 2021, `10.1145/3411763.3451657`. An image classifier trained on
superpixel material patches runs on unwrapped mesh textures, predicts semantic
material labels, and maps them to measured frequency-dependent absorption
coefficients, with the most frequent label determining the acoustic material.
Validated by simulated against measured room impulse response in a
point-cloud-reconstructed room. Swap absorption for permittivity and majority
vote for posterior and it is the same skeleton. Related: SoundSpaces 2.0
(arXiv:2206.08312), GWA (`10.1145/3528233.3530731`),
`10.1109/CoG51982.2022.9893613`, Sonify Anything (arXiv:2508.01789).

---

# Question 2: adjoint and reciprocity-based site characterisation

This was the paper's central claim to novelty. **It does not survive as stated.
The trick was imported, not invented**, and the import path is documented end to
end with primary sources.

## The chain

1. **Adjoint Boltzmann transport**, neutron shielding, 1950s and 1960s. The
   adjoint transport equation and the importance function are textbook there. The
   MASH adjoint shielding code is the concrete artefact (`10.2172/5524813`).
2. **Tregenza and Waters 1983**, "Daylight coefficients", Lighting Research and
   Technology, `10.1177/096032718301500201`. The independent building-physics
   instantiation carrying the same amortisation argument: precompute a per-point
   coefficient against a discretised sky, then apply any sky luminance
   distribution afterwards. This is the Radiance `rfluxmtx` workflow, and it is
   forty-three years old.
3. **Veach 1997**, sections 3.7.3 and 4.6, the adjoint and importance formulation
   of light transport. Veach credits the neutron transport lineage in his own
   text and states the amortisation argument directly: "many different
   equilibrium importance functions (one for each sensor)".
4. **Precomputed radiance transfer**, Sloan, Kautz, Snyder, SIGGRAPH 2002,
   `10.1145/566570.566612`. The closest structural match, and it should be read
   that way. Primary-source confirmations from the full PDF: rays are cast
   outward from the point ("for each p in O, we cast shadow rays in the hemisphere
   about p's normal"), the glossy transfer is a **non-square two-directional
   matrix** (for example 25x9) mapping external incident-lighting coefficients to
   local transferred radiance, and sections 7 and 8 store transfer matrices at
   **free-space grid points**, not only on surfaces. That is `T_x(u_loc, u_ext)`
   minus delay, frequency and polarisation. It is unambiguously a **first
   moment**, a linear operator on radiance, with colour as three independent
   scalar dot products. No covariance anywhere in the PRT line.
5. **Polarisation added.** Mojzík, Škrivan, Wilkie, Křivánek, "Bi-Directional
   Polarised Light Transport", EGSR 2016, `10.2312/SRE.20161215`
   (**abstract-only**, Eurographics does not register with Crossref, confirmed
   real through Semantic Scholar, 19 citations): defines polarised visual
   importance, represented by a 4x4 matrix "similar to the Mueller matrices used
   to represent polarised surface reflectance". Then Yi, Kim, Na, Tong, Kim,
   "Spin-Weighted Spherical Harmonics for Polarized Light Transport", ACM TOG
   43(4), SIGGRAPH 2024, `10.1145/3658139`, builds explicit **precomputed
   polarized radiance transfer**, PRT-style per-point precomputation against
   distant environment illumination with 4x4 Mueller transforms.
6. **Sensor-side second moment.** Steinberg, Ramamoorthi, Bitterli, d'Eon, Yan,
   Pharr, "A Generalized Ray Formulation For Wave-Optical Light Transport", ACM
   TOG 43(6), SIGGRAPH Asia 2024, `10.1145/3687902`. Its abstract states that
   prior physical light transport "requires tracing light paths starting from the
   light sources, which is often less efficient than tracing them from the
   sensor". Graphics now does sensor-side tracing of a coherence second moment
   with polarisation. It does not precompute it, store it per point, or amortise
   it over sources.
7. **Source and receiver hardware substitution as the headline feature.**
   Chaitanya et al., "Directional sources and listeners in interactive sound
   propagation using reciprocal wave field coding", ACM TOG 2020,
   `10.1145/3386569.3392459`: reciprocal per-probe directional operators
   supporting "any tabulated source directivity function and HRTF". Raghuvanshi
   and Snyder 2018 report 10x to 100x amortisation. That is the acoustics version
   of "the antenna zoo problem disappears", already shipped.

**Consequence.** The paper may not claim reciprocity, source-independence,
hardware-independence, angular resolution, per-point precomputation, or
polarisation-completeness as contributions. Each has a counter-citation above.
Highest-risk omissions if left uncited, ranked: Chaitanya 2020, MASH adjoint
shielding, Yi 2024 PPRT, Tregenza and Waters 1983, and Hill 1998
(`10.1109/15.709418`, plane-wave integral representation for fields in
reverberation chambers).

## What survives in the adjoint frame

Three things were searched for hard and not found:

- **Delay resolved inside a precomputed per-point operator.** Transient rendering
  exists (Jarabo et al., SIGGRAPH Asia 2014, `10.1145/2661229.2661251`) but is a
  per-image path tracer with nothing precomputed or amortised. Nothing in
  graphics combines polarised, transient and precomputed per-point transfer.
- **The coherency second moment as a reusable per-point deliverable.** PRT stores
  a first moment. Steinberg computes a second moment and discards it per image.
- **Any of it in radio propagation.**

## The wireless side, and why it is emptier than expected

- **The double-directional channel model**, Steinbauer, Molisch, Bonek, IEEE AP
  Magazine 2001, `10.1109/74.951559`, 614 citations. The obvious threat, and it is
  not one. It removes the **antennas** from the channel description. It does not
  remove the transmitter **position**. A double-directional measurement is still a
  measurement of one transmitter-receiver pair.
- **Channel knowledge maps** are the closest active line, and they weaken the
  problem-framing claim rather than the solution. The 6D CKM work
  (arXiv:2510.26166, 2025) opens by noting that conventional 2D and 3D CKM
  approaches assume fixed base-station configurations, and generalises to
  arbitrary transmitter and receiver positions. So as of 2025 to 2026 the problem
  statement is not novel. Their solution is a learned 6D representation of the
  full operator, which is strictly more expensive than factorising it. See also
  the CKM survey, arXiv:2511.04944.
- **Digital twin channel and radio environment knowledge pool**, BUPT, IEEE
  COMMag 2025 (`10.1109/MCOM.003.2400168`) and arXiv:2312.10287. Constructs
  environment-to-channel relationships, but by learning them, with no analytic
  reciprocity factorisation and no angular operator.
- **Room electromagnetics** (`10.1109/TAP.2017.2702708` and the Andersen, Nielsen,
  Pedersen line) is a genuine transmitter-agnostic per-environment descriptor, but
  it is one scalar, the reverberation time, with no angular structure.

## The uncomfortable neighbours, found independently

These are not RF and not polarised, but "segment or ray trace from a point, build
a per-location angular transfer function, integrate it against a source
distribution later" is an established move in at least three neighbouring fields.
The paper should cite one of them and own the resemblance rather than be shown it.

**Elevation-dependent clutter loss for Earth-space links is the same object,
computed routinely, with the plane-wave assumption exact.** ITU-R P.2108 section
3.3 is the statistical version. The deterministic version is published: "Clutter
Loss Modeling for Urban Satellite Links via Calibrated Ray-Tracing Simulations at
1.57 GHz", WPMC 2025, `10.1109/WPMC67460.2025.11351215` (**abstract-only**), with
a physical-statistical lineage back to `10.1049/IP-MAP:19990144` (1999). A
per-location, angular, source-position-agnostic environment descriptor obtained by
ray tracing a 3D urban model, later combined with an actual constellation
geometry. It is a scalar version of `K_x(u_ext)` with the same factorisation
logic.

**GNSS shadow matching and 3D-mapping-aided GNSS** compute, per candidate
position, predicted sky visibility and reception as a function of satellite
direction independent of which satellite, then combine with the live
constellation. Groves 2013, `10.1002/NAVI.38`, 149 citations. Skymask matching
from fisheye cameras, `10.3390/s20174728`. **The zero-bounce term of `T_x` and
the "measured p_LOS" result in `DECISIONS.md` are, structurally, GNSS skymasks.**
An earlier revision wrote that term as `T_0`, which now collides with the tissue
power transmission coefficient in the paper's symbol table. Note
also that LOS probability from 3D building data is itself a crowded area
(`10.1109/TAP.2024.3513540`, `10.1109/TWC.2021.3075099`), so "measured p_LOS
against the 3GPP curve" is a thinner result than `DECISIONS.md` assumes. What is
new there is the source of the geometry, not the quantity.

**Urban solar radiation from street-view imagery** does the whole factorisation:
segment a Google Street View panorama, derive per-location angular sky
visibility, integrate against the sun's angular trajectory to get exposure at a
pedestrian point. `10.1016/J.BUILDENV.2018.10.025` (Building and Environment 2019,
107 citations), mean radiant temperature from GSV (`10.3390/rs14020260`), and the
sky view factor review (`10.1016/j.buildenv.2019.106497`, 142 citations). Urban
canopy radiative models go further and carry surface albedo with multiple
reflections, which is a material property, so the analogy is not only to the
zero-bounce term.

---

# Question 3: population exposure at mmWave from reconstructed environments

## The self-collision, which is the largest single risk in the paper

**Wydaeghe, Shikhantsov, Vermeeren, Martens, Tanghe, Joseph (2026)**, "Hybrid
ray-tracing-QuaDRiGa/FDTD method for realistic 28 GHz exposure with 6G CF-MaMIMO
in 3D outdoor environments", npj Wireless Technology,
`10.1038/s44459-026-00031-4`, verified 2026-04-02. **Abstract-only.**

Google Earth 3D photorealistic tiles for photogrammetry, "we semantically
classify the meshes with an SOTA deep learning model", ray tracing at 28 GHz,
QuaDRiGa small-scale fading, Huygens-box hybridisation, `S_ab` by FDTD on an
anatomical phantom along a pedestrian path, results as a percentage of ICNIRP,
case studies in Helsinki and New York City, users against non-users.

That is the photogrammetric twin, semantic material segmentation, FR2, ray
tracing, absorbed power density, ICNIRP framing and multiple cities. Six of eight
ingredients, in print, same first author.

What remains: it is a forward pipeline where a specific deployment is an input,
and absorption comes from brute-force FDTD per scenario, which is precisely what a
stored `D(k_hat)` and a source-independent `T_x` replace. No deployment
distribution, two cities not ten, no population weighting, no FR3, no street-view
panoramas. **Cite it prominently in the introduction and argue the delta there.**

**Leeman, Wydaeghe, Van Der Straeten, Goegebeur, Vermeeren, Joseph (2025)**,
IEEE Access 13:30894, `10.1109/ACCESS.2025.3541352`. **Full text read.** Ghent,
3.775 GHz, MATLAB SBR, OSM prismatic buildings on SRTM terrain, real base-station
positions from Flemish conformity certificates, agent-based pedestrian model
seeded from GHSL population density, MRT against ZF, 4x4 against 8x8.

Two things verified in the text that matter. It **deliberately destroys the
angular information**: equations 13 to 15 sum ray phasors assuming an isotropic
receive antenna with G = 1, then compare against the ICNIRP reference level of
10 W/m2 as a ratio. No body, no APD, no averaging area. And its conclusion
**pre-announces this study's scope verbatim**: "The exposure levels in different
countries, cities and environment types will be quantified and categorized.
Lastly, the model could be adapted to include next-generation networks such as 6G
with higher frequencies or different antenna technologies like distributed
MaMIMO."

It also writes this study's justification for it: "the lack of detail in the OSM
dataset cannot only lead to an inaccurate representation of diffuse scattering,
but also an underestimation of the channel diversity", and "the use of a single
material for all buildings may also lead to inaccuracies."

**Novelty cannot rest on multi-city or on higher frequency.** Both are on record
as this group's planned next step.

Also spent: `10.1109/ACCESS.2022.3227107` already claims "For the first time, the
absorbed power density is computed for distributed massive MIMO 6G base stations
at 28 GHz" (indoor). Companion accuracy anchors:
`10.1109/OJCOMS.2026.3695293` (RT fused with two years of sensors, RMSE 5.47 dB,
r = 0.70) and `10.1109/ACCESS.2026.3682896` (EIRP-based RT against IEC 62232
in-situ, median deviation 1.6 to 3.8 dB).

## Ten cities is taken

**Veludo et al. (2025)**, "Assessing RF-EMF exposure in multiple microenvironments
across ten European countries with a focus on 5G", Environment International,
`10.1016/j.envint.2025.109540`. GOLIAT consortium, which is the likely reviewer
pool. Over 800 microenvironments, ten countries, two cities and three villages in
each. The headline is already an urban-form-drives-exposure claim: levels on
average 80 percent lower in villages than cities on downlink, inverted on uplink
at plus 35 percent.

Gap: ExpoM-RF4 exposimeter, 87.5 MHz to 6 GHz, so no FR2 and no FR3.
Measurement-only, scalar E-field per band, no dosimetry, no APD, and critically a
measurement cannot be re-integrated against a hypothetical deployment.

Reinforcing: Van Bladel et al., `10.1016/j.scitotenv.2026.182037`, same
ten-country framing. Huang, Varsier, Wiart et al., `10.1002/bem.21990`, the
multi-area comparison already executed with the exposure index machinery.
Thielens, Davi, Hema, Toledo-Crow, `10.1016/j.envres.2026.125040`, New York City
across five boroughs, correlated against population density and foot traffic but
**not against geometry**, which is the gap the morphology angle fills. Lineage:
Sagar 2018 `10.1016/j.envint.2018.02.036`, Urbinello 2014
`10.1016/j.envint.2014.03.007`, Joseph 2010 `10.1016/j.envres.2010.06.009`.

**If the paper contains the sentence "no one has compared cities", that sentence
is dead.** Do not claim the comparison. Claim what is compared.

## The factorisation is LEXNET, and must be framed as its angular generalisation

Varsier, Plets, Corre, Vermeeren, Joseph, Aerts, Martens, Wiart, "A novel method
to assess human population exposure induced by a wireless cellular network",
Bioelectromagnetics 36:451, 2015, `10.1002/bem.21928`. Open at
biblio.ugent.be/publication/7047651. **Full text read.**

Raw-dose coefficients are `d_DL = TD_DL * SAR_DL / S_inc_ref`, a **precomputed
matrix of normalised SAR values computed once and reused**, while the
deployment-dependent `S_inc` comes separately from network planning tools and is
swapped per scenario. LEXNET even states the licensing assumption: "the usage
pattern of the user considered in the EI formula does not influence the average
incident power density."

So "characterise once, swap the deployment in later" is exactly LEXNET, on the
body side. Two independent readings of the 2014 companion initially concluded the
opposite, and both were wrong.

The honest delta is a three-way split against LEXNET's two-way:
[angular body response] x [environment tensor] x [deployment distribution],
against LEXNET's [scalar body coefficient] x [scalar environment-and-deployment
term]. Both the angular resolution and the environment-from-deployment separation
are new. LEXNET's environment index is a two-valued indoor-outdoor time-budget
weight carrying no propagation physics, and its demonstration is one deployment
(hexagonal macro, 450 m ISD, LTE 2600 MHz, Paris 7th, through SIRADEL VOLCANO).
**Frame the tensor as the angular generalisation of the LEXNET `d_DL`
coefficient.** Anything vaguer reads as the exposure index restated.

## Deployment integration is well occupied

**Wiame, Demey, Vandendorpe, De Doncker, Oestges (2023)**, "Joint Data Rate and
EMF Exposure Analysis in Manhattan Environments: Stochastic Geometry and Ray
Tracing Approaches", IEEE TVT, `10.1109/TVT.2023.3307226`, arXiv:2301.11097. The
strongest external item here. Computes the same exposure metrics twice, once by
integrating over a Manhattan Poisson line process of base stations and once by
deterministic ray tracing in the same geometry, and shows they agree. That is the
existing bridge between ray tracing a city and integrating over a base-station
distribution. It also models corner diffraction. Gap: scalar received power, the
angular information discarded before dosimetry, no body, sub-6, synthetic
Manhattan.

Around it: Gontier et al. `10.1109/ACCESS.2021.3091804`,
`10.1109/TWC.2024.3400612` (real operator deployments),
`10.1109/TVT.2025.3554964` (densification and optimal node densities). Chen,
Elzanaty, Kishk et al. `10.1109/TWC.2023.3244155`. Muhammad et al.
`10.1109/ACCESS.2021.3103969` is the mmWave one, analytic incident power density
coverage probability for an mmWave tier against regulation. EMF-aware planning:
`10.1109/ACCESS.2023.3297098` (survey, cite it or the related work looks unread),
`10.1109/TMC.2021.3054482`, `10.1109/TVT.2015.2487038` (the canonical
"densification reduces exposure").

## The angular primitive is in ICNIRP 2020 itself

This changes how the angular claim must be worded, and it is the most important
framing correction in this document.

ICNIRP 2020, Health Phys 118(5):483, `10.1097/HP.0000000000001210`, equations 29
and 30, verbatim: the reflection coefficient "is derived from the dielectric
properties of the tissues, shape of the body surface, **incident angle and
polarization**", TE peaks at normal incidence and TM at the Brewster angle, then
"normal incidence is always the worst case scenario regarding temperature rise
(Li et al. 2019)", and the reference levels are derived on that basis.
Multi-source summation is frequency-wise and explicitly assumes worst-case
conditions among sources, so it is direction-blind by construction.

The guidelines therefore already contain an angle- and polarisation-dependent
transmittance and **deliberately replace the angular integral with its worst-case
bound**. The defensible framing is exactly that: the standards substitute normal
incidence for the angular integral, and here is what the actual integral gives for
a non-planar self-shadowing body against a real environmental angular spectrum.
Framed as "nobody has considered incidence angle", a referee with ICNIRP open ends
it in one line. The load-bearing citation behind ICNIRP's claim is Li, Sasaki,
Watanabe, Shirai, `10.1088/1361-6560/ab057a`.

Two more that must be engaged rather than discovered:

- **Diao, Li, Sasaki, Kodera, Laakso, El Hajj, Hirata (2021)**, IEEE TEMC,
  `10.1109/TEMC.2021.3098594`. Compares peak spatial-average of `n_hat . Re{S}`
  against peak spatial-average of `|S|` as a function of incidence angle, with
  Brewster enhancement for TM at large angles. **Picking a Poynting projection
  without engaging this is a first-round referee comment**, and it is the same
  trap already logged against the GOLIAT SAPD extraction.
- **Morimoto and Hirata (2022)**, `10.1088/1361-6560/ac994d`. Square against
  circular 4 cm2 averaging areas, and the note that 63195-1 and -2 recommend
  circular only for non-planar surfaces, with square not always conservative below
  5 mm and at or below 15 GHz.

## The body-side factorisation structure is a Ghent invention from 2008

Vermeeren, Joseph, Olivier, Martens, `10.1097/01.HP.0000298816.66888.05` (2008).
Vermeeren, Joseph, Martens, `10.1002/bem.21762` (2012). Thielens, Vermeeren,
Joseph, Martens, `10.1002/bem.21799` (2013), which precomputes per-direction FDTD
responses with two interpolation schemes (vectorial cell-wise under 1.8 percent
error), gives CDFs across five environments, and finds that no single worst-case
polarisation holds across organs. Conil, Hadjem, Gati, Wong, Wiart,
`10.1109/TEMC.2010.2061849` (2010), sweeps incidence in 10 degree steps over full
azimuth and elevation, which is a tabulated `D(k_hat)` at 2100 MHz. Kientega,
Conil, Wiart et al., `10.1007/s12243-011-0261-z`.

**"Precompute the body response per incident direction, get the angular
distribution from a channel model, superpose" is not new.** Two investigators
independently walked the forward citation graphs of the Vermeeren papers, roughly
fifty citing works each, and found no mmWave or APD descendant. The lift to
FR2 and FR3 with APD, where absorption becomes superficial and `D(k_hat)` becomes
a local surface property with self-shadowing rather than a global volume integral,
is open. **Claim the extension, never the invention.**

Free win available: the angle-averaged absorption cross-section lineage (Flintoft
et al. `10.1088/0031-9155/59/13/3297`, Melia et al. `10.1109/TEMC.2013.2248735`,
Bamba et al. `10.1088/0031-9155/59/23/7435`) assumes an isotropic diffuse spectrum
and reports one scalar. **Show the formalism reduces to ACS as rho goes
isotropic.** It is cheap and it converts the most established body of work in the
area from a threat into a validation.

## What the standards do and do not do

No standard defines an angular-combination rule for absorbed power density.
Verbatim scopes obtained:

- **IEC/IEEE 63195-1 and -2:2022** (`10.1109/IEEESTD.2022.9770427` and
  `10.1109/IEEESTD.2022.9770556`): power density incident to a head or body from
  devices "with their radiating part or parts at distances up to 200 mm".
  Near-field, single-device, 6 to 300 GHz. The only combination contemplated is
  across multiple transmitters of one device, not across incident directions.
  Structurally incapable of being the angular prior art.
- **IEC 62232** (2017, 2022 withdrawn 2025-04-29, and 2025). Combination is
  source-wise and scalar. The actual-maximum and power-reduction-factor machinery
  handles time-varying beams statistically. No angular weighting.
- **IEC TR 62669:2019**: case studies against 62232:2017, nothing angular.
- Transmitter-side half of the angular story: Xu, Anguiano Sanjurjo, Colombi,
  Törnevik (Ericsson), `10.3389/fpubh.2021.777759`, Monte Carlo over beam pointing
  directions at mmWave for power reduction factors. No body, no environment.

## What is open on the exposure side

1. No transmitter-agnostic **angular** transfer object stored per location and
   contracted against a deployment distribution afterwards.
2. No composition of a body-side absorption directivity with an environment-side
   angular power spectrum for APD. Nearest neighbours are single-plane-wave
   oblique-incidence studies (Diao 2021, Li and Sasaki
   `10.3389/fpubh.2022.795414`, Kapetanović `10.1109/JERM.2022.3225380`).
3. **No FR3 population exposure study of any kind.** "FR3 exposure" returns
   literally nothing on Semantic Scholar. Nearest is Rybakowski et al., MIKON
   2024, `10.23919/MIKON60251.2024.10633966`, about 10 GHz, single
   extreme-massive-MIMO base station, **abstract-only**. The cleanest open claim
   in the paper. Caveat: HoRAMA validates material assignment at 6.75 and
   16.95 GHz, so FR3 itself is not untouched, only FR3 exposure.
4. **No link between sky view factor, or any named urban-form metric, and RF
   propagation or exposure.** Four search systems, exact phrase. `"sky view
   factor"` with RF terms returned four hits, all GNSS or LoRa or lidar. `"urban
   morphology"` with RF-EMF returned zero. `"local climate zone"` with RF returned
   nothing relevant. The machinery is mature (Hu, Zhang, Gong, Ratti,
   `10.1016/j.buildenv.2019.106424`, 132 citations) and points only at solar,
   thermal comfort and heat island. **This negative rests on title and abstract
   coverage only.** Nearest port is Kaneko et al., ICOIN 2026,
   `10.1109/ICOIN68469.2026.11480554`, 360-degree sky imagery predicting Starlink
   link availability, title-only.

Nearest ancestor of "morphology explains propagation spread": Simić, Riihijärvi,
Mähönen, DySPAN 2015, `10.1109/DySPAN.2015.7343920`, "Can statistical propagation
models be saved by real 3D city data? A regionalized study of radio coverage in
New York City".

Expect one review comment regardless: the same move has been made for road
traffic **noise** across European cities from imagery through semantic
segmentation (Sharma, Jetschny, Maza 2026, `10.1007/978-3-032-31144-3_31`). The
defence is the angular tensor and body absorption, which have no counterpart in
noise.

---

# Question 4: the honest negatives

## 4.1 The diffraction self-diagnosis is wrong, in the direction that hurts

`MONOSTATIC_SBR.md` sections 9.3 and 14 **used to** call diffraction "the largest
known physical omission", landing on "exactly the elevation band the
rooftop-illumination scalar needs". **Four independent lines say that is false at
28 GHz, and the paper was defending the wrong flank.**

**Status: actioned.** That document's decision table, section 2.7, section 9.3
and section 14 now carry the ranking and the bound below, and diffraction has
been demoted from first to fifth in its weakness list. This section is kept as
the evidence, not as an outstanding complaint.

**The measured answer.** Charbonnier, Lai, Tenoux, Caudill, Gougeon, Senic,
Gentile, **Corre**, Chuang, Golmie (NIST and Siradel), "Calibration of
Ray-Tracing With Diffuse Scattering Against 28-GHz Directional Urban Channel
Measurements", IEEE TVT 2020, `10.1109/TVT.2020.3038620`. An earlier revision of
this document dropped Corre from the list. `ROUGHNESS.md` has it from the full
NIST-hosted PDF, and the ten-author form is the one to cite. Verbatim: "while most papers on
millimeter-wave ray-tracing do not even consider diffuse scattering, it accounted
for **20% of the total received power**, whereas **diffraction accounted for less
than 1%**." 28 GHz, directional sounder, urban, super-resolution MPC extraction,
488 acquisitions. **This is the strongest single citation in this report.** It
justifies the omission and indicts the priority ordering at the same time.

**The theoretical answer, triangulated three ways.** Chizhik, Du, Feick, Castro,
Rodríguez, Valenzuela (Nokia Bell Labs), IEEE TAP 2021,
`10.1109/TAP.2020.3044398`, arXiv:1908.00512: over 3000 links and 21 million power
samples in Manhattan and Valparaíso at 28 GHz from rooftop sites at 15 to 51 m,
receiver at 1.5 m. "the theoretical edge diffraction coefficient, which at large
diffraction angles (deep shadow) is on the order of **-42 dB at 28 GHz**." The
60 GHz companion (`10.1038/s41598-026-41462-x`) gives 46 dB. An independent
ITU-R P.526-15 knife-edge computation for Ghent geometry (eaves 12 to 20 m, head
1.7 m, pedestrian 2 to 12 m from the facade) returned 43 to 48 dB across the whole
low-elevation band. The frequency scaling closes too: knife-edge shadow loss goes
as 10 log10 f, so 42 dB at 28 GHz predicts 45.3 dB at 60 GHz against a published
46 dB.

Scaled from that anchor: 2 GHz -30.5, 6.75 GHz -35.8, 10 GHz -37.5, 16.95 GHz
-39.8, 28 GHz -42.0 dB. **FR3 is only 4.5 dB more diffractive than 28 GHz.** It is
not a different regime. An independent ITU-R P.1411 Xia-Bertoni computation agrees:
excess over free space from the full rooftop chain moves only 1.1 dB between 7.5
and 28 GHz.

**The geometry argument, which reverses section 9.3 outright.** Rooftop-diffracted
power arrives from the edge directly above the near facade, so at a head at 1.7 m
the arrival elevation is 35 to 86 degrees depending on eaves height and standoff.
That is the top of the 3 to 60 degree band or above it entirely. The
`1/sin^3(alpha)` weight at 60 degrees is 0.001 times its value at 5 degrees. **Adding
UTD would deposit power exactly where the study's own weight suppresses it by
three orders of magnitude.** Section 9.3 conflates the link with the local tensor:
the over-rooftop multiscreen transport a macrocell link needs is upstream of `K_x`
and factored out by construction. What `K_x` must capture is only the last edge.

**And the power-integral error is unmeasurable.** With blocked directions carrying
-45 dB, the error from omitting diffraction is 0.000 dB at open-azimuth fraction
0.30, 0.003 dB at 0.05, 0.014 dB at 0.01 and 0.135 dB at 0.001. Reaching 1 dB
needs an open fraction below 0.012 percent of azimuth. Korenmarkt's measured sky
fraction is 0.2271, the `sky_fraction_mean` over 32 fixed observers in
`outputs/crop_convergence/korenmarkt_crop_convergence.json` at 120 m and 200 m.
The 80 and 120 standpoint exposure runs give 0.229 to 0.247 for the same site, so
the argument holds on any of them. The UTD transition region, the one place
geometrical optics is
genuinely discontinuous, has half-width sqrt(lambda*s/2) = 28 cm at 28 GHz for
s = 15 m against 106 cm at 2 GHz, roughly 1.9 percent of directions at a
worst-case 6 dB, so about 0.06 dB of bias on `K_iso`.

**Recommendation, now carried out.** Section 9.3's qualitative worry has been
replaced with this quantitative bound, and the recommendation to publish
`f_open(alpha)`, the low-elevation open-azimuth fraction, per location as the
validity flag went in with it. That converts a confessed hole into a scoped and
defended decision, and it is a stronger paper for it.

**Still open, and it now blocks two documents rather than one.** Nothing in this
repository computes `f_open`. `DEPLOYMENT_GEOMETRY.md` section 6 carries a
per-site `f_open` table and sections 7.3 and 7.5 build the whole range-cap
leverage argument on it, all computed once by hand with no script behind them.
Until `f_open` is library code with a test on it, neither the validity flag here
nor the sensitivity band there can be regenerated.

**The genuine exceptions, stated plainly.** The parapet case is unambiguous:
Chizhik measures that moving the base station 5 m back from the roof edge costs
over 15 dB of extra average loss at under 100 m, with total excess over free space
25 to 50 dB, and the 60 GHz companion reproduces parapet blockage to 3.1 dB RMSE
with pure knife-edge theory and no empirical correction. If any assumed
transmitter sites sit behind parapets, a diffraction-free tracer predicts a hard
zero where measurement shows usable signal. Separately, Koivumäki, Steinböck,
Haneda, IEEE TAP 2021, `10.1109/TAP.2021.3050482`, at 28 GHz outdoor: the
processed point cloud reproduces "many weak diffracted paths that are found in
measurements and cannot be reproduced by diffuse scattering". **The Rayleigh split
is not a substitute for the diffracted field.**

No paper was found reporting "RMSE grows from X to Y dB when diffraction is
disabled" in urban mmWave. Do not claim such a study exists.

**Do not extrapolate COST 231 Walfisch-Ikegami above 2 GHz.** Its
`k_f = -4 + 1.5(f/925 - 1)` is linear in f, and at 28 GHz returns `k_f = +39.9`
and a total path loss of 348 dB. That is a fitting artefact. Use ITU-R P.1411-13
equation 41 with the flat `k_f = -8` for f above 2 GHz. Note also that the
classical models say the `f^0.9` Xia-Bertoni term makes multiscreen loss **fall**
by 9 dB per decade, so rooftop-to-rooftop propagation is more efficient at
millimetre wave. Anyone claiming the classical lineage supports dropping
diffraction at 28 GHz has not read it.

**Two factual corrections needed in `MONOSTATIC_SBR.md` section 10.** Sionna RT
diffraction was added in 0.15.0, removed in 1.0.0, restored in 1.2.0, and is
present in 2.0.1 as Kouyoumjian-Pathak UTD with the Luebbers finitely-conducting
heuristic, first order but supporting R...R.D.R...R chains in the path solver,
with the `diffraction` and `edge_diffraction` flags defaulting to False (so most
published Sionna results silently run without it). Sionna's diffraction has no
measurement validation found anywhere, only a shadow-boundary continuity notebook.
And MATLAB's `Method="sbr"` does second-order UTD while its image method does
none, which is the opposite of the usual assumption and kills any "SBR
architecturally cannot diffract" argument.

Where this method sits: behind everything. Sionna RT 2.0.1, MATLAB SBR, Remcom
X3D, Altair WinProp (heuristic UTD plus slope diffraction for over-rooftop), Ansys
Perceive EM (physical optics plus edge currents, explicitly not GTD), the Bologna
tracer (UTD plus vertex diffraction plus double-bounce diffraction,
`10.1109/ojap.2026.3717211`) and DiffeRT (Eertmans, arXiv:2510.16172, Fermat
principle with arbitrary reflection-diffraction sequences) all model it. This one
does not.

The "photogrammetric meshes make diffraction impossible" defence is partial and
was solved five years ago. Sionna applies no dihedral-angle or coplanarity filter
to wedges (`utils/wedges.py` uses Mitsuba's `primitive_silhouette_projection` with
only exterior-side and distinct-primitive tests), so triangle soup does yield
diffraction sources on tessellation artefacts, and Koivumäki measured that raw
point clouds produce spurious paths. But Koivumäki also solved wedge extraction on
unstructured survey geometry. So the honest wording is "unreliable without a
preprocessing stage we did not build", not "impossible". And Koivumäki's gift is
worth taking: "For condensed parameters of channels such as path loss, delay, and
angular spreads, ray tracing with the processed and raw point clouds shows equally
good accuracy." The outputs here are condensed parameters.

## 4.2 The real largest hole is the crop radius

Section 2.7 supports the rooftop weight on `h` in [13.5, 43.5] m above head and
`r` in [25, 250] m. The scene is cropped at 130 m. The fraction of the
`cos/sin^3` measure lying at elevations that require sources outside the crop is
27.5 percent for `h` = 8 m, 79.4 percent at 15 m, 88.5 percent at 20 m and
94.9 percent at 30 m.

⚠️ **Those four are superseded.** They were computed under the uncorrected
elevation law, `MONOSTATIC_SBR.md` section 2.7.1, and have not been remeasured.
The argument that the 130 m crop cannot hold the model's own source support is
unaffected by the correction, since the corrected law puts *less* weight at low
elevation, not more.

An earlier revision added that "sixty-four percent of the pure geometric weight
sits below 5 degrees and 89 percent below 9 degrees". **Neither figure is
reproducible from the support the code ever ran.** The superseded law on
[3.1, 60.1] deg gives **61.74 percent below 5 degrees and 88.39 percent below
9 degrees**; 64.18 percent needs a 3.0 degree lower edge that no version used.
Under the shipping corrected law the same two figures are 9.41 percent and
45.19 percent, which is the whole point of the correction. **The weight's stated
support and the crop radius contradict each other** either way, and
`MONOSTATIC_SBR.md` section 7.5 already measured that the crop has not converged.

This is about source placement, not scatterers. Scatterer truncation beyond 130 m
is worth only -19 to -41 dB, under 0.05 dB of error, from ITU-R P.1411-13 Table 11
measured 28 GHz NLOS delay spreads (74.5 ns median, 22 m excess path) and 3GPP
38.901 UMi-SC NLOS at 28 GHz (65.9 ns, 19.8 m). So the crop is fine for scatterers
and fatal for the low-elevation source weight. Note also that atmospheric
absorption cannot be used to justify truncation: ITU-R P.676-13 gives about
0.1 dB/km at 28 GHz, so 0.026 dB over 260 m.

**Status: actioned, and it grew a third leg.** `MONOSTATIC_SBR.md` now has a
section 9.4 carrying this argument, and its decision table and weakness list rank
the crop first. Writing it up surfaced that three different crop questions were
being run together, and only two of them are covered above. Scattered power is
bounded small, as this section says. Source support is broken, as this section
says. But `MONOSTATIC_SBR.md` section 7.5's own measurement is about neither: it
is about
**occlusion**, and under the adjoint `R^0` law a distant blocker changes `K_x(u)`
in that direction at full per-direction strength, which is why directions beyond
90 m carry -28.4 dB of the isotropic weight and that figure is still growing with
radius against a 30 dB budget. The delay-spread bound above does not retire that
one. The three compound rather than cancel.

## 4.3 Three novelty claims already in print

**The microfacet BRDF for radio propagation.** J.-F. Wagen, "Diffuse Scattering
and Specular Reflection from Facets of Arbitrary Size and Roughness using the
Computer Graphics GGX Model", ISNCC 2020, `10.1109/ISNCC49221.2020.9297355`.
**Abstract-only.** Abstract: "the **reciprocal, energy conserving** Walter et
al.'s GGX directional factor is proposed to complement the usual scattering and
reflection models for radio propagation. A single formulation ... spanning from
the specular reflection from a large smooth surface to the Lambertian scattering
from a very rough surface." GGX is a D/G/F microfacet BRDF. Swapping
Trowbridge-Reitz for Beckmann is a parameter choice inside the same framework, and
he already claimed reciprocity and energy conservation.

**"The Degli-Esposti directive model is non-reciprocal."** His own group said it
first and already fixed it. Vitucci, Cenni, Fuschini, Degli-Esposti, "A Reciprocal
Heuristic Model for Diffuse Scattering From Walls and Surfaces", IEEE TAP 2023,
`10.1109/TAP.2023.3278796`, arXiv:2209.12685: "the ER model, with the exception of
its Lambertian version, does not satisfy reciprocity, which is an important
physical-soundness requirement." Their section I explicitly considers and rejects
the microfacet route, citing Wagen, because "such models do not distinguish
specular from diffuse reflection and therefore cannot be easily implemented into
existing ray-based propagation models". Their Fig. 8 benchmarks GGX directly and
finds it does not go to zero at grazing scattering angles, **which is where the
rooftop weight lives**. RER reaches 1.59 dB RMSE against legacy ER's 1.85 dB.

Their strongest physical objection to Beckmann-Gaussian microfacets: to match the
Kirchhoff lobe for a brick **wall** at sigma_h = 1 cm and l_corr = 0.5 m, RER
needs alpha_R = 65, whereas the measured brick wall fits alpha_R = 4, because
real scattering comes from indentations, brick and mortar alternation and
sub-surface inhomogeneity rather than Gaussian surface roughness. That
centimetre is a wall statistic, not a brick face, and section 4.6.4 says why the
distinction has to be carried every time the number is quoted. Follow-on:
Melloni, Vitucci, Degli-Esposti, Berweger, Chuang, Gentile, Golmie,
arXiv:2605.17988 (2026), a directive and reciprocal ER model, which also supplies
the number "diffuse scattering can account for up to 40% of the received power"
at mmWave and sub-THz. Section 4.6.5 explains why that 40 % must not be quoted
alongside Charbonnier's measured 20 % as if the two disagreed.

**What survives:** the Rayleigh specular-diffuse split is a direct answer to
Vitucci's stated objection that microfacet models do not distinguish specular
from diffuse. Frame it as answering a published objection, cite the objection,
and benchmark against both RER and Wagen's GGX, or reviewers will. Two
qualifications, both from section 4.6. The split is the right model only for the
random-roughness classes, and Vitucci's own alpha_R = 65 against alpha_R = 4 is
the first of two independent demonstrations that facade diffuse power is
structural rather than Gaussian, which cuts against any framing that leans on the
split as a *complete* answer.

**Materials from imagery.** Question 1 above.

## 4.4 The 27 percent unseen material figure is not fatal, but it is stated wrongly

Fresnel reflectivity spread computed from `config/itu_p2040_4.json` at 28 GHz,
unpolarised, averaged over incidence with weight `cos(theta) dtheta`: concrete
-7.50, brick -8.70, glass -6.86, marble -6.49, plasterboard -10.48, chipboard
-10.78, wood -12.52, **metal -0.01 dB**. Masonry plus stone plus glass, which is
a European medieval core, spans **2.21 dB in total**. Concrete-prior against
glass-truth is -0.64 dB, so the confusion everyone worries about is the smallest
one in the table. Every P.2040 building material has b = 0, so the real part is
frequency-flat and **FR3 inherits the identical bound**: the same four materials
span 2.206 dB at 10 GHz against 2.207 dB at 28 GHz. That is a clean one-line
claim. Recomputed and confirmed 2026-08-02, all eight to the stated precision.
Quote the weight when quoting the numbers: a `cos(theta) sin(theta)` weight,
which is the other natural reading of "cosine-weighted", moves every entry by up
to 1.5 dB and shrinks the span to 1.82 dB.

Monte Carlo over a European-core truth distribution with a concrete prior,
4x10^5 draws, at the stated 27 percent unknown fraction: +0.08 ± 0.96 dB at order
1, +0.17 ± 1.37 at order 2, **+0.25 ± 1.68 dB at order 3**. Bias grows linearly in
bounce order and spread only as sqrt(n).

Published corroboration:

- **Cazzella et al., arXiv:2507.19173.** Milan, Sionna RT, 28 GHz. Changing only
  window material from concrete to glass gave max Hausdorff 2.42 dB and mean
  Chamfer 0.20 dB, with no change in ray delays or angles. **Worst-per-ray to
  aggregate-mean is a factor of 12 to 20**, which is the angular-integral
  cancellation, measured, on a real city. In the same paper, adding parked-vehicle
  meshes gave mean Hausdorff around 16 dB, so **geometry beats material by roughly
  20x**.
- **Hoydis et al., `10.1109/TMLCN.2024.3474639`.** Absolute log error on channel
  gain: 4.93 dB with ITU book materials, 2.16 dB learned, 1.00 dB neural. Their
  own caveat is that calibration also absorbs geometry and measurement error, so
  4.93 is an upper bound on the material-only term.
- **Kanhere and Rappaport, arXiv:2302.12380**: a fully calibrated mmWave tracer
  still has 2 to 3 dB residual standard deviation on directional path power. The
  prior cannot dominate that floor.
- **Possenti, Barbiroli, Vitucci, Fuschini, Fosci, Degli-Esposti,
  arXiv:2210.06883**: outdoor mmWave with measured materials, 4.7 dB RMSE at
  27 GHz and 3.6 dB at 38 GHz. Adding 1.7 dB in quadrature gives 5.0 dB and does
  not change the character of the result.
- **Roughness is nearly free, on the smaller of the two available height sets.**
  Guo, Zhang, Sun, Tao, **Gao**, arXiv:2502.00699, IEEE WCNC Wkshps 2025,
  `10.1109/WCNC61545.2025.10978814`: h_rms 0.170 mm (metal sheet), 0.216 (marble
  wall), 0.445 (smooth wall), 0.715 (rough wall), all sub-Rayleigh at 28 GHz
  (threshold 1.89 mm at 45 degrees). A 2x error in sigma_h costs 0.35 to 3.5 dB at
  28 GHz and 0.02 to 0.19 dB at 10 GHz. **Two corrections to how an earlier
  revision of this bullet described the source.** It was cited as "measured real
  facades", and it is not: the 28 GHz *scattering* was measured, the h_rms values
  were not, and the paper never states where Table I came from. There is no
  profilometer, laser, stylus or scan anywhere in it, and h_rms is used as an
  *input* that seeds the initial scattering coefficient before `S`, `alpha_R`,
  `alpha_i` and `Lambda` are tuned to minimise FVU in Wireless InSite. The
  giveaway is that the same table assigns a relative permittivity of 6.0 to a
  *metal sheet*, which is not a measurable dielectric constant. Read Table I as
  nominal simulator inputs. Second, the author list drops Ruifeng Gao. Caution
  that stands: their in-plane-only fit mispredicts out-of-plane backscatter, so if
  the output is a sphere integral, the in-plane-fitted `S` values in the
  literature are the wrong ones. This set turns out to be the same three walls as
  the set `ROUGHNESS.md` quarantines, which is section 4.6.3.

Two reframings that make the paper stronger. **Stop leading with 3.1 percent
surface visibility.** Area coverage is not the relevant number, power-weighted
interaction coverage is, and the study already has it: lead with "73 percent of
order-3 interaction vertices carry image evidence", and note the 27 percent
residual costs 1.7 dB of spread because the plausible-material set for a European
core spans only 2.21 dB. And **the one genuine vulnerability is metal**, the only
P.2040 material sitting 7.5 dB off the masonry cluster, where a metal-clad facade
misread as concrete under-predicts exposure one-sidedly and does not average out.
Cheapest high-value experiment: re-run with all unseen surfaces forced to metal
and report the shift. Expect 2 to 3 dB. It forecloses the referee's best question.

## 4.5 The threat nobody in this study is defending: 2 m geometry error

**OpenGERT**, `10.1109/DySPAN64764.2025.11115956`, **abstract-only on the
per-metre slopes**: "small changes in permittivity and conductivity minimally
affect channel statistics" while "variations in building height and position
significantly alter all statistics, even with noise standard deviations of
1 meter in height and 0.4 meters in position". The support mesh here has 2 m
geometric error, which is 2x and 5x beyond the scales they found already dominate.
Section 4.4's counter-argument (their perturbation is 10 percent around a correct
value, at 3.5 GHz) blunts the material half of their finding but not the geometry
half, which is the half that hurts.

Related: Lu, Cao, Yi, Salehi-Abari, "mmDiff", arXiv:2605.26406, at 28 GHz on
reconstructed geometry improves Sionna specular from 15.11 dB MAE to 4.60 dB using
a cosine-power angular lobe explicitly designed to absorb reconstruction noise. **If
the argument for a microfacet BRDF on photogrammetry is "the lobe absorbs
registration error", mmDiff owns that argument at 28 GHz.** The reciprocity angle
survives, since mmDiff makes no such claim.

A referee will ask why materials are being calibrated on a mesh whose geometry
error is the larger term. The honest answer is probably that an angular second
moment is more geometry-tolerant than a delay or power statistic, which is exactly
what Cazzella's 12 to 20x Hausdorff-to-Chamfer ratio supports. It has to be
demonstrated, not asserted.

## 4.6 The roughness position, reconciled against `ROUGHNESS.md`

This document and `ROUGHNESS.md` were written by different passes that did not
read each other, and they collided on the one thing both treat as load-bearing.
This section is the reconciled position. Where the two disagreed on a number, the
number was checked against the source or against
`config/surface_roughness.json`, and the loser is named.

### 4.6.1 The Rayleigh split survives, at half its advertised width

Sections 4.3 and the claim list below sell the Rayleigh specular-diffuse split as
the surviving physics differentiator, on the grounds that it answers Vitucci's
published objection that microfacet models cannot separate specular from diffuse.
That framing is correct and it should stay. But `ROUGHNESS.md` establishes that
the split is **the wrong model for eight of the sixteen classes** in
`config/surface_roughness.json`, and the code enforces that:
`SurfaceRoughnessPrior.specular_power_fraction` raises for any class whose
`structure` is `periodic_dominant` or `two_scale_periodic_plus_random` unless the
caller passes `allow_periodic=True`.

The two positions are not in conflict once the scope is stated. **The Rayleigh
split applies to the random-roughness classes. Periodic structure needs its own
treatment, and that treatment is being built rather than shipped**
(`semantic_twin/floquet.py`, `masonry.py`, `rcwa.py` and `kirchhoff.py` exist,
and nothing in the propagation path imports them yet). Concretely:

- Gaussian-random and therefore inside the split: `glass_glazing_unit`,
  `metal_cladding_panel_smooth`, `render_plaster_painted`,
  `concrete_as_cast_smooth`, `concrete_board_marked_or_exposed_aggregate`,
  `brick_face`, `asphalt_road_dense_graded`, `asphalt_road_coarse`.
- Periodic or two-scale and therefore outside it:
  `brick_wall_with_mortar_joints`, `stone_ashlar_dressed`,
  `stone_rough_rusticated`, `wood_cladding`, `metal_profiled_sheet`,
  `ceramic_tile_facade`, `concrete_paving_slab`, `stone_sett_paving`.

A mortar grid at 75 mm pitch supports 15 propagating orders at 28 GHz and 31 at
60 GHz, arriving at computable angles, so a smooth Gaussian lobe gets both the
magnitude and the angular distribution wrong. That is not a caveat to bury. It is
half the facade area in a European core.

What to write in the paper: claim the split for the random-roughness classes and
name the periodic ones as an explicit open item with a stated refusal in the
code. Claiming the split across the board invites the reviewer to find the eight
classes, and `ROUGHNESS.md` will be the document that finds it for them.

Note also, against claim 8 in the list below, that the Rayleigh split and the
roughness prior are separable claims. The prior distribution per semantic class
is unoccupied regardless of which scattering closure consumes it.

### 4.6.2 The strongest result in the pair, reached twice from disjoint sources

This is the finding that should be stated once, prominently, in the paper.

**Facade diffuse power at millimetre wave is structural, not Gaussian
micro-roughness.** Two independent literature passes reached that conclusion from
sources that do not overlap, and neither knew the other had.

From this document's strand, Vitucci, Cenni, Fuschini, Degli-Esposti, IEEE TAP
2023, `10.1109/TAP.2023.3278796`, arXiv:2209.12685: to match the Kirchhoff lobe
for a brick wall, their reciprocal effective-roughness model needs
`alpha_R = 65`, whereas the measured brick wall fits `alpha_R = 4`, because real
scattering comes from indentations, brick and mortar alternation and sub-surface
inhomogeneity rather than from Gaussian surface roughness.

From `ROUGHNESS.md`'s strand, four separate results:

- Kodra, Bernardi, Cenni, Hu, Barbiroli, Fuschini, Vitucci, Molina Garcia-Pardo,
  Martinez-Ingles, Salous, Degli-Esposti, IEEE OJAP 6(5):1490-1501, 2025,
  `10.1109/OJAP.2025.3587403`, on their own flat laboratory slabs: "The main
  origin of diffuse scattering in the considered cases cannot be surface
  roughness since all three materials have similar, smooth surfaces." Their
  fitted `S` falls with frequency for wood flooring and rises for plasterboard,
  which no RMS height can produce.
- Pascual-Garcia et al., IEEE Access 4:690-701, 2016,
  `10.1109/ACCESS.2016.2526600`, the only paper that measures metrology and fits
  `S` on the *same* physical samples: measured micro-roughness under-predicts the
  observed diffuse scattering by roughly an order of magnitude in amplitude and
  two in power, consistently, on every one of five samples.
- Landron, Feuerstein, Rappaport, IEEE TAP 44(3), 1996, Table I: real exterior
  walls characterised at 50 to 250 times the coupon values, a rough limestone
  wall at 2.5 cm RMS and a brick wall at 0.5 cm.
- Koivumaki et al. fitted whole facades at 28 GHz and found the Lambertian
  pattern beat the directive one, because pillars, protruding windows and street
  furniture returned as much backscatter as forward scatter.

Same conclusion, from Vitucci on one side and Kodra, Pascual-Garcia and Landron
on the other. Independent corroboration across two literature passes is the
strongest thing either document contains, and it is more publishable than either
document's separate contribution. It also has a direct architectural consequence:
if the diffuse fraction is set by structure rather than finish, it arrives in a
comb of grating orders at angles the semantic layer can already estimate from
course pitch, which a random roughness parameter can never predict.

The one honest hedge, which `ROUGHNESS.md` states and this document endorses: no
published experiment separates a comb from a smooth lobe on a real facade,
because every mmWave campaign uses either a jointless coupon or a whole building
with no angular resolution on a single patch. The measurement that would close it
is a bistatic scan at 28 GHz across one square metre of real brickwork at fixed
incidence. Until it exists, "structural" is very strongly indicated and not
proven.

### 4.6.3 The two RMS height sets are the same three walls, and that is a result

`ROUGHNESS.md` quarantines a second wall-scale set giving a marble wall 1.0 to
1.1 mm, a brick wall 6.5 to 8 mm and a "smooth wall" 4.1 mm, on the grounds that
it is radio-fitted and `SurfaceRoughnessPrior.__post_init__` raises if
`radio_fitted` is true. The names are near-identical to Guo's and the values
differ by 5 to 11 times, which looked like two campaigns disagreeing. It is not.

The second set is **Zhang, Sun, Tao, Zhu, Gao, "Diffuse scattering measurements
and mechanism analysis at 8, 12, and 28 GHz for typical building surfaces", npj
Wireless Technology 2(1), article 1, 2026, `10.1038/s44459-025-00016-9`**, open
access. Four of its five authors are Guo's co-authors, Guo himself is thanked in
the acknowledgements for the same measurement campaign, the site is the same
Minhang campus of Shanghai Jiao Tong University, and it cites the WCNC paper
directly. The dielectric constants identify the surfaces one to one: marble
6.2 against 6.1 and 6.2, smooth wall 5.8 against 6.0 and 5.7, and Guo's "rough
wall" at 10.5 is the npj paper's "brick wall" at 10.1 and 11.5. **Same three
walls, measured by the same people, at the same place.**

So there is no contradiction to resolve. There is one clean demonstration, on
identical physical surfaces, that a Gaussian roughness height inverted from radio
data is 5 to 11 times the geometric height the same group assumes going forward.
Three things make the npj numbers unusable as physical priors, and they are worth
writing down because the same trap catches every fitted height in this
literature:

- Their own Table 2 is captioned "Fitting parameters of BK and ER models for
  different materials", scored by SMAPE, and the text says the parameters come
  from "minimizing the discrepancy between measured data and ray-tracing
  simulation results". They are outputs, not measurements.
- **The fits are at 8 GHz**, where the free-space wavelength is 37.5 mm, and the
  28 GHz figure in that paper is a *simulation* driven by the 8 GHz fit rather
  than an independent 28 GHz roughness. Effective roughness does not transfer
  across frequency, and their own results show it failing: diffuse scattering at
  8 and 12 GHz is similar and distinct from 28 GHz, and the 28 GHz delay spread
  is much larger than at the other two bands. A true geometric sigma inside a
  Kirchhoff model would have handled all three with one number.
- Taken as geometry the npj brick height is self-refuting. At 6.5 mm and
  30 degrees incidence, `g^2` is 3.6 at 8 GHz but **43.6 at 28 GHz**, a coherent
  power fraction of 1e-19, and the same group reports 28 GHz power "concentrated
  in the specular reflection direction" for every surface. Guo's 0.715 mm gives
  `g^2 = 0.53` and 59 percent specular, which is a physically sensible facade.

The honest position for the paper is that **neither set is a surface metrology
result**. Guo's is an unsourced nominal input and the npj set is an explicit fit
output, and the gap between them is the size of the structural contribution that
section 4.6.2 says carries the diffuse power. That is the same conclusion
Vitucci reaches from `alpha_R = 65` against `alpha_R = 4`, arrived at from a
completely different direction, which makes it a third independent corroboration
rather than a fourth data set.

### 4.6.4 Brick roughness: say face or wall, every single time

The two documents quote brick RMS height as 1 cm and as 0.03 mm, a factor of 333.
**Both are right and they describe different objects.** This was the largest
apparent contradiction in the pair and it is not a contradiction at all.

- **Face.** A prepared monolithic patch with no joints, which is what a
  profilometer measures and what almost every published RMS height is. Every
  direct measurement of a brick face returns 0.024 to 0.095 mm.
  `config/surface_roughness.json` carries `brick_face` at 0.03 mm and that face
  is 99.9 % specular at 28 GHz.
- **Wall.** A metre-scale facade patch, which is what a fishnet face actually
  stands for, additionally carrying mortar joints, course relief, block relief,
  pointing, sills and reveals at centimetre pitch. Landron measures 0.5 cm RMS on
  a real brick wall and Vitucci's model parameter sits at 1 cm with a correlation
  length of 0.5 m, which is a wall-scale figure by any reading: no brick face has
  a half-metre correlation length.

The config enforces the distinction rather than averaging it. `brick_face` and
`brick_wall_with_mortar_joints` both carry `rms_height_mm = 0.03`, because that
field is defined as the face statistic in both, and the wall's structure lives in
a separate `periodic_component` block. The file's own `two_scales.do_not_average`
note says it directly: averaging the two produces a value that describes neither.

**Rule for every document and the paper: no brick roughness number appears
without the word face or the word wall next to it.** The same rule applies to
stone and to concrete paving.

### 4.6.5 The diffuse ceiling, and one number that has no source

Three figures for "how much of the received power is diffuse" are in circulation
across the two documents, and they do not all mean the same thing.

- **20 % of total received power.** Charbonnier et al. 2020, measured, 28 GHz,
  urban, directional sounder, 488 acquisitions. This is the one number with a
  measurement, a band and a denominator all stated. Use it.
- **Up to 40 %.** Melloni, Vitucci, Degli-Esposti, Berweger, Chuang, Gentile,
  Golmie, arXiv:2605.17988 (2026), stated for "mmWave and sub-THz". That is a
  cross-band envelope, not a 28 GHz urban figure, and quoting it against
  Charbonnier's 20 % as though they disagree is a category error.
- **36 %.** `ROUGHNESS.md` carries "20 to 36 percent" and gives no citation for
  the upper end. **It could not be sourced here.** The only quantity in either
  document that yields 0.36 is Charbonnier's calibrated building scattering
  coefficient `S = 0.6`, whose square is the diffuse share of *reflected* power
  rather than of *total received* power. That is a plausible arithmetic origin
  and it is an inference, not a confirmation, so it is recorded as an open item
  rather than repaired. Whoever wrote the 36 should say where it came from, and
  if it is the `S = 0.6` route then the sentence needs a different denominator.

Until that is settled, quote 20 % with Charbonnier attached, and quote 40 % with
Melloni and the words "across mmWave and sub-THz" attached. Do not write a range
that silently spans two denominators.

## 4.7 Xia et al., now read in full, and it settles two verdicts

The IEEE TAP 2024 paper was marked abstract-only and paywalled in two places in
an earlier revision of this document. The PDF is in `lit/` and has been read.
Page and section references below are to the printed article, IEEE TAP
72(10):7986-7997.

**Geometry is their own drone survey.** Section III-A: "The DJI Matrice 30 drone
equipped with a Seir v3 lens was used for oblique aerial photography, capturing
around 7000 aerial images. Subsequent 3-D reconstruction was performed using DJI
Terra software, resulting in the photogrammetric point clouds." The site is
Huangdao District, Qingdao, about 900 by 800 m, 55 buildings, 33 m of relief,
described as high greenery with minimal traffic and pedestrian flow. No ground
sample distance or point density is reported anywhere. That is a green suburban
campus, not a dense European core.

**Classes, with an internal inconsistency worth knowing.** Section II-A trains
seven: "ground, vegetation, building, wall, car, water, and street furniture".
The abstract and the Fig. 1 legend give six, with "fence" in place of "wall" and
no water. They are the same class under two names. Segmentation is RandLA-Net
pretrained on SensatUrban, so the taxonomy is not theirs either.

**Cars are deleted, clutter is retained.** Section I: "By construct, this
propagation scene model does not take car point clouds, owing to their
temporariness." Table II has five rows and no car row. Vegetation, fences and
street furniture are kept and meshed by ball pivoting (section II-B-3). Vegetation
becomes a closed triangle shell with wood permittivity, with no canopy volume
model, and they say so: "it is assumed that all the materials of the vegetation
are simplified as wood although actual vegetation should also include green
leaves."

**Retained, not recovered, and this is the verdict that matters.** There is no
street-level imagery in the paper. The clutter is in the model because the drone
overflew it, and the pipeline is strictly segment, drop cars, mesh the rest.
Nothing is inferred for anything the survey did not directly see. Their own
concession, section V-A: "There is an underestimation of path loss at transmitter
positions 1 and 3 possibly because more minute obstacles are not considered in
the scene model, leading to rays being traced that should not exist." Nadir and
oblique aerial photogrammetry is systematically blind to vertical facade detail,
under-canopy furniture, ground-level poles and bollards, awnings and parked
vehicle geometry, which is precisely what a street-level camera sees best.
**Surviving claim 1 holds.**

**Materials are one flat value per class.** Table II, five rows: Building
concrete 5.24 / 0.103, Ground very dry ground 3 / 0.002, Fence concrete 5.31 /
0.075, Pole metal 1 / 1e7, Vegetation wood 1.99 / 0.014, sourced from ITU-R
P.2040. No glass or window class exists at all, in an urban scene. The two
concrete rows come from *different revisions* of P.2040, the building row from
P.2040-3 and the fence row from P.2040-1, which is a small sloppiness and also
positive evidence that nothing was fitted.

**Two numbers to use, and one to be careful with.** Their scene-model ablation,
Table VI, at three transmitter positions: buildings and ground alone give RMSE
12.79 / 10.17 / 11.07 dB, adding fences and poles gives 12.06 / 9.72 / 10.49,
adding vegetation instead gives 7.17 / 6.33 / 6.82, and everything together gives
7.09 / 6.15 / 5.95. So **non-vegetation clutter is worth 0.6 to 0.7 dB and
vegetation is worth 4 to 5 dB**, and the two are never separated from each other.
Their headline "clutter matters" result is really a vegetation result. That is a
caution for this study's own motivation, not for its novelty. The geometry is
also unusual: both link ends at 2.2 to 2.5 m, vehicle-mounted, which is a V2V
geometry rather than a rooftop macrocell, and their best RMSE is about 6 dB,
which is not a tight benchmark.

**Their diffuse-scattering result is a useful negative.** They sweep the full
Degli-Esposti family (`S` from 0 to 1, `alpha_r` and `alpha_i` 1 to 4, `Lambda`
0.1 to 0.9) in Sionna-RT and conclude: "the account of vegetation scattering does
not significantly improve the prediction accuracy. This further confirms previous
studies that diffuse scattering plays an important role in modeling the
time/angle dispersion characteristics of channels (such as delay spread and angle
spread) [52], [53], rather than in path loss prediction." The whole `S` sweep
moves RMSE by under 0.3 dB. **Cite this whenever the paper argues that the
angular second moment is the right observable**, because it is a published,
measured statement that scalar path loss is the wrong place to look for
scattering physics. It is also a warning: any claim here that materials or
roughness change *path loss* has this paper against it at 2.8 GHz.

**Adjacent items this reading surfaced**, none previously in this document:
F. Zhang et al., IEEE TAP 72(3):2712-2722, Mar 2024 (same Wuhan group, the direct
predecessor), and Semkin et al., IEEE TVT 66(6):4647-4656, 2017, which did
drone oblique photogrammetry into a mesh into 60 GHz channel modelling seven
years earlier, and whose only stated gap is that it "does not distinguish between
different environmental elements in the scene".

---

# What the paper may claim

In descending order of safety.

1. **Clutter recovery from street-level imagery into an RF simulation.** The RF
   side knows it matters and has not solved it (`10.1017/S1759078716000349`,
   `10.1109/EUMC.2015.7345733`). The vision side does pole, sign and tree
   inventory from Mapillary at scale (`10.1177/03611981251372093`). Nobody joins
   them. **The Xia caveat is now closed and it closed in this claim's favour**:
   Xia et al. merely retain, from their own drone survey, and there is no
   street-level imagery anywhere in that paper. Section 4.7. The honest
   qualification is not about novelty but about motivation: their own ablation
   puts non-vegetation clutter at 0.6 to 0.7 dB at 2.8 GHz, so the case that it
   matters has to be made at FR2 or on a dispersion metric, not on path loss at
   sub-6.
2. **A delay-resolved, polarisation-complete, second-moment reciprocal transfer
   operator published as a reusable per-location deliverable, for RF exposure.**
   Not found in graphics, acoustics or radio. The narrowest claim and the only one
   that survived a deliberate attempt to break it.
3. **Third-party photogrammetric tiles at eleven-city scale with no per-scene
   reconstruction and no channel measurements.** Everything in question 1 is one
   site, or two or three scenes, and VisRFTwin, HoRAMA, RadioTwin and RFCanvas all
   need measurements or their own capture.
4. **FR3 population exposure.** Nothing exists.
5. **A posterior over material class, conditioned on a semantic observation,
   carried into the tracer.** Qualified. No RF paper does this, but Remcom ships a
   Monte Carlo material type, OpenGERT does plus or minus 10 percent Monte Carlo
   around a fixed assignment, and polynomial-chaos UQ of ray tracing dates from
   2014. Do not write "first to put uncertainty on material parameters". Write
   "first to carry a posterior over material *class* into the tracer". mmSV
   computes a per-pixel material probability and then takes a majority vote, so
   the distinction is exactly the retention.
6. **The attribute vector** (thin, rough, reflective, transparent, conductive,
   transient) as an axis orthogonal to material identity. Unclaimed in RF,
   transient especially, though mmSV does dynamic object removal. Nearest ancestor
   is "Visual Material Traits: Recognizing Per-Pixel Material Context", ICCVW 2013,
   `10.1109/ICCVW.2013.121`. Cite it.
7. **Sky view factor, or any named urban-form metric, as an RF exposure
   covariate.** Unoccupied, with the title-and-abstract caveat.
8. **A roughness prior *distribution* per semantic class, with evidence grades,
   at two bands.** Partially contested. VisRFTwin does VLM to discrete roughness
   level to scattering coefficient, and AODT already exposes RMS roughness and
   lobe exponents. Nobody publishes a per-class lognormal with its provenance and
   its refusals attached. Claim it at that resolution, not broader, and claim the
   prior separately from the closure that consumes it: section 4.6.1 restricts
   the Rayleigh split to the eight random-roughness classes, so a claim phrased
   as "roughness priors feeding a Rayleigh split" is claiming something the code
   deliberately refuses to do for the other eight. The prior itself is
   closure-agnostic and does not inherit that limit.
9. **A real street-level equirectangular panorama registered to Google
   Photorealistic 3D Tiles.** Nobody does exactly this: mmSV projects onto OSM
   prisms, VisRFTwin renders Google Earth Studio virtual views, DeepTelecom
   hand-rebuilds 3D Tiles, Cazzella uses hand-shot photos on OSM prisms. Caveat:
   OpenFACADES does panorama-to-geometry registration and material attribution at
   city scale, without RF.
10. **The image-space semantic-island fishnet.** Weakest, and weaker than it was
    before mmSV was read, since mmSV splits planes into 10 cm faces with a
    per-face majority material and merges neighbours. What survives is that the
    cut follows the semantic island boundary exactly rather than a fixed grid.
    Claim it narrowly and do not lean on it.

## Do not claim

- First to assign RF materials from imagery. mmSV (2023), Zhang and Brennan TAP
  (2024), HoRAMA, VisRFTwin, Kang et al. and RFDT-Channel all own this.
- First to vary material within a facade for outdoor ray tracing at 28 GHz.
  Cazzella et al. did it, in Sionna, at 28 GHz, and measured the impact.
- First to use photogrammetric geometry plus semantic segmentation plus clutter
  classes for outdoor ray tracing. Xia et al., IEEE TAP 2024, end to end with
  public code. Their own contribution 1 stakes exactly that sentence. What they
  do not do is get the clutter from imagery the survey could not see, which is
  where claim 1 lives.
- Reciprocity, source-independence, hardware-independence, per-point
  precomputation, angular resolution, or polarisation-completeness of a transfer
  operator. See question 2.
- First to consider incidence angle in exposure. ICNIRP 2020 equations 29 and 30.
- The precompute-and-swap factorisation. LEXNET, 2015.
- Multi-city comparison, 4 cm2 averaging, deployment-averaged exposure, or the
  phrase "digital twin" (Ericsson, `10.23919/EuCAP63536.2025.10999394`).

---

# Decisive items not reached

Ordered by how much each would change this document. UGent institutional access
resolves most of them.

| Item | Identifier | What is needed |
|---|---|---|
| Wagen, ISNCC 2020 | `10.1109/ISNCC49221.2020.9297355` | Does he use the full D/G/F microfacet form, or only the GGX D factor? If full, the microfacet contribution here is essentially nil and the framing must shift entirely to the Rayleigh split. IEEE returned 418, ResearchGate 403. |
| Kim et al., ETRI Journal 42(6) 2020 | `10.4218/etrij.2019-0411` | "Millimetre-wave diffraction-loss model based on over-rooftop propagation measurements". The only direct measurement of rooftop diffraction loss against angle at mmWave, so it is the check on section 4.1's entire argument. Wiley 403 on four routes. |
| Göktepe, Peter, Weiler, Keusgen, IJMWT 2016 | `10.1017/S1759078716000349` | Delta dB, delta delay spread and delta angular spread with and without cylindrical street clutter. Directly relevant to the safest available headline. Cambridge Core and IEEE blocked. |
| IEC/IEEE 63195-2:2022 | `10.1109/IEEESTD.2022.9770556` | The multiple-simultaneous-transmitter clause and the power density definition (`\|S\|`, `n_hat . Re{S}`, or modulus over a conformal surface). If it mandates a coherent vector sum, a referee can argue it already combines incident directions. Roughly 507 euro. Same question for IEC 62232:2025. |
| Zhang, Brennan et al., IEEE TAP 2024 | `10.1109/TAP.2024.3355502` | Whether any single building carries more than one material, and whether the electrical parameters are ITU-R P.2040 values or fitted. |
| Li, He, Ai et al., IEEE TCCN 2026 | `10.1109/TCCN.2026.3659825` | Whether classification is per-point, and whether per-class confidence propagates into ray tracing. If it does, surviving claim 5 weakens materially. |
| Joseph, Frei, Röösli et al. 2012 | `10.1002/bem.21737` | "Between-country comparison of whole-body SAR from personal exposure data in urban areas". The one paper coupling multi-city comparison to a dosimetric quantity. Title-only, no abstract retrievable anywhere. |
| Jawad, Lautru, Benlarbi-Delaï, De Doncker, IEEE TAP 2015 | `10.1109/TAP.2015.2434399` | The section II channel-parameter list: does it include angular spread and AoA distributions, or only amplitudes and delays? Decides footnote against differentiation obligation. |
| Järveläinen, Kurkela, Haneda, IEEE AWPL 2015 | `10.1109/LAWP.2015.2390917` | The canonical geometry-fidelity A/B at 60 GHz, dB and ns error against model detail. Järveläinen's 2016 Aalto thesis is likely open access. |

## Coverage limits, stated rather than papered over

- The session WebSearch budget was exhausted at 200 calls before most of this work
  started, so 2023 to 2026 preprint coverage is thinner than it should be. A
  recent Sionna-era paper doing exactly the adjoint construction cannot be fully
  ruled out.
- The sky view factor negative rests on title and abstract indexing in four
  systems. Strong, not airtight against a phrase buried in a body paragraph.
- Siradel and Luxcarta classify clutter from imagery for RF planning commercially
  and publish no methodology. No literature search closes that.
- Ansys HFSS SBR+ PTD/UTD/creeping-wave breakdown, Remcom X3D maximum diffraction
  order, and AODT diffraction status are all unverified. Vendor pages returned 000,
  403 or 404. Do not assert any of them.
- No patent search was run. A separate patent pass is needed before filing.
