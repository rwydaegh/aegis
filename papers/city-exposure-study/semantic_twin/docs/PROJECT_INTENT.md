# Project intent

What the author asked for, when, in his words, and whether it exists in the code
today. Written 2026-08-03 from the raw session transcripts rather than from any
document in this repository.

This is not a second decision log. `DECISIONS.md` records the calls that were
made and why, and it is good. `ROADMAP.md` records the phases and is honest about
what is unfinished. Neither of them records **who** made a call, and neither
records the instructions that were given and then quietly dropped. That gap is
what this file is for. Where an existing document already covers an item
correctly this file cites it and moves on.

Three rules were followed while writing it.

- His words are quoted verbatim, typos included, whenever the wording carries the
  intent. Nothing is paraphrased into something cleaner than he said.
- Status is verified against `.py` files and against files on disk, never against
  another markdown document. Where a document and the code disagree, that
  disagreement is the finding.
- Where a decision was taken by an agent rather than by him it is marked
  **agent call**. Where his intent was genuinely ambiguous it says so instead of
  picking a reading.

## How to regenerate this

The transcripts are at
`~/.claude/projects/-home-user-aegis-papers-city-exposure-study/*.jsonl`, one of
them 72 MB, plus 215 files at `~/.claude/projects/-home-user-aegis/` holding the
pre-history from before this directory existed. Do not read them raw. Filter for
`type == "user"`, drop `isSidechain`, drop `<task-notification>`, drop the
compaction summaries, and keep the `content[].type == "text"` blocks in
timestamp order. That yields about 60 real user turns for 2026-08-01 and
2026-08-02 and about 30 relevant ones from the sister project. Timestamps below
are UTC, as stored.

## Standing constraints

These were stated once, never renegotiated, and everything else has to fit inside
them.

**No measurement will ever be taken.** 2026-08-01 20:06, when asked whether to
plan a validation campaign: *"no were not doing any measurements lmao"*.
Restated at 20:22 against the masonry problem: *"no problem is tough enough not
to tackle! we want realism and ambition. i just wont ever go measure."* This is
load bearing. It is why the masonry response is derived from construction
standards, why `ROUGHNESS.md` grades its prior by provenance, and why any
accuracy figure in this study has to be a blind prediction rather than a
post-calibration residual. Correctly recorded in `ROADMAP.md` under work outside
the original phases.

**This is a PhD paper, not a product.** 2026-08-01 18:16, cutting off a
commercial framing: *"this isnt commercial haha, its a paper for my phd thats why
its in papers/"*. Earlier, 2026-06-01 00:43, on the same study: *"this is a good
goal but no need to be submitabble. it can just be a latex report with good
figures mostly."* The bar rose since then. On 2026-08-02 16:56 he asked for
*"an end-to-end IEEE style report methods and results ... think IEEE Access"*,
with the qualifier *"I know it will be shitty writing at first, but for now lets
just focus on content"* and *"Later we will run it through papermaker9000"*. So
prose polish is explicitly deferred to a later tool, and content is what is being
graded now.

**Ten cities is the figure to hit, at the cost of other parameters.** 2026-06-01
00:43: *"try to hit the figure '10 cities' at all costs and if other parameters
(there is a myriad of options) need to be sacrificed for that, so be it. I need
10 cities and a nice CDF type plot for sure."* Restated 2026-08-01 17:01: *"This
is for exposure, and we aim to have ten cities."* Delivered as eleven. The CDF
exists, `FIGURES/14_exposure_cdf_korenmarkt.png` and
`FIGURES/16_eleven_cities_exposure.png`.

**Worst-case realistic is the philosophy.** 2026-07-28 11:24: *"the philosophy is
always 'worst-case realistic'. so tbh the scheduler seems unnecessary as it
creates breathing room."* Same turn: *"dont think about uplink, out of scope."*
Uplink is still out of scope, correctly.

**An LLM belongs in the loop.** 2026-08-01 18:57: *"in general ive always been a
fan of using an LLM somewhere in the loop."* 2026-07-27 21:08, narrowing what
that means: *"we are not using meshlab or that 2022 ML model or 'a vision model'.
we are at most using a good LLM in headless claude code sessions."* Note the
tension with what was built: SAM 3 and SAM 3D Body are vision models, and they
are the material axis. He never objected to them once they were running, and on
2026-08-02 he treated SAM 3 coverage as the thing that mattered, so treat the
2026-07-27 line as superseded rather than as a live constraint. The separate ask,
an LLM that predicts material where evidence runs out, is a real open item and is
listed below.

