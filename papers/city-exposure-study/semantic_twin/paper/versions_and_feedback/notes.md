First of all, context, we are after all not submitting to IEEE Access but to IEEE OJ-COMS SI semantic_twin/paper/versions_and_feedback/SI-scope.md
So, right away, you will have to
- change the template to whatever OJ-COMS uses, I guess IEEE tran
- dispatch an agent to go find all sorts of pet peeves and guidelines of this specific journal things we should know. if there is a serious problem where we gotta take decisions lmk. small to small-medium stuff u can do urself.
- QA the result

On top of that, this paper is gonna get its edits. BUT, the paper manuscript gets 'reflected' inside of ~/phd/chapter6/, or at least a part of it. The phd has its own quirks, so its not a carbon copy even in the first place. But any change u do here, 99% of the time, also apply it in the phd. Either record very well what u do here (git?) followed by a pass, or do it edit-per-edit. Dont try to code this, its too dangerous.

Since we are also doing a shit ton here, I need you to produce a latexdiff in the end with a point by point report

Oh and finally, note that Wout reviewed a bit older version than what is live. Sometimes I might lose my mind at things that are already fixed or different...

Title:
old: Image-Informed Urban Propagation for Human Body Electromagnetic Field Absorption Across Ten Cities in the FR3 Band
new: Human-Centric 6G RF-EMF Exposure with AI-assisted Digital Twins in Ten Cities

Abstract (applies throughout):
Open directly with exposure. It has to be clear at the end it's an exposure paper. Dont lean tooo much into it cuz OJCOMS doesnt want it too hard, but Wout wants this. So like 1 or 2 sentence. Angle: that we need realistic exposure assessment in actual cities for epidimiological and monitoring reasons

So in the past, we worked with 5 cities, then we expanded to 10 of them and AFAIK those 10 are just perfectly similar same method it is just 10 cities. "Five of these locations" is therefore moot. Scan for 5 or five and flag/remove, cuz that is an old artefact
-the above point could be moot already, might already be done

In general, whenever we talk about routes, and it isnt that necessary to emphasise the "route"ness of the route, default more to the use of "city". So, exposure in "a city", that reads easier esp in places like abstracts and conclusions. u may also say routes in cities.

when u write things like "0.0616 dB", and that includes in figures, i'd prefer it in %. It reads easier and is more convincing. Unless it is not so sexy, id rather have u say 3 dB (>1-2 dB is the threshold)
also around this area, be very concrete, start the sentence explicitly using the word validation (not necessarily THE first word, but u know)

Abstract must contain some "concrete exposure result". Something with SAR. Even if it's dumb, or a bit weird. Ppl gotta have a high level idea of things like median SAR.