**Naming: leave the Inhouse and Google inconsistency alone.** 2026-08-01 17:23,
after an agent flagged that the prose says Inhouse everywhere and the code reads
`GOOGLE_API_KEY`: *"Long story short dw about that leave it be."* Still
inconsistent, on purpose. `semantic_twin/panorama.py:1` says "Inhouse Street
View" and calls `tile.googleapis.com`.

**Tooling conventions.** Subagents in parallel with the orchestrator thread
holding context, 2026-08-01 18:33. Smaller scoped agents after two of them ran
for over 90 minutes, 2026-08-01 22:31: *"this time try to note have them work for
2 hours and be a little bit more smaller scoped if possible"*. Permission to rent
GPU on Blue Lobster, same turn, but algorithms, caching and vectorisation first.
2026-08-02 23:40: *"do avoid using the max, think agent, please"*. He also wants
argument, not agreement, 2026-08-01 22:44: *"I love that u have opinion and arent
a yesman, good. But let me converse."*

## The spine, and how it drifted

This is the item he raised on 2026-08-02 23:40 and it deserves its own section
because it is the one place where the method moved and the reason for a whole
subsystem moved with it.

**The original pitch, 2026-08-01 17:23.** Transmitter co-located with the
receiver and with the street view camera. Rays leave that point in every theta
and phi, hit something, and the path that counts is the one that comes back:

> *"if we perform SBR ray tracing with the transmitter co-located with the user
> (and ultimately the receiver), the rays emanate from the same position where
> the street-view image was captured ... the final ray returning to the receiver
> (co-located with the transmitter) must come from one of those semantically
> classified areas."*

And the three-bounce version, same turn:

> *"transmitter -> A -> B (an out-of-view triangle) -> C -> receiver (the
> transmitter). This creates a monostatic response that describes
> non-line-of-sight independently of transmitter and receiver choices."*

**The reframing.** He pasted a long ChatGPT exchange on 2026-08-01 17:34 which
proposed replacing the closed loop with `T_S(Omega)`, the local transfer tensor,
built from rays that *escape* rather than rays that return, and read backwards by
reciprocity. He did not immediately buy it. 17:55: *"ill be honest with you, ive
read chatgpt explanation and i simply dont understand what he's trying to say. Do
you believe in its flaw, honestly?"* By 18:01 he had worked it out himself and
started refining it, asking whether Omega could be restricted to directions above
the skyline. So the adjoint framing is his, adopted after he understood it, and
`METHOD.tex` was written to explain it at his request. `DECISIONS.md` records the
call correctly under "Observable: adjoint transfer tensor, not the monostatic
loop", including the argument that the monostatic loop ranks locations backwards.

**What that decision did not account for, and what he noticed 34 hours later.**
2026-08-02 23:40:

> *"the whole idea of SAM gives us perfect materials so up to 2 reflections are
> guaranteed to touch the right material. I feel like that has kind of been lost
> in translation, so to speak."*

He is describing a property of the closed loop specifically. On a two-bounce
monostatic path `S -> A -> C -> S`, both `A` and `C` are visible from `S` by
construction, so both carry panorama evidence and both get an image-derived
material. That is the guarantee. Under the adjoint framing the path never returns
to `S`, so only the *first* hit is guaranteed panorama-visible. Every later
interaction lands wherever the ray goes, and the last one is visible from the
source, not from the camera. The guarantee halves. Reading the mechanism this way
is my inference from the geometry, not something he spelled out, but it is the
only reading under which his sentence is literally true, and it is a real cost
that `DECISIONS.md` does not list among the things the adjoint move gives up.
That entry claims the change *"costs nothing"* and lists only which rays get
written down. It should list this.

**What the code does now.** Pure escape and weight. `grep -rn "monostatic"` over
every `.py` file returns nothing. `semantic_twin/propagation/tracer.py:1-8` states
it plainly: rays leave `S`, bounce until they escape the cropped scene, and
deposit throughput weighted by an external illumination density at the exit
direction. Rays terminate by escaping, by truncation, or by roulette. There is no
return check and no second traversal. `ROADMAP.md` phase 4 already says the
monostatic loop was not built. That is accurate. What is not written anywhere is
that its loss took the two-bounce material guarantee with it.

**And the material binding does not compensate.** There is no bounce-index branch
anywhere in the tracer. `tracer.py:479` loops depth and `tracer.py:533` does
`klass = self.face_class[face]`, the same lookup at bounce 0 and bounce 3. A
triangle no panorama saw falls back to the geometric orientation rule, and
`semantic_binding.py` records that fallback in its own provenance string. At
Korenmarkt, the best-covered site, `covered_fraction_by_area` is 0.106. On the
eleven-city headline run it is exactly 0.0 at every site.

## Decision ledger

Chronological. Status is one of **built**, **partially built**, **never built**
or **superseded**, verified against code.

### Before this directory, from the sister project

| Date | What he said | Status |
|---|---|---|
| 2026-06-01 00:43 | Ten cities at all costs, CDF plot, LaTeX report not a submission | **built**, as eleven |
| 2026-07-27 20:47 | *"the base stations are a big deal too! aegis has a big database and very crude data from governments from it. that's actually kinda tough to model given the incomplete data!"* | **superseded** by the illumination-law approach, which deliberately never places a base station. See below. |
| 2026-07-27 20:47 | Keep triangle count down, only the parts the walk actually sees deserve attention | **built**, the fishnet and the crop |
| 2026-07-28 00:45 | Six materials is too few and too homogeneous, *"an entire facade is brick, and the next building is all stone"* | **partially built**. The ITU P.2040-4 table is in `config/itu_p2040_4.json` and a material posterior exists, but it reaches 10.6 percent of surface area at one site and 0 percent on the headline run. |
| 2026-07-28 11:32 | *"That's LOD1 no? our bar is set high... true 3D and facade level details on the wavelength scale"* | **partially built**. Photogrammetric tiles plus image-derived surface classes, not LOD3 geometry. Openings are not modelled as geometry. |
| 2026-07-28 12:14 | *"Tbh Im thinking digital twinning is a whole separate project. Write a huge md file about only that"* | **built**, and then some. `MONOSTATIC_SBR.md` is 175 kB, `MASONRY.md` 62 kB. |
| 2026-07-30 15:44 | *"Prove to me u can make a perfectly realistic scene with sufficient detail in Ghent. There is a 8x8 MIMO 28GHz antenna and 10 people walking around."* | **never built** as stated. This is the first appearance of the 8x8 array, four days before the version he repeated on 2026-08-01. See the never-happened list. |
| 2026-07-30 15:44 | *"I dont care for reproducibility and I know you feel a bit weird about all of this in a paper. I dont. I just need a great digital twin at any cost"* | Worth flagging: the study as built leans hard on reproducibility as its selling point. He said the opposite here about the twin-building step specifically. Not a contradiction, but the emphasis moved and he never revisited it. |

### 2026-08-01

**17:01, opening.** One camera location instead of many, fewer triangles, a
new prominent location rather than Ghent, ignore `hybrid_twin/`, ten cities.
All **built**. Milan Duomo became the second site, `DECISIONS.md` "Site selection
is gated on official Street View coverage".

**17:23, the method pitch.** Covered in the spine section above. Three sub-items:

- Three reflections, *"perhaps one non-specular"*, with materials described by
  effective roughness. **Built**, `DEFAULT_MAX_BOUNCES = 3` at
  `tracer.py:47`, with a Rayleigh specular and diffuse split. But see the
  inconsistency note below: that constant is currently uncommitted, the last
  committed value was 12, and `make_sensitivity_study.py:90` still hardcodes 4.
  `CODE_AUDIT.md` section 5 already flags this as a defect.
- *"It seems we'll need to write our own ray tracer, unless we stick with Siona
  RT."* **Built** as our own, on a Mitsuba 3 ray cast backend. Sionna was never
  used, and the Sionna cross-check in `MONOSTATIC_SBR.md` section 11 is still not
  built, which `ROADMAP.md` phase 5 states.
- *"I just wanted to sketch the concept and have it recorded in Markdown inside
  the project so we know what we're doing."* **Built**. This is the origin of the
  markdown-heavy convention in this directory.

**18:01, the antenna.** Three separate asks in one turn.

> *"isnt it sufficient to have Omega only from those directions we have right
> above the skyline? since those are the Tx antennas?"*

**Built**, and it became the illumination law. `directions.py:238-241` restricts
sources to height bands above the pedestrian head.

> *"are you sure we dont need to parameterize anything more about the antenna?
> It's of course going to be MIMO (so phase differences per AE)"*

> *"In my original plan I was gonna use three sectors and in each sector like a
> 8x8 MIMO canonical antenna and have it beamform to 'itself'.."*

**Never built** for 33 hours, then started tonight. See the never-happened list.

**18:16.** PhD not commercial. Standing constraint.

**18:27, four instructions in one turn.** This is the densest turn in the project
and it is where two things went missing.