The whole ordering in the RESULTS part (toward end) abstract is a little fucked, will need a lot of surgery:
-start with how much SAR
-then factor of 13
-then Direct paths largest share
-then the rest and validation with ray-tracer (dont be vague with "in a controlled test scene", no just say we're validating directly with an RT)
You see, in general, ppl like to see it hiiiigh level and KEEP IT SIMPLE STUPID. AGGRESISIVELY EASY VERBS LIKE IS HAVE GIVE INCREASES etc

So the abstract must essentially start with its goal, briefly, about exposure. Then it can talk about the method. You must sneak the words Human-Centric and Agentic AI (SAM 3 Agent) in there

also note that the abstract is max 250 words. ur over it rn already. but zoom out, and u will notice lots of useless shit to cut (no one cares about Europe, Latin America, and East Asia lol). If u dont know where, start using acronyms directly like EIRP.

Introduction:
Start with explanation about realistic RF-EMF exposure assessment. Go launch an agent that investigates what this means from ~/phd/.
New prose-->KISS verbs, no weird words, subjectverbobject short sentences, calm, papermaker9000 style rules and no AI language (no "X not Y")
cite my npj wireless tech paper in the introduction! see it as part of the lil literature review section

>whole-body absorption depends on
human whole-body absorption depends on

>Projecting
image-derived materials onto city geometry is therefore es-
tablished. This study does not claim any of these operations
as new. It uses them to build a material map around fixed
pedestrian routes, keeping the default geometry-based mate-
rial wherever the images give no reliable label.

remove entirely. will give u space to cite my npj paper. remember, it's exposure too

throughout the introduction we have to get closer to the SI: semantic_twin/paper/versions_and_feedback/SI-scope.md
that means we wanna sell the keywords I highlight there, mostly human-centric, the AI component from the image classification, and also the multimodel sensor fusion.

I'd like to see each paragraph in the introduction, not always but more or less, kinda open with something like 'the literature blabla', 'to solve this problem blabla', 'This work makes following contributions'. I'm being vague, you can do ur own thing, whatever. Essentially, papermaker9000 already gives the perfect recipe for a lit review. Structurally. First of all make sure u get that beat right. And I just want u to be slightly more explicit with signaling that structure. Can be a half-sentence like "Bla blabla bla, continuing..."

The current size is quite good (every addition is more or less a removal), landing more or less at the end of the first column of the second page, typical.

The introduction will need to follow or PM9K claaasic intro structure, WHILE signaling the SI buzzwords in a CONVINCING manner, AND also serving Wout, who is sometimes a bit caveman-y like "exposure mentioned??" "what goal" "contributions what". Wout's pet peeve is generally having really bloody dead simple sentence that state almost the quasi obvious very literally on the highest level. I already mentioned some of these points in my abstract critique. Concretely, add a simple sentence "The goal of this study is [something something 10 cities, not tooo much jargon]." with a period at the end.

Methods
First of all, rethink the entire section structuring. We currently have exotic section titles like Configuration and surface mapping into various other ones. What wout understands:
-Methods
-Results
-maaaybe a full Validation or Discussion section
and THEN u can have SUBsections where u can name them whatever tf u want. So e.g. right here, we have
II. Methods
A. Configuration
B. Agentic AI material assignement (perhaps, idk, ur still in charge)

Ban these words and find a simpler alternative (mini sentences or grammar changes allowed if a one-word replacement is awkward):
-Map / Mapped / Mapping
-Replica (feel free to replace by a mini sentence, OR, if u insist, u may also properly well define it with \emph{replica} and AFTER that u may use it.)
-Registration
-Audit
-Direct/specular transport. It's unclear what transport means.
-Nested
-Have an AI subagent brainstorm other words I might have missed and that fit right in this list, then if u feel confident enough, also ban them. I have the uncommon, weird-for-a-paper, and definitely the antropomorphisation of abstract concepts "doing" things

>Fig. 1 shows the study configuration
Fig. 1 shows the configuration

>Table 1 lists the ten selected routes
good example of where u should mention cities not routes

Fig 1 AND fig 2 have to be latex-placed extremely close to the start of the method section. use htb or htb!

>Fig. 2 shows the computation and its input checks
Fig. 2 shows the flowchart of the method.
this is a PM9K wout pet peeve btw.

You have to nicely, simply, calmly explain "Adjoint ray-tracing", use \emph, add a citation, cuz ppl dont initially know what that is.
When you do this, have a simple sentence go "Fig. 3 shows [short explanation]."

Scan the whole paper for anytime the word therefore or however appear in the non-beginning of a sentence. Then pull them to the beginning and write "Therefore, .." "However".

When u start talking about base stations or Tx. Add "We consider here a Distributed MaMIMO (DMaMIMO) architecture to represent 6G transmitters of the future \cite{something like my npj wireless tech paper}. Modelling a digital twin of future technology inherently means we cannot assume realistic locations of the Access Points (APs). Instead, they are placed uniformly on all plausible locations, in this case, the visible roofline around the user."
Then, pretty quick after you have to refer to Fig. 3 like Fig. 3 shows yadeyade. Hopefully this was already introuced properly with a 'Fig. 3 shows' when we discussed adjoint raytracing before, if not, do so. And the fig has to be close to that location.

Every single equation in this paper should avoid stacking itself so much. Try to have a normal-ass KISS equation. Also "Q = 4096" can easily be prose. In general we just wanna avoid whitespace. Two lines are allowed if ur cramming, but only if hard cramming. in this case do it elegantly and nicely.

The content in the flowchart is bad. I need easier words, verbs, less jargon. Really think high-levle here for a second. imo btw it is also a pretty lame flowchart (barely ok for a fig) cuz it's just one snake lol. It has to end in exposure (SAR). Picture that u are a reader, skimming the paper, this is one of the first things u read. Registration is a banned word. Put an agent on this, read relevant PM9K rules.

Ensure we have a boring introduction of Fig. 4 shows... and then the fig close to it.

Validation and results section opens with a piece of methods honestly... perhaps in a subsection related to human exposure SAR or something?

DO NOT MENTION FUCKING HASH VERIFICATION. God. Codex, if u read this shit and think oh god, u should honestly have the autonomy to remove these blunders without even asking. nobody cares about this. Come on, scan, think. Report this.

Clearly delineate a subsection validation, which would live under results section

>Exact order-1 specular transport

>for a prepared site
wdym prepared? just KISS

I would remove (nearly) all mentions of Fibonacci. It's quite distracting. Just say that the sphere is tesselated. Can also be simply (theta, phi). Glory to simplificty and clarity!

A percentage number cannot be determined to 77.662% accuracy that is insane. KISS man.

Table 2 is mentioning q10 q50 q90 naked like that? omg.. Put over all three: whole-body SAR [W/kg]

Fig 5 10 cities cdf: the tick marks in the top and right axes are a bit odd? Just follow PM9K rules...

Give which city has the highest median SAR. These are fucking obvious high level questions a casual reader expects to see advertized clearly..

In general the paper has to have this philsophy that we serve the POV of the reader, never some mistake we did in the past or some double run or whatever 'history' we had while making this

perhaps a subseciton on material influence? idk

>first-diffuse component
is a bit eye-brow raising. like ppl get confused

>Several limits restrict what the results can say.
Please. No. Results dont "say" things. KISS. I hate this sentence and framing. It's just, we're gonna discuss limitations now. Do better.

Do one of those audits of the paper where u tabulate every single verb used in the whole thing and put in bold where used and then carefully, thoughtfully think, if u stand by it. Aggresively try to use the easiest possible KISS verbs. Think of alternatives.

Conclusion has to have the sentence "Future work will consist of...."

Conclusion has to be clear about its contributions, and quantify key results
Currently the conclusion is about as big as it may get.