1. Blockage and depth cross-checking, two depth models against the tiles to
   decide whether a blob is a wall or a human. **Built**, `build_dynamic_bodies.py`
   range-corrects against fused monocular depth or a mesh floor ray.
2. *"Humans should always be sent to SAM3D, which will create a fully-fledged,
   posable SMPLX human for computing exposure later as bystanders. For now, don't
   start computing exposure."* **Partially built**, and this is the one he named
   as an example of drift. Details below.
3. Mesh repair by solidify, voxelize, decimate. **Rejected**, twice reviewed, and
   he was brought along rather than overruled. See the mind-changes section.
4. *"use Google Street View for higher resolution and the SAM model for semantic
   classification, especially to segment facades—not just buildings. Later we
   want to use ITU materials; let's aim for realism and ambition with as many
   different RF materials as possible."* **Partially built**. Street View is the
   source for the single-panorama sites, `data/panoramas/korenmarkt/metadata.json`
   carries `panoId` and `copyright`. But the twelve-station Korenmarkt walk, the
   only multi-station set and the one that carries the SAM 3 material binding,
   is **Mapillary**, its metadata carries `computed_geometry` and `sequence`. No
   document in this repo states that the two arms of the study use two different
   imagery providers. `WALK.md` is about Mapillary throughout and never says it is
   departing from an instruction.

**19:46.** *"if it's easier we can pivot the paper to FR3 if u want"*. **Taken.**
The study now leads at 15 GHz, `run_exposure.py:940` defaults `--frequency-ghz`
to 15.0, with the FR3 midpoint argument at `run_exposure.py:175` and 28 GHz kept
as the upper FR2 anchor. Note he offered this as a convenience, not as a
requirement, and the offer was accepted without a recorded discussion of what it
costs. Everything written before 19:46 that quotes 28 GHz, including several
`DECISIONS.md` entries, is still at 28 GHz on purpose because that is the band the
argument was made in.

**20:06.** Three answers in one turn. No measurements, ever. *"dont forget the
new 'RT method' is novel too"*, with Xia et al. handed over as the comparison
point, now in `PRIOR_ART.md`. And the open LLM question, quoted in full below
because it is unanswered.

**20:22 and 20:23.** *"may i request the ultimate digital twin then, if you say
you have that, clearly in Blender? so i wanna see everything available to us,
make it pretty and clear"* and *"btw would be cool if that DT is created in code
procedurally on request"*. **Built**, `showcase_blender.py`, `render_showcase.py`,
later `build_propagation_blends.py`. Procedural, on request, from code. He asked
again on 2026-08-02 23:40 for *"nice blender files with basically everything in it
at once"*, which suggests the current per-topic split does not satisfy the
original ask.

**22:31.** Ambition and scale, *"As much as possible, a grand set of walks in many
cities, realistically"*, plus an important licence: *"The top level here gives a
bit more info on the vision although that is quite old files and my mind tends to
change quite fast. U can take decisions urself."*

### 2026-08-02

**16:53, base station position.** He set two physical bounds and then asked for
the thing that had already been built:

> *"there is a max height a base station can be located at (in new york nobody
> puts a mmWave antenna on One World Trade Center) and also there is a max
> distance period for the link until it becomes no longer relevant. just like the
> rays in the RT, at one point we give up on the signal. The idea is that we are
> always agnostic to the exact position of the BS and try to kinda integrate over
> plausible locations. Do we have that?"*

**Built.** `directions.py:238-241` is exactly this: a height band and a range band
per site population, integrated over. `ROOFTOP_HEIGHT_BAND_M = (13.5, 43.5)`,
`ROOFTOP_RANGE_BAND_M = (25.0, 250.0)`, `STREET_HEIGHT_BAND_M = (2.5, 6.5)`,
`STREET_RANGE_BAND_M = (10.0, 150.0)`. His constraint is honoured in structure.
He then asked at 22:18 *"2.5 to 6.5 and 13.5 to 43.5 ; this is arbitrary,
correct?"* and `DEPLOYMENT_GEOMETRY.md` was written to answer it, which is the
right response. The code comment at `directions.py:236` points at
`MONOSTATIC_SBR.md` section 2.7 rather than at the campaign evidence, so a reader
of the code alone still cannot tell where the numbers came from.

**19:03, the antenna zoo.** On an agent that had scraped three national antenna
registers: *"idk how he did it, but it's lowkey wasted work as aegis/ has done
this suuuuper extensively and has a giant database. anyways, the problems with
this are quite predictable. it's the famous antenna zoo, and a very small
minority (in fact I think about 0 in europe) has nice standalone mmWave FR2 let
alone FR3"*. This is a standing instruction with history, it is in the AEGIS
memory as `feedback_reuse_aegis_data.md`. Check AEGIS before commissioning data
collection.

**20:36, the walk.** He looked at the Blender output and said:

> *"the walk layer defines a set of points that are just kinda spread out in the
> area. I guess u can kinda recognize a linear walk in it but there are lots of
> points kinda randomly spread (of which u used one specifically bad one). In my
> head a walk, is really the standard thing u see from Google, the one where u
> scroll nicely. Like, someone actually walked."*

**Not resolved, and the documents disagree with each other about it.** There are
two different things called a walk. The panorama walk at Korenmarkt is a real
capture sequence traversed, which is what `DECISIONS.md` means when it says
*"The walk is the link graph traversed, so no synthetic routing is needed"*. The
standpoint walk that actually produces every exposure number is a 3 m grid over
ray-cast walkable ground, filtered by five gates and chained by greedy nearest
neighbour, `PAPER_METHODS.md` section 6. That is the scattered point cloud he was
objecting to. `PAPER_METHODS.md` calls it *"a walk, not a sampling design"*, which
is defensible as physics but is not what he meant by walk, and no document
acknowledges that the two usages differ.

**20:46 and 20:56, confusion he flagged himself.** *"how can a base station be 60
degrees above a rooftop? note that i am generally confused"*, and the ground datum
warning that Google tiles carry large underground structures. Both were taken
seriously. The 60 degree figure came from the pre-correction fixed-elevation law,
`directions.py:306-307` keeps it only for reproducing old numbers, and the
correction is recorded in `DECISIONS.md` "The illumination model is the law, not
the bands". `GROUND_DATUM.md` answers the second. Good outcome, and it is worth
noticing that the illumination-law bug was found because he said he was confused.

**20:59, 21:48, 21:56, presentation.** Figures wanted in `PAPER_METHODS.md`,
*"your structure isnt great, e.g. , opening with 1.1 is like wtf are we doing and
kinda abstract"*. Then two notation complaints, `dd` and then *"what is Q and M.
if u havent defined, please take care of correct notation. speaking of notation,
overall i think u made poor choices. like d and el.."* **Addressed**, commits
`66d611fb` and `99dac875`, and section 1 now opens on a pedestrian, commit
`0c97e019`. Explainer figures 18 through 21 exist.

**22:07, the QA instruction.** After being told SAM 3 had run on 2 of 96
panoramas:

> *"Bruh this what I mean with QA. This convo on claude code has been very long
> check all my user message and how the PoC or my plans developped. Are we missing
> any other critical parts? This is important no???"*

This document is the answer to that question. The direct answer is yes, three
more: the antenna, the bystanders, and the material guarantee.

**22:20.** Approved the cheapest path to making the two arms one study, the SAM 3
hybrid pass on the eight Korenmarkt walk stations, *"--> Yes."*, plus *"ANd
prepare to do a proper big run to properly code everything we want."*

**22:26.** *"like whatever happened to beamforming, or nearby bodies for example?
AEGIS has plenty to say about MIMO stuff btw, and u obv dont re-raytrace."* He is
right on the physics. `DECISIONS.md` "Antennas are post-processing on a stored
path set, never a re-trace" says exactly that, and it was written before he asked.
The decision was recorded and the code was not written.

**22:38.** *"Russian roulette from bounce 3 onward -- im confused whats going on
there. when did u come up with that and whats the reasoning for this? so it's not
a determinstic model?"* **Agent call**, not his. `roulette_start = 3` and
`roulette_floor = 0.05` at `tracer.py:250-251` have been unchanged since the
commit that created the file, `ba3400c8`, whose message does not attribute them to
any request. The estimator is Monte Carlo but seeded, `tracer.py:376`, so it is
reproducible for a fixed seed. At a three-bounce budget roulette can only fire one
iteration before the hard cap, so it is nearly inert. His question deserves a
written answer somewhere and does not have one.

**23:40, the closing instruction.** *"i think i want 3 reflections max and thats
it. keep simple."* Then the drift observation quoted in the spine section. Then
three things to state in the paper, which are asks and not yet content:

> *"I think it's important also to state why we're doing certain things. I think
> there's been literature that says why we don't do diffeRT, and we also have a
> good reason that we stop at 3 reflections."*

`grep` finds no mention of DiffeRT or Sionna anywhere in `PAPER_METHODS.md`.
DiffeRT appears only in `PRIOR_ART.md`. There is no `BOUNCE_BUDGET.md`, although
`measure_bounce_evidence.py` exists to produce the evidence for one.

And a framing licence that should be read carefully:

> *"Just because something isn't quite improving on an older method doesn't mean
> we shouldn't do it. Even if it's just for marketing, it does sound pretty good
> when you can write in your paper that you have all these classes and fancy
> models and whatnot."*

He is not asking to overclaim. He is saying that the semantic layer earns its
place in the paper even where the ablation shows it does not move the number,
which is directly relevant to the current negative result in `SAM3_LADDER.md`.

## Where he changed his mind

He said explicitly that this happens and that it is legitimate, 2026-08-01 22:31:
*"my mind tends to change quite fast."* Recording both positions.

**The hand-built artistic digital twin, abandoned on time cost.** On 2026-07-28
00:45 he wanted a Blender scene built by an LLM to AAA standards, *"a high-quality
art piece with many custom models, clutter, and relevant details"*, and said the
existing six-material output *"feels very homogeneous"*. Seventeen hours later,
2026-07-28 01:45: *"ok for now i change my mind. only cuz it takes too long. im
more or less satisfied with the previous approach ... i just dont want it to go on
forever with modeling. I wanna get to the 10 cities and compute a little bit of
exposure."* What moved him was elapsed time, not an argument. The ambition itself
was never withdrawn and came back on 2026-08-01 as the semantic layer.

**The monostatic loop, given up after he understood the alternative.** Covered
above. What moved him was working through the reciprocity argument himself
between 17:55 and 18:01 on 2026-08-01, not being told. He has now partially
reopened it, which is why the spine section exists.

**Mesh repair by solidify and voxelize, conceded over three rounds.** He proposed
it 2026-08-01 18:27. Asked for its status at 19:27: *"WHatever happened to my
suggestion to improve the mesh? remember?"* Asked for visual evidence at 22:03:
*"why was the voxelizing into decimation rejected? can we show that visually?"*
Then argued the case at 22:44, at some length, that a clean coarse-where-flat mesh
is what a AAA game or a film would use and should reduce ray uncertainty. He was
answered with a triangle count and a BVH argument, pushed back on it, and the
result was a corrected rerun that retired three of the four original objections
and left one. `DECISIONS.md` "Voxel remeshing is still rejected, but for one
reason instead of four" and the later "Retracted: voxel remeshing deletes a third
to a half of the scene". This is the healthiest exchange in the project and both
sides moved. He also got the renders he asked for, `mesh_as_built_157k.png` and
the orbit set, after saying at 22:16 *"i wanna not see python graphs but real 3D"*.

**28 GHz to FR3, offered rather than demanded.** 2026-08-01 19:46. See above.
Flagging it here because it reads in the documents as a settled band choice, and
in the transcript it is a convenience offer that was accepted.

## Asked for and never happened

The point of the exercise.

### 1. The three-sector 8x8 MIMO array that beamforms to itself

Asked twice, five days apart. 2026-07-30 15:44: *"There is a 8x8 MIMO 28GHz
antenna and 10 people walking around."* 2026-08-01 18:01: *"In my original plan I
was gonna use three sectors and in each sector like a 8x8 MIMO canonical antenna
and have it beamform to 'itself'.."* Chased on 2026-08-02 22:26: *"whatever
happened to beamforming"*.

**Status as of 2026-08-03 00:00: under construction tonight, uncommitted, wired
into nothing.** `semantic_twin/propagation/antenna.py` exists, is 41 kB, has no
git history at all, and was last written minutes ago by a concurrent agent. It
contains a real 3GPP TR 38.901 planar array defaulting to `rows=8, columns=8`
at `antenna.py:183-184`, `THREE_SECTOR_AZIMUTHS_DEG = (0.0, 120.0, 240.0)` at
`antenna.py:291`, and broadcast, swept and loaded beam models. It is imported by
nothing except `tests/test_antenna.py` and its own CLI. Every published number in
this study comes from `run_exposure.py`, which never imports it, and whose base
stations radiate isotropically from a position density.

Note one thing before this is called finished. `tests/test_antenna.py:209-241`
asserts that a matched beam, every site putting its peak on the pedestrian, gives
a susceptibility bit-identical to no pattern at all. That is the estimator working
as designed, since a per-direction gain that is constant over the direction being
integrated cancels out of a normalised density. It also means that the literal
reading of *"beamform to 'itself'"* is invisible to this observable. That is worth
telling him plainly rather than shipping an array whose headline configuration
provably changes nothing.

### 2. SMPL-X bystanders that reach a result

2026-08-01 18:27: *"Humans should always be sent to SAM3D, which will create a
fully-fledged, posable SMPLX human for computing exposure later as bystanders."*

**Status: built, run, and connected to nothing that is published.** The bodies are
real. SAM 3 segments people, SAM 3D Body lifts them, `infer_sam3_body.py:67`,
checkpoint `facebook/sam-3d-body-vith`, and 18 bodies exist as
`outputs/korenmarkt_dynamic_bodies/*.npz` with a genuine manifest. They are placed
in scene ENU and range-corrected. `semantic_twin/propagation/bystanders.py` puts
them into a second Mitsuba scene as skin-permittivity triangles and traces it, and
`outputs/bystander_study/korenmarkt_15ghz_rows.jsonl` holds 132 rows from a
completed run. But `run_exposure.py` contains zero references to bystanders,
dynamic bodies or the body library, and no figure in `FIGURES/` and no line in
`PAPER_METHODS.md` mentions SMPL-X or bystanders. The only other consumer is
`export_propagation_payload.py:808-829`, which draws them in Blender.

So the sentence to give him is: the bodies exist and a sensitivity study on them
exists, and neither is in the paper. `BYSTANDERS.md` is honest about this and
says so in its own opening, *"Nothing in `run_exposure.py` was touched"*, so the
gap is disclosed at the module level and invisible at the paper level.

He did also say *"For now, don't start computing exposure"* in the same breath, so
the delay was authorised at the time. What was never done is the lifting of that
hold.

### 3. The guarantee that the first two reflections hit the right material

Covered in the spine section. Never true under the shipped framing, and the
coverage numbers mean it would not bite even if the framing allowed it.

### 4. An LLM predicting material where evidence runs out

2026-08-01 20:06, unanswered:

> *"where does the LLM fit into this? how did we solve point B's material? cant we
> do LLM --> predict a layered rugged material model --> analytical response? or
> perhaps have it look at the google textures idk"*

`DECISIONS.md` "The hidden middle bounce is a ray cast, not an inference problem"
answers the *geometry* half, B is found by ray casting. It explicitly leaves the
material half open: *"What we genuinely lack at B is its material ... handled by
marginalising over the class prior."* A prior is not what he asked for. He asked
for a model that looks at the texture and predicts a layered rough material.
`MATERIAL_VLM.md` and `analyse_material_vlm.py` exist and were touched tonight,
so this may be in progress, but it is not in the propagation path.

### 5. A blend file with everything in it at once

Asked 2026-08-01 20:22, asked again 2026-08-02 23:40: *"I would like to also see
nice blender files with basically everything in it at once."* What exists is a
per-purpose set: `korenmarkt_mesh_study.blend`, the showcase renders, and
`build_propagation_blends.py` producing one file per site for four sites. Asking
twice, thirty hours apart, means the first answer did not land.

### 6. A written reason for stopping at three bounces, and for not using DiffeRT

2026-08-02 23:40. Neither is in `PAPER_METHODS.md`. `measure_bounce_evidence.py`
exists but there is no `BOUNCE_BUDGET.md`, and the repository currently disagrees
with itself about the bounce count in three places, which `CODE_AUDIT.md` section
5 already documents as a defect.

### 7. Smaller items

- **A written answer to the Russian roulette question**, 2026-08-02 22:38. Asked,
  explained in chat, never written down.
- **GHSL population weighting** of standpoints. Named in the 2026-05-31 design as
  the sampling basis, and `ROADMAP.md` phase 6 admits it *"is still not applied"*.
  This one is honestly recorded already.
- **Sixty-nine of eighty-three panorama registrations feed nothing.** Recorded in
  `ROADMAP.md`. Listed here only so the three blockers stay together.

## Decided by an agent, not by him

Distinguishing these matters, because in a year they will all read the same.

- **Russian roulette from bounce 3, floor 0.05.** `tracer.py:250-251`. Agent, in
  the first commit of the file. He questioned it and has not endorsed it.
- **Power summation rather than field summation.** `tracer.py:10-14`. An agent
  call with a stated physical argument, that a publishable angular grid is five to
  seven orders of magnitude too coarse to sum amplitudes. He never asked for
  incoherent. Note it interacts with his MIMO ask, and `DECISIONS.md` "Coherent
  across the array, incoherent across the multipath" is the entry that reconciles
  them, correctly.
- **Polarisation carried, then not carried.** `DECISIONS.md` decided on
  2026-08-01 to carry the 3x3 from the start. `ROADMAP.md` phase 4 records that
  the tracer averages the two Fresnel coefficients into an unpolarised power and
  the cross-polarisation ratio is lost. Both agent calls, and the second reverses
  the first. He was not consulted on either.
- **Eleven cities rather than ten.** Agent, and a good call, but his number was
  ten and the extra site was not offered to him.
- **The 250 m crop radius**, and the retirement of diffraction in favour of it.
  Agent, evidence-driven, recorded in `DECISIONS.md`.
- **Milan Duomo as the second site.** Agent, from a Street View coverage screen.
  He only asked for *"another prominent location"*.
- **Duke as the phantom, and 1 W/m² as the reference incident density.**
  `run_exposure.py:78-88`. Agent. He asked *"how much power do the antennas
  emit?"* at 2026-08-02 23:20, and the honest answer is that no transmit power
  exists anywhere in the propagation code, only a normalising constant. That
  answer should be in the methods.

## Ambiguities left open

Not resolved here on purpose.

- **What he wants the walk to be.** On 2026-08-02 20:36 he said a walk is what
  Google shows you when you scroll. It is not clear whether that is a request to
  change the standpoint sampling, a request to change the *visualisation* so the
  ordering reads as a path, or a comment on the specific bad standpoint that was
  used in a figure. All three readings fit the turn. Ask him.
- **How much of the original monostatic idea he wants back.** On 2026-08-02 23:40
  he says the method *"kinda lost a little bit of its initial spirit"* and that
  line of sight is being *"slapped on top"*. He does not ask for the loop to
  return. He may be asking for the adjoint framing to be *told* as a development
  of the monostatic idea rather than as a replacement for it, which is a writing
  fix and not a physics one. He may also want the monostatic diagnostic actually
  computed, which `DECISIONS.md` promised as a derived quantity and which does not
  exist in code. Ask him which.
- **Whether the marketing licence extends to keeping the semantic layer in the
  headline.** He said a paper can carry the classes and models even when they do
  not improve on an older method. Whether that stretches to a headline table where
  `covered_fraction_by_area` is 0.0 is a different question, and I would not
  assume it does.
- **28 GHz or 15 GHz as the band the paper leads on.** He offered the FR3 pivot,
  it was taken, and a large amount of prose still argues at 28 GHz. He has not
  been asked to confirm.

## Corrections owed to documents I do not own

Recorded here rather than edited, per the ownership split.

**`DECISIONS.md`**

- The entry "Observable: adjoint transfer tensor, not the monostatic loop" claims
  the change *"costs nothing"*. It costs the two-bounce image-evidence guarantee
  described in the spine section above. Add that to the cost side, and note that
  he raised it on 2026-08-02 23:40.
- The same entry says the monostatic response *"is retained as a derived
  diagnostic"*. No such diagnostic exists in code. Either build it or strike the
  sentence.
- "Antennas are post-processing on a stored path set" reads as an implemented
  design. Add a status line saying the array model was not implemented until
  2026-08-03 and is not in any published run.
- Nothing in the file distinguishes an author decision from an agent decision.
  The cheapest fix is a one-word marker on each entry.

**`ROADMAP.md`**

- Phase 4 says the monostatic loop was not built, correctly. Add that its absence
  removed the material guarantee, so the reason it matters is visible.
- The out-of-scope list should include the bystander exposure result, which is
  computed and unpublished, so a reader does not assume it is missing.

**`PAPER_METHODS.md`**

- No mention of DiffeRT or Sionna anywhere. He asked for the reason not to use
  DiffeRT to be stated, 2026-08-02 23:40.
- No stated reason for the three-bounce budget. He asked for that too.
- Section 6 calls the standpoint set a walk. Say plainly that it is a grid over
  walkable ground chained by nearest neighbour, and that it is a different object
  from the panorama walk of `WALK.md`.
- No transmit power appears anywhere. Say so explicitly, since he asked.
- No mention of SMPL-X bystanders. Either bring the bystander study in or say it
  is out.

**`WALK.md` and `COVERAGE.md`**

- Neither states that the Korenmarkt walk is Mapillary while every single-panorama
  site is Google Street View, nor that this departs from an instruction given on
  2026-08-01 18:27. It may well be the right engineering call, Mapillary has the
  dense sequence and Street View does not, but it should be a recorded decision
  rather than a silent one.

**`REPORT.md`**

- Checked, and it makes no MIMO or beamforming claim, which is correct. Its only
  hits on "sector" are the sixteen angular sectors of a spread metric. If the
  array work lands tonight, this is the file most likely to overstate it, since
  it is the narrative document.
